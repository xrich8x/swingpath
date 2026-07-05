"""Metrics for each stage and for the end-to-end speed/spin outputs."""
from __future__ import annotations

import numpy as np

from ..physics.constants import rad_s_to_rpm


def detection_prf(pred: np.ndarray, gt: np.ndarray, dist_px: float = 5.0) -> dict:
    """Per-frame detection precision/recall/F1 at a pixel-distance threshold.

    pred, gt: (T,2) with NaN where absent.
    """
    tp = fp = fn = 0
    for p, g in zip(pred, gt):
        has_p = np.isfinite(p).all()
        has_g = np.isfinite(g).all()
        if has_p and has_g:
            if np.linalg.norm(p - g) <= dist_px:
                tp += 1
            else:
                fp += 1; fn += 1
        elif has_p and not has_g:
            fp += 1
        elif has_g and not has_p:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def speed_error(pred_mps: float, gt_mps: float) -> dict:
    err = abs(pred_mps - gt_mps)
    return {"abs_mps": err, "abs_kmh": err * 3.6, "pct": 100.0 * err / max(gt_mps, 1e-9)}


def spin_error(pred_omega: np.ndarray, gt_omega: np.ndarray) -> dict:
    pred_omega = np.asarray(pred_omega, float); gt_omega = np.asarray(gt_omega, float)
    mag_err = abs(np.linalg.norm(pred_omega) - np.linalg.norm(gt_omega))
    pn, gn = np.linalg.norm(pred_omega), np.linalg.norm(gt_omega)
    if pn > 1e-9 and gn > 1e-9:
        cos = np.clip(np.dot(pred_omega, gt_omega) / (pn * gn), -1, 1)
        axis_deg = float(np.degrees(np.arccos(cos)))
    else:
        axis_deg = float("nan")
    return {"rpm_err": rad_s_to_rpm(mag_err),
            "rpm_pct": 100.0 * mag_err / max(gn, 1e-9),
            "axis_deg": axis_deg}


def trajectory_rmse(pred3d: np.ndarray, gt3d: np.ndarray) -> float:
    d = pred3d - gt3d
    return float(np.sqrt(np.mean(np.sum(d * d, axis=1))))


def aggregate(records: list[dict], key: str) -> dict:
    vals = np.array([r[key] for r in records if np.isfinite(r.get(key, np.nan))])
    if not len(vals):
        return {}
    return {"mean": float(vals.mean()), "median": float(np.median(vals)),
            "p90": float(np.percentile(vals, 90)), "n": int(len(vals))}
