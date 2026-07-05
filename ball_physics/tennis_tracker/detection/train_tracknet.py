"""Train the TrackNet-style ball detector.

Usage:
    python -m tennis_tracker.detection.train_tracknet \
        --data /path/to/dataset_root --epochs 30 --out runs/tracknet

`data_root` should contain one sub-directory per clip, each with frames and a
`Label.csv` (TrackNet format). See detection/dataset.py.
"""
from __future__ import annotations

import argparse
import os
from glob import glob

try:
    import torch
    from torch.utils.data import DataLoader, random_split
except Exception as e:  # pragma: no cover
    raise ImportError("training requires PyTorch. `pip install torch`.") from e

from .tracknet import TrackNet, heatmap_loss
from .dataset import TrackNetDataset
from .heatmap import decode_heatmap


def evaluate(model, loader, device, tol_px=4.0):
    model.eval()
    tp = fp = fn = 0
    with torch.no_grad():
        for x, y in loader:
            pred = torch.sigmoid(model(x.to(device))).cpu().numpy()
            tgt = y.numpy()
            for b in range(pred.shape[0]):
                for c in range(pred.shape[1]):
                    pk = decode_heatmap(pred[b, c])
                    gk = decode_heatmap(tgt[b, c], thresh=0.5)
                    if pk and gk:
                        d = ((pk[0]-gk[0])**2 + (pk[1]-gk[1])**2) ** 0.5
                        tp += int(d <= tol_px); fp += int(d > tol_px); fn += int(d > tol_px)
                    elif pk and not gk:
                        fp += 1
                    elif gk and not pk:
                        fn += 1
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec, rec, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dataset root (clips as subdirs)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--in_frames", type=int, default=3)
    ap.add_argument("--out_frames", type=int, default=3)
    ap.add_argument("--out", default="runs/tracknet")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(args.out, exist_ok=True)
    clip_dirs = [d for d in glob(os.path.join(args.data, "*")) if os.path.isdir(d)]
    ds = TrackNetDataset(clip_dirs, in_frames=args.in_frames, out_frames=args.out_frames)
    if len(ds) == 0:
        raise SystemExit("No samples found. Check dataset layout / Label.csv files.")
    n_val = max(1, int(0.1 * len(ds)))
    tr, va = random_split(ds, [len(ds) - n_val, n_val])
    tl = DataLoader(tr, batch_size=args.batch, shuffle=True, num_workers=4, drop_last=True)
    vl = DataLoader(va, batch_size=args.batch, shuffle=False, num_workers=2)

    model = TrackNet(args.in_frames, args.out_frames).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)

    best = -1.0
    for ep in range(args.epochs):
        model.train()
        running = 0.0
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = heatmap_loss(model(x), y)
            loss.backward()
            opt.step()
            running += loss.item()
        sched.step()
        prec, rec, f1 = evaluate(model, vl, device)
        print(f"epoch {ep:3d} | loss {running/len(tl):.4f} | val P {prec:.3f} R {rec:.3f} F1 {f1:.3f}")
        if f1 >= best:
            best = f1
            torch.save({"model": model.state_dict(), "in_frames": args.in_frames,
                        "out_frames": args.out_frames}, os.path.join(args.out, "best.pt"))
    print("best F1", best, "saved to", os.path.join(args.out, "best.pt"))


if __name__ == "__main__":
    main()
