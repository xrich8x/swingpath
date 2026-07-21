"""speedspin.py — physics-based shot speed + spin (wraps the ball_physics framework).

The pipeline: build a metric camera from the court calibration, find ball
direction-reversals (hits + bounces), and classify each by PLAYER PROXIMITY — a
reversal near a player is a racquet hit, one away from both players is a ground
bounce. Each hit->bounce arc is then anchored on the court plane (which pins the
otherwise-ambiguous monocular depth) and the flight physics is inverted for
speed + spin.

Camera scale depends on the horizontal FOV (known per phone; estimate for
broadcast), so pass `hfov_deg` for your footage.

HONESTY NOTE (Session E1, measured — see the plausibility band below): a
bounce anchor alone does NOT make speed well-posed. It pins one END of the
flight; the launch point is still free to slide along its viewing ray, and
speed slides with it over a ~2.8x range at under 0.15 px of reprojection cost.
The earlier "~4% on synthetic" figure came from a synthetic setup that also
knew the launch point. Treat every number here as provisional until E3 supplies
that second constraint.
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


# --- Plausibility band (Session E1) -----------------------------------------
# A low reprojection error does NOT certify an arc. Measured on noise-free
# ground truth (tools/arc_observability.py): sliding the launch point along its
# own viewing ray from 0.3 m to 3.0 m yields shot speeds from 55 to 152 km/h for
# one true 87 km/h ball, and EVERY one of them reprojects under 0.15 px. The
# monocular hit->bounce arc, pinned only at the bounce, leaves launch depth free,
# and the fit trades depth against speed (and against the Magnus term) for
# almost nothing in pixels. So `reproj_px` measures self-consistency, not truth.
#
# Until a second constraint pins the launch point (E3 — a contact-height prior
# or the striker's court position from pose), an arc must ALSO land inside
# physically plausible bands before anything downstream may call it a
# measurement. Real evidence this is needed: yt_rally2 @60fps produced an arc at
# reproj 3.5 px reporting 110 km/h with 10,361 rpm — pro topspin is ~2-3,200 rpm.
SPEED_BAND_KMH = (20.0, 250.0)
SPIN_BAND_RPM = 3500.0


def _plausible(speed_kmh: float, spin_rpm: float) -> Optional[str]:
    """None if the readout is physically believable, else why it is not."""
    lo, hi = SPEED_BAND_KMH
    if not np.isfinite(speed_kmh) or not lo <= speed_kmh <= hi:
        return f"speed {speed_kmh:.0f} km/h outside {lo:.0f}-{hi:.0f}"
    if not np.isfinite(spin_rpm) or abs(spin_rpm) > SPIN_BAND_RPM:
        return f"spin {spin_rpm:.0f} rpm exceeds {SPIN_BAND_RPM:.0f}"
    return None


def _readout(a, b, r, reproj, fps, reproj_max_px) -> dict:
    """One arc's public record, with the reason it was rejected (if it was)."""
    why = _plausible(r.speed_kmh, r.spin_rpm)
    if why is None and reproj > reproj_max_px:
        why = f"reproj {reproj:.1f}px exceeds {reproj_max_px:.1f}px"
    return {
        "start_frame": int(a), "end_frame": int(b),
        "t_hit_s": round(a / fps, 2), "t_bounce_s": round(b / fps, 2),
        "speed_kmh": round(r.speed_kmh, 1),
        "spin_rpm": round(r.spin_rpm, 0),
        "topspin_rpm": round(r.topspin_rpm, 0),
        "reproj_px": round(reproj, 1),
        "ok": why is None,
        "reject_reason": why,
    }


# Our court frame is (x = width 0..10.97, y = length 0..23.77); the physics
# framework's is (X = length, Y = width measured to the image LEFT, Z = up).
# The Y flip is not cosmetic — it is what makes the frame right-handed with +Z
# up, which the simulator's gravity depends on. Mirrors bridge._OUR2FW exactly;
# change both together.
def _to_framework_xy(court_xy):
    return (float(court_xy[1]), 5.485 - float(court_xy[0]))


def _striker_xy(near_img, far_img, near_court, far_court, frame, ball_uv,
                max_px=400.0):
    """Court (X, Y) of whichever player struck this ball, or None.

    The striker is the player closest to the ball in the image at the hit frame.
    Requiring a court position too means an arc silently falls back to the old
    bounce-only fit when pose lost the player, rather than inventing a launch.
    """
    best, best_d = None, max_px
    for img_list, court_list in ((near_img, near_court), (far_img, far_court)):
        if not img_list or not court_list or frame >= len(img_list) \
                or frame >= len(court_list):
            continue
        p, c = img_list[frame], court_list[frame]
        if p is None or c is None:
            continue
        d = float(np.hypot(ball_uv[0] - p[0], ball_uv[1] - p[1]))
        if d < best_d:
            best, best_d = c, d
    return _to_framework_xy(best) if best is not None else None


def _estimate_from_events(track, hit_idx, bounce_idx, camera, Hfw, fps,
                          min_arc, reproj_max_px, fit_anchored,
                          striker_xy_at=None, launch_from_striker=None,
                          fit_launch_anchored=None, max_striker_miss_m=2.5):
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

        # Pin the launch end too, when pose can say where the striker stood.
        # Without it the fit is under-determined and speed is arbitrary (E1).
        p_launch, miss, source = None, None, "bounce_only"
        if striker_xy_at is not None and np.isfinite(seg[0]).all():
            xy = striker_xy_at(h, seg[0])
            if xy is not None:
                p_launch, miss = launch_from_striker(camera, seg[0], xy)
                if p_launch is None or miss > max_striker_miss_m \
                        or not 0.0 <= p_launch[2] <= 4.0:
                    p_launch = None      # implausible contact -> fall back
        if p_launch is not None:
            r, reproj, _ = fit_launch_anchored(seg_t, seg, camera, Hfw,
                                               p_launch, track[b])
            source = "striker_launch"
        else:
            r, reproj, _ = fit_anchored(seg_t, seg, camera, Hfw, track[b], "end")

        rec = _readout(h, b, r, reproj, fps, reproj_max_px)
        rec["launch_source"] = source
        if p_launch is not None:
            rec["launch_height_m"] = round(float(p_launch[2]), 2)
            rec["striker_miss_m"] = round(float(miss), 2)
        shots.append(rec)
    return shots


def _falling_then_rising(track: np.ndarray):
    """Row-maxima of the ball (falls then rises) — bounce OR near-player hit."""
    vy = np.gradient(track[:, 1])
    return [i for i in range(2, len(track) - 2) if vy[i - 1] > 0 and vy[i + 1] < 0]


def estimate(ball_px, near_img, far_img, named_corners, img_wh, fps, *,
             hfov_deg: float = 70.0, player_radius_px: float = 180.0,
             min_arc: int = 6, reproj_max_px: float = 6.0,
             hit_idx=None, bounce_idx=None,
             near_court=None, far_court=None):
    """Returns a list of arc readouts (struck shots), each a dict with
    start_frame/end_frame, t_hit_s, t_bounce_s, speed_kmh, spin_rpm, topspin_rpm,
    reproj_px, ok. `near_img`/`far_img` are per-frame player image positions (or None).

    When `hit_idx`/`bounce_idx` (frame indices from the events layer) are given,
    arcs are built hit -> first-bounce directly from them — the court-plane event
    detection is far more reliable than the image-space row-max heuristic here
    (low skidding bounces barely reverse in image y, and racquet contacts happen a
    racquet-length from the feet the proximity check measures against).

    `near_court`/`far_court` are the same players' positions in COURT metres. Give
    them and each arc is pinned at its launch end as well as its bounce, which is
    what makes speed observable at all (E1) — without them the fit falls back to
    the bounce-only anchor and its speed should not be believed.
    """
    _ensure_path()
    from tennis_tracker.bridge import (camera_from_court_corners, fit_anchored,
                                       fit_launch_anchored, launch_from_striker)
    from tennis_tracker.tracking import link_detections, fill_gaps

    camera, Hfw = camera_from_court_corners(named_corners, img_wh, hfov_deg=hfov_deg)

    n = len(ball_px)
    per_frame = [np.array([[p[0], p[1]]], float) if p else None for p in ball_px]
    track = fill_gaps(link_detections(per_frame))

    if hit_idx is not None and bounce_idx is not None:
        striker_xy_at = None
        if near_court is not None or far_court is not None:
            def striker_xy_at(frame, ball_uv):
                return _striker_xy(near_img, far_img, near_court, far_court,
                                   frame, ball_uv)
        return _estimate_from_events(track, hit_idx, bounce_idx, camera, Hfw, fps,
                                     min_arc, reproj_max_px, fit_anchored,
                                     striker_xy_at=striker_xy_at,
                                     launch_from_striker=launch_from_striker,
                                     fit_launch_anchored=fit_launch_anchored)

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
        shots.append(_readout(a, b, r, reproj, fps, reproj_max_px))
    return shots
