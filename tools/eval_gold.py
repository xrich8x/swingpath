"""Score perception caches against the human gold labels (HANDOFF §8 fix 1.4).

The first honest benchmark in this project: every earlier number was
self-graded (models scored against their own teacher's pseudo-labels). Here
the reference is a human's clicks from gold_label_server.py.

For each cache, on gold BALL frames:
  hit    the track has a lock within --radius px (default 10) of the click
  wrong  the track has a lock, but farther than --radius (locked onto
         something else — HUD box, other ball, net post)
  miss   the track has no lock at all
and on gold NO-BALL frames:
  FP     the track claims a lock where the human says there is no ball in play

"Unsure" labels are excluded from all denominators. Frames whose video frame
number is not a multiple of the cache's frame_step are skipped for that cache
(counted and reported).

Usage (repo root):
  backend/.venv/Scripts/python.exe tools/eval_gold.py \
      --labels data/gold/yt_rally2.labels.json \
      data/output/demo30.perception.json [more caches ...] \
      [--names archive968 ...] [--radius 10] [--markdown out.md]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median


def load(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cache_index(cache: dict):
    """frame -> position in ball_px, or None if that frame was not processed.

    Caches written by `ball_perception.py --target-fps` carry an explicit
    `src_frames` list (decimation by timestamp is not a fixed stride); everything
    else is the classic every-`frame_step`-th-frame layout.
    """
    src = cache.get("src_frames")
    if src:
        lut = {int(f): i for i, f in enumerate(src)}
        return lambda f: lut.get(f)
    step = cache["frame_step"]
    n = len(cache["ball_px"])
    return lambda f: (f // step) if (f % step == 0 and f // step < n) else None


def score(cache: dict, gold: dict[int, dict], buckets: dict[int, str],
          radius: float) -> dict:
    at = cache_index(cache)
    ball_px = cache["ball_px"]
    res = {
        "n_ball": 0, "hit": 0, "wrong": 0, "miss": 0,
        "n_noball": 0, "fp": 0, "skipped": 0,
        "errors": [],            # px error on ball frames where a lock exists
        "hits5": 0, "hits25": 0,
        "per_bucket": {},        # bucket -> dict(n, hit, wrong, miss, n_nb, fp)
    }
    for frame, lab in gold.items():
        pos = at(frame)
        if pos is None or pos >= len(ball_px):
            res["skipped"] += 1
            continue
        lock = ball_px[pos]
        b = res["per_bucket"].setdefault(
            buckets.get(frame, "?"),
            {"n": 0, "hit": 0, "wrong": 0, "miss": 0, "n_nb": 0, "fp": 0})
        if lab["ball"] is True:
            res["n_ball"] += 1
            b["n"] += 1
            if lock is None:
                res["miss"] += 1
                b["miss"] += 1
            else:
                err = math.dist(lock, (lab["x"], lab["y"]))
                res["errors"].append(err)
                res["hits5"] += err <= 5
                res["hits25"] += err <= 25
                if err <= radius:
                    res["hit"] += 1
                    b["hit"] += 1
                else:
                    res["wrong"] += 1
                    b["wrong"] += 1
        else:  # ball is False -> human says no ball in play
            res["n_noball"] += 1
            b["n_nb"] += 1
            if lock is not None:
                res["fp"] += 1
                b["fp"] += 1
    return res


def pct(a: int, b: int) -> str:
    return f"{100.0 * a / b:5.1f}%" if b else "    –"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("caches", nargs="+", help="perception cache json files")
    ap.add_argument("--labels", default="data/gold/yt_rally2.labels.json")
    ap.add_argument("--manifest", default=None,
                    help="defaults to <labels dir>/<clip>.manifest.json")
    ap.add_argument("--names", nargs="*", default=None,
                    help="display names, one per cache (default: file stems)")
    ap.add_argument("--radius", type=float, default=10.0)
    ap.add_argument("--common-frames", action="store_true",
                    help="score only gold frames that EVERY cache processed. "
                         "Required for fps comparisons: a decimated run sees "
                         "fewer gold frames, and a different frame subset is a "
                         "different test set.")
    ap.add_argument("--markdown", default=None,
                    help="also write the tables as markdown to this file")
    args = ap.parse_args()

    gold_data = load(args.labels)
    clip = gold_data["clip"]
    man_path = args.manifest or str(Path(args.labels).parent / f"{clip}.manifest.json")
    manifest = load(man_path)
    buckets = {r["frame"]: r["bucket"] for r in manifest["frames"]}

    gold: dict[int, dict] = {}
    n_unsure = 0
    for k, lab in gold_data["labels"].items():
        if lab.get("unsure") or lab.get("ball") is None:
            n_unsure += 1
        else:
            gold[int(k)] = lab

    caches = [load(c) for c in args.caches]
    if args.common_frames:
        before = len(gold)
        for cache in caches:
            at = cache_index(cache)
            n = len(cache["ball_px"])
            gold = {f: lab for f, lab in gold.items()
                    if (p := at(f)) is not None and p < n}
        print(f"[common-frames] {before} -> {len(gold)} gold frames "
              f"processed by all {len(caches)} caches")

    n_ball = sum(1 for v in gold.values() if v["ball"])
    n_nob = len(gold) - n_ball
    names = args.names or [Path(c).name.replace(".perception.json", "")
                           for c in args.caches]
    if len(names) != len(args.caches):
        raise SystemExit("--names must match the number of caches")

    lines: list[str] = []

    def w(s: str = "") -> None:
        print(s)
        lines.append(s)

    w(f"Gold labels: {args.labels}  clip={clip}")
    w(f"  {len(gold)} scored frames = {n_ball} ball + {n_nob} no-ball"
      f"  ({n_unsure} unsure excluded)")
    w(f"  hit radius: {args.radius:g} px")
    w()

    results = []
    for cache, name in zip(caches, names):
        results.append((name, score(cache, gold, buckets, args.radius)))

    hdr = (f"{'track':<22} {'hit@10':>7} {'wrong>10':>9} {'miss':>6} "
           f"{'hit@5':>7} {'hit@25':>7} {'med.err':>8} {'FP(no-ball)':>12}")
    w(hdr)
    w("-" * len(hdr))
    for name, r in results:
        med = f"{median(r['errors']):6.1f}px" if r["errors"] else "      –"
        w(f"{name:<22} {pct(r['hit'], r['n_ball']):>7} "
          f"{pct(r['wrong'], r['n_ball']):>9} {pct(r['miss'], r['n_ball']):>6} "
          f"{pct(r['hits5'], r['n_ball']):>7} {pct(r['hits25'], r['n_ball']):>7} "
          f"{med:>8} {pct(r['fp'], r['n_noball']):>12}"
          + (f"  [{r['skipped']} skipped]" if r["skipped"] else ""))
    w()

    bucket_names = [b for b in ("serve", "near", "far", "disagree", "noball")
                    if any(b in r["per_bucket"] for _, r in results)]
    cols = bucket_names + ["noball-FP"]
    w(f"per bucket: hit@{args.radius:g} on ball frames; last column = "
      f"false-positive rate on the no-ball frames of the noball bucket")
    hdr2 = f"{'track':<22}" + "".join(f" {b:>10}" for b in cols)
    w(hdr2)
    w("-" * len(hdr2))
    for name, r in results:
        row = f"{name:<22}"
        for b in bucket_names:
            pb = r["per_bucket"].get(b)
            row += f" {pct(pb['hit'], pb['n']) if pb else '–':>10}"
        nb = r["per_bucket"].get("noball")
        row += f" {pct(nb['fp'], nb['n_nb']) if nb else '–':>10}"
        w(row)

    if args.markdown:
        md = ["| track | hit@10 | wrong>10 | miss | hit@5 | hit@25 | med.err | FP (no-ball) |",
              "|---|---|---|---|---|---|---|---|"]
        for name, r in results:
            med = f"{median(r['errors']):.1f}px" if r["errors"] else "–"
            md.append(
                f"| {name} | {pct(r['hit'], r['n_ball']).strip()} "
                f"| {pct(r['wrong'], r['n_ball']).strip()} "
                f"| {pct(r['miss'], r['n_ball']).strip()} "
                f"| {pct(r['hits5'], r['n_ball']).strip()} "
                f"| {pct(r['hits25'], r['n_ball']).strip()} | {med} "
                f"| {pct(r['fp'], r['n_noball']).strip()} |")
        md.append("")
        md.append("| track | " + " | ".join(cols) + " |")
        md.append("|---|" + "---|" * len(cols))
        for name, r in results:
            cells = []
            for b in bucket_names:
                pb = r["per_bucket"].get(b)
                cells.append(pct(pb["hit"], pb["n"]).strip() if pb else "–")
            nb = r["per_bucket"].get("noball")
            cells.append(pct(nb["fp"], nb["n_nb"]).strip() if nb else "–")
            md.append(f"| {name} | " + " | ".join(cells) + " |")
        Path(args.markdown).write_text("\n".join(md) + "\n", encoding="utf-8")
        w(f"\nmarkdown tables -> {args.markdown}")


if __name__ == "__main__":
    main()
