"""live.py — streaming line calls.

The offline pipeline analyzes a finished clip. This is the *live* path: feed it
frames one at a time (from a recording in progress, or a webcam) and it emits an
IN/OUT call the instant it detects a bounce — the SwingVision-style live call.

Line calls need only the BALL, not pose — so this drops the expensive player
model and streams just the ball, which is what makes near-real-time feasible.

  push_frame(frame, t)  -> runs the ball detector, returns a LineCall or None
  push_position(px, t)  -> same, but you supply the ball pixel (e.g. to replay a
                           cached track, or plug in a faster detector)

Bounce detection is online (a small fixed latency): a bounce is a local minimum
of the ball's court-plane speed. Single-camera bounces have no true height, so
this is a court-speed heuristic — calls are best-effort, as everywhere else.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

from . import analytics, calibration, court


@dataclass
class LineCall:
    t_s: float
    xy: list[float]            # bounce position, court metres
    call: str                  # "in" | "out"
    margin_m: float            # how far inside/outside the line (signed-ish, metres)


class LiveAnalyzer:
    """Streaming ball tracker + online bounce detector + live line caller.

    Calibrate once (fixed camera), then push frames in order. Designed to run
    alongside a live recording — call it as frames arrive.
    """

    def __init__(
        self,
        homography,
        singles: bool = True,
        line_margin_m: float = 0.05,
        min_speed_drop: float = 0.6,
        min_call_gap_s: float = 0.5,
    ) -> None:
        self.H = homography
        self.singles = singles
        self.line_margin_m = line_margin_m
        self.min_speed_drop = min_speed_drop
        self.min_call_gap_s = min_call_gap_s

        self._valid: list[tuple[float, float, float]] = []  # (t, x_m, y_m)
        self._seg: list[float] = []                          # court-plane speeds
        self._last_call_t: float = -1e9
        self.calls: list[LineCall] = []

    # -- streaming API -------------------------------------------------------
    def push_frame(self, frame, t_s: float, detector) -> Optional[LineCall]:
        """Detect the ball in `frame` and advance the stream."""
        return self.push_position(detector.detect(frame), t_s)

    def push_position(self, ball_px, t_s: float) -> Optional[LineCall]:
        """Advance the stream with a pre-detected ball pixel (or None)."""
        if ball_px is None:
            return None  # gap; bounce logic uses valid points only
        x, y = calibration.image_to_court(self.H, [ball_px])[0]
        self._valid.append((t_s, float(x), float(y)))
        if len(self._valid) >= 2:
            self._seg.append(self._speed(self._valid[-2], self._valid[-1]))
        return self._detect_bounce()

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _speed(a, b) -> float:
        dt = b[0] - a[0]
        if dt <= 0:
            return 0.0
        return math.dist((a[1], a[2]), (b[1], b[2])) / dt

    def _detect_bounce(self) -> Optional[LineCall]:
        # Need three segments to test the middle one for a local minimum.
        if len(self._seg) < 3:
            return None
        s_prev, s_cand, s_next = self._seg[-3], self._seg[-2], self._seg[-1]
        is_min = s_cand < s_prev and s_cand < s_next
        is_dip = s_cand < self.min_speed_drop * max(s_prev, s_next, 1e-9)
        if not (is_min and is_dip):
            return None
        # Candidate segment is (_valid[-3], _valid[-2]); call the bounce at _valid[-2].
        t, x, y = self._valid[-2]
        if t - self._last_call_t < self.min_call_gap_s:
            return None
        self._last_call_t = t

        in_bounds = (
            court.is_in_singles(x, y, self.line_margin_m)
            if self.singles
            else court.is_in_doubles(x, y, self.line_margin_m)
        )
        margin = self._distance_inside(x, y)
        call = LineCall(t_s=round(t, 2), xy=[round(x, 3), round(y, 3)],
                        call="in" if in_bounds else "out", margin_m=round(margin, 3))
        self.calls.append(call)
        return call

    def _distance_inside(self, x: float, y: float) -> float:
        """Signed distance to the nearest singles/doubles boundary (+ inside)."""
        xl = court.X_LEFT_SINGLES if self.singles else court.X_LEFT_DOUBLES
        xr = court.X_RIGHT_SINGLES if self.singles else court.X_RIGHT_DOUBLES
        dx = min(x - xl, xr - x)
        dy = min(y - court.Y_NEAR_BASELINE, court.Y_FAR_BASELINE - y)
        return min(dx, dy)


def _draw_overlay(frame, ball_px, flash):
    """Draw the live ball + the flashing IN/OUT call. `flash` = (LineCall, frames_left, bounce_px)."""
    import cv2

    if ball_px is not None:
        cv2.circle(frame, (int(ball_px[0]), int(ball_px[1])), 7, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "LIVE line calls", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    if flash:
        c, _, bp = flash
        color = (80, 220, 80) if c.call == "in" else (60, 60, 240)
        if bp is not None:
            cv2.circle(frame, (int(bp[0]), int(bp[1])), 16, color, 3, cv2.LINE_AA)
        cv2.putText(frame, c.call.upper(), (40, 112), cv2.FONT_HERSHEY_DUPLEX, 2.2, color, 5, cv2.LINE_AA)
        cv2.putText(frame, f"{c.margin_m:+.2f} m", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)


def stream(video, homography, ball_source, out_path=None, singles=True, on_call=None):
    """Drive the live line caller over a video/webcam.

    `video` is a path or "0" for a webcam. `ball_source(i, frame)` returns the
    ball pixel (or None) — pass a BallDetector.detect, a fast detector, or a
    cached lookup. Emits each LineCall to `on_call` as it fires, optionally writes
    an annotated video, and returns the list of calls.
    """
    import time

    import cv2

    cap = cv2.VideoCapture(0 if str(video) == "0" else video)
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open source: {video!r}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = (
        cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        if out_path else None
    )

    la = LiveAnalyzer(homography, singles=singles)
    flash = None
    i = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        ball_px = ball_source(i, frame)
        call = la.push_position(ball_px, i / fps)
        if call is not None:
            if on_call:
                on_call(call)
            bp = calibration.court_to_image(homography, [call.xy])[0]
            flash = (call, int(fps * 0.6), bp)
        _draw_overlay(frame, ball_px, flash)
        if flash:
            flash = (flash[0], flash[1] - 1, flash[2]) if flash[1] > 1 else None
        if writer is not None:
            writer.write(frame)
        i += 1
    cap.release()
    if writer is not None:
        writer.release()
    elapsed = time.time() - t0
    n_in = sum(c.call == "in" for c in la.calls)
    print(f"[live] {len(la.calls)} calls ({n_in} in / {len(la.calls) - n_in} out) "
          f"over {i} frames; {i / max(elapsed, 1e-9):.1f} fps processing")
    return la.calls
