"""physics_fill_probe.py — does physics beat interpolation on the BLIND frames? (E4)

The honest test before building the gray-box predictor. On a calibrated gold clip,
for every hit->bounce flight we:
  1. fit the striker-launch drag+Magnus arc (the parts we already have) using ONLY
     the DETECTED points in that flight,
  2. simulate it and project to image at every frame (incl. the blind ones),
and compare, on the human-labelled frames inside the flight, three fills against
the human click:

  raw       the detector's own lock (None on blind frames)
  interp    smooth_and_fill over the image track (today's shipped fill)
  physics   the striker-anchored ballistic prediction

The decisive number is the error on BLIND gold frames (detector saw nothing) —
that is exactly what a physics fill is supposed to recover. If physics beats
interp there, the gray-box approach is proven and we scale it; if not, we learn
why before training anything.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\physics_fill_probe.py \\
      --cache ..\\data\\output\\fps\\rally2_ballnet.perception.json \\
      --keypoints ..\\data\\yt_rally2_pts.json --labels ..\\data\\gold\\yt_rally2.labels.json
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
from tennis_tracker.bridge import (camera_from_court_corners,  # noqa: E402
                                   launch_from_striker, fit_launch_anchored)
from tennis_tracker.physics import simulate                   # noqa: E402

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def to_framework_xy(court_xy):
    # mirror of swingvision.speedspin._to_framework_xy
    return (float(court_xy[1]), 5.485 - float(court_xy[0]))


def build_court_track(ball_px, H, fps):
    """image ball_px -> (t, x, y) court-metre track, pipeline-style."""
    import swingvision.ball as bm
    n = len(ball_px)
    bp = bm.remove_outliers(ball_px, max_jump=1280 * 0.06)
    bp = bm.rectify_track(bp, max_speed_px=3000.0 / fps, resid_px=35.0)
    raw = []
    for p in bp:
        if p is None:
            raw.append(None); continue
        x, y = calibration.image_to_court(H, [p])[0]
        raw.append([float(x), float(y)] if
                   (-2.5 <= x <= court.DOUBLES_WIDTH + 2.5 and -2.5 <= y <= court.LENGTH + 2.5)
                   else None)
    raw = bm.cap_court_jumps(raw, max_step_m=84.0 / fps)
    sm = smooth_and_fill(raw, window=7, polyorder=2)
    return [(i / fps, float(sm[i, 0]), float(sm[i, 1])) for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_ballnet.perception.json"))
    ap.add_argument("--keypoints", default=str(REPO / "data/yt_rally2_pts.json"))
    ap.add_argument("--labels", default=str(REPO / "data/gold/yt_rally2.labels.json"))
    ap.add_argument("--hfov", type=float, default=93.46)
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--max-reproj", type=float, default=15.0,
                    help="only fill from arcs whose physics fit reprojects within "
                         "this (px) — a real single flight fits tight; a mis-paired "
                         "multi-bounce span does not and must not be filled")
    ap.add_argument("--max-flight-s", type=float, default=1.1,
                    help="reject 'arcs' longer than a plausible single flight")
    ap.add_argument("--json-out", default=None)
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

    # events, exactly as the pipeline builds them
    track = build_court_track(ball_px, H, args.fps)
    gaps = events.ball_player_gap(ball_px, cache.get("near_kpts") or [],
                                  cache.get("far_kpts") or [], n)
    hits = events.drop_midflight_hits(events.detect_hits_hybrid(gaps, track), track)
    bounces = events.detect_bounces_between_hits(ball_px, hits, n, track=track)

    # arcs: hit -> first bounce after it, within a plausible single-flight span
    hset = sorted(hits); bset = sorted(bounces)
    arcs = []
    for k, h in enumerate(hset):
        nxt = hset[k + 1] if k + 1 < len(hset) else n - 1
        cand = [b for b in bset if h + 4 <= b <= nxt
                and (b - h) / args.fps <= args.max_flight_s]
        if cand:
            arcs.append((h, cand[0]))
    print(f"{len(hits)} hits, {len(bounces)} bounces, {len(arcs)} hit->bounce arcs; "
          f"{len(gold)} gold ball frames")

    # per-frame physics prediction over each arc
    phys = {}      # frame -> (u,v)
    fitted_arcs = 0
    for (h, b) in arcs:
        a = h + 2
        seg = ball_px[a:b + 1]
        # Match speedspin exactly: anchor the launch at frame a (=h+2, t=0), so
        # p0 and the time origin agree. Requires frame a to be detected.
        if not seg or seg[0] is None:
            continue
        idx = [k for k, p in enumerate(seg) if p is not None]
        if len(idx) < 4:
            continue
        # striker = the player closest to the ball (court metres) at the hit
        best = None
        bx, by = calibration.image_to_court(H, [seg[0]])[0]
        for cl in (near_c, far_c):
            p = cl[h] if h < len(cl) and cl[h] is not None else None
            if p is None:
                continue
            d = math.hypot(bx - p[0], by - p[1])
            if best is None or d < best[1]:
                best = (p, d)
        if best is None:
            continue
        striker_xy = to_framework_xy(best[0])
        bounce_uv = seg[idx[-1]]
        p_launch, miss = launch_from_striker(camera, seg[0], striker_xy)
        if p_launch is None or miss > 2.5 or not 0.0 <= p_launch[2] <= 4.0:
            continue
        times = np.array(idx, float) / args.fps       # idx[0] == 0 (seg[0] detected)
        uv = np.array([seg[k] for k in idx], float)
        try:
            _, reproj, (P0, V0, OM) = fit_launch_anchored(
                times, uv, camera, Hfw, p_launch, bounce_uv)
        except Exception:
            continue
        # Only fill from a fit that actually matches the ball it CAN see. A tight
        # reproj means the single-flight physics is right and its blind-frame
        # prediction is trustworthy; a loose one means this "arc" is not one
        # physical flight and filling it would draw the ball in the wrong place.
        if reproj > args.max_reproj:
            continue
        fitted_arcs += 1
        # project the fitted flight at EVERY frame in [a..b]
        all_t = np.arange(0, b - a + 1, dtype=float) / args.fps
        tr = simulate(P0, V0, OM, dt=2e-3, t_max=float(all_t[-1]) + 0.05, bounces=0)
        proj = camera.project(tr.sample(all_t))
        for k in range(len(all_t)):
            phys[a + k] = (float(proj[k, 0]), float(proj[k, 1]))

    # interp fill (image space), same as pipeline's smooth_and_fill on ball_px
    interp = smooth_and_fill(ball_px, window=7, polyorder=2)

    # Score all three fills on the SAME frames — the ones the gated physics fill
    # actually covers — so interp and physics are compared apples-to-apples.
    res = {m: {"blind": [], "seen": []} for m in ("raw", "interp", "physics")}
    for f, v in gold.items():
        if f not in phys or f >= n:
            continue
        truth = (v["x"], v["y"])
        blind = ball_px[f] is None
        key = "blind" if blind else "seen"
        if ball_px[f] is not None:
            res["raw"][key].append(math.dist(ball_px[f], truth))
        if np.isfinite(interp[f]).all():
            res["interp"][key].append(math.dist(interp[f], truth))
        if f in phys:
            res["physics"][key].append(math.dist(phys[f], truth))

    def stat(errs):
        if not errs:
            return "   –  (n=0)"
        e = np.array(errs)
        return (f"med {np.median(e):5.1f}px  mean {e.mean():5.1f}px  "
                f"hit@10 {100*(e<=10).mean():4.0f}%  (n={len(e)})")

    print(f"\nfitted {fitted_arcs}/{len(arcs)} arcs; physics covers {len(phys)} frames\n")
    print("BLIND gold frames inside a flight (the decisive test — detector saw nothing):")
    for m in ("interp", "physics"):
        print(f"  {m:<8} {stat(res[m]['blind'])}")
    print("\nDETECTED gold frames inside a flight (fit-quality reference):")
    for m in ("raw", "interp", "physics"):
        print(f"  {m:<8} {stat(res[m]['seen'])}")

    if args.json_out:
        out = {m: {k: [round(x, 2) for x in res[m][k]] for k in res[m]} for m in res}
        Path(args.json_out).write_text(json.dumps(
            {"cache": Path(args.cache).name, "n_arcs": len(arcs),
             "fitted_arcs": fitted_arcs, "phys_frames": len(phys), "errors": out},
            indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
