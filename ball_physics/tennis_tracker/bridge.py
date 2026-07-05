"""Bridge: SwingVision-clone court setup + ball track -> robust speed & spin.

Turns the clone's outputs (a court calibration = 4 corner pixels, and a TrackNet
ball pixel track) into per-shot speed/spin, with the robustness the raw
single-arc fit lacks on real footage:

  * pixel-outlier rejection on the ball track (teleports),
  * Kalman smoothing + bounce detection + arc segmentation,
  * a physics fit that is BOUNDED to plausible ranges (no divergence) and
    ANCHORED at the court plane when an arc begins at a bounce,
  * a reprojection-error guard that flags unreliable arcs instead of reporting
    nonsense.

Camera note: from 4 coplanar court points you can recover the camera pose only
up to the focal length, so you must supply the horizontal field of view
(`hfov_deg`). It's known for a given phone; estimate it for broadcast. Speed
scales with it, so get it roughly right.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

try:
    import cv2
except Exception as e:  # pragma: no cover
    raise ImportError("bridge requires OpenCV") from e

from .data.camera import Camera
from .calibration.court import homography_from_points
from .calibration.lift import lift_contact
from .tracking import link_detections, fill_gaps, KalmanSmoother, detect_bounces, segment_arcs
from .estimation.trajectory_fit import fit_arc

# Map the clone's court landmarks (court.py: x=width 0..10.97, y=length 0..23.77)
# to this framework's world frame (X=length 0..23.77, Y=width centred +-5.485).
_OUR2FW = {
    "near_bl_doubles": [0.0, -5.485],
    "near_br_doubles": [0.0, +5.485],
    "far_bl_doubles": [23.77, -5.485],
    "far_br_doubles": [23.77, +5.485],
}


def camera_from_court_corners(named_corners: dict, img_wh, hfov_deg: float = 70.0):
    """Build (Camera, homography) from the 4 named doubles-corner pixels.

    `named_corners`: {clone landmark name: [u, v]} for the four doubles corners.
    `img_wh`: (width, height). `hfov_deg`: horizontal field of view (see note).
    """
    keys = [k for k in _OUR2FW if k in named_corners]
    if len(keys) < 4:
        raise ValueError("need the 4 doubles corners (near/far _bl/_br_doubles)")
    img = np.array([named_corners[k] for k in keys], np.float32)
    w3d = np.array([[*_OUR2FW[k], 0.0] for k in keys], np.float32)
    w2d = np.array([_OUR2FW[k] for k in keys], np.float32)

    W, H = img_wh
    f = (W / 2.0) / np.tan(np.radians(hfov_deg) / 2.0)
    K = np.array([[f, 0, W / 2.0], [0, f, H / 2.0], [0, 0, 1.0]])
    ok, rvec, tvec = cv2.solvePnP(w3d, img, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        raise RuntimeError("solvePnP failed for the court corners")
    R, _ = cv2.Rodrigues(rvec)
    cam = Camera(K=K, R=R, t=tvec[:, 0], width=int(W), height=int(H))
    Hh = homography_from_points(img, w2d)
    return cam, Hh


def _detect_events(track: np.ndarray, min_turn_deg: float = 45.0, min_sep: int = 4):
    """Contact frames = sharp direction reversals of the ball (a hit or a bounce).

    A flight arc lives between two contacts, so this segments far better than a
    row-maximum bounce heuristic on broadcast tracks (where the ball crosses the
    net repeatedly). Returns sorted contact indices into `track`.
    """
    vel = np.diff(track, axis=0)
    events: list[int] = []
    for i in range(1, len(vel)):
        v1, v2 = vel[i - 1], vel[i]
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 < 1e-6 or n2 < 1e-6:
            continue
        ang = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)))
        if ang >= min_turn_deg and (not events or i - events[-1] >= min_sep):
            events.append(i)
    return events


def _remove_outliers(ball_px, max_jump: float):
    """Null single-frame teleports (same idea as backend ball.remove_outliers)."""
    out = [None if p is None else [float(p[0]), float(p[1])] for p in ball_px]
    for i in range(1, len(out) - 1):
        b, a, c = out[i], out[i - 1], out[i + 1]
        if b is None or a is None or c is None:
            continue
        mid = ((a[0] + c[0]) / 2.0, (a[1] + c[1]) / 2.0)
        if np.hypot(b[0] - mid[0], b[1] - mid[1]) > max_jump:
            out[i] = None
    return out


def _peak_readout(p0, v0, omega, t_max):
    """Summarise a fitted arc at its PEAK speed (≈ off-the-racquet shot speed)."""
    from .physics import simulate
    from .estimation.kinematics import summarize
    tr = simulate(p0, v0, omega, dt=2e-3, t_max=max(t_max, 1e-3), bounces=0)
    i = int(np.argmax(np.linalg.norm(tr.vel, axis=1)))
    return summarize(tr.vel[i], omega), tr


def fit_anchored(times, uv, camera, H, anchor_uv, anchor_at="start", anchor_w=100.0):
    """Fit one arc with one endpoint pinned to the court plane (a bounce).

    Start-anchor: hard-fix p0. End-anchor: soft-penalise the last point toward the
    lifted bounce (forward physics — drag isn't time-reversible, so no reversal).
    Returns (peak_MotionReadout, reproj_px, (p0, v0, omega)). reproj is 2D only.
    """
    from .physics import simulate
    times = np.asarray(times, float)
    uv = np.asarray(uv, float)
    p_anchor = lift_contact(np.asarray(anchor_uv, float), H)[0]
    if anchor_at == "end":
        fit = fit_arc(times, uv, camera=camera, anchor=(-1, p_anchor, anchor_w),
                      physical_bounds=True)
    else:
        fit = fit_arc(times, uv, camera=camera, p0_init=p_anchor, fix_p0=True,
                      physical_bounds=True)
    tr = simulate(fit.p0, fit.v0, fit.omega, dt=2e-3, t_max=float(times[-1]) + 0.05, bounces=0)
    pred = camera.project(tr.sample(times))
    valid = np.isfinite(uv).all(axis=1)
    reproj = float(np.sqrt(np.mean(np.sum((pred - uv)[valid] ** 2, axis=1)))) if valid.any() else 1e9
    readout, _ = _peak_readout(fit.p0, fit.v0, fit.omega, float(times[-1]) + 0.05)
    return readout, reproj, (fit.p0, fit.v0, fit.omega)


def find_bounces(times, track, camera, H, *, max_reproj_px: float = 4.0,
                 win: int = 12, min_gap: int = 4):
    """Detect ground bounces by court-plane consistency.

    Candidates are row maxima where the ball falls then rises (a bounce or a
    near-court hit). A candidate is confirmed a BOUNCE only if, when anchored to
    the court plane, BOTH the incoming and outgoing arcs fit cleanly — a mid-air
    contact anchored to z=0 cannot (it sits ~1 m too low, so the arcs miss).
    """
    times = np.asarray(times, float)
    vy = np.gradient(track[:, 1])
    n = len(track)
    bounces = []
    for c in range(2, n - 2):
        if not (vy[c - 1] > 0 and vy[c + 1] < 0):    # falling -> rising (row max)
            continue
        if bounces and c - bounces[-1] < min_gap:
            continue
        a, b = max(0, c - win), min(n, c + win + 1)
        if c - a < 4 or b - c < 4:
            continue
        _, rin, _ = fit_anchored(times[a:c + 1] - times[a], track[a:c + 1], camera, H, track[c], "end")
        _, rout, _ = fit_anchored(times[c:b] - times[c], track[c:b], camera, H, track[c], "start")
        if rin <= max_reproj_px and rout <= max_reproj_px:
            bounces.append(c)
    return bounces


def estimate_shots(ball_px, fps: float, camera: Camera, H: np.ndarray, *,
                   reproj_max_px: float = 6.0, min_arc_points: int = 6,
                   max_jump_px: float = 120.0, bounce_max_reproj: float = 3.0):
    """Per-flight-arc speed & spin from a ball pixel track. Returns a list of
    dicts; `ok=False` marks arcs the reprojection guard rejected."""
    n = len(ball_px)
    cleaned = _remove_outliers(ball_px, max_jump_px)
    per_frame = [np.array([[p[0], p[1]]], float) if p else None for p in cleaned]
    track = fill_gaps(link_detections(per_frame))
    sm = KalmanSmoother(dt=1.0, q=2.0, r=3.0)(track)
    times = np.arange(n, dtype=float) / fps

    # Detect bounces on the SMOOTHED track (robust row-maxima), but anchor + fit
    # on the FILLED track — the Kalman smoother rounds the sharp bounce kink, so
    # its bounce position is biased; the filled track keeps the true corner.
    bounces = find_bounces(times, sm.pos, camera, H, max_reproj_px=bounce_max_reproj)
    cuts = [0] + list(bounces) + [n - 1]
    bset = set(bounces)

    shots = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < min_arc_points:
            continue
        seg = track[a:b + 1]                       # raw filled pixels (sharp corners)
        seg_t = np.arange(b - a + 1, dtype=float) / fps
        valid = int(np.isfinite(seg).all(axis=1).sum())

        # Anchor at whichever endpoint is a bounce (a hit→bounce arc anchors its
        # END; a bounce→hit arc anchors its START). Both pin the depth -> speed.
        if a in bset:
            r, rep, _ = fit_anchored(seg_t, seg, camera, H, track[a], "start")
            anchored = True
        elif b in bset:
            r, rep, _ = fit_anchored(seg_t, seg, camera, H, track[b], "end")
            anchored = True
        else:
            fit = fit_arc(seg_t, seg, camera=camera, physical_bounds=True)
            _, rep, _ = (fit.readout, fit.rmse, None)
            r = fit.readout
            anchored = False

        ok = bool(anchored and rep <= reproj_max_px)
        shots.append({
            "arc": (int(a), int(b)),
            "speed_kmh": round(r.speed_kmh, 1),
            "spin_rpm": round(r.spin_rpm, 0),
            "topspin_rpm": round(r.topspin_rpm, 0),
            "sidespin_rpm": round(r.sidespin_rpm, 0),
            "reproj_px": round(rep, 1),
            "anchored": anchored,
            "n_points": valid,
            "ok": ok,
        })
    return shots
