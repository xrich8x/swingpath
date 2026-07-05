"""End-to-end orchestration: video (or 2D track) -> per-shot speed & spin.

Two entry points:
  * `TennisTracker.process_track(times, uv)` — the fully-validated core. Give it
    a 2D ball track + a calibrated camera and it returns a reading per flight arc.
  * `TennisTracker.process_video(path)` — convenience wrapper that runs the
    learned detector + court detector first. Requires torch + trained weights.

The seven stages map onto modules like this:
  1. data/synthesize.py        ground-truth & synthetic training data
  2. detection/tracknet.py     ball detection (heatmaps)         [needs torch]
  3. tracking/tracker.py       link + smooth + bounce + segment
  4. calibration/court.py+lift court homography + 2D->3D lift
  5. estimation/trajectory_fit speed (and a first spin estimate)
  6. estimation/spin_net.py    learned spin/velocity (synthetic-to-real) [torch]
  7. eval/metrics.py           evaluation
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .data.camera import Camera
from .tracking import link_detections, fill_gaps, KalmanSmoother, detect_bounces, segment_arcs
from .calibration.lift import lift_arc
from .estimation.kinematics import MotionReadout


@dataclass
class ShotReadout:
    arc: tuple[int, int]
    readout: MotionReadout
    reproj_rmse: float
    n_points: int


class TennisTracker:
    def __init__(self, camera: Camera, homography: Optional[np.ndarray] = None,
                 detector=None, spin_net=None, fps: float = 60.0):
        self.camera = camera
        self.H = homography
        self.detector = detector       # callable: frames -> per-frame (M,2) detections
        self.spin_net = spin_net        # optional warm-start initialiser
        self.fps = fps
        self.kf = KalmanSmoother(dt=1.0, q=2.0, r=3.0)

    # ---- core: a 2D track in, readings out ----
    def process_track(self, times: np.ndarray, uv: np.ndarray) -> list[ShotReadout]:
        times = np.asarray(times, float)
        uv = np.asarray(uv, float)
        track = fill_gaps(link_detections([p.reshape(1, 2) if np.all(np.isfinite(p)) else None
                                           for p in uv]))
        sm = self.kf(track)
        bounces = detect_bounces(sm)
        arcs = segment_arcs(len(track), bounces)

        readings: list[ShotReadout] = []
        for (a, b) in arcs:
            seg_t = times[a:b] - times[a]
            seg_uv = uv[a:b]
            if np.isfinite(seg_uv).all(axis=1).sum() < 4:
                continue
            v0_init = omega_init = None
            if self.spin_net is not None:
                v0_init, omega_init = self._spinnet_init(seg_t, seg_uv)
            # anchor the arc start at a homography-lifted contact if it begins at a bounce
            anchor_uv = uv[a] if (a - 1) in bounces and self.H is not None else None
            la = lift_arc(seg_t, seg_uv, self.camera, anchor_uv=anchor_uv, H=self.H,
                          v0_init=v0_init, omega_init=omega_init)
            readings.append(ShotReadout((a, b), la.fit.readout, la.fit.rmse,
                                        int(np.isfinite(seg_uv).all(axis=1).sum())))
        return readings

    def _spinnet_init(self, times, uv):
        try:
            import torch
            from .estimation.spin_net import make_features
        except Exception:
            return None, None
        feat, n = make_features(uv, img_wh=(self.camera.width, self.camera.height))
        with torch.no_grad():
            out = self.spin_net(torch.from_numpy(feat).unsqueeze(0),
                                torch.tensor([n]))
        return out["v0"][0].cpu().numpy(), out["omega"][0].cpu().numpy()

    # ---- convenience: full video path ----
    def process_video(self, path: str) -> list[ShotReadout]:
        """Detect the ball per frame, then run the core. Needs torch + a detector."""
        if self.detector is None:
            raise RuntimeError("process_video needs a detector; pass one to TennisTracker "
                               "or use process_track with your own 2D track.")
        try:
            import cv2
        except Exception as e:
            raise ImportError("process_video needs OpenCV") from e
        cap = cv2.VideoCapture(path)
        frames = []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(fr)
        cap.release()
        fps = cap.get(cv2.CAP_PROP_FPS) or self.fps
        per_frame = self.detector(frames)                      # list of (M,2) pixel dets
        times = np.arange(len(per_frame)) / fps
        track = fill_gaps(link_detections(per_frame))
        return self.process_track(times, track)
