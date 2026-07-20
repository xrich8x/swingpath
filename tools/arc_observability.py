"""arc_observability.py — is shot speed even OBSERVABLE from one camera? (E1.4)

`arc_error_budget.py` found something that reframes the whole arc workstream:
on PERFECT, noise-free, ground-truth pixels with a PERFECT bounce anchor, the
physics fit reprojects at 1.5-3 px (it sails through the 6 px gate) and still
reports a speed 43% too low. Two different initialisations land on 48.6 and
173.1 km/h — for a 86.9 km/h ball — and BOTH reproject inside 2 px.

So the failing arcs were never a detection problem or a gate-tuning problem.
A hit->bounce arc seen by one camera and pinned at ONE end is under-determined:
the launch point slides along its viewing ray, and the fit trades depth against
speed at almost no cost in reprojection.

This tool maps that degeneracy — it walks the launch point along its own viewing
ray, fits everything else at each depth, and prints reprojection against
recovered speed. A flat reprojection curve over a wide speed range IS the
finding. It then prices the constraints that could break the tie, the cheapest
first, because we already know where the striking player is standing.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\arc_observability.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ball_physics"))

from tennis_tracker.bridge import camera_from_court_corners           # noqa: E402
from tennis_tracker.calibration.lift import lift_contact              # noqa: E402
from tennis_tracker.estimation.trajectory_fit import fit_arc          # noqa: E402
from tennis_tracker.physics import simulate                           # noqa: E402

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
TRUE = dict(p0=[20.0, 0.5, 1.0], v0=[-24.0, -1.0, 2.5], rpm=2400)


def truth():
    v0 = np.array(TRUE["v0"], float)
    horiz = np.array([v0[0], v0[1], 0.0]); horiz /= np.linalg.norm(horiz)
    omega = np.cross([0.0, 0.0, 1.0], horiz) * (TRUE["rpm"] * 2 * np.pi / 60.0)
    tr = simulate(np.array(TRUE["p0"], float), v0, omega, dt=2e-4, t_max=3.0, bounces=0)
    return tr, float(tr.t[-1]), omega, float(np.linalg.norm(v0)) * 3.6


def ray_point(camera, uv, depth_z):
    """Back-project a pixel to the plane z = depth_z (world metres)."""
    ray = np.linalg.inv(camera.K) @ np.array([uv[0], uv[1], 1.0])
    d = camera.R.T @ ray
    c = -camera.R.T @ camera.t
    return c + ((depth_z - c[2]) / d[2]) * d


def reproj_of(camera, p0, v0, omega, times, uv):
    tr = simulate(p0, v0, omega, dt=2e-3, t_max=float(times[-1]) + 0.05, bounces=0)
    pred = camera.project(tr.sample(times))
    return float(np.sqrt(np.mean(np.sum((pred - uv) ** 2, axis=1))))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keypoints", default=str(REPO / "data" / "yt_rally2_pts.json"))
    ap.add_argument("--hfov", type=float, default=93.46)
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--sigma-px", type=float, default=0.0)
    ap.add_argument("--gate", type=float, default=6.0)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    kp = json.loads(Path(args.keypoints).read_text(encoding="utf-8"))
    camera, H = camera_from_court_corners({k: kp[k] for k in CORNERS},
                                          (1280, 720), hfov_deg=args.hfov)
    tr, t_b, omega_true, speed_true = truth()

    t = np.arange(0.0, t_b + 1e-9, 1.0 / args.fps)
    uv = camera.project(tr.sample(t))
    if args.sigma_px:
        uv = uv + np.random.default_rng(0).normal(0, args.sigma_px, uv.shape)
    a = 2
    times = t[a:] - t[a]
    obs = uv[a:]
    anchor = lift_contact(np.asarray(uv[-1], float), H)[0]

    print(f"ground truth: {speed_true:.1f} km/h, {TRUE['rpm']} rpm topspin, "
          f"launch p0={TRUE['p0']}, flight {t_b*1000:.0f} ms")
    print(f"observed at {args.fps:g} fps -> {len(obs)} samples, "
          f"noise {args.sigma_px:g} px, gate {args.gate:g} px\n")

    # --- 1. the degeneracy: slide the launch point along its own viewing ray ---
    print("A. launch point walked along its viewing ray (v0 + spin refit at each depth)")
    hdr = (f"{'launch z (m)':>13} {'launch x (m)':>13} {'recovered km/h':>15} "
           f"{'err':>8} {'reproj':>9} {'passes gate':>12}")
    print(hdr); print("-" * len(hdr))
    rows = []
    for z0 in (0.3, 0.6, 1.0, 1.5, 2.0, 2.5, 3.0):
        p_fixed = ray_point(camera, obs[0], z0)
        v_guess = (anchor - p_fixed) / max(times[-1], 1e-3)
        fit = fit_arc(times, obs, camera=camera, p0_init=p_fixed, v0_init=v_guess,
                      fix_p0=True, physical_bounds=True)
        rep = reproj_of(camera, p_fixed, fit.v0, fit.omega, times, obs)
        kmh = float(np.linalg.norm(fit.v0)) * 3.6
        rows.append(dict(mode="ray_walk", z0=z0, x0=float(p_fixed[0]),
                         kmh=kmh, reproj=rep))
        print(f"{z0:>13.1f} {p_fixed[0]:>13.1f} {kmh:>15.1f} "
              f"{100*(kmh-speed_true)/speed_true:>+7.0f}% {rep:>8.2f}px "
              f"{'YES' if rep <= args.gate else 'no':>12}")

    passing = [r for r in rows if r["reproj"] <= args.gate]
    if passing:
        lo = min(r["kmh"] for r in passing); hi = max(r["kmh"] for r in passing)
        print(f"\n  -> {len(passing)}/{len(rows)} launch depths pass the {args.gate:g} px "
              f"gate, spanning {lo:.0f}-{hi:.0f} km/h ({hi/max(lo,1e-6):.1f}x) "
              f"around a true {speed_true:.0f} km/h.")
        print("     The gate cannot tell these apart. Speed is not observable from "
              "reprojection alone.")

    # --- 2. what a second constraint buys ---
    print("\nB. adding a second constraint (the cheapest ones we can already supply)")
    hdr2 = f"{'constraint':<44} {'recovered km/h':>15} {'err':>8} {'reproj':>9}"
    print(hdr2); print("-" * len(hdr2))

    def report(label, p0, fixed):
        v_guess = (anchor - p0) / max(times[-1], 1e-3)
        fit = fit_arc(times, obs, camera=camera, p0_init=p0, v0_init=v_guess,
                      fix_p0=fixed, physical_bounds=True,
                      anchor=None if fixed else (-1, anchor, 100.0))
        p_used = p0 if fixed else fit.p0
        rep = reproj_of(camera, p_used, fit.v0, fit.omega, times, obs)
        kmh = float(np.linalg.norm(fit.v0)) * 3.6
        rows.append(dict(mode=label, kmh=kmh, reproj=rep))
        print(f"{label:<44} {kmh:>15.1f} "
              f"{100*(kmh-speed_true)/speed_true:>+7.0f}% {rep:>8.2f}px")

    # The arc starts at t[a], not at the racquet, so the honest "perfect" p0 is
    # the true trajectory sampled at the arc's first frame.
    p_true_a = tr.sample(np.array([t[a]]))[0]
    report("bounce anchor only (what we ship today)",
           ray_point(camera, obs[0], 0.8), False)
    report("+ perfect 3D launch point (unobtainable upper bound)", p_true_a, True)
    print()
    # What we could actually supply: a height prior on the ball at the arc's
    # first frame. Sensitivity to getting that height wrong is the whole story.
    z_true = float(p_true_a[2])
    for dz in (0.0, 0.25, 0.5, -0.25, -0.5):
        report(f"+ contact-height prior z={z_true + dz:.2f} m "
               f"({'exact' if dz == 0 else f'{dz:+.2f} m wrong'})",
               ray_point(camera, obs[0], z_true + dz), True)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"fps": args.fps, "sigma_px": args.sigma_px, "gate": args.gate,
             "speed_true_kmh": speed_true, "rows": rows}, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
