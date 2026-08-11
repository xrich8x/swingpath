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


# --- dataset index -> source video frame -------------------------------------
# Labelling happens on the SOURCE video (720p/1080p), not the 512x288 network
# input where a far ball is ~1.6 px. Getting this arithmetic wrong would put the
# labeller on a frame from a different moment and silently poison the labels, so
# it is verified against the pixels in the tool and pinned here.

WS = [0, 1200, 2400]           # processed index of each window seam
STARTS = [1213, 2846, 4479]    # source frame each window began at


def test_first_frame_of_each_window_maps_to_that_window_start():
    for w, s in zip(WS, STARTS):
        assert sel.source_frame(w, WS, STARTS, 2) == s


def test_within_a_window_the_source_advances_by_the_frame_step():
    """relabel_train_clips grabs step-1 frames then reads, so processed frame k
    is source start + k*step — a 60 fps clip sampled at 30."""
    assert sel.source_frame(5, WS, STARTS, 2) == 1213 + 10
    assert sel.source_frame(1205, WS, STARTS, 2) == 2846 + 10


def test_step_one_clips_advance_one_for_one():
    assert sel.source_frame(7, WS, STARTS, 1) == 1220


# --- repeating an earlier queue ----------------------------------------------
# A re-run has two jobs that pull against each other: REPEAT the old gaps, so the
# one thing that changed is the only difference, and include FRESH ones, so a rate
# can be measured without the labeller's memory of the first pass in it.

def _man(gaps):
    rows = []
    for gi, (clip, a, m, b) in enumerate(gaps):
        for f, bucket in ((a, "anchor"), (m, "farcourt_gap"), (b, "anchor")):
            rows.append({"frame": len(rows), "gap": gi, "bucket": bucket,
                         "src_dataset": clip, "src_frame": f})
    return {"frames": rows}


def test_the_gaps_of_an_earlier_queue_are_recovered_from_its_manifest(tmp_path):
    p = tmp_path / "q.manifest.json"
    p.write_text(json.dumps(_man([("c1", 10, 12, 14), ("c2", 5, 7, 9)])),
                 encoding="utf-8")
    assert sel.gaps_in_manifest(p) == {("c1", 10, 12, 14), ("c2", 5, 7, 9)}


def test_a_manifest_without_gap_ids_is_still_recoverable(tmp_path):
    """The first pilot's manifest predates the field and is exactly the queue a
    re-run needs to repeat."""
    man = _man([("c1", 10, 12, 14), ("c2", 5, 7, 9)])
    for r in man["frames"]:
        del r["gap"]
    p = tmp_path / "q.manifest.json"
    p.write_text(json.dumps(man), encoding="utf-8")
    assert sel.gaps_in_manifest(p) == {("c1", 10, 12, 14), ("c2", 5, 7, 9)}


def test_a_candidate_is_matched_to_a_manifest_gap_by_its_frames():
    cand = ("/some/path/to/c1", 10, (1, 2), 12, (3, 4), 14, (5, 6))
    assert sel.key_of(cand) == ("c1", 10, 12, 14)


def test_repeats_are_spread_through_the_queue_not_stacked_at_the_front():
    """Repeats first would mean they are all labelled first and the fresh gaps
    last, so any drift over a session lands entirely on one of the two groups."""
    got = sel._interleave(["r"] * 3, ["f"] * 9)
    assert got.count("r") == 3 and got.count("f") == 9
    pos = [i for i, x in enumerate(got) if x == "r"]
    assert max(pos) - min(pos) >= 6, f"repeats bunched together: {got}"


def test_interleaving_with_nothing_to_interleave_is_a_no_op():
    assert sel._interleave([], ["f", "f"]) == ["f", "f"]
    assert sel._interleave(["r"], []) == ["r"]


# --- "far court" must mean the far court, not the top of the frame -----------
# FAR_FRAC calls the top 36% of the FRAME far court. That is a proxy for the far
# half of the COURT and it only holds for the framing it was written against.
# Measured on the clips added later: tc8CGFxyRE8 puts 3.2% of its labels in the
# top 36% of the frame and 84.0% past the net — a 26x error that made the queue
# skip a clip full of far-court ball.

def test_without_a_calibration_it_falls_back_to_the_frame_row_rule(tmp_path):
    """Most clips have no homography, and the proxy is all there is for them.
    The fallback must be the OLD behaviour exactly, or existing queues shift."""
    d = tmp_path / "yt_nocalib"
    d.mkdir()
    is_far, how = sel.far_test(d, tmp_path)
    assert how == "frame-row"
    assert is_far(100.0, 40.0) is True            # top 36% of 288 -> far
    assert is_far(100.0, 200.0) is False


def test_the_frame_row_rule_is_unchanged_at_its_boundary(tmp_path):
    d = tmp_path / "yt_nocalib"
    d.mkdir()
    is_far, _ = sel.far_test(d, tmp_path)
    edge = sel.FAR_FRAC * sel.IN_H
    assert is_far(0.0, edge - 0.01) is True
    assert is_far(0.0, edge + 0.01) is False


def test_a_gap_is_selected_by_whatever_predicate_it_is_given(tmp_path):
    """candidates() must route through the predicate, not re-test the row itself
    — otherwise the geometric rule is computed and then quietly ignored."""
    _clip(tmp_path, "c", {10: (100, NEAR_Y), 14: (140, NEAR_Y)})
    assert sel.candidates(tmp_path) == [], "near-court gap should be skipped"
    # A clip WITH a calibration would call the geometric predicate here; the
    # fallback path is what this fixture exercises, and it must still refuse.


def _cand(clip, a, m, b):
    return (f"/data/ball_dataset/{clip}", a, None, m, None, b, None)


def test_an_already_labelled_gap_is_kept_out_of_a_fresh_queue():
    """A gap labelled once teaches nothing a second time, and it carries the
    labeller's memory of that pass, so it cannot be part of a clean rate."""
    cands = [_cand("c1", 1, 2, 3), _cand("c2", 4, 5, 6)]
    reps, fresh, n = sel.split_pools(cands, set(), {("c1", 1, 2, 3)})
    assert n == 1 and reps == [] and [sel.key_of(c) for c in fresh] == [("c2", 4, 5, 6)]


def test_an_explicit_repeat_wins_over_an_exclude():
    """One session can legitimately repeat one queue and skip another, and the
    same gap can appear in both lists. If exclude won, the controlled half of the
    queue would silently empty and the A/B would quietly become a fresh run."""
    cands = [_cand("c1", 1, 2, 3)]
    reps, fresh, n = sel.split_pools(cands, {("c1", 1, 2, 3)}, {("c1", 1, 2, 3)})
    assert n == 0 and len(reps) == 1 and fresh == []


def test_the_frame_just_before_a_seam_belongs_to_the_earlier_window():
    """Off by one here would jump ~1600 source frames to another moment."""
    assert sel.source_frame(1199, WS, STARTS, 2) == 1213 + 1199 * 2
    assert sel.source_frame(1200, WS, STARTS, 2) == 2846
