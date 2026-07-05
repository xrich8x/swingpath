"""Court constants and landmark geometry (the geometry layer).

A regulation tennis court, all dimensions in metres. The coordinate system is a
top-down, right-handed plane:

    x: 0 .. WIDTH   left doubles sideline -> right doubles sideline
    y: 0 .. LENGTH  near baseline -> far baseline
    net at y = LENGTH / 2

These are *real-world* coordinates. The homography maps between this plane and
image pixels. Court constants here are mirrored in frontend/src/lib/court.js;
keep the two in sync (see CLAUDE.md).
"""

from __future__ import annotations

# --- Regulation dimensions (metres) -----------------------------------------
LENGTH = 23.77          # baseline to baseline
DOUBLES_WIDTH = 10.97   # doubles sideline to doubles sideline
SINGLES_WIDTH = 8.23    # singles sideline to singles sideline
ALLEY = (DOUBLES_WIDTH - SINGLES_WIDTH) / 2.0   # 1.37, each doubles alley
SERVICE_LINE_FROM_NET = 6.40                    # net to service line
NET_Y = LENGTH / 2.0                            # 11.885

# Derived x positions of the four vertical lines (left -> right).
X_LEFT_DOUBLES = 0.0
X_LEFT_SINGLES = ALLEY                          # 1.37
X_CENTER = DOUBLES_WIDTH / 2.0                  # 5.485
X_RIGHT_SINGLES = DOUBLES_WIDTH - ALLEY         # 9.60
X_RIGHT_DOUBLES = DOUBLES_WIDTH                 # 10.97

# Derived y positions of the horizontal lines (near -> far).
Y_NEAR_BASELINE = 0.0
Y_NEAR_SERVICE = NET_Y - SERVICE_LINE_FROM_NET  # 5.485
Y_FAR_SERVICE = NET_Y + SERVICE_LINE_FROM_NET   # 18.285
Y_FAR_BASELINE = LENGTH                         # 23.77

# --- Named landmarks --------------------------------------------------------
# 14 intersections a homography solve / keypoint model can anchor on. Names are
# the contract: calibration JSON and detect_court_keypoints() use these keys.
LANDMARKS: dict[str, tuple[float, float]] = {
    # Doubles corners
    "near_bl_doubles": (X_LEFT_DOUBLES, Y_NEAR_BASELINE),
    "near_br_doubles": (X_RIGHT_DOUBLES, Y_NEAR_BASELINE),
    "far_bl_doubles": (X_LEFT_DOUBLES, Y_FAR_BASELINE),
    "far_br_doubles": (X_RIGHT_DOUBLES, Y_FAR_BASELINE),
    # Singles sideline meets baseline
    "near_bl_singles": (X_LEFT_SINGLES, Y_NEAR_BASELINE),
    "near_br_singles": (X_RIGHT_SINGLES, Y_NEAR_BASELINE),
    "far_bl_singles": (X_LEFT_SINGLES, Y_FAR_BASELINE),
    "far_br_singles": (X_RIGHT_SINGLES, Y_FAR_BASELINE),
    # Service line meets singles sideline
    "near_sl_left": (X_LEFT_SINGLES, Y_NEAR_SERVICE),
    "near_sl_right": (X_RIGHT_SINGLES, Y_NEAR_SERVICE),
    "far_sl_left": (X_LEFT_SINGLES, Y_FAR_SERVICE),
    "far_sl_right": (X_RIGHT_SINGLES, Y_FAR_SERVICE),
    # Center service line meets service line (the "T")
    "near_t": (X_CENTER, Y_NEAR_SERVICE),
    "far_t": (X_CENTER, Y_FAR_SERVICE),
}

# --- Line segments for drawing the full court -------------------------------
# Each segment is (start_xy, end_xy) in court metres. overlay.py / the frontend
# project these to pixels with court_to_image to draw the line set.
LINES: list[tuple[tuple[float, float], tuple[float, float]]] = [
    # Baselines
    ((X_LEFT_DOUBLES, Y_NEAR_BASELINE), (X_RIGHT_DOUBLES, Y_NEAR_BASELINE)),
    ((X_LEFT_DOUBLES, Y_FAR_BASELINE), (X_RIGHT_DOUBLES, Y_FAR_BASELINE)),
    # Doubles sidelines
    ((X_LEFT_DOUBLES, Y_NEAR_BASELINE), (X_LEFT_DOUBLES, Y_FAR_BASELINE)),
    ((X_RIGHT_DOUBLES, Y_NEAR_BASELINE), (X_RIGHT_DOUBLES, Y_FAR_BASELINE)),
    # Singles sidelines
    ((X_LEFT_SINGLES, Y_NEAR_BASELINE), (X_LEFT_SINGLES, Y_FAR_BASELINE)),
    ((X_RIGHT_SINGLES, Y_NEAR_BASELINE), (X_RIGHT_SINGLES, Y_FAR_BASELINE)),
    # Service lines
    ((X_LEFT_SINGLES, Y_NEAR_SERVICE), (X_RIGHT_SINGLES, Y_NEAR_SERVICE)),
    ((X_LEFT_SINGLES, Y_FAR_SERVICE), (X_RIGHT_SINGLES, Y_FAR_SERVICE)),
    # Center service line
    ((X_CENTER, Y_NEAR_SERVICE), (X_CENTER, Y_FAR_SERVICE)),
    # Net
    ((X_LEFT_DOUBLES, NET_Y), (X_RIGHT_DOUBLES, NET_Y)),
]


def landmark_names() -> list[str]:
    """Stable ordering of landmark names (dict order is insertion order)."""
    return list(LANDMARKS.keys())


def is_in_singles(x: float, y: float, margin: float = 0.0) -> bool:
    """True if (x, y) lies within the singles court, with an optional margin
    (metres) added to every boundary. Used by the line-call geometry."""
    return (
        X_LEFT_SINGLES - margin <= x <= X_RIGHT_SINGLES + margin
        and Y_NEAR_BASELINE - margin <= y <= Y_FAR_BASELINE + margin
    )


def is_in_doubles(x: float, y: float, margin: float = 0.0) -> bool:
    """True if (x, y) lies within the doubles court, with an optional margin."""
    return (
        X_LEFT_DOUBLES - margin <= x <= X_RIGHT_DOUBLES + margin
        and Y_NEAR_BASELINE - margin <= y <= Y_FAR_BASELINE + margin
    )


def near_half(y: float) -> bool:
    """True if y is on the near side of the net."""
    return y < NET_Y
