"""Train OUR ball detector (swingvision._ballnet.BallNet) on the pseudo-label
dataset built by build_ball_dataset.py / relabel_train_clips.py.

    .venv-train/Scripts/python.exe train_ballnet.py --epochs 40

Samples are 3-frame windows (newest first, 512x288, /255) with a Gaussian target
heatmap at the tracker's pseudo-label. Temporal split per clip: the last 20% of
labeled frames are validation (no leakage from smoothing/augmentation). Metric is
localization: predicted heatmap peak vs label (median px + hit-rate within 10px).
Best checkpoint -> weights/ballnet.pt.

v2 additions (HANDOFF §11): datasets may carry "negatives" — frame indices with
NO ball, trained against an all-zero heatmap. v1 never saw a negative, which is
why it fires at junk whenever play stops (60% FP on the human gold benchmark).
Val negatives report the false-fire rate (peak >= 0.5, the OurBallDetector
default score_thresh); model selection uses hit@10 minus false-fire so a
checkpoint can't win by firing everywhere. --exclude skips clips: indoor_elev
(= yt_rally2) is excluded BY DEFAULT — it is the human gold benchmark clip and
must never be trained on.
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
# Visibility-weighted loss (TOTNet §ablation): occlusion augmentation ALONE makes
# tracking WORSE; it only helps when the occluded (hard) samples are weighted higher
# so the model is forced to recover the ball from temporal context instead of the
# missing current-frame pixels. Synthetic-occlusion frames are our "fully occluded"
# visibility level and carry OCC_WEIGHT; everything else is 1.0.
OCC_WEIGHT = 3.0
# Negative frames (no ball, incl. mined hard negatives) carry an all-zero target,
# so with pos_weight=100 on the ball pixels and 4x more positives than negatives,
# a negative's loss is negligible and the model never learns to shut up on the
# HUD/post/fence confusers (measured: false-fire stuck ~90% on the val hard
# negatives even as recall recovered). Upweighting the negative SAMPLE is the
# direct lever — suppressing a false-fire now costs as much as finding a ball.
NEG_WEIGHT = 8.0


def gaussian_heatmap(x, y, w=IN_W, h=IN_H, sigma=SIGMA):
    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    gx = np.exp(-((xs - x) ** 2) / (2 * sigma * sigma))
    gy = np.exp(-((ys - y) ** 2) / (2 * sigma * sigma))
    return np.outer(gy, gx)


def _motion_blur_kernel(size, angle_deg):
    """A directional line kernel — simulates a fast ball / camera motion streak."""
    k = np.zeros((size, size), np.float32)
    k[size // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle_deg, 1.0)
    k = cv2.warpAffine(k, M, (size, size))
    s = k.sum()
    return k / s if s > 0 else k


class BallWindows(Dataset):
    def __init__(self, root, split="train", val_frac=0.2, augment=True,
                 exclude=(), use_hard_negs=True):
        self.samples = []   # (clip_dir, frame_idx, x, y); x is None => negative
        self.augment = augment and split == "train"
        for tag in sorted(os.listdir(root)):
            if tag in exclude:
                continue
            d = os.path.join(root, tag)
            lp = os.path.join(d, "labels.json")
            if not os.path.isfile(lp):
                continue
            with open(lp, "r", encoding="utf-8") as f:
                meta = json.load(f)
            items = sorted(((int(k), v) for k, v in meta["labels"].items()))
            labeled = {int(k) for k in meta["labels"]}   # frames that HAVE a ball
            n_val = max(1, int(len(items) * val_frac))
            keep = items[:-n_val] if split == "train" else items[-n_val:]
            for idx, (x, y) in keep:
                self.samples.append((d, idx, float(x), float(y)))
            negs = sorted(meta.get("negatives", []))
            if negs:
                n_val = max(1, int(len(negs) * val_frac))
                nkeep = negs[:-n_val] if split == "train" else negs[-n_val:]
                self.samples += [(d, idx, None, None) for idx in nkeep]
            # Hard negatives (mine_hard_negatives.py): frames where BallNet
            # STATIC-fired on a fixture (HUD/post/fence/crowd) — its documented
            # false-fire weakness. Guard: never use a frame that HAS a labeled
            # ball as an all-zero-target negative, even if the fixture fire was
            # elsewhere in it (that frame does contain a ball).
            hp = os.path.join(d, "hard_negatives.json")
            if use_hard_negs and os.path.isfile(hp):
                with open(hp, "r", encoding="utf-8") as f:
                    hard = sorted(set(json.load(f).get("hard_negatives", []))
                                  - labeled - set(negs))
                if hard:
                    n_val = max(1, int(len(hard) * val_frac))
                    hkeep = hard[:-n_val] if split == "train" else hard[-n_val:]
                    self.samples += [(d, idx, None, None) for idx in hkeep]

    def counts(self):
        n_neg = sum(1 for s in self.samples if s[2] is None)
        return len(self.samples) - n_neg, n_neg

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
        negative = x is None
        occluded = False

        if self.augment:
            if random.random() < 0.5:     # horizontal flip
                frames = [cv2.flip(f, 1) for f in frames]
                if not negative:
                    x = IN_W - 1 - x
            if random.random() < 0.5:     # brightness / contrast jitter
                a = 1.0 + random.uniform(-0.25, 0.25)
                b = random.uniform(-20, 20)
                frames = [cv2.convertScaleAbs(f, alpha=a, beta=b) for f in frames]
            if random.random() < 0.5:     # small translation
                tx, ty = random.randint(-24, 24), random.randint(-16, 16)
                M = np.float32([[1, 0, tx], [0, 1, ty]])
                frames = [cv2.warpAffine(f, M, (IN_W, IN_H)) for f in frames]
                if not negative:
                    x, y = x + tx, y + ty
                    x = min(max(x, 0), IN_W - 1)
                    y = min(max(y, 0), IN_H - 1)
            if random.random() < 0.35:    # MOTION BLUR — fast ball / camera (BlurBall)
                ker = _motion_blur_kernel(random.choice([5, 7, 9, 11]),
                                          random.uniform(0, 180))
                frames = [cv2.filter2D(f, -1, ker) for f in frames]
            if not negative and random.random() < 0.30:
                # OCCLUSION (TOTNet): hide the ball in the NEWEST frame only, keeping
                # the target at its true spot. The prior two frames still show it, so
                # the model must learn to carry the ball through a brief occlusion
                # (a player/racket/net crossing) instead of dropping it.
                r = random.randint(8, 26)
                xi, yi = int(round(x)), int(round(y))
                col = tuple(int(v) for v in np.random.randint(0, 256, 3))
                cv2.rectangle(frames[0], (xi - r, yi - r), (xi + r, yi + r), col, -1)
                occluded = True

        arr = np.concatenate(frames, axis=2).astype(np.float32) / 255.0
        inp = np.ascontiguousarray(np.rollaxis(arr, 2, 0))
        if negative:
            hm = np.zeros((1, IN_H, IN_W), dtype=np.float32)
            x = y = -1.0   # sentinel: evaluate() separates negatives on x < 0
        else:
            hm = gaussian_heatmap(x, y)[None]
        # dtype pinned: augmentation clamps can make x/y ints, and a batch that
        # mixes Long and Float xy tensors fails to collate (torch.stack).
        w = NEG_WEIGHT if negative else (OCC_WEIGHT if occluded else 1.0)
        return (torch.from_numpy(inp), torch.from_numpy(hm),
                torch.tensor([x, y], dtype=torch.float32),
                torch.tensor(w, dtype=torch.float32))


def evaluate(model, loader, device, fire_thresh=0.5):
    """Positives: localization (median px error, hit@10). Negatives (xy < 0
    sentinel): false-fire rate — fraction whose peak clears fire_thresh, the
    OurBallDetector default score_thresh."""
    model.eval()
    errs, fires = [], []
    with torch.no_grad():
        for inp, _, xy, _ in loader:
            out = torch.sigmoid(model(inp.to(device)))[:, 0]
            B, H, W = out.shape
            flat = out.reshape(B, -1)
            peak = flat.max(dim=1).values.cpu()
            idx = flat.argmax(dim=1).cpu()
            px = (idx % W).float()
            py = (idx // W).float()
            neg = xy[:, 0] < 0
            errs += torch.hypot(px - xy[:, 0], py - xy[:, 1])[~neg].tolist()
            fires += (peak[neg] >= fire_thresh).tolist()
    errs = np.array(errs)
    med = float(np.median(errs)) if len(errs) else float("nan")
    hit10 = float((errs <= 10).mean()) if len(errs) else 0.0
    ff = float(np.mean(fires)) if fires else 0.0
    return med, hit10, ff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/ball_dataset")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--out", default="weights/ballnet.pt")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--exclude", nargs="*", default=["indoor_elev"],
                    help="dataset dirs to skip (default: the gold benchmark clip)")
    ap.add_argument("--motion-attention", action="store_true", dest="motion_attention",
                    help="TrackNetV4-style learnable motion attention (frame-diff gate) "
                         "in BallNet — for the v4 model")
    args = ap.parse_args()

    train_ds = BallWindows(args.data, "train", exclude=args.exclude)
    val_ds = BallWindows(args.data, "val", augment=False, exclude=args.exclude)
    tp, tn = train_ds.counts()
    vp, vn = val_ds.counts()
    print(f"train {tp}+{tn}neg / val {vp}+{vn}neg | device {args.device} | "
          f"excluded {args.exclude}")
    train_ld = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2,
                          pin_memory=(args.device == "cuda"))
    val_ld = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    model = BallNet(motion_attention=args.motion_attention).to(args.device)
    n_par = sum(p.numel() for p in model.parameters())
    print(f"BallNet params: {n_par/1e6:.2f}M"
          f"{' (+motion-attention)' if args.motion_attention else ''}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    # reduction='none' so we can weight each sample by its visibility (OCC_WEIGHT for
    # synthetic-occlusion frames) before averaging — the TOTNet fix that turns
    # occlusion augmentation from a regression into a gain.
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(100.0, device=args.device),
                                reduction="none")

    best = -1.0
    for ep in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for inp, hm, _, w in train_ld:
            inp, hm, w = inp.to(args.device), hm.to(args.device), w.to(args.device)
            opt.zero_grad()
            per_px = crit(model(inp), hm)            # [B,1,H,W]
            per_sample = per_px.mean(dim=(1, 2, 3))  # [B]
            loss = (per_sample * w).mean()
            loss.backward()
            opt.step()
            tot += loss.item()
        sched.step()
        med, hit10, ff = evaluate(model, val_ld, args.device)
        # selection: find the ball AND shut up when there is none — a model
        # can't win the checkpoint race by firing everywhere
        score = hit10 - ff
        marker = ""
        if score > best:
            best = score
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            torch.save({"model_state_dict": model.state_dict()}, args.out)
            marker = "  <- saved"
        print(f"epoch {ep:3d}  loss {tot/max(len(train_ld),1):.4f}  "
              f"val median {med:.1f}px  within10px {hit10*100:.1f}%  "
              f"false-fire {ff*100:.1f}%{marker}", flush=True)
    print(f"best (hit@10 - false-fire): {best*100:.1f}%  -> {args.out}")


if __name__ == "__main__":
    main()
