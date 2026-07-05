"""Train OUR ball detector (swingvision._ballnet.BallNet) on the pseudo-label
dataset built by build_ball_dataset.py.

    .venv-train/Scripts/python.exe train_ballnet.py --epochs 40

Samples are 3-frame windows (newest first, 512x288, /255) with a Gaussian target
heatmap at the tracker's pseudo-label. Temporal split per clip: the last 20% of
labeled frames are validation (no leakage from smoothing/augmentation). Metric is
localization: predicted heatmap peak vs label (median px + hit-rate within 10px).
Best checkpoint -> weights/ballnet.pt.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swingvision._ballnet import BallNet

IN_W, IN_H = 512, 288
SIGMA = 3.0


def gaussian_heatmap(x, y, w=IN_W, h=IN_H, sigma=SIGMA):
    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    gx = np.exp(-((xs - x) ** 2) / (2 * sigma * sigma))
    gy = np.exp(-((ys - y) ** 2) / (2 * sigma * sigma))
    return np.outer(gy, gx)


class BallWindows(Dataset):
    def __init__(self, root, split="train", val_frac=0.2, augment=True):
        self.samples = []   # (clip_dir, frame_idx, x, y)
        self.augment = augment and split == "train"
        for tag in sorted(os.listdir(root)):
            d = os.path.join(root, tag)
            lp = os.path.join(d, "labels.json")
            if not os.path.isfile(lp):
                continue
            with open(lp, "r", encoding="utf-8") as f:
                meta = json.load(f)
            items = sorted(((int(k), v) for k, v in meta["labels"].items()))
            n_val = max(1, int(len(items) * val_frac))
            keep = items[:-n_val] if split == "train" else items[-n_val:]
            for idx, (x, y) in keep:
                self.samples.append((d, idx, float(x), float(y)))

    def __len__(self):
        return len(self.samples)

    def _frame(self, d, i):
        img = cv2.imread(os.path.join(d, f"{i:05d}.jpg"))
        if img is None:   # missing predecessor: repeat the nearest available
            img = cv2.imread(os.path.join(d, f"{max(i, 0):05d}.jpg"))
        return img

    def __getitem__(self, k):
        d, i, x, y = self.samples[k]
        frames = [self._frame(d, i), self._frame(d, i - 1), self._frame(d, i - 2)]

        if self.augment:
            if random.random() < 0.5:     # horizontal flip
                frames = [cv2.flip(f, 1) for f in frames]
                x = IN_W - 1 - x
            if random.random() < 0.5:     # brightness / contrast jitter
                a = 1.0 + random.uniform(-0.25, 0.25)
                b = random.uniform(-20, 20)
                frames = [cv2.convertScaleAbs(f, alpha=a, beta=b) for f in frames]
            if random.random() < 0.5:     # small translation
                tx, ty = random.randint(-24, 24), random.randint(-16, 16)
                M = np.float32([[1, 0, tx], [0, 1, ty]])
                frames = [cv2.warpAffine(f, M, (IN_W, IN_H)) for f in frames]
                x, y = x + tx, y + ty
                x = min(max(x, 0), IN_W - 1)
                y = min(max(y, 0), IN_H - 1)

        arr = np.concatenate(frames, axis=2).astype(np.float32) / 255.0
        inp = np.ascontiguousarray(np.rollaxis(arr, 2, 0))
        hm = gaussian_heatmap(x, y)[None]
        return torch.from_numpy(inp), torch.from_numpy(hm), torch.tensor([x, y])


def evaluate(model, loader, device):
    model.eval()
    errs = []
    with torch.no_grad():
        for inp, _, xy in loader:
            out = torch.sigmoid(model(inp.to(device)))[:, 0]
            B, H, W = out.shape
            flat = out.reshape(B, -1).argmax(dim=1).cpu()
            px = (flat % W).float()
            py = (flat // W).float()
            errs += torch.hypot(px - xy[:, 0], py - xy[:, 1]).tolist()
    errs = np.array(errs)
    return float(np.median(errs)), float((errs <= 10).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/ball_dataset")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--out", default="weights/ballnet.pt")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    train_ds = BallWindows(args.data, "train")
    val_ds = BallWindows(args.data, "val", augment=False)
    print(f"train {len(train_ds)} / val {len(val_ds)} samples | device {args.device}")
    train_ld = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2,
                          pin_memory=(args.device == "cuda"))
    val_ld = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    model = BallNet().to(args.device)
    n_par = sum(p.numel() for p in model.parameters())
    print(f"BallNet params: {n_par/1e6:.2f}M")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(100.0, device=args.device))

    best = -1.0
    for ep in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for inp, hm, _ in train_ld:
            inp, hm = inp.to(args.device), hm.to(args.device)
            opt.zero_grad()
            loss = crit(model(inp), hm)
            loss.backward()
            opt.step()
            tot += float(loss)
        sched.step()
        med, hit10 = evaluate(model, val_ld, args.device)
        marker = ""
        if hit10 > best:
            best = hit10
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            torch.save({"model_state_dict": model.state_dict()}, args.out)
            marker = "  <- saved"
        print(f"epoch {ep:3d}  loss {tot/max(len(train_ld),1):.4f}  "
              f"val median {med:.1f}px  within10px {hit10*100:.1f}%{marker}", flush=True)
    print(f"best within-10px: {best*100:.1f}%  -> {args.out}")


if __name__ == "__main__":
    main()
