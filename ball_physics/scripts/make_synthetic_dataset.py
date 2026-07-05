"""Generate a synthetic labeled dataset for SpinNet.

    python scripts/make_synthetic_dataset.py --n 20000 --out data/synth_train.npz
    python scripts/make_synthetic_dataset.py --n 2000  --out data/synth_val.npz --seed 99
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis_tracker.data.synthesize import build_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fps", type=float, default=60.0)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    n = build_dataset(args.n, args.out, seed=args.seed, fps=args.fps)
    print(f"wrote {n} samples -> {args.out}")


if __name__ == "__main__":
    main()
