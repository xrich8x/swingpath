"""Lift 2D ball pixels to metric 3D.

Two regimes:
  * Points on the court plane (bounce contacts) -> exact via homography.
  * Airborne arcs -> underdetermined from one view; we recover them by fitting
    the physics model in image space (reprojection), optionally anchoring the
    start at a homography-lifted contact point.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..data.camera import Camera
from ..estimation.trajectory_fit import fit_arc, FitResult
from .court import image_to_ground


@dataclass
class LiftedArc:
    pos3d: np.ndarray        # (N,3) reconstructed 3D at the given times
    fit: FitResult


def lift_contact(uv: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Exact 3D of a ball touching the court (z=0) via the court homography."""
    return image_to_ground(uv, H)


def lift_arc(times: np.ndarray, uv: np.ndarray, camera: Camera, *,
             anchor_uv: Optional[np.ndarray] = None, H: Optional[np.ndarray] = None,
             v0_init: Optional[np.ndarray] = None,
             omega_init: Optional[np.ndarray] = None) -> LiftedArc:
    """Reconstruct a 3D airborne arc from a 2D track + calibrated camera.

    If `anchor_uv` and `H` are given, the arc's start position is fixed to the
    homography lift of that contact pixel (greatly stabilises the depth).
    """
    p0_init = None
    fix_p0 = False
    if anchor_uv is not None and H is not None:
        p0_init = lift_contact(anchor_uv, H)[0]
        fix_p0 = True
    fit = fit_arc(times, uv, camera=camera, p0_init=p0_init, fix_p0=fix_p0,
                  v0_init=v0_init, omega_init=omega_init)
    from ..physics import simulate
    tr = simulate(fit.p0, fit.v0, fit.omega, dt=2e-3, t_max=float(times[-1]) + 0.05, bounces=0)
    return LiftedArc(tr.sample(np.asarray(times, float)), fit)
