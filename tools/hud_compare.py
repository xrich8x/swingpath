"""hud_compare.py — score our per-shot speeds against SwingVision's HUD (E3).

Matches each shot in one of our match.json files to the HUD reading that
followed it (the panel appears shortly after the stroke) and reports the deltas,
plus the coverage gap in BOTH directions: strokes SwingVision registered that our
events layer never produced a shot for, and shots we produced that no reading
pairs with. Both gaps are results, not nuisances: they are the denominator any
accuracy claim has to carry.

Reference caveat (also stamped into the output): the HUD is SwingVision's own
single-camera estimate, not radar. Agreement means "same world", not "correct".

  cd backend
  .venv\\Scripts\\python.exe ..\\tools\\hud_compare.py \\
      --match ..\\data\\output\\fps\\rally2_launch.json \\
      --hud ..\\data\\gold\\hud_yt_rally2.json

WHAT `surplus_shots` IS AND IS NOT (Session F step 1)
----------------------------------------------------
The session brief asked for "phantom speed — a confident speed on a shot the HUD
has no stroke for". MEASURED: that metric is identically zero and has been
dropped. The 17 readings in data/gold/hud_yt_rally2.json tile source frames
62..2214 with a constant 2-frame gap (the step=2 decimation) — the HUD is a
PERSISTENT PANEL showing the last stroke's speed until the next replaces it, not
a sparse event list. There is no instant at which "the HUD has no reading", so
every shot we produce falls inside some panel.

What survives is only the accounting identity of a 1-to-1 assignment:
`surplus_shots = n_ours - n_matched`. It is reported here as TIE-BREAK evidence
only, never as a pick criterion, for three reasons: n is ~14, the HUD misses
strokes on its own terms (so an unmatched pair is a JOINT failure this tool
cannot attribute), and `speed_confident` derives from the same ball_px mask that
a false-fire change modifies, making the confident subset partially self-graded.
tools/event_audit.py adjudicates against human gold clicks instead, and that is
the number to pick on.

THE MATCHER WAS WRONG, AND FIXING IT MOVES THE COVERAGE NUMBER
--------------------------------------------------------------
This tool used to match greedily forward with a hard `lag >= 0.0` floor. That
floor is not physical — our own `t_hit_s` carries a +/-2-frame error of its own,
so a panel can legitimately be timestamped slightly BEFORE the hit we assign it
to. MEASURED on data/output/rally2_seg10.json: our shot at t=14.73 could not
claim the 14.60 s panel (lag -0.13 s), so it took the 16.20 s panel instead (lag
+1.47 s, versus a typical observed 0.5-0.9 s), which orphaned our real shot at
t=15.73 — a shot the human gold clicks independently exonerate (a decided
`ball: true` label 2 frames away). One 0.13 s timing error cascaded into two
wrong verdicts, and inflated `surplus_shots` with a shot that was never a
phantom.

Replaced with an order-preserving (monotonic) assignment that maximises matched
pairs, and a default window of -0.25..2.0 s. CONSEQUENCE: coverage on
rally2_seg10 moves 11/17 -> the number this tool now prints. Every coverage
figure quoted before this change was computed by the old matcher and is NOT
comparable across the fix — re-measure, do not compare.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

MPH_TO_KMH = 1.609344


def match_monotonic(shots, readings, lag_lo, lag_hi, target_lag=None):
    """Order-preserving assignment of shots to HUD readings.

    Both sequences are time-ordered and the panel order follows the stroke order,
    so a crossing match (a later stroke claiming an earlier stroke's panel) is
    physically impossible; forbidding it is what stops one mis-timed pairing from
    cascading down the rest of the rally, which is exactly how the previous greedy
    matcher produced a phantom.

    Maximises the number of pairs first, then minimises total |lag - target_lag|.
    With `target_lag=None` the secondary objective is total lag, i.e. "the panel
    appears as soon as it can" — used for the first pass, whose matched lags then
    supply the median for a second pass. Returns a list of (shot_i, reading_j, lag).
    """
    n, m = len(shots), len(readings)
    # dp[i][j] = (pairs, cost) for shots[i:] against readings[j:]; maximise pairs,
    # then minimise cost. Walk backwards so dp[0][0] is the whole problem.
    dp = [[(0, 0.0)] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best = dp[i + 1][j]                       # drop this shot
            if dp[i][j + 1] > best:                   # drop this reading
                best = dp[i][j + 1]
            lag = readings[j]["t_start_s"] - shots[i]["t_hit_s"]
            if lag_lo <= lag <= lag_hi:
                c = abs(lag) if target_lag is None else abs(lag - target_lag)
                sub = dp[i + 1][j + 1]
                # Tuples compare lexicographically and we want MORE pairs at LESS
                # cost, so negate the cost to keep a single `>` comparison honest.
                cand = (sub[0] + 1, sub[1] - c)
                if cand > best:
                    best = cand
            dp[i][j] = best

    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if dp[i][j] == dp[i + 1][j]:
            i += 1
        elif dp[i][j] == dp[i][j + 1]:
            j += 1
        else:
            pairs.append((i, j, readings[j]["t_start_s"] - shots[i]["t_hit_s"]))
            i += 1
            j += 1
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--match", required=True, help="our match.json")
    ap.add_argument("--hud", required=True, help="hud_ocr.py read output")
    ap.add_argument("--lag", type=float, nargs=2, default=(-0.25, 2.0),
                    metavar=("MIN", "MAX"),
                    help="panel appears MIN..MAX s after the stroke it describes. "
                         "MIN is negative on purpose: our t_hit_s has its own "
                         "+/-2-frame error, and a hard 0.0 floor demonstrably "
                         "orphaned a real shot on rally2_seg10.")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    match = json.loads(Path(args.match).read_text(encoding="utf-8"))
    hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))
    shots = match["shots"]
    readings = hud["shots"]

    lag_lo, lag_hi = args.lag
    # Two passes: the first pins down the cardinality and a median lag, the second
    # re-solves the ties around that median. Setting the target from the data
    # rather than from a guessed constant is the point — the observed lag is a
    # property of SwingVision's rendering, not something this project gets to pick.
    first = match_monotonic(shots, readings, lag_lo, lag_hi)
    med_lag = statistics.median([lag for _, _, lag in first]) if first else None
    idx = match_monotonic(shots, readings, lag_lo, lag_hi, target_lag=med_lag)
    pairs = [(shots[i], readings[j], lag) for i, j, lag in idx]
    matched_shots = {i for i, _, _ in idx}
    matched_readings = {j for _, j, _ in idx}

    surplus = [s for i, s in enumerate(shots) if i not in matched_shots]
    surplus_conf = [s for s in surplus if s.get("speed_confident")]
    unmatched = [r for j, r in enumerate(readings) if j not in matched_readings]

    print(f"ours: {len(shots)} shots   HUD: {len(readings)} readings   "
          f"matched: {len(pairs)}   (matcher: monotonic-dp, "
          f"lag window {lag_lo:+.2f}..{lag_hi:+.2f}s)")
    print(f"coverage: our events layer produced shots for "
          f"{len(pairs)}/{len(readings)} strokes SwingVision registered "
          f"({100 * len(pairs) / max(len(readings), 1):.0f}%)")
    lags = [lag for _, _, lag in pairs]
    if lags:
        print(f"observed lag: min {min(lags):+.2f}s  median {med_lag:+.2f}s  "
              f"max {max(lags):+.2f}s")
    print()

    hdr = (f"{'t_hit':>7} {'type':<9} {'ours km/h':>10} {'src':<8} "
           f"{'HUD km/h':>9} {'delta':>8} {'conf':>5}")
    print(hdr); print("-" * len(hdr))
    rows, deltas_conf = [], []
    for s, r, lag in pairs:
        ours = s["speed_kmh"]
        ref = r["kmh"]
        d = 100.0 * (ours - ref) / ref
        conf = bool(s.get("speed_confident"))
        if conf:
            deltas_conf.append(abs(d))
        rows.append(dict(t_hit_s=s["t_hit_s"], type=s.get("type"),
                         ours_kmh=ours, source=s.get("speed_source"),
                         hud_kmh=ref, hud_mph=r["mph"], delta_pct=round(d, 1),
                         confident=conf, lag_s=round(lag, 2)))
        print(f"{s['t_hit_s']:>7.2f} {s.get('type', '?'):<9} {ours:>10.1f} "
              f"{s.get('speed_source', '?'):<8} {ref:>9.1f} {d:>+7.1f}% "
              f"{'yes' if conf else 'no':>5}")

    print()
    if deltas_conf:
        mae = sum(deltas_conf) / len(deltas_conf)
        print(f"MAE on confident shots: {mae:.1f}%  (n={len(deltas_conf)})")
    else:
        print("MAE on confident shots: no confident matched shots")

    if unmatched:
        print(f"unmatched HUD strokes (we produced no shot): "
              f"{', '.join(str(r['mph']) + 'MPH@' + str(r['t_start_s']) for r in unmatched[:8])}"
              + (" ..." if len(unmatched) > 8 else ""))
    surplus_rows = [dict(t_hit_s=s["t_hit_s"], type=s.get("type"),
                         ours_kmh=s["speed_kmh"], source=s.get("speed_source"),
                         confident=bool(s.get("speed_confident")))
                    for s in surplus]
    if surplus:
        shown = ", ".join(
            f"{s['t_hit_s']:.2f}s {s['speed_kmh']:.0f}km/h"
            + ("*" if s.get("speed_confident") else "")
            for s in surplus[:8])
        print(f"surplus shots (no HUD reading pairs with them): {shown}"
              + (" ..." if len(surplus) > 8 else ""))
        print(f"  {len(surplus)} surplus, {len(surplus_conf)} of them confident "
              f"(* = confident). TIE-BREAK EVIDENCE ONLY - the HUD misses strokes "
              f"too, so an unmatched shot is a joint failure this tool cannot "
              f"attribute. Adjudicate with tools/event_audit.py.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "match": Path(args.match).name, "hud": Path(args.hud).name,
            "reference": hud.get("source"),
            "matcher": "monotonic-dp", "lag_window_s": [lag_lo, lag_hi],
            "lag_stats_s": (None if not lags else
                            {"min": round(min(lags), 2),
                             "median": round(med_lag, 2),
                             "max": round(max(lags), 2)}),
            "n_ours": len(shots), "n_hud": len(readings), "n_matched": len(pairs),
            "n_surplus": len(surplus), "n_surplus_confident": len(surplus_conf),
            "mae_confident_pct": (round(sum(deltas_conf) / len(deltas_conf), 1)
                                  if deltas_conf else None),
            "pairs": rows,
            "surplus": surplus_rows,
            "unmatched_hud": [dict(t_start_s=r["t_start_s"], mph=r["mph"],
                                   kmh=r["kmh"]) for r in unmatched]},
            indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
