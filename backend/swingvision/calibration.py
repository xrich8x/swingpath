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
    frame: np.ndarray, min_confidence: float = COURT_DETECTION_MIN_CONFIDENCE,
    verify: bool = True,
) -> Optional[dict[str, tuple[float, float]]]:
    """Detect the 14 named court keypoints in a frame.

    Returns a {landmark_name: (x_px, y_px)} mapping, or None when detection is
    low-confidence OR fails the white-line self-check (verify_court) — the caller
    then falls back to a manual calibration JSON instead of trusting a court that
    isn't on the real lines.
    """
    det = detect_court(frame)
    if det is None or det.confidence < min_confidence:
        return None
    if verify and not verify_court(frame, det.homography).ok:
        return None
    return det.keypoints


# --- White-line self-check: is a candidate court real, and is it the right one? ---
@dataclass
class CourtCheck:
    """Verdict from verify_court. `ok` is the accept/refuse gate."""
    ok: bool
    coverage: float       # fraction of the visible projected court lines on white
    centrality: float     # 0..1, 1 = court centre projects to the frame centre
    visible_frac: float   # fraction of the projected court that is inside the frame


_COURT_LINE_SAMPLES: Optional[np.ndarray] = None


def _court_line_samples(per_metre: float = 3.0) -> np.ndarray:
    """Points sampled densely along every court line, in metres (cached).

    This is the rigid tennis-court template — projecting ALL of it means we know
    where each line SHOULD be even where the real paint is faded, cracked, or
    occluded. Coverage below then measures how much of that shape the image
    actually supports; it never needs a line to be unbroken.
    """
    global _COURT_LINE_SAMPLES
    if _COURT_LINE_SAMPLES is None:
        pts = []
        for a, b in court.LINES:
            seglen = math.hypot(b[0] - a[0], b[1] - a[1])
            n = max(2, int(seglen * per_metre))
            for t in np.linspace(0.0, 1.0, n):
                pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        _COURT_LINE_SAMPLES = np.asarray(pts, dtype=np.float64)
    return _COURT_LINE_SAMPLES


def line_ridge_mask(frame: np.ndarray, tau: int = 9, sat_max: int = 90) -> np.ndarray:
    """White-line mask robust to amateur/indoor lighting (used by the self-check).

    A court line is a bright RIDGE: brighter than the surface a few pixels to its
    left+right, OR above+below, by `tau`. That test is invariant to global
    brightness, so it survives dim indoor courts and bright ceilings where the
    tophat+global-Otsu `white_line_mask` collapses. A low-saturation constraint
    (S < sat_max) keeps genuine white lines and drops coloured ridges (fence bars,
    court-colour seams). Line width scales with frame width.

    tau=9 (was 18): the higher bar missed faint/compressed amateur lines, so
    correct courts on some clips scored near-zero coverage and were wrongly
    refused. A tau sweep on the gold set showed 9 recovers those clips
    (e.g. am_classB 0.20->0.63, am_ntrp30 0.60->0.87) while a wrong court's
    coverage rises only ~0.27->0.34 — still clear of the 0.40 accept gate.
    """
    import cv2

    d = max(2, int(round(frame.shape[1] * 0.006)))   # ~ line half-width
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.int16)
    sat = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 1]

    def sh(a, dx, dy):
        return np.roll(np.roll(a, dy, axis=0), dx, axis=1)

    bright_h = (gray - sh(gray, d, 0) > tau) & (gray - sh(gray, -d, 0) > tau)
    bright_v = (gray - sh(gray, 0, d) > tau) & (gray - sh(gray, 0, -d) > tau)
    mask = ((bright_h | bright_v) & (sat < sat_max)).astype(np.uint8) * 255
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)))


def court_line_coverage(frame: np.ndarray, H: np.ndarray,
                        tol_px: Optional[float] = None) -> tuple[float, float]:
    """(coverage, visible_frac) for a candidate court.

    coverage     = fraction of the IN-FRAME projected court lines that land within
                   tol_px of a real white-line pixel.
    visible_frac = fraction of the whole projected court that is inside the frame
                   (amateur courts often run off the edge; only the visible part
                   can be checked).
    """
    import cv2

    mask = line_ridge_mask(frame)
    h, w = mask.shape[:2]
    if tol_px is None:
        tol_px = max(2.0, w * 0.006)
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    return _coverage_from_dt(dt, H, w, h, tol_px)


def _coverage_from_dt(dt: np.ndarray, H: np.ndarray, w: int, h: int,
                      tol_px: float) -> tuple[float, float]:
    """coverage, visible_frac for H against a precomputed distance-to-line map.
    Separated so a candidate search can score many courts on ONE distance map."""
    img = court_to_image(H, _court_line_samples())
    x = np.round(img[:, 0]).astype(int)
    y = np.round(img[:, 1]).astype(int)
    inb = (x >= 0) & (x < w) & (y >= 0) & (y < h)
    n = int(inb.sum())
    if n == 0:
        return 0.0, 0.0
    on = dt[y[inb], x[inb]] <= tol_px
    return float(on.sum()) / n, n / len(img)


def court_centrality(frame: np.ndarray, H: np.ndarray) -> float:
    """1.0 when the court centre (net midpoint) projects to the frame centre,
    dropping to 0 at the corners / off-frame. A real main court sits centrally;
    a background or adjacent court projects off to the side."""
    h, w = frame.shape[:2]
    c = court_to_image(H, [(court.DOUBLES_WIDTH / 2.0, court.NET_Y)])[0]
    dx = (c[0] - w / 2.0) / (w / 2.0)
    dy = (c[1] - h / 2.0) / (h / 2.0)
    return float(max(0.0, 1.0 - math.hypot(dx, dy) / math.sqrt(2.0)))


def verify_court(frame: np.ndarray, H: np.ndarray, *,
                 min_coverage: float = 0.40, min_visible: float = 0.30,
                 min_centrality: float = 0.70,
                 tol_px: Optional[float] = None) -> CourtCheck:
    """Accept/refuse a candidate court against the real white lines.

    Guards two failure modes the reprojection/keypoint-count gates miss:
      * a self-consistent but WRONG court that doesn't lie on any white lines
        (low coverage), and
      * a lock onto a real but OFF-CENTRE background/adjacent court (low
        centrality).
    """
    cov, vis = court_line_coverage(frame, H, tol_px)
    cen = court_centrality(frame, H)
    ok = cov >= min_coverage and vis >= min_visible and cen >= min_centrality
    return CourtCheck(ok=ok, coverage=cov, centrality=cen, visible_frac=vis)


# --- Guided-framing setup (SwingVision-style: control the input, not the model) ---
_DBL_CORNERS = ("far_bl_doubles", "far_br_doubles",
                "near_bl_doubles", "near_br_doubles")
_CORNER_PRETTY = {"far_bl_doubles": "far-left", "far_br_doubles": "far-right",
                  "near_bl_doubles": "near-left", "near_br_doubles": "near-right"}


@dataclass
class FramingReport:
    """Plain-English quality grade of a court setup, so the app can guide framing
    (SwingVision's approach: require a canonical full-court view rather than solve
    detection from any angle). `level` is good | warn | poor."""
    level: str
    corners_visible: int      # of the 4 doubles corners, how many are inside the frame
    centrality: float         # court centred in the frame (1 = dead centre)
    coverage: float           # lines land on real white pixels
    elevation: float          # far/near baseline width ratio; low => flat/low camera
    messages: list

    @property
    def ok(self) -> bool:
        return self.level == "good"


def framing_report(frame: np.ndarray, H: np.ndarray, *,
                   min_coverage: float = 0.40, min_centrality: float = 0.60,
                   min_elevation: float = 0.28) -> FramingReport:
    """Grade how well a clip is framed for reliable analysis, given a court
    calibration H (auto-detected or manual). Checks SwingVision's canonical-setup
    requirements: all 4 corners in frame, court centred, camera high enough (the
    far half not crushed), and lines actually detectable. Returns actionable
    guidance. Runs on one frame, so it works both offline and (later) live.
    """
    h, w = frame.shape[:2]
    pts = {n: court_to_image(H, [court.LANDMARKS[n]])[0] for n in _DBL_CORNERS}
    visible = {n: (0 <= p[0] < w and 0 <= p[1] < h) for n, p in pts.items()}
    n_vis = sum(visible.values())
    cen = court_centrality(frame, H)
    cov, _ = court_line_coverage(frame, H)
    near_w = math.dist(pts["near_bl_doubles"], pts["near_br_doubles"])
    far_w = math.dist(pts["far_bl_doubles"], pts["far_br_doubles"])
    elev = far_w / near_w if near_w > 1 else 0.0

    msgs: list[str] = []
    if n_vis < 4:
        off = ", ".join(_CORNER_PRETTY[n] for n, ok in visible.items() if not ok)
        msgs.append(f"Corner(s) off-screen: {off} - zoom out or reposition so the "
                    f"whole court is in the frame.")
    if cen < min_centrality:
        msgs.append("Court is off-centre - aim the camera at the middle of the court.")
    if elev < min_elevation:
        msgs.append("Camera looks low/flat - mount it higher (~5 ft, behind the "
                    "baseline) so the far half isn't crushed.")
    if cov < min_coverage:
        msgs.append("Court lines are hard to detect - set the corners manually, or "
                    "improve lighting/framing.")

    if n_vis < 3:
        level = "poor"   # can't even see the court -> a real framing problem
    elif (n_vis == 4 and cen >= min_centrality and elev >= min_elevation
          and cov >= min_coverage):
        level = "good"
        msgs.insert(0, "Framing looks good - whole court visible, centred, lines clear.")
    else:
        level = "warn"   # usable, but a fixable issue (corner, angle, or faint lines)
    return FramingReport(level=level, corners_visible=n_vis, centrality=cen,
                         coverage=cov, elevation=elev, messages=msgs)


_AM_CORNER_NAMES = ("far_bl_doubles", "far_br_doubles",
                    "near_bl_doubles", "near_br_doubles")


def detect_court_amateur(frame: np.ndarray, max_lines: int = 6,
                         verify: bool = True) -> Optional[CourtDetection]:
    """Classical court detector for amateur footage (no weights).

    Detects white lines with the ridge mask, clusters them into candidate
    baselines (horizontal) and sidelines (vertical), then tries every pair x pair
    as the doubles-court bounds and keeps the candidate whose FULL projected
    template best lands on the lines AND sits centrally (coverage x centrality).

    This directly implements the two amateur asks:
      * "pick the central court, not a random one" — centrality is in the score,
        so a background/adjacent court loses to the main one;
      * "continue lines that cut off" — bounding lines are intersected
        analytically, so a corner that falls OUTSIDE the frame is still recovered
        as long as the two lines forming it are visible (heatmap models can't do
        this). The full-template score also disambiguates which lines are the
        court bounds vs the service/centre lines.

    Returns a CourtDetection (or None). `verify` applies the white-line
    self-check so a weak best-candidate is refused rather than trusted.
    """
    import cv2

    mask = line_ridge_mask(frame)
    h, w = mask.shape[:2]
    segs = _hough_segments(mask)
    horiz = _cluster_lines([s for s in segs if _is_horizontalish(s)], True, frame.shape)
    vert = _cluster_lines([s for s in segs if not _is_horizontalish(s)], False, frame.shape)
    if len(horiz) < 2 or len(vert) < 2:
        return None

    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    tol = max(2.0, w * 0.006)
    Hs, Vs = horiz[:max_lines], vert[:max_lines]
    court_pts = [court.LANDMARKS[n] for n in _AM_CORNER_NAMES]

    best: Optional[tuple[float, np.ndarray, float]] = None
    for i in range(len(Hs)):
        for j in range(i + 1, len(Hs)):           # Hs[i]=far (higher), Hs[j]=near
            for a in range(len(Vs)):
                for b in range(a + 1, len(Vs)):    # Vs[a]=left, Vs[b]=right
                    pts = [_intersect(Hs[i], Vs[a]), _intersect(Hs[i], Vs[b]),
                           _intersect(Hs[j], Vs[a]), _intersect(Hs[j], Vs[b])]
                    if any(p is None for p in pts):
                        continue
                    try:
                        H = compute_homography(court_pts, pts)
                    except (ValueError, np.linalg.LinAlgError):
                        continue
                    cov, vis = _coverage_from_dt(dt, H, w, h, tol)
                    if vis < 0.30:
                        continue
                    score = cov * court_centrality(frame, H)
                    if best is None or score > best[0]:
                        best = (score, H, cov)

    if best is None:
        return None
    _, H, cov = best
    if verify and not verify_court(frame, H).ok:
        return None
    names = court.landmark_names()
    named = {n: tuple(map(float, court_to_image(H, [court.LANDMARKS[n]])[0]))
             for n in names}
    return CourtDetection(keypoints=named, homography=H, confidence=cov)


# --- Homography refinement (snap the overlay onto the real lines) ------------
def refine_homography_bounded(frame: np.ndarray, named_points, max_move_px: float = 35.0,
                              boxes=None, mask_fn=None):
    """Snap a rough 4-corner calibration onto the white lines — BOUNDED.

    The unbounded refine_homography collapses to degenerate solutions (it will
    happily fold the court onto any bright edges). This version optimises the four
    corner pixels within ±max_move_px of the manual guess, which keeps the
    solution in the basin of the true court while letting every projected line
    (baselines, service lines, centre line, sidelines) pull the corners into
    place — the same many-constraint effect the learned 14-keypoint model gives
    broadcast footage. Returns (H, refined_named_points, mean_dt_cost).

    `mask_fn` selects the white-line detector (default white_line_mask, the
    tophat+Otsu classical one). Pass line_ridge_mask for amateur/indoor footage,
    where tophat+Otsu collapses — measured to snap rough clicks far tighter there.
    """
    import cv2
    from scipy.optimize import minimize

    names = list(named_points.keys())
    court_pts = [court.LANDMARKS[n] for n in names]
    x0 = np.asarray([named_points[n] for n in names], dtype=np.float64).ravel()

    mask = (mask_fn or white_line_mask)(frame)
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


def snap_to_lines(frame: np.ndarray, named, *, min_coverage: float = 0.40,
                  max_move_px: float = 30.0):
    """Snap a manual/auto court calibration onto the amateur white lines — GUARDED.

    Refines the four doubles corners so the projected court lines land on real
    white-line pixels (via the amateur-robust line_ridge_mask). Measured on the
    court gold set (tools/eval_court_snap.py): this roughly HALVES whole-court
    error on hard/indoor/rec courts (median ~12.8 -> ~5.9 px) and lifts line
    coverage ~0.48 -> ~0.79.

    The snap is KEPT only if it clears the coverage bar AND does not lower coverage
    vs the input. So on surfaces whose lines the white-line mask can't see (clay:
    dusty orange paint), coverage stays low, the snap is REFUSED, and the caller's
    original clicks are returned unchanged (safe fallback to manual, as documented).

    Returns (H, named_out, snapped: bool, cov_before, cov_after). On skip/refuse,
    named_out is the input `named` and H is built from it unchanged.
    """
    corners = {n: list(named[n]) for n in _DBL_CORNERS if n in named}
    if len(corners) < 4 or len(named) < 4:
        # Can't snap without the four corners; return H from the clicks if solvable.
        try:
            H_before = homography_from_landmarks(named)
            cov_before = court_line_coverage(frame, H_before)[0]
        except Exception:
            H_before, cov_before = None, 0.0
        return H_before, named, False, cov_before, cov_before
    H_before = homography_from_landmarks(named)
    cov_before = court_line_coverage(frame, H_before)[0]
    try:
        H_after, refined, _ = refine_homography_bounded(
            frame, corners, max_move_px=max_move_px, mask_fn=line_ridge_mask)
    except Exception:
        return H_before, named, False, cov_before, cov_before
    cov_after = court_line_coverage(frame, H_after)[0]
    if cov_after >= min_coverage and cov_after >= cov_before - 1e-6:
        return H_after, refined, True, cov_before, cov_after
    return H_before, named, False, cov_before, cov_after


def court_lock_step(frame: np.ndarray, H_prev: np.ndarray, boxes=None,
                    max_shift_px: float = 14.0, max_scale: float = 0.03,
                    max_rot_deg: float = 1.2, mask_fn=None,
                    min_shift_px: float = 0.6):
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

    KNOWN LIMITATION (verified 2026-07-11, synthetic pan): this reliably STABILISES
    a static camera (freezes to the calibration, 0 jitter) but does NOT track a
    sustained pan. The ridge dt landscape is shallow (a full 8px offset only moves
    the cost ~3.9->2.7), so the local Nelder-Mead optimiser stays near identity and
    the court drifts with the pan. Fine for amateur fixed-camera footage (the
    target); tracking panning/handheld/broadcast motion needs a stronger search
    (coarse-grid seed) or a peaked line-distance signal -- an open item.
    """
    import cv2
    from scipy.optimize import minimize

    mask = (mask_fn or line_ridge_mask)(frame)
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
    # Mean displacement this correction would apply to the court points. Below the
    # deadband it's jitter (or a static camera) -> freeze at identity so a locked
    # court never wobbles; only real motion (> min_shift_px) is tracked.
    disp = float(np.hypot(*(apply_params(res.x) - base).T).mean())
    if (res.fun >= c0 - 1e-3 or disp < min_shift_px
            or abs(tx) > max_shift_px or abs(ty) > max_shift_px
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


# Standard behind-the-baseline broadcast framing: the four doubles corners as
# fractions of (width, height). A fixed seed the line-snap refines per clip —
# broadcast cameras are similar enough that this converges without any manual
# click, which is what makes the PRO court path automatic.
BROADCAST_SEED_FRAC: dict[str, tuple[float, float]] = {
    "near_bl_doubles": (0.12, 0.93), "near_br_doubles": (0.88, 0.91),
    "far_bl_doubles": (0.28, 0.35), "far_br_doubles": (0.76, 0.34),
}


def line_coverage(frame: np.ndarray, H: np.ndarray, tol_px: float = 4.0) -> float:
    """Fraction of projected court-line points that land within tol_px of a real
    white-line pixel — an interpretable calibration self-check (1.0 = perfect).
    Used to ACCEPT or REFUSE an auto fit instead of emitting a wrong overlay."""
    import cv2

    mask = white_line_mask(frame)
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    h, w = mask.shape
    proj = court_to_image(H, _sample_court_lines())
    xs, ys = proj[:, 0], proj[:, 1]
    inside = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
    if inside.sum() == 0:
        return 0.0
    near = dt[ys[inside].astype(np.intp), xs[inside].astype(np.intp)] <= tol_px
    return float(near.sum()) / float(len(proj))   # off-frame points count as misses


def detect_court_broadcast(
    frame: np.ndarray, min_coverage: float = 0.6, tol_px: float = 5.0
) -> Optional["CourtDetection"]:
    """Automatic court calibration for PROFESSIONAL/broadcast footage (pro profile).

    Broadcast courts are a fixed high camera with clean, straight white lines —
    ideal for a line-snap fit. We seed a canonical behind-the-baseline framing
    (BROADCAST_SEED_FRAC), refine all four corners onto the detected white lines
    (refine_homography, reusing the ArtLabss-derived line helpers), then GATE on
    line_coverage: if too few projected lines land on real lines the fit is
    refused (returns None -> caller falls back to manual/learned) rather than
    emitting the kind of skewed overlay the classical detector produces here.
    """
    import cv2

    h_img, w_img = frame.shape[:2]
    seed = {n: [fx * w_img, fy * h_img]
            for n, (fx, fy) in BROADCAST_SEED_FRAC.items()}
    names = list(seed)
    H_seed = compute_homography([court.LANDMARKS[n] for n in names],
                                [seed[n] for n in names])
    # Restrict the line-snap to the court region (doubles rectangle + a small
    # margin, projected through the seed): otherwise the optimiser stretches a
    # corner out to grab white furniture just off court — the umpire chair, the
    # tramline extensions — which bulges the sideline (measured on Wimbledon).
    m, W, Ln = 1.6, court.DOUBLES_WIDTH, court.LENGTH
    poly = court_to_image(H_seed, [(-m, -m), (W + m, -m), (W + m, Ln + m), (-m, Ln + m)])
    roi = np.zeros((h_img, w_img), np.uint8)
    cv2.fillConvexPoly(roi, poly.astype(np.int32), 255)
    masked = frame.copy()
    masked[roi == 0] = 0
    H, refined, _ = refine_homography(masked, seed)
    cov = line_coverage(frame, H, tol_px=tol_px)   # scored on the real frame
    if cov < min_coverage:
        return None
    kpts = {n: tuple(float(v) for v in court_to_image(H, [court.LANDMARKS[n]])[0])
            for n in court.LANDMARKS}
    return CourtDetection(keypoints=kpts, homography=H, confidence=cov)


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
    verify: bool = True,
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
    if verify and not verify_court(frame, H).ok:
        return None   # self-consistent fit, but not on the real white lines / off-centre
    kept = {n: named[n] for n, keep in zip(names, inl) if keep}
    return CourtDetection(keypoints=kept, homography=H, confidence=len(kept) / 14.0)
