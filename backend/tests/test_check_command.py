"""`run.py check` must predict `analyze`, and must quote the measured error.

Two properties are pinned here, because both were broken and both are the kind
of thing that silently regresses.

1. DELEGATION. `check` used to read ONE frame and run
   detect_court_learned -> detect_court, while `analyze` runs
   `courtfit.fit_video_frames` consensus over 8 frames and accepts only >=6
   agreeing. Measured on data/demo30.mp4 with no keypoints: the old path
   returned a court and graded it POOR, while `analyze` REFUSES the clip
   outright ("2 of 8 frames (needs 6)"). A pre-flight that blesses a clip the
   product rejects is worse than no pre-flight. `check` now calls
   `pipeline.calibrate_video` — the same entry point — so the two cannot drift.
   This is trap 15: predict a behaviour by invoking it, never by re-deriving it.

2. THE CALL-ACCURACY NUMBER REACHES THE USER. `calibration.expected_call_accuracy`
   and `CALL_MAJORITY_FLOOR_PCT` were computed, documented and test-pinned, and
   were reachable only through `courtfit.setup_verdict`, which `check` did not
   call. The old output ended at "elevation 0.42" — a proxy. These tests fail if
   the measured number stops being printed beside its floor.
"""

import argparse
import io
import contextlib

import numpy as np
import pytest

import run as run_cli
from swingvision import calibration, court, courtfit


def _frame(w=1280, h=720):
    return np.zeros((h, w, 3), dtype=np.uint8)


class _StubCap:
    """cv2.VideoCapture stand-in: check only needs one frame for setup_verdict."""

    def __init__(self, frame):
        self._f = frame

    def read(self):
        return True, self._f

    def release(self):
        pass


def _corners_for_height(height_m, w=1280, h=720):
    """Doubles corners as seen by a REAL camera at `height_m`, through the same
    projection the shape lock uses. Keeps the fixtures physical: a hand-made
    quad no camera could see would be graded 'poor' for the wrong reason, and
    setup_verdict would never reach the call-accuracy branch at all."""
    back_m = 6.0
    pitch = np.arctan2(float(height_m), back_m + court.LENGTH / 2.0)
    p = [court.DOUBLES_WIDTH / 2.0, -back_m, float(height_m), 0.0, pitch, w * 0.9]
    named = courtfit._cam_corners(p, w, h, court)
    assert named is not None, f"no valid camera at {height_m} m for the fixture"
    return {n: [float(xy[0]), float(xy[1])] for n, xy in named.items()}


# ---------------------------------------------------------------- delegation

def test_check_calls_the_same_calibration_entry_point_as_analyze(monkeypatch, tmp_path):
    """check must go through pipeline.calibrate_video, not its own detector."""
    seen = {}

    def fake_calibrate_video(video_path, keypoints_path=None, overlay_path=None):
        seen["video"] = video_path
        seen["keypoints"] = keypoints_path
        named = _corners_for_height(3.0)
        H = calibration.homography_from_landmarks(named)
        return H, 0.5, "auto-court(7/8)", named, 90.0, 0.0, None

    monkeypatch.setattr(run_cli.pipeline, "calibrate_video", fake_calibrate_video)
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", lambda *a, **k: _StubCap(_frame()))

    vid = tmp_path / "clip.mp4"
    args = argparse.Namespace(video=str(vid), keypoints="corners.json")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_cli._cmd_check(args)

    assert rc == 0
    assert seen.get("video") == str(vid), (
        "check did not call pipeline.calibrate_video - it is predicting analyze "
        "by re-deriving it again (trap 15)"
    )
    assert seen.get("keypoints") == "corners.json", (
        "check must pass --keypoints through, or it grades a different court "
        "than analyze would use")
    # and it reports what that shared path decided
    assert "auto-court(7/8)" in buf.getvalue()


def test_check_reports_the_refusal_analyze_would_raise(monkeypatch, tmp_path):
    """When calibrate_video refuses, check must say analyze would stop, and
    pass the refusal through verbatim rather than grading some other court."""
    msg = ("auto court calibration did not reach high confidence (the best court "
           "was confirmed on only 2 of 8 frames (needs 6)).")

    def refusing(video_path, keypoints_path=None, overlay_path=None):
        raise ValueError(msg)

    monkeypatch.setattr(run_cli.pipeline, "calibrate_video", refusing)

    import cv2
    monkeypatch.setattr(cv2, "VideoCapture",
                        lambda *a, **k: _StubCap(_frame()))

    args = argparse.Namespace(video=str(tmp_path / "c.mp4"), keypoints=None)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_cli._cmd_check(args)
    out = buf.getvalue()

    assert rc == 0
    assert "REFUSED" in out
    assert "2 of 8 frames" in out, "the refusal must be passed through, not paraphrased"


# ------------------------------------------------------- the number is printed

@pytest.mark.parametrize("height_m", [1.0, 1.5, 3.0, 6.0])
def test_check_prints_call_accuracy_and_floor_at_every_height(monkeypatch, tmp_path,
                                                              height_m):
    named = _corners_for_height(height_m)

    def fake_calibrate_video(video_path, keypoints_path=None, overlay_path=None):
        H = calibration.homography_from_landmarks(named)
        return H, 0.4, "manual", named, 90.0, 0.0, None

    monkeypatch.setattr(run_cli.pipeline, "calibrate_video", fake_calibrate_video)
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", lambda *a, **k: _StubCap(_frame()))

    args = argparse.Namespace(video=str(tmp_path / "c.mp4"), keypoints=None)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_cli._cmd_check(args)
    out = buf.getvalue()

    expect = calibration.expected_call_accuracy(height_m)
    floor = calibration.CALL_MAJORITY_FLOOR_PCT

    assert "close calls correct" in out, "call accuracy is not reported at all"
    assert f"{expect:.0f}%" in out, (
        f"expected the measured {expect:.0f}% for a {height_m} m mount in the output")
    assert f"{floor:.0f}%" in out, "the majority-class floor must be quoted beside it"
    # The old output's proxy must not come back as the headline.
    assert "elevation" not in out.lower()


def test_check_says_plainly_when_the_mount_is_worthless(monkeypatch, tmp_path):
    """A 1.0 m mount scores 54.0% against a 56.2% floor - worse than always
    answering 'in'. That has to read as a stop sign, not as a statistic."""
    named = _corners_for_height(1.0)

    def fake_calibrate_video(video_path, keypoints_path=None, overlay_path=None):
        H = calibration.homography_from_landmarks(named)
        return H, 0.4, "manual", named, 90.0, 0.0, None

    monkeypatch.setattr(run_cli.pipeline, "calibrate_video", fake_calibrate_video)
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", lambda *a, **k: _StubCap(_frame()))

    args = argparse.Namespace(video=str(tmp_path / "c.mp4"), keypoints=None)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_cli._cmd_check(args)
    out = buf.getvalue()

    assert "ADDS NOTHING" in out, (
        "a mount at or below the majority-class floor must be called out, not "
        "reported as a neutral percentage")


def test_check_has_no_court_weights_flag():
    """`analyze` has no --court-weights. A checkpoint override honoured only by
    check would reintroduce the very divergence this command exists to remove."""
    parser = run_cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["check", "x.mp4", "--court-weights", "w.pt"])
