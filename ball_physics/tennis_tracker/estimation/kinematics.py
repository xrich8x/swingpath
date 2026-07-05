"""Helpers to construct and interpret spin, and to summarise estimator output.

Spin sign convention (travel mostly along +x, z up), validated against the
simulator:
    topspin  -> omega about the horizontal axis perpendicular to travel,
                pointing +y for +x travel. Magnus pushes the ball DOWN
                (dips, lands shorter).
    backspin -> the opposite sign (floats, lands longer).
    sidespin -> omega about the vertical (z) axis (curves left/right).
    rifle    -> omega about the travel axis (gyro spin; little aero effect).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..physics.constants import rad_s_to_rpm

_RPM2RAD = 2.0 * np.pi / 60.0


def _frame(travel_dir: np.ndarray | None):
    """Return (top_axis, side_axis=up, rifle_axis) for a horizontal travel dir."""
    travel = np.array([1.0, 0.0, 0.0]) if travel_dir is None else np.asarray(travel_dir, float)
    travel = np.array([travel[0], travel[1], 0.0])
    travel /= max(np.linalg.norm(travel), 1e-9)
    up = np.array([0.0, 0.0, 1.0])
    top_axis = np.cross(up, travel)            # horizontal, perp to travel (+y for +x)
    top_axis /= max(np.linalg.norm(top_axis), 1e-9)
    return top_axis, up, travel


def spin_vector(topspin_rpm: float = 0.0, sidespin_rpm: float = 0.0,
                rifle_rpm: float = 0.0, travel_dir: np.ndarray | None = None) -> np.ndarray:
    """Compose a spin vector (rad/s) from intuitive components."""
    top_axis, up, rifle_axis = _frame(travel_dir)
    return (topspin_rpm * top_axis + sidespin_rpm * up + rifle_rpm * rifle_axis) * _RPM2RAD


@dataclass
class MotionReadout:
    speed_mps: float
    speed_kmh: float
    spin_rpm: float
    spin_axis: np.ndarray
    topspin_rpm: float       # signed: + topspin, - backspin
    sidespin_rpm: float      # signed
    launch_deg: float        # vertical launch angle


def summarize(v0: np.ndarray, omega: np.ndarray) -> MotionReadout:
    """Turn raw initial velocity + spin vector into human-readable metrics."""
    v0 = np.asarray(v0, float)
    omega = np.asarray(omega, float)
    speed = float(np.linalg.norm(v0))
    top_axis, up, _ = _frame(v0)
    horiz = float(np.linalg.norm(v0[:2]))
    omega_mag = float(np.linalg.norm(omega))
    return MotionReadout(
        speed_mps=speed,
        speed_kmh=speed * 3.6,
        spin_rpm=rad_s_to_rpm(omega_mag),
        spin_axis=(omega / omega_mag) if omega_mag > 1e-9 else np.zeros(3),
        topspin_rpm=rad_s_to_rpm(float(np.dot(omega, top_axis))),
        sidespin_rpm=rad_s_to_rpm(float(np.dot(omega, up))),
        launch_deg=float(np.degrees(np.arctan2(v0[2], horiz))),
    )
