"""synth_truth.py — measure the measurement chain against EXACT ground truth.

WHY THIS EXISTS
---------------
Every accuracy number in this project is an AGREEMENT number. Ball recall is
agreement with human clicks; speed is agreement with 7 readings off a SwingVision
HUD. Agreement is the right currency for perception, where there is no other
truth — but the geometry and physics layers are closed-form, and for those we can
manufacture truth exactly.

Simulate a ball with a known launch velocity through the real drag+gravity+Magnus
model, project it through a REAL clip's camera calibration, add the pixel noise and
dropout our detector actually has, then run the SHIPPED measurement code on the
result and compare against the number we started from. No labels, no HUD, no human.

THE QUESTION IT ANSWERS
-----------------------
CLAUDE.md states, as a standing rule, that reported speed reads ~15-20% under a
radar gun because it is AVERAGE flight speed rather than LAUNCH speed, and that
this "must not be corrected". That is a physical argument, and it has never been
verified — the HUD comparison (n=7) cannot separate the causes.

There are three distinct reasons our number is below the launch speed, and this
tool separates them into an error budget:

  1. launch -> true average 3D speed   the ball DECELERATES (drag). Physics.
  2. true avg 3D -> true avg GROUND    analytics.shot_speed_kmh integrates path
                                       length in COURT METRES on the ground plane,
                                       so the vertical component is discarded.
                                       Geometry, and unavoidable from one camera.
  3. true avg ground -> our estimate   what calibration + detector noise + the
                                       z=0 flat-projection assumption actually cost.
                                       THE ONLY PART THAT IS OUR ERROR.

Only (3) is a defect. (1) and (2) are the definition of the quantity. Separating
them turns "don't correct the bias" from a belief into a measurement.

    cd backend && .venv-train/Scripts/python.exe ../tools/synth_truth.py \
        --keypoints ../data/yt_rally2_pts.json --n 400

Runs on CPU if torch has no CUDA; it is a few hundred short simulations.
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

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
MS_TO_KMH = 3.6


def line_distance_m(xy):
    """Distance from a court-frame bounce to the nearest edge of the IN region.

    A line call is only informative near a line. Pooled agreement is NOT: with
    any realistic launch distribution most bounces land well inside, so a metre
    of positional error still calls them correctly and the percentage saturates
    at ~100% for cameras that are visibly bad. Restricting to bounces within a
    short distance of a line is what separates them.

    The region is the singles court used by `analytics.is_in` for a groundstroke.
    """
    from swingvision import court
    x0, x1 = court.X_LEFT_SINGLES, court.X_RIGHT_SINGLES
    y0, y1 = court.Y_NEAR_BASELINE, court.Y_FAR_BASELINE
    x, y = float(xy[0]), float(xy[1])
    if x0 <= x <= x1 and y0 <= y <= y1:
        return min(x - x0, x1 - x, y - y0, y1 - y)      # inside: to nearest edge
    dx = max(x0 - x, 0.0, x - x1)
    dy = max(y0 - y, 0.0, y - y1)
    return math.hypot(dx, dy)


def to_court_xy(fw_xy):
    """tennis_tracker (physics) frame -> swingvision court frame, in metres.

    THE TWO FRAMES ARE NOT THE SAME, and conflating them is not a subtle error:
      swingvision   x = width  0..10.97, y = length 0..23.77, origin near-left
      tennis_tracker X = length 0..23.77, Y = width +5.485..-5.485 (to image LEFT),
                     origin at the near-baseline centre, +Z up so gravity works
    The simulator lives in the second; analytics.line_call and image_to_court live
    in the first. The first version of this tool compared a physics-frame bounce
    against a court-frame estimate and reported a 30 m median error on a 23.77 m
    court — absurd enough to catch, which is the only reason it was caught.

    Exact inverse of speedspin._to_framework_xy; asserted at startup so the pair
    cannot drift apart (that file already says "change both together").
    """
    return (5.485 - float(fw_xy[1]), float(fw_xy[0]))


def simulate(kp, hfov, w, h, n, fps, horizon_s, seed, truth_fps=None):
    """Known-truth flights, projected through the clip's real camera.

    `truth_fps` decouples the TRUTH grid from the MEASUREMENT grid, and it exists
    for one experiment: comparing frame rates. With truth sampled at the same fps
    being tested, `truth_of` interpolates the bounce between coarser samples at
    low fps, so the truth itself would be least accurate exactly where the
    measurement is — the comparison would flatter high frame rates for free.

    Set it to a multiple of every fps under test (240 covers 15/30/60/120/240):
    truth is then computed once on the fine grid and each fps is an exact
    DECIMATION of it, so the runs are strictly nested and perfectly paired.
    Returns the stride; it is 1 and the behaviour is unchanged when unset.
    """
    import torch
    from tennis_tracker.bridge import camera_from_court_corners
    from tennis_tracker.physics.simulator_torch import (
        project_batch, sample_at, simulate_batch)
    sys.path.insert(0, str(REPO / "tools"))
    from gen_synth_camera import draw_launch

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    cam, _ = camera_from_court_corners({c: kp[c] for c in CORNERS}, (w, h),
                                       hfov_deg=hfov)
    K = torch.tensor(cam.K, dtype=torch.float32, device=dev)
    R = torch.tensor(cam.R, dtype=torch.float32, device=dev)
    tc = torch.tensor(cam.t, dtype=torch.float32, device=dev)
    rng = np.random.default_rng(seed)

    grid_fps, stride = float(fps), 1
    if truth_fps:
        stride = int(round(float(truth_fps) / float(fps)))
        if stride < 1 or abs(truth_fps / stride - fps) > 1e-6:
            raise ValueError(f"truth_fps {truth_fps} is not an integer multiple "
                             f"of fps {fps} — decimation would not be exact")
        grid_fps = float(truth_fps)

    query = torch.arange(0, horizon_s, 1.0 / grid_fps, device=dev)
    v0, omega, p0 = draw_launch(rng, n)
    with torch.no_grad():
        pos, _, tg = simulate_batch(torch.tensor(p0, device=dev),
                                    torch.tensor(v0, device=dev),
                                    torch.tensor(omega, device=dev),
                                    n_steps=int(horizon_s / 2.5e-3), dt=2.5e-3)
        q = sample_at(pos, tg, query)                 # (B,T,3) true 3D, metres
        uv = project_batch(q, K, R, tc).cpu().numpy()  # (B,T,2) true pixels
    return q.cpu().numpy(), uv, query.cpu().numpy(), v0, rng, stride


def truth_of(xyz, t):
    """Exact quantities for one flight, from the simulated 3D path.

    The flight ends at the BOUNCE — the first downward crossing of z=0 — found by
    linear interpolation between the straddling samples rather than by taking the
    nearest frame, because at 60 fps a ball at 25 m/s moves 0.4 m per frame and
    rounding to a frame would put a fake 20 cm into the line call.
    """
    z = xyz[:, 2]
    idx = np.where((z[:-1] > 0) & (z[1:] <= 0))[0]
    if len(idx) == 0:
        return None
    i = int(idx[0])
    f = z[i] / (z[i] - z[i + 1])                       # 0..1 between i and i+1
    bounce = xyz[i] + f * (xyz[i + 1] - xyz[i])
    t_b = t[i] + f * (t[i + 1] - t[i])

    path = np.vstack([xyz[: i + 1], bounce])
    tt = np.append(t[: i + 1], t_b)
    dur = float(tt[-1] - tt[0])
    if dur <= 0:
        return None
    d3 = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
    d2 = float(np.sum(np.linalg.norm(np.diff(path[:, :2], axis=0), axis=1)))
    return {"i_bounce": i, "frac": f, "t_b": t_b,
            # converted out of the physics frame — see to_court_xy
            "bounce_xy": list(to_court_xy(bounce[:2])),
            "avg3d_kmh": d3 / dur * MS_TO_KMH,
            "avg_ground_kmh": d2 / dur * MS_TO_KMH,
            "dur_s": dur}


def measure(kp, *, hfov=93.46, width=1280, height=720, n=400, fps=30.0,
            horizon_s=2.0, pixel_noise=2.0, dropout=0.30, min_len=5,
            low_z=1.0, seed=0, truth_fps=None) -> list:
    """Simulate `n` flights through this calibration and MEASURE them our way.

    Returns one row per usable flight, each carrying the exact truth alongside
    our estimate. Split out of main() so a caller can sweep calibrations
    (tools/height_curve.py) without shelling out and re-importing torch per run.
    """
    from swingvision import analytics, calibration
    from swingvision.speedspin import _to_framework_xy

    # The frame pair is load-bearing: get it wrong and every bounce is metres
    # out while every speed still looks plausible. Check it, do not assume it.
    for probe in ((0.0, 0.0), (10.97, 23.77), (3.2, 11.885)):
        assert max(abs(a - b) for a, b in
                   zip(to_court_xy(_to_framework_xy(probe)), probe)) < 1e-9, \
            "to_court_xy is not the inverse of speedspin._to_framework_xy"

    H = calibration.homography_from_landmarks({c: kp[c] for c in CORNERS})
    xyz, uv, t, v0, rng, stride = simulate(kp, hfov, width, height, n, fps,
                                           horizon_s, seed, truth_fps)

    rows = []
    for i in range(len(xyz)):
        tr = truth_of(xyz[i], t)
        if tr is None:
            continue
        launch_kmh = float(np.linalg.norm(v0[i])) * MS_TO_KMH
        j = tr["i_bounce"]

        # What the detector would hand downstream: the in-air, in-frame pixels,
        # jittered and thinned exactly as our real one is. `stride` decimates the
        # fine truth grid to the frame rate under test (1 when truth_fps is off).
        m = np.arange(0, j + 1, stride)
        px = uv[i, m].astype(np.float64).copy()
        keep = (np.isfinite(px).all(axis=1) & (px[:, 0] >= 0) & (px[:, 0] < width)
                & (px[:, 1] >= 0) & (px[:, 1] < height))
        px, tm = px[keep], t[m][keep]
        if len(px) < min_len:
            continue
        px += rng.normal(0, pixel_noise, px.shape)
        alive = rng.random(len(px)) >= dropout
        if alive.sum() < min_len:
            continue
        px, tm = px[alive], tm[alive]

        # Back-project to the court plane, then measure — the "approx" path.
        court_xy = calibration.image_to_court(H, px)
        track = [(float(a), float(b), float(c)) for a, b, c in
                 zip(tm, court_xy[:, 0], court_xy[:, 1])]
        est_kmh = analytics.shot_speed_kmh(track)
        if est_kmh <= 0:
            continue

        # THE SAME MEASUREMENT, RESTRICTED TO A LOW BALL. image_to_court solves
        # for where the ray meets z=0, so a ball at height h lands further
        # down-court than it really is, and a near-grazing ray runs to infinity.
        # The pipeline never sees the worst of this — gate_ball_to_court drops
        # points that project outside the court+runoff box, which is mostly the
        # high ones. Re-measuring on only the genuinely low samples isolates how
        # much of the error is the FLAT-PROJECTION ASSUMPTION rather than noise,
        # and shows where the assumption stops being usable.
        z_true = xyz[i, m][keep][alive][:, 2]
        low = z_true <= low_z
        est_low = 0.0
        if low.sum() >= min_len:
            est_low = analytics.shot_speed_kmh([track[k] for k in np.where(low)[0]])

        # Line call: our bounce estimate is the last projected point (the shipped
        # pipeline anchors on a detected bounce; here we take the track's end,
        # which is the same information a perfect bounce detector would have).
        est_bounce = [track[-1][1], track[-1][2]]
        rows.append({
            "launch_kmh": launch_kmh,
            "avg3d_kmh": tr["avg3d_kmh"],
            "avg_ground_kmh": tr["avg_ground_kmh"],
            "est_kmh": est_kmh,
            "est_low_kmh": est_low,
            "n_low": int(low.sum()),
            "true_call": analytics.line_call(tr["bounce_xy"]),
            "est_call": analytics.line_call(est_bounce),
            "bounce_err_m": math.dist(tr["bounce_xy"], est_bounce),
            "line_dist_m": line_distance_m(tr["bounce_xy"]),
            "n_pts": len(track),
        })
    return rows


def summarize(rows, near_m: float = 0.5) -> dict:
    """The headline numbers, computed in ONE place so two callers cannot
    quietly disagree about what "our error" means.

    `near_m` is the band around a line inside which a call is actually a call —
    see line_distance_m for why the pooled figure alone is misleading.
    """
    def pct(a, b):
        return 100.0 * (np.asarray(a) - np.asarray(b)) / np.asarray(b)

    launch = [r["launch_kmh"] for r in rows]
    a3 = [r["avg3d_kmh"] for r in rows]
    ag = [r["avg_ground_kmh"] for r in rows]
    est = [r["est_kmh"] for r in rows]
    be = [r["bounce_err_m"] for r in rows]
    agree = sum(1 for r in rows if r["true_call"] == r["est_call"])
    err = np.abs(pct(est, ag))
    # The low-ball restriction is the only SPEED number worth comparing between
    # setups: the unrestricted one is dominated by rays that graze the plane and
    # run to infinity, so it measures the tail, not the camera.
    lowr = [r for r in rows if r["est_low_kmh"] > 0]
    low = {"n_low": len(lowr), "low_bias_pct": float("nan"),
           "low_abs_err_median": float("nan"), "low_abs_err_p90": float("nan")}
    if lowr:
        el = [r["est_low_kmh"] for r in lowr]
        gl = [r["avg_ground_kmh"] for r in lowr]
        le = np.abs(pct(el, gl))
        low = {"n_low": len(lowr),
               "low_bias_pct": float(np.median(pct(el, gl))),
               "low_abs_err_median": float(np.median(le)),
               "low_abs_err_p90": float(np.percentile(le, 90))}
    near = [r for r in rows if r.get("line_dist_m", 1e9) <= near_m]
    near_agree = sum(1 for r in near if r["true_call"] == r["est_call"])
    # A binary call's floor is NOT 50% — it is the majority class. Without this
    # baseline, "50.5% agreement" could quietly be WORSE than answering "in"
    # every time, and would still read like chance.
    n_in = sum(1 for r in near if r["true_call"] == "in")
    base = (100.0 * max(n_in, len(near) - n_in) / len(near)) if near else float("nan")
    return {
        **low,
        "near_m": near_m,
        "n_near": len(near),
        "call_agree_near_pct":
            (100.0 * near_agree / len(near)) if near else float("nan"),
        "call_near_majority_pct": base,
        "n": len(rows),
        "drag_pct": float(np.median(pct(a3, launch))),
        "ground_proj_pct": float(np.median(pct(ag, a3))),
        "our_pct": float(np.median(pct(est, ag))),
        "total_vs_launch_pct": float(np.median(pct(est, launch))),
        "our_abs_err_median": float(np.median(err)),
        "our_abs_err_p90": float(np.percentile(err, 90)),
        "call_agree_pct": 100.0 * agree / len(rows),
        "call_agree": agree,
        "bounce_err_median_m": float(np.median(be)),
        "bounce_err_p90_m": float(np.percentile(be, 90)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keypoints", default="../data/yt_rally2_pts.json")
    ap.add_argument("--hfov", type=float, default=93.46)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--fps", type=float, default=30.0,
                    help="the SHIPPED effective rate; frame_step targets ~30")
    ap.add_argument("--horizon-s", type=float, default=2.0)
    ap.add_argument("--pixel-noise", type=float, default=2.0,
                    help="detector centroid jitter, px @720p")
    ap.add_argument("--dropout", type=float, default=0.30,
                    help="fraction of frames the detector misses")
    ap.add_argument("--min-len", type=int, default=5)
    ap.add_argument("--low-z", type=float, default=1.0,
                    help="ball height (m) under which the flat z=0 back-projection "
                         "is a fair approximation; the gate keeps mostly these")
    ap.add_argument("--near-m", type=float, default=0.5, dest="near_m",
                    help="band around a line inside which a call is a real call")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    kp = json.loads(Path(args.keypoints).read_text(encoding="utf-8"))
    rows = measure(kp, hfov=args.hfov, width=args.width, height=args.height,
                   n=args.n, fps=args.fps, horizon_s=args.horizon_s,
                   pixel_noise=args.pixel_noise, dropout=args.dropout,
                   min_len=args.min_len, low_z=args.low_z, seed=args.seed)

    if not rows:
        raise SystemExit("no usable flights — loosen --dropout or --min-len")

    def pct(a, b):
        return 100.0 * (np.asarray(a) - np.asarray(b)) / np.asarray(b)

    launch = [r["launch_kmh"] for r in rows]
    a3 = [r["avg3d_kmh"] for r in rows]
    ag = [r["avg_ground_kmh"] for r in rows]
    est = [r["est_kmh"] for r in rows]
    med = lambda v: float(np.median(v))  # noqa: E731

    print(f"{len(rows)} synthetic flights through {Path(args.keypoints).name} "
          f"(fps={args.fps:g}, noise={args.pixel_noise:g}px, dropout={args.dropout:g})")
    print(f"true launch speed  median {med(launch):6.1f} km/h")
    print()
    print("SPEED ERROR BUDGET — where the under-read comes from")
    print(f"  1. drag (launch -> true avg 3D)      {med(pct(a3, launch)):+6.1f}%   physics")
    print(f"  2. ground projection (3D -> ground)  {med(pct(ag, a3)):+6.1f}%   geometry, "
          f"one camera cannot see z")
    print(f"  3. OUR MEASUREMENT (ground -> est)   {med(pct(est, ag)):+6.1f}%   <- the only "
          f"part that is error")
    print(f"  ----------------------------------------------")
    print(f"  total vs launch                      {med(pct(est, launch)):+6.1f}%   "
          f"(CLAUDE.md says -15..-20%)")
    print()
    q = np.percentile(np.abs(pct(est, ag)), [50, 90])
    print(f"our |error| vs the quantity we actually claim to measure: "
          f"median {q[0]:.1f}%, p90 {q[1]:.1f}%")

    lowr = [r for r in rows if r["est_low_kmh"] > 0]
    if lowr:
        el = [r["est_low_kmh"] for r in lowr]
        gl = [r["avg_ground_kmh"] for r in lowr]
        ql = np.percentile(np.abs(pct(el, gl)), [50, 90])
        print()
        print(f"SAME MEASUREMENT, ball below {args.low_z:g} m only "
              f"({len(lowr)} flights) — isolates the flat-projection assumption:")
        print(f"  bias {med(pct(el, gl)):+.1f}%   |error| median {ql[0]:.1f}%, "
              f"p90 {ql[1]:.1f}%")
        print("  The gap between this and the line above IS the cost of putting an")
        print("  airborne ball on the ground plane — which is why the pipeline gates")
        print("  the track and fits a physics arc instead of trusting this path.")

    agree = sum(1 for r in rows if r["true_call"] == r["est_call"])
    print(f"line call agrees with truth on {agree}/{len(rows)} "
          f"({100*agree/len(rows):.1f}%)")
    s = summarize(rows, near_m=args.near_m)
    print(f"  ...but on the {s['n_near']} bounces within {args.near_m:g} m of a line "
          f"— the only ones where the call is a CALL — {s['call_agree_near_pct']:.1f}%")
    be = [r["bounce_err_m"] for r in rows]
    print(f"bounce position error: median {med(be):.2f} m, p90 "
          f"{float(np.percentile(be, 90)):.2f} m")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "synth_truth",
            "measured_against":
                "EXACT simulated truth (drag+gravity+Magnus), projected through "
                f"{Path(args.keypoints).name}'s real calibration. No human labels.",
            "n": len(rows), "fps": args.fps, "pixel_noise": args.pixel_noise,
            "dropout": args.dropout,
            "median_pct": {
                "drag_launch_to_avg3d": round(med(pct(a3, launch)), 1),
                "ground_projection": round(med(pct(ag, a3)), 1),
                "our_measurement": round(med(pct(est, ag)), 1),
                "total_vs_launch": round(med(pct(est, launch)), 1),
            },
            "line_call_agreement_pct": round(100 * agree / len(rows), 1),
            "bounce_err_m_median": round(med(be), 3),
            "rows": rows,
        }, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
