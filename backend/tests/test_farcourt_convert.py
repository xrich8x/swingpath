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
    # The midpoint click must MOVE, or the (separate) motion test rejects the gap
    # and this stops measuring the anchor tolerance it is named for.
    labels = {"0": _click(*off), "1": _click(300.0, 200.0)}
    assert f2d.adjudicate(man720, labels)[1][0]["accepted"] is False
    assert f2d.adjudicate(man1080, labels)[1][0]["accepted"] is True


def test_turning_the_control_off_keeps_everything_but_still_records_the_verdict():
    man = {"frames": _trio(0)}
    labels = {"0": _click(600, 400), "1": _click(610, 405)}
    accepted, verdicts = f2d.adjudicate(man, labels, enforce=False)
    assert len(accepted) == 3
    assert verdicts[0]["anchors_confirmed"] == [], "the measurement must survive"


# --- the click-motion test ------------------------------------------------------
# Reported-only until 2026-08-13, then ENFORCED. The change is not a change of
# mind, it is a change of evidence: the threshold was originally found AFTER
# looking at the twelve gaps that suggested it, and a cutoff fitted to its own
# evidence is a memory, not a control. It has since reproduced on 49 INDEPENDENT
# gaps (farcourt_cal1) with a bimodal distribution, a valley at 9-16 px, and 17
# clicks at exactly zero. data/output/farcourt_l2.md.

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


def test_a_zero_motion_gap_is_now_rejected():
    """A ball in play cannot be in the same place two frames apart, so a click
    that never moves is a static object by definition.

    This test previously asserted the OPPOSITE — that the diagnostic never gated —
    on the grounds that a cutoff fitted to twelve gaps would filter real far-court
    balls. That reasoning was right for the evidence available then. It was
    replaced only once the threshold reproduced on an independent round, where 17
    of 49 clicks sat at exactly zero: those are not noisy labels, they are the
    labeller clicking the identical pixel twice."""
    man = {"frames": _trio(0)}
    labels = {"0": _click(100, 50), "1": _click(100, 50), "2": _click(100, 50)}
    accepted, verdicts = f2d.adjudicate(man, labels)
    assert verdicts[0]["click_motion_px"] == 0.0
    assert verdicts[0]["accepted"] is False and accepted == []


def test_the_motion_test_can_be_disabled():
    """0 restores the pre-2026-08-13 behaviour, so the earlier rounds stay
    re-adjudicable exactly as they were scored at the time."""
    man = {"frames": _trio(0)}
    labels = {"0": _click(100, 50), "1": _click(100, 50), "2": _click(100, 50)}
    accepted, verdicts = f2d.adjudicate(man, labels, min_motion_px=0.0)
    assert verdicts[0]["accepted"] is True and len(accepted) == 3


def test_the_motion_threshold_scales_with_frame_height():
    """Like every other pixel threshold here: the same physical travel covers
    1.5x the pixels at 1080p, so a click that passes at 720p can fail at 1080p."""
    lab = {"0": _click(100, 50), "1": _click(110, 50), "2": _click(110, 50)}
    assert f2d.adjudicate({"frames": _trio(0, height=720)}, lab)[1][0]["accepted"] is True
    assert f2d.adjudicate({"frames": _trio(0, height=1080)}, lab)[1][0]["accepted"] is False


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
                               {str(f): _click(20.0, 20.0) for f in (10, 20, 30)})
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
                               {str(f): _click(20.0, 20.0) for f in (10, 20, 30)})
    assert [m["source_frame"] for m in rt["mismatches"]] == [20]
    assert rt["mismatches"][0]["closest_to"] == 21


PILOT = REPO / "data" / "labels" / "farcourt_pilot.manifest.json"


@pytest.mark.skipif(not PILOT.is_file(), reason="pilot queue not present")
def test_the_shipped_pilot_queue_is_quarantined():
    """Roughly a third of its 36 clicks are on a graphic or on empty background.
    They are kept as evidence and must never become training data."""
    with pytest.raises(SystemExit, match="contaminated"):
        l2d.refuse_if_contaminated(PILOT)


# --- the round-trip gate's tie case (2026-08-13) ---------------------------------
# The gate asks "is this sample closest to the frame it claims?" via an argmin. On
# a static court neighbouring frames TIE, and argmin then decides by dict order
# rather than by pixels — measured on TilAFMPc0yg:2787, where frames 2786 and 2787
# both score 2.575. That was reported as a hard mismatch. It is the same
# "the argmin carries no information" case the gate already reports as unresolved,
# so it is now judged on the same min_margin.

def _verdict(d, f, min_margin=0.02):
    """The gate's decision rule, isolated from video I/O."""
    best = min(d, key=d.get)
    others = [v for g, v in d.items() if g != f]
    margin = (min(others) - d[f]) / max(d[f], 1e-6) if others else 0.0
    lead = (d[f] - d[best]) / max(d[f], 1e-6)
    if best != f and lead >= min_margin:
        return "mismatch"
    return "unresolved" if (best != f or margin < min_margin) else "ok"


def test_an_exact_tie_is_unresolved_not_a_mismatch():
    d = {2786: 2.575, 2787: 2.575, 2788: 2.702}
    assert _verdict(d, 2787) == "unresolved"


def test_a_real_gradient_to_another_frame_is_still_a_mismatch():
    """RZ_wyJ9rI3Q:1231 — monotonic across the window, best is 21% better than
    the claimed frame, so the true match is probably outside it."""
    d = {1228: 3.01, 1229: 2.946, 1230: 2.887, 1231: 2.764,
         1232: 2.618, 1233: 2.413, 1234: 2.187}
    assert _verdict(d, 1231) == "mismatch"


def test_a_clean_match_still_passes():
    d = {9: 5.0, 10: 1.0, 11: 5.2}
    assert _verdict(d, 10) == "ok"


# --- the gate's index mapping (2026-08-13) ---------------------------------------
# build() numbers each triplet by its POSITION in the usable-frame list, so the
# round-trip gate must invert that with the SAME list. It re-derived the list and
# included `unsure` frames, which build() drops; on any clip with one, every later
# sample was checked against the wrong source frame and the gate reported a phantom
# 2-3 frame offset. It discriminated perfectly on the real data: the only two clips
# that failed were the only two with an unsure label, 19 with none all passed.

def test_usable_frames_drops_unsure_and_keeps_both_verdicts():
    import labels_to_dataset as l2d
    raw = {"10": {"ball": True, "x": 1.0, "y": 2.0},
           "11": {"unsure": True, "x": 3.0, "y": 4.0},   # dropped by build()
           "12": {"ball": False},
           "13": {"ball": True, "x": None}}             # no position -> unusable
    assert l2d.usable_frames(raw) == [10, 12]


def test_the_gate_and_the_builder_agree_on_which_frames_are_written():
    """The bug was two implementations of one rule. This fails if they diverge."""
    import labels_to_dataset as l2d
    raw = {"5": {"ball": True, "x": 1.0, "y": 1.0},
           "6": {"unsure": True},
           "7": {"ball": True, "x": 2.0, "y": 2.0},
           "8": {"ball": False}}
    wanted = l2d.usable_frames(raw)
    # what build() would compute internally, spelled out independently here
    pos = {int(k) for k, v in raw.items()
           if not v.get("unsure") and v.get("ball") and v.get("x") is not None}
    neg = {int(k) for k, v in raw.items()
           if not v.get("unsure") and v.get("ball") is False}
    assert wanted == sorted(pos | neg)
    # and the sample index for entry k is 3k+2, so an unsure frame must not shift it
    assert wanted.index(7) == 1, "an unsure frame must not occupy a triplet slot"
