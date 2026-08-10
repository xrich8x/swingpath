"""A mask on a labelling input is worse than no mask when it is wrong.

The first far-court pilot put 5 of 36 human clicks inside a burned-in scoreboard,
so the queue now paints those graphics out. But the same tool, run too greedily,
painted 37% of one frame including the court — and a labeller shown a grey court
cannot find a ball that is there. Both directions are pinned here.
"""

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("cv2")

import mask_hud as mh  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def _agree(h=200, w=300, boxes=(), base=0.1):
    """An agreement map: `base` everywhere, 1.0 inside each (x, y, w, h)."""
    a = np.full((h, w), base, np.float32)
    for x, y, bw, bh in boxes:
        a[y:y + bh, x:x + bw] = 1.0
    return a


def _plate(h=200, w=300, boxes=()):
    """A median plate with synthetic structure (stripes) inside each box."""
    p = np.full((h, w, 3), 40, np.uint8)
    for x, y, bw, bh in boxes:
        p[y:y + bh, x:x + bw] = 30
        p[y:y + bh:3, x:x + bw] = 230        # hard horizontal edges, like text
    return p


# --- what the rule must ACCEPT ------------------------------------------------

def test_a_structured_rigid_panel_flush_to_a_border_is_a_graphic():
    box = (0, 0, 60, 40)
    got = mh.boxes_from_agreement(_agree(boxes=[box]), (300, 200),
                                  _plate(boxes=[box]))
    assert len(got) == 1
    assert (got[0]["x"], got[0]["y"]) == (0, 0)
    assert got[0]["src"] == "auto"


def test_boxes_come_back_in_source_pixels_not_working_pixels():
    """Stats run on a downscaled frame; a box applied at the wrong scale would
    paint the wrong part of the 1080p frame the labeller actually sees."""
    box = (0, 0, 60, 40)
    got = mh.boxes_from_agreement(_agree(boxes=[box]), (1200, 800),
                                  _plate(boxes=[box]))
    assert got[0]["w"] == 60 * 4 and got[0]["h"] == 40 * 4


# --- what the rule must REJECT, each for its own reason ------------------------

def test_a_large_rigid_region_is_the_sky_or_the_court_not_a_graphic():
    box = (0, 0, 200, 150)                    # 50% of the frame
    assert mh.boxes_from_agreement(_agree(boxes=[box]), (300, 200),
                                   _plate(boxes=[box])) == []


def test_a_rigid_region_away_from_every_border_is_not_a_graphic():
    """An overlay is composited against an edge; a still object mid-court is not."""
    box = (120, 80, 60, 40)
    assert mh.boxes_from_agreement(_agree(boxes=[box]), (300, 200),
                                   _plate(boxes=[box])) == []


def test_a_rigid_region_whose_surround_is_equally_rigid_is_scenery():
    """THE CONSTRAINT THAT KEEPS THE COURT OUT. An empty court is rigid, but so
    is everything around it; a scoreboard is rigid while the scene behind moves."""
    box = (0, 0, 60, 40)
    a = _agree(boxes=[box], base=1.0)         # the whole frame is rigid
    assert mh.boxes_from_agreement(a, (300, 200), _plate(boxes=[box])) == []


def test_a_rigid_flat_region_with_no_structure_is_not_a_graphic():
    """A strip of empty court under a busy sideline passes every other test."""
    box = (0, 0, 60, 40)
    flat = np.full((200, 300, 3), 40, np.uint8)
    assert mh.boxes_from_agreement(_agree(boxes=[box]), (300, 200), flat) == []


def test_merging_two_legal_boxes_cannot_exceed_the_area_cap():
    """A union of legal boxes is not itself legal — letting one through is how a
    first cut painted 37% of a frame, court included."""
    boxes = [(0, 0, 55, 45), (50, 0, 55, 45), (100, 0, 55, 45), (150, 0, 55, 45)]
    got = mh.boxes_from_agreement(_agree(boxes=boxes), (300, 200), _plate(boxes=boxes))
    assert all(b["w"] * b["h"] <= mh.MAX_AREA_FRAC * 300 * 200 for b in got)


# --- painting ------------------------------------------------------------------

def test_apply_mask_changes_only_the_declared_boxes():
    img = np.random.default_rng(0).integers(0, 255, (100, 120, 3), dtype=np.uint8)
    out = mh.apply_mask(img, [{"x": 10, "y": 20, "w": 30, "h": 15}])
    assert (out[20:35, 10:40] == np.array(mh.FILL, np.uint8)).all()
    keep = np.ones(img.shape[:2], bool)
    keep[20:35, 10:40] = False
    assert (out[keep] == img[keep]).all(), "painted outside its own box"


def test_a_rejected_proposal_is_recorded_but_never_painted():
    """Two auto proposals lie on the court. They are kept in the file so the
    record of the refusal survives, and a re-run cannot resurrect them."""
    img = np.full((100, 120, 3), 7, np.uint8)
    boxes = [{"x": 0, "y": 0, "w": 20, "h": 20, "src": "rejected"}]
    assert (mh.apply_mask(img, boxes) == img).all()
    assert mh._drop_rejected(
        [{"x": 5, "y": 5, "w": 4, "h": 4, "src": "auto"}], boxes) == []


def test_a_hand_authored_box_survives_absorbing_an_auto_one():
    """Only manual boxes cover the score panels. If merging made one disposable,
    the next detector re-run would silently delete the mask."""
    got = mh._merge([{"x": 0, "y": 0, "w": 50, "h": 50, "src": "manual"},
                     {"x": 10, "y": 10, "w": 10, "h": 10, "src": "auto"}])
    assert len(got) == 1 and got[0]["src"] == "manual"


def test_a_rejected_box_never_shadows_a_hand_authored_one():
    manual = [{"x": 0, "y": 0, "w": 40, "h": 40, "src": "manual"}]
    rejected = [{"x": 0, "y": 0, "w": 100, "h": 100, "src": "rejected"}]
    assert mh._drop_rejected(manual, rejected) == manual


def test_covers_is_half_open_so_a_box_edge_is_not_double_counted():
    b = [{"x": 10, "y": 10, "w": 5, "h": 5}]
    assert mh.covers(b, 10, 10) and not mh.covers(b, 15, 10)


# --- the committed mask file ---------------------------------------------------

MASKS = REPO / "data" / "hud_masks.json"


@pytest.mark.skipif(not MASKS.is_file(), reason="no committed mask file")
def test_every_committed_box_is_inside_its_own_frame():
    doc = json.loads(MASKS.read_text(encoding="utf-8"))
    for name, c in doc["clips"].items():
        w, h = c["src_wh"]
        for b in c["boxes"]:
            assert 0 <= b["x"] and 0 <= b["y"], f"{name} {b}"
            assert b["x"] + b["w"] <= w and b["y"] + b["h"] <= h, f"{name} {b}"
            assert b.get("src") in {"auto", "manual", "rejected"}, f"{name} {b}"


@pytest.mark.skipif(not MASKS.is_file(), reason="no committed mask file")
def test_no_clip_is_mostly_masked():
    """A generous mask over sky costs nothing; a generous mask over the court
    costs exactly the labels this queue exists to collect."""
    doc = json.loads(MASKS.read_text(encoding="utf-8"))
    for name, c in doc["clips"].items():
        w, h = c["src_wh"]
        painted = sum(b["w"] * b["h"] for b in c["boxes"]
                      if b.get("src") != "rejected")
        assert painted / (w * h) < 0.25, f"{name} masks {painted / (w * h):.0%}"
