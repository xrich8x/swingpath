"""Trajectory smoothing: gap filling and denoising (ball.smooth_and_fill)."""

import math

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


def test_suppress_false_locks_persistent_fixture():
    """A lock that holds still for >=0.2s of frames is a fixture (HUD/net post):
    the whole slow-drifting run is wiped, while a real moving ball is kept."""
    from swingvision.ball import suppress_false_locks

    ball = [[100.0 + 20 * i, 200.0 + 8 * i] for i in range(8)]      # clear trajectory
    fixture = [[600.0 + 0.4 * i, 50.0 - 0.3 * i] for i in range(10)]  # creeps <12px
    out = suppress_false_locks(ball + [None] + fixture, fps_eff=30.0)
    assert out[0:8] == ball, "a moving ball run must survive"
    assert all(p is None for p in out[9:19]), "a persistent near-static run is wiped"


def test_suppress_false_locks_short_excursion():
    """A 1-3 frame mislock that never forms a >=0.15s trajectory is dropped;
    a sustained ball-plausible segment is kept."""
    from swingvision.ball import suppress_false_locks

    ball = [[100.0 + 25 * i, 300.0 - 6 * i] for i in range(7)]      # 7-frame track
    blip = [[900.0, 80.0], [40.0, 500.0]]                          # 2-frame jumpy blip
    out = suppress_false_locks(ball + [None] + blip, fps_eff=30.0)
    assert out[0:7] == ball, "a sustained ball segment must survive"
    assert all(p is None for p in out[8:10]), "a 2-frame chaotic blip is dropped"


def test_suppress_false_locks_scales_with_fps():
    """The static duration is a TIME, not a frame count: at 60fps it takes twice
    as many frames to call a lock a fixture."""
    from swingvision.ball import suppress_false_locks

    fixture = [[500.0, 100.0] for _ in range(7)]   # 7 identical frames
    # 0.2s = 6 frames at 30fps -> the 7-frame static run is a fixture, wiped. The
    # moving tail starts well away from the fixture so it forms its own segment.
    moving = [[800.0 + 30 * i, 400.0 + 30 * i] for i in range(12)]
    at30 = suppress_false_locks(fixture + moving, fps_eff=30.0)
    assert all(p is None for p in at30[0:7]), "static run wiped at 30fps"
    assert at30[7:] == moving, "moving tail kept"


def test_coast_fill_follows_the_arc():
    """A mid-flight gap is filled along the ball's parabola, not a straight line:
    on data that IS a parabola the coast recovers it near-exactly, far closer than
    linear interpolation would."""
    from swingvision.ball import coast_fill

    true = [[10.0 * t, 2.0 * (t - 10) ** 2 + 100.0] for t in range(21)]
    gap = {7, 8, 9, 10, 11, 12, 13}                      # 7-frame gap, anchors 6 & 14
    track = [None if t in gap else list(true[t]) for t in range(21)]
    filled, coasted = coast_fill(track, fps_eff=30.0)
    assert math.dist(filled[10], true[10]) < 3.0, "arc-coast should recover the parabola"
    # a straight chord between anchors 6 and 14 floats ~32px above the true apex
    lin_y = true[6][1] + (true[14][1] - true[6][1]) * (10 - 6) / (14 - 6)
    assert abs(lin_y - true[10][1]) > 10.0, "sanity: linear really is far off here"
    assert coasted[10] is True and coasted[6] is False


def test_coast_fill_flags_guessed_frames():
    from swingvision.ball import coast_fill

    track = [[0.0, 0.0], [10.0, 5.0], None, None, [40.0, 20.0], [50.0, 25.0]]
    filled, coasted = coast_fill(track, fps_eff=30.0)
    assert all(p is not None for p in filled), "interior gap gets filled"
    assert coasted == [False, False, True, True, False, False]


def test_coast_fill_linear_fallback_across_a_hit():
    """Horizontal velocity reverses inside the gap (a hit/bounce) -> don't coast a
    single parabola through the corner; fall back to a straight line."""
    from swingvision.ball import coast_fill

    track = [[0.0, 50.0], [10.0, 40.0], [20.0, 30.0], None, None, None,
             [20.0, 30.0], [10.0, 40.0], [0.0, 50.0]]
    filled, coasted = coast_fill(track, fps_eff=30.0)
    # linear between [20,30] and [20,30] stays put; a parabola fit to the reversing
    # anchors would bulge sideways. Assert it did NOT bulge.
    assert abs(filled[4][0] - 20.0) < 1.0 and abs(filled[4][1] - 30.0) < 1.0
    assert coasted[4] is True


def test_coast_fill_leaves_edge_gaps_empty():
    """A gap with no anchor on one side is unbounded -> left empty, not guessed."""
    from swingvision.ball import coast_fill

    lead = coast_fill([None, None, [10.0, 10.0], [20.0, 12.0]], fps_eff=30.0)[0]
    assert lead[0] is None and lead[1] is None
    trail = coast_fill([[10.0, 10.0], [20.0, 12.0], None, None], fps_eff=30.0)[0]
    assert trail[2] is None and trail[3] is None


def test_smooth_forecast_denoises_and_preserves_line():
    """A noisy straight track is denoised: the smoothed points sit far closer to
    the true line than the noisy inputs, without lagging off it."""
    from swingvision.ball import smooth_forecast

    rng = np.random.default_rng(0)
    true = [(5.0 * t, 100.0 + 3.0 * t) for t in range(40)]
    noisy = [[x + rng.normal(0, 4), y + rng.normal(0, 4)] for x, y in true]
    sm, coasted, conf = smooth_forecast(noisy, fps_eff=30.0)
    raw_err = np.mean([math.dist(noisy[t], true[t]) for t in range(40)])
    sm_err = np.mean([math.dist(sm[t], true[t]) for t in range(5, 35)])
    assert sm_err < raw_err * 0.7, f"smoothing should cut error (raw {raw_err:.1f}, sm {sm_err:.1f})"
    assert not any(coasted), "no gaps -> nothing is a forecast"


def test_smooth_forecast_forecasts_through_a_gap():
    """A gap in a smooth track is forecast along the motion and flagged coasted."""
    from swingvision.ball import smooth_forecast

    track = [[5.0 * t, 100.0 + 2.0 * t] for t in range(30)]
    for t in (12, 13, 14, 15):
        track[t] = None
    sm, coasted, conf = smooth_forecast(track, fps_eff=30.0)
    assert sm[13] is not None and coasted[13] is True
    assert math.dist(sm[13], (5.0 * 13, 100.0 + 2.0 * 13)) < 6.0, "forecast should follow the line"
    assert conf[13] < conf[5], "confidence decays inside a gap"


def test_smooth_forecast_gates_an_outlier():
    """A single wild lock (a fixture flash) is rejected, not tracked."""
    from swingvision.ball import smooth_forecast

    track = [[5.0 * t, 100.0] for t in range(30)]
    track[15] = [900.0, 700.0]                     # teleport outlier
    sm, coasted, conf = smooth_forecast(track, fps_eff=30.0)
    assert math.dist(sm[15], (5.0 * 15, 100.0)) < 20.0, "outlier must be gated out"


def test_gate_ball_to_court_rejects_adjacent():
    """A lock inside the court's image trapezoid is kept; one far to the side (an
    adjacent court) is dropped. Simple affine homography: (x,y)m -> (30x+100, 700-30y)px."""
    from swingvision.ball import gate_ball_to_court

    H = np.array([[30.0, 0, 100], [0, -30, 700], [0, 0, 1]])
    track = [[265.0, 343.0], None, [850.0, 343.0]]   # on-court, gap, adjacent-court
    out = gate_ball_to_court(track, H, (1280, 720))
    assert out[0] == [265.0, 343.0], "on-court lock kept"
    assert out[1] is None
    assert out[2] is None, "adjacent-court lock rejected"


def test_gate_ball_to_court_no_homography_passthrough():
    """No calibration -> keep every lock (an amateur clip must not lose the ball)."""
    from swingvision.ball import gate_ball_to_court

    track = [[10.0, 10.0], None, [900.0, 50.0]]
    assert gate_ball_to_court(track, None, (1280, 720)) == [[10.0, 10.0], None, [900.0, 50.0]]


def _pts_homography(kp_names, kp_px):
    from swingvision import calibration, court

    return calibration.compute_homography([court.LANDMARKS[n] for n in kp_names], kp_px)


def test_smooth_forecast_is_scale_equivariant():
    """The same scene at 1.5x resolution must give exactly 1.5x the track.

    Without it the innovation gate y'S^-1y inflates by the square of the scale
    (S built from a 720p meas_var, y measured in 1080p pixels), so real detections
    are rejected as outliers on bigger frames.
    """
    from swingvision.ball import smooth_forecast

    track = [[40.0 + 9 * i, 300.0 - 0.4 * i * i] for i in range(24)]
    track[7] = [track[7][0] + 55.0, track[7][1] - 55.0]      # one outlier to gate
    base, cb, _ = smooth_forecast(track, fps_eff=30.0)

    s = 1.5
    big = [[p[0] * s, p[1] * s] for p in track]
    scaled, cs, _ = smooth_forecast(big, fps_eff=30.0, res_scale=s)

    assert cb == cs, "the same frame must be gated/coasted at either resolution"
    for a, b in zip(base, scaled):
        assert (a is None) == (b is None)
        if a is not None:
            assert abs(a[0] * s - b[0]) < 1e-6 and abs(a[1] * s - b[1]) < 1e-6

    # res_scale=1.0 is the shipped 720p path, untouched.
    same, _, _ = smooth_forecast(track, fps_eff=30.0, res_scale=1.0)
    assert same == base


def test_tracker_gate_scales_with_frame_height():
    """The velocity-association radius is in pixels, so it must follow the frame
    size. Identity at 720p; 1.5x at 1080p."""
    from swingvision.ball import BallTracker

    class _Null:
        def reset(self):
            pass

        def detect(self, frame):
            return None

    assert BallTracker(_Null(), (1280, 720), use_bgsub=False).gate == 70.0
    assert BallTracker(_Null(), (1920, 1080), use_bgsub=False).gate == 105.0


def test_suppress_min_segment_survives_a_detector_blink():
    """A real trajectory with one missed frame in the middle must survive.

    The min-segment test used to require STRICTLY consecutive detections while its
    length threshold scaled with fps, so at 60 fps it demanded 9 unbroken locks —
    at a realistic ~60% per-frame recall, roughly a 1% event. One blink split a
    real ball's run in two and both halves fell under the bar and were deleted.
    """
    from swingvision.ball import suppress_false_locks

    # A ball crossing the frame at ~40 px/frame for 12 frames, blinking once.
    track = [[100.0 + 40 * i, 300.0 + 12 * i] for i in range(12)]
    track[6] = None

    strict = suppress_false_locks(list(track), fps_eff=60.0, seg_gap_s=0.0)
    lenient = suppress_false_locks(list(track), fps_eff=60.0, seg_gap_s=0.05)

    assert sum(p is not None for p in strict) == 0, "test no longer pins the bug"
    assert sum(p is not None for p in lenient) == 11, "the blink must be bridged"

    # Bridging must not smuggle in a teleport: the step budget scales with the gap.
    jump = [[100.0, 300.0], [140.0, 312.0], None, [9000.0, 9000.0], [9040.0, 9012.0]]
    out = suppress_false_locks(jump, fps_eff=60.0, seg_gap_s=0.05)
    assert out[3] is None and out[4] is None, "a gap must not license a teleport"


def test_suppress_res_scale_is_identity_at_720p():
    """res_scale=1.0 must reproduce the shipped 720p behaviour bit for bit, and a
    1080p scale must be more permissive (a real ball covers 1.5x the pixels there,
    so the same track must not become 'too jumpy to be a trajectory')."""
    from swingvision.ball import suppress_false_locks

    # A ball moving ~55 px/frame at 720p; at 1080p the same motion is ~82 px/frame.
    t720 = [[100.0 + 55 * i, 300.0 + 20 * i] for i in range(12)]
    t1080 = [[150.0 + 82 * i, 450.0 + 30 * i] for i in range(12)]

    a = suppress_false_locks(t720, fps_eff=60.0)
    b = suppress_false_locks(t720, fps_eff=60.0, res_scale=1.0)
    assert a == b

    kept720 = sum(p is not None for p in suppress_false_locks(t720, fps_eff=60.0))
    kept1080 = sum(p is not None for p in
                   suppress_false_locks(t1080, fps_eff=60.0, res_scale=1080.0 / 720.0))
    assert kept1080 >= kept720, "the same physical track must survive at 1080p"


def test_smooth_forecast_scale_is_opt_in():
    """Passing no scale must reproduce the shipped behaviour exactly, and passing a
    flat scale must be a no-op (the rescale normalises on the clip's own spread)."""
    from swingvision.ball import smooth_forecast

    track = [[10.0 + 4 * i, 200.0 - 0.3 * i * i] for i in range(30)]
    base, _, _ = smooth_forecast(track, fps_eff=30.0)
    flat, _, _ = smooth_forecast(track, fps_eff=30.0, scale_m_per_px=[0.05] * 30)
    for a, b in zip(base, flat):
        assert (a is None) == (b is None)
        if a is not None:
            assert abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6

    # A varying scale must change something, or the option is doing nothing at all.
    ramp, _, _ = smooth_forecast(track, fps_eff=30.0,
                                 scale_m_per_px=[0.02 + 0.02 * i for i in range(30)])
    assert any(abs(a[0] - c[0]) > 1e-9 or abs(a[1] - c[1]) > 1e-9
               for a, c in zip(base, ramp) if a is not None and c is not None)


def test_gate_scales_with_resolution():
    """The SAME scene at 720p and 1080p must gate identically.

    The old band was 220/120 px absolute, so doubling the frame height halved the
    airborne allowance in court terms. Measured on the am_hard_utr gold clicks it
    kept only 15.4% of far-court balls at 1080p (vs 100% of the 720p clips) — the
    gate, not the detector, was deleting the far ball.
    """
    from swingvision.ball import gate_ball_to_court

    names = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
    px720 = [[200.0, 640.0], [1080.0, 640.0], [520.0, 300.0], [760.0, 300.0]]
    H720 = _pts_homography(names, px720)
    H1080 = _pts_homography(names, [[x * 1.5, y * 1.5] for x, y in px720])

    # One ball, high over the far court: 200 px above the far edge at 720p, the
    # same place = 300 px above it at 1080p. The old absolute 220 px band keeps it
    # at 720p and rejects it at 1080p purely because the frame got bigger.
    lock720, lock1080 = [640.0, 100.0], [960.0, 150.0]
    keep = lambda t, H, wh, **kw: gate_ball_to_court([t], H, wh, **kw)[0] is not None

    assert keep(lock720, H720, (1280, 720)), "in play at 720p"
    assert keep(lock1080, H1080, (1920, 1080)), "same ball must stay in play at 1080p"
    # Pin the bug this replaced: with the margins frozen at their 720p values the
    # 1080p verdict flips. (Undo the scaling to reproduce the shipped behaviour.)
    assert not keep(lock1080, H1080, (1920, 1080),
                    top_extra_px=220.0 * 720.0 / 1080.0,
                    side_extra_px=120.0 * 1280.0 / 1920.0), "test no longer discriminates"


def test_gate_keeps_an_airborne_far_ball():
    """A lob over the far court is inside the PLAY VOLUME even though it is well
    outside the ground plane's trapezoid. The extruded box is what makes that a
    derivation instead of a tuned pixel margin."""
    from swingvision import calibration, court
    from swingvision.ball import gate_ball_to_court, play_volume_polygon

    names = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
    px = [[200.0, 640.0], [1080.0, 640.0], [520.0, 300.0], [760.0, 300.0]]
    H = _pts_homography(names, px)
    wh = (1280, 720)
    hfov = 70.0

    # Where a ball 4 m above the far baseline's midpoint actually appears.
    mid_x = court.DOUBLES_WIDTH / 2.0
    aloft = calibration.project_court_3d(H, wh, [(mid_x, court.LENGTH, 4.0)], hfov)
    assert aloft is not None, "pose must solve for this synthetic camera"
    p = [float(aloft[0][0]), float(aloft[0][1])]

    ground = calibration.court_to_image(H, [(mid_x, court.LENGTH)])[0]
    assert p[1] < ground[1], "an airborne ball sits ABOVE its ground point in frame"
    assert gate_ball_to_court([p], H, wh, hfov_deg=hfov)[0] is not None
    assert play_volume_polygon(H, wh, hfov_deg=hfov) is not None


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
