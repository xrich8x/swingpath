"""eval/behind_camera.py - is `_ori_detail` scoring points BEHIND the camera?

Fell out of eval/evid_band_sweep.py, which reported n_seen = 10 of 10 court lines
"geometrically in frame" on every one of the 10 human-calibrated clips - including
`am_hard_utr`, a 1.74 m mount whose own audit says it measures 7.5 m of the court's
23.77 m and does not reach the net. All ten lines cannot be in that frame.

THE SUSPECTED MECHANISM
-----------------------
`calibration._apply` projects with `out[:, :2] / out[:, 2:3]` and never checks the
SIGN of the homogeneous coordinate. A court point beyond the camera's horizon has
w < 0, and dividing by a negative w mirrors it back through the principal point -
straight into the frame, at a plausible-looking pixel. `_ori_detail`'s bounds test

    inb = (x >= 0) & (x < w) & (y >= 0) & (y < h)

then counts it as an in-frame sample of a model line.

If that is happening it is a REAL and better-aimed candidate than the evidence band,
because it is asymmetric in exactly the direction that hurts:

  * those phantom samples can never have paint on them, so they land in the
    DENOMINATOR of `agree` and never in the numerator;
  * they appear when the far half of the court is beyond the horizon, i.e. on LOW
    MOUNTS - the amateur framing this project exists for;
  * so the true court on a low camera is scored against a denominator inflated with
    samples that are geometrically incapable of being supported.

WHAT IS MEASURED
----------------
At the HUMAN court on each calibrated clip: how many samples sit behind the camera,
how many of the 10 lines are genuinely observable once they are dropped, and what
`agree` becomes when the denominator is corrected. Reported as a margin against the
same coarse-grid distractors the rest of the harness uses, because a level that
rises without the margin rising is a wrong-court lever.

Sign convention: a homography is defined up to scale, so w > 0 means nothing on its
own. It is normalised here against the court centre, which is in front of the camera
in any view that shows a court at all.

    backend/.venv/Scripts/python.exe eval/behind_camera.py
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

from swingvision.courtfit import DBL  # noqa: E402

WRONG_PX_640 = 20.0


def _w_sign(H, pts):
    """Homogeneous w for each court point, sign-normalised so that +ve is in front
    of the camera (calibrated against the court centre, which always is)."""
    hom = np.column_stack([np.asarray(pts, float), np.ones(len(pts))])
    w = (H @ hom.T).T[:, 2]
    c = (H @ np.array([5.485, 11.885, 1.0]))[2]
    return w if c >= 0 else -w


def detail_fixed(H, calibration, court, dt, cos2, sin2, w, h, tol, athr, cf,
                 require_front: bool):
    """`_ori_detail`, with the option of dropping behind-camera samples.

    Deliberately a copy of the shipped function rather than a call into it: the fix
    under test is one term inside `inb`, and there is no way to reach that term from
    outside. Everything else is line-for-line the same so the comparison is honest."""
    S, lid, EA, EB = cf._court_samples(court)
    P = calibration.court_to_image(H, S)
    pa = calibration.court_to_image(H, EA)
    pb = calibration.court_to_image(H, EB)
    ang = np.arctan2(pb[:, 1] - pa[:, 1], pb[:, 0] - pa[:, 0])
    c2, s2 = np.cos(2 * ang)[lid], np.sin(2 * ang)[lid]
    x, y = np.round(P[:, 0]).astype(int), np.round(P[:, 1]).astype(int)
    inb = (x >= 0) & (x < w) & (y >= 0) & (y < h)
    front = _w_sign(H, S) > 0
    if require_front:
        inb = inb & front
    if int(inb.sum()) < len(P) * 0.30:
        return 0.0, 0, 0, float((~front).mean())
    xi, yi = np.clip(x, 0, w - 1), np.clip(y, 0, h - 1)
    align = cos2[yi, xi] * c2 + sin2[yi, xi] * s2
    d = dt[yi, xi]
    sup = inb & (d <= tol) & (align >= athr)
    near = inb & (d <= tol * cf.EVID_BAND)
    nL = int(lid.max()) + 1
    inb_cnt = np.bincount(lid, weights=inb.astype(float), minlength=nL)
    sup_cnt = np.bincount(lid, weights=sup.astype(float), minlength=nL)
    near_cnt = np.bincount(lid, weights=near.astype(float), minlength=nL)
    seen = inb_cnt >= 3
    ev = seen & (near_cnt / np.maximum(inb_cnt, 1) >= cf.EVID_MIN)
    if not ev.any():
        return 0.0, 0, 0, float((~front).mean())
    agree = float(sup_cnt[ev].sum()) / float(max(1.0, inb_cnt[ev].sum()))
    return agree, int(ev.sum()), int(seen.sum()), float((~front).mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from run_refs import references, frames_from

    print(f"at the HUMAN court, {a.frames} frames per clip. 'behind' = share of the "
          f"court's own sample points that project from BEHIND the camera.\n")
    print(f"{'clip':16s} {'behind':>7s} {'lines':>11s} {'g shipped':>10s} "
          f"{'g front':>8s} {'d g':>7s} | {'m shipped':>10s} {'m front':>8s} {'d m':>7s}")
    print("-" * 92)

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

            g0, _e0, s0, beh = detail_fixed(Ht, calibration, court, dt, cos2, sin2,
                                            w, h, tol, 0.80, cf, False)
            g1, _e1, s1, _b = detail_fixed(Ht, calibration, court, dt, cos2, sin2,
                                           w, h, tol, 0.80, cf, True)

            ax = [np.asarray(v) * (w if i in (0, 3, 4) else h)
                  for i, v in enumerate(cf.COARSE_GRID)]
            b0 = b1 = 0.0
            for cx, yn, yf, wn, wf in itertools.product(*ax):
                c = cf._corners(cx, yn, yf, wn, wf)
                cand = np.array([c[n] for n in DBL], float)
                if float(np.mean(np.hypot(*(cand - txy).T))) * scale <= WRONG_PX_640:
                    continue
                try:
                    Hw = calibration.compute_homography(cpts, [c[n] for n in DBL])
                except Exception:
                    continue
                b0 = max(b0, detail_fixed(Hw, calibration, court, dt, cos2, sin2,
                                          w, h, tol, 0.80, cf, False)[0])
                b1 = max(b1, detail_fixed(Hw, calibration, court, dt, cos2, sin2,
                                          w, h, tol, 0.80, cf, True)[0])
            per.append((beh, s0, s1, g0, g1, g0 - b0, g1 - b1))
        if not per:
            continue
        m = np.median(np.array(per, float), axis=0)
        rows.append({"clip": clip, "behind": m[0], "seen_shipped": m[1],
                     "seen_front": m[2], "g_shipped": m[3], "g_front": m[4],
                     "margin_shipped": m[5], "margin_front": m[6]})
        print(f"{clip:16s} {m[0]*100:6.1f}% {m[1]:4.0f} -> {m[2]:<4.0f} "
              f"{m[3]:10.3f} {m[4]:8.3f} {m[4]-m[3]:+7.3f} | "
              f"{m[5]:+10.3f} {m[6]:+8.3f} {m[6]-m[5]:+7.3f}", flush=True)

    if not rows:
        return
    print("-" * 92)
    dg = float(np.median([r["g_front"] - r["g_shipped"] for r in rows]))
    dm = float(np.median([r["margin_front"] - r["margin_shipped"] for r in rows]))
    won = sum(1 for r in rows if r["margin_front"] > r["margin_shipped"])
    lost = sum(1 for r in rows if r["margin_front"] < r["margin_shipped"])
    print(f"median behind-camera share {np.median([r['behind'] for r in rows])*100:.1f}%"
          f"   median d g {dg:+.3f}   median d MARGIN {dm:+.3f}   "
          f"margin up on {won}, down on {lost} of {len(rows)}")
    above = sum(1 for r in rows if r["g_front"] >= 0.33)
    was = sum(1 for r in rows if r["g_shipped"] >= 0.33)
    print(f"true court clears the 0.33 accept gate on {was} -> {above} of {len(rows)} clips")
    print("\nThe MARGIN column decides this, not g. A fix that lifts the truth and the\n"
          "wrong courts equally has bought a higher number and no more separation.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
