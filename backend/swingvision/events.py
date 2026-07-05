"""events.py — hits, bounces, rallies, shot type.

This module straddles geometry and logic. Given a *court-plane* ball track (the
output of perception + projection), it derives discrete events:

  - detect_hits    : racquet contacts, seen as sharp direction reversals
  - detect_bounces : court-speed heuristic for the ball striking the ground
  - segment_rallies: group hits separated by long gaps into rallies (logic)
  - classify_shot  : forehand / backhand heuristic (replaced by a learned
                     classifier in Phase 3)

Bounce detection from a single camera has no true ball height — it's a kink in
the court-plane path, not a measured bounce. That's a known limitation, not a
bug (see CLAUDE.md). The demo generator produces these events directly; these
functions are the real implementations the perception pipeline feeds into.
"""

from __future__ import annotations

import math
from typing import Sequence

Track = Sequence[Sequence[float]]   # sequence of (t_s, x_m, y_m)


def _velocity(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    """(vx, vy, speed) between two (t, x, y) samples, per second."""
    dt = b[0] - a[0]
    if dt <= 0:
        return 0.0, 0.0, 0.0
    vx = (b[1] - a[1]) / dt
    vy = (b[2] - a[2]) / dt
    return vx, vy, math.hypot(vx, vy)


def _turn_angle(v_in: tuple[float, float], v_out: tuple[float, float]) -> float:
    """Angle in degrees between incoming and outgoing velocity vectors."""
    n_in = math.hypot(*v_in)
    n_out = math.hypot(*v_out)
    if n_in < 1e-9 or n_out < 1e-9:
        return 0.0
    cos = (v_in[0] * v_out[0] + v_in[1] * v_out[1]) / (n_in * n_out)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def detect_hits(track: Track, angle_thresh_deg: float = 80.0, min_gap_s: float = 0.4) -> list[int]:
    """Indices of likely racquet contacts.

    A hit reverses the ball's travel: the angle between the incoming and
    outgoing velocity exceeds `angle_thresh_deg`. Consecutive candidates within
    `min_gap_s` are de-duplicated to the sharpest turn.
    """
    pts = [tuple(p) for p in track]
    if len(pts) < 3:
        return []
    candidates: list[tuple[int, float]] = []
    for k in range(1, len(pts) - 1):
        vin = _velocity(pts[k - 1], pts[k])[:2]
        vout = _velocity(pts[k], pts[k + 1])[:2]
        angle = _turn_angle(vin, vout)
        if angle >= angle_thresh_deg:
            candidates.append((k, angle))

    hits: list[int] = []
    for k, angle in candidates:
        if hits and pts[k][0] - pts[hits[-1]][0] < min_gap_s:
            if angle > _turn_angle(
                _velocity(pts[hits[-1] - 1], pts[hits[-1]])[:2],
                _velocity(pts[hits[-1]], pts[hits[-1] + 1])[:2],
            ):
                hits[-1] = k  # keep the sharper turn
            continue
        hits.append(k)
    return hits


def detect_bounces(track: Track, min_speed_drop: float = 0.5, min_gap_s: float = 0.15) -> list[int]:
    """Indices of likely bounces — a single-camera court-speed heuristic.

    With no true height, a bounce shows up as a local speed minimum where the
    court-plane direction kinks (the ball slows and changes heading as it skids
    off the surface). Returns local minima of the per-segment speed.

    Far-court pixel jitter, amplified by perspective into metre-scale wiggles, can
    spawn a burst of adjacent local minima; `min_gap_s` de-duplicates minima closer
    than that, keeping the deepest dip, so one physical bounce yields one index.
    """
    pts = [tuple(p) for p in track]
    if len(pts) < 3:
        return []
    speeds = [_velocity(pts[k], pts[k + 1])[2] for k in range(len(pts) - 1)]
    raw: list[int] = []
    for k in range(1, len(speeds) - 1):
        if speeds[k] < speeds[k - 1] and speeds[k] < speeds[k + 1]:
            if speeds[k] < min_speed_drop * max(speeds[k - 1], speeds[k + 1]):
                raw.append(k)
    bounces: list[int] = []
    for k in raw:
        if bounces and pts[k][0] - pts[bounces[-1]][0] < min_gap_s:
            if speeds[k] < speeds[bounces[-1]]:
                bounces[-1] = k  # keep the deeper dip
            continue
        bounces.append(k)
    return bounces


def segment_rallies(hit_times: Sequence[float], gap_s: float = 4.0,
                    force_break_after: Sequence[int] = ()) -> list[list[int]]:
    """Group hit indices into rallies. A gap longer than `gap_s` between
    consecutive hits ends a rally. Pure logic — a deterministic split.

    `force_break_after` are hit indices after which the rally MUST end regardless
    of timing — the tennis rule that a second bounce before the next contact ends
    the point (whatever contact follows is a pickup/feed, not rally play)."""
    breaks = set(force_break_after)
    rallies: list[list[int]] = []
    current: list[int] = []
    prev_t: float | None = None
    for i, t in enumerate(hit_times):
        if prev_t is not None and t - prev_t > gap_s:
            if current:
                rallies.append(current)
            current = []
        current.append(i)
        prev_t = t
        if i in breaks:
            rallies.append(current)
            current = []
            prev_t = None
    if current:
        rallies.append(current)
    return rallies


def _kp(kpts, idx, conf=0.3):
    """A keypoint (x, y) if confident enough, else None."""
    if kpts is None or idx >= len(kpts):
        return None
    x, y, c = kpts[idx]
    return (float(x), float(y)) if c >= conf else None


def _mean_pts(pts):
    pts = [p for p in pts if p is not None]
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def classify_shot(
    hit_x: float,
    player_x: float,
    handedness: str = "right",
    facing_away: bool = True,
    *,
    is_serve: bool = False,
    volleyed: bool = False,
    striker_kpts=None,
    contact_xy_img=None,
) -> str:
    """Classify a stroke: serve | overhead | volley | forehand | backhand.

    Combines ball geometry (what we can compute) with player pose at contact (what
    we must learn from the body):
      - serve:    first contact of the rally (caller flag).
      - overhead: contact well above the shoulders (a smash) — needs pose + the ball
                  image position at contact.
      - volley:   the ball was struck before bouncing on the striker's side.
      - fore/back: which side of the body the contact is on, in the player's own
                  left/right frame (depends on handedness and which way they face).

    `striker_kpts` is the striker's 17 COCO keypoints (x, y, conf) in image pixels at
    the hit frame; `contact_xy_img` is the ball's image position at contact. When pose
    is unavailable it degrades to the court-x side heuristic (hit_x vs player_x).
    """
    if is_serve:
        return "serve"

    shoulders = _mean_pts([_kp(striker_kpts, 5), _kp(striker_kpts, 6)])
    hips = _mean_pts([_kp(striker_kpts, 11), _kp(striker_kpts, 12)])

    # Overhead/smash. The old test ("ball above the shoulder line in image y")
    # misfires from an elevated camera: the ball sits at a different DEPTH than
    # the player, so a waist-high contact beyond them projects above their
    # shoulders. The robust cue compares the player's own body parts (same depth,
    # same perspective): a smash means the racket ARM is extended overhead — a
    # wrist above the head — with the ball also up there. Both conditions or it's
    # a groundstroke.
    if shoulders is not None and contact_xy_img is not None:
        torso = abs((hips[1] if hips else shoulders[1] + 1) - shoulders[1]) + 1e-6
        head = _mean_pts([_kp(striker_kpts, 0), _kp(striker_kpts, 1), _kp(striker_kpts, 2)])
        head_y = head[1] if head else shoulders[1] - 0.9 * torso
        wrists = [_kp(striker_kpts, 9), _kp(striker_kpts, 10)]
        wrist_raised = any(w is not None and w[1] < head_y for w in wrists)
        ball_high = contact_xy_img[1] < shoulders[1] - 0.4 * torso
        if ball_high and wrist_raised:
            return "overhead"

    if volleyed:
        return "volley"

    # Forehand vs backhand: side of contact relative to the body centre, mapped to
    # the player's dominant side. Prefer the pose body-centre (image space) when we
    # have it and the ball image position; else fall back to court-x.
    dominant_right = (handedness == "right") == facing_away
    if shoulders is not None and contact_xy_img is not None:
        side = contact_xy_img[0] - shoulders[0]   # +: ball on the image-right of body
    else:
        side = hit_x - player_x
    on_dominant_side = side > 0 if dominant_right else side < 0
    return "forehand" if on_dominant_side else "backhand"


def contact_side(striker_kpts, contact_xy_img, hit_x=None, player_x=None):
    """Signed side of contact relative to the striker's body (+ = image right,
    falling back to court-x). Used to infer HANDEDNESS across a match: players
    hit more forehands than backhands, so the majority contact side is the
    dominant side. Returns None when neither cue is available."""
    shoulders = _mean_pts([_kp(striker_kpts, 5), _kp(striker_kpts, 6)])
    if shoulders is not None and contact_xy_img is not None:
        return contact_xy_img[0] - shoulders[0]
    if hit_x is not None and player_x is not None:
        return hit_x - player_x
    return None


def infer_handedness(sides: Sequence[float], facing_away: bool,
                     min_shots: int = 6, min_majority: float = 0.6) -> str:
    """Infer a player's handedness from their contact sides over a match (logic).

    Rationale: rally play skews toward the forehand, so the majority contact
    side is the dominant (racket) side. In image space the forehand side of a
    right-hander is the image-RIGHT when they face away from the camera and the
    image-LEFT when they face it. Conservative: returns "right" (the default)
    unless there are at least `min_shots` usable groundstrokes AND a
    `min_majority` majority on one side.
    """
    usable = [s for s in sides if s is not None and abs(s) > 1e-6]
    if len(usable) < min_shots:
        return "right"
    right_frac = sum(1 for s in usable if s > 0) / len(usable)
    if right_frac >= min_majority:
        majority_image_right = True
    elif right_frac <= 1.0 - min_majority:
        majority_image_right = False
    else:
        return "right"   # no clear majority: keep the default
    # majority image side -> dominant side -> handedness, given facing.
    return "right" if majority_image_right == facing_away else "left"


def classify_spin(kpts_window, contact_xy_img) -> str:
    """topspin | slice | flat | "" — from the racket-hand path through contact.

    A topspin swing brushes LOW-to-HIGH (the wrist rises through contact; image y
    decreases); a slice comes HIGH-to-LOW. Both wrist and torso are on the same
    body, so the comparison is depth-consistent from any camera height (unlike
    ball-vs-body tests). `kpts_window` is the striker's keypoints for the frames
    around the hit (centre = contact frame). Returns "" when the wrist isn't
    tracked well enough to judge.
    """
    if not kpts_window or contact_xy_img is None:
        return ""
    mid = len(kpts_window) // 2
    centre = kpts_window[mid]
    # Racket hand = the wrist nearer the ball at contact.
    cands = [(i, _kp(centre, i)) for i in (9, 10)]
    cands = [(i, p) for i, p in cands if p is not None]
    if not cands:
        return ""
    wrist_idx = min(cands, key=lambda ip: math.hypot(ip[1][0] - contact_xy_img[0],
                                                     ip[1][1] - contact_xy_img[1]))[0]
    ys = [(k, _kp(kp, wrist_idx)) for k, kp in enumerate(kpts_window)]
    ys = [(k, p[1]) for k, p in ys if p is not None]
    if len(ys) < 3 or ys[-1][0] == ys[0][0]:
        return ""
    # Torso height at contact scales the threshold (resolution-independent).
    shoulders = _mean_pts([_kp(centre, 5), _kp(centre, 6)])
    hips = _mean_pts([_kp(centre, 11), _kp(centre, 12)])
    if shoulders is None or hips is None:
        return ""
    torso = abs(hips[1] - shoulders[1]) + 1e-6
    rise = (ys[0][1] - ys[-1][1]) / torso   # +: wrist moved UP across the window
    if rise > 0.35:
        return "topspin"
    if rise < -0.35:
        return "slice"
    return "flat"
