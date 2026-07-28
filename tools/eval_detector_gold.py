"""eval_detector_gold.py — raw-detector recall + false-fire on the gold clips (E5).

Isolates what a BallNet retrain changed, without the tracker's gates: for every
gold frame, run the detector on its 3-frame window and score recall (hit@10 on
ball frames), far-court recall (image y < 260), and false-fire (fires on a
no-ball frame). Point it at two weight files to compare v2.1 vs baseline.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\eval_detector_gold.py \\
      --weights weights/ballnet_v21.pt --device cuda
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

CLIPS = [
    ("am_hard_utr", "data/am_hard_utr.mp4"),   # NEW 1080p gold (primary)
    ("gold_shell", "data/gold_shell.mp4"),
    ("gold_clay", "data/gold_clay.mp4"),
    ("gold_am", "data/gold_am.mp4"),
    ("yt_rally2", "data/yt_rally2.mp4"),
    ("yt_match40", "data/yt_match40.mp4"),
]


def score_clip(det, video, labels, radius=10.0, far_frac=0.36):
    gold = {int(k): v for k, v in json.loads(Path(labels).read_text(encoding="utf-8"))["labels"].items()}
    ball = {f: v for f, v in gold.items() if v.get("ball") and not v.get("unsure")}
    noball = {f: v for f, v in gold.items() if v.get("ball") is False and not v.get("unsure")}
    cap = cv2.VideoCapture(str(video))
    # far-court band as a fraction of frame height, so 720p and 1080p are comparable
    far_y = far_frac * (cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720.0)
    hit = tot = fhit = ftot = fp = ftt = 0
    want = sorted(set(ball) | set(noball))
    for f in want:
        frames = []
        for j in (f - 2, f - 1, f):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, j))
            ok, im = cap.read()
            if ok:
                frames.append(im)
        if len(frames) < 3:
            continue
        det.reset()
        p = None
        for im in frames:
            p = det.detect(im)
        if f in ball:
            v = ball[f]
            tot += 1
            ok10 = p is not None and math.dist(p, (v["x"], v["y"])) <= radius
            hit += ok10
            if v["y"] < far_y:
                ftot += 1
                fhit += ok10
        else:
            ftt += 1
            fp += p is not None
    cap.release()
    return dict(recall=100 * hit / max(tot, 1), far=100 * fhit / max(ftot, 1),
                ff=100 * fp / max(ftt, 1), n=tot, nfar=ftot, nnb=ftt)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--weights", required=True)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    os.environ["BALLNET_WEIGHTS"] = args.weights
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=args.device)
    print(f"weights={args.weights}\n")
    print(f"{'clip':<12}{'recall':>8}{'far':>8}{'false-fire':>12}")
    print("-" * 40)
    agg = {"hit": 0, "tot": 0, "fhit": 0, "ftot": 0, "fp": 0, "ftt": 0}
    for tag, video in CLIPS:
        labels = REPO / "data" / "gold" / f"{tag}.labels.json"
        if not labels.exists() or not (REPO / video).exists():
            continue
        r = score_clip(det, REPO / video, labels)
        print(f"{tag:<12}{r['recall']:>7.1f}%{r['far']:>7.1f}%{r['ff']:>11.1f}%")
        agg["hit"] += r["recall"] / 100 * r["n"]; agg["tot"] += r["n"]
        agg["fhit"] += r["far"] / 100 * r["nfar"]; agg["ftot"] += r["nfar"]
        agg["fp"] += r["ff"] / 100 * r["nnb"]; agg["ftt"] += r["nnb"]
    print("-" * 40)
    print(f"{'POOLED':<12}{100*agg['hit']/max(agg['tot'],1):>7.1f}%"
          f"{100*agg['fhit']/max(agg['ftot'],1):>7.1f}%"
          f"{100*agg['fp']/max(agg['ftt'],1):>11.1f}%")


if __name__ == "__main__":
    main()
