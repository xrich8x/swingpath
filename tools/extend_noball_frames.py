"""Append extra likely-no-ball frames to an existing gold manifest.

The first labeling round exposed that the FP rate rests on few no-ball frames
(the selection heuristic over-predicted "no ball"; the human found a ball in
most of them). This adds frames chosen from two much stronger signals:

  seeded      frames temporally adjacent to the human's confirmed no-ball
              labels (dead time clusters around what a human called dead)
  fp-candidate frames where a trigger-happy track (archive / ballnet) locks
              but BOTH static-gated fresh tracks are silent — prime
              false-positive territory, the most informative frames to label

New frames get bucket "noball" so eval_gold.py folds them into the existing
FP columns with no changes. Labels already given are untouched; the labeler
resumes at the first new unlabeled frame.

  backend/.venv/Scripts/python.exe tools/extend_noball_frames.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from select_gold_frames import extract, load_cache, spread, static_flags  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", default="yt_rally2")
    ap.add_argument("--gold-dir", default="data/gold")
    ap.add_argument("--count", type=int, default=50)
    ap.add_argument("--seed-window", type=int, default=120,
                    help="video frames around each human no-ball label")
    ap.add_argument("--eager", nargs="*", default=[
        "data/output/demo30.perception.json",
        "data/output/demo30b.perception.json",
    ], help="trigger-happy caches (their solo locks flag FP candidates)")
    ap.add_argument("--gated", nargs="*", default=[
        "data/output/demo30_staticgate_fusion.perception.json",
        "data/output/demo30_staticgate_tracknet.perception.json",
    ], help="static-gated caches (must be silent for an FP candidate)")
    args = ap.parse_args()

    gold = REPO / args.gold_dir
    man_path = gold / f"{args.clip}.manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    labels = json.loads((gold / f"{args.clip}.labels.json")
                        .read_text(encoding="utf-8"))["labels"]

    have = {r["frame"] for r in manifest["frames"]}
    step = manifest["params"]["frame_step"]

    eager = [load_cache(REPO / c) for c in args.eager]
    gated = [load_cache(REPO / c) for c in args.gated]
    n_idx = min(len(c["ball_px"]) for c in eager + gated)
    eager_live = []
    for c in eager:
        flags = static_flags(c["ball_px"])
        eager_live.append([c["ball_px"][i] is not None and not flags[i]
                           for i in range(n_idx)])

    # human-confirmed dead time: even frames near a no-ball label
    seeds = [int(k) for k, v in labels.items() if v.get("ball") is False]
    seeded = set()
    for s in seeds:
        for f in range(s - args.seed_window, s + args.seed_window + 1):
            if f % step == 0 and 0 <= f // step < n_idx and f not in have:
                seeded.add(f)

    # FP candidates: an eager track locks (non-static), both gated ones silent
    fp_cand = set()
    for i in range(n_idx):
        f = i * step
        if f in have or f in seeded:
            continue
        if any(live[i] for live in eager_live) and \
                all(c["ball_px"][i] is None for c in gated):
            fp_cand.add(f)

    half = args.count // 2
    picked = spread(sorted(fp_cand), half)
    picked += spread(sorted(seeded - set(picked)), args.count - len(picked))
    picked = sorted(set(picked))

    manifest["frames"] = sorted(
        manifest["frames"] + [{"frame": f, "bucket": "noball"} for f in picked],
        key=lambda r: r["frame"])
    manifest["bucket_counts"]["noball"] += len(picked)
    manifest.setdefault("extensions", []).append({
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tool": "extend_noball_frames.py",
        "added": len(picked),
        "fp_candidates": sum(1 for f in picked if f in fp_cand),
        "seeded": sum(1 for f in picked if f in seeded),
    })
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    extract(REPO / manifest["video"], gold / "frames" / args.clip, picked)
    print(f"added {len(picked)} noball frames "
          f"({manifest['extensions'][-1]['fp_candidates']} FP-candidates, "
          f"{manifest['extensions'][-1]['seeded']} near human no-ball labels)")
    print(f"manifest now {len(manifest['frames'])} frames")


if __name__ == "__main__":
    main()
