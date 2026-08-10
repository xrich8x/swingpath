"""The far-court label queue must not waste a human's clicks.

Labelling is the one input nothing else substitutes for, and there are 4-5 hours
of it available. Three properties decide whether a queue is worth opening, and
each of them was a live bug or a live question while the tool was written.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

sel = pytest.importorskip("select_farcourt_labels")


def _clip(tmp_path, name, labels, window_starts=None, negatives=None):
    d = tmp_path / name
    d.mkdir(parents=True)
    (d / "labels.json").write_text(json.dumps({
        "labels": {str(k): list(v) for k, v in labels.items()},
        "window_starts": window_starts or [],
        "negatives": negatives or [],
    }), encoding="utf-8")
    return d


FAR_Y = 40.0        # well inside the top 36% of 288
NEAR_Y = 250.0


def test_a_bracketed_far_court_gap_is_a_candidate(tmp_path):
    _clip(tmp_path, "c", {10: (100, FAR_Y), 14: (140, FAR_Y)})
    c = sel.candidates(tmp_path)
    assert len(c) == 1
    _d, a, _pa, mid, _pm, b, _pb = c[0]
    assert (a, mid, b) == (10, 12, 14), "the midpoint is the frame worth labelling"


def test_near_court_gaps_are_not_queued(tmp_path):
    """The queue exists for the far court; a near-court gap is already covered."""
    _clip(tmp_path, "c", {10: (100, NEAR_Y), 14: (140, NEAR_Y)})
    assert sel.candidates(tmp_path) == []


def test_a_gap_spanning_a_window_boundary_is_rejected(tmp_path):
    """Windows are unrelated moments spliced into one directory, so interpolating
    across a boundary joins two positions that were never on one trajectory.
    Only ~1% of candidates do this, which is exactly why it would go unnoticed."""
    _clip(tmp_path, "c", {10: (100, FAR_Y), 14: (140, FAR_Y)}, window_starts=[0, 12])
    assert sel.candidates(tmp_path) == []


def test_long_gaps_are_rejected_because_there_is_no_usable_anchor(tmp_path):
    _clip(tmp_path, "c", {10: (100, FAR_Y), 10 + sel.MAX_GAP + 2: (140, FAR_Y)})
    assert sel.candidates(tmp_path) == []


def test_a_frame_already_known_to_hold_no_ball_is_not_queued(tmp_path):
    _clip(tmp_path, "c", {10: (100, FAR_Y), 14: (140, FAR_Y)}, negatives=[12])
    assert sel.candidates(tmp_path) == []


def test_round_robin_spreads_across_clips_rather_than_draining_the_biggest(tmp_path):
    """300 frames from one rally teaches far less than 300 spread across lighting,
    courts and camera heights — and one clip has 297 candidates while another has 7."""
    big = [("big", i, None, i, None, i, None) for i in range(100)]
    small = [("small", i, None, i, None, i, None) for i in range(3)]
    got = sel.round_robin(big + small, 6)
    assert sum(1 for g in got if g[0] == "small") == 3, "small clip was starved"
    assert len(got) == 6


def test_round_robin_returns_everything_when_asked_for_more_than_exists(tmp_path):
    few = [("a", i, None, i, None, i, None) for i in range(2)]
    assert len(sel.round_robin(few, 50)) == 2
