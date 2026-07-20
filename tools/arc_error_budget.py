"""arc_error_budget.py — why does every physics arc fail the 6 px gate? (E1.4)

The arc fit is a black box that reports one number, `reproj_px`, and on real
footage that number has been 13-284 px against a 6.0 px gate. This tool takes
the fit apart on GROUND TRUTH, so each error source can be priced separately:

  (a) EVENT TIMING   — the bounce frame we anchor to is off by k frames
  (b) SPARSITY       — a low frame rate leaves few samples in a ~0.5 s flight
  (c) DETECTION NOISE— the pixel track is jittery
  (d) PHASE          — even a perfectly-identified bounce FRAME is up to
                       0.5/fps seconds away from the true bounce INSTANT

The recipe: simulate a real tennis flight with known (p0, v0, omega) through a
real court calibration, project it to pixels at each frame rate, and hand the
result to the same `fit_anchored` the pipeline uses. Everything the fit sees is
perfect except the one variable under test, so whatever error comes out is
attributable.

Frame rate is the headline variable because an anchor that is one frame early
anchors an AIRBORNE ball to z=0, and how airborne it is depends entirely on fps.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\arc_error_budget.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ball_physics"))

from tennis_tracker.bridge import camera_from_court_corners, fit_anchored  # noqa: E402
from tennis_tracker.physics import simulate                                # noqa: E402

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")

# One representative groundstroke, in the framework's world frame
# (x = along court 0..23.77, y = across +-5.485, z = up).
SHOTS = {
    # struck near the far baseline, driven back toward the near court with topspin
    "drive_topspin": dict(p0=[20.0, 0.5, 1.0], v0=[-24.0, -1.0, 2.5], rpm=2400),
    # slower, higher loop — longer flight, more samples
    "loop_topspin": dict(p0=[20.0, -1.0, 1.2], v0=[-17.0, 1.5, 5.0], rpm=2800),
    # flat drive — least Magnus curvature
    "flat_drive": dict(p0=[19.0, 0.0, 1.1], v0=[-28.0, 0.0, 1.0], rpm=600),
}


def topspin_omega(v0, rpm):
    """Spin vector of `rpm` pure topspin for a ball travelling along v0."""
    v = np.asarray(v0, float)
    horiz = np.array([v[0], v[1], 0.0])
    horiz /= np.linalg.norm(horiz)
    axis = np.cross([0.0, 0.0, 1.0], horiz)      # topspin axis: right-hand rule
    return axis * (rpm * 2 * np.pi / 60.0)


def ground_truth_arc(shot):
    """Simulate to the first ground contact. Returns (trajectory, t_bounce)."""
    omega = topspin_omega(shot["v0"], shot["rpm"])
    tr = simulate(np.array(shot["p0"], float), np.array(shot["v0"], float), omega,
                  dt=2e-4, t_max=3.0, bounces=0)
    return tr, float(tr.t[-1]), omega


def sample_track(tr, camera, fps, phase, t_bounce, sigma_px, rng):
    """Project the flight onto a frame grid offset by `phase` frames.

    `phase` in [0,1) slides the grid relative to the true bounce instant, which
    is what decides how far the nearest FRAME is from the true bounce. Returns
    (times, uv, i_nearest_bounce_frame).
    """
    dt = 1.0 / fps
    t0 = -phase * dt
    times = np.arange(t0, t_bounce + dt, dt)
    times = times[times >= 0.0]
    pos = tr.sample(times)
    uv = camera.project(pos)
    if sigma_px:
        uv = uv + rng.normal(0.0, sigma_px, uv.shape)
    i_b = int(np.argmin(np.abs(times - t_bounce)))
    return times, uv, i_b


def run(camera, Hfw, shot_name, fps, offsets, sigma_px, n_phase, min_arc, rng):
    shot = SHOTS[shot_name]
    tr, t_bounce, omega = ground_truth_arc(shot)
    true_speed_kmh = float(np.linalg.norm(shot["v0"])) * 3.6
    rows = []
    for off in offsets:
        reprojs, speeds, anchor_h = [], [], []
        n_short = 0
        for p in range(n_phase):
            phase = p / n_phase
            times, uv, i_b = sample_track(tr, camera, fps, phase, t_bounce,
                                          sigma_px, rng)
            b = i_b + off
            # The arc the pipeline would build: hit+2 .. anchor frame.
            a = 2
            if b >= len(times) or b - a + 1 < min_arc:
                n_short += 1
                continue
            seg_t = times[a:b + 1] - times[a]
            seg_uv = uv[a:b + 1]
            r, reproj, _ = fit_anchored(seg_t, seg_uv, camera, Hfw, uv[b], "end")
            reprojs.append(reproj)
            speeds.append(r.speed_kmh)
            # how high the ball actually is at the frame we anchor to z=0
            anchor_h.append(float(tr.sample(np.array([times[b]]))[0, 2]))
        if not reprojs:
            rows.append(dict(fps=fps, offset=off, n=0, note="arc too short"))
            continue
        rows.append(dict(
            fps=fps, offset=off, n=len(reprojs),
            reproj_med=float(np.median(reprojs)),
            reproj_max=float(np.max(reprojs)),
            speed_med=float(np.median(speeds)),
            speed_err_pct=100.0 * (float(np.median(speeds)) - true_speed_kmh) / true_speed_kmh,
            anchor_height_m=float(np.median(np.abs(anchor_h))),
            short=n_short,
        ))
    return rows, t_bounce, true_speed_kmh


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keypoints", default=str(REPO / "data" / "yt_rally2_pts.json"))
    ap.add_argument("--hfov", type=float, default=93.46,
                    help="the value the yt_rally2 perception cache was built with")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--shot", default="drive_topspin", choices=sorted(SHOTS))
    ap.add_argument("--fps", type=float, nargs="*", default=[120, 60, 30, 24])
    ap.add_argument("--offsets", type=int, nargs="*", default=[-2, -1, 0, 1])
    ap.add_argument("--sigma-px", type=float, default=0.0)
    ap.add_argument("--phases", type=int, default=8)
    ap.add_argument("--min-arc", type=int, default=6,
                    help="speedspin.estimate's min_arc — arcs shorter than this "
                         "are never even attempted")
    ap.add_argument("--gate", type=float, default=6.0)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    kp = json.loads(Path(args.keypoints).read_text(encoding="utf-8"))
    named = {k: kp[k] for k in CORNERS if k in kp}
    if len(named) < 4:
        raise SystemExit(f"{args.keypoints} lacks the 4 doubles corners")
    camera, Hfw = camera_from_court_corners(named, (args.width, args.height),
                                            hfov_deg=args.hfov)

    rng = np.random.default_rng(0)
    all_rows = []
    for fps in args.fps:
        rows, t_bounce, _ = run(camera, Hfw, args.shot, fps, args.offsets,
                                args.sigma_px, args.phases, args.min_arc, rng)
        all_rows += rows

    print(f"shot={args.shot}  camera={args.keypoints} hfov={args.hfov}  "
          f"noise={args.sigma_px}px  phases={args.phases}  gate={args.gate}px")
    print(f"ground truth: flight {t_bounce*1000:.0f} ms, "
          f"launch speed {np.linalg.norm(SHOTS[args.shot]['v0'])*3.6:.1f} km/h, "
          f"{SHOTS[args.shot]['rpm']} rpm topspin\n")

    hdr = (f"{'fps':>5} {'anchor off':>11} {'samples':>8} {'ball z at anchor':>17} "
           f"{'reproj med':>11} {'reproj max':>11} {'speed err':>10} {'passes 6px':>11}")
    print(hdr)
    print("-" * len(hdr))
    for r in all_rows:
        if r["n"] == 0:
            print(f"{r['fps']:>5.0f} {r['offset']:>+11d} {'-':>8} {r['note']:>17}")
            continue
        print(f"{r['fps']:>5.0f} {r['offset']:>+11d} {r['n']:>8} "
              f"{r['anchor_height_m']:>16.2f}m {r['reproj_med']:>10.1f}px "
              f"{r['reproj_max']:>10.1f}px {r['speed_err_pct']:>+9.1f}% "
              f"{'YES' if r['reproj_med'] <= args.gate else 'no':>11}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"shot": args.shot, "hfov": args.hfov, "sigma_px": args.sigma_px,
             "phases": args.phases, "min_arc": args.min_arc, "rows": all_rows},
            indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
