"""eval/tol_sweep.py - is the true court scoring 0.20 because the paint is missing,
or because our GROUND TRUTH is a few pixels off?

A confound in every search-free number this session has produced, including its two
negatives. `_ori_detail` counts a model sample as supported only within

    tol = max(2.0, w * 0.006)        # 3.84 px at 640 wide

of a mask pixel. The human court comes from four clicked corners, and a couple of
pixels of click error at a corner becomes a much larger error at the far end of a
23.77 m line once it is projected. If that is what is happening, then "the true
court scores 0.203" is a statement about the labelling, not about the detector, and
every conclusion drawn from it is unsafe.

The two readings are cleanly separable, which is why this is worth two minutes:

  paint IS there, registration is off  -> g@true climbs steeply with tol and then
                                          plateaus, because the line is found as
                                          soon as the band is wide enough to reach it
  paint is genuinely absent            -> g@true stays flat; a wider band finds
                                          nothing because there is nothing to find

THE MARGIN STILL DECIDES. Widening tol lifts wrong courts too - a fat band is easier
for everyone to satisfy - so a rise in g@true that the margin does not follow is the
same wrong-court lever this session has now measured twice.

    backend/.venv/Scripts/python.exe eval/tol_sweep.py
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
MULTS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]      # 1.0 == as shipped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from run_refs import references, frames_from

    t0 = time.time()
    prepped = []
    for clip, pts_path, vid in references():
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        named = {n: v for n, v in ref.items() if not n.startswith("_")}
        if not all(n in named for n in DBL):
            continue
        for _p, im in frames_from(Path(vid), a.frames):
            dt, cos2, sin2, w, h, _l = cf._precompute(im, calibration, None)
            cpts = [court.LANDMARKS[n] for n in DBL]
            Ht = calibration.compute_homography(cpts, [named[n] for n in DBL])
            txy = np.array([calibration.court_to_image(Ht, [court.LANDMARKS[n]])[0]
                            for n in DBL])
            ax = [np.asarray(v) * (w if i in (0, 3, 4) else h)
                  for i, v in enumerate(cf.COARSE_GRID)]
            wrong = []
            for cx, yn, yf, wn, wf in itertools.product(*ax):
                c = cf._corners(cx, yn, yf, wn, wf)
                cand = np.array([c[n] for n in DBL], float)
                if float(np.mean(np.hypot(*(cand - txy).T))) * (640.0 / w) \
                        <= WRONG_PX_640:
                    continue
                try:
                    wrong.append(calibration.compute_homography(
                        cpts, [c[n] for n in DBL]))
                except Exception:
                    continue
            prepped.append((clip, dt, cos2, sin2, w, h,
                            max(2.0, w * 0.006), Ht, wrong))
    print(f"{len(prepped)} frames prepared in {time.time()-t0:.0f}s\n")

    rows = []
    for mult in MULTS:
        per = {}
        for clip, dt, cos2, sin2, w, h, tol0, Ht, wrong in prepped:
            tol = tol0 * mult

            def _g(H):
                return cf._ori_detail(H, calibration, court, dt, cos2, sin2,
                                      w, h, tol, 0.80)[0]
            gt = _g(Ht)
            bw = max((_g(H) for H in wrong), default=0.0)
            per.setdefault(clip, []).append((gt, bw))
        for clip, fr in per.items():
            gt = float(np.median([f[0] for f in fr]))
            bw = float(np.median([f[1] for f in fr]))
            rows.append({"mult": mult, "clip": clip, "g_true": gt,
                         "g_wrong": bw, "margin": gt - bw})
        print(f"  tol x{mult:<4} scored", flush=True)

    clips = sorted({r["clip"] for r in rows})
    print(f"\ng @ TRUE COURT by tol multiplier (x1.0 = as shipped)\n")
    print(f"{'clip':16s}" + "".join(f"{f'x{m}':>8s}" for m in MULTS) + "   shape")
    print("-" * (16 + 8 * len(MULTS) + 10))
    for c in clips:
        vals = [next(r["g_true"] for r in rows if r["clip"] == c and r["mult"] == m)
                for m in MULTS]
        base = vals[MULTS.index(1.0)]
        top = vals[-1]
        shape = ("CLIMBS" if top - base > 0.15 else
                 "flat  " if top - base < 0.05 else "mild  ")
        print(f"{c:16s}" + "".join(f"{v:8.3f}" for v in vals) + f"   {shape}")

    print(f"\nMARGIN by tol multiplier - the number that actually decides\n")
    print(f"{'clip':16s}" + "".join(f"{f'x{m}':>8s}" for m in MULTS))
    print("-" * (16 + 8 * len(MULTS)))
    for c in clips:
        vals = [next(r["margin"] for r in rows if r["clip"] == c and r["mult"] == m)
                for m in MULTS]
        print(f"{c:16s}" + "".join(f"{v:+8.3f}" for v in vals))
    print("-" * (16 + 8 * len(MULTS)))
    print(f"{'median':16s}" + "".join(
        f"{np.median([r['margin'] for r in rows if r['mult'] == m]):+8.3f}"
        for m in MULTS))
    print(f"{'wins':16s}" + "".join(
        f"{sum(1 for r in rows if r['mult'] == m and r['margin'] > 0):5d}/{len(clips):<2d}"
        for m in MULTS))
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
