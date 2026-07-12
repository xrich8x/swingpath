"""Directly score a BallNet checkpoint against the human gold ball clicks.

Runs the model on the 3-frame window (newest first, 512x288 — the training input)
at each gold frame, scales the heatmap peak back to video pixels, and compares to
the human click. Reports, per clip:
  hit@10   fraction of ball frames located within 10 px of the human click
  med_px   median localization error on ball frames
  FF%      false-fire rate on NO-BALL frames (peak >= score_thresh)

This is the honest metric (human clicks, not the tracker's pseudo-labels) for the
blur/occlusion-augmentation retrain. Unsure frames are excluded.

  backend/.venv/Scripts/python.exe tools/eval_ballnet_gold.py --weights backend/weights/ballnet.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
from swingvision._ballnet import BallNet  # noqa: E402

IN_W, IN_H = 512, 288
CLIPS = {"yt_rally2": "data/yt_rally2.mp4", "yt_match40": "data/yt_match40.mp4"}


def window(cap, F):
    """3 frames [F, F-1, F-2] resized to model input, or None if unavailable."""
    out = []
    for f in (F, F - 1, F - 2):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(f, 0))
        ok, im = cap.read()
        if not ok:
            return None
        out.append(cv2.resize(im, (IN_W, IN_H)))
    arr = np.concatenate(out, axis=2).astype(np.float32) / 255.0
    return np.ascontiguousarray(np.rollaxis(arr, 2, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--thresh", type=float, default=0.5, help="fire threshold for FF")
    args = ap.parse_args()

    model = BallNet()
    ckpt = torch.load(args.weights, map_location=args.device)
    model.load_state_dict(ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt)
    model.eval().to(args.device)
    print(f"model: {args.weights}")

    for clip, vid in CLIPS.items():
        man = json.loads((REPO / "data" / "gold" / f"{clip}.manifest.json").read_text())
        W, H = man["width"], man["height"]
        labs = json.loads((REPO / "data" / "gold" / f"{clip}.labels.json").read_text())["labels"]
        cap = cv2.VideoCapture(str(REPO / vid))
        errs, fires = [], []
        for k, v in labs.items():
            if v.get("unsure"):
                continue
            w = window(cap, int(k))
            if w is None:
                continue
            with torch.no_grad():
                hm = torch.sigmoid(model(torch.from_numpy(w[None]).to(args.device)))[0, 0]
            peak = float(hm.max())
            iy, ix = np.unravel_index(int(hm.argmax().cpu()), hm.shape)
            if v.get("ball"):
                px, py = ix * W / IN_W, iy * H / IN_H
                errs.append(float(np.hypot(px - v["x"], py - v["y"])))
            else:
                fires.append(peak >= args.thresh)
        cap.release()
        errs = np.array(errs)
        hit10 = 100 * (errs <= 10).mean() if len(errs) else 0.0
        med = np.median(errs) if len(errs) else float("nan")
        ff = 100 * np.mean(fires) if fires else 0.0
        print(f"  {clip:12s} hit@10 {hit10:5.1f}%  med {med:6.1f}px  FF {ff:5.1f}%  "
              f"(ball n={len(errs)}, noball n={len(fires)})")


if __name__ == "__main__":
    main()
