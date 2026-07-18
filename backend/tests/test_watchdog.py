"""Camera-change watchdog (courtfit.CourtWatchdog) + the projective rebase.

Synthetic court frames: while the camera is where calibration left it, coverage
stays high and the watchdog is quiet. When the frames start coming from a MOVED
camera (the projected court no longer sits on the lines), coverage collapses
relative to the watchdog's own baseline and it alarms after two consecutive bad
checks - one dip (a player standing on a line) must NOT alarm. The rebase math:
A = H_new @ H_old^-1 stored as a full 3x3 row must round-trip through
pipeline._cam_row_to_A so un-warped pixels land back in frame-0 space.
"""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from swingvision import calibration, court, courtfit
from swingvision.pipeline import _cam_row_to_A

_DBL = ("near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles")
_IMG_A = {  # calibrated camera position
    "near_bl_doubles": [150.0, 330.0], "near_br_doubles": [490.0, 330.0],
    "far_br_doubles": [400.0, 90.0], "far_bl_doubles": [240.0, 90.0],
}
# the camera after a bump: everything shifted right + slightly down
_IMG_B = {k: [v[0] + 45.0, v[1] + 18.0] for k, v in _IMG_A.items()}


def _H(named):
    return calibration.compute_homography(
        [court.LANDMARKS[n] for n in _DBL], [named[n] for n in _DBL])


def _frame(H, w=640, h=360):
    img = np.zeros((h, w, 3), np.uint8)
    for a, b in court.LINES:
        pa = calibration.court_to_image(H, [a])[0]
        pb = calibration.court_to_image(H, [b])[0]
        cv2.line(img, (int(round(pa[0])), int(round(pa[1]))),
                 (int(round(pb[0])), int(round(pb[1]))), (255, 255, 255), 2)
    return img


def test_stable_camera_stays_quiet():
    H = _H(_IMG_A)
    wd = courtfit.CourtWatchdog(calibration, court)
    states = [wd.check(_frame(H), H) for _ in range(8)]
    assert states[:5] == ["warmup"] * 5
    assert states[5:] == ["ok"] * 3


def test_camera_change_alarms_after_two_bad_checks():
    H_old = _H(_IMG_A)
    wd = courtfit.CourtWatchdog(calibration, court)
    for _ in range(5):
        wd.check(_frame(H_old), H_old)
    moved = _frame(_H(_IMG_B))          # frames now come from the bumped camera
    assert wd.check(moved, H_old) == "watch"
    assert wd.check(moved, H_old) == "changed"


def test_single_dip_does_not_alarm():
    H = _H(_IMG_A)
    wd = courtfit.CourtWatchdog(calibration, court)
    for _ in range(5):
        wd.check(_frame(H), H)
    blank = np.zeros((360, 640, 3), np.uint8)   # momentary total occlusion
    assert wd.check(blank, H) == "watch"
    assert wd.check(_frame(H), H) == "ok"       # recovered, no alarm


def test_projective_rebase_round_trips():
    H_old, H_new = _H(_IMG_A), _H(_IMG_B)
    A = H_new @ np.linalg.inv(H_old)
    A = A / A[2, 2]
    row = [float(v) for v in A.ravel()]          # what _perceive stores (9 numbers)
    A_back = _cam_row_to_A(row)
    inv = np.linalg.inv(A_back)
    for n in _DBL:                               # bumped-camera pixel -> frame-0 pixel
        px = np.array([*_IMG_B[n], 1.0])
        q = inv @ px
        q = q[:2] / q[2]
        assert np.allclose(q, _IMG_A[n], atol=1e-6)


def test_affine_rows_still_supported():
    A = np.eye(3)
    A[0, 2], A[1, 2] = 12.0, -7.0
    row6 = [float(v) for v in A[:2, :].ravel()]  # older caches store 6 numbers
    assert np.allclose(_cam_row_to_A(row6), A)
