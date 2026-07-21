"""Shot-type classification (events.classify_shot): pose + ball geometry."""

from swingvision.events import (
    classify_shot,
    classify_spin,
    infer_handedness,
    segment_rallies,
)


def _kpts(shoulder_x=500.0, shoulder_y=300.0, hip_y=450.0,
          wrist_y=None, nose_y=None):
    """A 17-keypoint COCO pose with confident shoulders (5,6) and hips (11,12).
    Optionally a confident nose (0) and right wrist (10)."""
    k = [[0.0, 0.0, 0.0] for _ in range(17)]
    if nose_y is not None:
        k[0] = [shoulder_x, nose_y, 0.9]        # nose
    k[5] = [shoulder_x - 20, shoulder_y, 0.9]   # left shoulder
    k[6] = [shoulder_x + 20, shoulder_y, 0.9]   # right shoulder
    if wrist_y is not None:
        k[10] = [shoulder_x + 30, wrist_y, 0.9]  # right wrist
    k[11] = [shoulder_x - 20, hip_y, 0.9]       # left hip
    k[12] = [shoulder_x + 20, hip_y, 0.9]       # right hip
    return k


def test_serve_takes_priority():
    assert classify_shot(0, 0, is_serve=True, striker_kpts=_kpts()) == "serve"


def test_overhead_needs_ball_high_AND_wrist_raised():
    # A real smash: ball above the shoulders AND the racket arm extended
    # overhead (wrist above the head).
    k = _kpts(shoulder_y=300.0, hip_y=450.0, nose_y=250.0, wrist_y=200.0)
    assert classify_shot(0, 0, striker_kpts=k, contact_xy_img=(500.0, 180.0)) == "overhead"


def test_high_camera_groundstroke_is_not_overhead():
    # From an elevated camera a waist-high contact BEYOND the player projects
    # above their shoulder line — but their hands stay down. The old
    # ball-vs-shoulders test called this an overhead; the wrist cue (same body,
    # same depth) must not.
    k = _kpts(shoulder_y=300.0, hip_y=450.0, nose_y=250.0, wrist_y=400.0)
    got = classify_shot(0, 0, handedness="right", facing_away=True,
                        striker_kpts=k, contact_xy_img=(560.0, 180.0))
    assert got == "forehand"


def test_volley_when_no_bounce_before_contact():
    # Normal contact height + volleyed flag -> volley (not overhead).
    k = _kpts()
    assert classify_shot(0, 0, volleyed=True, striker_kpts=k,
                         contact_xy_img=(500.0, 380.0)) == "volley"


def test_forehand_backhand_from_pose_side():
    k = _kpts(shoulder_x=500.0)
    # Right-hander facing away (near player): dominant side is image-right.
    fh = classify_shot(0, 0, handedness="right", facing_away=True,
                       striker_kpts=k, contact_xy_img=(560.0, 380.0))
    bh = classify_shot(0, 0, handedness="right", facing_away=True,
                       striker_kpts=k, contact_xy_img=(440.0, 380.0))
    assert fh == "forehand"
    assert bh == "backhand"


def test_left_hander_mirrors_sides():
    k = _kpts(shoulder_x=500.0)
    # Left-hander facing away: image-right contact is the BACKHAND side.
    assert classify_shot(0, 0, handedness="left", facing_away=True,
                         striker_kpts=k, contact_xy_img=(560.0, 380.0)) == "backhand"


def test_facing_toward_camera_mirrors_sides():
    k = _kpts(shoulder_x=500.0)
    # Far player faces the camera: image-right is now the backhand side.
    assert classify_shot(0, 0, facing_away=False, striker_kpts=k,
                         contact_xy_img=(560.0, 380.0)) == "backhand"


def test_falls_back_to_court_x_without_pose():
    # No pose: side from hit_x vs player_x. Right-hander facing away, ball to the
    # right (greater x) -> forehand.
    assert classify_shot(6.0, 5.0, handedness="right", facing_away=True) == "forehand"
    assert classify_shot(4.0, 5.0, handedness="right", facing_away=True) == "backhand"


# --- handedness inference ----------------------------------------------------

def test_infer_handedness_right_facing_away():
    # Majority of contacts on image-right, player facing away -> right-handed.
    assert infer_handedness([30, 40, -20, 55, 25, 60, 35], facing_away=True) == "right"


def test_infer_handedness_left_facing_away():
    # Majority on image-left, facing away -> left-handed.
    assert infer_handedness([-30, -40, 20, -55, -25, -60, -35], facing_away=True) == "left"


def test_infer_handedness_facing_camera_mirrors():
    # Same image-left majority but FACING the camera -> that's their right side.
    assert infer_handedness([-30, -40, 20, -55, -25, -60, -35], facing_away=False) == "right"


def test_infer_handedness_conservative_defaults():
    # Too few shots, or no clear majority -> default right (never guess "left").
    assert infer_handedness([-30, -40, -55], facing_away=True) == "right"
    assert infer_handedness([30, -40, 20, -55, 25, -60, 35, -20], facing_away=True) == "right"


# --- rally segmentation ------------------------------------------------------

def test_segment_rallies_by_gap():
    assert segment_rallies([0.0, 1.0, 2.0, 9.0, 10.0], gap_s=4.0) == [[0, 1, 2], [3, 4]]


def test_segment_rallies_double_bounce_forces_break():
    # Second bounce after shot 1 ends the point: shot 2 starts a NEW rally even
    # though it is within the time gap.
    got = segment_rallies([0.0, 1.0, 2.0, 3.0], gap_s=4.0, force_break_after=[1])
    assert got == [[0, 1], [2, 3]]


# --- spin (slice/topspin) heuristic -------------------------------------------

def _spin_window(y_path):
    """Keypoint windows where the right wrist follows y_path (image y)."""
    win = []
    for y in y_path:
        k = _kpts(shoulder_y=300.0, hip_y=400.0, wrist_y=y)
        win.append(k)
    return win


def test_classify_spin_topspin_low_to_high():
    # Wrist rises through contact (image y decreases) by > 0.35 torso -> topspin.
    win = _spin_window([420, 400, 380, 360, 340, 320, 300])
    assert classify_spin(win, contact_xy_img=(530.0, 360.0)) == "topspin"


def test_classify_spin_slice_high_to_low():
    win = _spin_window([300, 320, 340, 360, 380, 400, 420])
    assert classify_spin(win, contact_xy_img=(530.0, 360.0)) == "slice"


def test_classify_spin_flat_when_level():
    win = _spin_window([360, 361, 360, 359, 360, 361, 360])
    assert classify_spin(win, contact_xy_img=(530.0, 360.0)) == "flat"


def test_classify_spin_unknown_without_wrist():
    win = [_kpts() for _ in range(7)]   # no confident wrist anywhere
    assert classify_spin(win, contact_xy_img=(530.0, 360.0)) == ""


class TestPhysicalEventRules:
    """A rally shot is struck on one side and lands on the other (Session E3g/h).

    Both rules came from measurement, not intuition. Against the HUD's stroke
    list on yt_rally2: 15 of 29 candidate hits were phantoms, and every one of
    the 14 real ones kept the ball on the striker's side while 10 phantoms
    crossed the net immediately. Separately, 11 of 15 shots had their "landing"
    on the striker's OWN side, 2-5 m from the contact, and those carried a 56%
    median speed error against 24% for the ones that crossed.
    """

    FPS = 60.0

    def _track(self, ys, fps=None):
        fps = fps or self.FPS
        return [(i / fps, 5.0, y) for i, y in enumerate(ys)]

    def test_midflight_candidate_is_dropped(self):
        from swingvision import court, events
        # Ball starts just past the net and keeps going: not a contact.
        ys = [court.NET_Y - 0.5 + 0.4 * i for i in range(40)]
        assert events.drop_midflight_hits([0], self._track(ys)) == []

    def test_real_contact_at_the_baseline_is_kept(self):
        from swingvision import court, events
        # Struck near the far baseline, still on that side 0.33 s later.
        ys = [court.LENGTH - 1.0 - 0.05 * i for i in range(40)]
        assert events.drop_midflight_hits([0], self._track(ys)) == [0]

    def test_bounce_must_land_across_the_net(self):
        from swingvision import court, events
        n = 60
        # Hit at frame 0 on the near side; the ball never crosses the net.
        track = self._track([2.0 + 0.02 * i for i in range(n)])
        # An image-row maximum mid-span would otherwise be taken as the landing.
        ball_img = [[100.0, 200.0 + (30.0 if i == 30 else 0.0)] for i in range(n)]
        same_side = events.detect_bounces_between_hits(
            ball_img, [0, n - 1], n, track=track, require_cross_net=True)
        assert same_side == [], "a landing on the striker's own side is not a landing"

        # Same shape, but the ball does cross: the landing is accepted.
        crossed = self._track([2.0 + 0.4 * i for i in range(n)])
        assert crossed[30][2] > court.NET_Y
        assert events.detect_bounces_between_hits(
            ball_img, [0, n - 1], n, track=crossed, require_cross_net=True) == [30]

    def test_rule_can_be_disabled_for_footage_without_calibration(self):
        from swingvision import events
        n = 60
        ball_img = [[100.0, 200.0 + (30.0 if i == 30 else 0.0)] for i in range(n)]
        assert events.detect_bounces_between_hits(
            ball_img, [0, n - 1], n, require_cross_net=False) == [30]
