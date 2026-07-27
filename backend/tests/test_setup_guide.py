"""Setup guidance: the framing check the Court Setup tool shows live.

Two questions, graded from measurements (never guessed): can the camera SEE the
court, and is its ANGLE good enough to actually measure the court. Synthetic
cameras only - no footage or weights - so the thresholds are deterministic.
"""

import math

import numpy as np
import pytest

pytest.importorskip("cv2")
pytest.importorskip("scipy")

import cv2  # noqa: E402

from swingvision import calibration as C  # noqa: E402
from swingvision import court, courtfit  # noqa: E402

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
W, H = 1280, 720


def _cam(Cz, f_px, back=8.0):
    """Homography for a centre-line camera `back` m behind the baseline at height Cz."""
    Cx, Cy = court.DOUBLES_WIDTH / 2.0, -back
    pitch = math.atan2(Cz, back + court.LENGTH * 0.5)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd = np.array([0.0, ct, -st]); right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, st, ct])
    img, wld = [], []
    for n in DBL:
        X, Y = court.LANDMARKS[n]
        d = np.array([X - Cx, Y - Cy, -Cz]); z = d @ fwd
        img.append([W / 2 + f_px * (d @ right) / z, H / 2 - f_px * (d @ up) / z])
        wld.append([X, Y])
    return C.compute_homography(wld, img), {n: img[i] for i, n in enumerate(DBL)}


def _draw(Hm):
    frame = np.full((H, W, 3), (60, 120, 70), np.uint8)
    for a, b in court.LINES:
        p = C.court_to_image(Hm, [a])[0]; q = C.court_to_image(Hm, [b])[0]
        cv2.line(frame, tuple(np.round(p).astype(int)), tuple(np.round(q).astype(int)),
                 (245, 245, 245), 3, cv2.LINE_AA)
    return frame


def _f(hfov_deg):
    return W / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))


def test_reliable_span_grows_with_camera_height():
    """The measured reliable span is what makes 'mount it higher' a fact, not an
    opinion: a higher camera resolves more court depth."""
    spans = []
    for cz in (1.5, 3.0, 6.0):
        Hm, _ = _cam(cz, _f(74))
        frac, until = C.reliable_court_span(Hm)
        spans.append(until)
    assert spans[0] < spans[1] < spans[2], spans


def test_reliable_span_shrinks_on_a_wider_lens():
    """At a fixed height, 'seeing more court' by going wider costs resolution."""
    _, until_tight = C.reliable_court_span(_cam(2.5, _f(60))[0])
    _, until_wide = C.reliable_court_span(_cam(2.5, _f(110))[0])
    assert until_wide < until_tight


def test_low_camera_is_graded_poor_and_says_why():
    Hm, corners = _cam(1.4, _f(90))
    v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
    assert v["angle"]["level"] == "poor"
    assert v["angle"]["height_m"] < 2.0
    assert "%" in v["angle"]["msg"]          # quantified, not vague


def test_good_camera_is_graded_good():
    Hm, corners = _cam(7.0, _f(60))
    v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
    assert v["angle"]["level"] == "good"
    assert v["angle"]["reliable_frac"] > 0.5


def test_never_claims_far_half_when_span_stops_short_of_the_net():
    """The honesty guard: only claim the far half when the span really passes the
    net. (An earlier draft said 'including the far half' at an 8.8 m reach.)"""
    for cz in (1.2, 1.6, 2.0, 2.6, 3.4, 5.0, 8.0):
        Hm, corners = _cam(cz, _f(80))
        v = courtfit.setup_verdict(_draw(Hm), corners, C, court)
        _frac, until = C.reliable_court_span(Hm)
        msg = v["angle"]["msg"]
        if until < court.NET_Y:
            # states the shortfall as fact, never claims coverage it doesn't have,
            # and is never graded "good" (advice like "...extends it past the net"
            # is fine - that's a fix, not a claim)
            assert "short of the net" in msg
            assert "Both service boxes are covered" not in msg
            assert v["angle"]["level"] != "good"
        else:
            assert "past the net" in msg


def test_setup_gate_matches_the_analysis_gate():
    """The framing guide and the shot-confidence gate must use ONE definition of
    reliable, or the setup advice would contradict the resulting match.json."""
    assert C.RELIABLE_SCALE_M_PER_PX == 0.09
    Hm, _ = _cam(3.0, _f(70))
    p_near = C.court_to_image(Hm, [(court.DOUBLES_WIDTH / 2, 0.0)])[0]
    assert C.court_scale_m_per_px(Hm, p_near) <= C.RELIABLE_SCALE_M_PER_PX
