"""The P0-3 far-end contact criterion, pinned.

This replaces `hit_xy[1] > court.NET_Y`, which called 193 of 196 contacts on a real
match "far" because the ball is ~1 m up at contact and the camera sits behind the
near baseline, so a near hit's ground ray lands past the net. The replacement uses
only the ball's raw IMAGE y-track: a far-end hit is a local MINIMUM (the ball
recedes UP the frame and a far-end hit sends it back down), a near-end hit a local
maximum.

Pinned here because it is new logic that no other test covers and because the whole
P0-3 result rests on the population it selects.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

pop = pytest.importorskip("p0_3_population")


FPS = 30.0


def _inputs(ys, hit_index, *, height=720, frame_step=1):
    """A synthetic perception cache + match with one shot at `hit_index`."""
    match = {
        "video": {"fps": FPS, "height": height, "width": 1280},
        "shots": [{"id": 0, "rally_id": 0, "t_hit_s": hit_index / FPS,
                   "player": "A", "hit_xy": [5.0, 5.0]}],
    }
    perception = {
        "frame_step": frame_step,
        "ball_px": [None if y is None else [640.0, float(y)] for y in ys],
    }
    return match, perception


def _v_track(hit, slope, n=41):
    """A V or inverted-V in image y with its vertex at `hit`."""
    return [300.0 + slope * abs(i - hit) for i in range(n)]


def test_local_minimum_in_image_y_is_a_far_end_hit():
    # y falls into the vertex and rises after it -> the ball went away, then came back.
    match, perception = _inputs(_v_track(20, +4.0), 20)
    rec = pop.classify_contacts(match, perception)[0]
    assert rec["end"] == "far", rec


def test_local_maximum_in_image_y_is_a_near_end_hit():
    match, perception = _inputs(_v_track(20, -4.0), 20)
    rec = pop.classify_contacts(match, perception)[0]
    assert rec["end"] == "near", rec


def test_a_ball_passing_straight_through_is_undecided():
    ys = [200.0 + 4.0 * i for i in range(41)]
    match, perception = _inputs(ys, 20)
    rec = pop.classify_contacts(match, perception)[0]
    assert rec["end"] == "undecided"
    assert "reversal" in rec["reason"]


def test_a_reversal_smaller_than_the_threshold_is_undecided():
    # 0.2 px/frame at 720p is under the 0.8 px/frame floor: noise, not a hit.
    match, perception = _inputs(_v_track(20, +0.2), 20)
    assert pop.classify_contacts(match, perception)[0]["end"] == "undecided"


def test_the_slope_floor_scales_with_frame_height():
    """Every pixel threshold scales by frame_height/720 (CLAUDE.md conventions).
    A 1.0 px/frame reversal clears the floor at 720p and must NOT at 1080p, where
    the same physical motion would be 1.5x larger."""
    ys = _v_track(20, +1.0)
    m720, p720 = _inputs(ys, 20, height=720)
    m1080, p1080 = _inputs(ys, 20, height=1080)
    assert pop.classify_contacts(m720, p720)[0]["end"] == "far"
    assert pop.classify_contacts(m1080, p1080)[0]["end"] == "undecided"


def test_too_few_ball_detections_refuses_rather_than_guesses():
    ys = _v_track(20, +4.0)
    for i in range(15, 20):          # leave 0 usable samples before the contact
        ys[i] = None
    match, perception = _inputs(ys, 20)
    rec = pop.classify_contacts(match, perception)[0]
    assert rec["end"] == "undecided"
    assert "too few" in rec["reason"]


def test_frame_step_maps_processed_index_to_the_right_source_frame():
    """match['video']['fps'] is the EFFECTIVE rate, so t_hit_s * fps indexes the
    perception cache; the SOURCE frame is that times frame_step. The first probe
    conflated the two and seeked to half the intended time on a 60 fps clip."""
    match, perception = _inputs(_v_track(20, +4.0), 20, frame_step=2)
    rec = pop.classify_contacts(match, perception)[0]
    assert rec["processed_index"] == 20
    assert rec["source_frame"] == 40


def test_contact_ball_position_falls_back_to_a_nearby_frame():
    ys = _v_track(20, +4.0)
    ys[20] = None
    match, perception = _inputs(ys, 20)
    rec = pop.classify_contacts(match, perception)[0]
    assert rec["ball_px_at_contact"] is not None
    assert rec["ball_px_frame_used"] in (19, 21)


def test_alternation_report_counts_only_decided_pairs():
    recs = [{"rally_id": 0, "t_hit_s": 0.0, "end": "near"},
            {"rally_id": 0, "t_hit_s": 1.0, "end": "far"},
            {"rally_id": 0, "t_hit_s": 2.0, "end": "near"},
            {"rally_id": 1, "t_hit_s": 3.0, "end": "undecided"}]
    out = pop.alternation_report(recs)
    assert out["decided_consecutive_pairs"] == 2
    assert out["alternating"] == 2


def test_pipeline_agreement_sizes_the_projection_artefact():
    """`pipeline.py` sets striker from the GROUND-projected contact, so on a clip
    with the artefact it calls everything B. The report must surface that."""
    recs = [{"end": "near", "pipeline_player": "B"},
            {"end": "far", "pipeline_player": "B"},
            {"end": "undecided", "pipeline_player": "B"}]
    out = pop.pipeline_agreement(recs)
    assert out["decided"] == 2
    assert out["agree"] == 1
    assert out["pipeline_called_far_pct"] == 100.0
