"""index_of — the gold-frame parity guard, and the most expensive bug in this
project's measurement history.

At step=2 on a 60 fps clip half the gold frames are odd. Without a
`f % step == 0` check they get scored against the ball's position one SOURCE
frame earlier, against a 10 px tolerance, which on 1080p is often further than
the ball moves. That is not noise: it silently turns correct detections into
misses, and it forced E6 part 2's published before/after pair to be withdrawn
(CLAUDE.md records the retraction).

The guard now lives in exactly one place, tools/eval_model_filters.py, and is
imported by event_audit.py and inspect_false_locks.py rather than re-typed.
These tests are what keep the third copy from reappearing.
"""

from eval_model_filters import index_of


def test_unprocessed_frames_return_none_rather_than_a_neighbour():
    """The whole bug in one assertion: at step=2, frame 101 was never processed,
    so it has NO position - not the position of frame 100."""
    at = index_of(2, 100)
    assert at(100) == 50
    assert at(101) is None
    assert at(102) == 51


def test_step_one_processes_everything():
    at = index_of(1, 100)
    assert [at(f) for f in (0, 1, 2, 99)] == [0, 1, 2, 99]


def test_frames_past_the_end_of_the_track_are_none():
    """A gold label beyond the last processed frame is unscoreable, not a miss.
    Counting it as a miss understates the tracker on any clip whose labels run
    past a truncated run."""
    at = index_of(2, 10)
    assert at(18) == 9
    assert at(20) is None


def test_the_guard_is_what_makes_odd_labels_unscoreable():
    """Documents the blast radius by clip. yt_rally2 gold is 100% even frames so
    step=2 is lossless there; am_hard_utr is 48.6% odd, so half its labels are
    invisible at the shipped step and need --frame-step 1."""
    at = index_of(2, 1000)
    odd = [f for f in range(0, 200) if at(f) is None]
    assert odd == [f for f in range(0, 200) if f % 2]


def test_zero_is_processed_at_every_step():
    for step in (1, 2, 3, 5):
        assert index_of(step, 10)(0) == 0
