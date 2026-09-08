"""eval/proposer_rejects.py - WHERE the CourtNet-global arm dies, per frame.

`proposer_ab.py` reports that an arm did not lock. That is not a diagnosis: a
three-stage chain (GLOBAL proposal -> LOCAL snap -> 6-DOF lock) can die at any
stage, and the whole point of the ordering experiment is WHICH stage. So inspect
the rejects, not what survived:

  stage 0  detect_court_learned returned None  (no proposal at all)
  stage 1  a proposal exists - how far is it from the human court, at 640 px?
  stage 2  after the classical snap - did the local stage move it closer?
  stage 3  lock_quad refused (returned None) or kept it - and at what error?

Scored against the human `_exact` clicks, same reference as proposer_ab.py.

    backend/.venv/Scripts/python.exe eval/proposer_rejects.py --only am_hard_utr
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

os.environ.setdefault(
    "COURTNET_WEIGHTS", str(REPO / "backend" / "weights" / "court_detector.pt"))

import run_refs  # noqa: E402
from swingvision import calibration, court, courtfit  # noqa: E402
from swingvision.courtfit import DBL  # noqa: E402


def err640(named_ref, pts, w):
    if pts is None or not all(k in pts for k in DBL):
        return None
    Href = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [named_ref[n] for n in DBL])
    Hfit = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [pts[n] for n in DBL])
    e = float(np.mean([
        np.hypot(*(calibration.court_to_image(Href, [court.LANDMARKS[n]])[0]
                   - calibration.court_to_image(Hfit, [court.LANDMARKS[n]])[0]))
        for n in DBL]))
    return round(e * 640.0 / float(w), 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=run_refs.ACCEPT_K)
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=str(REPO / "eval" / "out" / "proposer_rejects.json"))
    a = ap.parse_args()

    print(f"weights resolved: {courtfit.resolved_courtnet_weights()}")
    refs = run_refs.references()
    if a.only:
        keep = set(a.only.split(","))
        refs = [r for r in refs if r[0] in keep]

    rows = []
    for clip, pts_path, vid in refs:
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        named_ref = {k: v for k, v in ref.items() if not k.startswith("_")}
        if not all(n in named_ref for n in DBL):
            continue
        frames = run_refs.frames_from(vid, a.k)
        if not frames:
            continue
        h, w = frames[0][1].shape[:2]
        per = []
        for _p, im in frames:
            prop, conf = courtfit._propose_courtnet(im, calibration, court)
            if prop is None:
                per.append({"stage": 0, "prop": None, "snap": None, "lock": None})
                continue
            _, out, _s, _c0, _c1 = calibration.snap_to_lines(
                im, prop, min_coverage=0.0, max_move_px=60.0)
            use = out if all(k in out for k in DBL) else prop
            locked = courtfit.lock_quad(use, calibration, court, w, h,
                                        dt=courtfit.line_distance_map(im, calibration))[0]
            per.append({"stage": 3 if locked is not None else 2,
                        "conf": round(conf, 3),
                        "prop": err640(named_ref, prop, w),
                        "snap": err640(named_ref, use, w),
                        "lock": err640(named_ref, locked, w)})
        n0 = sum(1 for x in per if x["stage"] == 0)
        n_lock = sum(1 for x in per if x["stage"] == 3)
        props = [x["prop"] for x in per if x["prop"] is not None]
        rows.append({"clip": clip, "surface": vid.parent.name, "frames": len(per),
                     "no_proposal": n0, "locked": n_lock,
                     "prop_err_median": None if not props else round(float(np.median(props)), 2),
                     "per_frame": per})
        print(f"{clip:22s} {vid.parent.name:10s} no_proposal={n0}/{len(per)} "
              f"locked={n_lock}/{len(per)} prop_err640_median={rows[-1]['prop_err_median']}",
              flush=True)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
