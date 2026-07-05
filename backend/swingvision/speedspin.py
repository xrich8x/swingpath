"""speedspin.py — physics-based shot speed + spin (wraps the ball_physics framework).

The pipeline: build a metric camera from the court calibration, find ball
direction-reversals (hits + bounces), and classify each by PLAYER PROXIMITY — a
reversal near a player is a racquet hit, one away from both players is a ground
bounce. Each hit->bounce arc is then anchored on the court plane (which pins the
otherwise-ambiguous monocular depth) and the flight physics is inverted for
speed + spin.

Speed is well-posed once anchored (~4% on synthetic); spin magnitude is looser.
Camera scale depends on the horizontal FOV (known per phone; estimate for
broadcast), so pass `hfov_deg` for your footage.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

import numpy as np

_BALL_PHYSICS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ball_physics"))


def _ensure_path():
    if _BALL_PHYSICS not in sys.path:
        sys.path.insert(0, _BALL_PHYSICS)


def _estimate_from_events(track, hit_idx, bounce_idx, camera, Hfw, fps,
                          min_arc, reproj_max_px, fit_anchored):
    """Build one arc per struck shot from the events layer: hit h -> the first
    bounce >= ~4 frames later and before the next hit. Single ballistic flights by
    construction; each is end-anchored at its bounce and physics-fit."""
    n = len(track)
    hits = sorted(int(h) for h in hit_idx)
    # The court-speed-minima detector fires at racquet contacts too (speed dips at a
    # hit) — those are NOT ground bounces and must not anchor a flight. Drop any
    # bounce candidate within a few frames of a hit.
    bounces = sorted(int(b) for b in bounce_idx
                     if all(abs(b - h) > 3 for h in hits))
    shots = []
    for k, h in enumerate(hits):
        next_hit = hits[k + 1] if k + 1 < len(hits) else n - 1
        cand = [b for b in bounces if h + 4 <= b <= next_hit]
        if not cand:
            continue
        b = cand[0]
        if b - h < min_arc:
            continue
        # Skip the contact frame(s): at the racquet the ball reverses violently and
        # its centroid rides the strings — the first frames after a hit aren't free
        # flight and poison the fit. The flight is (h+2 .. b], anchored at b.
        a = h + 2
        seg = track[a:b + 1]
        if np.isfinite(seg).all(axis=1).sum() < min_arc or not np.isfinite(track[b]).all():
            continue
        seg_t = np.arange(b - a + 1, dtype=float) / fps
        r, reproj, _ = fit_anchored(seg_t, seg, camera, Hfw, track[b], "end")
        shots.append({
            "start_frame": int(h), "end_frame": int(b),
            "t_hit_s": round(h / fps, 2), "t_bounce_s": round(b / fps, 2),
            "speed_kmh": round(r.speed_kmh, 1),
            "spin_rpm": round(r.spin_rpm, 0),
            "topspin_rpm": round(r.topspin_rpm, 0),
            "reproj_px": round(reproj, 1),
            "ok": bool(reproj <= reproj_max_px),
        })
    return shots


def _falling_then_rising(track: np.ndarray):
    """Row-maxima of the ball (falls then rises) — bounce OR near-player hit."""
    vy = np.gradient(track[:, 1])
    return [i for i in range(2, len(track) - 2) if vy[i - 1] > 0 and vy[i + 1] < 0]


def estimate(ball_px, near_img, far_img, named_corners, img_wh, fps, *,
             hfov_deg: float = 70.0, player_radius_px: float = 180.0,
             min_arc: int = 6, reproj_max_px: float = 6.0,
             hit_idx=None, bounce_idx=None):
    """Returns a list of arc readouts (struck shots), each a dict with
    start_frame/end_frame, t_hit_s, t_bounce_s, speed_kmh, spin_rpm, topspin_rpm,
    reproj_px, ok. `near_img`/`far_img` are per-frame player image positions (or None).

    When `hit_idx`/`bounce_idx` (frame indices from the events layer) are given,
    arcs are built hit -> first-bounce directly from them — the court-plane event
    detection is far more reliable than the image-space row-max heuristic here
    (low skidding bounces barely reverse in image y, and racquet contacts happen a
    racquet-length from the feet the proximity check measures against).
    """
    _ensure_path()
    from tennis_tracker.bridge import camera_from_court_corners, fit_anchored
    from tennis_tracker.tracking import link_detections, fill_gaps

    camera, Hfw = camera_from_court_corners(named_corners, img_wh, hfov_deg=hfov_deg)

    n = len(ball_px)
    per_frame = [np.array([[p[0], p[1]]], float) if p else None for p in ball_px]
    track = fill_gaps(link_detections(per_frame))

    if hit_idx is not None and bounce_idx is not None:
        return _estimate_from_events(track, hit_idx, bounce_idx, camera, Hfw, fps,
                                     min_arc, reproj_max_px, fit_anchored)

    # Classify reversals: near a player -> hit; away -> bounce (the anchorable contact).
    bounces, hits = [], []
    for c in _falling_then_rising(track):
        if not np.isfinite(track[c]).all():
            continue
        near_hit = False
        for players in (near_img, far_img):
            p = players[c] if c < len(players) else None
            if p is not None and np.hypot(track[c][0] - p[0], track[c][1] - p[1]) < player_radius_px:
                near_hit = True
                break
        if near_hit:
            hits.append(c)
        elif not bounces or c - bounces[-1] >= 4:
            bounces.append(c)

    # Cut at EVERY reversal — a bounce-to-bounce span contains the racquet hit
    # between them (two flights joined at a kink), which no single ballistic fit
    # can match. Keep only arcs that END at a bounce (the anchorable contact).
    cuts = sorted({0, n - 1, *bounces, *hits})
    bset = set(bounces)
    shots = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < min_arc or b not in bset:
            continue
        seg = track[a:b + 1]
        if np.isfinite(seg).all(axis=1).sum() < min_arc:
            continue
        seg_t = np.arange(b - a + 1, dtype=float) / fps
        r, reproj, _ = fit_anchored(seg_t, seg, camera, Hfw, track[b], "end")
        shots.append({
            "start_frame": int(a), "end_frame": int(b),
            "t_hit_s": round(a / fps, 2), "t_bounce_s": round(b / fps, 2),
            "speed_kmh": round(r.speed_kmh, 1),
            "spin_rpm": round(r.spin_rpm, 0),
            "topspin_rpm": round(r.topspin_rpm, 0),
            "reproj_px": round(reproj, 1),
            "ok": bool(reproj <= reproj_max_px),
        })
    return shots
