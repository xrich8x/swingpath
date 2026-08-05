"""tools/_goldset.py must reproduce every clip table it replaced, exactly.

Seven tools each hardcoded their own gold-clip table in one of four shapes. The
registry replaces them. This test pins the derived tables against the literals as
they stood before the refactor, INCLUDING ORDER — pooled numbers accumulate in
iteration order and the committed evidence JSONs record per-clip blocks in it, so
a reordering would silently change published output without failing anything else.

If a gold clip is ever added, these literals are meant to fail: update them
deliberately, and re-check any pooled number that moves.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs

# ---- the literals, copied verbatim from each tool before the refactor ----

LIT_VIDEOS = {                                   # eval_pose_proximity, eval_racquet_negation
    "am_hard_utr": "data/am_hard_utr.mp4",
    "gold_shell": "data/gold_shell.mp4",
    "gold_clay": "data/gold_clay.mp4",
    "gold_am": "data/gold_am.mp4",
    "yt_rally2": "data/yt_rally2.mp4",
    "yt_match40": "data/yt_match40.mp4",
}

LIT_NAME_VIDEO_CALIB = [                         # eval_detector_gold
    ("am_hard_utr", "data/am_hard_utr.mp4", "data/am_hard_utr_pts.json"),
    ("gold_shell", "data/gold_shell.mp4", None),
    ("gold_clay", "data/gold_clay.mp4", None),
    ("gold_am", "data/gold_am.mp4", None),
    ("yt_rally2", "data/yt_rally2.mp4", "data/yt_rally2_pts.json"),
    ("yt_match40", "data/yt_match40.mp4", "data/yt_match40_pts.json"),
]

LIT_CALIB_TRIPLES = [                            # eval_court_gate
    ("am_hard_utr", "data/am_hard_utr.mp4", "data/am_hard_utr_pts.json"),
    ("yt_rally2", "data/yt_rally2.mp4", "data/yt_rally2_pts.json"),
    ("yt_match40", "data/yt_match40.mp4", "data/yt_match40_pts.json"),
]

LIT_CALIB_MAP = {                                # eval_model_filters, tune_suppress
    "am_hard_utr": ("data/am_hard_utr.mp4", "data/am_hard_utr_pts.json",
                    "data/gold/am_hard_utr.labels.json"),
    "yt_rally2": ("data/yt_rally2.mp4", "data/yt_rally2_pts.json",
                  "data/gold/yt_rally2.labels.json"),
    "yt_match40": ("data/yt_match40.mp4", "data/yt_match40_pts.json",
                   "data/gold/yt_match40.labels.json"),
}


def test_videos_table():
    assert gs.videos() == LIT_VIDEOS
    assert list(gs.videos()) == list(LIT_VIDEOS), "iteration order changed"


def test_name_video_calib_table():
    assert gs.name_video_calib() == LIT_NAME_VIDEO_CALIB


def test_calibrated_triples_table():
    assert gs.calibrated_triples() == LIT_CALIB_TRIPLES


def test_calibrated_map_table():
    assert gs.calibrated_map() == LIT_CALIB_MAP
    assert list(gs.calibrated_map()) == list(LIT_CALIB_MAP), "iteration order changed"


def test_exactly_three_clips_are_calibrated():
    """The geometric far-court band exists only on these. A clip silently losing
    its calibration would move far_geo without moving anything else."""
    assert set(gs.CALIBRATED) == {"am_hard_utr", "yt_rally2", "yt_match40"}


def test_every_clip_has_labels_and_a_real_video_path():
    for name, c in gs.GOLD.items():
        assert c.labels == f"data/gold/{name}.labels.json"
        assert c.video == f"data/{name}.mp4"
        assert (REPO / c.labels).is_file(), f"{name}: labels missing"


def test_res_scale_is_a_no_op_at_720p():
    assert gs.res_scale(720) == 1.0
    assert gs.res_scale(1080) == 1.5


def test_ball_and_noball_populations_match_published_counts():
    """The numbers every criterion in this project is scored against. 1201 ball
    clicks and 204 no-ball frames are quoted throughout CLAUDE.md; 'unsure' is in
    neither population."""
    total_ball = sum(len(gs.ball_frames(c)) for c in gs.GOLD)
    total_noball = sum(len(gs.noball_frames(c)) for c in gs.GOLD)
    assert total_ball == 1201, f"ball population drifted: {total_ball}"
    assert total_noball == 204, f"no-ball population drifted: {total_noball}"


def test_rate_at_edges():
    assert gs.rate_at([], 5) == 0.0
    assert gs.rate_at([1, 2, 3, 400], 3) == 75.0
