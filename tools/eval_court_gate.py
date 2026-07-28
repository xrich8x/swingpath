"""eval_court_gate.py — does the court-region gate keep the REAL ball?

`ball.gate_ball_to_court` drops locks outside the court's image region. Its whole
risk is over-rejection: a gate that also eats real far-court balls buys precision
with recall, which this project has explicitly refused to do.

So measure it the only honest way — against the HUMAN GOLD CLICKS. Every ball
frame a person labelled is, by definition, a real ball; the fraction the gate
would keep is its recall ceiling. Nothing here uses model output.

    cd backend && .venv/Scripts/python.exe ../tools/eval_court_gate.py

Reports, per calibrated gold clip and pooled: retention overall, retention in the
far band, and the two rungs side by side (A = extruded play volume from the fitted
camera, B = ground trapezoid + a resolution-scaled pixel band).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import ball as ball_mod, calibration, court, courtfit  # noqa: E402

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")

# Gold clips that HAVE a calibration. gold_shell/gold_clay/gold_am have none, so
# they cannot be scored here at all — an H-dependent gate has nothing to test.
CLIPS = [
    ("am_hard_utr", "data/am_hard_utr.mp4", "data/am_hard_utr_pts.json"),
    ("yt_rally2", "data/yt_rally2.mp4", "data/yt_rally2_pts.json"),
    ("yt_match40", "data/yt_match40.mp4", "data/yt_match40_pts.json"),
]


def load_clip(pts_path, video):
    kp = json.loads(Path(pts_path).read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(str(video))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                       [kp[n] for n in CORN])
    # Fit the actual camera for the lens: assuming 70 deg misreads every clip
    # (am_hard_utr is 86, yt_match40 is 21) and the gate's geometry depends on it.
    hfov = None
    fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court,
                                w, h, allow_roll=True)
    if fit is not None:
        hfov = float(calibration.hfov_from_focal(fit[3][5], w))
    return H, (w, h), hfov


def retention(clicks, poly):
    if poly is None:
        return None
    keep = sum(cv2.pointPolygonTest(poly, (float(x), float(y)), False) >= 0
               for x, y in clicks)
    return keep, len(clicks)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--far-frac", type=float, default=0.36,
                    help="far band as a fraction of frame height (resolution-relative)")
    ap.add_argument("--max-ball-height", type=float, default=6.0)
    args = ap.parse_args()

    print(f"{'clip':<13}{'lens':>8}{'A all':>13}{'A far':>13}"
          f"{'B all':>13}{'B far':>13}{'old all':>13}{'old far':>13}")
    print("-" * 88)
    agg = {k: [0, 0] for k in ("a", "af", "b", "bf", "o", "of")}
    for tag, video, pts in CLIPS:
        lab = REPO / "data" / "gold" / f"{tag}.labels.json"
        if not lab.exists() or not (REPO / video).exists() or not (REPO / pts).exists():
            continue
        H, wh, hfov = load_clip(REPO / pts, REPO / video)
        gold = json.loads(lab.read_text(encoding="utf-8"))["labels"]
        clicks = [(v["x"], v["y"]) for v in gold.values()
                  if v.get("ball") and not v.get("unsure")]
        far_y = args.far_frac * wh[1]
        far = [c for c in clicks if c[1] < far_y]

        pa = ball_mod.play_volume_polygon(H, wh, hfov_deg=hfov,
                                          max_ball_height_m=args.max_ball_height)
        pb = ball_mod.play_volume_polygon(H, wh, hfov_deg=None)
        # "old": the shipped-before behaviour — 220/120 px ABSOLUTE at any
        # resolution. Undo rung B's scaling to reproduce it exactly.
        po = ball_mod.play_volume_polygon(
            H, wh, hfov_deg=None,
            top_extra_px=220.0 * 720.0 / wh[1], side_extra_px=120.0 * 1280.0 / wh[0])
        cells = []
        for poly, keys in ((pa, ("a", "af")), (pb, ("b", "bf")), (po, ("o", "of"))):
            for pts_set, key in ((clicks, keys[0]), (far, keys[1])):
                r = retention(pts_set, poly)
                if r is None or r[1] == 0:
                    cells.append("     n/a")
                    continue
                agg[key][0] += r[0]
                agg[key][1] += r[1]
                cells.append(f"{100 * r[0] / r[1]:.1f}% ({r[1]})")
        lens = "n/a" if hfov is None else f"{hfov:.0f}deg"
        print(f"{tag:<13}{lens:>8}" + "".join(f"{c:>13}" for c in cells))
    print("-" * 88)
    out = []
    for key in ("a", "af", "b", "bf", "o", "of"):
        n, d = agg[key]
        out.append("n/a" if d == 0 else f"{100 * n / d:.1f}% ({d})")
    print(f"{'POOLED':<13}{'':>8}" + "".join(f"{c:>13}" for c in out))
    print("\nMeasured against human gold clicks (data/gold/*.labels.json); every "
          "labelled ball frame is a real ball, so these are retention ceilings.")


if __name__ == "__main__":
    main()
