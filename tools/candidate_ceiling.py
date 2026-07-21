"""candidate_ceiling.py — how good could tracking POSSIBLY get? (E3e)

We keep fixing the tracker one gate at a time and the numbers keep moving a
little. Before doing that again, this asks the question that bounds the whole
effort: when we miss the ball, is it because the DETECTOR never saw it, or
because our tracker picked the wrong one of several things it did see?

The detector's heatmap usually lights up in several places. `_postprocess` keeps
exactly one — the strongest blob — and BallTracker then applies hard gates to
that single survivor. Any frame where the true ball was the 2nd or 3rd blob is
lost forever, and no amount of gate-tuning downstream can recover it.

So: decode the top-K blobs per gold frame and report

  top-1     the ball is the strongest blob            (today's ceiling)
  top-K     the ball is ANY of the top K blobs        (the ceiling a smarter
                                                       selector could reach)
  none      no blob within tolerance                  (a genuine detector miss —
                                                       only better perception or
                                                       higher resolution helps)

If top-K greatly exceeds top-1, the tracker is throwing away recoverable ball
and the fix is SELECTION (offline global trajectory optimisation over
candidates), not more gates. If top-K ~ top-1, the detector is the ceiling and
selection work is wasted.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\candidate_ceiling.py --device cuda
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


def decode_topk(det, feature_map, k: int, thresh: int = 127):
    """All blobs in the heatmap, strongest first, in FRAME pixels."""
    fm = feature_map.reshape((det.in_h, det.in_w)).astype(np.uint8)
    _, binm = cv2.threshold(fm, thresh, 255, cv2.THRESH_BINARY)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(binm, connectivity=8)
    blobs = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < 1:
            continue
        peak = float(fm[lab == i].max())
        blobs.append((area * peak, float(cent[i][0]), float(cent[i][1])))
    blobs.sort(key=lambda b: -b[0])
    return blobs[:k]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", default=str(REPO / "data/yt_rally2.mp4"))
    ap.add_argument("--labels", default=str(REPO / "data/gold/yt_rally2.labels.json"))
    ap.add_argument("--weights", default="weights/tracknet.pt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--radius", type=float, default=10.0)
    ap.add_argument("--far-y", type=float, default=260.0)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    import torch
    from swingvision.ball import BallDetector
    det = BallDetector(args.weights, device=args.device)

    gold = {int(k): v for k, v in
            json.loads(Path(args.labels).read_text(encoding="utf-8"))["labels"].items()
            if v.get("ball") and not v.get("unsure")}
    cap = cv2.VideoCapture(args.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    res = {"n": 0, "top1": 0, "topk": 0, "none": 0, "ranks": [],
           "far_n": 0, "far_top1": 0, "far_topk": 0}
    for f, lab in sorted(gold.items()):
        frames = []
        for j in (f - 2, f - 1, f):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, j))
            ok, img = cap.read()
            if ok:
                frames.append(img)
        if len(frames) < 3:
            continue
        imgs = np.concatenate([cv2.resize(x, (det.in_w, det.in_h)) for x in
                               (frames[2], frames[1], frames[0])],
                              axis=2).astype(np.float32) / 255.0
        inp = torch.from_numpy(np.rollaxis(imgs, 2, 0)[None]).float().to(det.device)
        with torch.no_grad():
            out = det.model(inp)
        fmap = out.argmax(dim=1).detach().cpu().numpy()[0]

        truth = (lab["x"], lab["y"])
        far = lab["y"] < args.far_y
        res["n"] += 1
        res["far_n"] += far
        rank = None
        for i, (_, cx, cy) in enumerate(decode_topk(det, fmap, args.topk)):
            p = (cx * W / det.in_w, cy * H / det.in_h)
            if math.dist(p, truth) <= args.radius:
                rank = i
                break
        if rank is None:
            res["none"] += 1
        else:
            res["ranks"].append(rank)
            res["topk"] += 1
            res["far_topk"] += far
            if rank == 0:
                res["top1"] += 1
                res["far_top1"] += far
    cap.release()

    n, fn = res["n"], max(res["far_n"], 1)
    print(f"{n} gold ball frames, top-{args.topk} blobs, hit radius {args.radius:g}px\n")
    hdr = f"{'':<34}{'all court':>12}{'far court':>12}"
    print(hdr); print("-" * len(hdr))
    print(f"{'ball IS the strongest blob':<34}{100*res['top1']/n:>11.1f}%"
          f"{100*res['far_top1']/fn:>11.1f}%")
    print(f"{f'ball is among the top {args.topk}':<34}{100*res['topk']/n:>11.1f}%"
          f"{100*res['far_topk']/fn:>11.1f}%")
    print(f"{'detector never saw it':<34}{100*res['none']/n:>11.1f}%"
          f"{100*(fn-res['far_topk'])/fn:>11.1f}%")
    if res["ranks"]:
        from collections import Counter
        c = Counter(res["ranks"])
        print(f"\nwhere the ball ranked when present: "
              + ", ".join(f"#{r+1}: {c[r]}" for r in sorted(c)))
    head = 100 * (res["topk"] - res["top1"]) / n
    print(f"\nRecoverable by better SELECTION alone: {head:.1f} points of recall "
          f"({res['topk'] - res['top1']} frames).")
    print(f"Today's shipped pipeline scores 49.2% hit@10 on these labels, so the "
          f"selection ceiling is {100*res['topk']/n:.1f}%.")

    if args.json_out:
        res.pop("ranks", None)
        Path(args.json_out).write_text(json.dumps(
            {"video": Path(args.video).name, "topk": args.topk,
             "radius": args.radius, **res}, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
