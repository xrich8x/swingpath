"""Physical constants for tennis-ball flight.

All SI units. Coordinate convention used everywhere in this package:
    x : along the court length (net-to-baseline direction of travel)
    y : across the court width
    z : up (gravity acts in -z)

Values are ITF-typical. They are *defaults*: real systems should calibrate
the aerodynamic coefficients (CD, and the CL(spin) mapping) against measured
trajectories, because they vary with ball wear, pressure and air conditions.
"""
from __future__ import annotations

import numpy as np

# --- Ball ---
MASS = 0.057            # kg   (ITF: 56.0-59.4 g)
DIAMETER = 0.067        # m    (ITF: 6.54-6.86 cm)
RADIUS = DIAMETER / 2.0
AREA = np.pi * RADIUS ** 2          # m^2, reference (frontal) area

# --- Environment ---
AIR_DENSITY = 1.21      # kg/m^3  (~20 C, sea level)
GRAVITY = 9.81          # m/s^2
G_VEC = np.array([0.0, 0.0, -GRAVITY])

# --- Default aerodynamic coefficients ---
# Drag coefficient of a tennis ball is ~0.5-0.65 over normal play speeds.
CD_DEFAULT = 0.55

# Bounce (court-surface) defaults. Normal coefficient of restitution and a
# tangential friction coefficient. Hard court ~0.75; clay lower; grass lower.
COR_NORMAL = 0.75       # e_n
COR_TANGENT = 0.0       # tangential restitution (0 = no tangential "bounce-back")
FRICTION = 0.25         # mu, ball-court sliding friction

# Convenience: 0.5 * rho * A appears in both drag and lift.
HALF_RHO_A = 0.5 * AIR_DENSITY * AREA


def rpm_to_rad_s(rpm: float) -> float:
    return rpm * 2.0 * np.pi / 60.0


def rad_s_to_rpm(omega_mag: float) -> float:
    return omega_mag * 60.0 / (2.0 * np.pi)
