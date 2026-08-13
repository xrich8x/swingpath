"""SwingVision's rendered output must never become training signal.

User instruction, 2026-08-13: do not train on SwingVision information. Five clips
in the training pool carry a burned-in overlay — mini-court radar, stroke/speed
readout, score panel, and a watermark that is a literal yellow tennis ball — and
83 pseudo-labels landed inside one of those graphics.

The rule is enforced in two places and both are pinned here: the trainer REFUSES
to start on an unscrubbed overlay clip, and `BallWindows` paints the boxes at load
while dropping the in-box labels. A guard that can be forgotten is not a guard.
"""

import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

DATASET = REPO / "data" / "ball_dataset"
pytestmark = pytest.mark.skipif(
    not DATASET.is_dir(), reason="training pool not present on this machine")


def _sv_dirs():
    from scrub_swingvision import sv_clips
    return [f"yt_{s}" for s in sv_clips()
            if (DATASET / f"yt_{s}").is_dir()]


def test_every_overlay_clip_is_scrubbed():
    """The pool as committed must satisfy the rule, not merely be able to."""
    missing = [t for t in _sv_dirs()
               if not (DATASET / t / "swingvision_mask.json").is_file()]
    assert not missing, f"unscrubbed SwingVision clips in the pool: {missing}"


def test_the_guard_refuses_an_unscrubbed_dir():
    """Proved by removing a mask file and requiring the abort — the same way the
    court split guard is proved, because a guard nobody has seen fire is a guess."""
    import train_ballnet as T
    dirs = _sv_dirs()
    if not dirs:
        pytest.skip("no SwingVision clips in the pool")
    p = DATASET / dirs[0] / "swingvision_mask.json"
    bak = p.with_suffix(".json.testbak")
    shutil.move(p, bak)
    try:
        with pytest.raises(SystemExit) as e:
            T.assert_no_swingvision_leak(str(DATASET), ())
        assert dirs[0] in str(e.value)
        assert "REFUSING TO TRAIN" in str(e.value)
    finally:
        shutil.move(bak, p)
    T.assert_no_swingvision_leak(str(DATASET), ())      # restored -> passes again


def test_excluding_the_dir_is_also_compliant():
    """Dropping the clip entirely is a legitimate way to satisfy the rule; it just
    costs the data. The guard must not force the scrub specifically."""
    import train_ballnet as T
    dirs = _sv_dirs()
    if not dirs:
        pytest.skip("no SwingVision clips in the pool")
    p = DATASET / dirs[0] / "swingvision_mask.json"
    bak = p.with_suffix(".json.testbak")
    shutil.move(p, bak)
    try:
        T.assert_no_swingvision_leak(str(DATASET), (dirs[0],))
    finally:
        shutil.move(bak, p)


def test_boxes_are_painted_and_in_box_labels_are_dropped():
    import train_ballnet as T
    import cv2
    dirs = _sv_dirs()
    if not dirs:
        pytest.skip("no SwingVision clips in the pool")
    ds = T.BallWindows(str(DATASET), split="train", augment=False)
    d = str(DATASET / dirs[0])
    boxes = ds.sv_masks.get(d)
    assert boxes, f"{dirs[0]} loaded no mask boxes"

    painted = ds._frame(d, 0)
    assert painted is not None
    for b in boxes:
        region = painted[b["y"]:b["y"] + b["h"], b["x"]:b["x"] + b["w"]]
        assert region.size > 0
        assert np.all(region == 60), f"{b['what']} not painted flat"

    drop = set(json.loads((DATASET / dirs[0] / "swingvision_mask.json")
                          .read_text(encoding="utf-8"))["drop_labels"])
    positives = {i for (dd, i, x, _y, _c) in ds.samples if dd == d and x is not None}
    assert not (positives & drop), "a label inside a SwingVision graphic survived"


def test_masks_are_stored_in_frame_space_not_source_space():
    """The boxes come from data/hud_masks.json in SOURCE pixels (1280x720) while
    the extracted frames are 512x288. Storing the unscaled box would paint a
    quarter of the frame — including the court — and nothing downstream would say
    so. Pinned because it is the exact class of bug this repo has hit repeatedly
    with unscaled pixel constants."""
    for t in _sv_dirs():
        blob = json.loads((DATASET / t / "swingvision_mask.json")
                          .read_text(encoding="utf-8"))
        fw, fh = blob["frame_wh"]
        for b in blob["boxes"]:
            assert 0 <= b["x"] <= fw and 0 <= b["y"] <= fh, f"{t}: box outside frame"
            assert b["x"] + b["w"] <= fw + 1, f"{t}: box wider than the frame"
            assert b["y"] + b["h"] <= fh + 1, f"{t}: box taller than the frame"


def test_scrub_is_idempotent_in_what_it_reports():
    """Re-running the scanner must not discover new labels to drop — if it does,
    the mask files and the labels have drifted apart."""
    from scrub_swingvision import sv_clips, _in_any
    for stem, v in sv_clips().items():
        d = DATASET / f"yt_{stem}"
        if not d.is_dir():
            continue
        blob = json.loads((d / "swingvision_mask.json").read_text(encoding="utf-8"))
        labels = json.loads((d / "labels.json").read_text(encoding="utf-8"))["labels"]
        sw, sh = blob["src_wh"]; lw, lh = blob["frame_wh"]
        found = {int(k) for k, (x, y) in labels.items()
                 if _in_any(x * sw / lw, y * sh / lh, v["boxes"])}
        assert found == set(blob["drop_labels"]), f"{stem}: drop list is stale"
