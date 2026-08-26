"""tools/_goldset.py must reproduce every clip table it replaced, exactly.

Seven tools each hardcoded their own gold-clip table in one of four shapes. The
registry replaces them. This test pins the derived tables against the literals as
they stood before the refactor, INCLUDING ORDER — pooled numbers accumulate in
iteration order and the committed evidence JSONs record per-clip blocks in it, so
a reordering would silently change published output without failing anything else.

If a gold clip is ever added, these literals are meant to fail: update them
deliberately, and re-check any pooled number that moves.

VIDEO PATHS UPDATED 2026-08-20: source videos were reorganised into
data/incoming/<surface>/. The FILES are byte-identical and their BASENAMES are
unchanged - which is what matters, because the ball gold-leak guard
(train_ballnet.gold_source_videos) and data/train_clips/lineage.json both key on
basename, and a rename would silently defeat both (trap T17). Only the directory
moved, so every historical number remains reproducible from the same bytes; these
literals track the move rather than pinning a folder that no longer exists.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs

# ---- the literals, copied verbatim from each tool before the refactor ----

LIT_VIDEOS = {                                   # eval_pose_proximity, eval_racquet_negation
    "am_hard_utr": "data/incoming/Hardcourt/am_hard_utr.mp4",
    "gold_shell": "data/incoming/Shell/gold_shell.mp4",
    "gold_clay": "data/incoming/Clay/gold_clay.mp4",
    "gold_am": "data/incoming/Hardcourt/gold_am.mp4",
    "yt_rally2": "data/incoming/Shell/yt_rally2.mp4",
    "yt_match40": "data/incoming/Hardcourt/yt_match40.mp4",
}

LIT_NAME_VIDEO_CALIB = [                         # eval_detector_gold
    ("am_hard_utr", "data/incoming/Hardcourt/am_hard_utr.mp4", "data/am_hard_utr_pts.json"),
    ("gold_shell", "data/incoming/Shell/gold_shell.mp4", None),
    ("gold_clay", "data/incoming/Clay/gold_clay.mp4", None),
    ("gold_am", "data/incoming/Hardcourt/gold_am.mp4", None),
    ("yt_rally2", "data/incoming/Shell/yt_rally2.mp4", "data/yt_rally2_pts.json"),
    ("yt_match40", "data/incoming/Hardcourt/yt_match40.mp4", "data/yt_match40_pts.json"),
]

LIT_CALIB_TRIPLES = [                            # eval_court_gate
    ("am_hard_utr", "data/incoming/Hardcourt/am_hard_utr.mp4", "data/am_hard_utr_pts.json"),
    ("yt_rally2", "data/incoming/Shell/yt_rally2.mp4", "data/yt_rally2_pts.json"),
    ("yt_match40", "data/incoming/Hardcourt/yt_match40.mp4", "data/yt_match40_pts.json"),
]

LIT_CALIB_MAP = {                                # eval_model_filters, tune_suppress
    "am_hard_utr": ("data/incoming/Hardcourt/am_hard_utr.mp4", "data/am_hard_utr_pts.json",
                    "data/gold/am_hard_utr.labels.json"),
    "yt_rally2": ("data/incoming/Shell/yt_rally2.mp4", "data/yt_rally2_pts.json",
                  "data/gold/yt_rally2.labels.json"),
    "yt_match40": ("data/incoming/Hardcourt/yt_match40.mp4", "data/yt_match40_pts.json",
                   "data/gold/yt_match40.labels.json"),
}


# The literals above are the SIX-clip tables as they stood before 2026-08-11.
# Four clips were added that day. These tests now check two things: the legacy
# six still derive exactly as they did (so a historical number stays
# reproducible), and the additions appear in canonical order at the END (so a
# pooled figure accumulated in iteration order changes only by extension).

def test_the_legacy_six_still_derive_exactly():
    assert {k: v for k, v in gs.videos().items() if k in gs.LEGACY_SIX} == LIT_VIDEOS
    assert [r for r in gs.name_video_calib() if r[0] in gs.LEGACY_SIX]         == LIT_NAME_VIDEO_CALIB
    assert [r for r in gs.calibrated_triples() if r[0] in gs.LEGACY_SIX]         == LIT_CALIB_TRIPLES
    assert {k: v for k, v in gs.calibrated_map().items() if k in gs.LEGACY_SIX}         == LIT_CALIB_MAP


def test_the_legacy_six_come_first_and_in_the_original_order():
    """Pooled numbers accumulate in iteration order and the committed evidence
    JSONs record per-clip blocks in it. Appending is safe; interleaving is not."""
    assert list(gs.videos())[:6] == list(LIT_VIDEOS)
    assert list(gs.calibrated_map())[:3] == list(LIT_CALIB_MAP)


def test_the_calibrated_set_grew_from_three_to_seven():
    """The geometric far-court band exists only on calibrated clips. It used to
    be three; the four additions all carry a hand-placed homography, which is
    what makes far_geo answerable on a high mount at all."""
    assert set(gs.CALIBRATED) == {
        "am_hard_utr", "yt_rally2", "yt_match40",
        "gold_UHf0LeMU2pg", "gold_sAjkpeRq4P4", "gold_uR5q2cSM6AY",
        "gold_L73ep7JHiJ4"}


def test_every_clip_has_labels_and_a_real_video_path():
    for name, c in gs.GOLD.items():
        assert c.labels == f"data/gold/{name}.labels.json"
        assert (REPO / c.labels).is_file(), f"{name}: labels missing"
        # Source videos moved to data/incoming/<surface>/ on 2026-08-20 and are
        # now resolved by BASENAME (_goldset.find_video), because the basename is
        # what the ball leak guard and lineage.json key on - the one part of a
        # video's identity that must never change. So assert the basename and
        # that the file is really there, NOT a hardcoded folder that will rot the
        # next time the footage is reorganised.
        stem = name if name in gs.LEGACY_SIX else name.removeprefix("gold_")
        assert Path(c.video).name == f"{stem}.mp4", f"{name}: wrong video basename"
        assert (REPO / c.video).is_file(), f"{name}: video missing at {c.video}"
        if name not in gs.LEGACY_SIX:
            assert c.calib == f"data/{stem}_pts.json"
            assert (REPO / c.calib).is_file(), f"{name}: calibration missing"


def test_res_scale_is_a_no_op_at_720p():
    assert gs.res_scale(720) == 1.0
    assert gs.res_scale(1080) == 1.5


def test_the_legacy_six_still_reproduce_the_published_counts():
    """1201 ball clicks and 204 no-ball frames are quoted throughout CLAUDE.md.
    The benchmark GREW on 2026-08-11, so the totals legitimately changed — but
    every historical figure was measured against these six clips, and it must
    stay possible to reproduce one exactly. If this drifts, an old number in the
    docs has silently stopped meaning what it says."""
    total_ball = sum(len(gs.ball_frames(c)) for c in gs.LEGACY_SIX)
    total_noball = sum(len(gs.noball_frames(c)) for c in gs.LEGACY_SIX)
    assert total_ball == 1201, f"legacy ball population drifted: {total_ball}"
    assert total_noball == 204, f"legacy no-ball population drifted: {total_noball}"


def test_the_new_clips_actually_add_population():
    """A clip in the registry with no labels scores nothing while making every
    'pooled over N clips' line read larger — the worst kind of quiet dilution."""
    added = [c for c in gs.GOLD if c not in gs.LEGACY_SIX]
    assert added, "the 2026-08-11 additions are missing from the registry"
    for name in added:
        assert len(gs.ball_frames(name)) > 0, f"{name} contributes no ball frames"
        assert len(gs.noball_frames(name)) > 0, f"{name} contributes no no-ball frames"


def test_pooled_numbers_are_not_comparable_across_the_growth():
    """Guards the reason this is dangerous: the pooled populations moved, so a
    figure quoted before the additions cannot be set beside one quoted after."""
    legacy_ball = sum(len(gs.ball_frames(c)) for c in gs.LEGACY_SIX)
    all_ball = sum(len(gs.ball_frames(c)) for c in gs.GOLD)
    assert all_ball > legacy_ball


def test_rate_at_edges():
    assert gs.rate_at([], 5) == 0.0
    assert gs.rate_at([1, 2, 3, 400], 3) == 75.0
