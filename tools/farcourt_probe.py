"""farcourt_probe.py — is far-court failure a RESOLUTION problem? (E2)

Measured on yt_rally2's human gold labels: the far ball is 3.9 px across in the
source frame and the detector resizes 1280x720 down to its 640x360 input, so the
net actually sees a ball **2.0 px wide**. Near-court balls survive at 4.0 px.
Contrast is not the culprit — far balls measure 142/255 against the dark curtain
versus 71/255 near. Only size differs.

If that diagnosis is right, feeding the same detector a crop at native (or
better) resolution should recover far-court balls with NO retraining. This tool
tests exactly that, in three conditions:

  full     1280x720 -> 640x360, the shipping path                (baseline)
  tile     fixed native-resolution tiles over the far court      (shippable)
  oracle   a 640x360 native crop centred on the human's click    (upper bound —
           cheating on WHERE to look, to isolate whether RESOLUTION is the
           blocker. Never a shippable number; it answers "is it worth
           engineering the where?")

Scored on the gold FAR-court frames only, at 10 px and TrackNet's own 5 px.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\farcourt_probe.py --device cuda
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

IN_W, IN_H = 640, 360


def crop_box(cx, cy, w, h, W, H):
    """A w x h box centred on (cx, cy), shifted to stay inside the frame."""
    x0 = int(round(min(max(cx - w / 2, 0), W - w)))
    y0 = int(round(min(max(cy - h / 2, 0), H - h)))
    return x0, y0, x0 + w, y0 + h


def detect_in(det, frames, box=None):
    """Run the detector over 3 consecutive frames, optionally on a fixed crop.

    Returns (x, y) in FULL-FRAME pixels, or None. The crop is identical across
    the three frames so the net's motion cue stays valid.
    """
    det.reset()
    out = None
    for f in frames:
        sub = f if box is None else f[box[1]:box[3], box[0]:box[2]]
        out = det.detect(sub)
    if out is None or box is None:
        return out
    # detect() already scaled from 640x360 back to the CROP's pixel space.
    return out[0] + box[0], out[1] + box[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", default=str(REPO / "data/yt_rally2.mp4"))
    ap.add_argument("--labels", default=str(REPO / "data/gold/yt_rally2.labels.json"))
    ap.add_argument("--weights", default="weights/tracknet.pt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--far-y", type=float, default=260.0,
                    help="image y above which a ball counts as far court")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    from swingvision.ball import BallDetector
    det = BallDetector(args.weights, device=args.device)

    gold = json.loads(Path(args.labels).read_text(encoding="utf-8"))["labels"]
    far = {int(k): v for k, v in gold.items()
           if v.get("ball") and not v.get("unsure") and v["y"] < args.far_y}
    print(f"{len(far)} gold FAR-court ball frames (image y < {args.far_y:g})")

    cap = cv2.VideoCapture(args.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Fixed tiles over the far court: two native-res 640x360 windows, overlapping
    # in x, covering where far balls actually live (measured y range 128-387).
    tiles = [(200, 60, 840, 420), (560, 60, 1200, 420)]

    res = {k: {"hit10": 0, "hit5": 0, "found": 0, "errs": []}
           for k in ("full", "tile", "oracle")}
    for f, lab in sorted(far.items()):
        frames = []
        for j in (f - 2, f - 1, f):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, j))
            ok, img = cap.read()
            if ok:
                frames.append(img)
        if len(frames) < 3:
            continue
        truth = (lab["x"], lab["y"])

        got = {"full": detect_in(det, frames)}

        best = None
        for t in tiles:
            p = detect_in(det, frames, t)
            if p is None:
                continue
            d = math.dist(p, truth)
            if best is None or d < best[1]:
                best = (p, d)
        got["tile"] = best[0] if best else None

        box = crop_box(truth[0], truth[1], IN_W, IN_H, W, H)
        got["oracle"] = detect_in(det, frames, box)

        for k, p in got.items():
            if p is None:
                continue
            d = math.dist(p, truth)
            res[k]["found"] += 1
            res[k]["errs"].append(d)
            res[k]["hit10"] += d <= 10
            res[k]["hit5"] += d <= 5
    cap.release()

    n = len(far)
    hdr = f"{'condition':<10}{'fires':>8}{'hit@10':>9}{'hit@5':>8}{'median err':>13}"
    print("\n" + hdr)
    print("-" * len(hdr))
    for k in ("full", "tile", "oracle"):
        r = res[k]
        med = f"{np.median(r['errs']):.1f}px" if r["errs"] else "—"
        print(f"{k:<10}{r['found']:>7}/{n}{100*r['hit10']/n:>8.1f}%"
              f"{100*r['hit5']/n:>7.1f}%{med:>13}")
    print("\nbaseline for scale: near-court hit@10 is ~81% on this clip.")
    print("'oracle' cheats on WHERE to look and is not a shippable number — it "
          "answers\nwhether RESOLUTION is the blocker. If oracle >> full, the "
          "remaining work is\npredicting the crop, which the previous frame's "
          "track already tells us.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"video": Path(args.video).name, "n_far": n, "far_y": args.far_y,
             "tiles": tiles,
             "results": {k: {kk: (vv if kk != "errs" else
                                  round(float(np.median(vv)), 2) if vv else None)
                             for kk, vv in v.items()} for k, v in res.items()}},
            indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
