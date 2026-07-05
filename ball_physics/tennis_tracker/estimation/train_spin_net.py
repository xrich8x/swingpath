"""Train SpinNet on synthetic trajectories (synthetic-to-real recipe).

Generate data first:
    python -m tennis_tracker.scripts.make_synthetic_dataset --n 20000 --out data/synth_train.npz
    python -m tennis_tracker.scripts.make_synthetic_dataset --n 2000  --out data/synth_val.npz --seed 99
Then train:
    python -m tennis_tracker.estimation.train_spin_net \
        --train data/synth_train.npz --val data/synth_val.npz --epochs 50 --out runs/spinnet

Loss = supervised (v0, omega, p0) + optional physics-informed reprojection,
which rolls the predicted launch state through the differentiable simulator and
matches it back to the *input* 2D track. The reprojection term makes the model
robust to the exact spin parameterisation and improves real-world transfer.
"""
from __future__ import annotations

import argparse
import os

import numpy as np

try:
    import torch
    from torch.utils.data import Dataset, DataLoader
except Exception as e:  # pragma: no cover
    raise ImportError("training requires PyTorch. `pip install torch`.") from e

from .spin_net import SpinNet, make_features, V_SCALE, OMEGA_SCALE, P_SCALE
from ..physics.simulator_torch import simulate_batch, sample_at, project_batch


class SynthDataset(Dataset):
    def __init__(self, npz_path: str, fps: float = 60.0, max_len: int = 80):
        d = np.load(npz_path, allow_pickle=True)
        self.uv = d["uv"]; self.t = d["t"]
        self.v0 = d["v0"]; self.omega = d["omega"]; self.p0 = d["p0"]
        self.K = d["K"].astype(np.float32); self.R = d["R"].astype(np.float32); self.tc = d["t_cam"].astype(np.float32)
        self.fps = fps; self.max_len = max_len

    def __len__(self):
        return len(self.uv)

    def __getitem__(self, i):
        feat, n = make_features(self.uv[i], max_len=self.max_len)
        t = np.asarray(self.t[i], np.float32)[:self.max_len]
        tt = np.zeros(self.max_len, np.float32); tt[:len(t)] = t - t[0] if len(t) else 0.0
        return (torch.from_numpy(feat), torch.tensor(n),
                torch.from_numpy(tt),
                torch.tensor(self.v0[i], dtype=torch.float32),
                torch.tensor(self.omega[i], dtype=torch.float32),
                torch.tensor(self.p0[i], dtype=torch.float32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--phys_weight", type=float, default=0.1, help="physics reprojection loss weight")
    ap.add_argument("--out", default="runs/spinnet")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(args.out, exist_ok=True)
    tr = SynthDataset(args.train); va = SynthDataset(args.val)
    tl = DataLoader(tr, batch_size=args.batch, shuffle=True, num_workers=4, drop_last=True)
    vl = DataLoader(va, batch_size=args.batch, shuffle=False, num_workers=2)
    K = torch.tensor(tr.K, device=device); R = torch.tensor(tr.R, device=device); tc = torch.tensor(tr.tc, device=device)

    model = SpinNet().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)

    def step(batch, train=True):
        feat, n, tt, v0, omega, p0 = [b.to(device) for b in batch]
        pred = model(feat, n)
        # supervised term (scaled units)
        l_v = ((pred["v0"] - v0) / V_SCALE).pow(2).mean()
        l_w = ((pred["omega"] - omega) / OMEGA_SCALE).pow(2).mean()
        l_p = ((pred["p0"] - p0) / P_SCALE).pow(2).mean()
        loss = l_v + l_w + l_p
        # physics-informed reprojection term
        if args.phys_weight > 0:
            pos, _, tg = simulate_batch(pred["p0"], pred["v0"], pred["omega"], n_steps=700, dt=2e-3)
            q = sample_at(pos, tg, tt)                       # (B,T,3)
            uv_pred = project_batch(q, K, R, tc)             # (B,T,2)
            # reconstruct GT pixels from features (un,vn -> pixels) and mask
            mask = feat[..., 4:5]
            uv_gt = torch.stack([(feat[..., 0] + 0.5) * 1280.0,
                                 (feat[..., 1] + 0.5) * 720.0], dim=-1)
            rep = (((uv_pred - uv_gt) / 1280.0) ** 2 * mask).sum() / mask.sum().clamp_min(1.0)
            loss = loss + args.phys_weight * rep
        if train:
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
        return float(loss), float(l_v), float(l_w), float(l_p)

    best = 1e9
    for ep in range(args.epochs):
        model.train()
        agg = np.zeros(4)
        for batch in tl:
            agg += step(batch, True)
        agg /= len(tl)
        model.eval()
        with torch.no_grad():
            vagg = np.mean([step(b, False)[0] for b in vl])
        print(f"epoch {ep:3d} | train {agg[0]:.4f} (v {agg[1]:.3f} w {agg[2]:.3f} p {agg[3]:.3f}) | val {vagg:.4f}")
        sched.step()
        if vagg < best:
            best = vagg
            torch.save({"model": model.state_dict()}, os.path.join(args.out, "best.pt"))
    print("best val", best, "->", os.path.join(args.out, "best.pt"))


if __name__ == "__main__":
    main()
