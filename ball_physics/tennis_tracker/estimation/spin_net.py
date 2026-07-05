"""Learned spin / velocity estimator (PyTorch) — the synthetic-to-real model.

A sequence network reads the 2D ball track (normalised pixel positions and
finite differences) and regresses the launch state: initial velocity v0, spin
vector omega, and start position p0. Trained purely on synthetic trajectories
from `data/synthesize.py`, it learns the mapping from a track's *shape* to its
3D motion + spin — which resolves the monocular depth/spin ambiguity that a
single-arc least-squares fit cannot (Kienzle et al., CVPRW 2025, established
that a synthetic-only model transfers zero-shot to real footage).

Use it standalone, or as a warm-start initialiser for the physics fit in
`estimation/trajectory_fit.py` (predict -> refine).
"""
from __future__ import annotations

try:
    import torch
    import torch.nn as nn
except Exception as e:  # pragma: no cover
    raise ImportError("spin_net requires PyTorch. `pip install torch`.") from e


# Output scaling so the network regresses ~unit-variance targets.
V_SCALE = 40.0          # m/s
OMEGA_SCALE = 300.0     # rad/s  (~2865 rpm)
P_SCALE = 5.0           # m


class SpinNet(nn.Module):
    """Input:  x (B,T,F) track features, lengths (B,) valid frame counts.
    Output: dict with v0 (B,3), omega (B,3), p0 (B,3), all in SI units.
    Feature layout produced by `make_features`: [u, v, du, dv, mask] (F=5).
    """

    def __init__(self, in_feat: int = 5, hidden: int = 128, layers: int = 2):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(in_feat, 64, 5, padding=2), nn.ReLU(inplace=True), nn.BatchNorm1d(64),
            nn.Conv1d(64, 128, 5, padding=2), nn.ReLU(inplace=True), nn.BatchNorm1d(128),
        )
        self.gru = nn.GRU(128, hidden, num_layers=layers, batch_first=True,
                          bidirectional=True, dropout=0.1 if layers > 1 else 0.0)
        self.head = nn.Sequential(
            nn.Linear(2 * hidden, 128), nn.ReLU(inplace=True),
            nn.Linear(128, 9),
        )

    def forward(self, x, lengths=None):
        h = self.conv(x.transpose(1, 2)).transpose(1, 2)     # (B,T,128)
        out, _ = self.gru(h)                                 # (B,T,2*hidden)
        if lengths is not None:
            mask = (torch.arange(out.shape[1], device=out.device)[None, :]
                    < lengths[:, None]).float().unsqueeze(-1)
            pooled = (out * mask).sum(1) / mask.sum(1).clamp_min(1.0)
        else:
            pooled = out.mean(1)
        y = self.head(pooled)
        return {
            "v0": y[:, 0:3] * V_SCALE,
            "omega": y[:, 3:6] * OMEGA_SCALE,
            "p0": y[:, 6:9] * P_SCALE,
        }


def make_features(uv: "list|object", img_wh=(1280, 720), max_len: int = 80):
    """Turn one (N,2) pixel track (NaN where missing) into (T,F) features + length.

    Returns numpy arrays; collate into tensors in your DataLoader.
    """
    import numpy as np
    uv = np.asarray(uv, float)
    W, H = img_wh
    N = min(len(uv), max_len)
    feat = np.zeros((max_len, 5), np.float32)
    prev = None
    for i in range(N):
        u, v = uv[i]
        mask = 1.0 if (np.isfinite(u) and np.isfinite(v)) else 0.0
        un = (u / W - 0.5) if mask else 0.0
        vn = (v / H - 0.5) if mask else 0.0
        du = dv = 0.0
        if mask and prev is not None:
            du, dv = un - prev[0], vn - prev[1]
        feat[i] = [un, vn, du, dv, mask]
        if mask:
            prev = (un, vn)
    return feat, N
