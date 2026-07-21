"""hit_gap_probe.py — pick the hit-detector threshold from data, not intuition (E3d).

Uses the HUD as ground truth for WHEN strokes happened, then asks what the
ball-to-player gap actually looks like at those moments versus everywhere else.
That separation (or lack of it) is what decides whether proximity can work at
all — and if it can, where the threshold belongs.

Then it sweeps the threshold and reports coverage vs extras against the HUD, so
the shipped value is the measured optimum rather than a guess.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\hit_gap_probe.py \\
      --cache ..\\data\\output\\fps\\rally2_e3d.perception.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

from hit_coverage_probe import build_track, coverage       # noqa: E402
from swingvision import events                             # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_e3d.perception.json"))
    ap.add_argument("--keypoints", default=str(REPO / "data/yt_rally2_pts.json"))
    ap.add_argument("--hud", default=str(REPO / "data/gold/hud_yt_rally2.json"))
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--lag", type=float, nargs=2, default=(0.1, 1.6))
    args = ap.parse_args()

    cache = json.loads(Path(args.cache).read_text(encoding="utf-8"))
    track, _ = build_track(args.cache, args.keypoints, args.fps)
    n = len(track)
    gaps = events.ball_player_gap(cache["ball_px"], cache.get("near_kpts") or [],
                                  cache.get("far_kpts") or [], n)
    hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))["shots"]

    print(f"{n} frames; gap known on {int(np.isfinite(gaps).sum())} "
          f"({100*np.isfinite(gaps).mean():.0f}%)")

    # Windows where a stroke really happened, per the HUD's lag band.
    lo, hi = args.lag
    stroke = np.zeros(n, bool)
    for r in hud:
        a = int(round((r["t_start_s"] - hi) * args.fps))
        b = int(round((r["t_start_s"] - lo) * args.fps))
        stroke[max(0, a):min(n, b + 1)] = True

    on = gaps[stroke & np.isfinite(gaps)]
    off = gaps[~stroke & np.isfinite(gaps)]
    print(f"\ngap in player-heights (lower = ball closer to a player):")
    print(f"{'':14}{'n':>6}{'5th':>8}{'25th':>8}{'median':>8}")
    for name, v in (("during strokes", on), ("elsewhere", off)):
        if len(v):
            print(f"{name:<14}{len(v):>6}{np.percentile(v,5):>8.2f}"
                  f"{np.percentile(v,25):>8.2f}{np.median(v):>8.2f}")
    if len(on) and len(off):
        print(f"\nseparation: stroke-window 25th pct {np.percentile(on,25):.2f} vs "
              f"elsewhere 25th pct {np.percentile(off,25):.2f}")

    print(f"\nthreshold sweep (HUD strokes = {len(hud)}):")
    hdr = f"{'max_gap':>8}{'min_turn':>10}{'hits':>7}{'covered':>10}{'extras':>8}"
    print(hdr); print("-" * len(hdr))
    best = None
    for max_gap in (0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0):
        for min_turn in (0.0, 20.0, 40.0):
            idx = events.detect_hits_by_gap(gaps, track, max_gap=max_gap,
                                            min_turn_deg=min_turn)
            times = [track[k][0] for k in idx]
            cov, extras = coverage(times, hud, lag=tuple(args.lag))
            print(f"{max_gap:>8.1f}{min_turn:>10.0f}{len(idx):>7}"
                  f"{cov:>7}/{len(hud):<3}{extras:>8}")
            # Prefer coverage, then fewest extras.
            key = (-cov, extras)
            if best is None or key < best[0]:
                best = (key, max_gap, min_turn, cov, extras)
    _, mg, mt, cov, extras = best
    print(f"\nbest: max_gap={mg} min_turn={mt}  -> {cov}/{len(hud)} covered, "
          f"{extras} extras")
    print("for scale: the shipping angle-only detector gets 17/17 with 34 extras.")


if __name__ == "__main__":
    main()
