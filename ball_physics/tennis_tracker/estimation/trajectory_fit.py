"""Recover initial velocity and spin by inverting the flight model.

Given observed ball positions over one flight arc (either metric 3D points, or
2D pixel tracks plus a calibrated camera), we search for the launch state
(p0, v0, omega) whose simulated trajectory best matches the observations, in a
least-squares sense. The Magnus term makes the trajectory curve as a function
of spin, so spin is identifiable from the *shape* of the arc.

This is the interpretable, no-training estimator. For noisy monocular 2D input
the depth direction is weakly constrained; warm-start it with `spin_net` and/or
fix p0 from a homography-lifted contact point. A differentiable PyTorch version
(autograd through an RK4 unroll) is straightforward to build from
`simulator_torch.py` for end-to-end / batched fitting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import least_squares

from ..physics import simulate
from ..physics.aerodynamics import DragModel, LiftModel
from ..data.camera import Camera
from .kinematics import summarize, MotionReadout


@dataclass
class FitResult:
    p0: np.ndarray
    v0: np.ndarray
    omega: np.ndarray
    success: bool
    rmse: float                # residual RMSE (m if fit to 3D, px if fit to 2D)
    readout: MotionReadout


def _forward(p0, v0, omega, times, drag, lift, t_pad=0.05):
    tr = simulate(p0, v0, omega, dt=2e-3, t_max=float(times[-1]) + t_pad,
                  drag=drag, lift=lift, bounces=0)
    return tr.sample(times)


def fit_arc(
    times: np.ndarray,
    obs: np.ndarray,
    *,
    camera: Optional[Camera] = None,
    p0_init: Optional[np.ndarray] = None,
    v0_init: Optional[np.ndarray] = None,
    omega_init: Optional[np.ndarray] = None,
    fix_p0: bool = False,
    drag: Optional[DragModel] = None,
    lift: Optional[LiftModel] = None,
    physical_bounds: bool = False,
    anchor: Optional[tuple] = None,
    spin_free: bool = True,
) -> FitResult:
    """Fit (p0, v0, omega) to one arc.

    Args:
        times: (N,) observation times (s), starting near 0.
        obs:   (N,3) metric positions, OR (N,2) pixels if `camera` is given.
               NaN rows are ignored.
        fix_p0: hold p0 at its initial value (use when the launch/contact point
               is known from a homography lift).
        physical_bounds: constrain v0 / omega / p0 to physically plausible ranges.
               Essential for noisy monocular 2D — without it the depth ambiguity
               lets the optimiser wander to absurd speeds.
        spin_free: when False, omega is held at zero. Spin is the softest
               parameter in the model — over a short arc the optimiser buys a
               cheap residual reduction by pinning all three components at their
               bound (|omega| = 750*sqrt(3) rad/s = 12,405 rpm, which is exactly
               what real arcs kept reporting). Fitting spin-free first and only
               accepting spin when it clearly earns its residual is how the
               caller tells a measured curve from an excuse.
    """
    drag = drag or DragModel()
    lift = lift or LiftModel()
    times = np.asarray(times, float)
    obs = np.asarray(obs, float)
    use_2d = camera is not None and obs.shape[1] == 2
    valid = np.isfinite(obs).all(axis=1)

    # --- initial guess ---
    if use_2d:
        # back-project first valid pixel onto a guessed depth; rough but ok to start
        if p0_init is None:
            p0_init = np.array([0.0, 0.0, 0.8])
    else:
        if p0_init is None:
            p0_init = obs[valid][0].copy()
    if v0_init is None:
        if not use_2d and valid.sum() >= 2:
            idx = np.where(valid)[0][:2]
            v0_init = (obs[idx[1]] - obs[idx[0]]) / max(times[idx[1]] - times[idx[0]], 1e-3)
        else:
            v0_init = np.array([30.0, 0.0, 4.0])
    if omega_init is None:
        omega_init = np.zeros(3)

    def pack(p0, v0, omega):
        return v0.tolist() + omega.tolist() if fix_p0 else p0.tolist() + v0.tolist() + omega.tolist()

    def unpack(x):
        if fix_p0:
            return np.asarray(p0_init, float), np.array(x[0:3]), np.array(x[3:6])
        return np.array(x[0:3]), np.array(x[3:6]), np.array(x[6:9])

    def residuals(x):
        p0, v0, omega = unpack(x)
        pred3d = _forward(p0, v0, omega, times, drag, lift)
        if use_2d:
            pred = camera.project(pred3d)
        else:
            pred = pred3d
        r = (pred - obs)[valid]
        r = np.nan_to_num(r, nan=0.0).reshape(-1)
        if anchor is not None:
            # Soft-pin one trajectory point (e.g. a bounce) to a known 3D location.
            # Works with forward physics (drag isn't time-reversible, so a hard
            # end-anchor via reversal would be unphysical). anchor = (idx, xyz, w).
            idx, xyz, w = anchor
            r = np.concatenate([r, w * (pred3d[idx] - np.asarray(xyz, float))])
        return r

    x0 = np.array(pack(np.asarray(p0_init, float), np.asarray(v0_init, float),
                       np.asarray(omega_init, float)))

    # Physical bounds keep the (ill-conditioned) monocular fit from diverging.
    bounds = (-np.inf, np.inf)
    if physical_bounds:
        v_lo, v_hi = [-75.0] * 3, [75.0] * 3            # m/s per component (~270 km/h)
        # rad/s (~7160 rpm). The no-spin cap is small but not zero: x0 is clipped
        # into the box by +-1e-6, so a tighter bound would invert it.
        w_cap = 750.0 if spin_free else 1e-3
        w_lo, w_hi = [-w_cap] * 3, [w_cap] * 3
        p_lo, p_hi = [-6.0, -12.0, 0.0], [30.0, 12.0, 6.0]   # m, on/over the court
        lo = (v_lo + w_lo) if fix_p0 else (p_lo + v_lo + w_lo)
        hi = (v_hi + w_hi) if fix_p0 else (p_hi + v_hi + w_hi)
        x0 = np.clip(x0, np.array(lo) + 1e-6, np.array(hi) - 1e-6)
        bounds = (np.array(lo), np.array(hi))

    res = least_squares(residuals, x0, method="trf", max_nfev=400, x_scale="jac",
                        bounds=bounds)
    p0, v0, omega = unpack(res.x)
    rmse = float(np.sqrt(np.mean(res.fun ** 2))) if res.fun.size else float("nan")
    return FitResult(p0, v0, omega, bool(res.success), rmse, summarize(v0, omega))
