"""`bounce_reset` is a MEASURED NEGATIVE kept off by default.

It must stay inert unless explicitly asked for - the shipped smoother path is
what every published number was measured on, and a parameter that quietly
changed it would invalidate them. These tests pin that, and pin that the flag
is not a no-op when it IS asked for (a knob that does nothing would let a future
sweep "measure" it and conclude wrongly).

See smooth_forecast's docstring for the gate it failed and the numbers.
"""

import numpy as np
import pytest

from swingvision import ball as ball_mod


def _falling_then_bouncing(n=40, x0=100.0, vx=6.0, floor=400.0, kink=20, v=25.0):
    """A ball descending in image space (y grows downward) that bounces at frame
    `kink` and rises again.

    TWO THINGS THIS FIXTURE HAS TO GET RIGHT, both learned by getting them wrong:

    1. The corner must be a VELOCITY DISCONTINUITY, not a smooth parabola. A
       parabola is exactly what a constant-acceleration model predicts, so it
       sails through the innovation gate and nothing is ever rejected.
    2. It must be SHARP ENOUGH. The CA model carries an acceleration term, and
       with sigma_jerk=1.0 it absorbs a 20 px/frame velocity swing without a
       single rejection. Measured: 20 px swing changes nothing, 40 px does. A
       real bounce on a 720p clip is far sharper than either.
    """
    pts = []
    for i in range(n):
        y = floor - v * (kink - i) if i <= kink else floor - v * (i - kink)
        pts.append((x0 + vx * i, y))
    return pts


def test_off_by_default():
    import inspect
    sig = inspect.signature(ball_mod.smooth_forecast)
    assert sig.parameters["bounce_reset"].default is False, (
        "bounce_reset failed its pre-registered gate; it must not be on by default")


def test_explicit_false_is_identical_to_the_default_path():
    pts = _falling_then_bouncing()
    a, ca, _ = ball_mod.smooth_forecast(list(pts), fps_eff=30.0)
    b, cb, _ = ball_mod.smooth_forecast(list(pts), fps_eff=30.0, bounce_reset=False)
    assert a == b and ca == cb


def test_flag_is_not_inert_when_enabled():
    """A knob that changes nothing would let a future sweep 'measure' it and
    conclude it does no harm, which is worse than not having it."""
    pts = _falling_then_bouncing()
    a, _, _ = ball_mod.smooth_forecast(list(pts), fps_eff=30.0)
    b, _, _ = ball_mod.smooth_forecast(list(pts), fps_eff=30.0, bounce_reset=True)
    same = all((p is None and q is None) or (p is not None and q is not None
                                             and np.allclose(p, q))
               for p, q in zip(a, b))
    assert not same, "bounce_reset=True produced an identical track on a bounce"


def test_rising_ball_does_not_trigger_the_reset():
    """The test is directional on purpose: only a descending model can bounce.
    A ball travelling straight up must not be reset, or the flag would fire on
    ordinary post-contact flight."""
    pts = [(100.0 + 6.0 * i, 400.0 - 8.0 * i) for i in range(30)]   # rising
    a, _, _ = ball_mod.smooth_forecast(list(pts), fps_eff=30.0)
    b, _, _ = ball_mod.smooth_forecast(list(pts), fps_eff=30.0, bounce_reset=True)
    for p, q in zip(a, b):
        assert (p is None) == (q is None)
        if p is not None:
            assert np.allclose(p, q), "reset fired on a purely rising track"
