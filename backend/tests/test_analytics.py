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


def test_stats_exclude_low_confidence_calls_and_speeds():
    """Low-camera reality: far-court bounces are perspective-amplified noise. Their
    in/out verdict must NOT inflate the headline score (it goes to `uncertain`) and
    their speed must NOT enter the avg/top speed."""
    from swingvision import schema

    def mk(i, call, call_conf, speed, speed_conf):
        return schema.Shot(
            id=i, rally_id=0, player="A", type="forehand", t_hit_s=float(i),
            speed_kmh=speed, hit_xy=[1.0, 1.0], bounce_xy=[2.0, 2.0],
            bounce_t_s=float(i) + 0.5, is_in=(call == "in"), call=call,
            call_confident=call_conf, speed_confident=speed_conf)

    shots = [
        mk(0, "in", True, 100.0, True),
        mk(1, "out", True, 80.0, True),
        mk(2, "in", False, 200.0, False),    # far court: uncertain call, noisy speed
        mk(3, "out", False, 50.0, False),
    ]
    rally = schema.Rally(id=0, start_s=0.0, end_s=4.0, shot_ids=[0, 1, 2, 3], winner="A")
    st = schema.compute_stats(shots, [rally])

    assert st.line_calls == {"in": 1, "out": 1, "uncertain": 2}
    assert st.avg_speed_kmh == 90.0     # mean of the two confident speeds (100, 80)
    assert st.top_speed_kmh == 100.0    # 200 km/h noise excluded
