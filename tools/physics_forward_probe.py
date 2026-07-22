"""physics_forward_probe.py — predict the flight FORWARD from how it was hit (E4).

physics_fill_probe showed the fit-to-both-ends approach is accurate on a genuine
single flight (~3 px) but can't reach the blind FAR frames — because it anchors
on the far bounce we cannot see. This tests the user's actual idea and the
gray-box literature's method: pin the launch from the striker (pose), fit the
initial velocity+spin from ONLY the first well-observed (near-court, big-ball)
frames after the hit, then SIMULATE FORWARD through the blind far frames — no far
anchor needed. Score the prediction against the human clicks on the LATER frames,
split near vs far, to see how far ahead the physics stays true.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\physics_forward_probe.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ball_physics"))
sys.path.insert(0, str(REPO / "tools"))

from swingvision import calibration, court, events            # noqa: E402
from swingvision.ball import smooth_and_fill                  # noqa: E402
from tennis_tracker.bridge import camera_from_court_corners, launch_from_striker  # noqa: E402
from tennis_tracker.estimation.trajectory_fit import fit_arc  # noqa: E402
from tennis_tracker.physics import simulate                   # noqa: E402
from physics_fill_probe import build_court_track, to_framework_xy, CORNERS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_ballnet.perception.json"))
    ap.add_argument("--keypoints", default=str(REPO / "data/yt_rally2_pts.json"))
    ap.add_argument("--labels", default=str(REPO / "data/gold/yt_rally2.labels.json"))
    ap.add_argument("--hfov", type=float, default=93.46)
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--fit-s", type=float, default=0.20,
                    help="seconds of early flight to fit the launch velocity from")
    ap.add_argument("--max-flight-s", type=float, default=1.1)
    args = ap.parse_args()

    cache = json.loads(Path(args.cache).read_text(encoding="utf-8"))
    ball_px = cache["ball_px"]
    near_c = cache.get("near_court") or []
    far_c = cache.get("far_court") or []
    n = len(ball_px)
    kp = json.loads(Path(args.keypoints).read_text(encoding="utf-8"))
    H = calibration.compute_homography([court.LANDMARKS[c] for c in CORNERS],
                                       [kp[c] for c in CORNERS])
    camera, Hfw = camera_from_court_corners({c: kp[c] for c in CORNERS},
                                            (1280, 720), hfov_deg=args.hfov)
    gold = {int(k): v for k, v in json.loads(Path(args.labels).read_text(encoding="utf-8"))["labels"].items()
            if v.get("ball") and not v.get("unsure")}

    track = build_court_track(ball_px, H, args.fps)
    gaps = events.ball_player_gap(ball_px, cache.get("near_kpts") or [],
                                  cache.get("far_kpts") or [], n)
    hits = events.drop_midflight_hits(events.detect_hits_hybrid(gaps, track), track)
    bounces = events.detect_bounces_between_hits(ball_px, hits, n, track=track)
    hset, bset = sorted(hits), sorted(bounces)
    arcs = []
    for k, h in enumerate(hset):
        nxt = hset[k + 1] if k + 1 < len(hset) else n - 1
        cand = [b for b in bset if h + 4 <= b <= nxt and (b - h) / args.fps <= args.max_flight_s]
        if cand:
            arcs.append((h, cand[0]))

    fit_frames = int(round(args.fit_s * args.fps))
    interp = smooth_and_fill(ball_px, window=7, polyorder=2)
    # error buckets: predicted frames beyond the fit window, split near/far by image y
    err = {"phys": {"near": [], "far": []}, "interp": {"near": [], "far": []}}
    n_arcs_fit = 0
    for (h, b) in arcs:
        a = h + 2
        seg = ball_px[a:b + 1]
        if not seg or seg[0] is None:
            continue
        idx = [k for k, p in enumerate(seg) if p is not None]
        fit_idx = [k for k in idx if k <= fit_frames]
        if len(fit_idx) < 4:
            continue
        bx, by = calibration.image_to_court(H, [seg[0]])[0]
        best = None
        for cl in (near_c, far_c):
            p = cl[h] if h < len(cl) and cl[h] is not None else None
            if p is None:
                continue
            d = math.hypot(bx - p[0], by - p[1])
            if best is None or d < best[1]:
                best = (p, d)
        if best is None:
            continue
        p_launch, miss = launch_from_striker(camera, seg[0], to_framework_xy(best[0]))
        if p_launch is None or miss > 2.5 or not 0.0 <= p_launch[2] <= 4.0:
            continue
        # fit v0, omega with p0 FIXED at the striker launch, on the early frames only
        t_fit = np.array(fit_idx, float) / args.fps
        uv_fit = np.array([seg[k] for k in fit_idx], float)
        try:
            fit = fit_arc(t_fit, uv_fit, camera=camera, p0_init=np.asarray(p_launch, float),
                          fix_p0=True, physical_bounds=True)
        except Exception:
            continue
        # sanity: the fit must reproject the EARLY window tightly, else skip
        tr0 = simulate(fit.p0, fit.v0, fit.omega, dt=2e-3, t_max=float(t_fit[-1]) + 0.02, bounces=0)
        rep = float(np.sqrt(np.mean(np.sum((camera.project(tr0.sample(t_fit)) - uv_fit) ** 2, axis=1))))
        if rep > 8.0:
            continue
        n_arcs_fit += 1
        # simulate forward over the whole arc and score frames BEYOND the fit window
        all_t = np.arange(0, b - a + 1, dtype=float) / args.fps
        tr = simulate(fit.p0, fit.v0, fit.omega, dt=2e-3, t_max=float(all_t[-1]) + 0.05, bounces=0)
        proj = camera.project(tr.sample(all_t))
        for f, v in gold.items():
            k = f - a
            if k <= fit_frames or k < 0 or k >= len(all_t):
                continue
            truth = (v["x"], v["y"])
            region = "far" if v["y"] < 260 else "near"
            err["phys"][region].append(math.dist(proj[k], truth))
            if f < n and np.isfinite(interp[f]).all():
                err["interp"][region].append(math.dist(interp[f], truth))

    def stat(e):
        if not e:
            return "    –  (n=0)"
        a = np.array(e)
        return f"med {np.median(a):6.1f}px  hit@25 {100*(a<=25).mean():4.0f}%  (n={len(a)})"

    print(f"fit {args.fit_s:g}s early flight -> predict forward; {n_arcs_fit} arcs used\n")
    print("FORWARD-PREDICTED frames (beyond the fit window), vs human gold:")
    for region in ("near", "far"):
        print(f"  [{region} court]")
        print(f"     physics {stat(err['phys'][region])}")
        print(f"     interp  {stat(err['interp'][region])}")


if __name__ == "__main__":
    main()
