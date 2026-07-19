"""overlay.py — draw the court line set back onto frames (the visual proof).

Given a homography, project every court line (court.LINES) from metres into image
pixels with calibration.court_to_image and draw them on the frame. If the drawn
lines sit on the real court lines, the calibration is right. This is the Phase 1
acceptance check you can see with your eyes.

Also provides synthetic_court_image(), which renders a clean court from a known
homography — used by the tests (and handy for demos) to validate detection +
overlay without real footage.
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np

from . import calibration, court

# BGR colours (OpenCV order).
_LINE_COLOR = (60, 255, 255)   # yellow-ish, stands out on green/clay
_NET_COLOR = (230, 230, 230)
_DOT_COLOR = (40, 120, 255)    # orange landmarks


def _ipt(p) -> tuple[int, int]:
    return int(round(float(p[0]))), int(round(float(p[1])))


def draw_court(
    frame: np.ndarray,
    H: np.ndarray,
    color=_LINE_COLOR,
    thickness: int = 2,
    dots: bool = True,
    k1: float = 0.0,
) -> np.ndarray:
    """Draw the full court line set (and optionally the named landmarks) onto
    `frame` in place, using H to project court metres to pixels.

    When k1 != 0, H is taken to live in UNDISTORTED (pinhole) pixel space and
    every line is drawn as a polyline bent back through the lens
    (calibration.distort_points), so the overlay hugs the real, curved paint."""
    import cv2

    lens = abs(k1) > 1e-12
    for a, b in court.LINES:
        is_net = a[1] == court.NET_Y and b[1] == court.NET_Y
        col = _NET_COLOR if is_net else color
        if lens:
            ts = np.linspace(0.0, 1.0, 24)[:, None]
            line_m = np.asarray(a, float) + ts * (np.asarray(b, float) - np.asarray(a, float))
            pts = calibration.court_to_image(H, line_m)
            pts = calibration.distort_points(pts, k1, (frame.shape[1], frame.shape[0]))
            cv2.polylines(frame, [np.round(pts).astype(np.int32).reshape(-1, 1, 2)],
                          False, col, thickness, cv2.LINE_AA)
        else:
            p = calibration.court_to_image(H, [a])[0]
            q = calibration.court_to_image(H, [b])[0]
            cv2.line(frame, _ipt(p), _ipt(q), col, thickness, cv2.LINE_AA)
    if dots:
        for name, xy in court.LANDMARKS.items():
            p = calibration.court_to_image(H, [xy])[0]
            if lens:
                p = calibration.distort_points([p], k1, (frame.shape[1], frame.shape[0]))[0]
            cv2.circle(frame, _ipt(p), max(3, thickness + 1), _DOT_COLOR, -1, cv2.LINE_AA)
    return frame


def synthetic_court_image(
    H: np.ndarray,
    width: int = 1280,
    height: int = 720,
    surface=(70, 120, 60),
    line=(245, 245, 245),
    thickness: int = 3,
) -> np.ndarray:
    """Render a clean court onto a blank surface from a known homography. Used to
    validate detection/overlay without real video."""
    img = np.full((height, width, 3), surface, dtype=np.uint8)
    draw_court(img, H, color=line, thickness=thickness, dots=False)
    return img


def _load_frame(src: Union[str, np.ndarray]) -> np.ndarray:
    import cv2

    if isinstance(src, np.ndarray):
        return src.copy()
    img = cv2.imread(src)
    if img is None:
        raise FileNotFoundError(f"could not read image: {src!r}")
    return img


def render_overlay_image(
    src: Union[str, np.ndarray], H: np.ndarray, out_path: str, **kw
) -> str:
    """Draw the court overlay on a single image and write it to out_path."""
    import cv2

    img = _load_frame(src)
    draw_court(img, H, **kw)
    cv2.imwrite(out_path, img)
    return out_path


def render_overlay_video(
    video_path: str,
    H: np.ndarray,
    out_path: str,
    max_frames: Optional[int] = None,
    **kw,
) -> str:
    """Draw the court overlay on every frame of a video and write an annotated
    preview. A fixed camera means one H works for the whole clip."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path!r}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    try:
        n = 0
        while True:
            ok, frame = cap.read()
            if not ok or (max_frames is not None and n >= max_frames):
                break
            draw_court(frame, H, **kw)
            writer.write(frame)
            n += 1
    finally:
        cap.release()
        writer.release()
    return out_path
