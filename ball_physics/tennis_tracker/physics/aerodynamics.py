"""Aerodynamic coefficient models for a spinning tennis ball.

The lift (Magnus) coefficient depends on the dimensionless *spin ratio*
    S = r * |omega| / |v|
i.e. the ratio of the ball's surface speed to its translational speed.

Default CL(S) uses the Stepanek-style relation
    CL = S / (2 S + 1)
which is monotonic, smooth, ->0 as S->0 and saturates near 0.5 for large S.
That range (~0-0.3 for typical play) matches published tennis measurements.
Swap in a calibrated curve via `LiftModel` when you have ground-truth spin.

References: Stepanek (1988); Cross, "Trajectory of a Spinning Tennis Ball".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import CD_DEFAULT, RADIUS


def spin_ratio(speed: float, omega_mag: float, radius: float = RADIUS) -> float:
    """S = r|omega| / |v|. Guarded against |v| -> 0."""
    return radius * omega_mag / max(speed, 1e-9)


@dataclass
class DragModel:
    """Drag coefficient. Constant by default; subclass/replace for speed- or
    spin-dependent CD if you calibrate one."""
    cd: float = CD_DEFAULT

    def __call__(self, speed: float, omega_mag: float) -> float:
        return self.cd


@dataclass
class LiftModel:
    """Magnus lift coefficient CL as a function of spin ratio S.

    CL = cl_max * S / (sat * S + 1) ; defaults reproduce CL = S/(2S+1).
    """
    cl_max: float = 1.0
    sat: float = 2.0

    def __call__(self, speed: float, omega_mag: float) -> float:
        s = spin_ratio(speed, omega_mag)
        return self.cl_max * s / (self.sat * s + 1.0)
