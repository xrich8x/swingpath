"""Visualise how spin bends a tennis-ball trajectory (no training needed).

    python scripts/demo_physics.py --out physics_demo.png
"""
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tennis_tracker.physics import simulate
from tennis_tracker.estimation import spin_vector, summarize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="physics_demo.png")
    args = ap.parse_args()

    p0 = np.array([0.0, 0.0, 1.0])
    v0 = np.array([38.0, 0.0, 4.0])
    shots = {
        "flat (no spin)": np.zeros(3),
        "topspin 2800 rpm": spin_vector(topspin_rpm=2800, travel_dir=v0),
        "backspin 2000 rpm": spin_vector(topspin_rpm=-2000, travel_dir=v0),
        "sidespin 2000 rpm": spin_vector(sidespin_rpm=2000, travel_dir=v0),
    }

    fig, (ax_side, ax_top) = plt.subplots(1, 2, figsize=(13, 4.5))
    for label, omega in shots.items():
        tr = simulate(p0, v0, omega, bounces=1)
        r = summarize(v0, omega)
        ax_side.plot(tr.pos[:, 0], tr.pos[:, 2], label=f"{label}")
        ax_top.plot(tr.pos[:, 0], tr.pos[:, 1], label=f"{label}")
        print(f"{label:20s} land x={tr.pos[tr.bounce_indices[0]][0]:5.1f} m  "
              f"speed={r.speed_kmh:5.1f} km/h  spin={r.spin_rpm:5.0f} rpm")

    ax_side.axhline(0, color="k", lw=0.8)
    ax_side.axvline(11.885, color="g", ls="--", lw=0.8, label="net")
    ax_side.set_xlabel("court length x (m)"); ax_side.set_ylabel("height z (m)")
    ax_side.set_title("Side view"); ax_side.legend(fontsize=8); ax_side.set_ylim(bottom=0)
    ax_top.axhline(0, color="k", lw=0.4)
    ax_top.set_xlabel("court length x (m)"); ax_top.set_ylabel("lateral y (m)")
    ax_top.set_title("Top view (sidespin curve)"); ax_top.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(args.out, dpi=130)
    print("saved", args.out)


if __name__ == "__main__":
    main()
