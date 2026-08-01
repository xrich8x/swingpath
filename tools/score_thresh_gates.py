"""score_thresh_gates.py — apply Session F's pre-registered decision rule to a
set of chain-ladder runs.

The gates were fixed BEFORE any arm was measured, and their order is fixed too.
This script exists so that ordering is executed by code rather than by whoever
is reading the table, which is how a recall regression gets rationalised away.

  backend/.venv/Scripts/python.exe tools/score_thresh_gates.py \\
      --baseline data/output/f_stbase_*.json \\
      --arm 0.6 data/output/f_st06_*.json \\
      --arm 0.7 data/output/f_st07_*.json

GATE 0  comparability   - same clips, same frame_step, same weights.
GATE 1  recall safety   - HARD. Pooled FULL-row recall must not fall more than
                          1.0 pt, and far_geo not more than 2.0 pt on ANY single
                          clip. E6 bought that recall; Session F may not spend
                          it. A failure here kills the arm regardless of
                          everything else.
GATE 2  the pick        - ghost-ball `fires_real` strictly DOWN on >=2 of 3
                          clips and up on none. (The event-audit term is applied
                          separately, on yt_rally2 only, by event_audit.py.)
GATE 3  tie-break only  - total fires, false-fire.

Pooled recall is weighted by each clip's labelled-ball count, not averaged over
clips: an unweighted mean would let the 175-label clip outvote the 258-label one.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

FULL = "+ kalman smooth (FULL)"


def load(paths):
    """{clip: FULL-row} plus the run metadata needed for the comparability gate."""
    rows, meta = {}, {}
    for p in sorted(set(sum((glob.glob(x) for x in paths), []))):
        blob = json.loads(Path(p).read_text(encoding="utf-8"))
        clip = blob["clip"]
        full = next((r for r in blob["rows"] if r["stage"] == FULL), None)
        if full is None:
            continue
        rows[clip] = full
        meta[clip] = {"frame_step": blob.get("frame_step"),
                      "weights": tuple(blob.get("weights", [])),
                      "n_ball": full["n_scored"], "score_thresh": blob.get("score_thresh")}
    return rows, meta


def pooled_recall(rows):
    num = sum(r["recall"] / 100 * r["n_scored"] for r in rows.values())
    den = sum(r["n_scored"] for r in rows.values())
    return 100 * num / max(den, 1), den


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baseline", nargs="+", required=True)
    ap.add_argument("--arm", nargs="+", action="append", required=True,
                    metavar=("NAME PATH"),
                    help="repeatable: a label followed by one or more json paths")
    ap.add_argument("--max-recall-drop", type=float, default=1.0)
    ap.add_argument("--max-geo-drop", type=float, default=2.0)
    args = ap.parse_args()

    base, bmeta = load(args.baseline)
    bpool, bn = pooled_recall(base)
    print(f"BASELINE  clips={sorted(base)}  pooled recall {bpool:.1f}% "
          f"over {bn} labelled ball frames")
    for c in sorted(base):
        r = base[c]
        print(f"    {c:<12} recall {r['recall']:>5.1f}%  far_geo "
              f"{str(r['far_geo']):>5}  ff {r['false_fire']:>5.1f}%  "
              f"fires {r['fires']} ({r['fires_real']} solid, "
              f"{r['fires_coasted']} faded)")

    for entry in args.arm:
        name, paths = entry[0], entry[1:]
        arm, ameta = load(paths)
        print(f"\nARM {name}")
        for c in sorted(arm):
            r = arm[c]
            print(f"    {c:<12} recall {r['recall']:>5.1f}%  far_geo "
                  f"{str(r['far_geo']):>5}  ff {r['false_fire']:>5.1f}%  "
                  f"fires {r['fires']} ({r['fires_real']} solid, "
                  f"{r['fires_coasted']} faded)")

        # GATE 0 - comparability
        g0 = []
        if set(arm) != set(base):
            g0.append(f"clip sets differ: {sorted(arm)} vs {sorted(base)}")
        for c in sorted(set(arm) & set(base)):
            if ameta[c]["frame_step"] != bmeta[c]["frame_step"]:
                g0.append(f"{c}: frame_step {ameta[c]['frame_step']} vs "
                          f"{bmeta[c]['frame_step']}")
            if ameta[c]["weights"] != bmeta[c]["weights"]:
                g0.append(f"{c}: weights differ")
            if ameta[c]["n_ball"] != bmeta[c]["n_ball"]:
                g0.append(f"{c}: scoreable ball frames {ameta[c]['n_ball']} vs "
                          f"{bmeta[c]['n_ball']}")
        print(f"  GATE 0 comparability: {'PASS' if not g0 else 'VOID - ' + '; '.join(g0)}")
        if g0:
            continue

        # GATE 1 - recall safety, HARD
        apool, _ = pooled_recall(arm)
        drop = bpool - apool
        fails = []
        if drop > args.max_recall_drop:
            fails.append(f"pooled recall {bpool:.1f} -> {apool:.1f} "
                         f"(-{drop:.1f} pt, limit {args.max_recall_drop})")
        for c in sorted(arm):
            bg, ag = base[c]["far_geo"], arm[c]["far_geo"]
            if bg is not None and ag is not None and bg - ag > args.max_geo_drop:
                fails.append(f"{c} far_geo {bg} -> {ag} (-{bg-ag:.1f} pt, "
                             f"limit {args.max_geo_drop})")
        print(f"  GATE 1 recall safety: pooled {bpool:.1f}% -> {apool:.1f}% "
              f"({apool-bpool:+.1f} pt)")
        if fails:
            print(f"    FAIL - {'; '.join(fails)}")
            print("    Arm killed. E6 bought that recall; this gate is hard.")
            continue
        print("    PASS")

        # GATE 2 - the pick
        down = [c for c in arm if arm[c]["fires_real"] < base[c]["fires_real"]]
        up = [c for c in arm if arm[c]["fires_real"] > base[c]["fires_real"]]
        ok = len(down) >= 2 and not up
        print(f"  GATE 2 ghost-ball fires_real: down on {len(down)} "
              f"({', '.join(sorted(down)) or 'none'}), up on {len(up)} "
              f"({', '.join(sorted(up)) or 'none'}) -> "
              f"{'PASS' if ok else 'FAIL'}")
        for c in sorted(arm):
            print(f"      {c:<12} {base[c]['fires_real']} -> {arm[c]['fires_real']} "
                  f"solid   ({base[c]['fires']} -> {arm[c]['fires']} total)")
        print("  GATE 3 tie-break: total fires "
              f"{sum(base[c]['fires'] for c in base)} -> "
              f"{sum(arm[c]['fires'] for c in arm)}")
        print("  NOTE the event-audit half of Gate 2 (phantom_ball_under_hit must "
              "not increase) is applied separately by tools/event_audit.py, on "
              "yt_rally2 only.")


if __name__ == "__main__":
    main()
