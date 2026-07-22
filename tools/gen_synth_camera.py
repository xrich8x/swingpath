"""gen_synth_camera.py — synthetic ball flights through a REAL camera, on GPU (E4b).

The gray-box net learns the map from a 2D track's SHAPE to its 3D launch state,
and that map is camera-specific, so the training data is rendered through the
exact camera the net will be applied to (built from the clip's court-corner
calibration, same PnP as the physics fit). No human labels, no leak, unlimited.

Trajectories are batch-simulated on the GPU (differentiable ballistic sim), so
this is seconds, not the ~75 min a per-shot CPU RK4 loop took.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\gen_synth_camera.py \\
     --keypoints ..\\data\\yt_rally2_pts.json --hfov 93.46 --n 30000 \\
     --out ..\\data\\output\\synth\\rally2_train.npz
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ball_physics"))

import torch                                                   # noqa: E402
from tennis_tracker.bridge import camera_from_court_corners    # noqa: E402
from tennis_tracker.estimation.kinematics import spin_vector   # noqa: E402
from tennis_tracker.physics.simulator_torch import (           # noqa: E402
    simulate_batch, sample_at, project_batch)

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def draw_launch(rng, n):
    """Same distributions as data/synthesize.sample_shot, vectorised."""
    speed = rng.uniform(18.0, 55.0, n)
    launch = np.radians(rng.uniform(-5.0, 22.0, n))
    azim = np.radians(rng.uniform(-8.0, 8.0, n))
    v0 = np.stack([speed * np.cos(launch) * np.cos(azim),
                   speed * np.cos(launch) * np.sin(azim),
                   speed * np.sin(launch)], axis=1)
    topspin = rng.uniform(-1500, 3500, n)
    sidespin = rng.uniform(-1200, 1200, n)
    omega = np.stack([spin_vector(topspin[i], sidespin[i], travel_dir=v0[i])
                      for i in range(n)])
    p0 = np.stack([rng.uniform(0.0, 2.0, n), rng.uniform(-3.0, 3.0, n),
                   rng.uniform(0.3, 1.2, n)], axis=1)
    return v0.astype(np.float32), omega.astype(np.float32), p0.astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--hfov", type=float, default=93.46)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--fps", type=float, default=60.0)
    ap.add_argument("--horizon-s", type=float, default=1.5)
    ap.add_argument("--pixel-noise", type=float, default=1.5)
    ap.add_argument("--dropout", type=float, default=0.35,
                    help="fraction of in-air frames dropped — mimic our real "
                         "far-court blind rate so the net learns from sparse tracks")
    ap.add_argument("--min-len", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    kp = json.loads(Path(args.keypoints).read_text(encoding="utf-8"))
    cam, _ = camera_from_court_corners({c: kp[c] for c in CORNERS},
                                       (args.width, args.height), hfov_deg=args.hfov)
    K = torch.tensor(cam.K, dtype=torch.float32, device=dev)
    R = torch.tensor(cam.R, dtype=torch.float32, device=dev)
    tc = torch.tensor(cam.t, dtype=torch.float32, device=dev)
    rng = np.random.default_rng(args.seed)

    query = torch.arange(0, args.horizon_s, 1.0 / args.fps, device=dev)   # (T,)
    n_steps = int(args.horizon_s / 2.5e-3)

    recs_uv, recs_t, recs_pos, recs_v0, recs_om, recs_p0 = [], [], [], [], [], []
    BATCH = 4000
    while len(recs_uv) < args.n:
        v0, omega, p0 = draw_launch(rng, BATCH)
        with torch.no_grad():
            pos, _, tg = simulate_batch(torch.tensor(p0, device=dev),
                                        torch.tensor(v0, device=dev),
                                        torch.tensor(omega, device=dev),
                                        n_steps=n_steps, dt=2.5e-3)
            q = sample_at(pos, tg, query)                       # (B,T,3)
            uv = project_batch(q, K, R, tc).cpu().numpy()       # (B,T,2)
            z = q[..., 2].cpu().numpy()                         # (B,T)
        qn = q.cpu().numpy()
        tq = query.cpu().numpy()
        for i in range(BATCH):
            if len(recs_uv) >= args.n:
                break
            in_air = z[i] >= 0.02
            inframe = ((uv[i, :, 0] >= 0) & (uv[i, :, 0] < args.width) &
                       (uv[i, :, 1] >= 0) & (uv[i, :, 1] < args.height))
            keep = in_air & inframe & np.isfinite(uv[i]).all(axis=1)
            if keep.sum() < args.min_len:
                continue
            m = np.where(keep)[0]
            m = m[:m.max() + 1]                                 # contiguous up to last in-air
            u = uv[i, m].astype(np.float32).copy()
            u += rng.normal(0, args.pixel_noise, u.shape).astype(np.float32)
            drop = rng.random(len(u)) < args.dropout
            u[drop] = np.nan
            if np.isfinite(u).all(axis=1).sum() < args.min_len:
                continue
            recs_uv.append(u)
            recs_t.append(tq[m].astype(np.float32))
            recs_pos.append(qn[i, m].astype(np.float32))
            recs_v0.append(v0[i]); recs_om.append(omega[i]); recs_p0.append(p0[i])

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        t=np.array(recs_t, dtype=object), uv=np.array(recs_uv, dtype=object),
        pos3d=np.array(recs_pos, dtype=object),
        v0=np.stack(recs_v0), omega=np.stack(recs_om), p0=np.stack(recs_p0),
        K=cam.K, R=cam.R, t_cam=cam.t)
    print(f"wrote {len(recs_uv)} samples -> {args.out} "
          f"(GPU batch, hfov={args.hfov}, dropout={args.dropout})")


if __name__ == "__main__":
    main()
