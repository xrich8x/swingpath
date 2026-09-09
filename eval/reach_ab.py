"""eval/reach_ab.py - did 4a33635's 6x refiner reach at 4K cost shell any court?

ONE VARIABLE. `autodetect` bounds each candidate's corner refinement to
`max_move_px`. Commit 4a33635 changed that bound from an absolute 55.0 px to
`55.0 * (w / 640.0)`, which is an EXACT no-op on the 640-wide gold gate and a 6x
LOOSENING on the 3840-wide indoor-shell clips - which are not in the gate pool, so
a shell-only effect was invisible to that commit's own control.

  ARM A  shipped      max_move_px = 55.0 * (w/640) = 330.0 px at 3840
  ARM B  pre-4a33635  max_move_px = 55.0            (absolute, as it was)

Both arms run on the SAME decoded frames of the SAME clips, through the same
snap_to_lines(min_coverage=0.0, max_move_px=60) and the same lock_quad and the same
consensus - `auto_fit_frame` is called unmodified in both.

HOW ARM B IS PRODUCED WITHOUT EDITING SHIPPED CODE. `calibration.refine_homography_
bounded` is wrapped, and the wrapper rewrites `max_move_px` ONLY when the incoming
value equals 55.0*(w/640) to within 1e-6 - i.e. only the autodetect call this commit
touched. `snap_to_lines`' own 60.0 px call, and every other caller, pass through
untouched. `n_rewrites` is reported per clip: it must be 0 in arm A and > 0 in arm B,
otherwise the A/B did not happen and the run is void.

TRUTH IS HUMAN ONLY - the `_exact` calibrations in data/<clip>_pts.json, via
eval/run_refs.references(). The error metric and the 20 px@640 accept band are
IMPORTED from eval/candidate_audit.py, not re-implemented, so these numbers mean the
same thing as qa's proposal-recall run of 2026-09-09.

    backend/.venv/Scripts/python.exe eval/reach_ab.py --shell --k 8 \
        --json data/output/reach_ab_shell.json
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

SHELL = ["flexi_franz_p01", "flexi_franz_p07", "flexi_joy_p01", "flexi_joy_p07",
         "hillsborough_p02", "hillsborough_p08", "mpc_mixed_p02", "mpc_mixed_p08",
         "mpc_tuesday_p01", "mpc_tuesday_p07"]

SHIPPED_REACH = 55.0          # the constant, at the 640-wide anchor it was tuned on
ANCHOR_W = 640.0


def _patch_reach(calibration, absolute: bool, counter):
    """Return a restore fn. `absolute=True` reverts ONLY autodetect's reach to 55.0."""
    orig = calibration.refine_homography_bounded

    def wrapped(frame, named_points, max_move_px=35.0, *a, **kw):
        w = frame.shape[1]
        scaled = SHIPPED_REACH * (w / ANCHOR_W)
        if abs(max_move_px - scaled) < 1e-6:
            counter["autodetect_calls"] += 1
            if absolute:
                counter["n_rewrites"] += 1
                max_move_px = SHIPPED_REACH
        else:
            counter["other_calls"] += 1
        return orig(frame, named_points, max_move_px, *a, **kw)

    calibration.refine_homography_bounded = wrapped
    return lambda: setattr(calibration, "refine_homography_bounded", orig)


def _arm(frames, truth, scale, absolute):
    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from candidate_audit import _err_640, WRONG_PX_640

    counter = {"autodetect_calls": 0, "other_calls": 0, "n_rewrites": 0}
    restore = _patch_reach(calibration, absolute, counter)
    t0 = time.time()
    try:
        fits = [cf.auto_fit_frame(im, calibration, court) for _p, im in frames]
    finally:
        restore()
    locked = [i for i, f in enumerate(fits) if f]
    errs = {i: _err_640(truth, fits[i], calibration, court, scale) for i in locked}
    vals = sorted(e for e in errs.values() if e is not None)
    good = [i for i in locked if errs[i] is not None and errs[i] <= WRONG_PX_640]
    pts, votes = cf.consensus(fits)
    cons = (_err_640(truth, pts, calibration, court, scale)
            if pts is not None else None)
    return {"locked": len(locked), "n_good": len(good),
            "best_err": (vals[0] if vals else None), "errs": vals,
            "votes": int(votes), "cons_err": cons,
            "reach_px": (SHIPPED_REACH if absolute
                         else SHIPPED_REACH * (frames[0][1].shape[1] / ANCHOR_W)),
            "secs": round(time.time() - t0, 1), **counter}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--shell", action="store_true", help="the 10 indoor-shell clips")
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from run_refs import references, frames_from
    from swingvision.courtfit import DBL

    want = set(a.clips or []) | (set(SHELL) if a.shell else set())
    refs = [r for r in references() if not want or r[0] in want]
    print(f"{len(refs)} clips, k={a.k}; ARM A = shipped 55*(w/640), "
          f"ARM B = pre-4a33635 absolute 55\n", flush=True)

    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        head = "?"
    import cv2
    stamp = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "commit": head, "cv2": cv2.__version__, "k": a.k,
             "python": platform.python_version(), "machine": platform.node(),
             "metric": "candidate_audit._err_640, accept 20.0 px@640",
             "truth": "human _exact data/<clip>_pts.json via run_refs.references()"}
    print(json.dumps(stamp), flush=True)

    rows = []
    hdr = (f"{'clip':17s} {'w':>5s} | {'A lock':>6s} {'A good':>6s} {'A best':>7s} "
           f"{'A vote':>6s} | {'B lock':>6s} {'B good':>6s} {'B best':>7s} {'B vote':>6s}")
    print("\n" + hdr)
    print("-" * len(hdr), flush=True)
    for clip, pts_path, vid in refs:
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        truth = {n: v for n, v in ref.items() if not n.startswith("_")}
        if not all(n in truth for n in DBL):
            print(f"{clip:17s} skipped: incomplete corners", flush=True)
            continue
        frames = frames_from(Path(vid), a.k)
        if not frames:
            print(f"{clip:17s} skipped: no frames", flush=True)
            continue
        h, w = frames[0][1].shape[:2]
        scale = 640.0 / w
        A = _arm(frames, truth, scale, absolute=False)
        B = _arm(frames, truth, scale, absolute=True)
        del frames
        row = {"clip": clip, "w": w, "h": h, "frames": a.k,
               "mount_m": ref.get("_audit", {}).get("camera_height_m"),
               "A_shipped_scaled": A, "B_absolute_55": B}
        rows.append(row)

        def f(v, n=1):
            return "-" if v is None else f"{v:.{n}f}"
        print(f"{clip:17s} {w:5d} | {A['locked']:6d} {A['n_good']:6d} "
              f"{f(A['best_err']):>7s} {A['votes']:6d} | {B['locked']:6d} "
              f"{B['n_good']:6d} {f(B['best_err']):>7s} {B['votes']:6d}", flush=True)
        if a.json:
            Path(a.json).write_text(json.dumps(
                {"stamp": stamp, "rows": rows}, indent=1), encoding="utf-8")

    # ---- the pre-registered summary
    nA = sum(1 for r in rows if r["A_shipped_scaled"]["n_good"] > 0)
    nB = sum(1 for r in rows if r["B_absolute_55"]["n_good"] > 0)
    recA = {r["clip"].rsplit("_p", 1)[0] for r in rows
            if r["A_shipped_scaled"]["n_good"] > 0}
    recB = {r["clip"].rsplit("_p", 1)[0] for r in rows
            if r["B_absolute_55"]["n_good"] > 0}
    nolockA = [r["clip"] for r in rows if r["A_shipped_scaled"]["locked"] == 0]
    nolockB = [r["clip"] for r in rows if r["B_absolute_55"]["locked"] == 0]
    print(f"\nreaches truth: A {nA}/{len(rows)} clips ({len(recA)} recordings "
          f"{sorted(recA)}) | B {nB}/{len(rows)} ({len(recB)} recordings {sorted(recB)})")
    print(f"no lock at all: A {nolockA} | B {nolockB}")
    gained = [r["clip"] for r in rows
              if r["B_absolute_55"]["n_good"] > 0 and r["A_shipped_scaled"]["n_good"] == 0]
    lost = [r["clip"] for r in rows
            if r["A_shipped_scaled"]["n_good"] > 0 and r["B_absolute_55"]["n_good"] == 0]
    print(f"B gains: {gained or '-'}   B loses: {lost or '-'}")
    tot_rw = sum(r["B_absolute_55"]["n_rewrites"] for r in rows)
    tot_a = sum(r["A_shipped_scaled"]["n_rewrites"] for r in rows)
    print(f"reach rewrites: arm A {tot_a} (must be 0), arm B {tot_rw} (must be > 0)")
    if a.json:
        Path(a.json).write_text(json.dumps({"stamp": stamp, "rows": rows}, indent=1),
                                encoding="utf-8")
        print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
