"""Recover speed & spin from observations by inverting the physics (no training).

Simulates a known shot, samples it like a 60 fps camera would, adds noise, then
fits the launch state back. Demonstrates both the clean 3D case and the harder
monocular-2D case.

    python scripts/demo_fit.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis_tracker.physics import simulate
from tennis_tracker.estimation import spin_vector, summarize, fit_arc
from tennis_tracker.data.camera import make_courtside_camera
from tennis_tracker.eval import speed_error, spin_error


def main():
    rng = np.random.default_rng(0)
    v0 = np.array([28.0, 1.5, 6.0])
    omega = spin_vector(topspin_rpm=2600, sidespin_rpm=400, travel_dir=v0)   # +y = topspin
    p0 = np.array([1.0, 0.0, 0.9])
    gt = summarize(v0, omega)
    print(f"TRUTH    speed {gt.speed_kmh:6.1f} km/h | spin {gt.spin_rpm:5.0f} rpm "
          f"(top {gt.topspin_rpm:+.0f}, side {gt.sidespin_rpm:+.0f})")

    tr = simulate(p0, v0, omega, bounces=0)
    times = np.arange(0, tr.t[-1] - 0.02, 1 / 60)
    pos = tr.sample(times)

    # (a) 3D observations (multi-view / lifted), 2 cm noise
    obs3d = pos + rng.normal(0, 0.02, pos.shape)
    f3 = fit_arc(times, obs3d)
    se, sp = speed_error(f3.readout.speed_mps, gt.speed_mps), spin_error(f3.omega, omega)
    print(f"FIT 3D   speed {f3.readout.speed_kmh:6.1f} km/h | spin {f3.readout.spin_rpm:5.0f} rpm "
          f"| speed err {se['pct']:.1f}% | spin err {sp['rpm_pct']:.1f}% / axis {sp['axis_deg']:.1f} deg")

    # (b) monocular 2D, 1.5 px noise, anchored start + warm init
    cam = make_courtside_camera()
    uv = cam.project(pos) + rng.normal(0, 1.5, (len(pos), 2))
    f2 = fit_arc(times, uv, camera=cam, p0_init=p0, fix_p0=True,
                 v0_init=v0 * 0.9, omega_init=omega * 0.5)
    se2 = speed_error(f2.readout.speed_mps, gt.speed_mps)
    print(f"FIT 2D   speed {f2.readout.speed_kmh:6.1f} km/h | spin {f2.readout.spin_rpm:5.0f} rpm "
          f"| speed err {se2['pct']:.1f}% | reproj {f2.rmse:.2f} px")


if __name__ == "__main__":
    main()
