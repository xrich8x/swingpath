"""Tests for the composite calibration score.

Pure logic - no video, no model. The point of these is to PIN the two design decisions
that the evidence file rests on:
  * coherence, not thresholds: a narrow lens on a HIGH mount (broadcast) must not flag,
    while the same narrow lens on a LOW mount (depth compression) must;
  * a missing signal is silent, never a vote either way.
Every numeric fixture below is taken from `data/output/composite_signal_sweep.json`, so a
constant change that moves a real clip's verdict breaks a test rather than a doc.
"""
import pytest

from swingvision import calib_score as cs


# --- real rows out of the sweep, so the fixtures cannot drift from the evidence -----
GOOD_YT_MATCH40 = dict(coverage=0.948, visible_frac=0.989, centrality=0.926,
                       residual_px=1.09, cam_h_m=1.62, hfov_deg=91.1, clear_px720=-8.9)
BROADCAST_EALA = dict(coverage=0.921, visible_frac=1.000, centrality=0.944,
                      residual_px=4.45, cam_h_m=8.73, hfov_deg=24.5, clear_px720=7.2)
DEPTH_15_YT = dict(coverage=0.824, visible_frac=0.987, centrality=0.952,
                   residual_px=0.08, cam_h_m=1.66, hfov_deg=55.3, clear_px720=-19.3)
WRONG_BAK = dict(coverage=0.436, visible_frac=1.000, centrality=0.920,
                 residual_px=12.35, cam_h_m=10.82, hfov_deg=20.9, clear_px720=9.0)


def test_believed_correct_clip_does_not_flag():
    sc = cs.composite_score(GOOD_YT_MATCH40)
    assert not sc.flag
    assert sc.reasons == []
    assert cs.explain(sc) == "Every check agrees on this court."


def test_broadcast_narrow_lens_high_mount_does_not_flag():
    """eala is a real Wimbledon broadcast camera: 24.5 deg lens at 8.7 m. It false-rejected
    two previous screens. A narrow lens is only incoherent on a LOW mount."""
    sc = cs.composite_score(BROADCAST_EALA)
    assert not sc.flag, sc.reasons
    assert "lens_coherence" not in sc.fired
    assert "camera_height" not in sc.fired   # 8.7 m is broadcast, not absurd


def test_depth_compression_flags_via_lens_coherence():
    """The corruption every shipped gate is blind to: same low mount, lens collapses."""
    sc = cs.composite_score(DEPTH_15_YT)
    assert sc.flag
    assert "lens_coherence" in sc.fired
    assert "implausibly narrow" in cs.explain(sc)


def test_the_one_real_wrong_calibration_is_MISSED_and_this_is_pinned():
    """THE headline negative result, pinned so nobody quietly "fixes" it.

    `data/yt_match40_pts.json.bak-2026-09-05` is the ONE confirmed-wrong calibration this
    project has (corners on asphalt and a hedge). It fits a 10.8 m camera with a 20.9 deg
    lens - which is EXACTLY the broadcast signature the coherence rule exists to exonerate,
    and is within 2 m and 4 deg of the real Wimbledon clip `eala_pts_auto`. Its coverage
    (0.436) also sits above `verify_court`'s 0.40 bar and below four believed-correct
    clips. The composite scores it 0.

    Do not retune to catch it: n = 1, and every constant that would catch it re-breaks
    eala. See docs/evidence/composite-calibration-score.md."""
    sc = cs.composite_score(WRONG_BAK)
    assert not sc.flag
    assert sc.score == 0


def test_lines_alone_cannot_flag():
    """`verify_court` reads line CONTRAST and false-rejects three real clips here, so it
    is worth half a vote. This pins the weight, not just the threshold."""
    sig = dict(GOOD_YT_MATCH40, coverage=0.10)
    sc = cs.composite_score(sig)
    assert "lines" in sc.fired
    assert sc.score == pytest.approx(0.5)
    assert not sc.flag


def test_lines_plus_one_other_does_flag():
    sig = dict(GOOD_YT_MATCH40, coverage=0.10, residual_px=99.0)
    sc = cs.composite_score(sig)
    assert {"lines", "residual"} <= set(sc.fired)
    assert sc.score == pytest.approx(1.5)
    assert sc.flag


def test_missing_signal_is_silent_not_a_vote():
    """A refused net tape or an empty court must neither flag nor exonerate."""
    full = cs.composite_score(GOOD_YT_MATCH40)
    thin = cs.composite_score({k: v for k, v in GOOD_YT_MATCH40.items()
                               if k not in ("clear_px720",)})
    assert thin.score == full.score
    assert "net_coherence" not in [i.name for i in thin.indicators]
    assert "net_coherence" in [i.name for i in full.indicators]


def test_absent_optional_signals_never_appear():
    sc = cs.composite_score(GOOD_YT_MATCH40)
    names = [i.name for i in sc.indicators]
    assert "tape_height" not in names
    assert "player_feet" not in names


def test_net_coherence_needs_the_contradiction_not_the_clearance():
    """A big clearance on a genuinely high mount is a good setup, not an error."""
    tower = dict(GOOD_YT_MATCH40, clear_px720=200.0, cam_h_m=8.0)
    assert "net_coherence" not in cs.composite_score(tower).fired
    squashed = dict(GOOD_YT_MATCH40, clear_px720=200.0, cam_h_m=1.7)
    assert "net_coherence" in cs.composite_score(squashed).fired


def test_camera_height_flags_only_impossible_heights():
    assert "camera_height" not in cs.composite_score(
        dict(GOOD_YT_MATCH40, cam_h_m=8.0)).fired
    assert "camera_height" in cs.composite_score(
        dict(GOOD_YT_MATCH40, cam_h_m=-0.7)).fired      # rotate 15 deg produces these
    assert "camera_height" in cs.composite_score(
        dict(GOOD_YT_MATCH40, cam_h_m=40.0)).fired


def test_tape_height_uses_the_pre_registered_10_pct_bar():
    assert "tape_height" not in cs.composite_score(
        dict(GOOD_YT_MATCH40, tape_delta_pct=6.7)).fired
    assert "tape_height" in cs.composite_score(
        dict(GOOD_YT_MATCH40, tape_delta_pct=-18.5)).fired


def test_player_feet_anchor_reads_court_y():
    assert "player_feet" not in cs.composite_score(
        dict(GOOD_YT_MATCH40, feet_max_y_m=24.0)).fired
    assert "player_feet" in cs.composite_score(
        dict(GOOD_YT_MATCH40, feet_max_y_m=41.0)).fired


def test_reason_strings_are_human_and_actionable():
    sc = cs.composite_score(DEPTH_15_YT)
    txt = cs.explain(sc)
    assert txt.startswith("This court may be wrong:")
    assert txt.endswith(".")
    for r in sc.reasons:
        assert r and r[0].islower() or r[0].isalpha()
        assert "None" not in r


def test_flag_at_is_a_parameter_not_a_constant_in_the_body():
    sig = dict(GOOD_YT_MATCH40, coverage=0.10)
    assert not cs.composite_score(sig).flag
    assert cs.composite_score(sig, flag_at=0.5).flag


def test_score_is_the_sum_of_fired_weights():
    sig = dict(GOOD_YT_MATCH40, coverage=0.10, residual_px=99.0, cam_h_m=-1.0)
    sc = cs.composite_score(sig)
    assert sc.score == pytest.approx(sum(i.weight for i in sc.indicators if i.fired))
