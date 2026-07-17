"""Line-fit AUTO court detection (project B), measured on the court gold labels.

No per-court model. The pipeline is generate -> score -> snap -> verify:
  1. GUESS GRID: sweep plausible behind-baseline court shapes, parameterised as a
     trapezoid (near/far baseline height, half-widths, centre). Widths/heights may
     exceed the frame, so OFF-FRAME corners are represented for free.
  2. SCORE cheaply: each guess's projected court lines vs a distance-transform of
     the amateur line mask (line_ridge_mask) — pick the top-K by coverage.
  3. SNAP the top-K onto the lines (refine_homography_bounded, ridge mask).
  4. VERIFY (verify_court): keep the best that clears the coverage+centrality gate;
     if none clears it, return None (falls back to manual — never a wrong court).

Scored against the human gold labels (same metrics as eval_court):
  detect%   fraction of usable frames an auto court was returned + verified
  corner    median px error of the 4 baseline corners vs the human clicks
  kp_err    median px error over all 14 keypoints
  IoU       court-outline overlap with the human court
  false%    unusable frames that wrongly returned a court (must stay ~0)

  backend/.venv/Scripts/python.exe tools/eval_court_autodetect.py --all --per-clip 3
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

GOLD = REPO / "data" / "gold"

from swingvision import courtfit as _courtfit
from swingvision.courtfit import (  # noqa: F401  (engine moved to the package)
    DBL, _quad_iou, autodetect,
)


def __getattr__(name):  # keep `ad._anything` working for older scripts
    return getattr(_courtfit, name)


def score_clip(clip, per_clip, grid, topk, use_prior=True):
    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        return None
    import cv2
    from swingvision import calibration, court

    labs = json.loads(lab_path.read_text(encoding="utf-8"))["labels"]
    frames_dir = GOLD / "frames" / clip
    usable = [k for k, v in labs.items()
              if v.get("court") is True and all(n in v.get("keypoints", {}) for n in DBL)]
    unusable = [k for k, v in labs.items() if v.get("court") is False]
    if per_clip:
        usable = usable[:: max(1, len(usable) // per_clip)][:per_clip]
        unusable = unusable[:per_clip]

    det = 0
    corner_e, kp_e, ious = [], [], []
    for k in usable:
        img = cv2.imread(str(frames_dir / f"f{int(k):05d}.jpg"))
        if img is None:
            continue
        res = autodetect(img, calibration, court, grid=grid, topk=topk, use_prior=use_prior)
        if res is None:
            continue
        det += 1
        H = res[0]
        gk = labs[k]["keypoints"]
        corner_e += [float(np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                      - np.array(gk[n])))) for n in DBL]
        kp_e += [float(np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                  - np.array(gk[n])))) for n in gk if n in court.LANDMARKS]
        pc = [tuple(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]) for n in DBL]
        ious.append(_quad_iou(pc, [tuple(gk[n]) for n in DBL]))

    false = 0
    for k in unusable:
        img = cv2.imread(str(frames_dir / f"f{int(k):05d}.jpg"))
        if img is None:
            continue
        if autodetect(img, calibration, court, grid=grid, topk=topk) is not None:
            false += 1

    return {"clip": clip, "usable": len(usable), "det": det,
            "detect_pct": 100 * det / len(usable) if usable else 0.0,
            "corner": median(corner_e) if corner_e else None,
            "kp": median(kp_e) if kp_e else None,
            "iou": median(ious) if ious else None,
            "unusable": len(unusable),
            "false_pct": 100 * false / len(unusable) if unusable else None}


def fmt(x, s="{:.1f}"):
    return "  -  " if x is None else s.format(x)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--per-clip", type=int, default=3, help="frames per clip (0=all)")
    ap.add_argument("--grid", type=int, default=4, help="guesses per axis")
    ap.add_argument("--topk", type=int, default=8, help="candidates to snap+verify")
    ap.add_argument("--no-prior", action="store_true", help="disable the camera-angle prior")
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))
    print(f"camera-angle prior: {'OFF' if args.no_prior else 'ON'}")

    hdr = (f"{'clip':22s} {'frm':>3s} {'detect%':>7s} {'corner':>6s} "
           f"{'kp_err':>6s} {'IoU':>5s} {'false%':>6s}")
    print(hdr); print("-" * len(hdr))
    agg = {"det": [], "cor": [], "iou": [], "false": []}
    for c in clips:
        r = score_clip(c, args.per_clip if args.per_clip else 0, args.grid, args.topk,
                       use_prior=not args.no_prior)
        if r is None:
            continue
        print(f"{r['clip']:22s} {r['usable']:3d} {fmt(r['detect_pct']):>7s} "
              f"{fmt(r['corner']):>6s} {fmt(r['kp']):>6s} "
              f"{fmt(r['iou'],'{:.2f}'):>5s} {fmt(r['false_pct']):>6s}")
        agg["det"].append(r["detect_pct"])
        if r["corner"] is not None:
            agg["cor"].append(r["corner"])
        if r["iou"] is not None:
            agg["iou"].append(r["iou"])
        if r["false_pct"] is not None:
            agg["false"].append(r["false_pct"])
    print("-" * len(hdr))
    print(f"{'MEAN':22s} {'':3s} {fmt(np.mean(agg['det'])):>7s} "
          f"{fmt(np.median(agg['cor']) if agg['cor'] else None):>6s} "
          f"{'':6s} {fmt(np.median(agg['iou']) if agg['iou'] else None,'{:.2f}'):>5s} "
          f"{fmt(np.mean(agg['false']) if agg['false'] else None):>6s}")


if __name__ == "__main__":
    main()
