"""The far-court queue's route into training data, and the two refusals on it.

Three things can quietly poison a training set from here, and each cost real
evidence to discover:

  * a midpoint label taken from a gap whose ANCHORS were both false locks. The
    human, finding no ball, clicks something — sky, foliage, a scoreboard — and
    the result is a Gaussian on empty background, which is worse than no label.
    MEASURED on the pilot: 7 of 12 gaps (data/output/farcourt_anchor_audit.md);
  * an off-by-one between the frame the human saw and the frame that gets
    built. Nothing downstream would ever show it;
  * the pilot's own labels being consumed by a later build because the only
    thing stopping them was a paragraph in an evidence file.
"""

import json
from pathlib import Path

import pytest

import farcourt_labels_to_dataset as f2d  # noqa: E402
import labels_to_dataset as l2d  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def _row(frame, bucket, prior, clip="c", gap=None, height=720, video="v.mp4"):
    r = {"frame": frame, "bucket": bucket, "src_dataset": clip, "src_frame": frame,
         "prior_x": prior[0], "prior_y": prior[1], "height": height, "width": 1280,
         "video": video, "video_frame": 1000 + frame}
    if gap is not None:
        r["gap"] = gap
    return r


def _trio(base, prior=(100.0, 50.0), **kw):
    return [_row(base, "anchor", prior, **kw),
            _row(base + 1, "farcourt_gap", prior, **kw),
            _row(base + 2, "anchor", prior, **kw)]


def _click(x, y):
    return {"ball": True, "x": x, "y": y}


# --- grouping frames back into gaps -------------------------------------------

def test_a_manifest_without_gap_ids_still_groups_anchor_mid_anchor():
    """The pilot's manifest predates the field and is the evidence the control is
    needed, so it has to stay adjudicable. Falling back to one-gap-per-frame
    would accept every midpoint — exactly the failure being guarded."""
    rows = _trio(0) + _trio(3)
    assert f2d.gap_ids(rows) == [0, 0, 0, 1, 1, 1]


def test_recorded_gap_ids_win_over_the_fallback():
    rows = _trio(0, gap=7) + _trio(3, gap=9)
    assert f2d.gap_ids(rows) == [7, 7, 7, 9, 9, 9]


def test_a_queue_built_without_anchors_gives_each_midpoint_its_own_gap():
    rows = [_row(0, "farcourt_gap", (1, 1)), _row(1, "farcourt_gap", (1, 1))]
    assert f2d.gap_ids(rows) == [0, 1]


# --- the anchor control --------------------------------------------------------

def test_a_gap_whose_anchors_the_human_did_not_confirm_is_dropped():
    man = {"frames": _trio(0)}
    labels = {"0": _click(600, 400), "1": _click(610, 405), "2": _click(620, 410)}
    accepted, verdicts = f2d.adjudicate(man, labels)
    assert accepted == [] and verdicts[0]["accepted"] is False


def test_one_confirmed_anchor_is_enough_to_keep_the_gap():
    man = {"frames": _trio(0)}
    labels = {"0": _click(102, 51), "1": _click(600, 400), "2": _click(900, 20)}
    accepted, verdicts = f2d.adjudicate(man, labels)
    assert len(accepted) == 3 and verdicts[0]["anchors_confirmed"] == [0]


def test_an_unsure_anchor_confirms_nothing():
    man = {"frames": _trio(0)}
    labels = {"0": {"ball": None, "unsure": True}, "1": _click(100, 50)}
    _acc, verdicts = f2d.adjudicate(man, labels)
    assert verdicts[0]["anchors_clicked"] == 0 and verdicts[0]["accepted"] is False


def test_a_no_ball_verdict_on_an_anchor_does_not_confirm_it():
    """A human saying "no ball" where the tracker locked is the tracker being
    WRONG, which is the opposite of confirmation."""
    man = {"frames": _trio(0)}
    labels = {"0": {"ball": False, "x": None, "y": None}, "1": _click(100, 50)}
    _acc, verdicts = f2d.adjudicate(man, labels)
    assert verdicts[0]["accepted"] is False


def test_the_tolerance_scales_with_frame_height():
    """Every pixel threshold in this stack scales by frame_height/720; the same
    physical miss covers 1.5x the pixels at 1080p."""
    off = (100.0 + 20.0, 50.0)                       # 20 px from the prior
    man720 = {"frames": _trio(0, height=720)}
    man1080 = {"frames": _trio(0, height=1080)}
    labels = {"0": _click(*off)}
    assert f2d.adjudicate(man720, labels)[1][0]["accepted"] is False
    assert f2d.adjudicate(man1080, labels)[1][0]["accepted"] is True


def test_turning_the_control_off_keeps_everything_but_still_records_the_verdict():
    man = {"frames": _trio(0)}
    labels = {"0": _click(600, 400), "1": _click(610, 405)}
    accepted, verdicts = f2d.adjudicate(man, labels, enforce=False)
    assert len(accepted) == 3
    assert verdicts[0]["anchors_confirmed"] == [], "the measurement must survive"


# --- the click-motion diagnostic ------------------------------------------------
# Reported, never enforced. The threshold that separates the cases was found AFTER
# looking at twelve gaps, so it is pre-registered for the next queue rather than
# fitted to that one — but the numbers themselves have to be right.

def test_click_motion_reports_a_static_click_against_a_moving_tracker():
    """The failure it exists to surface: the human clicks a wall mark while the
    tracker's own anchors are 240 px apart. Two different objects."""
    rows = [_row(0, "anchor", (100.0, 50.0)), _row(1, "farcourt_gap", (200.0, 150.0)),
            _row(2, "anchor", (300.0, 250.0))]
    labels = {"0": _click(700, 100), "1": _click(703, 100), "2": _click(706, 100)}
    human, tracker = f2d.click_motion(rows, labels)
    assert human == 6.0
    assert round(tracker) == 283


def test_click_motion_measures_the_humans_path_not_their_endpoints():
    """A ball that comes down and goes back up covers distance the endpoints hide."""
    rows = [_row(0, "anchor", (0.0, 0.0)), _row(1, "farcourt_gap", (0.0, 0.0)),
            _row(2, "anchor", (0.0, 0.0))]
    labels = {"0": _click(0, 0), "1": _click(0, 40), "2": _click(0, 0)}
    assert f2d.click_motion(rows, labels)[0] == 80.0


def test_unsure_and_no_ball_frames_drop_out_of_the_path():
    rows = [_row(0, "anchor", (0.0, 0.0)), _row(1, "farcourt_gap", (0.0, 0.0)),
            _row(2, "anchor", (0.0, 0.0))]
    labels = {"0": _click(0, 0), "1": {"ball": None, "unsure": True},
              "2": _click(0, 10)}
    assert f2d.click_motion(rows, labels)[0] == 10.0


def test_the_diagnostic_never_changes_a_verdict():
    """If it ever gated, a cutoff fitted to twelve gaps would be filtering real
    far-court balls — the exact data this whole queue exists to collect."""
    man = {"frames": _trio(0)}
    labels = {"0": _click(100, 50), "1": _click(100, 50), "2": _click(100, 50)}
    accepted, verdicts = f2d.adjudicate(man, labels)
    assert verdicts[0]["click_motion_px"] == 0.0
    assert verdicts[0]["accepted"] is True and len(accepted) == 3


# --- splitting one queue back into many clips ----------------------------------

def test_labels_are_split_by_source_video_and_rekeyed_to_source_frames():
    """The whole reason this file exists: labels_to_dataset takes ONE video and
    reads label keys as indices into it; the queue is 12 videos renumbered 0..N."""
    rows = _trio(0, video="a.mp4") + _trio(3, video="b.mp4")
    labels = {str(i): _click(10 + i, 20 + i) for i in range(6)}
    got = f2d.split_by_clip(rows, labels)
    assert sorted(got) == ["a.mp4", "b.mp4"]
    assert sorted(got["a.mp4"]) == ["1000", "1001", "1002"]
    assert got["b.mp4"]["1005"] == _click(15, 25)


def test_a_frame_with_no_source_video_is_not_split_into_a_dataset():
    """Two dataset dirs came from a pipeline that recorded no video; their frames
    are 512x288 JPEGs with no source to rebuild a triplet from."""
    rows = [_row(0, "farcourt_gap", (1, 1))]
    rows[0]["video"], rows[0]["video_frame"] = None, None
    assert f2d.split_by_clip(rows, {"0": _click(1, 1)}) == {}


# --- the contamination refusal --------------------------------------------------

def test_a_contaminated_manifest_is_refused(tmp_path):
    p = tmp_path / "q.manifest.json"
    p.write_text(json.dumps({"contaminated": "clicks on a scoreboard"}))
    with pytest.raises(SystemExit, match="contaminated"):
        l2d.refuse_if_contaminated(p)


def test_force_is_the_only_way_past_it(tmp_path):
    p = tmp_path / "q.manifest.json"
    p.write_text(json.dumps({"contaminated": "clicks on a scoreboard"}))
    l2d.refuse_if_contaminated(p, force=True)


def test_a_clean_or_missing_manifest_passes(tmp_path):
    ok = tmp_path / "q.manifest.json"
    ok.write_text(json.dumps({"clip": "q", "frames": []}))
    l2d.refuse_if_contaminated(ok)
    l2d.refuse_if_contaminated(tmp_path / "nope.manifest.json")


def test_the_manifest_is_found_from_the_labels_path():
    """The single-video converter is pointed at a *.labels.json, so the refusal
    only bites if the sibling manifest is derived correctly."""
    p = Path("data/labels/farcourt_pilot.labels.json")
    assert l2d._sibling_manifest(p).name == "farcourt_pilot.manifest.json"


# --- the round-trip gate --------------------------------------------------------

def _fake_clip(path, n=40):
    """A clip whose frames are all different, so "closest frame" is answerable."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (128, 96))
    rng = np.random.default_rng(7)
    for i in range(n):
        f = rng.integers(0, 60, (96, 128, 3), dtype=np.uint8)
        cv2.rectangle(f, (2 * i, 10), (2 * i + 14, 30), (250, 250, 250), -1)
        vw.write(f)
    vw.release()
    return path


def test_the_round_trip_gate_passes_a_correctly_built_dataset(tmp_path):
    pytest.importorskip("cv2")
    vid = _fake_clip(tmp_path / "c.mp4")
    lab = tmp_path / "c.labels.json"
    lab.write_text(json.dumps({"labels": {str(f): _click(20.0, 20.0)
                                          for f in (10, 20, 30)}}))
    l2d.build("c", vid, lab, tmp_path / "ds")
    rt = f2d.verify_round_trip(tmp_path / "ds", "c", vid,
                               {str(f): {} for f in (10, 20, 30)})
    assert rt["checked"] == 3 and rt["mismatches"] == []


def test_the_round_trip_gate_catches_an_off_by_one(tmp_path):
    """The failure this exists for. Nothing downstream would ever surface a
    label that describes the frame next door, so the check has to be able to
    tell them apart — a perceptual hash provably cannot (see the docstring on
    verify_round_trip)."""
    cv2 = pytest.importorskip("cv2")
    vid = _fake_clip(tmp_path / "c.mp4")
    lab = tmp_path / "c.labels.json"
    lab.write_text(json.dumps({"labels": {str(f): _click(20.0, 20.0)
                                          for f in (10, 20, 30)}}))
    l2d.build("c", vid, lab, tmp_path / "ds")
    # Replace one built sample with its neighbour, exactly as a seek off by one
    # would have written it.
    cap = cv2.VideoCapture(str(vid))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 21)
    ok, wrong = cap.read()
    cap.release()
    assert ok
    cv2.imwrite(str(tmp_path / "ds" / "c" / "00005.jpg"),
                cv2.resize(wrong, (512, 288)))
    rt = f2d.verify_round_trip(tmp_path / "ds", "c", vid,
                               {str(f): {} for f in (10, 20, 30)})
    assert [m["source_frame"] for m in rt["mismatches"]] == [20]
    assert rt["mismatches"][0]["closest_to"] == 21


PILOT = REPO / "data" / "labels" / "farcourt_pilot.manifest.json"


@pytest.mark.skipif(not PILOT.is_file(), reason="pilot queue not present")
def test_the_shipped_pilot_queue_is_quarantined():
    """Roughly a third of its 36 clicks are on a graphic or on empty background.
    They are kept as evidence and must never become training data."""
    with pytest.raises(SystemExit, match="contaminated"):
        l2d.refuse_if_contaminated(PILOT)
