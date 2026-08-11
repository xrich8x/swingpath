"""Trimming a recording must never quietly delete tennis.

Two scene-similarity versions of this detector shipped plausible-looking numbers
while discarding rallies — one of them ten minutes of them from a single clip —
and both were caught only by rendering the frames they THREW AWAY. The face test
that replaced them fails in the opposite, survivable direction, and the manual
drop list exists because it has two blind spots that a threshold cannot close.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

fps = pytest.importorskip("find_play_segments")


def test_a_drop_in_the_middle_splits_one_segment_into_two():
    got = fps.subtract([(0.0, 600.0)], [[200.0, 260.0]], min_seg_s=45.0)
    assert got == [(0.0, 200.0), (260.0, 600.0)]


def test_a_drop_at_the_head_moves_the_start_rather_than_dropping_the_segment():
    """The sponsor read that opens one real clip is 40 s of a presenter holding a
    book. Losing the whole 7-minute segment over it would be the wrong trade."""
    assert fps.subtract([(248.0, 727.0)], [[0.0, 295.0]], min_seg_s=45.0) \
        == [(295.0, 727.0)]


def test_a_remnant_shorter_than_the_minimum_is_discarded_not_kept():
    """A 20 s sliver between two interruptions is a fragment, not a passage of
    play, and feeding it to the window sampler produces a directory that cannot
    make a single 3-frame training window."""
    got = fps.subtract([(0.0, 600.0)], [[100.0, 140.0], [160.0, 200.0]],
                       min_seg_s=45.0)
    assert (140.0, 160.0) not in got
    assert got == [(0.0, 100.0), (200.0, 600.0)]


def test_drops_outside_a_segment_leave_it_untouched():
    assert fps.subtract([(300.0, 600.0)], [[0.0, 100.0], [700.0, 900.0]]) \
        == [(300.0, 600.0)]


def test_overlapping_drops_do_not_resurrect_the_overlap():
    assert fps.subtract([(0.0, 600.0)], [[100.0, 300.0], [200.0, 400.0]],
                        min_seg_s=45.0) == [(0.0, 100.0), (400.0, 600.0)]


def test_a_drop_covering_everything_leaves_nothing():
    assert fps.subtract([(0.0, 600.0)], [[0.0, 600.0]]) == []


def test_a_clip_with_no_face_anywhere_is_kept_whole():
    """Five of the nine real clips are tennis end to end. The failure that
    mattered most was slicing those into pieces on a threshold that had no
    evidence behind it."""
    import numpy as np

    thumbs = [(float(i), np.zeros((270, 480), np.float32)) for i in range(120)]
    segs, ff = fps.segments(thumbs)
    assert segs == [(0.0, 119.0)]
    assert max(ff) == 0.0


def test_too_short_to_judge_returns_nothing_rather_than_guessing():
    import numpy as np

    thumbs = [(float(i), np.zeros((270, 480), np.float32)) for i in range(10)]
    assert fps.segments(thumbs) == ([], [])
