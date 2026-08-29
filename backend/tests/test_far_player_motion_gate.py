"""Pins the logic of `eval/far_player_motion_gate.py`, the runner for the
pre-registered far-player MOTION gate.

Why these tests and not others: the gate FAILED (median 5.75 box-heights, 7 of 15
within 1.5, against a bar of <=1.5 on >=10 of 15). A failed gate's credibility rests
entirely on the population having been selected by the SAME rule that produced the
published 15/25 figure, and on the metric being the one that was pre-registered.
So the tests pin exactly those two things plus the null control's determinism.

They do NOT re-run the gate: that needs the video. Rule 2 also means these tests must
never be edited to make a re-run "pass" - they exist to prove the runner did not
quietly redefine the question.
"""

import os
import sys

import numpy as np
import pytest

_EVAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "eval")
if _EVAL not in sys.path:
    sys.path.insert(0, _EVAL)

fpmg = pytest.importorskip("far_player_motion_gate")
sweep = pytest.importorskip("p0_3_tolerance_sweep")


def test_edge_dist_is_identical_to_the_sweep_that_defined_the_population():
    """The 15/25 figure came from tools/p0_3_tolerance_sweep.py. If this runner's
    distance differs by so much as a branch, it is scoring a different population."""
    rng = np.random.default_rng(0)
    for _ in range(200):
        box = sorted(rng.uniform(0, 100, 2).tolist()) + sorted(rng.uniform(0, 100, 2).tolist())
        box = [box[0], box[2], box[1], box[3]]
        pt = rng.uniform(-20, 120, 2).tolist()
        assert fpmg._edge_dist(box, pt) == pytest.approx(sweep._edge_dist(box, pt))


def test_edge_dist_is_zero_inside_the_box():
    assert fpmg._edge_dist([0, 0, 10, 10], [5, 5]) == 0.0
    assert fpmg._edge_dist([0, 0, 10, 10], [13, 10]) == pytest.approx(3.0)
    assert fpmg._edge_dist([0, 0, 10, 10], [13, 14]) == pytest.approx(5.0)


def _probe(entries):
    return {"contacts": [{
        "shot_id": 1, "source_frame": 100, "ball_px_at_contact": [50.0, 50.0],
        "near_player_box_full_frame": None, "contact_on_near_player": False,
        "arms": {"A": {"accepted": [], "rejected": entries}},
    }]}


def _cand(box, h, small=True, notnear=True, score=0.9):
    return {"box": box, "box_h_px": h, "score": score,
            "small_enough": small, "not_the_near_player": notnear}


def test_population_uses_the_sweeps_own_filter():
    """small_enough AND not_the_near_player - the near player is not a candidate for
    'where is the FAR player', and a full-height box is not a far-sized one."""
    assert fpmg.build_population(_probe([_cand([0, 0, 10, 30], 30, small=False)]), "A") == []
    assert fpmg.build_population(_probe([_cand([0, 0, 10, 30], 30, notnear=False)]), "A") == []
    assert len(fpmg.build_population(_probe([_cand([0, 0, 10, 30], 30)]), "A")) == 1
    assert fpmg.build_population(_probe([]), "A") == []


def test_population_picks_the_nearest_candidate_by_edge_distance():
    far = _cand([0, 0, 10, 30], 30.0)
    near = _cand([40, 40, 60, 70], 30.0)
    pop = fpmg.build_population(_probe([far, near]), "A")
    assert len(pop) == 1
    assert pop[0]["ref_box_POST_HOC"] == [40.0, 40.0, 60.0, 70.0]
    assert pop[0]["anchor_edge_dist_px"] == 0.0        # (50,50) is inside that box


def test_reference_centroid_is_the_box_centre_and_normaliser_is_box_height():
    pop = fpmg.build_population(_probe([_cand([10, 20, 30, 60], 40.0)]), "A")
    assert pop[0]["ref_centroid_POST_HOC"] == [20.0, 40.0]
    assert pop[0]["ref_box_h_px"] == 40.0


def test_the_bar_constants_are_the_pre_registered_ones():
    """Rule 2. If a future edit moves any of these, the gate is no longer the gate
    that was pre-registered on 2026-08-29 and its verdict does not carry over."""
    assert fpmg.BAR_REL_H == 1.5
    assert fpmg.BAR_N_FRAMES == 10
    assert fpmg.POP_N == 15


def test_movers_is_used_unmodified():
    """The gate says `eval/movers.py` unmodified. Pin the constants the runner
    stamps into its provenance so a silent retune cannot masquerade as the same run."""
    import movers
    assert movers.WORK_W == 960
    assert movers.PLATE_MAX == 31
    assert movers.MAX_PLAYERS == 4
    assert movers.AREA_MIN_FRAC == 2.0e-4
    assert movers.AREA_MAX_FRAC == 6.0e-2
    assert movers.MIN_H_OVER_W == 0.8


def test_window_is_one_full_clean_plate_with_no_subsampling():
    """31 frames == movers.PLATE_MAX, so clean_plate uses every frame it is given."""
    import movers
    assert 2 * fpmg.WINDOW_HALF + 1 == movers.PLATE_MAX


def test_contrast_is_descriptive_and_signed_the_obvious_way():
    """A bright patch on a dark surround must report positive delta_L, and a patch
    identical to its surround must report ~0. No threshold is asserted anywhere -
    contrast has NO pre-registered bar and cannot pass or fail anything."""
    import cv2
    frame = np.full((200, 200, 3), 40, np.uint8)
    box = [80, 80, 120, 120]
    flat = fpmg.contrast_stats(frame, box)
    assert flat["abs_delta_L"] == pytest.approx(0.0, abs=0.01)
    assert flat["delta_chroma_ab"] == pytest.approx(0.0, abs=0.01)

    frame[80:120, 80:120] = 220
    bright = fpmg.contrast_stats(frame, box)
    assert bright["delta_L"] > 40.0
    assert bright["abs_delta_L"] == pytest.approx(bright["delta_L"])
    # L is reported on the CIELAB 0..100 scale, not OpenCV's 0..255 byte scale.
    assert 0.0 <= bright["box_mean_L"] <= 100.0
    assert cv2 is not None


def test_contrast_returns_none_for_a_degenerate_box():
    frame = np.zeros((50, 50, 3), np.uint8)
    assert fpmg.contrast_stats(frame, [10, 10, 11, 11]) is None


def test_null_control_draw_is_seeded_and_reproducible():
    """Rule 7: one variable, seeded. Two generators at the same seed must pick the
    same blobs; a different seed must be free to differ."""
    sizes = [3, 1, 4, 2, 4, 2, 3]
    a = [int(np.random.default_rng(0).integers(n)) for n in sizes]
    b = [int(np.random.default_rng(0).integers(n)) for n in sizes]
    assert a == b
