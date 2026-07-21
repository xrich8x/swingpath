"""The physics world frame must be right-handed with +Z up (Session E3).

Four coplanar court corners give a two-fold ambiguous camera pose, and the
corner mapping decides the handedness. Get either wrong and the frame has +Z
pointing into the ground — reprojection looks perfect, but the simulator's
gravity (-Z) is then inverted and every fitted arc is unphysical. Nothing in a
reprojection error can catch that, so it is pinned here.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ball_physics")))

bridge = pytest.importorskip("tennis_tracker.bridge")

# yt_rally2's manual calibration: a real 1280x720 clip with a ~3.3 m camera.
CORNERS = {
    "near_bl_doubles": [-47.0, 561.0],
    "near_br_doubles": [1213.0, 537.0],
    "far_bl_doubles": [504.0, 222.0],
    "far_br_doubles": [743.0, 224.0],
}
IMG_WH = (1280, 720)
HFOV = 93.46


@pytest.fixture(scope="module")
def cam():
    camera, _ = bridge.camera_from_court_corners(CORNERS, IMG_WH, hfov_deg=HFOV)
    return camera


def test_camera_sits_above_the_court(cam):
    """The mirrored pose puts the camera underground; reprojection can't tell."""
    centre = -cam.R.T @ cam.t
    assert centre[2] > 0.0
    assert 1.0 < centre[2] < 12.0, "implausible camera height for a court camera"


def test_up_in_the_world_is_up_in_the_image(cam):
    """A ball 1 m above the service line must appear HIGHER (smaller v)."""
    on_court = cam.project(np.array([[11.885, 0.0, 0.0]]))[0]
    aloft = cam.project(np.array([[11.885, 0.0, 1.0]]))[0]
    assert aloft[1] < on_court[1]


def test_corners_still_reproject(cam):
    errs = [np.linalg.norm(cam.project(np.array([[*w, 0.0]]))[0] - CORNERS[k])
            for k, w in bridge._OUR2FW.items()]
    assert np.mean(errs) < 5.0


def test_speedspin_shares_the_bridge_convention():
    """_to_framework_xy must map our court metres into the same frame."""
    from swingvision import speedspin
    from swingvision import court
    for name, fw in bridge._OUR2FW.items():
        ours = court.LANDMARKS[name]
        assert speedspin._to_framework_xy(ours) == pytest.approx(tuple(fw), abs=1e-6)


def test_launch_from_striker_lands_above_the_court(cam):
    """A ball pixel above a player standing at the baseline lifts to a sane height."""
    striker = (1.0, 0.0)                           # near baseline, mid-court
    on_court = cam.project(np.array([[1.0, 0.0, 0.0]]))[0]
    aloft_uv = cam.project(np.array([[1.0, 0.0, 1.2]]))[0]
    p, miss = bridge.launch_from_striker(cam, aloft_uv, striker)
    assert miss < 0.05
    assert p[2] == pytest.approx(1.2, abs=0.05)
    assert on_court[1] > aloft_uv[1]
