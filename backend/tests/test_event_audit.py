"""event_audit.py — the product-level false-fire metric (Session F step 1).

These pin the parts that decide what a number MEANS: which events leave the
denominator, and how a landing that is really a hit is kept from being counted
twice.
"""

import pytest

from event_audit import adjudicate, coverage_at, landing_verdict, wilson95


# frame -> click dict (ball) or False (no ball). `unsure` labels never appear
# here: the human declined to call it, so neither a pass nor a phantom can be
# read off them.
DECIDED = {100: {"x": 50.0, "y": 60.0}, 200: False, 300: {"x": 10.0, "y": 10.0}}
FPS = 60.0


def at_identity(f):
    return f


def track_with(frame, xy):
    """The real track is a list indexed by PROCESSED frame, so the stand-in has
    to be one too — a dict would silently take the `pf >= len(tr)` branch and
    every localisation test would pass for the wrong reason."""
    tr = [None] * 400
    tr[frame] = list(xy)
    return tr


def test_event_far_from_any_label_is_unknown_not_a_pass():
    """The load-bearing rule. At a 116-frame label spacing most events have no
    nearby label at all; scoring those as either clean or phantom would be
    inventing evidence."""
    v, _, _, d, _ = adjudicate(150 / FPS, FPS, DECIDED, 3, None, at_identity)
    assert v == "unknown"
    assert d == 50


def test_event_on_a_no_ball_label_is_a_phantom():
    v, f, near, d, _ = adjudicate(202 / FPS, FPS, DECIDED, 3, None, at_identity)
    assert (v, f, near, d) == ("phantom_ball", 202, 200, 2)


def test_tolerance_is_inclusive_at_k():
    assert adjudicate(203 / FPS, FPS, DECIDED, 3, None,
                      at_identity)[0] == "phantom_ball"
    assert adjudicate(204 / FPS, FPS, DECIDED, 3, None,
                      at_identity)[0] == "unknown"


def test_ball_present_splits_on_the_10px_click_tolerance():
    """Same tolerance the gold ladder scores recall at, so 'localised' here means
    the same thing as a hit there."""
    assert adjudicate(100 / FPS, FPS, DECIDED, 3, track_with(100, (50.0, 60.0)),
                      at_identity)[0] == "localised"
    assert adjudicate(100 / FPS, FPS, DECIDED, 3, track_with(100, (59.0, 60.0)),
                      at_identity)[0] == "localised"
    assert adjudicate(100 / FPS, FPS, DECIDED, 3, track_with(100, (61.0, 60.0)),
                      at_identity)[0] == "ball_elsewhere"


def test_without_a_track_the_verdict_stops_at_ball_present():
    """No perception cache must degrade the report, never fabricate a column."""
    assert adjudicate(100 / FPS, FPS, DECIDED, 3, None,
                      at_identity)[0] == "ball_present"


def test_click_ok_false_never_localises():
    """Landings are adjudicated for presence only; the contact usually falls
    between detections, so demanding a 10 px match would blame the smoother for
    doing its job."""
    assert adjudicate(100 / FPS, FPS, DECIDED, 3, track_with(100, (999.0, 999.0)),
                      at_identity, click_ok=False)[0] == "ball_present"


def test_unprocessed_frame_falls_back_to_ball_present():
    """A decimated run cannot look at every source frame; index_of returns None
    there and the audit must not read that as the ball being elsewhere."""
    assert adjudicate(100 / FPS, FPS, DECIDED, 3, track_with(100, (50.0, 60.0)),
                      lambda f: None)[0] == "ball_present"


def test_a_coasted_landing_is_not_a_phantom():
    """The three-way split. pipeline.py says the exact contact usually falls
    BETWEEN detections, so a landing on an interpolated frame is the smoother
    working, not a false fire. Calling it a phantom would make every recall
    improvement look like a precision regression."""
    assert landing_verdict("ball_present", True) == "coasted"
    assert landing_verdict("ball_present", False) == "real_detection"
    assert landing_verdict("localised", True) == "coasted"
    assert landing_verdict("ball_elsewhere", False) == "real_detection"


def test_a_landing_on_a_no_ball_click_stays_a_phantom():
    """Only the third bucket counts against us, and the coasted flag must not
    launder it."""
    assert landing_verdict("phantom_ball", True) == "phantom_ball"
    assert landing_verdict("phantom_ball", False) == "phantom_ball"


def test_unknown_landings_pass_through_the_split_untouched():
    assert landing_verdict("unknown", None) == "unknown"


def test_wilson_interval_is_wide_at_this_n():
    """The number that stops '1/8' being read as a rate. If this ever narrows,
    the CI is being computed on the wrong denominator."""
    lo, hi = wilson95(2, 12)
    assert lo <= 5 and hi >= 40
    assert wilson95(0, 0) is None
    lo, hi = wilson95(0, 12)
    assert lo == 0 and hi > 0


def test_coverage_at_is_monotonic_in_k():
    frames = [0, 50, 100]
    c = [coverage_at(frames, 120, k) for k in (0, 2, 5, 10)]
    assert c == sorted(c)
    assert c[0] < 100.0


def test_dense_labels_give_full_coverage():
    assert coverage_at(list(range(0, 100, 2)), 100, 1) == pytest.approx(100.0)
