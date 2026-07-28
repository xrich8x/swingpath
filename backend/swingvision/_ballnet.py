"""Our own ball-detection network (compact 3-frame heatmap U-Net).

Unlike the vendored TrackNet (yastrebksv) and WASB (nttcom) checkpoints — which
carry opposite domain biases (broadcast vs amateur) — this net is trained on OUR
footage domains via pseudo-labels from the tracker's confident locks (see
backend/train_ballnet.py). Deliberately small (~1.3M params) so it is fast on CPU
and exportable to the phone.

Input : 3 consecutive RGB frames, NEWEST first, resized to 512x288, /255,
        stacked to 9 channels (same convention as ball.WASBDetector).
Output: (B, 1, 288, 512) heatmap logits; sigmoid -> per-pixel ball confidence.
"""

import torch
import torch.nn as nn


def _block(cin, cout):
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
    )


class MotionPrompt(nn.Module):
    """TrackNetV4-style learnable motion attention, derived from the 3-frame input
    the net already receives. |f0-f1| and |f1-f2| -> a small conv -> a per-pixel gate
    in [floor, 1]: static regions (burned-in HUD, net posts, line markers) are
    suppressed, moving ones (the ball) are kept. `floor` is a learned scalar so
    training controls how hard to suppress (never fully zero, so a briefly-static
    ball at an apex isn't erased). See TrackNetV4 (arXiv:2409.14543)."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(6, 8, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(8, 1, 1),
        )
        self.floor = nn.Parameter(torch.tensor(0.1))

    def forward(self, x):
        f0, f1, f2 = x[:, 0:3], x[:, 3:6], x[:, 6:9]              # newest, mid, oldest
        d = torch.cat([(f0 - f1).abs(), (f1 - f2).abs()], dim=1)  # (B,6,H,W)
        a = torch.sigmoid(self.net(d))                            # (B,1,H,W) in (0,1)
        floor = self.floor.clamp(0.0, 0.9)
        return floor + (1.0 - floor) * a                          # in [floor, 1]


class BallNet(nn.Module):
    def __init__(self, in_channels: int = 9, base: int = 16,
                 motion_attention: bool = False):
        super().__init__()
        self.motion_attention = motion_attention
        if motion_attention:
            self.motion = MotionPrompt()
        c1, c2, c3, c4 = base, base * 2, base * 4, base * 8
        self.enc1 = _block(in_channels, c1)
        self.enc2 = _block(c1, c2)
        self.enc3 = _block(c2, c3)
        self.enc4 = _block(c3, c4)
        self.pool = nn.MaxPool2d(2)
        self.up3 = nn.ConvTranspose2d(c4, c3, 2, stride=2)
        self.dec3 = _block(c3 * 2, c3)
        self.up2 = nn.ConvTranspose2d(c3, c2, 2, stride=2)
        self.dec2 = _block(c2 * 2, c2)
        self.up1 = nn.ConvTranspose2d(c2, c1, 2, stride=2)
        self.dec1 = _block(c1 * 2, c1)
        self.head = nn.Conv2d(c1, 1, 1)

    def forward(self, x):
        e1 = self.enc1(x)                 # 288x512
        e2 = self.enc2(self.pool(e1))     # 144x256
        e3 = self.enc3(self.pool(e2))     # 72x128
        e4 = self.enc4(self.pool(e3))     # 36x64
        d3 = self.dec3(torch.cat([self.up3(e4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        heat = self.head(d1)              # (B,1,288,512) logits
        if self.motion_attention:
            # Fuse motion attention in LOGIT space (keeps the sigmoid-heatmap
            # interface): log(a) < 0 where nothing moves -> suppresses static
            # false-fires; ~0 where the ball moves -> untouched. (TrackNetV4 A ⊙ V.)
            heat = heat + torch.log(self.motion(x) + 1e-4)
        return heat
