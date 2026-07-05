"""Court geometry + court-plane <-> image homography.

World frame (matches the physics/camera modules):
    x along the court length, near baseline at x=0, far baseline at x=23.77 m
    y across the width, centre line at y=0
    z up, court plane at z=0
    net at x=11.885 m

In production, get the image keypoints from a learned detector
(e.g. yastrebksv/TennisCourtDetector: 14-point heatmap net + line-intersection
refinement). Here we provide the reference geometry and the homography math;
plug your detected pixels into `homography_from_points`.
"""
from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

LENGTH = 23.77
DOUBLES_HALF = 10.97 / 2.0       # 5.485
SINGLES_HALF = 8.23 / 2.0        # 4.115
NET_X = LENGTH / 2.0             # 11.885
SERVICE_FROM_NET = 6.40
SERVICE_NEAR_X = NET_X - SERVICE_FROM_NET   # 5.485
SERVICE_FAR_X = NET_X + SERVICE_FROM_NET    # 18.285

# Named keypoints on the court plane (x, y), z=0. Keys mirror common 14-point sets.
KEYPOINTS: dict[str, np.ndarray] = {
    "near_doubles_left":  np.array([0.0, +DOUBLES_HALF]),
    "near_doubles_right": np.array([0.0, -DOUBLES_HALF]),
    "far_doubles_left":   np.array([LENGTH, +DOUBLES_HALF]),
    "far_doubles_right":  np.array([LENGTH, -DOUBLES_HALF]),
    "near_singles_left":  np.array([0.0, +SINGLES_HALF]),
    "near_singles_right": np.array([0.0, -SINGLES_HALF]),
    "far_singles_left":   np.array([LENGTH, +SINGLES_HALF]),
    "far_singles_right":  np.array([LENGTH, -SINGLES_HALF]),
    "svc_near_left":      np.array([SERVICE_NEAR_X, +SINGLES_HALF]),
    "svc_near_right":     np.array([SERVICE_NEAR_X, -SINGLES_HALF]),
    "svc_far_left":       np.array([SERVICE_FAR_X, +SINGLES_HALF]),
    "svc_far_right":      np.array([SERVICE_FAR_X, -SINGLES_HALF]),
    "svc_near_center":    np.array([SERVICE_NEAR_X, 0.0]),
    "svc_far_center":     np.array([SERVICE_FAR_X, 0.0]),
}


def homography_from_points(image_pts: np.ndarray, world_pts: np.ndarray):
    """H mapping world-plane (x,y) -> image (u,v) using >=4 correspondences."""
    if cv2 is None:
        raise RuntimeError("OpenCV required for homography")
    image_pts = np.asarray(image_pts, np.float32)
    world_pts = np.asarray(world_pts, np.float32)
    H, _ = cv2.findHomography(world_pts, image_pts, cv2.RANSAC, 5.0)
    return H


def named_correspondences(image_kps: dict[str, np.ndarray]):
    """Pair detected named pixels with their reference world coords."""
    names = [n for n in image_kps if n in KEYPOINTS]
    img = np.array([image_kps[n] for n in names], np.float32)
    wld = np.array([KEYPOINTS[n] for n in names], np.float32)
    return img, wld


def image_to_ground(uv: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Map image points to the court plane (returns (N,3) with z=0).

    Only valid for points physically ON the plane (e.g. a bounce contact).
    """
    uv = np.atleast_2d(uv).astype(float)
    Hinv = np.linalg.inv(H)
    pts = np.hstack([uv, np.ones((len(uv), 1))])
    w = (Hinv @ pts.T).T
    xy = w[:, :2] / w[:, 2:3]
    return np.hstack([xy, np.zeros((len(xy), 1))])


def ground_to_image(xy: np.ndarray, H: np.ndarray) -> np.ndarray:
    xy = np.atleast_2d(xy).astype(float)
    pts = np.hstack([xy, np.ones((len(xy), 1))])
    uvw = (H @ pts.T).T
    return uvw[:, :2] / uvw[:, 2:3]
