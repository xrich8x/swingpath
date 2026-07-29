"""tune_suppress.py — sweep ball.suppress_false_locks against the gold labels.

`suppress_false_locks` is the single largest recall loss in the shipped chain: on
am_hard_utr (1080p) it cost 15 points (50.3 -> 35.4) to buy 21 points of
false-fire, against the 3.9 points documented at 720p. This sweeps its parameters
so the operating point is chosen from measurement rather than inherited.

One GPU perception pass, then every parameter combination is evaluated in memory
against the human gold clicks — so a full sweep costs the same as a single ladder
run. Frame alignment uses the same guard as tools/eval_gold.py: a gold frame the
decimation never processed is SKIPPED, not scored as a miss.

    cd backend && .venv-train/Scripts/python.exe ../tools/tune_suppress.py \\
        --clip am_hard_utr --device cuda --frame-step 1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import ball as B, calibration, court, courtfit  # noqa: E402

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
CLIPS = {
    "am_hard_utr": ("data/am_hard_utr.mp4", "data/am_hard_utr_pts.json",
                    "data/gold/am_hard_utr.labels.json"),
    "yt_rally2": ("data/yt_rally2.mp4", "data/yt_rally2_pts.json",
                  "data/gold/yt_rally2.labels.json"),
    "yt_match40": ("data/yt_match40.mp4", "data/yt_match40_pts.json",
                   "data/gold/yt_match40.labels.json"),
}


def build_calib(pts_rel, wh):
    kp = json.loads((REPO / pts_rel).read_text(encoding="utf-8"))
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                       [kp[n] for n in CORN])
    fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court,
                                wh[0], wh[1], allow_roll=True)
    hfov = 70.0 if fit is None else float(calibration.hfov_from_focal(fit[3][5], wh[0]))
    return H, hfov


def score(tr, ball, noball, step, far_geo):
    def at(f):
        return (f // step) if (f % step == 0 and f // step < len(tr)) else None

    hit = tot = hg = tg = 0
    for f, v in ball.items():
        pf = at(f)
        if pf is None:
            continue
        tot += 1
        p = tr[pf]
        ok = p is not None and math.dist(p, (v["x"], v["y"])) <= 10.0
        hit += ok
        if f in far_geo:
            tg += 1; hg += ok
    nb = [f for f in noball if at(f) is not None]
    fires = sum(1 for f in nb if tr[at(f)] is not None)
    return (100 * hit / max(tot, 1), 100 * hg / max(tg, 1),
            100 * fires / max(len(nb), 1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", default="am_hard_utr", choices=list(CLIPS))
    ap.add_argument("--weights", default="weights/ballnet_v21.pt")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--frame-step", type=int, default=None)
    args = ap.parse_args()

    video_rel, pts_rel, labels_rel = CLIPS[args.clip]
    video = REPO / video_rel
    cap = cv2.VideoCapture(str(video))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0; cap.release()
    H, hfov = build_calib(pts_rel, (W, Hh))
    step = args.frame_step or max(1, round(src_fps / 30.0))
    fps_eff = src_fps / step
    rs = Hh / 720.0

    g = {int(k): v for k, v in json.loads((REPO / labels_rel).read_text(encoding="utf-8"))["labels"].items()}
    ball = {f: v for f, v in g.items() if v.get("ball") and not v.get("unsure")}
    noball = [f for f, v in g.items() if v.get("ball") is False and not v.get("unsure")]
    far_geo = set()
    for f, v in ball.items():
        try:
            if calibration.court_scale_m_per_px(H, (v["x"], v["y"])) > \
                    calibration.RELIABLE_SCALE_M_PER_PX:
                far_geo.add(f)
        except Exception:
            pass

    os.environ["BALLNET_WEIGHTS"] = args.weights
    from swingvision.ball import OurBallDetector, BallTracker
    det = OurBallDetector(device=args.device)
    cam_xyz = calibration.camera_position_m(H, (W, Hh), hfov)
    tracker = BallTracker([det], (W, Hh), use_bgsub=False, homography=H,
                          fps=fps_eff, cam_xyz=cam_xyz)
    cap = cv2.VideoCapture(str(video))
    raw, idx, t0 = [], 0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            raw.append(tracker.update(frame))
        idx += 1
    cap.release()
    print(f"{args.clip} {W}x{Hh} step={step} fps_eff={fps_eff:.0f} rs={rs:.2f} | "
          f"perceived {len(raw)} frames in {time.time()-t0:.0f}s")
    print(f"gold: {len(ball)} ball ({len(far_geo)} far_geo) / {len(noball)} no-ball\n")

    # Everything up to suppression is fixed; only its parameters vary.
    pre = B.remove_outliers(list(raw), max_jump=max(W, Hh) * 0.06)
    pre = B.rectify_track(pre, max_speed_px=3000.0 * rs / fps_eff, resid_px=35.0 * rs)
    r0, f0, ff0 = score(pre, ball, noball, step, far_geo)
    print(f"{'seg_dur':>8}{'seg_gap':>9}{'recall':>9}{'far_geo':>9}{'false-fire':>12}")
    print("-" * 47)
    print(f"{'(off)':>8}{'-':>9}{r0:>8.1f}%{f0:>8.1f}%{ff0:>11.1f}%")

    for seg_dur in (0.15, 0.10):
        for seg_gap in (0.0, 0.03, 0.05, 0.10):
            tr = B.suppress_false_locks(list(pre), fps_eff=fps_eff, res_scale=rs,
                                        seg_dur_s=seg_dur, seg_gap_s=seg_gap)
            tr = B.gate_ball_to_court(tr, H, (W, Hh), hfov_deg=hfov)
            tr, _c, _q = B.smooth_forecast(tr, fps_eff=fps_eff, res_scale=rs)
            r, fg, ff = score(tr, ball, noball, step, far_geo)
            print(f"{seg_dur:>8.2f}{seg_gap:>9.2f}{r:>8.1f}%{fg:>8.1f}%{ff:>11.1f}%")
    print("\nFULL shipped chain after suppression (court gate + kalman), scored "
          "against human gold clicks. '(off)' is the track entering suppression.")


if __name__ == "__main__":
    main()
