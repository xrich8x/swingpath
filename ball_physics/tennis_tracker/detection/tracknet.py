"""TrackNet-style ball detector (PyTorch).

Encoder-decoder that consumes a short stack of consecutive RGB frames and emits
one Gaussian heatmap per frame. Feeding multiple frames lets the network exploit
motion, which is essential for a small, fast, sometimes-blurred ball. This is the
V2 idea (multi-frame in -> multi-frame heatmaps out).

For production you can instead drop in stronger public checkpoints — WASB
(nttcom/WASB-SBDT) or BlurBall (cogsys-tuebingen/blurball) outperform vanilla
TrackNet — behind the same `(frames)->heatmaps` interface used by the pipeline.

Reference: Huang et al., "TrackNet" (arXiv:1907.03698) and TrackNetV2/V3/V4.
"""
from __future__ import annotations

try:
    import torch
    import torch.nn as nn
except Exception as e:  # pragma: no cover
    raise ImportError("tracknet requires PyTorch. `pip install torch`.") from e


def _block(cin, cout, n=2):
    layers = []
    for i in range(n):
        layers += [nn.Conv2d(cin if i == 0 else cout, cout, 3, padding=1),
                   nn.ReLU(inplace=True),
                   nn.BatchNorm2d(cout)]
    return nn.Sequential(*layers)


class TrackNet(nn.Module):
    """Input:  (B, 3*in_frames, H, W) in [0,1].
    Output: (B, out_frames, H, W) heatmap logits (apply sigmoid for probs).
    H, W should be divisible by 8 (e.g. 360x640 -> use 288x512 or 360x640).
    """

    def __init__(self, in_frames: int = 3, out_frames: int = 3):
        super().__init__()
        self.in_frames, self.out_frames = in_frames, out_frames
        c = 3 * in_frames
        self.e1 = _block(c, 64)
        self.e2 = _block(64, 128)
        self.e3 = _block(128, 256, n=3)
        self.pool = nn.MaxPool2d(2, 2)
        self.bott = _block(256, 512, n=3)
        self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.d3 = _block(512 + 256, 256, n=3)
        self.d2 = _block(256 + 128, 128)
        self.d1 = _block(128 + 64, 64)
        self.head = nn.Conv2d(64, out_frames, 1)

    def forward(self, x):
        e1 = self.e1(x)
        e2 = self.e2(self.pool(e1))
        e3 = self.e3(self.pool(e2))
        b = self.bott(self.pool(e3))
        d3 = self.d3(torch.cat([self.up(b), e3], 1))
        d2 = self.d2(torch.cat([self.up(d3), e2], 1))
        d1 = self.d1(torch.cat([self.up(d2), e1], 1))
        return self.head(d1)        # logits


def heatmap_loss(logits, target, pos_weight: float = 200.0, focal: bool = True,
                 gamma: float = 2.0):
    """Heatmap regression loss.

    Heatmaps are ~99.9% background, so we up-weight the positive blob. With
    `focal`, also down-weights easy negatives (helps with blur/occlusion).
    """
    import torch.nn.functional as F
    prob = torch.sigmoid(logits)
    bce = F.binary_cross_entropy_with_logits(
        logits, target, reduction="none",
        pos_weight=torch.tensor(pos_weight, device=logits.device))
    if focal:
        p_t = prob * target + (1 - prob) * (1 - target)
        bce = bce * (1 - p_t).clamp(min=1e-6) ** gamma
    return bce.mean()
