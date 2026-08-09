"""gate_verdict.py — pool eval_model_filters runs and apply the ghost-ball gate.

WHY THIS EXISTS
---------------
The standing gate is stated per-candidate and POOLED across the calibrated gold
clips: solid ghosts must fall, recall must not drop more than 2 pts, far_geo must
not drop more than 2 pts. Every session so far has pooled it by hand from printed
tables, and Session I found the two failure modes that invites — a resume list that
omitted one of the three clips, and per-clip numbers that disagree in SIGN being
summarised as if they agreed.

Pooling is a weighted question, not an average of percentages: yt_rally2 contributes
26 no-ball frames and yt_match40 24, so a mean of the three false-fire percentages
is not the false-fire rate. This sums the numerators and denominators.

WHAT IT ALSO REPORTS, AND WHY IT MATTERS MORE THAN THE VERDICT
--------------------------------------------------------------
The deciding metric is a count of ~10 out of ~74 no-ball frames. At that size the
sampling noise is +/-2.9 frames, so the gate can only resolve near-elimination:
halving the ghost rate needs ~312 no-ball frames to detect at 80% power, and a 30%
cut needs ~970. "Solid ghosts did not fall" therefore does NOT establish "the
intervention does nothing" — it establishes "no intervention has nearly eliminated
them, and smaller effects are below the resolution of this test set."

So the tool prints the required-n alongside the verdict, and — when the runs carry
`fire_frames` — whether the arms fire on the SAME frames. A stable set of hard
confusers and a shifting one read identically as a count, and they call for
opposite next moves: go and look at those frames, versus go and label more.

    py tools/gate_verdict.py data/output/session_i_ab/filters_*.json \
        --baseline ballnet_i_base.pt --candidate ballnet_i_conf.pt
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

STAGE = "+ kalman smooth (FULL)"     # the shipped chain; the row the product sees
Z_A, Z_B = 1.959964, 0.8416212       # alpha .05 two-sided, power .80


def n_per_arm(p1: float, p2: float) -> float:
    """Two-proportion sample size. Unpaired, so it OVERSTATES what a paired
    (McNemar) comparison on identical frames needs — the honest reading is an
    order of magnitude, not a target to hit exactly."""
    if p1 == p2:
        return float("inf")
    pb = (p1 + p2) / 2.0
    a = Z_A * math.sqrt(2 * pb * (1 - pb))
    b = Z_B * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return (a + b) ** 2 / (p1 - p2) ** 2


def load(paths):
    """{weights_name: {clip: the FULL-chain row}}."""
    runs: dict[str, dict[str, dict]] = {}
    for p in paths:
        doc = json.loads(Path(p).read_text(encoding="utf-8"))
        clip = doc.get("clip") or Path(p).stem.replace("filters_", "")
        for row in doc.get("rows", []):
            if row.get("stage") != STAGE:
                continue
            name = Path(row.get("weights", "?")).name
            runs.setdefault(name, {})[row.get("clip", clip)] = row
    return runs


def pool(by_clip: dict[str, dict]) -> dict:
    """Sum numerators and denominators. A mean of percentages would weight a
    26-frame clip the same as a 53-frame one."""
    nb = sum(r["n_noball"] for r in by_clip.values())
    nsc = sum(r["n_scored"] for r in by_clip.values())
    solid = sum(r["fires_real"] or 0 for r in by_clip.values())
    fires = sum(r["fires"] for r in by_clip.values())
    hits = sum(round(r["recall"] / 100.0 * r["n_scored"]) for r in by_clip.values())
    geos = [r["far_geo"] for r in by_clip.values() if r.get("far_geo") is not None]
    return {"n_noball": nb, "n_scored": nsc, "solid": solid, "fires": fires,
            "recall": 100.0 * hits / max(nsc, 1),
            "far_geo_worst_clip": min(geos) if geos else None,
            "far_geo_mean": sum(geos) / len(geos) if geos else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", help="filters_<clip>.json from eval_model_filters")
    ap.add_argument("--baseline", required=True, help="weights filename of the control arm")
    ap.add_argument("--candidate", required=True, help="weights filename of the treatment arm")
    args = ap.parse_args()

    runs = load(args.runs)
    for want in (args.baseline, args.candidate):
        if want not in runs:
            raise SystemExit(f"no rows for {want!r}; found {sorted(runs)}")

    base, cand = runs[args.baseline], runs[args.candidate]
    shared = sorted(set(base) & set(cand))
    if not shared:
        raise SystemExit("the two arms share no clips")
    missing = sorted((set(base) | set(cand)) - set(shared))
    if missing:
        print(f"WARNING scored on only one arm, excluded from the pool: {missing}")

    print(f"clips pooled: {', '.join(shared)}\n")
    print(f"  {'clip':<14}{'solid base':>11}{'solid cand':>11}{'d':>5}"
          f"{'recall b':>10}{'recall c':>10}")
    signs = set()
    for c in shared:
        b, k = base[c], cand[c]
        d = (k["fires_real"] or 0) - (b["fires_real"] or 0)
        signs.add((d > 0) - (d < 0))
        print(f"  {c:<14}{b['fires_real']:>11}{k['fires_real']:>11}{d:>+5}"
              f"{b['recall']:>9.1f}%{k['recall']:>9.1f}%")

    pb, pc = pool({c: base[c] for c in shared}), pool({c: cand[c] for c in shared})
    print(f"\n  POOLED        {pb['solid']:>11}{pc['solid']:>11}"
          f"{pc['solid'] - pb['solid']:>+5}{pb['recall']:>9.1f}%{pc['recall']:>9.1f}%"
          f"   ({pb['n_noball']} no-ball, {pb['n_scored']} ball frames)")

    if len(signs - {0}) > 1:
        print("\n  !! the clips DISAGREE IN SIGN - the pooled number is an average of "
              "opposite effects,\n     which is the signature of noise rather than a "
              "mechanism. Read the per-clip rows.")

    d_solid = pc["solid"] - pb["solid"]
    d_rec = pc["recall"] - pb["recall"]
    d_geo = (None if pb["far_geo_worst_clip"] is None else
             pc["far_geo_worst_clip"] - pb["far_geo_worst_clip"])
    checks = [("solid ghosts FALL", d_solid < 0, f"{d_solid:+d}"),
              ("recall drop <= 2 pts", d_rec >= -2.0, f"{d_rec:+.1f} pts"),
              ("far_geo drop <= 2 pts (worst clip)",
               d_geo is None or d_geo >= -2.0,
               "n/a" if d_geo is None else f"{d_geo:+.1f} pts")]
    print("\n  pre-registered gate")
    for label, ok, val in checks:
        print(f"    [{'PASS' if ok else 'FAIL'}] {label:<38} {val}")
    print(f"\n  VERDICT: {'PASS' if all(c[1] for c in checks) else 'FAIL'}")

    # Resolution. Without this a null result reads as "nothing there" when it may
    # only mean "below what 74 frames can see".
    nb, p1 = pb["n_noball"], pb["solid"] / max(pb["n_noball"], 1)
    print(f"\n  RESOLUTION of this test set - {nb} no-ball frames, "
          f"solid-ghost rate {100*p1:.1f}%")
    print(f"    sd of the count by sampling alone: "
          f"{math.sqrt(nb * p1 * (1 - p1)):.1f} frames")
    for label, p2 in (("near-eliminate", 0.5 / nb), ("halve", p1 / 2),
                      ("cut by 30%", p1 * 0.7)):
        n = n_per_arm(p1, p2)
        verdict = "detectable" if n <= nb else f"needs {n:.0f} ({n/nb:.1f}x more)"
        print(f"    {label:<16} {verdict}")

    # Identity, not just count — the question a tally cannot answer.
    fb = {c: base[c].get("fire_frames_solid") for c in shared}
    fc = {c: cand[c].get("fire_frames_solid") for c in shared}
    if all(v is not None for v in (*fb.values(), *fc.values())):
        sb = {(c, f) for c, v in fb.items() for f in v}
        sc = {(c, f) for c, v in fc.items() for f in v}
        both = len(sb & sc)
        print(f"\n  SAME FRAMES?  {both} of {len(sb | sc)} solid-ghost frames fire on "
              f"BOTH arms ({100*both/max(len(sb | sc),1):.0f}% overlap)")
        print("    high overlap => a stable set of hard confusers; go and LOOK at them.")
        print("    low overlap  => the count is stable but the frames are not; the "
              "effect is below resolution and the fix is more labelled no-ball frames.")
    else:
        print("\n  (re-run eval_model_filters to record fire_frames_solid for the "
              "same-frames check)")


if __name__ == "__main__":
    main()
