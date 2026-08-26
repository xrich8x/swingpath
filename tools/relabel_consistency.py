"""relabel_consistency.py — measure whether the gold labels agree with THEMSELVES.

WHY THIS EXISTS (review finding P0-2)
-------------------------------------
Every number in docs/STATE.md is a comparison against 1,851 human ball clicks and
308 no-ball frames. All 2,159 came from **one person, one pass, with no second
pass and no second labeller**, so the reliability of the ground truth itself has
never been measured. There is currently no way to separate "the model got worse"
from "the labels drifted" when a future figure looks surprising.

This is the cheap version of the fix: re-label a random sample of ALREADY-labelled
frames, blind, and compare the two passes. It needs no second person.

WHAT IT MEASURES, precisely
---------------------------
Not accuracy — there is nothing more true than a human click to compare against
here. It measures **self-consistency**, which is a CEILING on accuracy: if the
same person disagrees with themselves 8% of the time, no model result inside 8%
is distinguishable from labelling noise. That is the error bar this project has
been quoting every figure without.

Three outputs, meaning different things:
  - CLASS agreement   ball / no-ball / unsure decided the same way both times.
  - POSITION spread   for frames both passes called "ball", the pixel distance
                      between the two clicks. Compare against the eval radius:
                      hit@10px is not meaningful if the labeller's own two clicks
                      routinely land 12 px apart.
  - FLIP DIRECTION    ball->noball is a miss; noball->ball is a false label. They
                      are different problems and are reported separately.

HOW IT STAYS HONEST
-------------------
The second pass must be blind. This tool writes a manifest of sampled frames
ONLY — it never copies pass 1's answers anywhere the labelling UI can show them,
and it refuses to score until a separate labels file exists. The sample is seeded,
so the frame choice is reproducible and cannot be quietly re-rolled until it
flatters.

USAGE
-----
  # 1. draw a reproducible blind sample of already-labelled frames
  py tools/relabel_consistency.py plan --n 80 --seed 0

  # 2. label them in the normal UI, which resumes into the pass-2 directory
  py tools/gold_label_server.py --gold-dir data/gold/relabel_pass2

  # 3. score pass 1 against pass 2
  py tools/relabel_consistency.py score --markdown data/output/label_consistency.md
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import _goldset as gs  # noqa: E402

PASS2 = REPO / "data" / "gold" / "relabel_pass2"
EVAL_RADIUS_PX = 10.0          # what eval_gold.py scores at; see docs/LABELLING.md


def _labels(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["labels"]


def _state(lab: dict) -> str:
    """The three-state schema collapsed to one token (docs/LABELLING.md)."""
    if lab.get("unsure"):
        return "unsure"
    if lab.get("ball") is True:
        return "ball"
    if lab.get("ball") is False:
        return "noball"
    return "unlabelled"


def plan(n: int, seed: int) -> None:
    """Draw a reproducible sample of already-labelled frames across all clips."""
    rng = random.Random(seed)
    pool = []
    for name, clip in gs.GOLD.items():
        p = REPO / clip.labels
        if not p.is_file():
            continue
        for f, lab in _labels(p).items():
            if _state(lab) != "unlabelled":
                pool.append((name, int(f)))
    if not pool:
        raise SystemExit("no labelled frames found")
    pool.sort()                      # deterministic order BEFORE shuffling
    rng.shuffle(pool)
    sample = sorted(pool[:n])

    PASS2.mkdir(parents=True, exist_ok=True)
    by_clip: dict[str, list[int]] = {}
    for name, f in sample:
        by_clip.setdefault(name, []).append(f)

    for name, frames in by_clip.items():
        man = REPO / "data" / "gold" / f"{name}.manifest.json"
        src = json.loads(man.read_text(encoding="utf-8"))
        want = set(frames)
        out = dict(src)
        out["frames"] = [r for r in src["frames"] if r["frame"] in want]
        out["relabel_pass"] = {"of": name, "seed": seed, "n": len(out["frames"]),
                               "why": "P0-2 self-consistency, blind re-label"}
        (PASS2 / f"{name}.manifest.json").write_text(
            json.dumps(out, indent=1), encoding="utf-8")

    total = sum(len(v) for v in by_clip.values())
    print(f"sampled {total} frames across {len(by_clip)} clips (seed {seed})")
    for name, frames in sorted(by_clip.items()):
        print(f"  {name:<24} {len(frames)}")
    rel = PASS2.relative_to(REPO).as_posix()
    print(f"\nmanifests -> {rel}")
    print("Label them BLIND - do not open the pass-1 labels first:")
    print(f"  py tools/gold_label_server.py --gold-dir {rel}")


def score(markdown: str | None) -> None:
    if not PASS2.exists():
        raise SystemExit("no pass-2 directory; run `plan` first")
    pos_err: list[float] = []
    agree = disagree = 0
    flips: dict[str, int] = {}

    for name, clip in gs.GOLD.items():
        p2 = PASS2 / f"{name}.labels.json"
        p1 = REPO / clip.labels
        if not (p2.is_file() and p1.is_file()):
            continue
        a, b = _labels(p1), _labels(p2)
        for f, lab2 in b.items():
            s2 = _state(lab2)
            if s2 == "unlabelled" or f not in a:
                continue
            s1 = _state(a[f])
            if s1 == "unlabelled":
                continue
            if s1 == s2:
                agree += 1
                if s1 == "ball":
                    pos_err.append(math.dist((a[f]["x"], a[f]["y"]),
                                             (lab2["x"], lab2["y"])))
            else:
                disagree += 1
                key = f"{s1}->{s2}"
                flips[key] = flips.get(key, 0) + 1

    n = agree + disagree
    if n == 0:
        raise SystemExit("nothing scored yet - label the pass-2 manifests first")

    pos_err.sort()

    def q(k: float) -> float:
        return pos_err[min(len(pos_err) - 1, int(k * len(pos_err)))]

    lines = [
        "# Gold-label self-consistency (review finding P0-2)",
        "",
        f"**n = {n}** re-labelled frames | **Tool:** `tools/relabel_consistency.py`",
        "",
        "**Measured against:** the SAME labeller's first pass, blind. This is "
        "self-consistency, NOT accuracy - there is nothing more true than a human "
        "click to compare against here. Read it as a CEILING: a model difference "
        "smaller than this noise is not distinguishable from labelling drift.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Class agreement | **{100.0 * agree / n:.1f}%** ({agree}/{n}) |",
        f"| Class disagreement | {100.0 * disagree / n:.1f}% ({disagree}/{n}) |",
    ]
    if pos_err:
        within = 100.0 * sum(1 for d in pos_err if d <= EVAL_RADIUS_PX) / len(pos_err)
        lines += [
            f"| Click distance, median | **{q(0.5):.1f} px** |",
            f"| Click distance, p90 | {q(0.9):.1f} px |",
            f"| Click distance, max | {pos_err[-1]:.1f} px |",
            f"| Both clicks within the eval radius ({EVAL_RADIUS_PX:g} px) | "
            f"{within:.1f}% |",
        ]
    if flips:
        lines += ["", "**Disagreements by direction** - not interchangeable: "
                  "`ball->noball` is a missed ball, `noball->ball` is a false "
                  "label, and they damage different metrics.", "",
                  "| Flip | n |", "|---|---|"]
        lines += [f"| `{k}` | {v} |" for k, v in sorted(flips.items())]
    lines += [
        "", "## How to read this", "",
        f"- If click distance p90 approaches the {EVAL_RADIUS_PX:g} px eval "
        "radius, every hit@10px figure in docs/STATE.md carries that much slack "
        "and should be quoted with it.",
        "- If class agreement is below ~95%, note the no-ball population is only "
        "308 frames pooled, so a handful of flips moves a false-fire rate "
        "visibly.",
        "- A high number here does NOT mean the labels are correct. It means they "
        "are repeatable. Trap T12 already records that agreement can rise while "
        "truth does not.",
    ]

    out = "\n".join(lines) + "\n"
    print(out)
    if markdown:
        Path(markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(markdown).write_text(out, encoding="utf-8")
        print(f"wrote {markdown}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="draw a reproducible blind sample")
    p.add_argument("--n", type=int, default=80)
    p.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("score", help="compare pass 2 against pass 1")
    s.add_argument("--markdown", default=None)
    args = ap.parse_args()
    if args.cmd == "plan":
        plan(args.n, args.seed)
    else:
        score(args.markdown)


if __name__ == "__main__":
    main()
