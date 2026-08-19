"""Which rule ended each rally, and why the score is labelled unvalidated.

WHY THIS EXISTS
---------------
The rally/score layer has NO ground truth: no point boundary has ever been
labelled, so unlike the ball (1851 human clicks) or the court (20 clips) it
cannot be scored at all. The external review's conclusion was that the score and
point count "should currently be treated as unvalidated" — and nothing in the
product said so.

It cannot be scored, but it CAN report which rule split it. `segment_rallies`
breaks on two things: the tennis second-bounce rule, and a bare 2.0 s gap timer.
Measured on yt_match40, **62 of 62 breaks came from the timer and 0 from the
tennis rule** — segmentation is a heuristic wearing a rule's clothes. That is a
statement the code can make about itself without any labels, so it is what the
UI shows instead of a confident scoreline.
"""

from swingvision.events import segment_rallies


# --- the default contract must not have moved -------------------------------

def test_default_return_shape_is_unchanged():
    """with_reasons defaults off, so every existing caller is untouched."""
    got = segment_rallies([0.0, 1.0, 2.0, 9.0, 10.0], gap_s=4.0)
    assert got == [[0, 1, 2], [3, 4]]
    assert isinstance(got, list) and isinstance(got[0], list)


def test_reasons_do_not_change_the_split():
    times, gap, force = [0.0, 1.0, 2.0, 9.0, 10.0], 4.0, [1]
    plain = segment_rallies(times, gap_s=gap, force_break_after=force)
    withr, _ = segment_rallies(times, gap_s=gap, force_break_after=force,
                               with_reasons=True)
    assert plain == withr


# --- the diagnosis itself ---------------------------------------------------

def test_a_pure_timeout_split_is_reported_as_such():
    """The yt_match40 shape: every break from the clock, none from tennis."""
    _, r = segment_rallies([0.0, 1.0, 9.0, 10.0, 20.0], gap_s=4.0,
                           with_reasons=True)
    assert r == {"timeout": 2, "tennis_rule": 0}


def test_the_tennis_rule_is_counted_separately():
    _, r = segment_rallies([0.0, 1.0, 2.0, 3.0], gap_s=4.0,
                           force_break_after=[1], with_reasons=True)
    assert r["tennis_rule"] == 1
    assert r["timeout"] == 0


def test_both_rules_can_fire_in_one_clip():
    # break after idx 1 (tennis), then a 10 s hole (timeout)
    _, r = segment_rallies([0.0, 1.0, 2.0, 12.0], gap_s=4.0,
                           force_break_after=[1], with_reasons=True)
    assert r["tennis_rule"] == 1 and r["timeout"] == 1


def test_a_single_unbroken_rally_reports_no_breaks():
    """Zero breaks must not be confused with 'the tennis rule fired'."""
    _, r = segment_rallies([0.0, 1.0, 2.0], gap_s=4.0, with_reasons=True)
    assert r == {"timeout": 0, "tennis_rule": 0}


def test_empty_input_is_safe():
    rallies, r = segment_rallies([], gap_s=4.0, with_reasons=True)
    assert rallies == [] and r == {"timeout": 0, "tennis_rule": 0}
