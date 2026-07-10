"""Fine-tune the court-keypoint model (CourtNet) on OUR calibrated clips.

Transfer learning from the broadcast-trained checkpoint (weights/court_detector.pt)
to the amateur angles in ../data/court_dataset (built by build_court_dataset.py).
The core augmentation is RANDOM PERSPECTIVE: every sample is re-warped as if shot
from a different camera angle (corner jitter -> homography warp of image AND
keypoints), so each user court-setup teaches a whole neighbourhood of angles, not
one. Horizontal flips swap the left/right keypoint identities.

    .venv-train/Scripts/python.exe train_courtnet.py --epochs 15
Best checkpoint -> weights/courtnet_ft.pt (calibration.detect_court_learned
prefers it automatically when present; the reprojection gate still applies).
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
from swingvision._courtnet import CourtNet

IN_W, IN_H = 640, 360
SIGMA = 7.0
# Horizontal flip swaps left/right keypoint identities (order: COURT_KP_LANDMARKS).
FLIP_MAP = [1, 0, 3, 2, 6, 7, 4, 5, 9, 8, 11, 10, 12, 13]


def heatmaps(kps, w=IN_W, h=IN_H, sigma=SIGMA):
    """15 target heatmaps: 14 keypoints + court centre (mean of the 4 corners)."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    out = np.zeros((15, h, w), dtype=np.float32)
    pts = list(kps) + [np.mean(kps[:4], axis=0)]
    for i, (x, y) in enumerate(pts):
        if not (-40 <= x < w + 40 and -40 <= y < h + 40):
            continue
        out[i] = np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * sigma * sigma))
    return out


class CourtFrames(Dataset):
    def __init__(self, root, split="train", val_frac=0.2, augment=True,
                 balance_to=60):
        # Balance domains: each clip is repeated up to ~balance_to training frames
        # so a big single-calibration clip (indoor_elev, 222) can't drown the small
        # hand-labelled amateur clips (~15 each), and broadcast isn't forgotten.
        # Random-perspective augmentation turns the repeats into distinct samples.
        self.samples = []
        self.augment = augment and split == "train"
        for tag in sorted(os.listdir(root)):
            lp = os.path.join(root, tag, "labels.json")
            if not os.path.isfile(lp):
                continue
            meta = json.load(open(lp))
            items = sorted(((int(k), v) for k, v in meta["labels"].items()))
            n_val = max(1, int(len(items) * val_frac))
            keep = items[:-n_val] if split == "train" else items[-n_val:]
            reps = max(1, round(balance_to / max(1, len(keep)))) if split == "train" else 1
            for idx, kps in keep:
                for _ in range(reps):
                    self.samples.append((os.path.join(root, tag), idx, np.asarray(kps, np.float32)))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, k):
        d, i, kps = self.samples[k]
        img = cv2.imread(os.path.join(d, f"{i:05d}.jpg"))
        kps = kps.copy()

        if self.augment:
            if random.random() < 0.5:   # horizontal flip + identity swap
                img = cv2.flip(img, 1)
                kps[:, 0] = IN_W - 1 - kps[:, 0]
                kps = kps[FLIP_MAP]
            if random.random() < 0.6:   # random perspective = new camera angle
                j = IN_W * 0.05
                src = np.float32([[0, 0], [IN_W, 0], [IN_W, IN_H], [0, IN_H]])
                dst = src + np.random.uniform(-j, j, (4, 2)).astype(np.float32)
                P = cv2.getPerspectiveTransform(src, dst)
                img = cv2.warpPerspective(img, P, (IN_W, IN_H))
                ones = np.ones((len(kps), 1), np.float32)
                q = (P @ np.hstack([kps, ones]).T).T
                kps = (q[:, :2] / q[:, 2:3]).astype(np.float32)
            if random.random() < 0.5:   # lighting jitter
                a = 1.0 + random.uniform(-0.3, 0.3)
                b = random.uniform(-25, 25)
                img = cv2.convertScaleAbs(img, alpha=a, beta=b)

        inp = np.rollaxis(img.astype(np.float32) / 255.0, 2, 0)
        return torch.from_numpy(np.ascontiguousarray(inp)), torch.from_numpy(heatmaps(kps)), torch.from_numpy(kps)


def evaluate(model, loader, device):
    model.eval()
    errs = []
    with torch.no_grad():
        for inp, _, kps in loader:
            out = torch.sigmoid(model(inp.to(device)))
            B = out.shape[0]
            hm = out.reshape(B, 15, IN_H, IN_W)[:, :14]
            flat = hm.reshape(B, 14, -1).argmax(dim=2).cpu()
            px = (flat % IN_W).float()
            py = (flat // IN_W).float()
            e = torch.hypot(px - kps[:, :, 0], py - kps[:, :, 1])
            vis = (kps[:, :, 0] >= 0) & (kps[:, :, 0] < IN_W) & (kps[:, :, 1] >= 0) & (kps[:, :, 1] < IN_H)
            errs += e[vis].tolist()
    errs = np.asarray(errs)
    return float(np.median(errs)), float((errs <= 8).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/court_dataset")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--init", default="weights/court_detector.pt")
    ap.add_argument("--out", default="weights/courtnet_ft.pt")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--freeze-encoder", action="store_true", dest="freeze_encoder",
                    help="train the decoder only (v1 recipe; too conservative alone)")
    args = ap.parse_args()

    train_ds = CourtFrames(args.data, "train")
    val_ds = CourtFrames(args.data, "val", augment=False)
    print(f"train {len(train_ds)} / val {len(val_ds)} | device {args.device}")
    train_ld = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2,
                          pin_memory=(args.device == "cuda"))
    val_ld = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    model = CourtNet(out_channels=15)
    model.load_state_dict(torch.load(args.init, map_location="cpu"))
    model.to(args.device)
    # Optionally freeze the encoder (v1 recipe — proved too conservative on its
    # own). Default: all params trainable at a LOW lr (v2), relying on the
    # broadcast oversampling to prevent the forgetting that broke v0.
    frozen = 0
    if args.freeze_encoder:
        for name, p in model.named_parameters():
            if any(name.startswith(f"conv{i}.") for i in range(1, 11)):
                p.requires_grad = False
                frozen += 1
    print(f"frozen encoder params: {frozen}")
    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    # MSE on sigmoid heatmaps — the regime the checkpoint was originally trained
    # in; positives up-weighted so the loss doesn't collapse to all-background.
    def crit(logits, target):
        prob = torch.sigmoid(logits)
        w = 1.0 + 20.0 * target
        return (w * (prob - target) ** 2).mean()

    med0, hit0 = evaluate(model, val_ld, args.device)
    print(f"BEFORE fine-tune: val median {med0:.1f}px  within8px {hit0*100:.1f}%")

    best = hit0
    for ep in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for inp, hm, _ in train_ld:
            inp, hm = inp.to(args.device), hm.to(args.device)
            opt.zero_grad()
            out = model(inp).reshape(hm.shape)
            loss = crit(out, hm)
            loss.backward()
            opt.step()
            tot += float(loss.detach())
        sched.step()
        med, hit = evaluate(model, val_ld, args.device)
        mark = ""
        if hit > best:
            best = hit
            torch.save(model.state_dict(), args.out)
            mark = "  <- saved"
        print(f"epoch {ep:3d}  loss {tot/max(len(train_ld),1):.4f}  "
              f"val median {med:.1f}px  within8px {hit*100:.1f}%{mark}", flush=True)
    print(f"best within-8px: {best*100:.1f}% (started {hit0*100:.1f}%) -> {args.out}")


if __name__ == "__main__":
    main()
