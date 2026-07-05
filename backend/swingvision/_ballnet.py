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


class BallNet(nn.Module):
    def __init__(self, in_channels: int = 9, base: int = 16):
        super().__init__()
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
        return self.head(d1)              # (B,1,288,512) logits
