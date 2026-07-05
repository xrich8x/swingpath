"""Heatmap label generation and decoding for the ball detector.

TrackNet-style detectors regress a Gaussian "blob" centred on the ball instead
of a bounding box. These helpers are pure NumPy so they work for offline label
generation and for decoding predictions without importing torch.
"""
from __future__ import annotations

import numpy as np


def gaussian_heatmap(h: int, w: int, cx: float, cy: float, sigma: float = 3.0) -> np.ndarray:
    """Render an (h,w) heatmap with a Gaussian peak (=1) at (cx,cy).

    Returns all-zeros if the centre is NaN (ball not visible in this frame).
    """
    hm = np.zeros((h, w), np.float32)
    if not (np.isfinite(cx) and np.isfinite(cy)):
        return hm
    # only evaluate a local window for speed
    r = int(np.ceil(3 * sigma))
    x0, x1 = max(0, int(cx) - r), min(w, int(cx) + r + 1)
    y0, y1 = max(0, int(cy) - r), min(h, int(cy) + r + 1)
    if x0 >= x1 or y0 >= y1:
        return hm
    xs = np.arange(x0, x1)[None, :]
    ys = np.arange(y0, y1)[:, None]
    hm[y0:y1, x0:x1] = np.exp(-((xs - cx) ** 2 + (ys - cy) ** 2) / (2 * sigma ** 2))
    return hm


def decode_heatmap(hm: np.ndarray, thresh: float = 0.5,
                   refine: bool = True) -> tuple[float, float, float] | None:
    """Return (x, y, score) of the peak, or None if below threshold.

    With `refine`, computes a local intensity-weighted centroid for sub-pixel
    accuracy. Score is the peak value (use it to gate visibility).
    """
    score = float(hm.max())
    if score < thresh:
        return None
    iy, ix = np.unravel_index(int(np.argmax(hm)), hm.shape)
    if not refine:
        return float(ix), float(iy), score
    r = 2
    y0, y1 = max(0, iy - r), min(hm.shape[0], iy + r + 1)
    x0, x1 = max(0, ix - r), min(hm.shape[1], ix + r + 1)
    patch = hm[y0:y1, x0:x1]
    wsum = patch.sum()
    if wsum <= 1e-6:
        return float(ix), float(iy), score
    ys = np.arange(y0, y1)[:, None]
    xs = np.arange(x0, x1)[None, :]
    cx = float((patch * xs).sum() / wsum)
    cy = float((patch * ys).sum() / wsum)
    return cx, cy, score
