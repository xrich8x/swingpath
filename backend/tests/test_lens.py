"""Lens distortion (division model): point round-trips + the plumb-line k1
estimator on synthetic distorted court renders (known k1 in -> k1 out).

The render is the honest test: draw a clean pinhole court (overlay.
synthetic_court_image), remap it through a KNOWN k1 (each distorted pixel
samples the pinhole image at its undistorted position), then ask estimate_k1
to read the k1 back off the curved lines alone.
"""

import math

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import calibration, court, overlay

W, H = 1280, 720
# A plausible behind-the-baseline framing with long visible lines.
_CORNERS = {
    "near_bl_doubles": (154.0, 670.0), "near_br_doubles": (1126.0, 655.0),
    "far_bl_doubles": (358.0, 252.0), "far_br_doubles": (973.0, 245.0),
}


def _pinhole_court():
    Hm = calibration.homography_from_landmarks(_CORNERS)
    return overlay.synthetic_court_image(Hm, W, H, thickness=3)


def _distort_image(img, k1):
    """Warp a pinhole render through the division model: the distorted image at
    p_d shows what the pinhole camera saw at undistort(p_d)."""
    yy, xx = np.mgrid[0:H, 0:W]
    pts = np.column_stack([xx.ravel(), yy.ravel()]).astype(np.float64)
    und = calibration.undistort_points(pts, k1, (W, H))
    map_x = und[:, 0].reshape(H, W).astype(np.float32)
    map_y = und[:, 1].reshape(H, W).astype(np.float32)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR)


# --- point transforms --------------------------------------------------------

def test_undistort_identity_at_k1_zero():
    pts = np.array([[10.0, 20.0], [640.0, 360.0], [1270.0, 700.0]])
    assert np.allclose(calibration.undistort_points(pts, 0.0, (W, H)), pts)
    assert np.allclose(calibration.distort_points(pts, 0.0, (W, H)), pts)


def test_distortion_centre_is_fixed_point():
    c = np.array([[W / 2.0, H / 2.0]])
    for k1 in (-0.25, -0.05, 0.1):
        assert np.allclose(calibration.undistort_points(c, k1, (W, H)), c)
        assert np.allclose(calibration.distort_points(c, k1, (W, H)), c)


def test_point_round_trip():
    rng = np.random.default_rng(7)
    pts = rng.uniform([0, 0], [W, H], size=(200, 2))
    for k1 in (-0.22, -0.08, 0.08):
        und = calibration.undistort_points(pts, k1, (W, H))
        back = calibration.distort_points(und, k1, (W, H))
        assert np.allclose(back, pts, atol=1e-6), f"round trip broke at k1={k1}"


def test_barrel_pulls_points_outward_when_undistorting():
    # Barrel (k1<0): observed points sit closer to the centre than pinhole
    # would put them, so undistortion must push them OUT.
    p = np.array([[1200.0, 650.0]])
    und = calibration.undistort_points(p, -0.15, (W, H))[0]
    c = np.array([W / 2.0, H / 2.0])
    assert np.hypot(*(und - c)) > np.hypot(*(p[0] - c))


# --- the estimator on synthetic renders --------------------------------------

@pytest.mark.parametrize("k1_true,tol", [(-0.08, 0.03), (-0.18, 0.05)])
def test_estimate_k1_round_trip(k1_true, tol):
    img = _distort_image(_pinhole_court(), k1_true)
    est = calibration.estimate_k1(img)
    assert est.n_lines >= 3, f"too few usable lines ({est.n_lines})"
    assert abs(est.k1 - k1_true) <= tol, (
        f"k1 {est.k1:+.3f} vs true {k1_true:+.3f} (lines: {est.per_line})")


def test_estimate_k1_near_zero_on_pinhole_render():
    est = calibration.estimate_k1(_pinhole_court())
    assert abs(est.k1) <= 0.02, f"pinhole render read k1={est.k1:+.3f}"


def test_estimate_k1_refuses_blank_frame():
    blank = np.zeros((H, W, 3), np.uint8)
    est = calibration.estimate_k1(blank)
    assert est.k1 == 0.0 and est.n_lines == 0


def test_undistorted_corners_give_straight_sidelines():
    # The functional claim behind step 2: undistorting points recovers pinhole
    # geometry. Take court-line points, distort them (what a wide lens observes),
    # undistort them back, and check they are collinear again.
    Hm = calibration.homography_from_landmarks(_CORNERS)
    a, b = (0.0, 0.0), (0.0, court.LENGTH)      # left doubles sideline
    ts = np.linspace(0, 1, 9)[:, None]
    line_m = np.asarray(a) + ts * (np.asarray(b) - np.asarray(a))
    pin = calibration.court_to_image(Hm, line_m)
    seen = calibration.distort_points(pin, -0.18, (W, H))
    # the distorted observation is measurably curved...
    def max_dev(pts):
        d = pts[-1] - pts[0]
        n = np.array([-d[1], d[0]]) / np.hypot(*d)
        return float(np.abs((pts - pts[0]) @ n).max())
    assert max_dev(seen) > 2.0
    # ...and undistortion straightens it to sub-pixel
    fixed = calibration.undistort_points(seen, -0.18, (W, H))
    assert max_dev(fixed) < 0.1
