"""hud_compare.py — score our per-shot speeds against SwingVision's HUD (E3).

Matches each shot in one of our match.json files to the HUD reading that
followed it (the panel appears shortly after the stroke) and reports the deltas,
plus the coverage gap — strokes SwingVision registered that our events layer
never produced a shot for. That gap is a result, not a nuisance: it is the
denominator any accuracy claim has to carry.

Reference caveat (also stamped into the output): the HUD is SwingVision's own
single-camera estimate, not radar. Agreement means "same world", not "correct".

  cd backend
  .venv\\Scripts\\python.exe ..\\tools\\hud_compare.py \\
      --match ..\\data\\output\\fps\\rally2_launch.json \\
      --hud ..\\data\\gold\\hud_yt_rally2.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MPH_TO_KMH = 1.609344


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--match", required=True, help="our match.json")
    ap.add_argument("--hud", required=True, help="hud_ocr.py read output")
    ap.add_argument("--lag", type=float, nargs=2, default=(0.0, 2.0),
                    metavar=("MIN", "MAX"),
                    help="panel appears MIN..MAX s after the stroke it describes")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    match = json.loads(Path(args.match).read_text(encoding="utf-8"))
    hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))
    shots = match["shots"]
    readings = hud["shots"]

    lag_lo, lag_hi = args.lag
    pairs, used = [], set()
    for s in shots:
        t = s["t_hit_s"]
        best, best_lag = None, None
        for i, r in enumerate(readings):
            if i in used:
                continue
            lag = r["t_start_s"] - t
            if lag_lo <= lag <= lag_hi and (best is None or lag < best_lag):
                best, best_lag = i, lag
        if best is not None:
            used.add(best)
            pairs.append((s, readings[best], best_lag))

    print(f"ours: {len(shots)} shots   HUD: {len(readings)} readings   "
          f"matched: {len(pairs)}")
    print(f"coverage: our events layer produced shots for "
          f"{len(pairs)}/{len(readings)} strokes SwingVision registered "
          f"({100 * len(pairs) / max(len(readings), 1):.0f}%)\n")

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
    unmatched = [r for i, r in enumerate(readings) if i not in used]
    if unmatched:
        print(f"unmatched HUD strokes (we produced no shot): "
              f"{', '.join(str(r['mph']) + 'MPH@' + str(r['t_start_s']) for r in unmatched[:8])}"
              + (" ..." if len(unmatched) > 8 else ""))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "match": Path(args.match).name, "hud": Path(args.hud).name,
            "reference": hud.get("source"),
            "n_ours": len(shots), "n_hud": len(readings), "n_matched": len(pairs),
            "mae_confident_pct": (round(sum(deltas_conf) / len(deltas_conf), 1)
                                  if deltas_conf else None),
            "pairs": rows}, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
