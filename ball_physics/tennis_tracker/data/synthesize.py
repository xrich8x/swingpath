"""Generate synthetic, physically-grounded labeled trajectories.

Real datasets give you 2D ball pixels but almost never spin or metric 3D.
So we generate (2D track, 3D track, initial velocity, spin) tuples from the
simulator and train the spin/3D estimator on them. This synthetic-to-real
recipe is what current monocular spin-estimation work relies on.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

from ..physics import simulate
from ..physics.aerodynamics import DragModel, LiftModel
from .camera import Camera, make_courtside_camera
from ..estimation.kinematics import spin_vector


@dataclass
class Sample:
    t: np.ndarray            # (N,) frame times (s)
    uv: np.ndarray           # (N,2) pixel coords (NaN where missing)
    pos3d: np.ndarray        # (N,3) ground-truth 3D (m)
    v0: np.ndarray           # (3,) initial velocity
    omega: np.ndarray        # (3,) spin (rad/s)
    p0: np.ndarray           # (3,) initial position
    bounce_t: list           # times of bounces within the window


def sample_shot(rng: np.random.Generator, cam: Camera, *, fps: float = 60.0,
                pixel_noise: float = 1.5, dropout: float = 0.1,
                drag: Optional[DragModel] = None, lift: Optional[LiftModel] = None) -> Sample:
    """Draw one random realistic groundstroke/serve and render it to 2D."""
    speed = rng.uniform(18.0, 55.0)                 # m/s (~65-198 km/h)
    launch = np.radians(rng.uniform(-5.0, 22.0))    # vertical angle
    azim = np.radians(rng.uniform(-8.0, 8.0))       # horizontal angle
    v0 = speed * np.array([np.cos(launch) * np.cos(azim),
                           np.cos(launch) * np.sin(azim),
                           np.sin(launch)])
    topspin = rng.uniform(-1500, 3500)              # signed: + topspin, - slice
    sidespin = rng.uniform(-1200, 1200)
    omega = spin_vector(topspin, sidespin, travel_dir=v0)
    p0 = np.array([rng.uniform(0.0, 2.0), rng.uniform(-3.0, 3.0), rng.uniform(0.3, 1.2)])

    tr = simulate(p0, v0, omega, bounces=1, drag=drag, lift=lift, t_max=3.0)
    if tr.t[-1] < 0.2:
        # degenerate (immediate ground); retry once with a flatter shot
        v0[2] = abs(v0[2]) + 2.0
        tr = simulate(p0, v0, omega, bounces=1, drag=drag, lift=lift, t_max=3.0)

    t_end = tr.t[-1]
    times = np.arange(0.0, t_end, 1.0 / fps)
    pos3d = tr.sample(times)
    uv = cam.project(pos3d)

    # keep only in-frame samples
    in_frame = (uv[:, 0] >= 0) & (uv[:, 0] < cam.width) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.height)
    in_frame &= ~np.isnan(uv).any(axis=1)
    times, pos3d, uv = times[in_frame], pos3d[in_frame], uv[in_frame]

    uv = uv + rng.normal(0, pixel_noise, uv.shape)
    if dropout > 0:
        miss = rng.random(len(uv)) < dropout
        uv[miss] = np.nan

    bounce_t = [float(tr.t[i]) for i in tr.bounce_indices if tr.t[i] <= t_end]
    return Sample(times, uv, pos3d, v0, omega, p0, bounce_t)


def build_dataset(n: int, out_path: str, *, seed: int = 0, fps: float = 60.0,
                  min_len: int = 8, **cam_kwargs) -> int:
    """Generate `n` samples and save to a compressed .npz (ragged -> object arrays).

    Returns the number of usable samples written.
    """
    rng = np.random.default_rng(seed)
    cam = make_courtside_camera(**cam_kwargs)
    recs = []
    while len(recs) < n:
        s = sample_shot(rng, cam, fps=fps)
        valid = np.isfinite(s.uv).all(axis=1).sum()
        if valid >= min_len:
            recs.append(s)
    np.savez_compressed(
        out_path,
        t=np.array([r.t for r in recs], dtype=object),
        uv=np.array([r.uv for r in recs], dtype=object),
        pos3d=np.array([r.pos3d for r in recs], dtype=object),
        v0=np.stack([r.v0 for r in recs]),
        omega=np.stack([r.omega for r in recs]),
        p0=np.stack([r.p0 for r in recs]),
        K=cam.K, R=cam.R, t_cam=cam.t,
    )
    return len(recs)
