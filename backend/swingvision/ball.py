"""ball.py — ball detection (ML, STUBBED) + trajectory smoothing (physics, REAL).

The detector is perception: pulling a fast, blurry, often-occluded ball out of
pixels is the make-or-break ML problem (a TrackNet checkpoint goes in detect()).
The smoothing is signal processing on the resulting noisy/gappy track — that part
is built and tested, because filling interpolated gaps is exactly what you do
once a real detector hands you broken trajectories.
"""

from __future__ import annotations

from collections import deque
from typing import Optional, Sequence

import numpy as np


def smooth_and_fill(
    positions: Sequence[Optional[Sequence[float]]],
    window: int = 7,
    polyorder: int = 2,
) -> np.ndarray:
    """Fill gaps and denoise a ball track.

    `positions` is a per-frame sequence where each item is an (x, y) pair or
    None for a frame the detector missed. Missing frames are linearly
    interpolated, then a Savitzky-Golay filter smooths the result (falling back
    gracefully when the track is too short to filter).

    Returns an (N, 2) float array with no gaps. Leading/trailing gaps are
    edge-filled by the interpolation.
    """
    n = len(positions)
    if n == 0:
        return np.zeros((0, 2), dtype=np.float64)

    xs = np.array([p[0] if p is not None else np.nan for p in positions], dtype=np.float64)
    ys = np.array([p[1] if p is not None else np.nan for p in positions], dtype=np.float64)
    xs = _interp_nan(xs)
    ys = _interp_nan(ys)

    w = _odd_window(window, n)
    if w >= polyorder + 2:
        from scipy.signal import savgol_filter

        xs = savgol_filter(xs, w, polyorder)
        ys = savgol_filter(ys, w, polyorder)

    return np.column_stack([xs, ys])


def remove_outliers(
    positions: Sequence[Optional[Sequence[float]]], max_jump: float = 100.0
) -> list[Optional[list[float]]]:
    """Null out single-frame teleports in a raw detection track.

    TrackNet (like any detector) occasionally fires on the wrong bright blob; the
    result is a lone point far from its neighbours. A point that sits more than
    `max_jump` from the midpoint of its two neighbours is dropped (set to None) so
    the downstream interpolation bridges the gap instead of trusting the spike.
    """
    out: list[Optional[list[float]]] = [None if p is None else [float(p[0]), float(p[1])] for p in positions]
    for i in range(1, len(out) - 1):
        b = out[i]
        a, c = out[i - 1], out[i + 1]
        if b is None or a is None or c is None:
            continue
        mid = ((a[0] + c[0]) / 2.0, (a[1] + c[1]) / 2.0)
        if np.hypot(b[0] - mid[0], b[1] - mid[1]) > max_jump:
            out[i] = None
    return out


def cap_court_jumps(
    positions: Sequence[Optional[Sequence[float]]], max_step_m: float = 2.8
) -> list[Optional[list[float]]]:
    """Null court-plane points that imply unphysical motion between frames.

    On the court plane a ball can move at most ~max_step_m metres per frame (at
    30fps, 2.8 m == ~300 km/h). A point that jumps further than that from the last
    accepted point is perspective-amplified far-court noise (a few pixels of jitter
    near the horizon = decimetres) or a tracking spike — drop it so interpolation
    bridges the gap instead of trusting the jump. Runs after projection to metres.
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    last: Optional[list[float]] = None
    for i, p in enumerate(out):
        if p is None:
            continue
        if last is not None and np.hypot(p[0] - last[0], p[1] - last[1]) > max_step_m:
            out[i] = None
            continue
        last = p
    return out


def filter_live_ball(
    positions: Sequence[Optional[Sequence[float]]],
    homography=None,
    *,
    min_run: int = 4,
    min_net_disp_px: float = 12.0,
    play_margin_m: float = 2.0,
) -> list[Optional[list[float]]]:
    """Keep only contiguous track segments that behave like a LIVE, in-play ball.

    The per-frame court gate and static-lock gate (BallTracker) run online and
    judge one detection at a time; this offline pass judges each contiguous
    locked run as a whole and nulls the ones that aren't a struck ball:

      - brief low-motion flickers: a run shorter than `min_run` frames whose net
        displacement is under `min_net_disp_px` — a detector twitch on a graphic
        or fixture that the 5-frame static-gate window let slip. A real ball,
        even in a 2-3 frame blur, travels much further than a flicker.
      - off-court runs (needs `homography`): a run whose court-plane projection
        never reaches the play area (doubles court + `play_margin_m` metres) — an
        adjacent-court ball or crowd motion that stayed inside the loose
        per-frame continue-bound but never actually got to the court. A real
        rally passes through the court, so at least one of its points lands in.

    Returns a new same-length list; dropped frames become None. Without a
    homography only the motion test applies (on an uncalibrated clip a *moving*
    off-court ball cannot be rejected geometrically — that needs the court).
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    Hinv = None if homography is None else np.linalg.inv(np.asarray(homography, float))
    if Hinv is not None:
        from . import court
        x_lo, x_hi = -play_margin_m, court.DOUBLES_WIDTH + play_margin_m
        y_lo, y_hi = -play_margin_m, court.LENGTH + play_margin_m

    def reaches_court(run_pts) -> bool:
        for x, y in run_pts:
            q = Hinv @ np.array([x, y, 1.0])
            if abs(q[2]) < 1e-9:
                continue
            cx, cy = q[0] / q[2], q[1] / q[2]
            if x_lo <= cx <= x_hi and y_lo <= cy <= y_hi:
                return True
        return False

    i, n = 0, len(out)
    while i < n:
        if out[i] is None:
            i += 1
            continue
        j = i
        while j < n and out[j] is not None:
            j += 1
        run = list(range(i, j))               # contiguous locked segment [i, j)
        pts = [out[k] for k in run]
        net = float(np.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]))
        drop = len(run) < min_run and net < min_net_disp_px
        if not drop and Hinv is not None and not reaches_court(pts):
            drop = True
        if drop:
            for k in run:
                out[k] = None
        i = j
    return out


def _interp_nan(a: np.ndarray) -> np.ndarray:
    """Linearly interpolate NaNs in a 1-D array; edge-fill the ends."""
    idx = np.arange(len(a))
    valid = ~np.isnan(a)
    if not valid.any():
        return a  # nothing to anchor on; leave as-is
    out = a.copy()
    out[~valid] = np.interp(idx[~valid], idx[valid], a[valid])
    return out


def _odd_window(window: int, n: int) -> int:
    """Largest valid odd Savitzky-Golay window <= window and <= n."""
    w = min(window, n)
    if w % 2 == 0:
        w -= 1
    return max(w, 0)


class BallDetector:
    """Per-frame ball detector backed by TrackNet (REAL).

    TrackNet takes three consecutive frames (to learn motion, since a single
    blurry frame is ambiguous) and outputs a heatmap whose peak is the ball.
    detect() keeps a rolling 3-frame buffer, so call it once per frame in order;
    the first two calls return None while the buffer fills.

    Weights: a checkpoint compatible with _tracknet.BallTrackerNet (see
    weights/tracknet.pt). The pipeline projects the returned pixel track to court
    metres with the homography and runs smooth_and_fill over it.
    """

    def __init__(self, weights: str, device: str = "cpu") -> None:
        import os

        import torch

        from ._tracknet import BallTrackerNet

        torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
        self.device = device
        self.weights_path = weights   # recorded in the perception-cache provenance
        self.in_h, self.in_w = 360, 640  # TrackNet input size (matched to weights)
        self.model = BallTrackerNet(out_channels=256)
        self.model.load_state_dict(torch.load(weights, map_location=device))
        self.model.eval().to(device)
        self._buf: deque = deque(maxlen=3)
        self.last_sub = None   # best sub-threshold response (tracker rescue)

    def reset(self) -> None:
        """Clear the frame buffer (call between independent clips)."""
        self._buf.clear()
        self.last_sub = None

    def detect(self, frame) -> Optional[tuple[float, float]]:
        """Return the ball's (x_px, y_px) in `frame`'s pixel space, or None."""
        import cv2
        import torch

        H, W = frame.shape[:2]
        self._buf.append(frame)
        if len(self._buf) < 3:
            return None

        cur, prev, preprev = self._buf[2], self._buf[1], self._buf[0]
        imgs = np.concatenate(
            [
                cv2.resize(cur, (self.in_w, self.in_h)),
                cv2.resize(prev, (self.in_w, self.in_h)),
                cv2.resize(preprev, (self.in_w, self.in_h)),
            ],
            axis=2,
        ).astype(np.float32) / 255.0
        inp = torch.from_numpy(np.rollaxis(imgs, 2, 0)[None]).float().to(self.device)
        with torch.no_grad():
            out = self.model(inp)
        feature_map = out.argmax(dim=1).detach().cpu().numpy()[0]
        cx, cy = self._postprocess(feature_map)
        if cx is None:
            # Sub-threshold rescue candidate: the net's best weak response. Only
            # BallTracker may use it, and only under its velocity/court gates.
            rx, ry = self._postprocess(feature_map, thresh=60)
            self.last_sub = (rx * W / self.in_w, ry * H / self.in_h) if rx is not None else None
            return None
        self.last_sub = None
        # Scale from the 640x360 inference space back to the frame.
        return cx * W / self.in_w, cy * H / self.in_h

    def _postprocess(self, feature_map, thresh: int = 127):
        """Decode the heatmap to (x, y) in 640x360 space.

        The original TrackNet decode accepted a frame only when HoughCircles found
        *exactly one* circle, discarding any frame with 0 or 2+ blobs. We instead
        take the strongest connected component (area x peak) of the thresholded
        confidence map: this returns a point whenever the net fires at all, and is
        what BallTracker gates temporally. Returns (None, None) on an empty map.
        """
        import cv2

        fm = feature_map.reshape((self.in_h, self.in_w)).astype(np.uint8)
        _, binm = cv2.threshold(fm, thresh, 255, cv2.THRESH_BINARY)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(binm, connectivity=8)
        best, best_score = None, 0.0
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < 1:
                continue
            peak = float(fm[lab == i].max())
            score = area * peak
            if score > best_score:
                best, best_score = (float(cent[i][0]), float(cent[i][1])), score
        return best if best is not None else (None, None)


class OurBallDetector:
    """OUR ball detector — swingvision._ballnet.BallNet trained on this project's
    own pseudo-label dataset (backend/train_ballnet.py), no third-party weights.
    Same detect() interface/convention as WASBDetector (3 frames newest-first,
    512x288, /255; heatmap peak above score_thresh)."""

    in_w, in_h = 512, 288

    def __init__(self, weights: str | None = None, device: str = "cpu",
                 score_thresh: float = 0.5) -> None:
        import os

        import torch

        from ._ballnet import BallNet

        # Weights precedence: explicit arg > BALLNET_WEIGHTS env > default v1.
        # The env hook lets a benchmark run point at ballnet_v2.pt without
        # touching the shipped ballnet.pt or the pipeline call chain; the
        # chosen file is recorded in the perception-cache provenance below.
        weights = weights or os.environ.get("BALLNET_WEIGHTS", "weights/ballnet.pt")
        torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
        self.device = device
        self.weights_path = weights   # recorded in the perception-cache provenance
        self.score_thresh = score_thresh
        self.model = BallNet()
        ckpt = torch.load(weights, map_location=device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"], strict=True)
        self.model.eval().to(device)
        self._buf: deque = deque(maxlen=3)
        self.last_sub = None   # best sub-threshold response (tracker rescue)

    def reset(self) -> None:
        self._buf.clear()
        self.last_sub = None

    def detect(self, frame) -> Optional[tuple[float, float]]:
        import cv2
        import torch

        H, W = frame.shape[:2]
        self._buf.append(frame)
        if len(self._buf) < 3:
            return None
        order = [self._buf[2], self._buf[1], self._buf[0]]   # newest first
        chans = [cv2.resize(f, (self.in_w, self.in_h)).astype(np.float32) / 255.0 for f in order]
        arr = np.concatenate(chans, axis=2)
        inp = torch.from_numpy(np.ascontiguousarray(np.rollaxis(arr, 2, 0))[None]).float().to(self.device)
        with torch.no_grad():
            hm = torch.sigmoid(self.model(inp)[0, 0]).cpu().numpy()
        iy, ix = np.unravel_index(hm.argmax(), hm.shape)
        pt = (float(ix) * W / self.in_w, float(iy) * H / self.in_h)
        if hm[iy, ix] < self.score_thresh:
            # Weak response kept as a tracker-gated rescue candidate.
            self.last_sub = pt if hm[iy, ix] >= 0.5 * self.score_thresh else None
            return None
        self.last_sub = None
        return pt


class WASBDetector:
    """Ball detector backed by WASB (HRNet, BMVC2023) — a stronger raw recall than
    TrackNet on fast/blurred balls. Drop-in for BallDetector: detect() keeps a
    rolling 3-frame buffer and returns (x_px, y_px) in frame space, or None.

    Preprocessing was reverse-engineered against the published tennis checkpoint and
    verified to localize the ball to ~2px median: 3 frames stacked NEWEST-first,
    scaled to 512x288 and /255, output heatmap channel 0 (the current frame), sigmoid
    then a confidence-thresholded best-blob centroid.
    """

    in_w, in_h = 512, 288

    def __init__(self, weights: str = "weights/wasb_tennis_best.pth.tar",
                 device: str = "cpu", score_thresh: float = 0.5) -> None:
        import os
        import torch

        from ._wasbnet import HRNet

        torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
        self.device = device
        self.weights_path = weights   # recorded in the perception-cache provenance
        self.score_thresh = score_thresh
        self.model = HRNet(in_channels=9, out_channels=3, stem_strides=(1, 1))
        ckpt = torch.load(weights, map_location=device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"], strict=True)
        self.model.eval().to(device)
        self._buf: deque = deque(maxlen=3)
        self.last_sub = None   # best sub-threshold response (tracker rescue)

    def reset(self) -> None:
        self._buf.clear()
        self.last_sub = None

    def detect(self, frame) -> Optional[tuple[float, float]]:
        import cv2
        import torch

        H, W = frame.shape[:2]
        self._buf.append(frame)
        if len(self._buf) < 3:
            return None
        # Newest-first: [t, t-1, t-2].
        order = [self._buf[2], self._buf[1], self._buf[0]]
        chans = [cv2.resize(f, (self.in_w, self.in_h)).astype(np.float32) / 255.0 for f in order]
        arr = np.concatenate(chans, axis=2)
        inp = torch.from_numpy(np.ascontiguousarray(np.rollaxis(arr, 2, 0))[None]).float().to(self.device)
        with torch.no_grad():
            hm = torch.sigmoid(self.model(inp)[0, 0]).cpu().numpy()
        cx, cy, score = self._decode(hm)
        if cx is None or score < self.score_thresh:
            # Weak response kept as a tracker-gated rescue candidate.
            self.last_sub = None
            if float(hm.max()) >= 0.5 * self.score_thresh:
                iy, ix = np.unravel_index(hm.argmax(), hm.shape)
                self.last_sub = (float(ix) * W / self.in_w, float(iy) * H / self.in_h)
            return None
        self.last_sub = None
        return cx * W / self.in_w, cy * H / self.in_h

    def _decode(self, hm):
        """Best blob over the thresholded heatmap; intensity-weighted centroid."""
        import cv2

        binm = (hm >= self.score_thresh).astype(np.uint8)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(binm, connectivity=8)
        if n <= 1:
            return None, None, 0.0
        best_i = max(range(1, n), key=lambda i: hm[lab == i].sum())
        ys, xs = np.where(lab == best_i)
        w = hm[ys, xs]
        return float((xs * w).sum() / w.sum()), float((ys * w).sum() / w.sum()), float(hm.max())


def _in_any_box(x: float, y: float, boxes, pad: float = 24.0) -> bool:
    """True if (x, y) falls inside any (x1, y1, x2, y2) box dilated by `pad` px.
    Used to mask players (and their racquet swing) out of background candidates."""
    if not boxes:
        return False
    for b in boxes:
        if b is None:
            continue
        x1, y1, x2, y2 = b
        if x1 - pad <= x <= x2 + pad and y1 - pad <= y <= y2 + pad:
            return True
    return False


def median_background(video_path, frame_step: int = 1, max_frames: Optional[int] = None,
                      max_samples: int = 80, scale: float = 0.5):
    """Build a static-camera background image by per-pixel median over the clip.

    Returns (bg_bgr_halfres, inv_scale) where inv_scale maps half-res pixels back
    to full-res. Up to max_samples frames are SEEKED to (not decoded sequentially),
    so building the model costs ~80 reads regardless of clip length instead of a full
    extra decode pass. A fixed camera is assumed (offline-first design); on panning
    footage BallTracker auto-skips the background channel per frame.
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    last = (min(total, max_frames) if max_frames else total) - 1
    if last < 0:
        cap.release()
        return None, 1.0 / scale
    n = min(max_samples, last + 1)
    targets = sorted({int(round(i)) for i in np.linspace(0, last, n)})
    samples = []
    for fi in targets:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)   # exact frame not required for a median
        ok, frame = cap.read()
        if ok:
            h, w = frame.shape[:2]
            samples.append(cv2.resize(frame, (int(w * scale), int(h * scale))))
    cap.release()
    if not samples:
        return None, 1.0 / scale
    bg = np.median(np.stack(samples), axis=0).astype(np.uint8)
    return bg, 1.0 / scale


class BallTracker:
    """Causal ball tracker: TrackNet (primary) fused with fixed-camera background
    subtraction (fallback), gated by a forward velocity prediction.

    TrackNet is confident-or-silent: when it fires it is right, but on a fast,
    motion-blurred ball it outputs nothing. On a static camera the ball is still a
    small, ball-sized blob in the frame-difference foreground; we accept such a
    blob only when it lies on the physically-predicted path (a velocity-scaled
    tube), which suppresses the crowd/limb/line foreground. Measured on a broadcast
    clip this lifts the locked-ball rate from ~75% to ~95%.

    Call update(frame) once per frame in order; returns (x, y) in frame pixels when
    the ball is locked (real evidence), or None (downstream smooth_and_fill bridges
    short gaps). Background subtraction is skipped on frames with large global
    change (a pan or cut), so it never invents a ball when the camera moves.
    """

    def __init__(self, detector, frame_wh, background=None,
                 inv_scale: float = 2.0, use_bgsub: bool = True, gate: float = 70.0,
                 max_coast: int = 8, max_bg_run: int = 5, fg_thresh: int = 28,
                 max_fg_ratio: float = 0.25, box_pad: float = 24.0,
                 homography=None, acquire_bound_m: float = 4.0,
                 continue_bound_m: float = 10.0, rescue: bool = False,
                 static_step_px: float = 3.0, static_min_run: int = 5):
        # One detector or several (e.g. TrackNet + WASB). Several are FUSED: each is
        # queried every frame (to keep its 3-frame buffer current) and the candidate
        # most consistent with the predicted path wins — their failure modes differ,
        # so the union recovers frames either alone would miss.
        self.detectors = list(detector) if isinstance(detector, (list, tuple)) else [detector]
        self.W, self.H = frame_wh
        # Court-plausibility gate (needs the homography). A candidate must
        # back-project within `acquire_bound_m` of the court to START a track (so a
        # crowd/scoreboard misfire can't seed one) and within `continue_bound_m` to
        # CONTINUE one (loose — a real airborne ball projects past the baseline, but
        # nothing real projects 20+ m beyond it). This kills the smooth drift into
        # the crowd that the velocity gate alone allowed.
        self.Hinv = None if homography is None else np.linalg.inv(np.asarray(homography, float))
        self.acquire_bound_m = acquire_bound_m
        self.continue_bound_m = continue_bound_m
        self.bg = background
        self.inv_scale = inv_scale
        self.use_bgsub = use_bgsub and background is not None
        self.gate = gate
        self.max_coast = max_coast
        self.max_bg_run = max_bg_run
        self.fg_thresh = fg_thresh
        self.max_fg_ratio = max_fg_ratio
        self.box_pad = box_pad
        self.last: Optional[tuple] = None
        self.vel = np.zeros(2)
        self.miss = 0
        self.bg_run = 0   # consecutive bg-only frames since the last TrackNet lock
        self.n_tnet = self.n_bg = self.n_sub = 0
        # Sub-threshold rescue is OPT-IN: measured on yt_rally2 it STEERS the
        # track onto weak false candidates (a wrong sub-threshold pick corrupts
        # the velocity prediction, then real detections get rejected as
        # off-path) — coverage fell 968 -> 781. Off until the detector can rank
        # weak candidates more reliably (hard-negative retrain).
        self.rescue = rescue
        # Static-lock gate: a rally ball never sits still, but burned-in HUD
        # graphics (SwingVision MPH labels / logo on sourced test clips), net
        # posts and other fixtures do — and detectors DO fire on them (measured
        # on yt_rally2: 103-183 of the locks per run were <3px/frame for >=5
        # frames). After static_min_run near-motionless emissions the "track"
        # is declared a fixture: dropped, its spot remembered (bounded list),
        # and no candidate near a known fixture may seed or extend a track
        # again — so the tracker goes back to looking for the real ball.
        # Costs nothing on clean footage: moving balls never trip it.
        self.static_step_px = static_step_px
        self.static_min_run = static_min_run
        self.static_run = 0
        self.static_anchors: list = []
        self.n_static = 0   # fixture zones found (for the analyze log)

    def _court_ok(self, pt, acquiring: bool) -> bool:
        """Court-plausibility of an image-space candidate: its ground back-projection
        must land within the acquire/continue bound of the court rectangle."""
        if self.Hinv is None or pt is None:
            return True   # no homography available: gate disabled
        from . import court

        p = np.asarray([pt[0], pt[1], 1.0], dtype=float)
        q = self.Hinv @ p
        if abs(q[2]) < 1e-9:
            return False
        x, y = q[0] / q[2], q[1] / q[2]
        b = self.acquire_bound_m if acquiring else self.continue_bound_m
        return (-b <= x <= court.DOUBLES_WIDTH + b) and (-b <= y <= court.LENGTH + b)

    def _static_ok(self, pt) -> bool:
        """False if the candidate sits in a known static-fixture zone (a spot
        where a previous track froze for static_min_run frames — HUD graphic,
        net post). A real ball only passes through; it never lives there."""
        r = 4.0 * self.static_step_px
        return all(np.hypot(pt[0] - a[0], pt[1] - a[1]) > r
                   for a in self.static_anchors)

    def _bg_candidates(self, frame, exclude_boxes=None):
        import cv2

        small = cv2.resize(frame, (self.bg.shape[1], self.bg.shape[0]))
        diff = cv2.absdiff(small, self.bg)
        g = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(g, self.fg_thresh, 255, cv2.THRESH_BINARY)
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        if th.mean() / 255.0 > self.max_fg_ratio:   # camera moved / lighting jump
            return []
        n, lab, stats, cent = cv2.connectedComponentsWithStats(th, connectivity=8)
        out = []
        for k in range(1, n):
            a = int(stats[k, cv2.CC_STAT_AREA])
            w = int(stats[k, cv2.CC_STAT_WIDTH]); h = int(stats[k, cv2.CC_STAT_HEIGHT])
            if 2 <= a <= 120 and w <= 22 and h <= 22:   # ball-sized, not a player blob
                cx = float(cent[k][0] * self.inv_scale)
                cy = float(cent[k][1] * self.inv_scale)
                if not _in_any_box(cx, cy, exclude_boxes, self.box_pad):
                    out.append((cx, cy))
        return out

    def update(self, frame, exclude_boxes=None) -> Optional[tuple]:
        """`exclude_boxes` are player bounding boxes (x1,y1,x2,y2 in frame px); any
        background-subtraction candidate inside one (dilated by box_pad) is rejected,
        so the bridge can't drift onto a player. With players masked, the bg-bridge
        may safely run longer to recover real ball-blur frames near a player."""
        # Query every detector each frame (advances all rolling buffers). Their
        # detections are the model candidates for this frame.
        dets = [d.detect(frame) for d in self.detectors]
        acquiring = self.last is None
        # Court-plausibility gate: drop candidates whose ground back-projection is
        # nowhere near the court (crowd, scoreboard, birds) BEFORE the velocity
        # logic sees them — smooth off-court drift must never extend a track.
        model_cands = [d for d in dets if d is not None and self._court_ok(d, acquiring)
                       and self._static_ok(d)]
        pred = None
        if self.last is not None:
            pred = (self.last[0] + self.vel[0], self.last[1] + self.vel[1])
        chosen, via_bg = None, False
        if model_cands:
            if pred is None:
                chosen = model_cands[0]   # no track yet: first on-court pick
            else:
                near = min(model_cands, key=lambda c: np.hypot(c[0] - pred[0], c[1] - pred[1]))
                if np.hypot(near[0] - pred[0], near[1] - pred[1]) <= self.gate * (2 + self.miss):
                    chosen = near
            if chosen is not None:
                self.n_tnet += 1
        # Sub-threshold rescue while COASTING mid-track: each detector exposes its
        # best below-threshold response (last_sub). During a live rally the ball is
        # usually the net's strongest weak firing even when motion blur kills the
        # confident one — accept it only on the predicted path, court-plausible,
        # outside player boxes, and within the same run budget as the bg-bridge
        # (weak evidence must never steer the track for long).
        if (chosen is None and self.rescue and pred is not None
                and self.bg_run < self.max_bg_run):
            subs = [getattr(d, "last_sub", None) for d in self.detectors]
            subs = [s for s in subs
                    if s is not None and self._court_ok(s, acquiring=False)
                    and self._static_ok(s)
                    and not _in_any_box(s[0], s[1], exclude_boxes, self.box_pad)]
            if subs:
                subs.sort(key=lambda c: np.hypot(c[0] - pred[0], c[1] - pred[1]))
                if np.hypot(subs[0][0] - pred[0], subs[0][1] - pred[1]) <= self.gate * (1 + self.miss):
                    chosen, via_bg = subs[0], True   # budgeted like a bg-bridge frame
                    self.n_sub += 1
        # bg-sub is a SHORT-gap bridge: stop after max_bg_run frames without a
        # TrackNet re-confirmation, or it drifts onto a player/static blob.
        if (chosen is None and self.use_bgsub and pred is not None
                and self.bg_run < self.max_bg_run):
            cands = [c for c in self._bg_candidates(frame, exclude_boxes)
                     if self._court_ok(c, acquiring=False) and self._static_ok(c)]
            if cands:
                cands.sort(key=lambda c: np.hypot(c[0] - pred[0], c[1] - pred[1]))
                if np.hypot(cands[0][0] - pred[0], cands[0][1] - pred[1]) <= self.gate * (1 + self.miss):
                    chosen, via_bg = cands[0], True
                    self.n_bg += 1
        if chosen is not None:
            c = np.asarray(chosen, dtype=float)
            # Static-lock gate: count consecutive near-motionless steps; at
            # static_min_run the track is a fixture, not a ball — drop it,
            # remember the spot (so it can't be re-locked), report nothing.
            # The first static_min_run-1 emissions necessarily leak (can't
            # know a lock is frozen until it has been frozen for a while).
            if (self.last is not None
                    and np.hypot(c[0] - self.last[0], c[1] - self.last[1])
                    < self.static_step_px):
                self.static_run += 1
                if self.static_run >= self.static_min_run - 1:
                    self.static_anchors.append((float(c[0]), float(c[1])))
                    del self.static_anchors[:-8]   # bounded fixture memory
                    self.n_static += 1
                    self.static_run = 0
                    self.last = None
                    self.vel = np.zeros(2)
                    self.miss = 0
                    self.bg_run = 0
                    return None
            else:
                self.static_run = 0
            if self.last is not None:
                self.vel = 0.5 * self.vel + 0.5 * (c - np.asarray(self.last))
            self.last = (float(c[0]), float(c[1]))
            self.miss = 0
            self.bg_run = self.bg_run + 1 if via_bg else 0
            return self.last
        self.miss += 1
        if self.miss > self.max_coast:
            self.last = None
            self.vel = np.zeros(2)
            self.bg_run = 0
        return None
