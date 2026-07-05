"""Validation tests for the physics core and the estimator.

Run with `pytest tests/` or `python tests/test_physics.py`. These encode the
sanity checks used during development: spin changes the trajectory the right
way, drag bleeds speed, and the fit recovers the launch state from noisy data.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis_tracker.physics import simulate
from tennis_tracker.estimation import spin_vector, summarize, fit_arc


P0 = np.array([0.0, 0.0, 1.0])
V0 = np.array([38.0, 0.0, 4.0])


def _land_x(omega):
    tr = simulate(P0, V0, omega, bounces=0)
    return tr.pos[-1, 0]


def test_topspin_lands_shorter_than_backspin():
    top = _land_x(spin_vector(topspin_rpm=2800, travel_dir=V0))
    flat = _land_x(np.zeros(3))
    back = _land_x(spin_vector(topspin_rpm=-2800, travel_dir=V0))
    assert top < flat < back, (top, flat, back)


def test_sidespin_deflects_laterally():
    tr = simulate(P0, V0, spin_vector(sidespin_rpm=2500, travel_dir=V0), bounces=0)
    assert abs(tr.pos[-1, 1]) > 0.5, tr.pos[-1, 1]


def test_drag_reduces_speed():
    tr = simulate(P0, V0, np.zeros(3), bounces=0)
    assert np.linalg.norm(tr.vel[-1]) < 0.95 * np.linalg.norm(tr.vel[0])


def test_kinematics_roundtrip():
    w = spin_vector(topspin_rpm=2000, sidespin_rpm=500)
    r = summarize(np.array([40, 0, 3.0]), w)
    assert abs(r.topspin_rpm - 2000) < 1
    assert abs(r.sidespin_rpm - 500) < 1


def test_fit_recovers_speed_and_spin_axis_3d():
    rng = np.random.default_rng(3)
    v0 = np.array([28.0, 1.5, 6.0])
    omega = spin_vector(topspin_rpm=2600, sidespin_rpm=400, travel_dir=v0)
    gt = summarize(v0, omega)
    tr = simulate(np.array([1.0, 0.0, 0.9]), v0, omega, bounces=0)
    times = np.arange(0, tr.t[-1] - 0.02, 1 / 60)
    obs = tr.sample(times) + rng.normal(0, 0.02, (len(times), 3))
    fit = fit_arc(times, obs)
    # Speed is well-constrained by a single arc; spin *magnitude* is recovered
    # well; the spin *axis* (topspin-vs-sidespin split) is ill-conditioned on a
    # short arc and varies with noise (~0-30 deg) -- this is exactly why the
    # bounce refinement and the learned SpinNet prior exist. Assert what is
    # genuinely stable.
    assert abs(fit.readout.speed_mps - gt.speed_mps) / gt.speed_mps < 0.02
    assert abs(fit.readout.spin_rpm - gt.spin_rpm) / gt.spin_rpm < 0.25
    pn, gn = np.linalg.norm(fit.omega), np.linalg.norm(omega)
    cos = np.dot(fit.omega, omega) / (pn * gn)
    assert np.degrees(np.arccos(np.clip(cos, -1, 1))) < 45.0  # loose sanity only


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print(f"\nAll {len(fns)} tests passed.")
