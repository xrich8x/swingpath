"""speed_confidence.py — which shots can we actually report? (E3f)

Per-frame recall has a hard ceiling: the detector puts the ball in its top-5
blobs on 77.9% of gold frames, and we are already at 72.5%, so no amount of
tracking work reaches 90%. That makes the useful question a different one —
not "how often do we see the ball" but **"for which shots is the track good
enough to report a number, and how wide must the honest band be?"**

This correlates cheap, track-derived quality signals against the measured error
vs the SwingVision HUD, then calibrates a speed BAND (a multiplicative interval)
and reports its true coverage. A shot that fails the quality bar gets no number
at all, which is a better product than a confident wrong one.

Signals tested (all computable at analyse time, no ground truth):
  real_frac   fraction of the hit->bounce span backed by a REAL detection
  n_real      count of those detections
  span_s      flight duration (a too-short "flight" is a mis-paired event)
  gap_max     longest run of consecutive interpolated frames inside the arc

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\speed_confidence.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))


def arc_quality(ball_px, a, b):
    """Track-quality signals for the frame span [a, b]."""
    span = ball_px[a:b + 1]
    real = [p is not None for p in span]
    n = len(real)
    if n == 0:
        return dict(real_frac=0.0, n_real=0, gap_max=999)
    gap = run = 0
    for r in real:
        run = 0 if r else run + 1
        gap = max(gap, run)
    return dict(real_frac=sum(real) / n, n_real=sum(real), gap_max=gap)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--match", default=str(REPO / "data/output/fps/rally2_e3e.json"))
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_e3e.perception.json"))
    ap.add_argument("--hud", default=str(REPO / "data/gold/hud_yt_rally2.json"))
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--lag", type=float, nargs=2, default=(0.0, 2.0))
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    match = json.loads(Path(args.match).read_text(encoding="utf-8"))
    cache = json.loads(Path(args.cache).read_text(encoding="utf-8"))
    hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))["shots"]
    ball_px = cache["ball_px"]

    lo, hi = args.lag
    rows, used = [], set()
    for s in match["shots"]:
        t = s["t_hit_s"]
        cands = [(i, r) for i, r in enumerate(hud)
                 if i not in used and lo <= r["t_start_s"] - t <= hi]
        if not cands:
            continue
        i, r = min(cands, key=lambda ir: ir[1]["t_start_s"] - t)
        used.add(i)
        a = int(round(t * args.fps))
        b = int(round(s["bounce_t_s"] * args.fps))
        q = arc_quality(ball_px, a, b)
        rows.append(dict(t_hit_s=t, ours=s["speed_kmh"], hud=r["kmh"],
                         err=100.0 * (s["speed_kmh"] - r["kmh"]) / r["kmh"],
                         span_s=round(s["bounce_t_s"] - t, 3), **q))

    if not rows:
        raise SystemExit("no shots matched a HUD reading")
    print(f"{len(rows)} shots matched to a HUD reading\n")
    hdr = (f"{'t_hit':>6}{'ours':>8}{'HUD':>7}{'err':>8}{'real_frac':>11}"
           f"{'n_real':>8}{'span_s':>8}{'gap_max':>9}")
    print(hdr); print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: abs(r["err"])):
        print(f"{r['t_hit_s']:>6.2f}{r['ours']:>8.1f}{r['hud']:>7.1f}"
              f"{r['err']:>+7.0f}%{r['real_frac']:>11.2f}{r['n_real']:>8}"
              f"{r['span_s']:>8.2f}{r['gap_max']:>9}")

    # Which signal separates accurate shots from wild ones?
    err = np.array([abs(r["err"]) for r in rows])
    print(f"\ncorrelation of |error| with each quality signal (n={len(rows)}):")
    for key in ("real_frac", "n_real", "span_s", "gap_max"):
        v = np.array([r[key] for r in rows], float)
        if v.std() < 1e-9:
            continue
        print(f"  {key:<11} r = {np.corrcoef(v, err)[0, 1]:+.2f}")

    # Calibrate a gate + band on the signal that separates best.
    print(f"\nquality gate sweep — report a speed only when the arc qualifies:")
    hdr2 = (f"{'gate':<30}{'kept':>7}{'median |err|':>14}{'band for 80%':>15}")
    print(hdr2); print("-" * len(hdr2))
    gates = [
        ("(none — report everything)", lambda r: True),
        ("real_frac >= 0.5", lambda r: r["real_frac"] >= 0.5),
        ("real_frac >= 0.7", lambda r: r["real_frac"] >= 0.7),
        ("real_frac >= 0.7 & n_real >= 8", lambda r: r["real_frac"] >= 0.7 and r["n_real"] >= 8),
        ("real_frac >= 0.8 & gap_max <= 3", lambda r: r["real_frac"] >= 0.8 and r["gap_max"] <= 3),
    ]
    best = None
    for name, fn in gates:
        kept = [r for r in rows if fn(r)]
        if not kept:
            print(f"{name:<30}{0:>7}{'—':>14}{'—':>15}")
            continue
        e = np.array([abs(r["err"]) for r in kept])
        band = np.percentile(e, 80)
        print(f"{name:<30}{len(kept):>7}{np.median(e):>13.0f}%{band:>14.0f}%")
        if len(kept) >= 3 and (best is None or np.median(e) < best[1]):
            best = (name, float(np.median(e)), len(kept), float(band))
    if best:
        print(f"\nbest gate: {best[0]} — keeps {best[2]}/{len(rows)} shots, "
              f"median error {best[1]:.0f}%, 80% of them within +-{best[3]:.0f}%")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"match": Path(args.match).name, "n": len(rows), "rows": rows},
            indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
