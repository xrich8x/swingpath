"""Assemble per-frame detections into smooth trajectories and find bounces.

Input: one (or few) candidate ball pixels per frame from the detector.
Output: a gap-filled, smoothed pixel track, plus bounce frame indices and the
flight-arc segments between them (each arc is what the estimator consumes).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def link_detections(per_frame: list[np.ndarray | None], gate_px: float = 80.0) -> np.ndarray:
    """Greedy nearest-neighbour link of one detection per frame.

    `per_frame[i]` is an (M,2) array of candidate pixels (or None/empty).
    Returns (T,2) track with NaN where no detection was linked.
    """
    T = len(per_frame)
    track = np.full((T, 2), np.nan)
    last = None
    for i, dets in enumerate(per_frame):
        if dets is None or len(dets) == 0:
            continue
        dets = np.atleast_2d(dets)
        if last is None:
            pick = dets[0]
        else:
            d = np.linalg.norm(dets - last, axis=1)
            j = int(np.argmin(d))
            pick = dets[j] if d[j] <= gate_px else dets[0]
        track[i] = pick
        last = pick
    return track


def fill_gaps(track: np.ndarray, max_gap: int = 5) -> np.ndarray:
    """Linearly interpolate NaN runs no longer than `max_gap` frames."""
    out = track.copy()
    n = len(track)
    valid = np.where(np.isfinite(track).all(axis=1))[0]
    for a, b in zip(valid[:-1], valid[1:]):
        if 1 < b - a <= max_gap + 1:
            for k in range(2):
                out[a:b + 1, k] = np.linspace(track[a, k], track[b, k], b - a + 1)
    return out


@dataclass
class Smoothed:
    pos: np.ndarray          # (T,2)
    vel: np.ndarray          # (T,2) px/frame


class KalmanSmoother:
    """Constant-acceleration Kalman filter + RTS smoother in 2D pixel space."""

    def __init__(self, dt: float = 1.0, q: float = 1.0, r: float = 2.0):
        self.dt, self.q, self.r = dt, q, r

    def _matrices(self):
        dt = self.dt
        F = np.eye(6)
        for i in range(2):
            F[i, i + 2] = dt
            F[i, i + 4] = 0.5 * dt * dt
            F[i + 2, i + 4] = dt
        H = np.zeros((2, 6)); H[0, 0] = H[1, 1] = 1.0
        G = np.array([0.5 * dt * dt, 0.5 * dt * dt, dt, dt, 1.0, 1.0])
        Q = np.outer(G, G) * self.q
        R = np.eye(2) * self.r
        return F, H, Q, R

    def __call__(self, track: np.ndarray) -> Smoothed:
        F, H, Q, R = self._matrices()
        T = len(track)
        xs_pred, Ps_pred, xs_filt, Ps_filt = [], [], [], []
        x = np.zeros(6)
        first = np.where(np.isfinite(track).all(axis=1))[0]
        if len(first):
            x[:2] = track[first[0]]
        P = np.eye(6) * 1e3
        for i in range(T):
            xp = F @ x; Pp = F @ P @ F.T + Q
            xs_pred.append(xp); Ps_pred.append(Pp)
            z = track[i]
            if np.isfinite(z).all():
                y = z - H @ xp
                S = H @ Pp @ H.T + R
                K = Pp @ H.T @ np.linalg.inv(S)
                x = xp + K @ y
                P = (np.eye(6) - K @ H) @ Pp
            else:
                x, P = xp, Pp
            xs_filt.append(x); Ps_filt.append(P)
        # RTS backward pass
        xs = [a.copy() for a in xs_filt]
        for i in range(T - 2, -1, -1):
            C = Ps_filt[i] @ F.T @ np.linalg.inv(Ps_pred[i + 1])
            xs[i] = xs_filt[i] + C @ (xs[i + 1] - xs_pred[i + 1])
        xs = np.array(xs)
        return Smoothed(pos=xs[:, :2], vel=xs[:, 2:4])


def detect_bounces(smoothed: Smoothed, drop_px: float = 6.0,
                   min_separation: int = 5) -> list[int]:
    """Bounces from a local maximum of the image-row followed by the ball
    rising again (a clear drop in row within the next few frames).

    Row v increases as the ball falls and decreases as it rises, so a bounce is
    a row maximum with a subsequent rise. Using only the *subsequent* rise makes
    this robust when the ball descends monotonically into the bounce (common for
    a receding shot, where there is no row "valley" on the approach side). The
    flight apex is a row minimum and is therefore never mistaken for a bounce.
    For best accuracy, re-confirm bounces on the reconstructed 3D z-crossing, or
    use a dedicated bounce classifier (several public repos ship one).
    """
    v = smoothed.pos[:, 1]
    out = []
    n = len(v)
    for i in range(1, n - 1):
        if v[i] >= v[i - 1] and v[i] > v[i + 1]:
            right = v[i + 1:min(n, i + 1 + min_separation)]
            if right.size and (v[i] - right.min()) >= drop_px:
                if not out or i - out[-1] >= min_separation:
                    out.append(i)
    return out


def segment_arcs(n_frames: int, bounce_idx: list[int]) -> list[tuple[int, int]]:
    """Half-open [start, end) frame ranges for each flight arc between bounces."""
    cuts = [0] + [b + 1 for b in bounce_idx] + [n_frames]
    return [(a, b) for a, b in zip(cuts[:-1], cuts[1:]) if b - a >= 3]
