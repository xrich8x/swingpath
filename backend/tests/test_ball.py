"""Trajectory smoothing: gap filling and denoising (ball.smooth_and_fill)."""

import numpy as np
import pytest

from swingvision.ball import smooth_and_fill


def test_fills_interior_gap():
    # A straight track with a missing middle frame should be linearly filled.
    positions = [(0.0, 0.0), None, (2.0, 2.0)]
    out = smooth_and_fill(positions, window=3, polyorder=1)
    assert out.shape == (3, 2)
    assert not np.isnan(out).any()
    assert np.allclose(out[1], (1.0, 1.0), atol=1e-6)


def test_edge_fill_and_shape():
    positions = [None, (1.0, 5.0), (2.0, 6.0), None]
    out = smooth_and_fill(positions, window=3, polyorder=1)
    assert out.shape == (4, 2)
    assert not np.isnan(out).any()


def test_smoothing_reduces_noise():
    rng = np.random.default_rng(1)
    n = 60
    t = np.linspace(0, 1, n)
    clean = np.column_stack([t * 10.0, t * 5.0])
    noisy = clean + rng.normal(scale=0.2, size=clean.shape)
    out = smooth_and_fill([tuple(p) for p in noisy], window=11, polyorder=2)
    # Smoothed track should be closer to the underlying line than the raw noise.
    assert np.abs(out - clean).mean() < np.abs(noisy - clean).mean()


def test_empty_track():
    out = smooth_and_fill([])
    assert out.shape == (0, 2)


def test_tracker_court_gate():
    """BallTracker._court_ok: candidates back-projecting far off-court are rejected;
    the acquire bound is stricter than the continue bound."""
    from swingvision.ball import BallTracker
    from swingvision import court

    # Simple metric homography: image px = 10 * court metres (no perspective).
    H = np.diag([10.0, 10.0, 1.0])

    class _NoopDet:
        def detect(self, frame):
            return None

    tr = BallTracker(_NoopDet(), (1920, 1080), homography=H)
    centre = (10 * court.DOUBLES_WIDTH / 2, 10 * court.LENGTH / 2)
    assert tr._court_ok(centre, acquiring=True)
    # 6 m behind the baseline: too far to START a track, fine to CONTINUE one.
    deep = (10 * court.DOUBLES_WIDTH / 2, 10 * (court.LENGTH + 6.0))
    assert not tr._court_ok(deep, acquiring=True)
    assert tr._court_ok(deep, acquiring=False)
    # 30 m beyond the baseline (the crowd): rejected in every state.
    crowd = (10 * court.DOUBLES_WIDTH / 2, 10 * (court.LENGTH + 30.0))
    assert not tr._court_ok(crowd, acquiring=False)
    # Without a homography the gate is disabled.
    tr2 = BallTracker(_NoopDet(), (1920, 1080))
    assert tr2._court_ok(crowd, acquiring=True)


def test_tracker_subthreshold_rescue():
    """While coasting mid-track, the tracker may accept a detector's best
    below-threshold response (last_sub) if it lies on the predicted path — but
    never to START a track, and never from inside a player box."""
    from swingvision.ball import BallTracker

    class _ScriptedDet:
        """Confident detections for a few frames, then only weak responses that
        continue the same motion."""
        def __init__(self):
            self.t = -1
            self.last_sub = None

        def detect(self, frame):
            self.t += 1
            x = 100.0 + 20.0 * self.t
            if self.t < 3:
                self.last_sub = None
                return (x, 500.0)
            self.last_sub = (x, 500.0)   # weak but on-path
            return None

    tr = BallTracker(_ScriptedDet(), (1920, 1080), use_bgsub=False, rescue=True)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    pts = [tr.update(frame) for _ in range(6)]
    # Locked through the weak frames instead of dropping out.
    assert all(p is not None for p in pts[1:]), pts
    assert tr.n_sub >= 2
    # But rescue never STARTS a track: weak-only from frame 0 stays unlocked.
    class _WeakOnly:
        def __init__(self):
            self.last_sub = (200.0, 200.0)

        def detect(self, frame):
            return None

    tr2 = BallTracker(_WeakOnly(), (1920, 1080), use_bgsub=False, rescue=True)
    assert all(tr2.update(frame) is None for _ in range(5))
    assert tr2.n_sub == 0


def test_tracker_rescue_respects_player_boxes():
    from swingvision.ball import BallTracker

    class _Det:
        def __init__(self):
            self.t = -1
            self.last_sub = None

        def detect(self, frame):
            self.t += 1
            x = 100.0 + 20.0 * self.t
            if self.t < 3:
                self.last_sub = None
                return (x, 500.0)
            self.last_sub = (x, 500.0)
            return None

    tr = BallTracker(_Det(), (1920, 1080), use_bgsub=False, rescue=True)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    box = (100, 400, 400, 600)   # player box covering the weak candidates
    pts = [tr.update(frame, exclude_boxes=[box]) for _ in range(6)]
    assert tr.n_sub == 0, "rescue must not fire inside a player box"


def test_tracker_static_lock_gate():
    """A detection that sits still for static_min_run frames is a fixture
    (burned-in HUD graphic, logo, net post), not a ball: the track is dropped,
    the spot is remembered, and the tracker never re-locks there."""
    from swingvision.ball import BallTracker

    class _StuckDet:
        def detect(self, frame):
            return (400.0, 200.0)   # HUD logo: never moves

    tr = BallTracker(_StuckDet(), (1920, 1080), use_bgsub=False)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    pts = [tr.update(frame) for _ in range(20)]
    # The first static_min_run-1 emissions necessarily leak (a frozen lock is
    # only knowable in hindsight); everything after is suppressed for good.
    assert all(p is not None for p in pts[:4])
    assert all(p is None for p in pts[4:])
    assert tr.n_static == 1


def test_tracker_static_gate_spares_moving_ball():
    """Clean footage (no burned-in HUD): a normally moving ball never trips
    the static gate — output is identical to a gate-less tracker."""
    from swingvision.ball import BallTracker

    class _MovingDet:
        def __init__(self):
            self.t = -1

        def detect(self, frame):
            self.t += 1
            return (100.0 + 20.0 * self.t, 500.0)

    tr = BallTracker(_MovingDet(), (1920, 1080), use_bgsub=False)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    pts = [tr.update(frame) for _ in range(15)]
    assert all(p is not None for p in pts)
    assert tr.n_static == 0 and not tr.static_anchors


def test_tracker_reacquires_real_ball_after_fixture():
    """After a fixture is suppressed the tracker is free again: a moving ball
    appearing elsewhere is acquired immediately."""
    from swingvision.ball import BallTracker

    class _HudThenBall:
        def __init__(self):
            self.t = -1

        def detect(self, frame):
            self.t += 1
            if self.t < 8:
                return (400.0, 200.0)              # stuck on the HUD
            return (800.0 + 25.0 * self.t, 600.0)  # the real ball, moving

    tr = BallTracker(_HudThenBall(), (1920, 1080), use_bgsub=False)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    pts = [tr.update(frame) for _ in range(16)]
    assert all(p is None for p in pts[4:8]), "fixture stays suppressed"
    assert all(p is not None for p in pts[8:]), "real ball reacquired"
    assert tr.n_static == 1


def test_filter_live_ball_motion():
    """Offline live-ball filter: a moving run is kept; a brief low-motion
    flicker (a detector twitch on a graphic) is dropped. No homography -> only
    the motion test applies."""
    from swingvision.ball import filter_live_ball

    moving = [[100.0 + 15 * i, 200.0 + 5 * i] for i in range(6)]   # real ball
    flick = [[600.0, 50.0], [601.0, 50.3], [600.4, 49.6]]         # 3-frame twitch
    track = [None] + moving + [None] + flick + [None]
    out = filter_live_ball(track)
    assert out[1:7] == moving, "a clearly moving run must be kept"
    assert all(p is None for p in out[8:11]), "a short low-motion flicker is dropped"


def test_filter_live_ball_offcourt():
    """With a homography, a run that never reaches the play area (adjacent
    court) is dropped even though it moves like a ball; an on-court run is
    kept."""
    from swingvision import court
    from swingvision.ball import filter_live_ball

    H = np.diag([10.0, 10.0, 1.0])   # court metres -> image px * 10
    on = [[10 * (2.0 + 0.3 * i), 10 * (11.0 + 0.2 * i)] for i in range(6)]        # over the court
    off = [[10 * (2.0 + 0.3 * i), 10 * (court.LENGTH + 12.0)] for i in range(6)]  # adjacent court
    out = filter_live_ball(on + [None] + off, homography=H)
    assert out[0:6] == on, "an on-court moving run must be kept"
    assert all(p is None for p in out[7:13]), "an off-court run is dropped"


def test_cap_court_jumps_scales_with_gap():
    """The displacement budget must grow with elapsed frames (E3b regression).

    The old gap-blind cap culled the first re-detection after any dropout —
    the ball had legitimately flown further than one frame's budget — and then
    cascaded, comparing every later point to an ever-staler anchor (measured:
    830 in-court points -> 113 on yt_rally2 @60fps)."""
    from swingvision.ball import cap_court_jumps

    # 1.4 m/frame budget; ball at 1.0 m/frame with a 10-frame dropout.
    track = [[0.0, 1.0 * i] for i in range(5)] + [None] * 10 \
        + [[0.0, 1.0 * i] for i in range(15, 25)]
    out = cap_court_jumps(track, max_step_m=1.4)
    kept = sum(p is not None for p in out)
    assert kept == 15, f"legit points after a gap must survive (kept {kept}/15)"

    # A genuine teleport (adjacent court, same instant) must still die.
    spike = [[0.0, 0.0], [0.0, 1.0], [0.0, 25.0], [0.0, 2.0]]
    out = cap_court_jumps(spike, max_step_m=1.4)
    assert out[2] is None, "a single-frame teleport must still be culled"
    assert out[3] is not None

    # And a long gap must not launder one: budget is capped absolutely.
    laundered = [[0.0, 0.0]] + [None] * 100 + [[0.0, 80.0]]
    out = cap_court_jumps(laundered, max_step_m=1.4, max_gap_allowance_m=30.0)
    assert out[-1] is None, "a 80 m jump is unphysical no matter the gap"


def test_static_gate_thresholds_scale_with_frame_rate():
    """The fixture gate is a TIME test, not a per-frame one (E3c regression).

    Tuned at 30fps (3 px/frame over 5 frames), it was applied unchanged at 60fps
    — where the same physical motion covers half the pixels per frame. Measured
    on yt_rally2 @60fps, 36.3% of FAR-court ball steps fell under 3 px/frame
    (near court: 8.5%), so the gate was discarding the far ball."""
    from swingvision.ball import BallTracker

    class _Noop:
        def reset(self):
            pass

        def detect(self, frame):
            return None

    at30 = BallTracker(_Noop(), (1280, 720), use_bgsub=False, fps=30.0)
    at60 = BallTracker(_Noop(), (1280, 720), use_bgsub=False, fps=60.0)

    # 30fps keeps the historical values exactly — no silent behaviour change.
    assert at30.static_step_px == pytest.approx(3.0)
    assert at30.static_min_run == 5

    # 60fps halves the per-frame step and doubles the run: same physical test.
    assert at60.static_step_px == pytest.approx(1.5)
    assert at60.static_min_run == 10

    # A true fixture (0 px/frame) is still caught at any rate; a far ball moving
    # 4.6 px/frame at 60fps (the measured median) now passes.
    assert 0.0 < at60.static_step_px < 4.6

    # Explicit values still win, so existing callers/experiments are unaffected.
    forced = BallTracker(_Noop(), (1280, 720), use_bgsub=False, fps=60.0,
                         static_step_px=3.0, static_min_run=5)
    assert forced.static_step_px == pytest.approx(3.0)
    assert forced.static_min_run == 5


def test_rectify_track_kills_sustained_wrong_locks():
    """The robust rectifier catches what remove_outliers cannot (E3i).

    remove_outliers only nulls a lone spike flanked by two good points. A
    sustained wrong lock (detector riding a fixture for a few frames) and a
    spike next to a gap both survive it — and those are the jumps that make the
    drawn trail go awry."""
    from swingvision.ball import rectify_track, remove_outliers

    # A ball moving steadily right, then 3 frames stuck on a fixture far away,
    # then back on the real path.
    track = [[100.0 + 8.0 * i, 200.0] for i in range(8)]
    track[4] = track[5] = track[6] = [600.0, 500.0]   # fixture, 3 frames
    ro = remove_outliers([list(p) for p in track], max_jump=76)
    assert ro[4] is not None, "remove_outliers misses a SUSTAINED wrong lock"

    rec = rectify_track(track, max_speed_px=60.0, resid_px=40.0)
    assert rec[4] is None and rec[5] is None and rec[6] is None
    # the genuine steady points survive
    assert rec[0] is not None and rec[7] is not None


def test_rectify_track_keeps_a_fast_but_consistent_ball():
    """A genuinely fast ball moving in a straight line is NOT an outlier."""
    from swingvision.ball import rectify_track

    fast = [[100.0 + 55.0 * i, 300.0] for i in range(10)]   # 55 px/frame, steady
    rec = rectify_track(fast, max_speed_px=60.0, resid_px=40.0)
    assert all(p is not None for p in rec), "a steady fast ball must be kept"


def test_rectify_track_handles_spike_next_to_a_gap():
    from swingvision.ball import rectify_track
    track = [[100.0, 200.0], [108.0, 200.0], [116.0, 200.0], None,
             [900.0, 90.0],                     # spike with a gap before it
             [132.0, 200.0], [140.0, 200.0]]
    rec = rectify_track(track, max_speed_px=60.0, resid_px=40.0)
    assert rec[4] is None
