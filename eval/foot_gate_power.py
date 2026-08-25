"""eval/foot_gate_power.py - can the player-foot gate actually tell a good lock from a bad one?

O1 killed B1's RECALL case: a refuse-only gate cannot manufacture an acceptance, and
even a perfect one leaves the two convertible reference clips at 50% and 67% survivor
agreement against a 75% bar. Its PRECISION case is still open, and this measures it.

THE CLAIM UNDER TEST
--------------------
Players stand on the court. Push their feet through a candidate homography and a
correct court puts them on it; the `am_ntrp45w`-family failure, which collapses all
23.77 m onto a curtain band near the horizon, sends them hundreds of metres away.

That is a plausible story and this project has been wrong about plausible stories
before. It is worth exactly what a measurement says it is worth.

MEASURED AS SEPARATION, ON EVERY LOCK, NOT AS ANECDOTES
--------------------------------------------------------
Every per-frame lock across all 30 clips (20 gold + 10 calibrated) is labelled from
the human court:

    GOOD  within 20 px @640 of truth  - the gate must NOT refuse these
    BAD   beyond that                 - the gate SHOULD refuse these

then scored by what fraction of the clip's foot points land inside the court under
that lock's homography. A useful gate has the two distributions apart; a useless one
has them on top of each other, and no threshold rescues that.

The threshold table is the decision. A refuse-only gate is only worth building if
some threshold kills a large share of BAD locks while killing almost no GOOD ones -
the collateral column is the one that spends the precision record.

Reuses the fit cache built by eval/agree_sweep.py, so the expensive `auto_fit_frame`
pass is not repeated. Run that first.

    backend/.venv/Scripts/python.exe eval/agree_sweep.py --rebuild     # first
    backend/.venv/Scripts/python.exe eval/foot_gate_power.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

from swingvision.courtfit import DBL  # noqa: E402

CACHE = REPO / "data" / "output" / "_fit_cache.json"
WRONG_PX_640 = 20.0
MARGINS_M = (5.0, 10.0, 20.0)      # court +/- this; 10.0 is movers.GATE_MARGIN_M
THRESHOLDS = (0.10, 0.25, 0.50, 0.75, 0.90)


def _err640(a, b, calibration, court, scale):
    try:
        Ha = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [a[n] for n in DBL])
        Hb = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [b[n] for n in DBL])
    except Exception:
        return None
    return float(np.mean([
        np.hypot(*(calibration.court_to_image(Ha, [court.LANDMARKS[n]])[0]
                   - calibration.court_to_image(Hb, [court.LANDMARKS[n]])[0]))
        for n in DBL])) * scale


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    if not CACHE.exists():
        raise SystemExit(f"no fit cache at {CACHE} - run eval/agree_sweep.py --rebuild")
    cache = json.loads(CACHE.read_text(encoding="utf-8"))

    from swingvision import calibration, court
    from score_truth import truth_sources
    import movers

    print(f"labelling every per-frame lock from the human court; GOOD = within "
          f"{WRONG_PX_640:.0f} px @640.\n")
    print(f"{'clip':24s} {'feet':>5s} {'good':>5s} {'bad':>4s} "
          + "".join(f"{f'g/b @{m:.0f}m':>13s}" for m in MARGINS_M))
    print("-" * (40 + 13 * len(MARGINS_M)))

    recs, t0 = [], time.time()
    for clip, src, frames in truth_sources(a.k):
        v = cache.get(clip)
        if not v:
            continue
        ims = [im for _k, im, _n in frames]
        feet = movers.foot_points(ims)
        scale = 640.0 / v["w"]
        per = []
        for i, (_key, _im, named) in enumerate(frames):
            if i >= len(v["fits"]) or v["fits"][i] is None:
                continue
            f = v["fits"][i]
            e = _err640(named, f, calibration, court, scale)
            if e is None:
                continue
            try:
                H = calibration.compute_homography(
                    [court.LANDMARKS[n] for n in DBL], [f[n] for n in DBL])
            except Exception:
                continue
            fr = {}
            for m in MARGINS_M:
                fr[m] = movers.feet_in_court(H, feet, calibration, court,
                                             margin_m=m)[0]
            per.append({"clip": clip, "src": src, "err": e,
                        "good": e <= WRONG_PX_640, "frac": fr,
                        "n_feet": len(feet)})
        recs += per
        g = [p for p in per if p["good"]]
        b = [p for p in per if not p["good"]]
        cols = ""
        for m in MARGINS_M:
            gm = f"{np.mean([p['frac'][m] for p in g]):.2f}" if g else "  - "
            bm = f"{np.mean([p['frac'][m] for p in b]):.2f}" if b else "  - "
            cols += f"{gm}/{bm:>4s}".rjust(13)
        print(f"{clip:24s} {len(feet):5d} {len(g):5d} {len(b):4d}{cols}", flush=True)

    good = [r for r in recs if r["good"]]
    bad = [r for r in recs if not r["good"]]
    print("-" * (40 + 13 * len(MARGINS_M)))
    print(f"{len(recs)} locks over {len({r['clip'] for r in recs})} clips: "
          f"{len(good)} GOOD, {len(bad)} BAD  ({time.time()-t0:.0f}s)")
    if not good or not bad:
        print("not enough of both classes to measure separation.")
        return

    print(f"\nSEPARATION - a gate is only worth building if these are far apart\n")
    print(f"{'margin':>8s} {'good mean':>10s} {'bad mean':>9s} {'gap':>7s} "
          f"{'good p10':>9s} {'bad p90':>8s}")
    print("-" * 56)
    for m in MARGINS_M:
        gv = np.array([r["frac"][m] for r in good])
        bv = np.array([r["frac"][m] for r in bad])
        print(f"{m:7.0f}m {gv.mean():10.3f} {bv.mean():9.3f} "
              f"{gv.mean()-bv.mean():+7.3f} {np.percentile(gv,10):9.3f} "
              f"{np.percentile(bv,90):8.3f}")

    print(f"\nWHAT A REFUSE-ONLY GATE WOULD ACTUALLY DO\n"
          f"(refuse a lock when its feet-in-court fraction is BELOW the threshold)\n")
    print(f"{'margin':>7s} {'thresh':>7s} {'bad killed':>18s} "
          f"{'GOOD killed (cost)':>20s}")
    print("-" * 56)
    best, rows = None, []
    for m in MARGINS_M:
        for t in THRESHOLDS:
            bk = sum(1 for r in bad if r["frac"][m] < t)
            gk = sum(1 for r in good if r["frac"][m] < t)
            rows.append({"margin": m, "thresh": t, "bad_killed": bk,
                         "good_killed": gk, "n_bad": len(bad), "n_good": len(good)})
            print(f"{m:6.0f}m {t:7.2f} {bk:8d}/{len(bad):<4d} "
                  f"({bk/len(bad)*100:4.1f}%) {gk:8d}/{len(good):<4d} "
                  f"({gk/len(good)*100:4.1f}%)")
            # the project's standing bar for a negation criterion: <=5% collateral
            if gk / len(good) <= 0.05 and (best is None or bk > best["bad_killed"]):
                best = rows[-1]
    print("-" * 56)
    if best:
        print(f"\nBest at the project's standing <=5% collateral ceiling: "
              f"margin {best['margin']:.0f} m, threshold {best['thresh']:.2f} -> "
              f"kills {best['bad_killed']/best['n_bad']*100:.1f}% of bad locks "
              f"at {best['good_killed']/best['n_good']*100:.1f}% collateral.")
        print("For scale, the two criteria this project already REJECTED on this bar "
              "were\npose proximity at 11.4% catch and racquet-box negation at 54.5% "
              "catch / 4.5%.")
    else:
        print("\nNO threshold reaches the <=5% collateral ceiling. On this evidence "
              "the foot\ngate is not a usable negation criterion and B1 should not "
              "be built.")

    if a.json:
        Path(a.json).write_text(json.dumps(
            {"locks": [{k: (v if k != "frac" else {str(a_): b_ for a_, b_ in v.items()})
                        for k, v in r.items()} for r in recs],
             "thresholds": rows}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
