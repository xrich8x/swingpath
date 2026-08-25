"""eval/evid_band_sweep.py - does the evidence gate cost us the MARGIN?

Step O2 of docs/sessions/SESSION_O_shell_courts.md. Search-free, so it needs no
shell ground truth and can run while the shell clips are being labelled.

THE HYPOTHESIS
--------------
`_ori_detail` decides a model line is "measurable" when paint sits within
**EVID_BAND (5.0) x tol**, but only counts support within **1 x tol**. A truss or a
fence rail 3-4 tol away from a projected court line therefore promotes that line
into the DENOMINATOR while contributing nothing to the numerator. On a cluttered
frame that is a mechanical drag on the score of the TRUE court.

If that is right, narrowing the band should lift the true court. But narrowing it
also lifts every wrong court, and a wrong court that drops to three well-supported
lines scores ~0.95 on them. So:

  * THE HEADLINE IS THE MARGIN, not the level.
        margin = score(true court) - max score(court >20 px from truth)
    A higher level at the truth with a lower margin is a recall lever that hands us
    a confident wrong court. That is how the seed-grid widening failed.
  * n_included IS REPORTED ON EVERY HYPOTHESIS, and three guards against the
    three-lines-at-0.95 degenerate are scored alongside the raw number.

WHAT THE GUARD MODES ARE
------------------------
    raw          the score as shipped
    scaled8      g * min(n_included, 8) / 8
    scaled_seen  g * n_included / n_geometrically_in_frame   <- the honest ratio:
                 on a low mount fewer than 8 lines are in frame at all, and a fixed
                 /8 punishes the amateur framing this project exists for
    gated7       g if n_included >= 7 else 0

`n_geometrically_in_frame` is free: it is exactly what n_included becomes when
EVID_MIN is 0, so the `geom` config below measures it for every candidate and the
other configs reuse it.

THE `geom` CONFIG IS THE CHEAP VERSION OF THE CLEANER FIX
----------------------------------------------------------
Deciding observability from GEOMETRY instead of from nearby paint is a one-line
change - `ev = seen`, dropping the EVID_MIN test - so the in-frame half of it costs
nothing and is measured here as a config rather than proposed as a build. Only the
un-occluded half needs new machinery. See the brief for the cost.

METHOD NOTE, so this is not mistaken for a product measurement: the sweep sets the
module constants `courtfit.EVID_BAND` / `EVID_MIN` and calls the REAL, shipped
`_ori_detail`, so no scoring logic is reimplemented here and none can drift. But a
constant swept in a diagnostic is not a constant shipped: whatever wins here has to
be re-measured through the full product path against the gold gate before it counts.

Ground truth is human only - the `"_exact": true` calibrations. Per the brief's
tuning rule, THIS is where tuning happens; the shell set is verification only.

    backend/.venv/Scripts/python.exe eval/evid_band_sweep.py
    backend/.venv/Scripts/python.exe eval/evid_band_sweep.py --frames 3 --json out.json
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

WRONG_PX_640 = 20.0     # the gate's own number; not a new one

# (label, EVID_BAND, EVID_MIN). `geom` must run FIRST - the others reuse its
# n_included as the geometric in-frame count.
CONFIGS = [
    ("geom",     5.0, 0.00),     # observability from geometry alone
    ("band5.0",  5.0, 0.20),     # AS SHIPPED
    ("band3.0",  3.0, 0.20),
    ("band2.0",  2.0, 0.20),
    ("band1.5",  1.5, 0.20),
    ("band1.0",  1.0, 0.20),     # measurable == supported
]
MODES = ("raw", "scaled8", "scaled_seen", "gated7")


def _mode_score(g: float, n_inc: int, n_seen: int, mode: str) -> float:
    if mode == "raw":
        return g
    if mode == "scaled8":
        return g * min(n_inc, 8) / 8.0
    if mode == "scaled_seen":
        return g * n_inc / max(n_seen, 1)
    return g if n_inc >= 7 else 0.0


def frame_setup(img, named, calibration, court, cf):
    """Everything that does not depend on the evidence gate, done once."""
    dt, cos2, sin2, w, h, _lines = cf._precompute(img, calibration, None)
    tol = max(2.0, w * 0.006)
    court_pts = [court.LANDMARKS[n] for n in DBL]
    scale = 640.0 / w

    H_true = calibration.compute_homography(court_pts, [named[n] for n in DBL])
    true_xy = np.array([calibration.court_to_image(H_true, [court.LANDMARKS[n]])[0]
                        for n in DBL])

    ax = [np.asarray(v) * (w if i in (0, 3, 4) else h)
          for i, v in enumerate(cf.COARSE_GRID)]
    wrong = []
    for cx, yn, yf, wn, wf in itertools.product(*ax):
        c = cf._corners(cx, yn, yf, wn, wf)
        cand = np.array([c[n] for n in DBL], float)
        if float(np.mean(np.hypot(*(cand - true_xy).T))) * scale <= WRONG_PX_640:
            continue                                   # this IS the true court
        try:
            wrong.append(calibration.compute_homography(court_pts, [c[n] for n in DBL]))
        except Exception:
            continue
    return {"dt": dt, "cos2": cos2, "sin2": sin2, "w": w, "h": h, "tol": tol,
            "H_true": H_true, "wrong": wrong}


def score_frame(fs, cfg_label, calibration, court, cf, seen_cache):
    """(g_true, n_true, {mode: (best_wrong_score, n_at_best)}) for one config."""
    def _d(H):
        return cf._ori_detail(H, calibration, court, fs["dt"], fs["cos2"], fs["sin2"],
                              fs["w"], fs["h"], fs["tol"], 0.80)

    g_true, _nl, n_true = _d(fs["H_true"])
    if cfg_label == "geom":
        seen_cache["true"] = n_true
        seen_cache["wrong"] = np.zeros(len(fs["wrong"]), int)
    ns_true = seen_cache["true"]

    best = {m: (-1.0, 0) for m in MODES}
    for j, H in enumerate(fs["wrong"]):
        g, _n, n_inc = _d(H)
        if cfg_label == "geom":
            seen_cache["wrong"][j] = n_inc
        ns = int(seen_cache["wrong"][j])
        for m in MODES:
            s = _mode_score(g, n_inc, ns, m)
            if s > best[m][0]:
                best[m] = (s, n_inc)
    return g_true, n_true, ns_true, best


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3, help="frames per clip")
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from run_refs import references, frames_from

    refs = references()
    if a.clips:
        refs = [r for r in refs if r[0] in set(a.clips)]
    print(f"{len(refs)} human-placed calibrations, {a.frames} frames each; "
          f"distractors = the shipped coarse grid; a candidate is WRONG beyond "
          f"{WRONG_PX_640:.0f} px @640\n")

    # --- one setup pass over every frame (the expensive part, done once)
    t0 = time.time()
    setups = []
    for clip, pts_path, vid in refs:
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        named = {n: v for n, v in ref.items() if not n.startswith("_")}
        if not all(n in named for n in DBL):
            print(f"  {clip}: skipped (incomplete corners)")
            continue
        for _p, im in frames_from(Path(vid), a.frames):
            setups.append((clip, frame_setup(im, named, calibration, court, cf)))
        print(f"  {clip}: ready", flush=True)
    print(f"\n{len(setups)} frames prepared in {time.time()-t0:.0f}s; "
          f"{np.mean([len(s[1]['wrong']) for s in setups]):.0f} distractors each\n")

    caches = [{} for _ in setups]
    keep_band, keep_min = cf.EVID_BAND, cf.EVID_MIN
    rows = []
    try:
        for label, band, emin in CONFIGS:
            cf.EVID_BAND, cf.EVID_MIN = band, emin
            t1 = time.time()
            per = {}
            for (clip, fs), cache in zip(setups, caches):
                gt, nt, ns, best = score_frame(fs, label, calibration, court, cf, cache)
                per.setdefault(clip, []).append((gt, nt, ns, best))
            for clip, fr in per.items():
                for m in MODES:
                    st = [_mode_score(g, n, ns, m) for g, n, ns, _b in fr]
                    sw = [b[m][0] for _g, _n, _ns, b in fr]
                    nw = [b[m][1] for _g, _n, _ns, b in fr]
                    rows.append({
                        "config": label, "mode": m, "clip": clip,
                        "s_true": float(np.median(st)),
                        "s_wrong": float(np.median(sw)),
                        "margin": float(np.median(st)) - float(np.median(sw)),
                        "n_true": float(np.median([f[1] for f in fr])),
                        "n_seen": float(np.median([f[2] for f in fr])),
                        "n_wrong": float(np.median(nw)),
                        "g_true": float(np.median([f[0] for f in fr]))})
            print(f"  {label:9s} scored in {time.time()-t1:.0f}s", flush=True)
    finally:
        cf.EVID_BAND, cf.EVID_MIN = keep_band, keep_min

    # --- the headline table: margin first, level second
    print(f"\n{'config':9s} {'mode':12s} {'margin':>8s} {'win':>6s} {'s@true':>7s} "
          f"{'s@wrg':>7s} {'n_inc':>6s} {'n_seen':>6s} {'n@wrg':>6s} {'g@true':>7s}")
    print("-" * 88)
    n_clips = len({r["clip"] for r in rows})
    best_key = None
    for label, _b, _e in CONFIGS:
        for m in MODES:
            sub = [r for r in rows if r["config"] == label and r["mode"] == m]
            if not sub:
                continue
            med = float(np.median([r["margin"] for r in sub]))
            win = sum(1 for r in sub if r["margin"] > 0)
            star = " " if not (label == "band5.0" and m == "raw") else "*"
            print(f"{label:9s} {m:12s} {med:+8.3f} {win:3d}/{n_clips:<2d} "
                  f"{np.median([r['s_true'] for r in sub]):7.3f} "
                  f"{np.median([r['s_wrong'] for r in sub]):7.3f} "
                  f"{np.median([r['n_true'] for r in sub]):6.1f} "
                  f"{np.median([r['n_seen'] for r in sub]):6.1f} "
                  f"{np.median([r['n_wrong'] for r in sub]):6.1f} "
                  f"{np.median([r['g_true'] for r in sub]):7.3f}{star}")
            if best_key is None or (win, med) > best_key[0]:
                best_key = ((win, med), label, m)
    print("-" * 88)
    print("* = AS SHIPPED (band 5.0, raw). Every other row is a candidate change.")
    if best_key:
        (win, med), label, m = best_key
        print(f"best by (clips won, median margin): {label} + {m}  "
              f"-> {win}/{n_clips} clips, median margin {med:+.3f}")
    print("\nA higher s@true with a LOWER margin is a recall lever that ships a\n"
          "confident wrong court. Read the margin column first.")

    # --- the population the hypothesis is actually about: the clips where the
    # shipped scorer puts the TRUE court below its own accept gate. A change that
    # only helps clips already comfortably accepted has not touched the problem.
    ship = {r["clip"]: r for r in rows
            if r["config"] == "band5.0" and r["mode"] == "raw"}
    hard = sorted(c for c, r in ship.items() if r["g_true"] < 0.33)
    print(f"\n\nTHE FAILING HALF - {len(hard)}/{n_clips} clips where the shipped "
          f"scorer puts the TRUE court below its own 0.33 gate:")
    print(f"  {', '.join(hard) if hard else '(none)'}")
    if hard:
        print(f"\n{'config':9s} {'mode':12s} {'margin':>8s} {'win':>6s} "
              f"{'s@true':>7s} {'s@wrg':>7s} {'>=0.33':>7s}")
        print("-" * 62)
        for label, _b, _e in CONFIGS:
            for m in MODES:
                sub = [r for r in rows if r["config"] == label and r["mode"] == m
                       and r["clip"] in set(hard)]
                if not sub:
                    continue
                star = "*" if (label == "band5.0" and m == "raw") else " "
                print(f"{label:9s} {m:12s} "
                      f"{np.median([r['margin'] for r in sub]):+8.3f} "
                      f"{sum(1 for r in sub if r['margin'] > 0):3d}/{len(hard):<2d} "
                      f"{np.median([r['s_true'] for r in sub]):7.3f} "
                      f"{np.median([r['s_wrong'] for r in sub]):7.3f} "
                      f"{sum(1 for r in sub if r['s_true'] >= 0.33):4d}/{len(hard):<2d}"
                      f"{star}")

    # --- per-clip margin CHANGE vs shipped: where does a candidate make it WORSE?
    print(f"\n\nPER-CLIP MARGIN vs SHIPPED (negative = this change made that clip "
          f"harder to tell apart)")
    cands = [(l, m) for l, _b, _e in CONFIGS for m in MODES
             if not (l == "band5.0" and m == "raw")]
    best4 = sorted(cands, key=lambda k: -float(np.median(
        [r["margin"] for r in rows if r["config"] == k[0] and r["mode"] == k[1]])))[:4]
    hdr = "".join(f"{l[:5]}/{m[:6]:>7s}" for l, m in best4)
    print(f"{'clip':24s} {'shipped':>8s} {hdr}")
    print("-" * (33 + 13 * len(best4)))
    for clip in sorted(ship):
        line = f"{clip:24s} {ship[clip]['margin']:+8.3f}"
        for l, m in best4:
            r = next(r for r in rows if r["config"] == l and r["mode"] == m
                     and r["clip"] == clip)
            line += f"{r['margin'] - ship[clip]['margin']:+13.3f}"
        print(line)

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
