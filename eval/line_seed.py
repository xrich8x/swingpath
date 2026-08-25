"""eval/line_seed.py - P3: build the court from the DETECTED LINES, not from a lattice.

The last branch standing in Session P. Three levers are already measured shut - refine
reach, the pose-prior weight in the ranking, and raising `topk` - and P1 named why:

  * the seed lattice's nearest court is 7-20 px@640 from the human court, while support
    is only counted within tol ~ 3.8 px, so the truth-nearest seed cannot fit the paint
    well enough to rank into the top 12;
  * and refinement does not rescue it - starting from that very seed it moves AWAY from
    truth on 17 of 38 clips and lands a median 14.1 px out (range 3.0-42.6).

Both failures share one cause: **every candidate this search can construct comes off a
5-parameter grid that knows nothing about where the paint actually is.**

THE ALTERNATIVE
---------------
A court's four outer corners are the intersections of four real lines - two baselines and
two doubles sidelines - and `_detect_lines` already returns those lines in normal form.
Pick two "across" lines and two "lengthwise" ones, intersect them, and the quad sits ON
the paint by construction. Its precision is set by the Hough line fit, not by a grid step.

WHAT THIS MEASURES, AND THE BAR IT HAS TO CLEAR
------------------------------------------------
Pre-registered before the first run:

    Line-derived seeding must produce a candidate CLOSER to the human court than the
    lattice's nearest seed (7-20 px@640) on a MAJORITY of clips.

Two numbers are reported per clip and they answer different questions:

    best      the closest quad to truth over every screened combination. Can the
              detected lines support the true court AT ALL? If this is large, the lines
              do not contain the answer and the branch is dead regardless of ranking.
    ranked    the distance of the quad the scorer would actually pick. The gap between
              `best` and `ranked` is what better ranking could buy - and only matters if
              `best` is good.

Ground truth is human only. Shell clips are VERIFICATION ONLY per the brief's tuning
rule and are reported separately; `mpc_tuesday` is excluded (labels disagree 25.4 px).

    backend/.venv/Scripts/python.exe eval/line_seed.py
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

# Keep the N longest lines in each family. The full cross-product of 20x20 lines is
# 36,100 quads; capping at 10 gives 2,025, which is the same order as the 2,207-seed
# lattice it is being compared against - so the comparison is of REPRESENTATION, not
# of how many candidates each side was allowed to try.
KEEP_PER_FAMILY = 10
ACROSS_DEG = 45.0        # |normal - 90deg| below this = an "across" line (baseline-ish)
EXCLUDE_TRUTH = {"mpc_tuesday_p01", "mpc_tuesday_p07"}


def _intersect(l1, l2):
    """(x, y) of two lines in (normal_angle, rho) form, or None if near-parallel.

    A line is x*cos(n) + y*sin(n) = rho, so two of them are a 2x2 solve whose
    determinant is sin(n2 - n1) - i.e. it vanishes exactly when they are parallel,
    which is the one case that has to be rejected rather than clamped."""
    n1, r1 = l1[0], l1[1]
    n2, r2 = l2[0], l2[1]
    det = np.sin(n2 - n1)
    if abs(det) < 1e-6:
        return None
    x = (r1 * np.sin(n2) - r2 * np.sin(n1)) / det
    y = (r2 * np.cos(n1) - r1 * np.cos(n2)) / det
    return float(x), float(y)


def split_families(lines):
    """(across, lengthwise) - baselines vs sidelines, longest first.

    CLUSTERED, NOT THRESHOLDED, and that distinction is the whole fix. The first
    version of this split lines by absolute orientation - "across" if the normal sat
    within 45deg of horizontal. It failed exactly where this project lives: on a low
    mount the doubles sidelines converge so steeply toward their vanishing point that
    they read as diagonal, land in the "across" bucket, and the lengthwise family
    starves. Measured on `am_hard_utr`, that split found TWO lengthwise lines while
    both true sidelines were sitting in the detected set at 0.1 and 2.2 px.

    The two families are the court's two vanishing directions, so the honest operation
    is a 2-cluster split on direction with no threshold at all. Angles are clustered in
    DOUBLE-ANGLE space (cos 2n, sin 2n) because a line at 179deg and one at 1deg are
    the same direction - the same representation `_ori_detail` already uses."""
    if len(lines) < 4:
        return [], []
    v = np.array([[np.cos(2 * n), np.sin(2 * n)] for n, _r, _w in lines])
    wt = np.array([w for _n, _r, w in lines], float)

    # seed the two centroids at the most dissimilar pair, then a few Lloyd steps
    d = v @ v.T
    i, j = np.unravel_index(int(np.argmin(d)), d.shape)
    c = np.array([v[i], v[j]], float)
    lab = np.zeros(len(v), int)
    for _ in range(8):
        lab = np.argmax(v @ c.T, axis=1)
        for k in (0, 1):
            m = lab == k
            if m.any():
                nc = (v[m] * wt[m, None]).sum(0)
                nrm = np.linalg.norm(nc)
                if nrm > 1e-9:
                    c[k] = nc / nrm

    # the cluster whose mean direction is nearer HORIZONTAL is the baselines: a
    # horizontal image line has normal 90deg, so double-angle 2n = 180deg -> cos = -1
    fam = [[], []]
    for idx, (n, rho, w) in enumerate(lines):
        fam[int(lab[idx])].append((n, rho, w))
    across_k = 0 if c[0][0] < c[1][0] else 1
    across, lengthwise = fam[across_k], fam[1 - across_k]
    across.sort(key=lambda t: -t[2])
    lengthwise.sort(key=lambda t: -t[2])
    return across[:KEEP_PER_FAMILY], lengthwise[:KEEP_PER_FAMILY]


def quads_from_lines(lines, w, h):
    """Every screened court quad the detected lines can form. [{corner: [x, y]}]."""
    across, lengthwise = split_families(lines)
    out = []
    for a1, a2 in itertools.combinations(across, 2):
        for l1, l2 in itertools.combinations(lengthwise, 2):
            pts = {}
            ok = True
            for ai, a in ((0, a1), (1, a2)):
                for li, l in ((0, l1), (1, l2)):
                    p = _intersect(a, l)
                    if p is None:
                        ok = False
                        break
                    pts[(ai, li)] = p
                if not ok:
                    break
            if not ok:
                continue
            # the LOWER across-line in the image is the near baseline
            ya = (pts[(0, 0)][1] + pts[(0, 1)][1]) / 2.0
            yb = (pts[(1, 0)][1] + pts[(1, 1)][1]) / 2.0
            near, far = (0, 1) if ya > yb else (1, 0)
            # left/right by x on the NEAR baseline, where the court is widest
            left, right = ((0, 1) if pts[(near, 0)][0] < pts[(near, 1)][0] else (1, 0))

            nbl, nbr = pts[(near, left)], pts[(near, right)]
            fbl, fbr = pts[(far, left)], pts[(far, right)]

            # --- screens: the same physical floors autodetect already applies, so a
            # quad that could never survive there is not counted as a candidate here.
            depth = ((nbl[1] + nbr[1]) - (fbl[1] + fbr[1])) / 2.0
            if depth < 0.06 * h:                       # autodetect's depth floor
                continue
            wn = abs(nbr[0] - nbl[0])
            wf = abs(fbr[0] - fbl[0])
            if wn < 0.15 * w or wf >= wn:              # width floor + perspective
                continue
            if not all(-2 * w < p[0] < 3 * w and -2 * h < p[1] < 3 * h
                       for p in (nbl, nbr, fbl, fbr)):
                continue                               # runaway intersection
            out.append({"near_bl_doubles": list(nbl), "near_br_doubles": list(nbr),
                        "far_br_doubles": list(fbr), "far_bl_doubles": list(fbl)})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    reach = {r["clip"]: r for r in json.loads(
        (REPO / "data" / "output" / "seed_reach.json").read_text(encoding="utf-8"))}

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips, {a.frames} frames each. Quads built from the DETECTED "
          f"LINES.\nBar (pre-registered): beat the lattice's nearest seed on a "
          f"majority of clips.\n")
    print(f"{'clip':22s} {'lines':>10s} {'quads':>6s} {'lattice':>8s} {'best':>6s} "
          f"{'ranked':>7s}  vs lattice")
    print("-" * 84)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        per = []
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            dt, cos2, sin2, w, h, lines = cf._precompute(
                im, calibration, calibration.court_line_mask)
            tol = max(2.0, w * 0.006)
            scale = 640.0 / w
            txy = np.array([named[n] for n in DBL], float)
            ac, ln = split_families(lines)
            qs = quads_from_lines(lines, w, h)
            if not qs:
                per.append({"n_across": len(ac), "n_len": len(ln), "n_quads": 0,
                            "best": None, "ranked": None})
                continue
            best, ranked, best_g = 1e9, None, -1.0
            cpts = [court.LANDMARKS[n] for n in DBL]
            for q in qs:
                cand = np.array([q[n] for n in DBL], float)
                d = float(np.mean(np.hypot(*(cand - txy).T))) * scale
                best = min(best, d)
                try:
                    H = calibration.compute_homography(cpts, [q[n] for n in DBL])
                except Exception:
                    continue
                g, _nl, _ev = cf._ori_detail(H, calibration, court, dt, cos2, sin2,
                                             w, h, tol, 0.80)
                if g > best_g:
                    best_g, ranked = g, d
            per.append({"n_across": len(ac), "n_len": len(ln), "n_quads": len(qs),
                        "best": best, "ranked": ranked})
        if not per:
            continue
        med = lambda k: (float(np.median([x[k] for x in per if x[k] is not None]))  # noqa: E731
                         if any(x[k] is not None for x in per) else None)
        lat = reach.get(clip, {}).get("seed_err")
        row = {"clip": clip, "src": src, "shell": frames[0][1].shape[1] >= 3000,
               "excluded": clip in EXCLUDE_TRUTH,
               "n_across": med("n_across"), "n_len": med("n_len"),
               "n_quads": med("n_quads"), "best": med("best"),
               "ranked": med("ranked"), "lattice": lat}
        rows.append(row)
        v = "-" if (row["best"] is None or lat is None) else (
            "BETTER" if row["best"] < lat else "worse")
        f = lambda x: "-" if x is None else f"{x:.1f}"    # noqa: E731
        print(f"{clip:22s} {row['n_across']:4.0f}a/{row['n_len']:<4.0f}l "
              f"{row['n_quads']:6.0f} {f(lat):>8s} {f(row['best']):>6s} "
              f"{f(row['ranked']):>7s}  {v}", flush=True)

    print("-" * 84)
    live = [r for r in rows if not r["excluded"] and r["best"] is not None
            and r["lattice"] is not None]
    print(f"{len(rows)} clips in {time.time()-t0:.0f}s.\n")
    for label, pop in (("GOLD (the gate)", [r for r in live if r["src"] == "gold"]),
                       ("REFERENCES (1920)",
                        [r for r in live if r["src"] == "ref" and not r["shell"]]),
                       ("SHELL (verification only)",
                        [r for r in live if r["shell"]])):
        if not pop:
            continue
        better = sum(1 for r in pop if r["best"] < r["lattice"])
        print(f"{label:26s} best-quad beats the lattice on {better}/{len(pop)}   "
              f"median best {np.median([r['best'] for r in pop]):5.1f} px "
              f"(lattice {np.median([r['lattice'] for r in pop]):5.1f})")

    tune = [r for r in live if not r["shell"]]
    if tune:
        b = sum(1 for r in tune if r["best"] < r["lattice"])
        print(f"\nPRE-REGISTERED BAR: beat the lattice on a majority of the tuning "
              f"clips.\n  {b}/{len(tune)} -> "
              f"{'PASSES' if b > len(tune)/2 else 'FAILS'}")
        gap = [r["ranked"] - r["best"] for r in tune if r["ranked"] is not None]
        if gap:
            print(f"\nranked minus best = what better RANKING could buy: median "
                  f"{np.median(gap):+.1f} px.\n  Only worth chasing if `best` is "
                  f"already good - a well-ranked bad quad is still a bad quad.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
