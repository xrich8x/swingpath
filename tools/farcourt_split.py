"""farcourt_split.py — hit@10 split by near/far image row, from gold labels.

The new gold clips are uncalibrated (uniform manifest, no court buckets), so
eval_gold cannot split near/far. This does it directly from the human clicks:
far = image y below --far-y (the ball high in the frame = far court). Reports
recall and false-fire per detector, per region.

  backend/.venv/Scripts/python.exe tools/farcourt_split.py \
      --labels data/gold/gold_shell.labels.json \
      --caches A.perception.json B.perception.json --names TrackNet BallNet
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def at(cache):
    src = cache.get("src_frames")
    if src:
        lut = {int(f): i for i, f in enumerate(src)}
        return lambda f: lut.get(f)
    step = cache["frame_step"]
    n = len(cache["ball_px"])
    return lambda f: (f // step) if (f % step == 0 and f // step < n) else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--caches", nargs="+", required=True)
    ap.add_argument("--names", nargs="+", required=True)
    ap.add_argument("--radius", type=float, default=10.0)
    ap.add_argument("--far-y", type=float, default=260.0)
    args = ap.parse_args()

    gold = {int(k): v for k, v in load(args.labels)["labels"].items()}
    ball = {f: v for f, v in gold.items() if v.get("ball") and not v.get("unsure")}
    noball = {f: v for f, v in gold.items()
              if v.get("ball") is False and not v.get("unsure")}
    far = {f: v for f, v in ball.items() if v["y"] < args.far_y}
    near = {f: v for f, v in ball.items() if v["y"] >= args.far_y}
    print(f"{Path(args.labels).stem}: {len(ball)} ball ({len(far)} far, "
          f"{len(near)} near), {len(noball)} no-ball\n")

    def region_hit(cache_at, ball_px, subset):
        hit = tot = 0
        for f, v in subset.items():
            pos = cache_at(f)
            if pos is None or pos >= len(ball_px):
                continue
            tot += 1
            p = ball_px[pos]
            if p and math.dist(p, (v["x"], v["y"])) <= args.radius:
                hit += 1
        return hit, tot

    hdr = f"{'detector':<12}{'all':>10}{'far':>10}{'near':>10}{'false-fire':>12}"
    print(hdr); print("-" * len(hdr))
    for name, cpath in zip(args.names, args.caches):
        cache = load(cpath)
        cat = at(cache)
        bp = cache["ball_px"]
        ha, ta = region_hit(cat, bp, ball)
        hf, tf = region_hit(cat, bp, far)
        hn, tn = region_hit(cat, bp, near)
        fp = ft = 0
        for f in noball:
            pos = cat(f)
            if pos is None or pos >= len(bp):
                continue
            ft += 1
            fp += bp[pos] is not None
        def pct(a, b):
            return f"{100*a/b:.1f}%" if b else "–"
        print(f"{name:<12}{pct(ha,ta):>10}{pct(hf,tf):>10}{pct(hn,tn):>10}"
              f"{pct(fp,ft):>12}")


if __name__ == "__main__":
    main()
