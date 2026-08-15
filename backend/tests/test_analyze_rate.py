"""`--full-rate` is frame_step=1, stated as a product mode.

The mechanism already existed: `--frame-step 1` has always processed every
frame. What did not exist was any way for a user to know that on 60fps footage
this is the largest measured accuracy gain in the tool (+5.8 pts close-call
accuracy at a 1.5 m mount, arc reprojection 148->91 px, HUD speed error
38.9->33.1%), or that it costs 2x perception time and is a wash-to-negative on
ball detection. A bare integer communicates none of that.

These tests pin the wiring, not the measurement — the measurement is
data/output/fps_decision.md and was done in Session H parts 5-6.

TRAP 1 NOTE: this makes step 1 a legitimate SHIPPED configuration on 60fps
clips. The default is still 'auto', so "shipped behaviour" with no qualifier
still means auto, and any number from a full-rate run must say so.
"""

import argparse
import contextlib
import io
import types

import pytest

import run as run_cli


def _fake_match():
    stats = types.SimpleNamespace(
        shot_count=3, rally_count=1, avg_speed_kmh=60.0, top_speed_kmh=90.0,
        line_calls={"in": 2, "out": 1})
    return types.SimpleNamespace(stats=stats)


def _capture_frame_step(monkeypatch):
    """Run `analyze` with everything stubbed, return the frame_step it passed."""
    seen = {}

    def fake_analyze_video(video, **kw):
        seen.update(kw)
        return _fake_match()

    monkeypatch.setattr(run_cli.pipeline, "analyze_video", fake_analyze_video)
    return seen


def _run(argv, monkeypatch):
    seen = _capture_frame_step(monkeypatch)
    args = run_cli.build_parser().parse_args(argv)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = args.func(args)
    return rc, seen, buf.getvalue()


def test_full_rate_resolves_to_frame_step_1(monkeypatch):
    rc, seen, _ = _run(["analyze", "clip.mp4", "--full-rate"], monkeypatch)
    assert rc == 0
    assert seen["frame_step"] == 1, (
        "--full-rate must reach the pipeline as frame_step=1; got "
        f"{seen['frame_step']!r}")


def test_default_is_still_auto(monkeypatch):
    """The default must NOT change. 60fps at full rate doubles perception cost,
    so it is opt-in until someone has run a real match end to end."""
    _, seen, _ = _run(["analyze", "clip.mp4"], monkeypatch)
    assert seen["frame_step"] == "auto"


def test_explicit_frame_step_still_works(monkeypatch):
    _, seen, _ = _run(["analyze", "clip.mp4", "--frame-step", "3"], monkeypatch)
    assert seen["frame_step"] == "3"


def test_full_rate_says_what_it_costs_and_buys(monkeypatch):
    """A mode that doubles runtime must announce it, not just do it."""
    _, _, out = _run(["analyze", "clip.mp4", "--full-rate"], monkeypatch)
    assert "EVERY frame" in out
    assert "doubles perception time" in out, "the cost must be stated"
    assert "wash-to-negative" in out, "the honest downside must be stated"
    assert "No-op on 30fps" in out, "say when it changes nothing"


def test_full_rate_and_frame_step_are_mutually_exclusive():
    """Passing both is a contradiction, not a preference - argparse must refuse
    rather than silently letting one win."""
    parser = run_cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["analyze", "x.mp4", "--full-rate", "--frame-step", "2"])


def test_full_rate_help_carries_the_measured_tradeoff():
    """The number is the whole reason the flag exists; if the help loses it, the
    flag is back to being an uninterpretable integer."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        with pytest.raises(SystemExit):
            run_cli.build_parser().parse_args(["analyze", "--help"])
    help_text = buf.getvalue()
    assert "--full-rate" in help_text
    assert "DOUBLES perception time" in help_text
    assert "fps_decision.md" in help_text, "point at the evidence"
