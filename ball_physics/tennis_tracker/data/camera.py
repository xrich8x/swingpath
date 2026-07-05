"""Minimal pinhole camera: project 3D world points to 2D pixels and back to rays.

Used to (a) render synthetic 2D ball tracks for training/eval, and (b) define
the homography between the court plane and the image (see calibration/).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def look_at(eye: np.ndarray, target: np.ndarray, up=(0, 0, 1)) -> np.ndarray:
    """World->camera rotation (rows are camera axes) for a camera at `eye`."""
    eye = np.asarray(eye, float); target = np.asarray(target, float); up = np.asarray(up, float)
    f = target - eye; f /= np.linalg.norm(f)        # forward (camera +z looks along f)
    r = np.cross(f, up); r /= np.linalg.norm(r)      # right (camera +x)
    u = np.cross(r, f)                               # down-ish (camera +y points down image)
    R = np.stack([r, -u, f], axis=0)                 # image y grows downward
    return R


@dataclass
class Camera:
    K: np.ndarray            # (3,3) intrinsics
    R: np.ndarray            # (3,3) world->camera rotation
    t: np.ndarray            # (3,)  world->camera translation (camera center C: t = -R C)
    width: int = 1280
    height: int = 720

    @property
    def center(self) -> np.ndarray:
        return -self.R.T @ self.t

    def project(self, pts_w: np.ndarray) -> np.ndarray:
        """World points (N,3) -> pixel coords (N,2). Points behind camera -> NaN."""
        pts_w = np.atleast_2d(pts_w)
        pc = (self.R @ pts_w.T + self.t[:, None]).T      # (N,3) camera coords
        z = pc[:, 2:3]
        uvw = (self.K @ pc.T).T
        uv = uvw[:, :2] / uvw[:, 2:3]
        uv[(z[:, 0] <= 0)] = np.nan
        return uv

    def ray(self, uv: np.ndarray) -> np.ndarray:
        """Pixel -> unit ray direction in world coords (from camera center)."""
        uv = np.atleast_2d(uv).astype(float)
        ones = np.ones((uv.shape[0], 1))
        d_cam = (np.linalg.inv(self.K) @ np.hstack([uv, ones]).T).T   # (N,3)
        d_world = (self.R.T @ d_cam.T).T
        return d_world / np.linalg.norm(d_world, axis=1, keepdims=True)


def make_courtside_camera(width=1280, height=720, hfov_deg=70.0,
                          height_m=4.0, behind_m=8.0, side_m=0.0) -> Camera:
    """A camera placed behind/above one baseline, looking down the court (+x).

    Defaults approximate a phone on a tripod a few metres behind the baseline.
    """
    f = (width / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
    K = np.array([[f, 0, width / 2.0], [0, f, height / 2.0], [0, 0, 1.0]])
    eye = np.array([-behind_m, side_m, height_m])
    target = np.array([11.885, 0.0, 0.5])     # look toward mid-court
    R = look_at(eye, target)
    t = -R @ eye
    return Camera(K=K, R=R, t=t, width=width, height=height)
