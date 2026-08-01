"""inspect_false_locks.describe — the roam/runLen pair that separates a fixture
from a ball without touching the court projection.

This is the same physical argument suppress_false_locks rests on: a real ball is
always traversing the frame, a fixture holds still, and a mislock on a player
flares for a few frames without forming a track.
"""

from inspect_false_locks import describe


def test_a_fixture_holds_a_long_run_and_barely_roams():
    locks = [[100.0, 100.0]] * 12
    roam, run = describe(locks, 6, None)
    assert run == 12
    assert roam == 0.0


def test_a_traversing_ball_roams_far_and_holds_no_run():
    locks = [[30.0 * i, 30.0 * i] for i in range(12)]
    roam, run = describe(locks, 6, None)
    assert run == 1                      # leaves the 15 px radius immediately
    assert roam > 100


def test_the_15px_radius_is_a_real_boundary_not_a_formality():
    """A ball crossing 10 px/frame diagonally moves 14.1 px — INSIDE the radius —
    so it still registers a 3-frame run. Documented rather than tuned away: it is
    why runLen alone never decides anything here and is always read next to roam,
    which is 100+ px for the same track."""
    locks = [[10.0 * i, 10.0 * i] for i in range(12)]
    roam, run = describe(locks, 6, None)
    assert run == 3
    assert roam > 100


def test_a_slow_drift_still_counts_as_a_run_within_the_radius():
    """The case the online per-frame static gate misses: a lock creeping below
    its step threshold. Run length catches the whole drift."""
    locks = [[100.0 + 1.0 * i, 100.0] for i in range(10)]
    roam, run = describe(locks, 0, None)
    assert run == 10
    assert roam < 15


def test_gaps_end_the_run_but_not_the_roam_window():
    locks = [[100.0, 100.0], None, [100.0, 100.0], [400.0, 400.0]]
    roam, run = describe(locks, 0, None)
    assert run == 1                      # a None neighbour stops the run
    assert roam > 300                    # but the window still sees the jump


def test_isolated_lock_has_no_roam():
    assert describe([None, [5.0, 5.0], None], 1, None) == (0.0, 1)
