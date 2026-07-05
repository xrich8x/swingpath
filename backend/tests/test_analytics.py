"""Shot speed and line calls (geometry)."""

import math

from swingvision import analytics, court


def test_speed_between():
    # 10 m in 1 s = 10 m/s = 36 km/h.
    assert math.isclose(analytics.speed_between((0, 0), 0.0, (10, 0), 1.0), 36.0)


def test_shot_speed_along_track():
    # Straight line, 20 m over 1 s = 72 km/h.
    track = [(0.0, 0.0, 0.0), (0.5, 10.0, 0.0), (1.0, 20.0, 0.0)]
    assert math.isclose(analytics.shot_speed_kmh(track), 72.0, rel_tol=1e-9)


def test_shot_speed_degenerate():
    assert analytics.shot_speed_kmh([(0.0, 1.0, 1.0)]) == 0.0


def test_line_call_groundstroke():
    assert analytics.line_call((5.0, 12.0), "forehand") == "in"
    assert analytics.line_call((5.0, 24.5), "forehand") == "out"   # long
    assert analytics.line_call((0.5, 12.0), "forehand") == "out"   # in the alley (singles)
    # Same wide ball is "in" for doubles.
    assert analytics.line_call((0.5, 12.0), "forehand", singles=False) == "in"


def test_line_call_serve():
    # Inside a service box.
    assert analytics.line_call((5.0, 14.0), "serve") == "in"
    # Past the service line (between service line and baseline) -> out for a serve.
    assert analytics.line_call((5.0, 20.0), "serve") == "out"


def test_speed_requires_forward_time():
    try:
        analytics.speed_between((0, 0), 1.0, (1, 0), 1.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-positive dt")
