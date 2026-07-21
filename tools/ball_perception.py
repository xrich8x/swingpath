"""Ball-only perception runner for the gold benchmark (HANDOFF §11).

Runs a chosen ball model + BallTracker over a clip and writes an
eval_gold-compatible cache ({frame_step, ball_px, ...}). Deliberately skips
pose/calibration so it works on clips with NO court corners (e.g. yt_match40,
the cold generalization clip) and stays a pure ball-tracking measurement.

Within one clip every model runs under identical conditions (same bgsub, same
gate state), so tracks are comparable; do NOT compare raw numbers across clips
with different calibration/gating.

For BallNet weight selection: --ballnet-weights, or the BALLNET_WEIGHTS env
var (OurBallDetector reads it), so v1 and v2 can be run without touching the
shipped ballnet.pt.

Run from backend/ so relative weight paths resolve:
  cd backend
  .venv-train\\Scripts\\python.exe ..\\tools\\ball_perception.py \\
     --video ..\\data\\yt_match40.mp4 --ball-model ours \\
     --ballnet-weights weights/ballnet_v2.pt --device cuda \\
     --out ..\\data\\output\\yt_match40_v2.perception.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))


def build_detectors(ball_model: str, device: str, tracknet_w: str):
    from swingvision.ball import BallDetector, WASBDetector
    dets, wf = [], {}
    if ball_model in ("tracknet", "fusion", "all"):
        d = BallDetector(tracknet_w, device=device); dets.append(d)
        wf["tracknet"] = getattr(d, "weights_path", tracknet_w)
    if ball_model in ("wasb", "fusion", "all"):
        d = WASBDetector(device=device); dets.append(d)
        wf["wasb"] = getattr(d, "weights_path", None)
    if ball_model in ("ours", "all"):
        from swingvision.ball import OurBallDetector
        d = OurBallDetector(device=device); dets.append(d)
        wf["ballnet"] = getattr(d, "weights_path", None)
    if not dets:
        raise SystemExit(f"unknown ball_model {ball_model!r}")
    return dets, wf


def load_homography(keypoints: str | None):
    if not keypoints:
        return None
    from swingvision import court
    from swingvision.calibration import compute_homography
    with open(keypoints, encoding="utf-8") as f:
        kp = json.load(f)
    names = [n for n in ("near_bl_doubles", "near_br_doubles",
                         "far_bl_doubles", "far_br_doubles") if n in kp]
    if len(names) < 4:
        return None
    return compute_homography([court.LANDMARKS[n] for n in names],
                              [kp[n] for n in names])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ball-model", default="tracknet",
                    choices=["tracknet", "wasb", "fusion", "ours", "all"])
    ap.add_argument("--ballnet-weights", default=None,
                    help="BallNet checkpoint for --ball-model ours (else BALLNET_WEIGHTS env)")
    ap.add_argument("--tracknet-weights", default="weights/tracknet.pt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--frame-step", type=int, default=1)
    ap.add_argument("--target-fps", type=float, default=None,
                    help="decimate to this frame rate instead of --frame-step "
                         "(allows non-integer ratios, e.g. 60 -> 24). Writes the "
                         "kept source frame indices as 'src_frames'.")
    ap.add_argument("--keypoints", default=None,
                    help="court corners json -> enables the court-plausibility gate")
    ap.add_argument("--no-bgsub", action="store_true")
    # Gate ablation (E3e): the detector puts the ball as its strongest blob on
    # 70.9% of gold frames while the pipeline reports 49.2%, so ~22 points are
    # destroyed between the two. These switches attribute that loss to a gate.
    ap.add_argument("--no-court-gate", action="store_true",
                    help="disable the court-plausibility gate")
    ap.add_argument("--no-static-gate", action="store_true",
                    help="disable the static-fixture gate")
    ap.add_argument("--velocity-gate", type=float, default=None,
                    help="override the velocity/distance gate in px (default 70)")
    ap.add_argument("--max-coast", type=int, default=None)
    ap.add_argument("--far-tile", action="store_true",
                    help="add a native-resolution far-court crop as a second "
                         "detector (SAHI-style); needs --keypoints")
    ap.add_argument("--max-frames", type=int, default=None)
    args = ap.parse_args()

    if args.ballnet_weights:
        os.environ["BALLNET_WEIGHTS"] = args.ballnet_weights

    import cv2
    from swingvision import calibration
    from swingvision.ball import BallTracker, median_background
    from swingvision.pipeline import COURT_GATE_MIN_CAM_H

    use_bgsub = not args.no_bgsub
    dets, weight_files = build_detectors(args.ball_model, args.device,
                                         args.tracknet_weights)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {args.video}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
    n_src = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # Frame selection. --target-fps decimates by timestamp (handles 60->24, which
    # no integer --frame-step can express); --frame-step keeps every k-th frame.
    keep: set[int] | None = None
    if args.target_fps:
        if src_fps <= 0:
            raise SystemExit("--target-fps needs a readable source fps")
        if args.target_fps > src_fps + 1e-6:
            raise SystemExit(f"--target-fps {args.target_fps} exceeds source {src_fps:.2f}")
        limit = min(n_src, args.max_frames) if args.max_frames else n_src
        n_out = int(round(limit * args.target_fps / src_fps))
        keep = {min(limit - 1, int(round(j * src_fps / args.target_fps)))
                for j in range(n_out)}
        eff_fps = args.target_fps
    else:
        eff_fps = src_fps / args.frame_step if src_fps else 0.0

    H = load_homography(args.keypoints)
    gate_H = cam_xyz = None
    if H is not None:
        cam_xyz = calibration.camera_position_m(H, (width, height), 70.0)
        gate_H = H if cam_xyz is not None else None
    print(f"[ball] {args.ball_model} on {Path(args.video).name} "
          f"({width}x{height}) src={src_fps:.2f}fps -> {eff_fps:.2f}fps "
          f"gate={'ON' if gate_H is not None else 'OFF'} "
          f"bgsub={use_bgsub} device={args.device}")

    # The background plate is a static-scene estimate; sample it identically
    # regardless of decimation so it is not a hidden variable across fps runs.
    bg, inv = (median_background(args.video, args.frame_step, args.max_frames)
               if use_bgsub else (None, 2.0))
    tk = dict(background=bg, inv_scale=inv, use_bgsub=use_bgsub,
              homography=None if args.no_court_gate else gate_H, fps=eff_fps,
              cam_xyz=cam_xyz)
    if args.no_static_gate:
        tk.update(static_step_px=0.0, static_min_run=10**9)
    if args.velocity_gate is not None:
        tk["gate"] = args.velocity_gate
    if args.max_coast is not None:
        tk["max_coast"] = args.max_coast
    if args.far_tile and H is not None:
        from swingvision.ball import RoiDetector, far_court_roi
        roi = far_court_roi(H, (width, height))
        if roi:
            tile_dets, _ = build_detectors(args.ball_model, args.device,
                                           args.tracknet_weights)
            dets = list(dets) + [RoiDetector(d, roi) for d in tile_dets]
            print(f"[ball] far-court tile detector ON roi={roi}")
    tracker = BallTracker(dets, (width, height), **tk)

    cap = cv2.VideoCapture(args.video)
    ball_px, src_frames = [], []
    idx = processed = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok or (args.max_frames is not None and idx >= args.max_frames):
            break
        take = (idx in keep) if keep is not None else (idx % args.frame_step == 0)
        if take:
            ball_px.append(tracker.update(frame))   # no pose exclude boxes
            src_frames.append(idx)
            processed += 1
            if processed % 500 == 0:
                dt = time.time() - t0
                print(f"  {processed} frames  {processed/dt:.1f} fps", flush=True)
        idx += 1
    cap.release()

    n_lock = sum(p is not None for p in ball_px)
    dt = time.time() - t0
    print(f"[ball] {processed} frames in {dt:.0f}s "
          f"({processed/max(dt,1e-6):.1f} fps); locks {n_lock}, "
          f"model={tracker.n_tnet} bg={tracker.n_bg} static-suppressed={tracker.n_static}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "frame_step": args.frame_step,
            "src_fps": round(src_fps, 3),
            "eff_fps": round(eff_fps, 3),
            # Present only for --target-fps runs, where the kept frames are not a
            # fixed stride; consumers (eval_gold) prefer it over frame_step.
            "src_frames": src_frames if keep is not None else None,
            "max_frames": args.max_frames,
            "bgsub": bool(use_bgsub),
            "ball_model": args.ball_model,
            "provenance": {
                "tool": "ball_perception.py",
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "video": Path(args.video).name,
                "weight_files": weight_files,
                "device": args.device,
                "court_gate": gate_H is not None,
                "static_gate": [tracker.static_step_px, tracker.static_min_run],
            },
            "ball_px": [list(p) if p else None for p in ball_px],
        }, f)
    print(f"[ball] wrote {args.out}")


if __name__ == "__main__":
    main()
