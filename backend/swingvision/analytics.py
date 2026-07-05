"""analytics.py — shot speed and line calls (the geometry layer).

Both are closed-form on court-plane (metre) positions. There is no model here and
there shouldn't be: given the trajectory, speed is distance/time and a line call
is a point-in-polygon test. ML upstream produces the positions; the answers here
are exact (see CLAUDE.md).

  - Speed is *average* ball speed over the shot, which reads ~15-20% below a
    radar gun (radar catches the peak just off the racquet). That gap is
    expected — don't "fix" it.
"""

from __future__ import annotations

import math
from typing import Sequence

from . import court

MS_TO_KMH = 3.6


def speed_between(
    p0: Sequence[float], t0: float, p1: Sequence[float], t1: float
) -> float:
    """Average speed (km/h) of the straight segment p0->p1 over dt = t1 - t0."""
    dt = t1 - t0
    if dt <= 0:
        raise ValueError("t1 must be after t0")
    dist = math.dist(p0, p1)
    return (dist / dt) * MS_TO_KMH


def shot_speed_kmh(track: Sequence[Sequence[float]]) -> float:
    """Average ball speed (km/h) along a trajectory.

    `track` is a sequence of (t_s, x_m, y_m). Speed is total path length divided
    by total elapsed time — the honest average over the shot, not the peak.
    """
    pts = [tuple(p) for p in track]
    if len(pts) < 2:
        return 0.0
    total_dist = 0.0
    for (t0, x0, y0), (t1, x1, y1) in zip(pts, pts[1:]):
        total_dist += math.dist((x0, y0), (x1, y1))
    total_time = pts[-1][0] - pts[0][0]
    if total_time <= 0:
        return 0.0
    return (total_dist / total_time) * MS_TO_KMH


def _in_service_region(x: float, y: float, margin: float) -> bool:
    """Inside either service box (both halves) — used for serve calls.

    A serve must land in the diagonally opposite service box; analytics here
    only checks the ball landed in *a* service region. The pipeline picks which
    box based on who served and the deuce/ad side.
    """
    within_width = court.X_LEFT_SINGLES - margin <= x <= court.X_RIGHT_SINGLES + margin
    near_box = court.Y_NEAR_SERVICE - margin <= y <= court.NET_Y + margin
    far_box = court.NET_Y - margin <= y <= court.Y_FAR_SERVICE + margin
    return within_width and (near_box or far_box)


def is_in(
    bounce_xy: Sequence[float],
    shot_type: str = "forehand",
    singles: bool = True,
    margin: float = 0.0,
) -> bool:
    """Did the bounce land in?

    - serve: inside a service box
    - everything else: inside the singles court (or doubles if singles=False)

    `margin` (metres) widens the boundary — use a small value to model the ball's
    radius / line width if you want the benefit of the doubt on the line.
    """
    x, y = bounce_xy
    if shot_type == "serve":
        return _in_service_region(x, y, margin)
    if singles:
        return court.is_in_singles(x, y, margin)
    return court.is_in_doubles(x, y, margin)


def line_call(
    bounce_xy: Sequence[float],
    shot_type: str = "forehand",
    singles: bool = True,
    margin: float = 0.0,
) -> str:
    """'in' or 'out' for a bounce. The string the schema's `call` field stores."""
    return "in" if is_in(bounce_xy, shot_type, singles, margin) else "out"
