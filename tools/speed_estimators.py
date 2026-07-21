"""speed_estimators.py — score competing shot-speed methods against the HUD.

The shipping method integrates path length between consecutive frames. That is
the wrong shape of estimator for a noisy track: every wobble ADDS length and
none cancels, so error accumulates instead of averaging out. Measured on
yt_rally2: a rally whose endpoints are 4.1 m apart integrates to 559.5 m.

The user's proposal — "the court has known dimensions, so time the ball from
point A to point B" — fixes exactly that, because only the two endpoints matter.
It also dodges the depth ambiguity that sank the physics fit (E1), on one
condition: both endpoints must be ON the court plane, where z=0 is a fact rather
than an assumption. A bounce satisfies that. A racquet contact does not.

So this compares, per shot, against SwingVision's reading for the same stroke:

  path      total path length / elapsed         (what ships today)
  chord     straight line hit->bounce / elapsed  (jitter-immune, but the hit end
                                                  is airborne and the flight is
                                                  curved -> reads low)
  b2b       bounce -> next bounce / elapsed      (both ends genuinely on the
                                                  plane; measures rally pace)
  striker   striker's court position -> bounce   (plane-exact both ends: pose
                                                  puts the player on the floor)

No estimator here is "the answer" until the numbers say so.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\speed_estimators.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

from hit_coverage_probe import build_track                    # noqa: E402
from swingvision import events                                # noqa: E402

MS_TO_KMH = 3.6


def path_len(track, a, b):
    return sum(math.dist(track[i][1:], track[i + 1][1:]) for i in range(a, b))


def chord(track, a, b):
    return math.dist(track[a][1:], track[b][1:])


def player_xy(court_list, frame, radius=6):
    """Striker's court position near `frame`, tolerant of pose dropouts."""
    n = len(court_list)
    for d in range(radius + 1):
        for f in (frame - d, frame + d):
            if 0 <= f < n and court_list[f] is not None:
                return court_list[f]
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_show.perception.json"))
    ap.add_argument("--keypoints", default=str(REPO / "data/yt_rally2_pts.json"))
    ap.add_argument("--hud", default=str(REPO / "data/gold/hud_yt_rally2.json"))
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--lag", type=float, nargs=2, default=(0.1, 1.6))
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    track, has_data = build_track(args.cache, args.keypoints, args.fps)
    cache = json.loads(Path(args.cache).read_text(encoding="utf-8"))
    near_c, far_c = cache.get("near_court") or [], cache.get("far_court") or []
    hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))["shots"]

    hits = sorted(events.detect_hits(track, angle_thresh_deg=70, min_gap_s=0.3))
    bounces = sorted(events.detect_bounces(track, min_speed_drop=0.55))
    bset = sorted(b for b in bounces if all(abs(b - h) > 3 for h in hits))

    # One arc per hit: hit -> first bounce after it, before the next hit.
    arcs = []
    for k, h in enumerate(hits):
        nxt = hits[k + 1] if k + 1 < len(hits) else len(track) - 1
        cand = [b for b in bset if h + 4 <= b <= nxt]
        if cand:
            arcs.append((h, cand[0]))

    rows = []
    for i, (h, b) in enumerate(arcs):
        dt = track[b][0] - track[h][0]
        if dt <= 0:
            continue
        est = {"path": path_len(track, h, b) / dt * MS_TO_KMH,
               "chord": chord(track, h, b) / dt * MS_TO_KMH}
        # bounce -> next bounce (rally pace between two plane-exact points)
        nb = next((b2 for (h2, b2) in arcs[i + 1:] if b2 > b), None)
        est["b2b"] = (math.dist(track[b][1:], track[nb][1:]) /
                      (track[nb][0] - track[b][0]) * MS_TO_KMH) if nb else None
        # striker's feet -> bounce
        ball = np.array(track[h][1:])
        best = None
        for cl in (near_c, far_c):
            p = player_xy(cl, h)
            if p is None:
                continue
            d = float(np.hypot(ball[0] - p[0], ball[1] - p[1]))
            if best is None or d < best[1]:
                best = (p, d)
        est["striker"] = (math.dist(best[0], track[b][1:]) / dt * MS_TO_KMH
                          if best else None)
        rows.append({"t_hit_s": round(track[h][0], 2), "dt": round(dt, 2), **est})

    # Match each HUD stroke to the arc that precedes it.
    lo, hi = args.lag
    used, pairs = set(), []
    for r in hud:
        cands = [(i, x) for i, x in enumerate(rows)
                 if i not in used and lo <= r["t_start_s"] - x["t_hit_s"] <= hi]
        if cands:
            i, x = min(cands, key=lambda ix: r["t_start_s"] - ix[1]["t_hit_s"])
            used.add(i)
            pairs.append((x, r))

    methods = ["path", "chord", "b2b", "striker"]
    print(f"{len(arcs)} arcs, {len(pairs)}/{len(hud)} matched to a HUD stroke\n")
    hdr = f"{'t_hit':>6} {'HUD':>6} " + "".join(f"{m:>18}" for m in methods)
    print(hdr); print("-" * len(hdr))
    errs = {m: [] for m in methods}
    for x, r in pairs:
        line = f"{x['t_hit_s']:>6.2f} {r['kmh']:>6.1f} "
        for m in methods:
            v = x[m]
            if v is None:
                line += f"{'—':>18}"
            else:
                d = 100 * (v - r["kmh"]) / r["kmh"]
                errs[m].append(d)
                line += f"{v:>10.0f} ({d:>+4.0f}%)"
        print(line)

    print(f"\n{'method':<10}{'n':>4}{'MAE':>8}{'median err':>12}{'bias':>9}"
          f"{'within 25%':>12}")
    print("-" * 55)
    summary = {}
    for m in methods:
        e = errs[m]
        if not e:
            continue
        mae = float(np.mean(np.abs(e)))
        summary[m] = {"n": len(e), "mae_pct": round(mae, 1),
                      "median_abs_pct": round(float(np.median(np.abs(e))), 1),
                      "bias_pct": round(float(np.mean(e)), 1),
                      "within25": int(sum(abs(x) <= 25 for x in e))}
        print(f"{m:<10}{len(e):>4}{mae:>7.0f}%{np.median(np.abs(e)):>11.0f}%"
              f"{np.mean(e):>+8.0f}%{sum(abs(x) <= 25 for x in e):>8}/{len(e)}")

    print("\nbias reading: a negative bias means the estimator reads LOW, which a "
          "straight-line\nmeasure must do — the ball's real path curves. A "
          "consistent bias is CORRECTABLE;\nscatter (high MAE with ~zero bias) is not.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"cache": Path(args.cache).name, "fps": args.fps,
             "reference": "SwingVision HUD (single-camera estimate, not radar)",
             "summary": summary, "rows": rows}, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
