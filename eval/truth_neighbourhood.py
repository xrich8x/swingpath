"""eval/truth_neighbourhood.py - "the true court scores 0.20" scores WHICH true court?

A METHOD CORRECTION, not a new idea. Every search-free number this project has
quoted - `eval/score_truth.py`'s table, the "true court scores 0.18-0.31 against a
0.33 gate on 5 of 10 clips" line that went out in the research brief, and both
negatives measured earlier today - evaluates the scorer at the human's four clicked
corners, exactly.

But the gate does not define "correct" as those exact corners. It defines correct as
**within 20 px at 640 wide**, and that band is wide on purpose: it is the empty gap
between accepted courts (3.4-13.9 px) and refused ones (25.5-111 px). So there is a
whole neighbourhood of courts the gate calls right, and the human's clicks are just
one sample from it - not necessarily the best-registered one.

`eval/candidate_audit.py` turned this from a worry into a fact. On `am_hard_utr` the
detector's own three locks all land within 20 px of the human court AND outrank it by
0.296 in the accept score. The detector's snap is better registered to the paint than
the clicks are. Scoring at the clicks therefore UNDERSTATES what the criteria can do,
by an amount nobody has measured.

WHAT THIS MEASURES
------------------
For each clip: the human court's score, and the best score of any court still inside
the gate's own 20 px definition of correct, found by a local sweep around the human
parameters. Then both margins against the same coarse-grid distractors.

  g_best >> g_human   the criteria CAN recognise this court; the earlier numbers
                      measured our labelling, not the scorer, and the "the scorer
                      cannot see the truth" reading has to be withdrawn
  g_best ~ g_human    the earlier numbers stand and the scorer really is blind here

Either result is worth having, and the first one invalidates a claim this project has
already published, which is exactly why it gets checked rather than assumed.

    backend/.venv/Scripts/python.exe eval/truth_neighbourhood.py
"""

from __future__ import annotations

import argparse
import itertools
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

WRONG_PX_640 = 20.0
# Local offsets per parameter, as a fraction of frame width (cx/wn/wf) or height
# (yn/yf). Deliberately finer than the coarse grid and capped well inside the 20 px
# band, so every candidate generated is one the gate would still call correct.
OFFS = (-0.010, -0.005, -0.002, 0.0, 0.002, 0.005, 0.010)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from run_refs import references, frames_from

    t0 = time.time()
    print(f"{'clip':16s} {'g@human':>8s} {'g@best':>8s} {'lift':>7s} {'err':>6s} "
          f"{'m@human':>8s} {'m@best':>8s} {'>=.33':>7s}")
    print("-" * 74)
    rows = []
    for clip, pts_path, vid in references():
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        named = {n: v for n, v in ref.items() if not n.startswith("_")}
        if not all(n in named for n in DBL):
            continue
        per = []
        for _p, im in frames_from(Path(vid), a.frames):
            dt, cos2, sin2, w, h, _l = cf._precompute(im, calibration, None)
            tol = max(2.0, w * 0.006)
            cpts = [court.LANDMARKS[n] for n in DBL]
            scale = 640.0 / w

            Ht = calibration.compute_homography(cpts, [named[n] for n in DBL])
            txy = np.array([calibration.court_to_image(Ht, [court.LANDMARKS[n]])[0]
                            for n in DBL])

            def _g(H):
                return cf._ori_detail(H, calibration, court, dt, cos2, sin2,
                                      w, h, tol, 0.80)[0]

            def _err(c):
                cand = np.array([c[n] for n in DBL], float)
                return float(np.mean(np.hypot(*(cand - txy).T))) * scale

            g_hum = _g(Ht)

            # --- the neighbourhood the GATE still calls correct
            p0 = cf._params_from_corners({n: np.asarray(named[n], float)
                                          for n in DBL})
            span = [w, h, h, w, w]
            g_best, e_best = g_hum, 0.0
            for combo in itertools.product(OFFS, repeat=5):
                p = [p0[i] + combo[i] * span[i] for i in range(5)]
                c = cf._corners(*p)
                e = _err(c)
                if e > WRONG_PX_640:
                    continue                 # outside the gate's own definition
                try:
                    g = _g(calibration.compute_homography(cpts, [c[n] for n in DBL]))
                except Exception:
                    continue
                if g > g_best:
                    g_best, e_best = g, e

            # --- distractors: the shipped coarse grid, same as every other harness
            ax = [np.asarray(v) * (w if i in (0, 3, 4) else h)
                  for i, v in enumerate(cf.COARSE_GRID)]
            bw = 0.0
            for cx, yn, yf, wn, wf in itertools.product(*ax):
                c = cf._corners(cx, yn, yf, wn, wf)
                if _err(c) <= WRONG_PX_640:
                    continue
                try:
                    bw = max(bw, _g(calibration.compute_homography(
                        cpts, [c[n] for n in DBL])))
                except Exception:
                    continue
            per.append((g_hum, g_best, e_best, g_hum - bw, g_best - bw))
        if not per:
            continue
        m = np.median(np.array(per, float), axis=0)
        rows.append({"clip": clip, "g_human": m[0], "g_best": m[1], "err_best": m[2],
                     "margin_human": m[3], "margin_best": m[4]})
        gate = ("both" if m[0] >= 0.33 else
                "BEST" if m[1] >= 0.33 else "neither")
        print(f"{clip:16s} {m[0]:8.3f} {m[1]:8.3f} {m[1]-m[0]:+7.3f} {m[2]:6.1f} "
              f"{m[3]:+8.3f} {m[4]:+8.3f} {gate:>7s}", flush=True)

    if not rows:
        return
    print("-" * 74)
    lift = float(np.median([r["g_best"] - r["g_human"] for r in rows]))
    mh = float(np.median([r["margin_human"] for r in rows]))
    mb = float(np.median([r["margin_best"] for r in rows]))
    ah = sum(1 for r in rows if r["g_human"] >= 0.33)
    ab = sum(1 for r in rows if r["g_best"] >= 0.33)
    wh = sum(1 for r in rows if r["margin_human"] > 0)
    wb = sum(1 for r in rows if r["margin_best"] > 0)
    n = len(rows)
    print(f"median lift {lift:+.3f}   median margin {mh:+.3f} -> {mb:+.3f}")
    print(f"clears the 0.33 gate: {ah}/{n} -> {ab}/{n}      "
          f"margin positive: {wh}/{n} -> {wb}/{n}")
    print(f"median distance of the best-scoring correct court from the human "
          f"clicks: {np.median([r['err_best'] for r in rows]):.1f} px @640")
    print(f"\n{time.time()-t0:.0f}s. If the lift is large, every search-free number "
          f"this project has\nquoted at the human corners is a LOWER BOUND and the "
          f"ones already published need\ncorrecting in place, not re-explaining.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
