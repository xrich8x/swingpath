"""select_farcourt_labels.py — queue the far-court frames worth a human click.

WHY THIS EXISTS
---------------
Far-court recall has been "waiting on a few hundred human labels" for several
sessions and never started, because the real number was never counted. It is
**4,087 frames** across **1,267 distinct bracketed gaps** — 4-5 hours of clicking.
A task that size does not get done; a ranked few hundred does.
(Counts and method: data/output/farcourt_label_yield.md.)

Filling them automatically is a MEASURED NEGATIVE: 89% of those frames sit in
bridges of <=10 frames with a confident detection on both sides, but interpolating
between the anchors lands within 10 px of a human click only **63%** of the time,
flat across bridge length. A label that wrong is a Gaussian on empty court.

WHAT THIS SELECTS, AND THE ONE JUDGEMENT IN IT
----------------------------------------------
ONE FRAME PER GAP, the midpoint. Every frame inside a 10-frame gap is a
near-duplicate of its neighbours, so labelling all ten buys roughly one frame of
information for ten clicks. The midpoint is also the furthest from both anchors —
the hardest and most informative single frame in the gap.

Clips are sampled round-robin so no clip dominates: labelling 300 frames from one
rally teaches far less than 300 spread across lighting, courts and camera heights.

--with-anchors (default) also queues the two anchor frames either side of each
gap. They cost clicks but earn them three times over:
  * CONTEXT — arrow-keying anchor -> midpoint -> anchor shows where the ball came
    from and went to, which is most of how a human finds a 2 px ball;
  * A CONTROL — if the anchors are easy to click and the midpoints are not, the
    frames are unlabelable rather than the labeller being slow;
  * A CHECK ON THE PSEUDO-LABELS — the anchors ARE tracker output, so a human
    disagreeing with one is a mislabelled training positive.

THE PREMISE THIS PILOT TESTS, WHICH IS NOT YET ESTABLISHED
-----------------------------------------------------------
The source videos for all 14 training clips are GONE; only 512x288 extracted JPEGs
survive. A far ball is ~1.6 px at that width. Spot checks show the interpolated
point often landing on background the same colour as the ball (white ball on white
signage, dark ball on dark wall) — plausibly why the detector missed it, and
plausibly why a human will too. **Run a small --gaps first and see whether the ball
is visibly there before committing hours.** If it is not, this data cannot be
labelled at all and the fix is new footage, not more clicking.

    py tools/select_farcourt_labels.py --gaps 10          # ~30 frames, a pilot
    py tools/lab_server.py                                # label them, Label tab

Writes into data/labels/ (the TRAIN pool). It refuses to touch data/gold/.
"""
from __future__ import annotations

import argparse
import bisect
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

IN_W, IN_H = 512, 288
FAR_FRAC = 0.36          # the project's resolution-comparable far_px band
MAX_GAP = 10             # 89% of far-court misses; beyond this there is no anchor


def candidates(data_root: Path, max_gap: int = MAX_GAP):
    """One (dir, a, pa, mid, p_interp, b, pb) per bracketed far-court gap."""
    out = []
    for lp in sorted(glob.glob(str(data_root / "*" / "labels.json"))):
        d = json.loads(Path(lp).read_text(encoding="utf-8"))
        L = d.get("labels") or {}
        neg = set(d.get("negatives") or [])
        # Windows are separate moments in the source video spliced into one
        # directory, so a gap spanning a boundary joins two unrelated positions.
        # Only ~1% do, but interpolating across one is meaningless.
        ws = sorted(d.get("window_starts") or [])
        ks = sorted(int(k) for k in L)
        for a, b in zip(ks, ks[1:]):
            g = b - a - 1
            if not (1 <= g <= max_gap):
                continue
            if ws and bisect.bisect_right(ws, a) != bisect.bisect_right(ws, b):
                continue
            xa, ya = L[str(a)]
            xb, yb = L[str(b)]
            m = (a + b) // 2
            if m in neg:
                continue
            t = (m - a) / (b - a)
            yi = ya + (yb - ya) * t
            if yi >= FAR_FRAC * IN_H:
                continue
            out.append((os.path.dirname(lp), a, (xa, ya), m,
                        (xa + (xb - xa) * t, yi), b, (xb, yb)))
    return out


def round_robin(cands, n):
    """Take from each clip in turn so no clip dominates the queue."""
    by = {}
    for c in cands:
        by.setdefault(c[0], []).append(c)
    for v in by.values():                      # spread within a clip too
        step = max(1, len(v) // max(1, n))
        v[:] = v[::step]
    picked, i = [], 0
    keys = sorted(by)
    while len(picked) < n and any(by[k] for k in keys):
        k = keys[i % len(keys)]
        if by[k]:
            picked.append(by[k].pop(0))
        i += 1
    return picked


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(REPO / "data/ball_dataset"))
    ap.add_argument("--out", default=str(REPO / "data/labels"))
    ap.add_argument("--clip", default="farcourt_pilot",
                    help="name of the queue; becomes <clip>.manifest.json")
    ap.add_argument("--gaps", type=int, default=10,
                    help="number of GAPS, not frames. With --with-anchors each "
                         "gap contributes 3 frames")
    ap.add_argument("--with-anchors", dest="anchors", action="store_true", default=True)
    ap.add_argument("--no-anchors", dest="anchors", action="store_false")
    ap.add_argument("--max-gap", type=int, default=MAX_GAP)
    args = ap.parse_args()

    out = Path(args.out)
    if "gold" in out.parts:
        raise SystemExit("refusing to write into the gold (TEST) pool")
    # Second, independent check that the mining root holds no gold clip.
    from train_ballnet import assert_no_gold_leak
    assert_no_gold_leak(args.data, exclude=())

    cands = candidates(Path(args.data), args.max_gap)
    print(f"{len(cands)} bracketed far-court gaps in {args.data}")
    picked = round_robin(cands, args.gaps)
    if not picked:
        raise SystemExit("no candidates")

    frames_dir = out / "frames" / args.clip
    frames_dir.mkdir(parents=True, exist_ok=True)
    rows, idx = [], 0
    for d, a, pa, m, pm, b, pb in picked:
        trio = [(a, pa, "anchor"), (m, pm, "farcourt_gap"), (b, pb, "anchor")]
        for src, (px, py), bucket in (trio if args.anchors else trio[1:2]):
            s = Path(d) / f"{src:05d}.jpg"
            if not s.is_file():
                continue
            shutil.copyfile(s, frames_dir / f"f{idx:05d}.jpg")
            rows.append({"frame": idx, "bucket": bucket,
                         # provenance so a click can be traced back to the frame
                         # it came from — these are renumbered, not source indices
                         "src_dataset": os.path.basename(d), "src_frame": src,
                         # what the tracker/interpolation thinks; the UI does not
                         # show it, so it cannot bias the click
                         "prior_x": round(px, 1), "prior_y": round(py, 1)})
            idx += 1

    man = {"clip": args.clip, "video": None,
           "source": "data/ball_dataset extracted frames; the source videos for "
                     "these clips no longer exist, so 512x288 is all there is",
           "width": IN_W, "height": IN_H, "fps": None, "video_frames": idx,
           "created": time.strftime("%Y-%m-%d %H:%M:%S"),
           "params": {"tool": "select_farcourt_labels.py", "gaps": len(picked),
                      "max_gap": args.max_gap, "far_frac": FAR_FRAC,
                      "with_anchors": args.anchors,
                      "selection": "midpoint of each bracketed far-court gap, "
                                   "round-robin over clips"},
           "bucket_counts": {b: sum(1 for r in rows if r["bucket"] == b)
                             for b in {r["bucket"] for r in rows}},
           "frames": rows}
    (out / f"{args.clip}.manifest.json").write_text(json.dumps(man, indent=1),
                                                    encoding="utf-8")
    clips = sorted({r["src_dataset"] for r in rows})
    print(f"wrote {out}/{args.clip}.manifest.json — {len(picked)} gaps, "
          f"{idx} frames, {len(clips)} clips")
    print(f"  {man['bucket_counts']}")
    print()
    print("Label them:  py tools/lab_server.py   (Label tab, TRAINING POOL)")
    print("THE QUESTION THIS ANSWERS: can you see the ball on the "
          "'farcourt_gap' frames at all? The 'anchor' frames are the control — "
          "the tracker found a ball on those, so if they are easy and the gaps "
          "are not, this data is unlabelable and the fix is new footage.")


if __name__ == "__main__":
    main()
