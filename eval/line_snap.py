"""eval/line_snap.py - P3b: snap a candidate court onto the DETECTED LINES.

Session P's surviving branch, re-aimed after P3a failed. Two measurements set this up
and both are in `data/output/`:

  THE LINES ARE THERE.  Projecting the human court's four outer lines and looking for
  the nearest detected line: the near baseline is within 8 px on 36/40 clips, the far
  baseline on 38/40, the left sideline on 38/40, the right on 27/40 - at medians of
  2.7 / 2.9 / 1.3 / 4.1 px@640. `_detect_lines` is finding the court.

  THE REFINER IS NOT USING THEM.  Started from the seed NEAREST truth,
  `refine_homography_bounded` moves AWAY from truth on 17 of 38 clips and closer on 13,
  landing a median 14.1 px out (range 3.0-42.6, worst 9.8 -> 42.6).

So the court's own lines are sitting 1.3-4.1 px away and the refiner walks past them.

WHY THIS AND NOT P3a (BUILD THE QUAD FROM SCRATCH)
---------------------------------------------------
P3a tried to CONSTRUCT the quad by choosing two "baseline" lines and two "sideline"
lines. It failed, and the reason is geometric rather than a tuning miss: under
perspective the two doubles sidelines CONVERGE toward their vanishing point, so they
are not parallel in the image and do not form an angular cluster. Any split of the
detected lines into two families by direction is therefore ill-posed - measured, on
`am_hard_utr` it put 24 of 26 lines in one family while both true sidelines sat in the
detected set at 0.1 and 2.2 px. Grouping court lines by angle is wrong in principle,
not just badly tuned. (Doing it properly needs vanishing-point grouping - a real build.)

Snapping sidesteps the grouping problem entirely: a candidate court already says WHICH
projected line is the left sideline, so each model line looks up its own nearest real
line and no clustering is needed.

THE METHOD
----------
Given a candidate's four corners: project the four OUTER court lines, match each to the
nearest detected line (within an angle and rho tolerance), and if all four match,
replace the corners with the four intersections. Iterate twice - the second pass has a
better homography to project with.

THE BAR, PRE-REGISTERED
-----------------------
Applied to the same truth-nearest seed the refiner gets, this must
  (a) land closer to truth than `refine_homography_bounded`'s median 14.1 px, AND
  (b) move CLOSER to truth on more clips than the refiner's 13 of 38.
Falling back to the candidate whenever four lines are not matched makes it refuse
rather than guess, so (b) is the honest test of whether it helps or just churns.

    backend/.venv/Scripts/python.exe eval/line_snap.py
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

# The four lines whose intersections ARE the doubles corners.
OUTER = (("near", (0.0, 0.0), (10.97, 0.0)),
         ("far", (0.0, 23.77), (10.97, 23.77)),
         ("left", (0.0, 0.0), (0.0, 23.77)),
         ("right", (10.97, 0.0), (10.97, 23.77)))
ANG_TOL_DEG = 6.0        # same angular tolerance _structure already uses (7 deg)
RHO_TOL_640 = 12.0       # in px@640; generous vs the 1.3-4.1 px medians measured
ITERS = 2
EXCLUDE_TRUTH = {"mpc_tuesday_p01", "mpc_tuesday_p07"}


def _intersect(l1, l2):
    n1, r1 = l1
    n2, r2 = l2
    det = np.sin(n2 - n1)
    if abs(det) < 1e-6:
        return None
    return (float((r1 * np.sin(n2) - r2 * np.sin(n1)) / det),
            float((r2 * np.cos(n1) - r1 * np.cos(n2)) / det))


def snap_to_detected(named, lines, calibration, court, cf, w):
    """Replace a candidate's corners with the intersections of the detected lines its
    own model lines match. Returns (named, n_matched) - unchanged when fewer than 4."""
    if not lines:
        return named, 0
    scale = 640.0 / w
    rho_tol = RHO_TOL_640 / scale                 # back to this frame's own pixels
    ang_tol = np.deg2rad(ANG_TOL_DEG)
    cur = named

    for _ in range(ITERS):
        try:
            H = calibration.compute_homography(
                [court.LANDMARKS[n] for n in DBL], [cur[n] for n in DBL])
        except Exception:
            return cur, 0
        found = {}
        for tag, a, b in OUTER:
            pa = calibration.court_to_image(H, [a])[0]
            pb = calibration.court_to_image(H, [b])[0]
            n0, r0 = cf._norm_form(pa, pb)
            best, bd = None, 1e18
            for ln, lr, _lw in lines:
                dth = abs(np.mod(n0 - ln + np.pi / 2, np.pi) - np.pi / 2)
                if dth > ang_tol:
                    continue
                dr = abs(r0 - lr)
                if dr <= rho_tol and dr < bd:
                    best, bd = (ln, lr), dr
            if best is not None:
                found[tag] = best
        if len(found) < 4:
            return cur, len(found)          # refuse rather than guess
        c = {}
        for tag, side in (("near_bl_doubles", ("near", "left")),
                          ("near_br_doubles", ("near", "right")),
                          ("far_br_doubles", ("far", "right")),
                          ("far_bl_doubles", ("far", "left"))):
            p = _intersect(found[side[0]], found[side[1]])
            if p is None:
                return cur, len(found)
            c[tag] = [p[0], p[1]]
        cur = c
    return cur, 4


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--rho-tol", type=float, default=None, dest="rho")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    global RHO_TOL_640
    if a.rho is not None:
        RHO_TOL_640 = a.rho

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources
    from seed_reach import build_seeds

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips, {a.frames} frames. Starting from the SAME truth-nearest "
          f"seed\nthe refiner gets, comparing where each one lands.\n")
    print(f"{'clip':22s} {'seed':>6s} {'refine':>7s} {'snap':>6s} {'matched':>8s}  "
          f"better?")
    print("-" * 68)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        per = []
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            mf = calibration.court_line_mask
            dt, cos2, sin2, w, h, lines = cf._precompute(im, calibration, mf)
            tol = max(2.0, w * 0.006)
            scale = 640.0 / w
            txy = np.array([named[n] for n in DBL], float)

            seeds, _prior = build_seeds(im, calibration, court, cf,
                                        dt, cos2, sin2, w, h, tol)
            if not seeds:
                continue
            d = []
            for _r, _g, _nl, p, _m in seeds:
                c = cf._corners(*p)
                d.append(float(np.mean(np.hypot(
                    *(np.array([c[n] for n in DBL], float) - txy).T))) * scale)
            j = int(np.argmin(d))
            seed_named = {k: list(v) for k, v in cf._corners(*seeds[j][3]).items()}
            e_seed = d[j]

            try:
                _Hs, ref, _ = calibration.refine_homography_bounded(
                    im, cf._corners(*seeds[j][3]), max_move_px=55.0, mask_fn=mf)
                e_ref = float(np.mean(np.hypot(
                    *(np.array([ref[n] for n in DBL], float) - txy).T))) * scale
            except Exception:
                e_ref = None

            snapped, nm = snap_to_detected(seed_named, lines, calibration, court, cf, w)
            e_snap = float(np.mean(np.hypot(
                *(np.array([snapped[n] for n in DBL], float) - txy).T))) * scale
            per.append({"seed": e_seed, "refine": e_ref, "snap": e_snap, "matched": nm})
        if not per:
            continue
        med = lambda k: (float(np.median([x[k] for x in per if x[k] is not None]))  # noqa: E731
                         if any(x[k] is not None for x in per) else None)
        row = {"clip": clip, "src": src, "shell": frames[0][1].shape[1] >= 3000,
               "excluded": clip in EXCLUDE_TRUTH, "seed": med("seed"),
               "refine": med("refine"), "snap": med("snap"),
               "matched": med("matched")}
        rows.append(row)
        f = lambda x: "-" if x is None else f"{x:.1f}"   # noqa: E731
        v = ("-" if row["refine"] is None else
             "SNAP" if row["snap"] < row["refine"] - 0.5 else
             "refine" if row["refine"] < row["snap"] - 0.5 else "tie")
        print(f"{clip:22s} {f(row['seed']):>6s} {f(row['refine']):>7s} "
              f"{f(row['snap']):>6s} {row['matched']:8.0f}  {v}", flush=True)

    print("-" * 68)
    live = [r for r in rows if not r["excluded"] and r["refine"] is not None]
    if not live:
        return
    snap_w = sum(1 for r in live if r["snap"] < r["refine"] - 0.5)
    ref_w = sum(1 for r in live if r["refine"] < r["snap"] - 0.5)
    closer_snap = sum(1 for r in live if r["snap"] < r["seed"] - 1)
    closer_ref = sum(1 for r in live if r["refine"] < r["seed"] - 1)
    print(f"{len(live)} clips in {time.time()-t0:.0f}s\n")
    print(f"median distance from truth   seed {np.median([r['seed'] for r in live]):5.1f} "
          f"-> refine {np.median([r['refine'] for r in live]):5.1f} "
          f"| snap {np.median([r['snap'] for r in live]):5.1f}")
    print(f"moves CLOSER than the seed   refine {closer_ref}/{len(live)}   "
          f"snap {closer_snap}/{len(live)}")
    print(f"head to head                 snap better on {snap_w}, refine better on "
          f"{ref_w}, tie {len(live)-snap_w-ref_w}")
    print(f"all four lines matched on    {sum(1 for r in live if r['matched'] >= 4)}"
          f"/{len(live)} clips")

    print(f"\nPRE-REGISTERED BAR: beat the refiner's median 14.1 px AND move closer on "
          f"more\nthan its 13/38 clips.")
    mb = np.median([r["snap"] for r in live]) < np.median([r["refine"] for r in live])
    print(f"  median: {'PASS' if mb else 'FAIL'}    "
          f"closer-count: {'PASS' if closer_snap > closer_ref else 'FAIL'}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
