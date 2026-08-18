"""tune_smoother.py — sweep smooth_forecast's gap-bridging policy (Session F+).

WHY THIS EXISTS
---------------
Session F measured that the ghost ball on a no-ball frame is NOT, at the margin,
a detector-precision problem. Raising the detector's score threshold to 0.7 drove
the chain to ZERO false fires after suppress_false_locks on yt_rally2 — and then
smooth_forecast put back seven, ALL of them interpolated. Total ghosts moved 8 ->
7 while recall paid 6.2 points. Anything that quietens the detector just hands the
same frames to the smoother.

So the lever is the smoother's own gap policy, and `max_gap_s = 0.4` has never
been swept. At the shipped ~30 fps that is TWELVE frames of invented ball
bridging a single detector dropout.

The parameter appears twice in smooth_forecast and the sweep moves both together,
which is correct — they are one policy:
  - ball.py:759   `miss >= max_gap` ends the segment (a filtering decision)
  - ball.py:793   `1 < (b - a) <= max_gap + 1` emits the bridge (a drawing one)

ONE PERCEPTION PASS, EVERY VALUE. smooth_forecast runs at the END of the chain,
so remove_outliers -> rectify_track -> suppress_false_locks -> gate_ball_to_court
is a fixed prefix computed once and every max_gap_s is scored in memory. Same
pattern as tools/tune_suppress.py, and unlike the score threshold (which lives
inside the detector and costs a fresh GPU pass per value).

  cd backend && .venv-train/Scripts/python.exe ../tools/tune_smoother.py \\
      --clip yt_rally2 --device cuda --frame-step 1

Scored against human gold clicks. The column that decides is `ghost` — the
FULL-row fires split solid/faded, which IS what the annotated video draws (see
tools/eval_model_filters.py). Recall and far_geo are the hard constraint: E6
bought them and this may not spend them.

FLOOR: max_gap = max(2, round(max_gap_s * fps_eff)), so 0.0 does not disable
bridging — it clamps to 2 frames. That floor is reported, not hidden.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import cv2  # noqa: E402

import _goldset as gs  # noqa: E402  — single source for the gold clip table
from eval_model_filters import (CLIPS, build_calib, far_masks, gold,  # noqa: E402
                                measure, perceive)

SWEEP = (0.0, 0.10, 0.15, 0.20, 0.30, 0.40)     # 0.40 is shipped
# This tool sweeps a parameter and picks a value from the result, so it may
# never select the blind HOLDOUT clips (review finding P0-1) — CLIPS itself
# stays the full calibrated_map() import above since eval_model_filters also
# uses it for single-config reporting runs, which the holdout stays open to.
TUNABLE_CLIPS = gs.tunable_calibrated_map()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", default="yt_rally2", choices=list(TUNABLE_CLIPS))
    ap.add_argument("--weights", default="weights/ballnet_v21.pt")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--frame-step", type=int, default=None,
                    help="1 makes every gold frame scoreable; am_hard_utr is "
                         "48.6%% odd frames, so its labels need it")
    ap.add_argument("--max-gap-s", type=float, nargs="+", default=list(SWEEP))
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    from swingvision import ball as B, calibration

    video_rel, pts_rel, labels_rel = CLIPS[args.clip]
    cap = cv2.VideoCapture(str(REPO / video_rel))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    H, hfov = build_calib(pts_rel, (W, Hh))
    step = args.frame_step or max(1, round(src_fps / 30.0))
    fps_eff = src_fps / step
    rs = Hh / 720.0
    cam_xyz = calibration.camera_position_m(H, (W, Hh), hfov)
    ballg, noball = gold(labels_rel)
    far_px, far_geo = far_masks(ballg, H, (W, Hh))

    scoreable = sum(1 for f in ballg if f % step == 0)
    print(f"{args.clip} {W}x{Hh} @ {src_fps:.0f}fps, step={step}, "
          f"fps_eff={fps_eff:.0f}, res_scale={rs:.2f}")
    print(f"  {scoreable} of {len(ballg)} labelled ball frames scoreable, "
          f"{len(noball)} no-ball frames\n")

    t0 = time.time()
    raw = perceive(REPO / video_rel, args.weights, args.device, H, cam_xyz,
                   W, Hh, fps_eff, step)
    print(f"  one perception pass, {time.time()-t0:.0f}s; every max_gap_s below "
          f"is scored from it\n")

    # Fixed prefix — identical to pipeline.analyze_video up to the smoother.
    pre = B.remove_outliers(list(raw), max_jump=max(W, Hh) * 0.06)
    pre = B.rectify_track(pre, max_speed_px=3000.0 * rs / fps_eff,
                          resid_px=35.0 * rs)
    pre = B.suppress_false_locks(pre, fps_eff=fps_eff, res_scale=rs)
    pre = B.gate_ball_to_court(pre, H, (W, Hh), hfov_deg=hfov)
    measure(pre, ballg, noball, step, "before smoother (reference)",
            far_px, far_geo)
    print()

    print(f"    {'stage':<32}{'false-fire':>7}{'recall':>9}{'far_px':>10}"
          f"{'far_geo':>9}")
    print("-" * 88)
    rows = []
    for g in args.max_gap_s:
        frames = max(2, round(g * fps_eff))
        tag = f"max_gap_s={g:.2f} ({frames}f)" + ("  <- shipped" if g == 0.40 else "")
        tr, coasted, _ = B.smooth_forecast(list(pre), fps_eff=fps_eff,
                                           res_scale=rs, max_gap_s=g)
        r = measure(tr, ballg, noball, step, tag, far_px, far_geo,
                    coasted=coasted)
        r["max_gap_s"] = g
        r["max_gap_frames"] = frames
        rows.append(r)

    print("\nMeasured against human gold clicks; hit = within 10 px. `fires` IS "
          "the ghost-ball product metric:\nthe frames the annotated video draws a "
          "ball on top of a human's 'no ball'. Solid = a real\ndetection, faded = "
          "interpolated. Pick on solid fires at flat recall/far_geo.")
    if any(g * fps_eff < 2 for g in args.max_gap_s):
        print(f"NOTE max_gap floors at 2 frames, so max_gap_s below "
              f"{2/fps_eff:.3f}s on this clip is the same policy.")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "tune_smoother",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "clip": args.clip, "weights": args.weights, "device": args.device,
            "frame_step": step, "fps_eff": round(fps_eff, 2),
            "resolution": f"{W}x{Hh}",
            "measured_against":
                f"human gold clicks on {args.clip}; hit = within 10 px. "
                f"{scoreable} of {len(ballg)} labelled ball frames scoreable at "
                f"step={step}; {len(noball)} no-ball frames. `fires` is the "
                f"ghost-ball product metric, split solid/faded.",
            "rows": rows}, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
