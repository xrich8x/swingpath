"""Auto-detect singles vs doubles from on-court player counts (pose.count_on_court,
pose.infer_doubles). The line-call boundary uses this; player tracking stays
two-slot."""

from swingvision import pose, calibration, court

_CN = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


class _StubPose:
    def __init__(self, xy):
        self._xy = xy

    def feet(self):
        return self._xy


def _H():
    img_pts = [(150, 320), (490, 320), (400, 95), (240, 95)]
    return calibration.compute_homography([court.LANDMARKS[n] for n in _CN], img_pts)


def _feet_at(H, x_m, y_m):
    return tuple(calibration.court_to_image(H, [(x_m, y_m)])[0])


def test_count_on_court_splits_by_half():
    H = _H()
    poses = [_StubPose(_feet_at(H, 3, 3)), _StubPose(_feet_at(H, 8, 4)),      # near
             _StubPose(_feet_at(H, 3, 20)), _StubPose(_feet_at(H, 8, 19))]    # far
    assert pose.count_on_court(poses, H) == (2, 2)


def test_count_ignores_people_off_court():
    H = _H()
    poses = [_StubPose(_feet_at(H, 4, 4)), _StubPose(_feet_at(H, 40, 40))]    # 2nd way off
    assert pose.count_on_court(poses, H) == (1, 0)


def test_infer_doubles():
    assert pose.infer_doubles([(2, 2)] * 10) is True
    assert pose.infer_doubles([(1, 1)] * 10) is False
    assert pose.infer_doubles([]) is False
    # a couple of noisy 2+2 frames in an otherwise-singles clip stays singles
    assert pose.infer_doubles([(1, 1)] * 9 + [(2, 2)]) is False
