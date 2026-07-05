"""Differentiable flight simulator (PyTorch), batched.

A faithful twin of `physics/simulator.py` (flight only; the bounce is handled
separately because it is near-discontinuous). Because the RK4 unroll is built
from differentiable ops, gradients flow from a trajectory/reprojection loss back
to (p0, v0, omega). Uses:

  * end-to-end / batched trajectory fitting (an autograd alternative to the
    scipy least-squares fit in `estimation/trajectory_fit.py`), and
  * physics-informed losses when training `spin_net`.

Keep the constants here in sync with `physics/constants.py`.
"""
from __future__ import annotations

import math

try:
    import torch
except Exception as e:  # pragma: no cover
    raise ImportError("simulator_torch requires PyTorch. `pip install torch`.") from e

# --- constants (mirror physics/constants.py) ---
MASS = 0.057
RADIUS = 0.0335
AREA = math.pi * RADIUS ** 2
AIR_DENSITY = 1.21
GRAVITY = 9.81
HALF_RHO_A = 0.5 * AIR_DENSITY * AREA
CD_DEFAULT = 0.55
CL_MAX = 1.0
CL_SAT = 2.0


def _accel(v, omega, cd, cl_max, cl_sat):
    """Batched acceleration. v,omega: (B,3). Returns (B,3)."""
    speed = torch.linalg.norm(v, dim=-1, keepdim=True).clamp_min(1e-9)   # (B,1)
    omega_mag = torch.linalg.norm(omega, dim=-1, keepdim=True)           # (B,1)

    a_grav = torch.zeros_like(v)
    a_grav[..., 2] = -GRAVITY

    a_drag = -(HALF_RHO_A * cd * speed / MASS) * v

    cross = torch.linalg.cross(omega, v, dim=-1)                         # (B,3)
    cross_mag = torch.linalg.norm(cross, dim=-1, keepdim=True)
    s = RADIUS * omega_mag / speed                                       # spin ratio
    cl = cl_max * s / (cl_sat * s + 1.0)
    # guard against div-by-zero where omega or cross is ~0
    safe = (cross_mag > 1e-9).float()
    a_lift = safe * (HALF_RHO_A * cl * speed ** 2 / MASS) * (cross / cross_mag.clamp_min(1e-9))

    return a_grav + a_drag + a_lift


def simulate_batch(p0, v0, omega, *, n_steps=900, dt=2e-3,
                   cd=CD_DEFAULT, cl_max=CL_MAX, cl_sat=CL_SAT):
    """Integrate B flights for n_steps. Returns (pos, vel, t).

    p0,v0,omega: (B,3) tensors. pos,vel: (B,n_steps+1,3); t: (n_steps+1,).
    """
    p, v = p0, v0
    ps, vs = [p], [v]
    for _ in range(n_steps):
        k1v = _accel(v, omega, cd, cl_max, cl_sat); k1p = v
        k2v = _accel(v + 0.5 * dt * k1v, omega, cd, cl_max, cl_sat); k2p = v + 0.5 * dt * k1v
        k3v = _accel(v + 0.5 * dt * k2v, omega, cd, cl_max, cl_sat); k3p = v + 0.5 * dt * k2v
        k4v = _accel(v + dt * k3v, omega, cd, cl_max, cl_sat); k4p = v + dt * k3v
        p = p + (dt / 6.0) * (k1p + 2 * k2p + 2 * k3p + k4p)
        v = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        ps.append(p); vs.append(v)
    pos = torch.stack(ps, dim=1)
    vel = torch.stack(vs, dim=1)
    t = torch.arange(n_steps + 1, device=p0.device, dtype=p0.dtype) * dt
    return pos, vel, t


def sample_at(pos, t_grid, query_t):
    """Differentiable linear interpolation of pos (B,S,3) at query times.

    t_grid: (S,) increasing. query_t: (B,Q) or (Q,). Returns (B,Q,3).
    """
    if query_t.dim() == 1:
        query_t = query_t.unsqueeze(0).expand(pos.shape[0], -1)
    S = t_grid.shape[0]
    dt = (t_grid[1] - t_grid[0]).clamp_min(1e-9)
    idx = torch.clamp((query_t / dt).floor().long(), 0, S - 2)          # (B,Q)
    t0 = torch.gather(t_grid.expand(pos.shape[0], -1), 1, idx)
    frac = ((query_t - t0) / dt).unsqueeze(-1).clamp(0, 1)              # (B,Q,1)
    g0 = torch.gather(pos, 1, idx.unsqueeze(-1).expand(-1, -1, 3))
    g1 = torch.gather(pos, 1, (idx + 1).unsqueeze(-1).expand(-1, -1, 3))
    return g0 * (1 - frac) + g1 * frac


def project_batch(pos, K, R, t):
    """Project (B,Q,3) world points to (B,Q,2) pixels with one shared camera.

    K:(3,3), R:(3,3), t:(3,). Differentiable.
    """
    B, Q, _ = pos.shape
    pc = pos @ R.T + t                                                  # (B,Q,3)
    uvw = pc @ K.T
    return uvw[..., :2] / uvw[..., 2:3].clamp_min(1e-6)
