"""A trim must not smuggle a gold clip into the training set.

The gold guard matches on the source video's FILENAME. Cutting a clip out of a
longer recording gives it a new name, so the guard saw a different video and
reported no leak about the same footage. Found live: gold clip `hd_shortcourt_1`
is `7 UTR vs 8 UTR [UHf0LeMU2pg].mp4`, and a training set had been built from
`UHf0LeMU2pg.mp4` — the identical match, cut shorter.

Every one of the 12 clips trimmed in that session had this hole, so this is the
regression test for the whole class, not for one file.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

tb = pytest.importorskip("train_ballnet")


def _pool(tmp_path, gold_video, dataset_video, lineage=None):
    root = tmp_path / "ball_dataset"
    (root / "yt_clip").mkdir(parents=True)
    (root / "yt_clip" / "labels.json").write_text(json.dumps(
        {"n_frames": 3, "labels": {}, "provenance": {"video": dataset_video}}),
        encoding="utf-8")
    gold = tmp_path / "gold"
    gold.mkdir()
    (gold / "g.manifest.json").write_text(json.dumps(
        {"clip": "hd_shortcourt_1", "video": gold_video}), encoding="utf-8")
    clips = tmp_path / "train_clips"
    clips.mkdir()
    if lineage is not None:
        (clips / "lineage.json").write_text(
            json.dumps({"clips": lineage}), encoding="utf-8")
    return root


def test_a_trim_of_a_gold_clip_is_refused(tmp_path):
    """The exact live case: same footage, different filename after the cut."""
    root = _pool(tmp_path, "data/incoming/7 UTR vs 8 UTR [UHf0LeMU2pg].mp4",
                 "UHf0LeMU2pg.mp4",
                 lineage={"UHf0LeMU2pg.mp4": "7 UTR vs 8 UTR [UHf0LeMU2pg].mp4"})
    with pytest.raises(SystemExit) as e:
        tb.assert_no_gold_leak(str(root), exclude=())
    assert "gold" in str(e.value).lower()


def test_without_the_lineage_the_same_leak_goes_UNDETECTED(tmp_path):
    """Pins the hole itself, so nobody 'simplifies' the lineage away: with no
    record of the cut, the guard cannot tell these are one video."""
    root = _pool(tmp_path, "data/incoming/7 UTR vs 8 UTR [UHf0LeMU2pg].mp4",
                 "UHf0LeMU2pg.mp4", lineage=None)
    tb.assert_no_gold_leak(str(root), exclude=())      # no raise — the bug


def test_a_trim_of_a_TRAINING_clip_is_still_allowed(tmp_path):
    """The guard must not become 'refuse anything that was ever trimmed'."""
    root = _pool(tmp_path, "data/gold_am.mp4", "CYqapSq5llo.mp4",
                 lineage={"CYqapSq5llo.mp4": "My Opponent [CYqapSq5llo].mp4"})
    tb.assert_no_gold_leak(str(root), exclude=())


def test_an_untrimmed_gold_video_is_still_caught(tmp_path):
    """The original name-match path keeps working with a lineage file present."""
    root = _pool(tmp_path, "data/gold_am.mp4", "gold_am.mp4", lineage={})
    with pytest.raises(SystemExit):
        tb.assert_no_gold_leak(str(root), exclude=())


def test_the_real_lineage_file_covers_every_trimmed_clip():
    """A lineage that silently misses a clip reads as protection and is not."""
    repo = Path(__file__).resolve().parents[2]
    lin = repo / "data" / "train_clips" / "lineage.json"
    segs = repo / "data" / "output" / "play_segments.json"
    if not (lin.is_file() and segs.is_file()):
        pytest.skip("no trimmed pool in this checkout")
    have = set(json.loads(lin.read_text(encoding="utf-8"))["clips"])
    want = set()
    for yid, r in json.loads(segs.read_text(encoding="utf-8"))["clips"].items():
        n = len(r["segments"])
        for k in range(1, n + 1):
            want.add(f"{yid}.mp4" if n == 1 else f"{yid}_s{k}.mp4")
    assert not (want - have), f"trimmed clips with no recorded source: {want - have}"
