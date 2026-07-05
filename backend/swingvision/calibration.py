"""Calibration: the homography solve + projection (geometry, TESTED) and the
court-keypoint detector (ML, STUBBED).

The dividing line matters (see CLAUDE.md):
  - compute_homography / court_to_image / image_to_court are exact closed-form
    math. They are tested and must not be replaced with a model.
  - detect_court_keypoints is perception. It reads messy pixels. The classical
    baseline here (white-line mask -> Hough -> intersections -> template fit) is
    real; the seam to swap in a learned keypoint model is marked below.

A homography H is a 3x3 matrix mapping court-plane points (metres) to image
points (pixels) in homogeneous coordinates:

    [u, v, w]^T = H @ [x, y, 1]^T ,   pixel = (u/w, v/w)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

from . import court


def compute_homography(
    court_points: Sequence[Sequence[float]],
    image_points: Sequence[Sequence[float]],
) -> np.ndarray:
    """Solve the homography mapping court (metres) -> image (pixels).

    Uses the normalized Direct Linear Transform: each correspondence gives two
    rows of a 2N x 9 system, solved by SVD (the right singular vector of the
    smallest singular value). Points are conditioned first (Hartley
    normalization) for numerical stability, then the transform is undone.

    Requires at least 4 non-collinear correspondences. Returns H normalized so
    that H[2, 2] == 1.
    """
    src = np.asarray(court_points, dtype=np.float64)
    dst = np.asarray(image_points, dtype=np.float64)
    if src.shape != dst.shape or src.shape[0] < 4 or src.shape[1] != 2:
        raise ValueError("need >=4 matching (x, y) point pairs")

    T_src, src_n = _normalize(src)
    T_dst, dst_n = _normalize(dst)

    rows = []
    for (x, y), (u, v) in zip(src_n, dst_n):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    A = np.asarray(rows, dtype=np.float64)

    _, _, Vt = np.linalg.svd(A)
    H_n = Vt[-1].reshape(3, 3)

    # Undo normalization:  H = T_dst^-1 @ H_n @ T_src
    H = np.linalg.inv(T_dst) @ H_n @ T_src
    if abs(H[2, 2]) < 1e-12:
        raise ValueError("degenerate homography (H[2,2] ~ 0)")
    return H / H[2, 2]


def _normalize(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Hartley normalization: translate to centroid, scale to mean distance
    sqrt(2). Returns (T, normalized_pts) with pts_n = (T @ [x, y, 1])[:2]."""
    centroid = pts.mean(axis=0)
    shifted = pts - centroid
    mean_dist = np.sqrt((shifted ** 2).sum(axis=1)).mean()
    scale = np.sqrt(2.0) / mean_dist if mean_dist > 1e-12 else 1.0
    T = np.array(
        [[scale, 0, -scale * centroid[0]],
         [0, scale, -scale * centroid[1]],
         [0, 0, 1]],
        dtype=np.float64,
    )
    homog = np.column_stack([pts, np.ones(len(pts))])
    pts_n = (T @ homog.T).T[:, :2]
    return T, pts_n


def _apply(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply a homography to an (N, 2) array, returning (N, 2)."""
    homog = np.column_stack([pts, np.ones(len(pts))])
    out = (H @ homog.T).T
    return out[:, :2] / out[:, 2:3]


def court_to_image(H: np.ndarray, points: Sequence[Sequence[float]]) -> np.ndarray:
    """Project court-plane points (metres) to image pixels."""
    pts = np.atleast_2d(np.asarray(points, dtype=np.float64))
    return _apply(H, pts)


def image_to_court(H: np.ndarray, points: Sequence[Sequence[float]]) -> np.ndarray:
    """Back-project image pixels onto the court plane (metres) via H^-1."""
    pts = np.atleast_2d(np.asarray(points, dtype=np.float64))
    return _apply(np.linalg.inv(H), pts)


def camera_height_m(H: np.ndarray, img_wh: Sequence[float], hfov_deg: float = 70.0) -> Optional[float]:
    """Estimate the camera's height above the court plane (metres) from the
    calibration homography + an assumed horizontal field of view.

    Projects the four doubles corners through H, solves PnP against their known
    court positions (z=0 plane), and reads the camera position's vertical
    component. Matters because ball geometry changes regime with height: a HIGH
    camera (broadcast) bounds an airborne ball's ground projection near the court,
    while a LOW camera (phone at ~2 m) sends it tens of metres past — so
    court-plausibility gating is only sound when the camera is high. Returns None
    if OpenCV or the solve is unavailable.
    """
    try:
        import cv2

        from . import court as _court

        world, img = [], []
        for n in ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles"):
            cx, cy = _court.LANDMARKS[n]
            world.append([cx, cy, 0.0])
            img.append(court_to_image(H, [(cx, cy)])[0])
        world = np.asarray(world, dtype=np.float64)
        img = np.asarray(img, dtype=np.float64)
        w, h = float(img_wh[0]), float(img_wh[1])
        fx = (w / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
        K = np.array([[fx, 0, w / 2.0], [0, fx, h / 2.0], [0, 0, 1.0]])
        ok, rvec, tvec = cv2.solvePnP(world, img, K, None, flags=cv2.SOLVEPNP_IPPE)
        if not ok:
            return None
        R, _ = cv2.Rodrigues(rvec)
        cam = (-R.T @ tvec).ravel()
        return float(abs(cam[2]))
    except Exception:
        return None


def focal_from_homography(H: np.ndarray, img_wh: Sequence[float]) -> Optional[float]:
    """Self-calibrate the focal length (pixels) from the court homography.

    H maps the court plane to the image: H ~ K [r1 r2 t]. With square pixels and
    the principal point at the image centre, the rotation constraints r1·r2 = 0
    and |r1| = |r2| become two linear equations in 1/f² — the court itself is the
    calibration target, so no assumed field of view is needed (the assumed-hfov
    guess this replaces was the dominant error in the physics speed fit).
    Returns None when the view is degenerate (e.g. camera looking straight down,
    where the equations lose conditioning) or the solution is non-physical.
    """
    h = np.asarray(H, dtype=np.float64)
    cx, cy = float(img_wh[0]) / 2.0, float(img_wh[1]) / 2.0
    a1, b1, c1 = h[0, 0] - cx * h[2, 0], h[1, 0] - cy * h[2, 0], h[2, 0]
    a2, b2, c2 = h[0, 1] - cx * h[2, 1], h[1, 1] - cy * h[2, 1], h[2, 1]
    # Two residuals linear in w = 1/f²:  A·w + B = 0, solved least-squares.
    A = np.array([a1 * a2 + b1 * b2, (a1 * a1 + b1 * b1) - (a2 * a2 + b2 * b2)])
    B = np.array([c1 * c2, c1 * c1 - c2 * c2])
    denom = float(A @ A)
    if denom < 1e-12:
        return None
    w = float(-(A @ B) / denom)
    if w <= 1e-12:
        return None
    f = 1.0 / np.sqrt(w)
    # Sanity: implied hfov within anything a real camera/phone/broadcast uses.
    hfov = np.degrees(2.0 * np.arctan(float(img_wh[0]) / (2.0 * f)))
    if not (25.0 <= hfov <= 110.0):
        return None
    return float(f)


def court_scale_m_per_px(H: np.ndarray, image_xy: Sequence[float]) -> float:
    """Local court-plane sensitivity at an image point: metres of court motion per
    pixel of image error (the operator norm of d(image_to_court)/d(pixel)).

    On a camera behind one baseline this is small near the camera (~0.02 m/px) and
    grows toward the far baseline (~0.10 m/px) as the court grazes the horizon — so
    a few pixels of ball-centroid jitter there become decimetres of position error.
    Used to flag far-court speeds/line-calls as low-confidence rather than report
    perspective-amplified noise as fact.
    """
    Hinv = np.linalg.inv(H)
    p = np.asarray(image_xy, dtype=np.float64)
    c0 = _apply(Hinv, p[None])[0]
    cx = _apply(Hinv, (p + [1.0, 0.0])[None])[0]
    cy = _apply(Hinv, (p + [0.0, 1.0])[None])[0]
    return float(max(np.hypot(*(cx - c0)), np.hypot(*(cy - c0))))


def reprojection_error(
    H: np.ndarray,
    court_points: Sequence[Sequence[float]],
    image_points: Sequence[Sequence[float]],
) -> float:
    """Mean Euclidean pixel error between projected court points and the given
    image points. The headline calibration-quality number."""
    projected = court_to_image(H, court_points)
    image = np.asarray(image_points, dtype=np.float64)
    return float(np.sqrt(((projected - image) ** 2).sum(axis=1)).mean())


def homography_from_landmarks(named_image_points: Mapping[str, Sequence[float]]) -> np.ndarray:
    """Convenience: build H from a {landmark_name: [x_px, y_px]} mapping using
    the canonical court coordinates in court.LANDMARKS. This is what the manual
    calibration JSON feeds into."""
    court_pts, image_pts = [], []
    for name, px in named_image_points.items():
        if name not in court.LANDMARKS:
            raise KeyError(f"unknown landmark {name!r}; see court.LANDMARKS")
        court_pts.append(court.LANDMARKS[name])
        image_pts.append(px)
    return compute_homography(court_pts, image_pts)


# --- Perception: court detection --------------------------------------------
# Classical baseline. A behind-the-baseline camera renders court lines as a set
# of near-horizontal lines (baselines, service lines) and near-vertical lines
# (sidelines, centre line). We mask the bright lines, find them with Hough,
# take horizontal x vertical intersections, anchor the four doubles corners to
# seed a homography, then refine against the full 14-point template.

COURT_DETECTION_MIN_CONFIDENCE = 0.5


@dataclass
class CourtDetection:
    """Result of court detection: the 14 named keypoints, the homography they
    induce, and a 0..1 confidence (fraction of template points that snapped to a
    real detected intersection)."""
    keypoints: dict[str, tuple[float, float]]
    homography: np.ndarray
    confidence: float


def white_line_mask(frame: np.ndarray) -> np.ndarray:
    """Binary mask of the court lines.

    Court lines are thin bright structures on a darker, roughly-uniform surface.
    A white tophat (image minus its morphological opening) isolates exactly that
    — thin and bright — and suppresses the surface regardless of its colour,
    which a global brightness threshold cannot do. Otsu then splits line from
    background on the tophat response.
    """
    import cv2

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    ksize = max(9, int(round(frame.shape[1] * 0.012)) | 1)  # > line thickness, odd
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    if int(tophat.max()) < 15:
        return np.zeros_like(gray)  # no line-like structure
    _, mask = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    open_k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k)


def _hough_segments(mask: np.ndarray) -> list[tuple[float, float, float, float]]:
    import cv2

    w = mask.shape[1]
    lines = cv2.HoughLinesP(
        mask,
        rho=1,
        theta=np.pi / 180.0,
        threshold=60,
        minLineLength=int(w * 0.08),
        maxLineGap=int(w * 0.04),
    )
    if lines is None:
        return []
    # OpenCV returns (N,1,4) or (N,4) depending on version — normalize.
    return [tuple(map(float, r)) for r in np.asarray(lines).reshape(-1, 4)]


def _homog_line(seg) -> np.ndarray:
    """Homogeneous line through a segment's endpoints (l = p1 x p2)."""
    x1, y1, x2, y2 = seg
    return np.cross([x1, y1, 1.0], [x2, y2, 1.0])


def _intersect(l1: np.ndarray, l2: np.ndarray) -> Optional[tuple[float, float]]:
    p = np.cross(l1, l2)
    if abs(p[2]) < 1e-9:
        return None  # parallel
    return (p[0] / p[2], p[1] / p[2])


def _is_horizontalish(seg) -> bool:
    x1, y1, x2, y2 = seg
    ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
    return ang < 45.0 or ang > 135.0


def _cluster_lines(segs, horizontal: bool, shape) -> list[np.ndarray]:
    """Merge near-duplicate segments into distinct court lines, keyed by where
    they cross the image's mid-axis so we can later pick the extremes."""
    h, w = shape[:2]
    keyed: list[tuple[float, np.ndarray]] = []
    for seg in segs:
        l = _homog_line(seg)
        if horizontal:
            ref = _intersect(l, _homog_line((w / 2, 0, w / 2, h)))  # x = w/2
            key = ref[1] if ref else None  # image-y at mid width
        else:
            ref = _intersect(l, _homog_line((0, h / 2, w, h / 2)))  # y = h/2
            key = ref[0] if ref else None  # image-x at mid height
        if key is not None and 0 <= (key if horizontal else key) <= (h if horizontal else w):
            keyed.append((key, l))
    keyed.sort(key=lambda t: t[0])

    merged: list[tuple[float, np.ndarray]] = []
    tol = (h if horizontal else w) * 0.02
    for key, l in keyed:
        if merged and abs(key - merged[-1][0]) < tol:
            continue  # same line as the previous cluster
        merged.append((key, l))
    return [l for _, l in merged]


def detect_court(frame: np.ndarray) -> Optional[CourtDetection]:
    """Classical court detection. Returns a CourtDetection or None if the line
    structure is too weak to anchor a homography.

    --- LEARNED-MODEL SEAM ---
    To swap in a trained court-keypoint network, replace the body up to the
    `compute_homography` calls with: run the model, read off the named landmark
    pixels, and build `named` from them. The refine + confidence logic below can
    stay. Keep the return type (CourtDetection) so callers don't change.
    """
    segs = _hough_segments(white_line_mask(frame))
    horiz = _cluster_lines([s for s in segs if _is_horizontalish(s)], True, frame.shape)
    vert = _cluster_lines([s for s in segs if not _is_horizontalish(s)], False, frame.shape)
    if len(horiz) < 2 or len(vert) < 2:
        return None

    # Extremes of each family bound the doubles court.
    far_baseline, near_baseline = horiz[0], horiz[-1]   # smallest / largest image-y
    left_double, right_double = vert[0], vert[-1]        # smallest / largest image-x

    corners = {
        "near_bl_doubles": _intersect(near_baseline, left_double),
        "near_br_doubles": _intersect(near_baseline, right_double),
        "far_bl_doubles": _intersect(far_baseline, left_double),
        "far_br_doubles": _intersect(far_baseline, right_double),
    }
    if any(c is None for c in corners.values()):
        return None

    # Seed a homography from the four corners.
    court_pts = [court.LANDMARKS[n] for n in corners]
    image_pts = [corners[n] for n in corners]
    try:
        H0 = compute_homography(court_pts, image_pts)
    except (ValueError, np.linalg.LinAlgError):
        return None

    # All detected intersections, for snapping the projected template onto real
    # line crossings (refinement).
    detected = [
        pt
        for lh in horiz
        for lv in vert
        if (pt := _intersect(lh, lv)) is not None
    ]
    detected_arr = np.array(detected) if detected else np.empty((0, 2))

    names = court.landmark_names()
    snap_radius = frame.shape[1] * 0.03
    named: dict[str, tuple[float, float]] = {}
    matched = 0
    for name in names:
        proj = court_to_image(H0, [court.LANDMARKS[name]])[0]
        if len(detected_arr):
            d = np.hypot(detected_arr[:, 0] - proj[0], detected_arr[:, 1] - proj[1])
            j = int(np.argmin(d))
            if d[j] <= snap_radius:
                named[name] = (float(detected_arr[j, 0]), float(detected_arr[j, 1]))
                matched += 1
                continue
        named[name] = (float(proj[0]), float(proj[1]))

    # Refit over all 14 snapped/projected points for a stable homography.
    H = compute_homography([court.LANDMARKS[n] for n in names], [named[n] for n in names])
    confidence = matched / len(names)
    return CourtDetection(keypoints=named, homography=H, confidence=confidence)


def detect_court_keypoints(
    frame: np.ndarray, min_confidence: float = COURT_DETECTION_MIN_CONFIDENCE
) -> Optional[dict[str, tuple[float, float]]]:
    """Detect the 14 named court keypoints in a frame.

    Returns a {landmark_name: (x_px, y_px)} mapping, or None when detection is
    low-confidence — the caller then falls back to a manual calibration JSON.
    """
    det = detect_court(frame)
    if det is None or det.confidence < min_confidence:
        return None
    return det.keypoints


# --- Homography refinement (snap the overlay onto the real lines) ------------
def refine_homography_bounded(frame: np.ndarray, named_points, max_move_px: float = 35.0,
                              boxes=None):
    """Snap a rough 4-corner calibration onto the white lines — BOUNDED.

    The unbounded refine_homography collapses to degenerate solutions (it will
    happily fold the court onto any bright edges). This version optimises the four
    corner pixels within ±max_move_px of the manual guess, which keeps the
    solution in the basin of the true court while letting every projected line
    (baselines, service lines, centre line, sidelines) pull the corners into
    place — the same many-constraint effect the learned 14-keypoint model gives
    broadcast footage. Returns (H, refined_named_points, mean_dt_cost).
    """
    import cv2
    from scipy.optimize import minimize

    names = list(named_points.keys())
    court_pts = [court.LANDMARKS[n] for n in names]
    x0 = np.asarray([named_points[n] for n in names], dtype=np.float64).ravel()

    mask = white_line_mask(frame)
    for b in boxes or []:
        if b is None:
            continue
        bx1, by1, bx2, by2 = (int(v) for v in b)
        mask[max(0, by1):by2, max(0, bx1):bx2] = 0
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    dt = np.minimum(dt, 25.0)
    h, w = mask.shape
    samples = _sample_court_lines(step_m=0.3)

    def cost(x):
        try:
            H = compute_homography(court_pts, x.reshape(-1, 2))
        except Exception:
            return 25.0
        pts = court_to_image(H, samples)
        xs = np.clip(pts[:, 0], 0, w - 1).astype(int)
        ys = np.clip(pts[:, 1], 0, h - 1).astype(int)
        inside = (pts[:, 0] >= -40) & (pts[:, 0] < w + 40) & (pts[:, 1] >= 0) & (pts[:, 1] < h)
        if inside.sum() < len(pts) * 0.5:
            return 25.0
        return float(dt[ys[inside], xs[inside]].mean())

    bounds = [(v - max_move_px, v + max_move_px) for v in x0]
    res = minimize(cost, x0, method="Nelder-Mead", bounds=bounds,
                   options={"maxiter": 3000, "xatol": 0.2, "fatol": 0.005})
    x = res.x
    refined = {n: [float(x[2 * i]), float(x[2 * i + 1])] for i, n in enumerate(names)}
    return compute_homography(court_pts, x.reshape(-1, 2)), refined, float(res.fun)


def court_lock_step(frame: np.ndarray, H_prev: np.ndarray, boxes=None,
                    max_shift_px: float = 14.0, max_scale: float = 0.03,
                    max_rot_deg: float = 1.2):
    """Track the court between frames by SNAPPING the previous homography onto the
    white lines of the current frame (small bounded similarity correction).

    Global motion estimators fail on consumer footage — burned-in UI graphics
    (scoreboards, watermarks) dominate both sparse features and dense gradient
    correlation, reporting "no motion" while a virtual camera pans/zooms the scene.
    Tracking the court's own lines side-steps that entirely: the cost is the mean
    distance-transform value sampled along the projected court lines, minimised
    over [tx, ty, log-scale, rotation] around the court's image centre, seeded at
    identity and hard-bounded so it can only make small per-frame corrections
    (never the degenerate collapse a blind line-snap can produce). Returns
    (A_step 3x3 image-space correction, cost) — identity when no improvement.
    """
    import cv2
    from scipy.optimize import minimize

    mask = white_line_mask(frame)
    for b in boxes or []:
        if b is None:
            continue
        x1, y1, x2, y2 = (int(v) for v in b)
        mask[max(0, y1):y2, max(0, x1):x2] = 0
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    dt = np.minimum(dt, 30.0)
    h, w = mask.shape

    samples = _sample_court_lines()
    base = court_to_image(H_prev, samples)   # (N,2) current-guess line pixels
    centre = base.mean(axis=0)

    def apply_params(p):
        tx, ty, ls, rot = p
        s = math.exp(ls)
        c, sn = math.cos(rot), math.sin(rot)
        pts = base - centre
        out = np.empty_like(pts)
        out[:, 0] = s * (c * pts[:, 0] - sn * pts[:, 1]) + centre[0] + tx
        out[:, 1] = s * (sn * pts[:, 0] + c * pts[:, 1]) + centre[1] + ty
        return out

    def cost(p):
        pts = apply_params(p)
        xs = np.clip(pts[:, 0], 0, w - 1).astype(int)
        ys = np.clip(pts[:, 1], 0, h - 1).astype(int)
        inside = (pts[:, 0] >= 0) & (pts[:, 0] < w) & (pts[:, 1] >= 0) & (pts[:, 1] < h)
        if inside.sum() < len(pts) * 0.3:
            return 30.0
        return float(dt[ys[inside], xs[inside]].mean())

    c0 = cost([0, 0, 0, 0])
    res = minimize(cost, [0.0, 0.0, 0.0, 0.0], method="Nelder-Mead",
                   options={"maxiter": 80, "xatol": 0.05, "fatol": 0.01})
    tx, ty, ls, rot = res.x
    if (res.fun >= c0 - 1e-3 or abs(tx) > max_shift_px or abs(ty) > max_shift_px
            or abs(ls) > max_scale or abs(rot) > math.radians(max_rot_deg)):
        return np.eye(3), c0
    s = math.exp(ls)
    c, sn = math.cos(rot), math.sin(rot)
    # Image-space similarity about `centre`, then translation.
    T1 = np.array([[1, 0, -centre[0]], [0, 1, -centre[1]], [0, 0, 1.0]])
    R = np.array([[s * c, -s * sn, 0], [s * sn, s * c, 0], [0, 0, 1.0]])
    T2 = np.array([[1, 0, centre[0] + tx], [0, 1, centre[1] + ty], [0, 0, 1.0]])
    return T2 @ R @ T1, float(res.fun)


def _sample_court_lines(step_m: float = 0.4) -> np.ndarray:
    """Dense points along every court line, in court metres."""
    pts: list[tuple[float, float]] = []
    for (a, b) in court.LINES:
        n = max(2, int(math.dist(a, b) / step_m))
        for t in np.linspace(0.0, 1.0, n):
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return np.asarray(pts, dtype=np.float64)


def refine_homography(
    frame: np.ndarray,
    named_points: Mapping[str, Sequence[float]],
    max_dist: float = 35.0,
):
    """Refine a rough manual calibration by snapping it onto the detected lines.

    Hand-clicked corners are imprecise, so the projected court drifts off the real
    lines. This optimises the corner image positions so the *projected* court lines
    land on the white-line pixels: it builds a distance transform of the line mask
    (0 on a line, growing away) and minimises the average distance sampled along
    the projected lines. Starting from the rough corners, it converges to the
    nearest true alignment.

    Returns (H, refined_named_points, residual_px). `residual_px` is the mean
    distance of the projected lines to the nearest real line pixel (lower = tighter).
    """
    import cv2
    from scipy.optimize import minimize

    names = list(named_points.keys())
    court_pts = [court.LANDMARKS[n] for n in names]
    x0 = np.asarray([named_points[n] for n in names], dtype=np.float64).ravel()

    mask = white_line_mask(frame)
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    dt = np.minimum(dt, max_dist)
    h, w = mask.shape
    samples = _sample_court_lines()

    def cost(x: np.ndarray) -> float:
        img_pts = x.reshape(-1, 2)
        try:
            H = compute_homography(court_pts, img_pts)
        except (ValueError, np.linalg.LinAlgError):
            return 1e6
        proj = court_to_image(H, samples)
        xs = proj[:, 0]
        ys = proj[:, 1]
        off = (xs < 0) | (xs >= w) | (ys < 0) | (ys >= h)
        xi = np.clip(xs, 0, w - 1).astype(np.intp)
        yi = np.clip(ys, 0, h - 1).astype(np.intp)
        c = dt[yi, xi].astype(np.float64)
        c[off] = max_dist
        return float(c.mean())

    res = minimize(cost, x0, method="Nelder-Mead",
                   options={"maxiter": 4000, "xatol": 0.25, "fatol": 0.005})
    refined = res.x.reshape(-1, 2)
    out = {n: [float(refined[i, 0]), float(refined[i, 1])] for i, n in enumerate(names)}
    H = compute_homography(court_pts, [out[n] for n in names])
    return H, out, float(res.fun)


# --- Learned court-keypoint model (the accurate calibration) ----------------
# The 14 model output channels, in order, mapped to our named landmarks. The
# model (yastrebksv/TennisCourtDetector) predicts these in image space; the
# mapping holds for any behind-the-baseline view (far baseline at image top).
COURT_KP_LANDMARKS = [
    "far_bl_doubles", "far_br_doubles", "near_bl_doubles", "near_br_doubles",
    "far_bl_singles", "near_bl_singles", "far_br_singles", "near_br_singles",
    "far_sl_left", "far_sl_right", "near_sl_left", "near_sl_right",
    "far_t", "near_t",
]
_COURT_MODEL = None


def _hough_peak(heatmap, low_thresh=170, min_radius=10, max_radius=25):
    """Peak of one keypoint heatmap (640x360 space), or (None, None)."""
    import cv2

    _, hm = cv2.threshold(heatmap, low_thresh, 255, cv2.THRESH_BINARY)
    circles = cv2.HoughCircles(hm, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                               param1=50, param2=2, minRadius=min_radius, maxRadius=max_radius)
    if circles is not None:
        return float(circles[0][0][0]), float(circles[0][0][1])
    return None, None


def _line_intersection(l1, l2):
    """Intersection of two segments (x1,y1,x2,y2), or None if near-parallel."""
    x1, y1, x2, y2 = l1
    x3, y3, x4, y4 = l2
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(d) < 1e-6:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / d
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / d
    return px, py


def _merge_lines(lines, tol=20.0):
    """Merge near-duplicate Hough segments (port of the repo's merge_lines)."""
    from scipy.spatial import distance

    lines = sorted(lines, key=lambda it: it[0])
    mask = [True] * len(lines)
    merged = []
    for i, line in enumerate(lines):
        if not mask[i]:
            continue
        for j, s in enumerate(lines[i + 1:]):
            if mask[i + j + 1]:
                if (distance.euclidean(line[:2], s[:2]) < tol
                        and distance.euclidean(line[2:], s[2:]) < tol):
                    line = [(line[0] + s[0]) / 2, (line[1] + s[1]) / 2,
                            (line[2] + s[2]) / 2, (line[3] + s[3]) / 2]
                    mask[i + j + 1] = False
        merged.append(line)
    return merged


def _refine_keypoint(frame, x, y, crop=40):
    """Sub-pixel keypoint refinement: in a small window around (x, y), find the
    two court lines and return their intersection (port of refine_kps)."""
    import cv2

    h, w = frame.shape[:2]
    x, y = int(x), int(y)
    x0, x1 = max(x - crop, 0), min(w, x + crop)
    y0, y1 = max(y - crop, 0), min(h, y + crop)
    sub = frame[y0:y1, x0:x1]
    if sub.size == 0:
        return x, y
    gray = cv2.threshold(cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY), 155, 255, cv2.THRESH_BINARY)[1]
    lines = cv2.HoughLinesP(gray, 1, np.pi / 180, 30, minLineLength=10, maxLineGap=30)
    if lines is None or len(lines) < 2:
        return x, y
    # OpenCV returns (N,1,4) or (N,4) depending on version — normalize.
    rows = np.asarray(lines).reshape(-1, 4)
    merged = _merge_lines([list(map(float, r)) for r in rows])
    if len(merged) == 2:
        inter = _line_intersection(merged[0], merged[1])
        if inter and 0 < inter[0] < (x1 - x0) and 0 < inter[1] < (y1 - y0):
            return x0 + inter[0], y0 + inter[1]
    return x, y


def detect_court_learned(
    frame: np.ndarray,
    weights: str = "weights/court_detector.pt",
    device: str = "cpu",
    min_points: int = 6,
) -> Optional[CourtDetection]:
    """Detect the court with the learned keypoint model (the accurate path).

    Runs the heatmap CNN, decodes up to 14 court keypoints, maps them to the
    named landmarks, and solves the homography. Returns None if too few keypoints
    are confidently found (then fall back to manual / classical).
    """
    import cv2
    import torch

    global _COURT_MODEL
    if _COURT_MODEL is None:
        from ._courtnet import CourtNet
        m = CourtNet(out_channels=15)
        # Prefer the fine-tuned checkpoint (train_courtnet.py — broadcast model
        # adapted to our amateur angles) when it exists; the reprojection gate
        # downstream still self-rejects any bad fit, so this stays safe.
        ft = os.path.join(os.path.dirname(weights), "courtnet_ft.pt")
        chosen = ft if os.path.exists(ft) else weights
        m.load_state_dict(torch.load(chosen, map_location=device))
        print(f"[calibration] court model: {os.path.basename(chosen)}")
        _COURT_MODEL = m.eval().to(device)

    h_img, w_img = frame.shape[:2]
    img = cv2.resize(frame, (640, 360)).astype(np.float32) / 255.0
    inp = torch.from_numpy(np.rollaxis(img, 2, 0)).unsqueeze(0).float().to(device)
    with torch.no_grad():
        pred = torch.sigmoid(_COURT_MODEL(inp)[0]).cpu().numpy()  # (15, 360, 640)

    import cv2

    # Service-line points (far_sl_left/right, far_t) refine poorly — skip those.
    no_refine = {8, 9, 12}
    named: dict[str, tuple[float, float]] = {}
    for i in range(14):
        hm = pred[i]
        cx, cy = _hough_peak((hm * 255).astype(np.uint8))  # sub-pixel via Hough
        if cx is None:
            py, px = np.unravel_index(int(hm.argmax()), hm.shape)
            if hm[py, px] < 0.40:
                continue
            cx, cy = float(px), float(py)
        x = cx * w_img / 640.0
        y = cy * h_img / 360.0
        if i not in no_refine:  # sub-pixel refine on the full-res frame
            x, y = _refine_keypoint(frame, x, y)
        named[COURT_KP_LANDMARKS[i]] = (float(x), float(y))

    if len(named) < min_points:
        return None
    names = list(named)
    src = np.array([court.LANDMARKS[n] for n in names], dtype=np.float64)
    dst = np.array([named[n] for n in names], dtype=np.float64)

    # Robust fit: RANSAC rejects keypoints the model mislocated; refit the final
    # homography with the tested DLT solver on the inliers only.
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 8.0)
    if mask is None:
        return None
    inl = mask.ravel().astype(bool)
    if int(inl.sum()) < min_points:
        return None
    H = compute_homography(src[inl], dst[inl])
    err = reprojection_error(H, src[inl], dst[inl])
    if err > 0.015 * max(w_img, h_img):
        return None
    kept = {n: named[n] for n, keep in zip(names, inl) if keep}
    return CourtDetection(keypoints=kept, homography=H, confidence=len(kept) / 14.0)
