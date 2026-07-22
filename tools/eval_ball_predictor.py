"""eval_ball_predictor.py — does the learned launch net beat least-squares + interp? (E4b)

The honest test of the gray-box net. On a calibrated gold clip, for each
hit->bounce flight we feed the observed (sparse, noisy) 2D track to SpinNet, get
the predicted launch state (v0, spin, p0), simulate it forward, project to image,
and compare against the human clicks on the flight frames — versus:
  interp    smooth_and_fill (today's shipped fill)
  lsq       the least-squares striker-anchored physics fit (the E4 baseline that lost)

`--p0 striker` overrides the net's launch POSITION with the pose-derived striker
launch (hybrid gray-box: learned velocity/spin, geometric launch point), which
the literature and E1 both argue is the better-constrained split.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\eval_ball_predictor.py \\
     --weights runs/ballpred_rally2/best.pt --p0 striker
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

import torch                                                  # noqa: E402
from swingvision import calibration, court, events            # noqa: E402
from swingvision.ball import smooth_and_fill                  # noqa: E402
from tennis_tracker.bridge import (camera_from_court_corners,  # noqa: E402
                                   launch_from_striker, fit_launch_anchored)
from tennis_tracker.physics import simulate                   # noqa: E402
from tennis_tracker.estimation.spin_net import SpinNet, make_features  # noqa: E402
from physics_fill_probe import build_court_track, to_framework_xy, CORNERS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_ballnet.perception.json"))
    ap.add_argument("--keypoints", default=str(REPO / "data/yt_rally2_pts.json"))
    ap.add_argument("--labels", default=str(REPO / "data/gold/yt_rally2.labels.json"))
    ap.add_argument("--weights", required=True)
    ap.add_argument("--p0", choices=["net", "striker"], default="striker")
    ap.add_argument("--hfov", type=float, default=93.46)
    ap.add_argument("--fps", type=float, default=60.0)
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

    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = SpinNet().to(device)
    net.load_state_dict(torch.load(args.weights, map_location=device)["model"])
    net.eval()

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

    interp = smooth_and_fill(ball_px, window=7, polyorder=2)
    err = {m: {"seen": [], "blind": []} for m in ("net", "lsq", "interp")}
    used = 0
    for (h, b) in arcs:
        a = h + 2
        seg = ball_px[a:b + 1]
        if not seg or seg[0] is None:
            continue
        idx = [k for k, p in enumerate(seg) if p is not None]
        if len(idx) < 5:
            continue
        # net prediction from the observed sparse track
        uv_arc = np.full((len(seg), 2), np.nan)
        for k in idx:
            uv_arc[k] = seg[k]
        feat, nlen = make_features(uv_arc, max_len=max(80, len(seg)))
        with torch.no_grad():
            pred = net(torch.from_numpy(feat)[None].to(device),
                       torch.tensor([nlen]).to(device))
        v0 = pred["v0"][0].cpu().numpy()
        omega = pred["omega"][0].cpu().numpy()
        p0_net = pred["p0"][0].cpu().numpy()

        # striker launch (for the hybrid p0 and the lsq baseline)
        bx, by = calibration.image_to_court(H, [seg[0]])[0]
        best = None
        for cl in (near_c, far_c):
            p = cl[h] if h < len(cl) and cl[h] is not None else None
            if p is None:
                continue
            d = math.hypot(bx - p[0], by - p[1])
            if best is None or d < best[1]:
                best = (p, d)
        p_launch = None
        if best is not None:
            p_launch, miss = launch_from_striker(camera, seg[0], to_framework_xy(best[0]))
            if p_launch is not None and (miss > 2.5 or not 0.0 <= p_launch[2] <= 4.0):
                p_launch = None

        p0 = p_launch if (args.p0 == "striker" and p_launch is not None) else p0_net
        all_t = np.arange(0, b - a + 1, dtype=float) / args.fps
        tr = simulate(p0, v0, omega, dt=2e-3, t_max=float(all_t[-1]) + 0.05, bounces=0)
        proj_net = camera.project(tr.sample(all_t))

        # lsq baseline (only if striker launch available)
        proj_lsq = None
        if p_launch is not None:
            times = np.array(idx, float) / args.fps
            uvd = np.array([seg[k] for k in idx], float)
            try:
                _, _, (P0, V0, OM) = fit_launch_anchored(times, uvd, camera, Hfw,
                                                         p_launch, seg[idx[-1]])
                trl = simulate(P0, V0, OM, dt=2e-3, t_max=float(all_t[-1]) + 0.05, bounces=0)
                proj_lsq = camera.project(trl.sample(all_t))
            except Exception:
                pass

        used += 1
        for f, v in gold.items():
            k = f - a
            if k < 0 or k >= len(all_t):
                continue
            truth = (v["x"], v["y"])
            key = "blind" if ball_px[f] is None else "seen"
            err["net"][key].append(math.dist(proj_net[k], truth))
            if proj_lsq is not None:
                err["lsq"][key].append(math.dist(proj_lsq[k], truth))
            if f < n and np.isfinite(interp[f]).all():
                err["interp"][key].append(math.dist(interp[f], truth))

    def stat(e):
        if not e:
            return "     –  (n=0)"
        a = np.array(e)
        return f"med {np.median(a):6.1f}px  hit@10 {100*(a<=10).mean():4.0f}%  hit@25 {100*(a<=25).mean():4.0f}%  (n={len(a)})"

    print(f"p0={args.p0}; {used} flights scored\n")
    for key in ("seen", "blind"):
        print(f"[{key} gold frames inside a flight]")
        for m in ("net", "lsq", "interp"):
            print(f"   {m:<7} {stat(err[m][key])}")
        print()


if __name__ == "__main__":
    main()
