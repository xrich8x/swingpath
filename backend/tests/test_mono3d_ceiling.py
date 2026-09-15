"""The monocular-3D ceiling rig: its geometry, its pairing, and its denominator.

Four things here would silently corrupt the measurement if they broke, and none
of them is visible in an output:

1. the ground-plane intersection (does the fitted arc really cross where we say),
2. the exact bounce truth (`truth_of`'s interpolated crossing),
3. the PAIRING — the 3D arm and the 2D control must score the same noisy pixels,
   which is only true while they share `synth_truth.noisy_pixels` and its rng
   draw order. That refactor is pinned here rather than re-diffed by hand.
4. the DENOMINATOR — non-converged fits and arcs that never reach the ground are
   failures inside the rate, not exclusions from it. A fitter that drops its
   hard cases grades its own homework.

Plus one mechanism check: bar F's mis-specified-physics arm is worthless if the
coefficient override is a silent no-op (`per_channel` already taught us that
lesson once), so the override is checked to actually move the flight.
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ball_physics")))

pytest.importorskip("scipy.optimize")
mono = pytest.importorskip("mono3d_ceiling")
import synth_truth as ST                                        # noqa: E402

# yt_rally2's manual calibration — a real 1280x720 clip (same corners as
# test_bridge_frame.py, which pins the frame handedness these rely on).
CORNERS = {
    "near_bl_doubles": [-47.0, 561.0],
    "near_br_doubles": [1213.0, 537.0],
    "far_bl_doubles": [504.0, 222.0],
    "far_br_doubles": [743.0, 224.0],
}
HFOV = 93.46


def test_ground_intersection_matches_a_closed_form_vacuum_parabola():
    """With drag and lift switched off the crossing has an exact answer.

    z(t) = z0 + vz t - g t^2 / 2 = 0, so t_b = (vz + sqrt(vz^2 + 2 g z0)) / g.
    Nothing else in this rig can tell us the crossing extraction is right.
    """
    from tennis_tracker.physics.aerodynamics import DragModel, LiftModel
    g, z0, vz, vx = 9.81, 1.0, 5.0, 10.0
    t_exp = (vz + math.sqrt(vz * vz + 2 * g * z0)) / g
    got = mono.ground_intersection([0.0, 0.0, z0], [vx, 0.0, vz],
                                   [0.0, 0.0, 0.0], 3.0,
                                   drag=DragModel(cd=0.0),
                                   lift=LiftModel(cl_max=0.0))
    assert got is not None
    xyz, t_b = got
    assert t_b == pytest.approx(t_exp, abs=5e-4)
    assert xyz[0] == pytest.approx(vx * t_exp, abs=5e-3)
    assert abs(xyz[2]) < 1e-9           # it IS the plane, not merely near it


def test_ground_intersection_is_the_first_crossing_and_none_when_there_is_none():
    up = mono.ground_intersection([0.0, 0.0, 1.0], [0.0, 0.0, 20.0],
                                  [0.0, 0.0, 0.0], 0.5)
    assert up is None, "a ball still rising at t_max has no crossing yet"
    down = mono.ground_intersection([0.0, 0.0, 1.0], [15.0, 0.0, 2.0],
                                    [0.0, 0.0, 0.0], 4.0)
    assert down is not None and down[1] < 1.2


def test_ground_intersection_is_insensitive_to_the_integrator_step():
    """The dt lever must not move the answer it is used to compute."""
    a = mono.ground_intersection([0.5, 1.0, 1.1], [28.0, 1.5, 6.0],
                                 [0.0, 180.0, 20.0], 4.0, dt=2e-3)
    b = mono.ground_intersection([0.5, 1.0, 1.1], [28.0, 1.5, 6.0],
                                 [0.0, 180.0, 20.0], 4.0, dt=2.5e-4)
    assert a is not None and b is not None
    assert abs(a[1] - b[1]) < 1e-3
    assert float(np.linalg.norm(a[0] - b[0])) < 2e-3


def test_truth_of_interpolates_the_crossing_rather_than_rounding_to_a_frame():
    """A frame-rounded bounce would put a fake 20 cm into a 10 cm bar."""
    g, z0, vz, vx = 9.81, 1.0, 4.0, 30.0
    t = np.arange(0, 1.5, 1.0 / 60.0)
    xyz = np.stack([vx * t, np.zeros_like(t), z0 + vz * t - 0.5 * g * t ** 2], 1)
    tr = ST.truth_of(xyz, t)
    t_exp = (vz + math.sqrt(vz * vz + 2 * g * z0)) / g
    assert tr["t_b"] == pytest.approx(t_exp, abs=1.0 / 60.0 / 8)
    # physics X (length) -> swingvision y (length); see synth_truth.to_court_xy
    assert tr["bounce_xy"][1] == pytest.approx(vx * tr["t_b"], abs=1e-6)
    # the naive alternative is to call the last IN-AIR sample the bounce; this
    # fixture must be one where that is clearly wrong, or the test proves nothing
    last_inair_x = vx * float(t[tr["i_bounce"]])
    assert abs(last_inair_x - vx * t_exp) > 0.10


def test_score_counts_non_convergence_and_no_crossing_as_failures():
    """Design call 3, pinned: the hard cases stay in the denominator."""
    flights = [{"flight": i, "true_bounce_xy": [5.0, 10.0], "true_t_b": 1.0,
                "ctrl_bounce_xy": [5.0, 10.0], "ctrl_err_m": 0.01,
                "ctrl_dt_frames": 0.0} for i in range(4)]
    fits = [
        # inside the bar, converged
        {"arm": "b1", "flight": 0, "converged": True, "crossed": True,
         "rmse_px": 1.0, "bounce_xy": [5.02, 10.0], "t_b": 1.0},
        # inside the bar but the optimiser never converged — still counted
        {"arm": "b1", "flight": 1, "converged": False, "crossed": True,
         "rmse_px": 9.0, "bounce_xy": [5.0, 10.01], "t_b": 1.0},
        # fitted an arc that never reaches the ground: a FAILURE, not a drop
        {"arm": "b1", "flight": 2, "converged": True, "crossed": False,
         "rmse_px": 1.0},
        # flight 3 has no fit at all (too few observations): also a failure
    ]
    res = mono.score(flights, fits, {"n_sim": 6, "no_truth": 1, "rig_drop": 1},
                     fps=60.0)
    b1 = res["b1"]
    assert res["n_presented"] == 4 and res["n_all_truth"] == 5
    assert b1["n_no_ground_crossing"] == 1 and b1["n_no_fit"] == 1
    assert b1["n_not_converged"] == 1
    assert b1["within_bar_pct_presented"] == pytest.approx(50.0)   # 2 of 4
    assert b1["within_bar_pct_all_truth"] == pytest.approx(40.0)   # 2 of 5
    assert res["control_2d"]["within_bar_pct_presented"] == pytest.approx(100.0)
    assert res["control_2d"]["within_bar_pct_all_truth"] == pytest.approx(80.0)


@pytest.mark.skipif(not pytest.importorskip("torch", reason="needs torch"),
                    reason="needs torch")
def test_the_two_arms_score_the_identical_noisy_pixels():
    """PAIRING + the synth_truth refactor, in one assertion.

    `synth_truth.measure` is the 2D control as it existed before this rig, and
    `build_flights` is the paired driver. Same keypoints, same seed, same
    parameters, so every bounce error `measure` reports must appear — as an
    exact float, in order — in the driver's control column. If the extraction of
    `noisy_pixels` had moved a single rng draw, these would diverge.
    """
    kw = dict(hfov=HFOV, width=1280, height=720, n=60, fps=30.0,
              pixel_noise=2.0, dropout=0.30, min_len=5, seed=11)
    rows = ST.measure(CORNERS, **kw)
    cfg = mono.make_cfg(img_height=720, width=1280, hfov=HFOV, n=60, fps=30.0,
                        truth_fps=None, pixel_noise=2.0, dropout=0.30, seed=11)
    flights, tally, _ = mono.build_flights(CORNERS, cfg)

    assert len(rows) >= 20, "fixture too small to be a real check"
    mine = [f["ctrl_err_m"] for f in flights]
    it = iter(mine)
    for r in rows:
        # measure() drops the odd flight on est_kmh<=0, so its errors are a
        # SUBSEQUENCE of the driver's — but every one must match exactly.
        assert any(v == r["bounce_err_m"] for v in it), \
            "the control arm diverged from synth_truth.measure"
    assert tally["n_sim"] == 60


@pytest.mark.skipif(not pytest.importorskip("torch", reason="needs torch"),
                    reason="needs torch")
def test_the_bar_F_aero_override_is_not_a_silent_no_op():
    """Passing the default must change nothing; passing +20% must change a lot.

    Bar F offsets the SIMULATOR's cd / cl_max away from the fitter's to break
    the shared-model premise. If the override were ignored the arm would report
    a reassuring null for the wrong reason.
    """
    base = dict(kp=CORNERS, hfov=HFOV, w=1280, h=720, n=8, fps=60.0,
                horizon_s=1.5, seed=3)
    a = ST.simulate(**base)[0]
    same = ST.simulate(**base, cd=0.55, cl_max=1.0, cl_sat=2.0)[0]
    hi = ST.simulate(**base, cd=0.55 * 1.2, cl_max=1.2)[0]
    assert np.array_equal(a, same), "explicit defaults must be a no-op"
    moved = np.nanmax(np.abs(hi - a))
    assert moved > 0.05, f"aero override barely moved the flight ({moved:.4f} m)"
