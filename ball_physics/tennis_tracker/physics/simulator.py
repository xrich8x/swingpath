"""Forward simulation of tennis-ball flight (NumPy, RK4).

Equations of motion (spin assumed constant during a flight arc, which is a
good approximation over the < 1 s arcs we care about):

    a = g  -  (HALF_RHO_A * CD * |v| / m) * v          # gravity + drag
           +  (HALF_RHO_A * CL * |v|^2 / m) * n_hat     # Magnus / lift
    n_hat = (omega x v) / |omega x v|

This module is the *foundation* of the whole framework: it generates the
synthetic training data, and it is the forward model the estimator inverts.
A differentiable PyTorch twin lives in `simulator_torch.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import constants as C
from .aerodynamics import DragModel, LiftModel


@dataclass
class Trajectory:
    t: np.ndarray            # (N,)   times (s)
    pos: np.ndarray          # (N, 3) positions (m)
    vel: np.ndarray          # (N, 3) velocities (m/s)
    bounce_indices: list = field(default_factory=list)  # indices where a bounce occurred

    def sample(self, times: np.ndarray) -> np.ndarray:
        """Linear-interpolate positions at arbitrary times (e.g. frame times)."""
        return np.stack([np.interp(times, self.t, self.pos[:, k]) for k in range(3)], axis=1)


def _accel(v: np.ndarray, omega: np.ndarray, drag: DragModel, lift: LiftModel) -> np.ndarray:
    speed = float(np.linalg.norm(v))
    if speed < 1e-9:
        return C.G_VEC.copy()
    omega_mag = float(np.linalg.norm(omega))

    # Drag: opposes velocity, ~ |v| v
    cd = drag(speed, omega_mag)
    a_drag = -(C.HALF_RHO_A * cd * speed / C.MASS) * v

    # Magnus: perpendicular to both spin and velocity, ~ |v|^2
    a_lift = np.zeros(3)
    if omega_mag > 1e-9:
        cross = np.cross(omega, v)
        cross_mag = float(np.linalg.norm(cross))
        if cross_mag > 1e-9:
            cl = lift(speed, omega_mag)
            a_lift = (C.HALF_RHO_A * cl * speed ** 2 / C.MASS) * (cross / cross_mag)

    return C.G_VEC + a_drag + a_lift


def _bounce(v: np.ndarray, omega: np.ndarray, *, e_n: float, e_t: float,
            mu: float, radius: float) -> tuple[np.ndarray, np.ndarray]:
    """Spin-aware impulse bounce off the z=0 plane.

    Slip-or-grip Coulomb friction model. Contact point (bottom of ball)
    horizontal velocity is v_horiz + omega x (-r z_hat). Friction acts to
    cancel that slip; if the required impulse exceeds mu * normal impulse the
    ball slides and friction is capped. Approximate but directionally correct:
    topspin kicks forward/low, backspin sits up/slow. Calibrate e_n, mu, e_t
    per surface.
    """
    vx, vy, vz = v
    # Normal impulse (per unit mass) magnitude
    Jn = (1.0 + e_n) * abs(vz)

    # Horizontal contact-point velocity (slip)
    # omega x (0,0,-r) = (-r*wy, r*wx, 0)
    slip = np.array([vx - radius * omega[1], vy + radius * omega[0]])
    slip_mag = float(np.linalg.norm(slip))

    v_out = v.copy()
    v_out[2] = -e_n * vz  # normal restitution

    omega_out = omega.copy()
    if slip_mag > 1e-9:
        # tangential impulse needed to bring slip to ~0 (grip), capped by friction
        Jt_needed = slip_mag / 3.5  # effective: accounts for ball moment of inertia coupling
        Jt = min(mu * Jn, Jt_needed)
        dir_slip = slip / slip_mag
        v_out[0] -= Jt * dir_slip[0]
        v_out[1] -= Jt * dir_slip[1]
        # friction torque changes spin (sign couples to slip direction)
        omega_out[0] += (Jt * dir_slip[1]) / radius * 0.4
        omega_out[1] -= (Jt * dir_slip[0]) / radius * 0.4
    # small tangential restitution
    v_out[0] *= (1.0 + e_t)
    v_out[1] *= (1.0 + e_t)
    return v_out, omega_out


def simulate(
    p0: np.ndarray,
    v0: np.ndarray,
    omega: np.ndarray,
    *,
    dt: float = 1e-3,
    t_max: float = 3.0,
    drag: Optional[DragModel] = None,
    lift: Optional[LiftModel] = None,
    bounces: int = 0,
    e_n: float = C.COR_NORMAL,
    e_t: float = C.COR_TANGENT,
    mu: float = C.FRICTION,
    stop_below_z: float = -0.5,
) -> Trajectory:
    """Integrate a flight from initial state with fixed-step RK4.

    Args:
        p0, v0: initial position (m) and velocity (m/s), shape (3,).
        omega:  spin vector (rad/s), shape (3,). Constant over the arc.
        bounces: how many ground bounces to simulate (0 = stop at first ground crossing).
    Returns a `Trajectory`.
    """
    drag = drag or DragModel()
    lift = lift or LiftModel()
    p = np.asarray(p0, float).copy()
    v = np.asarray(v0, float).copy()
    omega = np.asarray(omega, float).copy()

    ts, ps, vs = [0.0], [p.copy()], [v.copy()]
    bounce_idx = []
    n_steps = int(t_max / dt)
    remaining_bounces = bounces

    for i in range(n_steps):
        # RK4 on (p, v); omega constant
        k1v = _accel(v, omega, drag, lift)
        k1p = v
        k2v = _accel(v + 0.5 * dt * k1v, omega, drag, lift)
        k2p = v + 0.5 * dt * k1v
        k3v = _accel(v + 0.5 * dt * k2v, omega, drag, lift)
        k3p = v + 0.5 * dt * k2v
        k4v = _accel(v + dt * k3v, omega, drag, lift)
        k4p = v + dt * k3v

        p_next = p + (dt / 6.0) * (k1p + 2 * k2p + 2 * k3p + k4p)
        v_next = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        t_next = ts[-1] + dt

        # Ground crossing?
        if p[2] >= 0.0 and p_next[2] < 0.0:
            # linear interp to the z=0 instant
            frac = p[2] / (p[2] - p_next[2])
            p_hit = p + frac * (p_next - p)
            v_hit = v + frac * (v_next - v)
            ts.append(t_next - dt * (1 - frac)); ps.append(p_hit.copy()); vs.append(v_hit.copy())
            bounce_idx.append(len(ps) - 1)
            if remaining_bounces <= 0:
                break
            remaining_bounces -= 1
            v_hit, omega = _bounce(v_hit, omega, e_n=e_n, e_t=e_t, mu=mu, radius=C.RADIUS)
            p, v = p_hit.copy(), v_hit
            # nudge above ground to avoid re-trigger
            p[2] = max(p[2], 1e-4)
            continue

        p, v = p_next, v_next
        ts.append(t_next); ps.append(p.copy()); vs.append(v.copy())
        if p[2] < stop_below_z:
            break

    return Trajectory(np.array(ts), np.array(ps), np.array(vs), bounce_idx)
