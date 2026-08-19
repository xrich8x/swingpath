"""Coverage-gating for player movement stats.

WHY THIS EXISTS
---------------
`distance_run_m` is a path INTEGRAL over per-frame player positions, and it was
reported unconditionally. Measured on the committed perception caches the far
player is located on **1.0%** of frames (am_hard_utr), 11.0% (yt_match40) and
9.6% (demo30) — so player "B" came back as a confident `0.0` on every real clip
and the dashboard drew a zero-length bar beside that player's name.

The failure is not noise, it is DIRECTION: `_distance_run_m` forward-fills gaps,
so a sparse track becomes a flat path rather than a jagged one. Low coverage
therefore produces a small, precise-looking number instead of an obviously
broken one — the same trap `compute_stats` already fixed for speed ("reporting
0.0 was indistinguishable from a broken pipeline").

These tests pin the distinction that fix rests on: **None means not measurable,
and is not the same value as 0.0.**
"""

import pytest

from swingvision import pipeline


# --- _track_coverage: the denominator behind the gate -----------------------

def test_coverage_counts_missing_frames_not_just_present_ones():
    # 2 of 8 processed frames located -> 25%, NOT 100% of the 2 we happen to have.
    positions = [None, (1.0, 2.0), None, None, (1.1, 2.1), None, None, None]
    assert pipeline._track_coverage(positions) == pytest.approx(0.25)


def test_coverage_of_empty_and_fully_missing_tracks_is_zero():
    assert pipeline._track_coverage([]) == 0.0
    assert pipeline._track_coverage([None, None, None]) == 0.0


def test_coverage_of_complete_track_is_one():
    assert pipeline._track_coverage([(0.0, 0.0)] * 5) == 1.0


# --- The gate itself --------------------------------------------------------

def test_the_bar_is_the_projects_existing_seen_fraction_bar():
    """Not an invented threshold: the >=50% seen-fraction bar the project already
    uses to call a speed trusted (SCOREBOARD, Session M part 2). If this changes,
    it should change deliberately and for a stated reason."""
    assert pipeline.MIN_TRACK_COVERAGE == 0.50


def test_sparse_track_understates_rather_than_looking_broken():
    """The reason the gate is needed at all, demonstrated rather than asserted.

    A player who genuinely runs back and forth, sampled on only a few frames,
    forward-fills into a much SHORTER path than the same motion fully tracked.
    A reader cannot tell that number is wrong by looking at it.
    """
    fps = 30.0
    dense = [(0.0, float(i % 6)) for i in range(120)]
    sparse = [p if i % 20 == 0 else None for i, p in enumerate(dense)]

    d_dense = pipeline._distance_run_m(dense, fps)
    d_sparse = pipeline._distance_run_m(sparse, fps)

    assert pipeline._track_coverage(sparse) < pipeline.MIN_TRACK_COVERAGE
    assert d_sparse < d_dense          # sparse UNDERSTATES...
    assert d_sparse >= 0.0             # ...and still looks like a clean number


# --- The user-visible contract ---------------------------------------------

# --- IDENTITY: the failure coverage cannot see -----------------------------

def test_doubles_refuses_even_on_a_perfectly_dense_track():
    """The whole reason this is a separate check and not a stricter threshold.

    `pose.select_players_on_court` keeps ONE slot per court half (deliberate —
    see tests/test_doubles.py), so in doubles that slot swaps between partners.
    Coverage stays at 100% throughout, so the density gate sees nothing wrong.
    """
    dense = [(float(i % 4), 5.0) for i in range(120)]
    assert pipeline._track_coverage(dense) == 1.0      # density is perfect...

    d_singles, cov_s, why_s = pipeline._reportable_distance(dense, 30.0, singles=True)
    d_doubles, cov_d, why_d = pipeline._reportable_distance(dense, 30.0, singles=False)

    assert d_singles is not None and why_s is None     # ...and singles reports it
    assert d_doubles is None                           # ...but doubles refuses
    assert cov_d == 1.0                                # NOT because of coverage
    assert "doubles" in why_d


def test_refusal_always_carries_a_reason_and_a_number_never_does():
    sparse = [None] * 90 + [(1.0, 1.0)] * 10
    dense = [(float(i % 4), 5.0) for i in range(120)]

    _, _, why_sparse = pipeline._reportable_distance(sparse, 30.0, singles=True)
    _, _, why_doubles = pipeline._reportable_distance(dense, 30.0, singles=False)
    val, _, why_ok = pipeline._reportable_distance(dense, 30.0, singles=True)

    # The two refusals must be DISTINGUISHABLE — the UI explains them differently.
    assert why_sparse and why_doubles and why_sparse != why_doubles
    assert "%" in why_sparse and "doubles" not in why_sparse
    assert isinstance(val, float) and why_ok is None


def test_coverage_is_reported_even_when_the_distance_is_refused():
    """Coverage is the denominator; it must survive the refusal so the user can
    see HOW badly tracked a player was, not just that we gave up."""
    sparse = [None] * 95 + [(1.0, 1.0)] * 5
    dist, cov, why = pipeline._reportable_distance(sparse, 30.0, singles=True)
    assert dist is None and why
    assert cov == pytest.approx(0.05)


def test_none_and_zero_are_different_answers():
    """The whole point of the field. A player who stood still has 0.0; a player
    we could not track has None. Collapsing these is the bug being fixed."""
    still = [(5.0, 5.0)] * 60          # fully tracked, genuinely stationary
    assert pipeline._track_coverage(still) >= pipeline.MIN_TRACK_COVERAGE
    assert pipeline._distance_run_m(still, 30.0) == 0.0

    missing = [None] * 60              # never tracked
    assert pipeline._track_coverage(missing) < pipeline.MIN_TRACK_COVERAGE


# --- the depth bias in _reject_static_player (measured 2026-08-17) ----------

def _fake_track(n, step_px, body_px, start=(500.0, 300.0)):
    """A player walking steadily at `step_px` per sample, with a body `body_px`
    tall. Position list and keypoint list, as the pipeline holds them."""
    pos, kpts = [], []
    for i in range(n):
        x = start[0] + i * step_px
        y = start[1]
        pos.append((x / 50.0, y / 50.0))
        # two keypoints, body_px apart vertically -> a measurable body height
        kpts.append([[x, y, 0.9], [x, y + body_px, 0.9]])
    return pos, kpts


def test_fixed_radii_delete_a_moving_far_player():
    """The bug: identical MOTION relative to body size, opposite verdicts.

    Both tracks move the same distance in body-heights - i.e. both are equally
    'a person who ran' - but the near one is big on screen and the far one small.
    The shipped fixed 20 px radius keeps the near one and deletes the far one.
    """
    near_pos, near_k = _fake_track(60, step_px=2.0, body_px=110.0)
    far_pos, far_k = _fake_track(60, step_px=0.30, body_px=16.0)

    near_out, _ = pipeline._reject_static_player(list(near_pos), list(near_k), "near")
    far_out, _ = pipeline._reject_static_player(list(far_pos), list(far_k), "far")

    near_kept = sum(1 for p in near_out if p)
    far_kept = sum(1 for p in far_out if p)
    assert near_kept == 60, "the near player must survive (it does today)"
    assert far_kept == 0, "documents the bug: the far player is wiped"


def test_body_relative_radii_keep_the_same_far_player():
    """The fix: judge motion against the track's OWN size, which is depth-invariant."""
    far_pos, far_k = _fake_track(60, step_px=0.30, body_px=16.0)
    kept_fixed, _ = pipeline._reject_static_player(list(far_pos), list(far_k), "far")
    kept_rel, _ = pipeline._reject_static_player(list(far_pos), list(far_k), "far",
                                                 body_relative=True)
    assert sum(1 for p in kept_fixed if p) == 0
    assert sum(1 for p in kept_rel if p) == 60


def test_body_relative_still_rejects_a_genuine_fixture():
    """The guard must not be traded away. A poster does not move relative to its
    own size either, so normalising by size keeps the fixture test working."""
    pos, kpts = _fake_track(60, step_px=0.0, body_px=16.0)   # perfectly static
    out, _ = pipeline._reject_static_player(list(pos), list(kpts), "far",
                                            body_relative=True)
    assert sum(1 for p in out if p) == 0, "a static object must still be rejected"


def test_body_relative_is_off_by_default():
    """Not shipped: one clip, and the fixture population it guards against is not
    represented in any gold clip. Pin the default so it cannot drift in silently."""
    import inspect
    sig = inspect.signature(pipeline._reject_static_player)
    assert sig.parameters["body_relative"].default is False
