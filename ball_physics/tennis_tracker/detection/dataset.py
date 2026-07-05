"""Dataset for training the TrackNet-style detector.

Expects the common TrackNet CSV layout: a directory of frames per clip plus a
`Label.csv` with columns: file, visibility, x-coordinate, y-coordinate
(the public TrackNet / TennisProject datasets use this format).

Each item stacks `in_frames` consecutive frames as the input and renders
`out_frames` Gaussian heatmaps as the target.
"""
from __future__ import annotations

import os
from glob import glob

import numpy as np

try:
    import torch
    from torch.utils.data import Dataset
except Exception as e:  # pragma: no cover
    raise ImportError("dataset requires PyTorch. `pip install torch`.") from e

try:
    import cv2
except Exception as e:  # pragma: no cover
    raise ImportError("dataset requires OpenCV. `pip install opencv-python`.") from e

from .heatmap import gaussian_heatmap


def _read_label_csv(path: str):
    """Return list of (filename, x, y) with NaN where the ball is invisible."""
    rows = []
    with open(path) as f:
        header = f.readline().strip().split(",")
        # tolerate slight column-name variations
        def col(*names, default=None):
            for n in names:
                if n in header:
                    return header.index(n)
            return default
        i_file = col("file", "Frame", "filename", default=0)
        i_vis = col("visibility", "Visibility", "vis")
        i_x = col("x-coordinate", "x", "X")
        i_y = col("y-coordinate", "y", "Y")
        for line in f:
            p = line.strip().split(",")
            if len(p) <= max(i_x or 0, i_y or 0):
                continue
            vis = int(float(p[i_vis])) if i_vis is not None else 1
            x = float(p[i_x]) if vis and p[i_x] not in ("", "nan") else np.nan
            y = float(p[i_y]) if vis and p[i_y] not in ("", "nan") else np.nan
            rows.append((p[i_file], x, y))
    return rows


class TrackNetDataset(Dataset):
    def __init__(self, clip_dirs: list[str], in_frames=3, out_frames=3,
                 size=(360, 640), sigma=3.0, label_name="Label.csv"):
        self.in_frames, self.out_frames = in_frames, out_frames
        self.H, self.W = size
        self.sigma = sigma
        self.samples = []   # (clip_dir, [frame_paths], [(x,y),...])
        for d in clip_dirs:
            csv = os.path.join(d, label_name)
            if not os.path.exists(csv):
                continue
            rows = _read_label_csv(csv)
            paths = [os.path.join(d, r[0]) for r in rows]
            coords = [(r[1], r[2]) for r in rows]
            n = len(paths)
            span = max(in_frames, out_frames)
            for i in range(n - span + 1):
                self.samples.append((paths[i:i + span], coords[i:i + span]))

    def __len__(self):
        return len(self.samples)

    def _load(self, path):
        img = cv2.imread(path)
        if img is None:
            return np.zeros((self.H, self.W, 3), np.float32), 1.0, 1.0
        h0, w0 = img.shape[:2]
        img = cv2.cvtColor(cv2.resize(img, (self.W, self.H)), cv2.COLOR_BGR2RGB)
        return img.astype(np.float32) / 255.0, self.W / w0, self.H / h0

    def __getitem__(self, idx):
        paths, coords = self.samples[idx]
        frames, sx, sy = [], 1.0, 1.0
        for p in paths[:self.in_frames]:
            img, sx, sy = self._load(p)
            frames.append(img)
        x = np.concatenate(frames, axis=2)                  # (H,W,3*in_frames)
        x = torch.from_numpy(x.transpose(2, 0, 1)).float()

        hms = []
        for (cx, cy) in coords[:self.out_frames]:
            hms.append(gaussian_heatmap(self.H, self.W,
                                        cx * sx if np.isfinite(cx) else np.nan,
                                        cy * sy if np.isfinite(cy) else np.nan,
                                        self.sigma))
        y = torch.from_numpy(np.stack(hms, 0)).float()      # (out_frames,H,W)
        return x, y
