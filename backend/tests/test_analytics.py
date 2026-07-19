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


# --- Serve placement (geometry) --------------------------------------------
# Left box spans x in [1.37, 5.485]; right box [5.485, 9.60]. Bands are 0.7 m.
T = analytics.SERVE_T_BAND_M       # 0.7
W = analytics.SERVE_WIDE_BAND_M    # 0.7
XC = court.X_CENTER                # 5.485
XLS = court.X_LEFT_SINGLES         # 1.37
XRS = court.X_RIGHT_SINGLES        # 9.60
YFAR = (court.NET_Y + court.Y_FAR_SERVICE) / 2    # inside the far box
YNEAR = (court.Y_NEAR_SERVICE + court.NET_Y) / 2  # inside the near box


def test_serve_band_left_box_edges():
    # Near server serving into the far LEFT box (deuce court).
    # T edge: exactly 0.7 m from the centre line is still T (inclusive).
    assert analytics.serve_placement((XC - T, YFAR), "near") == ("deuce", "T")
    # Just outside the T band -> body.
    assert analytics.serve_placement((XC - T - 0.02, YFAR), "near") == ("deuce", "body")
    # Wide edge: exactly 0.7 m from the singles sideline is wide (inclusive).
    assert analytics.serve_placement((XLS + W, YFAR), "near") == ("deuce", "wide")
    # Just inside of the wide band -> body.
    assert analytics.serve_placement((XLS + W + 0.02, YFAR), "near") == ("deuce", "body")
    # Dead centre of the box is body.
    assert analytics.serve_placement(((XLS + XC) / 2, YFAR), "near") == ("deuce", "body")


def test_serve_band_right_box_edges():
    # Near server serving into the far RIGHT box (ad court).
    assert analytics.serve_placement((XC + T, YFAR), "near") == ("ad", "T")
    assert analytics.serve_placement((XC + T + 0.02, YFAR), "near") == ("ad", "body")
    assert analytics.serve_placement((XRS - W, YFAR), "near") == ("ad", "wide")
    assert analytics.serve_placement((XRS - W - 0.02, YFAR), "near") == ("ad", "body")


def test_serve_deuce_ad_depends_on_server_end():
    # A bounce in the LEFT box is deuce for the near server, ad for the far server
    # (a serve is struck cross-court, so the same box means opposite courts).
    left = (XLS + 0.9, YFAR)
    right = (XRS - 0.9, YNEAR)
    assert analytics.serve_placement(left, "near")[0] == "deuce"
    assert analytics.serve_placement(left, "far")[0] == "ad"
    assert analytics.serve_placement(right, "near")[0] == "ad"
    assert analytics.serve_placement(right, "far")[0] == "deuce"


def test_serve_on_centre_line_is_T():
    assert analytics.serve_placement((XC, YFAR), "near")[1] == "T"


def test_serve_placement_bad_end():
    try:
        analytics.serve_placement((XC, YFAR), "middle")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown server_end")
