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

# Static-fixture gate, expressed in TIME units so the same physical motion trips
# it identically at any frame rate. The numbers are the historical 30 fps values
# (3.0 px/frame, 5 frames) restated per second — behaviour at 30 fps is unchanged.
STATIC_STEP_PX_PER_S = 90.0
STATIC_MIN_RUN_S = 5.0 / 30.0


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


def rectify_track(
    positions: Sequence[Optional[Sequence[float]]],
    *,
    max_speed_px: float = 60.0,
    win: int = 6,
    resid_px: float = 40.0,
) -> list[Optional[list[float]]]:
    """Robust offline cleanup of a ball pixel track (Session E3i).

    `remove_outliers` only catches a LONE spike flanked by two good points. It
    misses the two failures you actually see in the drawn trail:
      * a SUSTAINED wrong lock — the detector rides a fixture (net post, HUD,
        the far player) for a few frames, so the "spike" has no clean neighbour
        and survives;
      * a spike next to a GAP — one neighbour is None, so the midpoint test
        cannot even run.
    Both make the trail "suddenly go awry", most often on the far side where the
    real ball is ~2 px and easily lost.

    The literature's answer is a global, motion-consistent path rather than a
    greedy per-frame pick (Viterbi / shortest-path over candidates). We do not
    keep per-frame candidates, so this is the one-track analogue: over a sliding
    window, fit a robust local line through the LOCKED points (Theil-Sen style —
    median of pairwise slopes, which ignores up to ~half the window being wrong)
    and null any point that (a) implies a speed above `max_speed_px` per frame
    from its accepted predecessor, or (b) sits more than `resid_px` off the local
    fit. Nulled points become gaps for the existing physics-aware interpolation to
    bridge — a straight coast is a better guess than a wrong lock.

    Pixel-space and calibration-free, so it runs on any clip and is measurable on
    the gold labels directly.
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    n = len(out)
    idx = [i for i in range(n) if out[i] is not None]
    if len(idx) < 3:
        return out

    def robust_predict(anchor_pos, refs):
        """Median-slope extrapolation to `anchor_pos+1` from prior locked refs."""
        if len(refs) < 2:
            return None
        vs = []
        for a in range(len(refs)):
            for b in range(a + 1, len(refs)):
                (ia, pa), (ib, pb) = refs[a], refs[b]
                dt = ib - ia
                if dt:
                    vs.append(((pb[0] - pa[0]) / dt, (pb[1] - pa[1]) / dt))
        if not vs:
            return None
        vx = float(np.median([v[0] for v in vs]))
        vy = float(np.median([v[1] for v in vs]))
        (li, lp) = refs[-1]
        return [lp[0] + vx * (anchor_pos - li), lp[1] + vy * (anchor_pos - li)]

    accepted: list[tuple[int, list[float]]] = []
    for i in idx:
        p = out[i]
        refs = accepted[-win:]
        pred = robust_predict(i, refs)
        drop = False
        if refs:
            li, lp = refs[-1]
            step = np.hypot(p[0] - lp[0], p[1] - lp[1]) / max(1, i - li)
            # A single big step is allowed (fast ball); a big step that ALSO
            # disagrees with the motion trend is a wrong lock.
            if step > max_speed_px and pred is not None:
                if np.hypot(p[0] - pred[0], p[1] - pred[1]) > resid_px:
                    drop = True
        # NB: no standalone "residual off the linear fit" test. A real ball arc
        # CURVES, so a linear extrapolation is legitimately off near the hit and
        # bounce — testing residual alone nulled exactly the fast, curved points
        # that define a shot's speed (measured: it moved speed error 28% -> 39%).
        # A wrong lock must show up as an unphysical STEP as well, which the test
        # above already requires; sustained wrong locks are caught because each
        # frame after the first re-tests the step against the last ACCEPTED point.
        if drop:
            out[i] = None
        else:
            accepted.append((i, p))
    return out


def cap_court_jumps(
    positions: Sequence[Optional[Sequence[float]]], max_step_m: float = 2.8,
    *, max_gap_allowance_m: float = 30.0,
) -> list[Optional[list[float]]]:
    """Null court-plane points that imply unphysical motion for the TIME elapsed.

    On the court plane a ball can move at most ~max_step_m metres per frame (at
    30fps, 2.8 m == ~300 km/h). A point that jumps further than physics allows
    from the last accepted point is perspective-amplified far-court noise (a few
    pixels of jitter near the horizon = decimetres) or a tracking spike — drop it
    so interpolation bridges the gap instead of trusting the jump.

    The budget scales with the number of frames elapsed since the last accepted
    point (Session E3b fix). The old fixed per-comparison cap was gap-blind:
    after any detection dropout the ball had legitimately flown many metres, so
    the first re-detection was culled — and because culled points never update
    the anchor, every subsequent point was compared to an ever-staler position
    and culled too. Measured on yt_rally2 @60fps: 830 in-court projections
    entered, 113 survived; the events layer starved downstream (5/17 strokes).
    `max_gap_allowance_m` caps the budget so a long gap cannot launder a
    teleport across the grounds.
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    last: Optional[list[float]] = None
    last_i: int = 0
    for i, p in enumerate(out):
        if p is None:
            continue
        if last is not None:
            allowed = min(max_step_m * (i - last_i), max_gap_allowance_m)
            if np.hypot(p[0] - last[0], p[1] - last[1]) > allowed:
                out[i] = None
                continue
        last = p
        last_i = i
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


def suppress_false_locks(
    positions: Sequence[Optional[Sequence[float]]],
    *,
    fps_eff: float = 30.0,
    static_radius_px: float = 12.0,
    static_dur_s: float = 0.20,
    seg_step_px: Optional[float] = None,
    seg_dur_s: float = 0.10,
    seg_gap_s: float = 0.0,
    res_scale: float = 1.0,
    tests: str = "both",
) -> list[Optional[list[float]]]:
    """Recall-safe, image-space removal of false ball locks (E5+).

    Both tests come from one physical fact: a real ball is ALWAYS moving across
    the screen; a fixture (burned-in HUD, net post, line marker, logo) is not, and
    a mislock on a player/racket flares for only a few frames without ever forming
    a trajectory. Neither test touches the court projection, so the monocular
    z-ambiguity that makes the court gate a no-op in the far court (a real far
    ball and a fixture project to the same overlapping court coords — measured)
    never enters here.

      - persistence: a lock that stays within `static_radius_px` for
        `static_dur_s` seconds of consecutive processed frames is a fixture. The
        online static-lock gate keys off a per-frame step threshold and misses a
        lock that creeps sub-threshold; this catches the whole slow-drifting run.
      - min-segment: a lock must belong to a run of >= `seg_dur_s` seconds of
        consecutive locks each within `seg_step_px` of the previous (a
        ball-plausible trajectory). A 1-4 frame excursion that never forms a
        track — a mislock jumping around a moving player — is dropped.

    Durations scale to fps (a fixture is static for a TIME, not a frame count).
    `seg_step_px` also scales with `res_scale` = frame_height / 720: it is a
    ball-MOTION threshold, and the same physical motion covers 1.5x the pixels at
    1080p, so frozen it chops a real track into sub-minimum segments that the
    min-segment test then deletes wholesale. No-op at 1280x720.

    `static_radius_px` deliberately does NOT scale, though the theory says it
    should (both bounds that set it — detector jitter and real ball excursion —
    are pixel quantities). MEASURED on am_hard_utr, scaling it 12 -> 18 px halved
    false-fire (13.2% -> 5.7%) but cost 3.4 pts of recall and 4.3 pts of far-court
    (far_geo 36.9% -> 32.6%). The reason is the low-camera reality this clip is:
    a far ball there moves so little that its 0.2 s excursion clears 12 px but not
    18, so the wider radius reclassifies real far balls as fixtures. Far-court
    recall is the thing this whole gate ladder exists to protect, so the radius
    stays put.

    `tests` selects which of the two runs — "both" (shipped), "persistence" or
    "minseg". It exists because they answer different questions and are mined
    differently: persistence proves a FIXTURE (already mined by
    mine_hard_negatives.py, reaching only the static 38% of confusers), while
    min-segment catches a brief flare that never forms a track — which is what a
    swung racquet looks like, and which no position-based criterion found. Default
    is unchanged and pinned by tests.

    Measured on the yt_rally2 gold labels: no-ball false-fire 61.5% -> 15.4% at a
    3.9-point recall cost (47.7% -> 43.8%). Survivors are in-court mislocks that
    only a more precise detector removes. Persistence runs first so fixtures can't
    chain into a real segment and mask the min-segment test.

    `seg_dur_s` was 0.15 and is now 0.10 — this stage is a pure precision/recall
    dial and 0.15 sat too far toward precision. Swept with tools/tune_suppress.py
    at the SHIPPED frame rate against human gold clicks:

        clip           seg_dur  recall  far_geo  false-fire
        yt_rally2        0.15    69.4%   69.8%     19.2%
        yt_rally2        0.10    72.5%   74.3%     23.1%
        am_hard_utr      0.15    50.0%   54.8%     16.7%
        am_hard_utr      0.10    54.4%   60.3%     25.0%

    The per-frame false-fire rise looks bad and does not reach the product: end to
    end on yt_rally2 the shot list is IDENTICAL (14 hits, 8 bounces, 14 shots — no
    phantom events), because `drop_events_without_ball` and the smoother's segment
    logic absorb stray locks that never form a trajectory. What does reach the
    product is accuracy, because better coverage means better tracks — median
    groundstroke speed error against the SwingVision HUD fell 29.9% -> 20.3%, and
    one more shot became confident.

    `seg_gap_s` (bridging a detector blink inside a run) is a MEASURED NO-OP at the
    shipped rate and stays at 0. The strict-consecutiveness problem it fixes is real
    but only bites at high fps: seg_dur is a TIME, so at fps_eff 60 the old rule
    demanded nine unbroken detections (~1% likely at 60% per-frame recall), while at
    the shipped ~30 fps it is only four. Swept at 30 fps, bridging gaps mostly
    chains false locks together — 0.15/0.03 gave 71.3% recall at 23.1% false-fire,
    strictly worse than 0.10/0.00's 72.5% at the same 23.1%.
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    n = len(out)
    static_run = max(4, round(static_dur_s * fps_eff))
    seg_len = max(3, round(seg_dur_s * fps_eff))
    rs = max(float(res_scale), 1e-6)
    step = (seg_step_px if seg_step_px is not None
            else 6600.0 * rs / max(fps_eff, 1.0))

    # persistence: wipe any run held within static_radius_px for static_run frames
    i = 0
    while i < n and tests in ("both", "persistence"):
        if out[i] is None:
            i += 1
            continue
        j = i + 1
        while j < n and out[j] is not None \
                and np.hypot(out[j][0] - out[i][0], out[j][1] - out[i][1]) <= static_radius_px:
            j += 1
        if j - i >= static_run:
            for k in range(i, j):
                out[k] = None
        i = j

    # min-segment: keep only ball-plausible trajectory runs SPANNING >= seg_len
    # frames. A run may bridge up to `seg_gap` missing frames.
    #
    # That tolerance is the whole point. The test used to require STRICTLY
    # consecutive detections, which made it exponentially harsher as fps rose:
    # seg_len is a time (0.15 s), so at fps_eff 60 it demanded NINE unbroken
    # detections, and at a realistic ~60% per-frame recall that is ~1% likely. One
    # blink in the middle of a real trajectory split it into two short runs and
    # both were deleted. A real ball is still a real ball when the detector
    # misses a frame; what makes it real is that it keeps MOVING plausibly.
    seg_gap = max(0, int(round(seg_gap_s * fps_eff)))
    if tests == "persistence":
        return out
    keep = [False] * n
    i = 0
    while i < n:
        if out[i] is None:
            i += 1
            continue
        run = [i]
        j = i
        while True:
            k = j + 1
            while k < n and out[k] is None and k - j <= seg_gap:
                k += 1
            if k >= n or out[k] is None or (k - j) > seg_gap + 1:
                break
            # Budget the step by the frames actually skipped, so bridging a gap
            # cannot smuggle in a teleport.
            if np.hypot(out[k][0] - out[j][0], out[k][1] - out[j][1]) > step * (k - j):
                break
            run.append(k)
            j = k
        if run[-1] - run[0] + 1 >= seg_len:
            for k in run:
                keep[k] = True
        i = j + 1
    for k in range(n):
        if not keep[k]:
            out[k] = None
    return out


def coast_fill(
    positions: Sequence[Optional[Sequence[float]]],
    *,
    fps_eff: float = 30.0,
    max_arc_gap_s: float = 0.40,
    hit_reversal_px: float = 8.0,
    win: int = 4,
) -> tuple[list[Optional[list[float]]], list[bool]]:
    """Fill interior track gaps by COASTING along the ball's arc, not a straight
    line (physics, not ML). Between two locks the ball is ballistic, so a degree-2
    fit x(t), y(t) through the surrounding locks follows the real parabola where a
    straight line floats. Returns (filled, coasted) — `coasted[k]` marks every
    frame we GUESSED (no detection), so the renderer can dim it and speed/bounce
    logic can refuse to trust it.

    Honesty rules baked in:
      - only gaps up to `max_arc_gap_s` seconds are arc-coasted; the fit is only
        trustworthy over a short flight. Longer gaps still get filled so the ball
        doesn't vanish, but with a conservative straight line (an arc extrapolated
        over ~1 s swings wildly), and every filled frame is flagged coasted.
      - a gap where the ball's horizontal velocity REVERSES is a hit/bounce inside
        the gap — the arc changes there, so we fall back to a straight line rather
        than coast a single parabola through the corner.
      - edge gaps (missing a lock on one side) are left empty: with nothing to
        anchor one end, any guess is unbounded.
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    n = len(out)
    coasted = [False] * n
    max_arc = max(2, round(max_arc_gap_s * fps_eff))

    def fill_linear(a, b):
        for k in range(a + 1, b):
            t = (k - a) / (b - a)
            out[k] = [positions[a][0] + t * (positions[b][0] - positions[a][0]),
                      positions[a][1] + t * (positions[b][1] - positions[a][1])]
            coasted[k] = True

    i = 0
    while i < n:
        if positions[i] is None:
            i += 1
            continue
        j = i + 1
        while j < n and positions[j] is None:
            j += 1
        if j >= n:                       # trailing edge gap: no right anchor
            break
        L = j - i - 1
        if L <= 0:
            i = j
            continue
        left = [k for k in range(max(0, i - win + 1), i + 1) if positions[k] is not None]
        right = [k for k in range(j, min(n, j + win)) if positions[k] is not None]
        pre_v = positions[i][0] - positions[left[0]][0] if len(left) >= 2 else 0.0
        post_v = positions[right[-1]][0] - positions[j][0] if len(right) >= 2 else pre_v
        reversal = pre_v * post_v < 0 and (abs(pre_v) > hit_reversal_px or abs(post_v) > hit_reversal_px)
        anchors = left + right
        if L <= max_arc and len(anchors) >= 3 and not reversal:
            ts = np.asarray(anchors, float)
            px = np.polyfit(ts, [positions[k][0] for k in anchors], 2)
            py = np.polyfit(ts, [positions[k][1] for k in anchors], 2)
            for k in range(i + 1, j):
                out[k] = [float(np.polyval(px, k)), float(np.polyval(py, k))]
                coasted[k] = True
        else:
            fill_linear(i, j)            # long gap or a hit inside it: straight line
        i = j
    return out, coasted


def play_volume_polygon(
    homography,
    img_wh: Sequence[float],
    *,
    hfov_deg: Optional[float] = None,
    runoff_m: float = 3.0,
    max_ball_height_m: float = 6.0,
    top_extra_px: float = 220.0,
    side_extra_px: float = 120.0,
) -> Optional[np.ndarray]:
    """Image-space region a ball in play can occupy: the projection of the court +
    runoff box extruded to `max_ball_height_m`. Returns an (N,1,2) float32 contour
    for `cv2.pointPolygonTest`, or None without a homography.

    A ball is not on the court plane, so the plane's trapezoid is the wrong shape —
    a lob sits well above its far edge. The box IS convex, so its image is exactly
    the convex hull of its eight projected corners. That derivation is the whole
    point: it self-scales with resolution, camera height and lens, where a fixed
    pixel margin does not.

    Two rungs:
      A. `hfov_deg` given and the pose solves -> the real extruded hull.
      B. otherwise -> the ground trapezoid plus a pixel band above its far edge,
         the pre-existing behaviour, but with the margins scaled off the frame
         size instead of being frozen at the 1280x720 they were tuned on.
    """
    import cv2

    from . import calibration, court as _court

    ro = runoff_m
    ground = [(-ro, -ro), (_court.DOUBLES_WIDTH + ro, -ro),
              (_court.DOUBLES_WIDTH + ro, _court.LENGTH + ro), (-ro, _court.LENGTH + ro)]
    if homography is None:
        return None

    # --- Rung A: the honest extruded play volume --------------------------------
    if hfov_deg:
        box = [(x, y, 0.0) for x, y in ground] + \
              [(x, y, float(max_ball_height_m)) for x, y in ground]
        pts = calibration.project_court_3d(homography, img_wh, box, float(hfov_deg))
        if pts is not None:
            hull = cv2.convexHull(pts.astype(np.float32))
            return hull.reshape(-1, 1, 2)

    # --- Rung B: ground trapezoid + a resolution-scaled airborne band -----------
    W, Hh = float(img_wh[0]), float(img_wh[1])
    top_extra = top_extra_px * (Hh / 720.0)
    side_extra = side_extra_px * (W / 1280.0)
    poly = np.array([calibration.court_to_image(homography, [p])[0] for p in ground],
                    np.float64)
    if not np.isfinite(poly).all():
        return None
    far_y = float(min(poly[2, 1], poly[3, 1]))
    lx = float(min(poly[2, 0], poly[3, 0])) - side_extra
    rx = float(max(poly[2, 0], poly[3, 0])) + side_extra
    band = np.array([[lx, far_y - top_extra], [rx, far_y - top_extra],
                     [rx, far_y], [lx, far_y]], np.float64)
    hull = cv2.convexHull(np.vstack([poly, band]).astype(np.float32))
    return hull.reshape(-1, 1, 2)


def gate_ball_to_court(
    positions: Sequence[Optional[Sequence[float]]],
    homography,
    img_wh: Sequence[float],
    *,
    hfov_deg: Optional[float] = None,
    runoff_m: float = 3.0,
    max_ball_height_m: float = 6.0,
    top_extra_px: float = 220.0,
    side_extra_px: float = 120.0,
) -> list[Optional[list[float]]]:
    """Reject ball locks that fall OUTSIDE the main court's IMAGE region — the ball
    tracked on an adjacent court. Court-SPACE gating can't do this: a real airborne
    far ball's ground (z=0) projection scatters as far sideways as an adjacent court
    (measured on gold — real far balls reach court-x 32), so it overlaps the very
    thing we want to reject. Image space separates them.

    The accepted region is `play_volume_polygon` — the court + runoff extruded to
    ball height and projected. Needs a valid homography (returns the input unchanged
    without one — an amateur clip with no calibration keeps every lock).

    Retention measured against HUMAN GOLD CLICKS (tools/eval_court_gate.py; every
    labelled ball frame is a real ball, so these are ceilings), far band = the top
    36% of frame height:

                          all balls        far court
        extruded volume   100% (617)       100% (255)
        scaled band        99.0%            97.6%
        220/120 px fixed   98.1%            95.7%

    The pooled numbers hide the point. On the two 720p clips all three agree at
    100%; the entire gap is am_hard_utr (1080p, 1.74 m camera), where the fixed
    margins kept only 15.4% of far-court balls and scaling them recovered just
    53.8%. The gate — not the detector — was deleting the far ball on exactly the
    amateur footage this project targets.
    """
    out: list[Optional[list[float]]] = [
        None if p is None else [float(p[0]), float(p[1])] for p in positions
    ]
    poly = play_volume_polygon(homography, img_wh, hfov_deg=hfov_deg, runoff_m=runoff_m,
                               max_ball_height_m=max_ball_height_m,
                               top_extra_px=top_extra_px, side_extra_px=side_extra_px)
    if poly is None:
        return out
    import cv2

    for i, p in enumerate(out):
        if p is not None and cv2.pointPolygonTest(poly, (p[0], p[1]), False) < 0:
            out[i] = None
    return out


def _ca_transition() -> np.ndarray:
    """Constant-acceleration state transition for one axis at dt=1: p+=v+a/2, v+=a."""
    return np.array([[1.0, 1.0, 0.5], [0.0, 1.0, 1.0], [0.0, 0.0, 1.0]])


def _ca_process(sigma_jerk: float) -> np.ndarray:
    """Continuous white-noise-jerk process covariance for one axis at dt=1."""
    return (sigma_jerk ** 2) * np.array([[1/20, 1/8, 1/6],
                                         [1/8, 1/3, 1/2],
                                         [1/6, 1/2, 1.0]])


def smooth_forecast(
    positions: Sequence[Optional[Sequence[float]]],
    *,
    fps_eff: float = 30.0,
    meas_var: float = 25.0,
    sigma_jerk: float = 1.0,
    gate_chi2: float = 13.8,
    reset_after: int = 3,
    bounce_reset: bool = False,
    max_gap_s: float = 0.4,
    scale_m_per_px: Optional[Sequence[Optional[float]]] = None,
    max_jerk_ratio: float = 4.0,
    jerk_ref_pct: float = 50.0,
    res_scale: float = 1.0,
    blocked: Optional[Sequence[bool]] = None,
) -> tuple[list[Optional[list[float]]], list[bool], list[float]]:
    """Smooth AND forecast the ball track with one physics model — a constant-
    acceleration Kalman filter + RTS (forward-backward) smoother in image pixels.

    Supersedes per-gap polyfit coasting: a single ballistic model governs the whole
    track, so noisy detections are DENOISED, gaps are FORECAST by the same model
    (no kink where a fill meets a detection), outlier locks are GATED OUT by their
    innovation, and the posterior covariance yields a per-frame confidence that
    decays the longer the ball is unseen.

    Hits/bounces (a sharp direction change) would otherwise be rounded by one
    smooth arc, so they trigger a RESET: `reset_after` consecutive gated detections
    (the model is stale) start a new segment, and the RTS pass never bridges across
    a reset — corners stay sharp.

    Only INTERPOLATION is emitted: a denoised detection, or a gap of at most
    `max_gap_s` seconds bounded by an accepted detection on BOTH sides. Forward /
    backward EXTRAPOLATION past a segment's outermost detections is dropped — that
    is where a constant-acceleration model runs away off-screen and paints a
    phantom ball through dead time. When the ball is genuinely gone, so is the dot.

    Returns (smoothed, coasted, confidence): `smoothed[i]` is (x, y) or None,
    `coasted[i]` marks interpolated frames (no detection — dim it and keep it out
    of speed/bounce), `confidence[i]` in [0, 1].

    `scale_m_per_px` (optional, per frame) makes the process noise DEPTH-AWARE:
    the filter works in image pixels, but a physical jerk of J m/s^3 shows up as
    J / court_scale_m_per_px px/s^3, so one pixel `sigma_jerk` is only correct at
    one court depth. sigma is rescaled by `scale[jerk_ref_pct] / scale[i]`, clamped
    to `max_jerk_ratio`.

    MEASURED, AND NOT USED BY THE PIPELINE (tools/eval_smoother.py, yt_rally2 gold,
    both arms fed identical pre-smoother locks):

        reference     hit@10   far    false-fire   jerk px/frame^2
        constant       43.4%  24.4%      19.2%          2.04
        median         43.8%  25.0%      26.9%          2.63
        p10            42.6%  25.6%      19.2%          1.94
        p2             41.5%  25.6%      19.2%          1.87

    The idea is sound and the effect is real but negligible. Normalising on the
    median makes it actively WORSE: half the frames get LOOSER than the tuned
    value, and that near-court loosening both de-smooths the track and lets more
    junk through the innovation gate (false-fire 19 -> 27%). Tightening only (p10)
    buys +1.2 pt far-court hit@10 and 5% less jerk for -0.8 pt overall — inside
    noise on 258 labelled frames, and nowhere near the 2.4x the Kalman itself
    bought. Kept as an off-by-default option so the measurement isn't repeated.
    Without it (the default, and every uncalibrated clip) behaviour is unchanged.

    `bounce_reset` (MEASURED NEGATIVE, off by default, kept so the measurement is
    not repeated). This stage is 68% of the post-bounce ball loss (-186 of -274
    locks in the 6-frame windows after 196 landings on yt_match40), and the cause
    is above: a reset needs `reset_after` CONSECUTIVE rejections, so a bounce
    costs the two detections either side of it. `bounce_reset` makes the test
    PHYSICAL instead of a counter - in image pixels y grows downward, so a
    descending ball has vy > 0 and a bounce flips it, and a rejection sitting
    ABOVE the prediction while the model still descends (with horizontal
    continuity, so an overhead false lock cannot trigger it) is a reflection
    rather than an outlier, and resets on that frame.

    Pre-registered gate: recall >= -2 pts, ghosts must not rise, real_landing
    >= +5 pts. Scored on human gold clicks through the shipped chain:

        clip          recall@10px   ghosts   real_landing
        yt_match40    52.7 -> 53.8   5 -> 6   70.9 -> 74.5
        yt_rally2     42.2 -> 41.5   4 -> 5   80.0 -> 80.0

    FAILS on both: +3.6 pts of real_landing on yt_match40 is short of the +5 bar,
    yt_rally2 has no headroom (already 80% however it is configured), and both
    cost a ghost. Directionally right where detections are SPARSE and inert where
    they are dense - the same density dependence the `reset_after` sweep and the
    `max_gap_s` sweep both hit. NOTE the ghost counts rest on 24/26 no-ball frames,
    well under the 74 the product gate uses, so +1 is inside sampling noise
    (trap T09); the real_landing columns are the load-bearing ones.
    Evidence: data/output/post_bounce_chain.md.

    Tuned on 1280x720@30fps gold + demo footage (meas_var=25 -> ~5px detector
    noise; sigma_jerk=1.0): jerkiness 9.9 -> 5.6 px/frame^2 at -1.6 pt hit@10.
    """
    n = len(positions)
    out: list[Optional[list[float]]] = [None] * n
    coasted = [False] * n
    conf = [0.0] * n
    if n == 0:
        return out, coasted, conf

    # Resolution. meas_var is px^2 and sigma_jerk is px, both tuned at 1280x720.
    # Their RATIO sets the smoothing bandwidth, so leaving both frozen keeps the
    # smoothing itself correct at any resolution — but it does NOT keep the
    # innovation GATE correct. That test is y' S^-1 y <= gate_chi2, and with S
    # built from a 720p meas_var while y is 1.5x larger at 1080p, the statistic
    # inflates by 2.25x: real detections get gated out as outliers, which both
    # loses them and triggers spurious segment resets. Scaling both restores exact
    # scale-equivariance. Identity at 720p.
    rs = max(float(res_scale), 1e-6)
    meas_var = meas_var * rs * rs
    sigma_jerk = sigma_jerk * rs

    F = np.zeros((6, 6)); F[:3, :3] = _ca_transition(); F[3:, 3:] = _ca_transition()
    Q = np.zeros((6, 6)); Q[:3, :3] = _ca_process(sigma_jerk); Q[3:, 3:] = _ca_process(sigma_jerk)
    Hm = np.zeros((2, 6)); Hm[0, 0] = 1.0; Hm[1, 3] = 1.0
    R = np.eye(2) * meas_var
    I6 = np.eye(6)
    max_gap = max(2, round(max_gap_s * fps_eff))

    # Per-frame process-noise multiplier. Q scales with sigma_jerk^2, so a sigma
    # ratio of (median_scale / scale[i]) is a Q factor of its square.
    qfac = np.ones(n)
    if scale_m_per_px is not None:
        sc = np.array([np.nan if (i >= len(scale_m_per_px) or scale_m_per_px[i] is None)
                       else float(scale_m_per_px[i]) for i in range(n)])
        good = np.isfinite(sc) & (sc > 1e-9)
        if good.any():
            ref = float(np.percentile(sc[good], jerk_ref_pct))
            ratio = np.ones(n)
            ratio[good] = np.clip(ref / sc[good], 1.0 / max_jerk_ratio, max_jerk_ratio)
            qfac = ratio ** 2

    # Seed velocity/acceleration variances are px^2/frame^n, so they scale with
    # resolution squared like meas_var does.
    v0, a0 = 400.0 * rs * rs, 100.0 * rs * rs

    def seed(z):
        s = np.array([z[0], 0.0, 0.0, z[1], 0.0, 0.0])
        C = np.diag([meas_var, v0, a0, meas_var, v0, a0])
        return s, C

    seg_id = [-1] * n
    xf: list = [None] * n; Pf: list = [None] * n     # posterior
    xp: list = [None] * n; Pp: list = [None] * n     # prior
    used = [False] * n
    x = P = None; seg = 0; miss = 0; rej = 0

    for i in range(n):
        z = positions[i]
        if x is None:                       # (re)acquire on the next detection
            if z is not None:
                x, P = seed(z)
                xp[i], Pp[i], xf[i], Pf[i] = x.copy(), P.copy(), x.copy(), P.copy()
                used[i] = True; seg_id[i] = seg
            continue
        x = F @ x; P = F @ P @ F.T + Q * qfac[i]
        xp[i], Pp[i] = x.copy(), P.copy()
        accept = False
        if z is not None:
            y = np.array([z[0], z[1]]) - Hm @ x
            S = Hm @ P @ Hm.T + R
            if float(y @ np.linalg.solve(S, y)) <= gate_chi2:
                K = P @ Hm.T @ np.linalg.inv(S)
                x = x + K @ y; P = (I6 - K @ Hm) @ P
                accept = True; rej = 0; miss = 0
            else:
                rej += 1
                # A BOUNCE IS NOT AN OUTLIER, and waiting for `reset_after`
                # rejections to notice costs the two detections either side of it.
                # Measured (data/output/post_bounce_chain.md): this stage is 68%
                # of the post-bounce ball loss, and losing the frames right after
                # a landing is what closes the hit->landing span speed needs and
                # starves the second-bounce rally rule.
                # The discriminator is physical, not a counter. In image pixels y
                # grows DOWNWARD, so a descending ball has vy > 0 and a bounce
                # flips it negative. A rejection that sits ABOVE the prediction
                # while the model is still descending is a reflection; one that
                # sits anywhere else is an outlier. Horizontal continuity is
                # required too, so a false lock overhead cannot trigger a reset.
                # NOTE the filter runs at dt = 1 FRAME (_ca_transition), so the
                # state's velocities are already px/frame - no dt factor here.
                if bounce_reset and rej < reset_after:
                    px_sd = float(np.sqrt(meas_var)) * res_scale
                    dy = float(z[1]) - float(x[3])       # +ve = below prediction
                    dx = abs(float(z[0]) - float(x[0]))
                    x_tol = max(3.0 * px_sd, 2.0 * abs(float(x[1])))
                    if float(x[4]) > 0.0 and dy < -2.0 * px_sd and dx <= x_tol:
                        rej = reset_after      # trip the reset on THIS frame
        if not accept:
            miss += 1
        used[i] = accept
        xf[i], Pf[i] = x.copy(), P.copy(); seg_id[i] = seg
        if rej >= reset_after or miss >= max_gap:
            x = P = None; seg += 1; rej = 0; miss = 0
            if z is not None and accept is False and rej == 0:  # re-seed on this lock
                x, P = seed(z)
                xp[i], Pp[i], xf[i], Pf[i] = x.copy(), P.copy(), x.copy(), P.copy()
                used[i] = True; seg_id[i] = seg

    # RTS smoother, within each segment only (never across a reset)
    xs = [None if xf[i] is None else xf[i].copy() for i in range(n)]
    Ps = [None if Pf[i] is None else Pf[i].copy() for i in range(n)]
    for i in range(n - 2, -1, -1):
        if xf[i] is None or xs[i + 1] is None or seg_id[i] != seg_id[i + 1] or Pp[i + 1] is None:
            continue
        C = Pf[i] @ F.T @ np.linalg.inv(Pp[i + 1])
        xs[i] = xf[i] + C @ (xs[i + 1] - xp[i + 1])
        Ps[i] = Pf[i] + C @ (Ps[i + 1] - Pp[i + 1]) @ C.T

    def emit(i, is_coast):
        out[i] = [float(xs[i][0]), float(xs[i][3])]
        coasted[i] = is_coast
        pv = float(Ps[i][0, 0] + Ps[i][3, 3]) if Ps[i] is not None else 0.0
        conf[i] = 1.0 / (1.0 + pv / (4.0 * meas_var))

    # Interpolation only: every accepted detection, plus gaps <= max_gap frames that
    # are bounded by an accepted detection on both sides within one segment. Leading/
    # trailing extrapolation (a segment's forecast tail) is never emitted.
    #
    # `blocked` marks frames an EARLIER stage positively judged not-a-ball — in the
    # pipeline, the locks suppress_false_locks and the court gate deleted. Without it
    # this stage cannot tell those two gaps apart:
    #
    #   detector never fired here      -> the ball was probably there and unseen;
    #                                     interpolating is the right guess.
    #   a lock was DELETED as false    -> the pipeline has already decided there was
    #                                     no ball here; interpolating across it
    #                                     re-asserts exactly what suppression denied.
    #
    # Measured on the three calibrated gold clips (2026-08-13): suppression takes
    # ghost fires 9 -> 1 on am_hard_utr and this stage put them back to 6, all five
    # added ones interpolated. Five of six model x clip runs got worse here. So a gap
    # whose interior contains a blocked frame is left unbridged. This is NOT
    # `max_gap_s` by another name — that shrinks every bridge and was measured to
    # cost recall ~1:1 (Session F step 4); this refuses only the bridges a previous
    # stage already argued against, and leaves ordinary detector gaps alone.
    accepted_by_seg: dict[int, list[int]] = {}
    for i in range(n):
        if used[i] and seg_id[i] >= 0 and xs[i] is not None:
            accepted_by_seg.setdefault(seg_id[i], []).append(i)
    for U in accepted_by_seg.values():
        for u in U:
            emit(u, False)
        for a, b in zip(U, U[1:]):
            if not (1 < (b - a) <= max_gap + 1):
                continue
            if blocked is not None and any(
                    k < len(blocked) and blocked[k] for k in range(a + 1, b)):
                continue
            for k in range(a + 1, b):
                if xs[k] is not None:
                    emit(k, True)
    return out, coasted, conf


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
    512x288, /255; heatmap peak above score_thresh).

    SCORE_THRESH: 0.5 was an inherited default and had never been swept until
    Session F. Swept against human gold clicks on all six gold clips
    (tools/eval_detector_gold.py --score-thresh; 1201 ball / 204 no-ball frames):

        thresh  recall  far_px  far_geo  false-fire  recall-ff
         0.30    71.3%   71.5%    74.5%     46.6%       24.7
         0.40    70.4%   70.0%    73.4%     38.7%       31.7
         0.50    69.4%   68.8%    72.5%     34.8%       34.6   <- shipped
         0.60    68.0%   67.8%    70.8%     30.9%       37.1
         0.70    66.1%   65.9%    69.1%     23.0%       43.1
         0.80    62.9%   60.8%    65.1%     16.7%       46.2
         0.90    56.0%   53.2%    58.8%      9.8%       46.2

    The trade is strongly favourable up to ~0.7 (0.5 -> 0.7 buys 11.8 points of
    false-fire for 3.3 of recall) and turns bad after it (0.8 -> 0.9 is 6.9 for
    6.9). But `recall - false-fire` is a SHORTLISTING device only — it cannot see
    whether a lock ever became a drawn ball or an event, and the whole point of
    E6 was that far-court recall is the expensive thing. The shipped value is
    decided on the product metric; see the Session F entry in CLAUDE.md.
    """

    in_w, in_h = 512, 288

    def __init__(self, weights: str | None = None, device: str = "cpu",
                 score_thresh: float = 0.5) -> None:
        import os

        import torch

        from ._ballnet import BallNet

        # Weights precedence: explicit arg > BALLNET_WEIGHTS env > shipped default.
        # Default is the hard-negative model ballnet_v21.pt (E5+): measured through
        # the tracker + suppress_false_locks on the two calibrated gold clips it
        # roughly halves no-ball false-fire vs ballnet.pt (pooled 14% -> 6%) at
        # flat pooled recall (51.8% -> 50.2%) — precision the tracker turns into
        # cleaner tracks. The env hook still points a benchmark at any weight file
        # without touching the pipeline call chain; the file is recorded in the
        # perception-cache provenance below.
        weights = weights or os.environ.get("BALLNET_WEIGHTS", "weights/ballnet_v21.pt")
        torch.set_num_threads(os.cpu_count() or torch.get_num_threads())
        self.device = device
        self.weights_path = weights   # recorded in the perception-cache provenance
        # Same env-hook pattern as the weights above, and for the same reason: it
        # points a benchmark at a different operating point without threading an
        # argument through every construction site. 0.5 is an INHERITED default
        # that was never swept until Session F; the sweep is in the class
        # docstring. It is stamped into the perception-cache provenance, because
        # a cache built at one threshold is not a cache for another.
        env_thresh = os.environ.get("BALLNET_SCORE_THRESH")
        self.score_thresh = float(env_thresh) if env_thresh else score_thresh
        # INPUT RESOLUTION, same env-hook pattern and the same reason again.
        # BallNet is fully convolutional, so it runs at any size divisible by the
        # encoder stride WITHOUT retraining — which makes "how much far-court
        # recall does the downscale cost?" a measurable question rather than an
        # argument. The far ball is ~3.9 px in a 720p frame (farcourt_probe, E2);
        # at 512 wide it reaches the net at ~1.6 px, SMALLER than the 2.0 px the
        # 640-wide TrackNet saw. NOTE the net was TRAINED at 512x288, so a larger
        # input also makes the ball larger than anything it was fitted on — this
        # can hurt, and that is exactly why it is measured rather than assumed.
        env_in = os.environ.get("BALLNET_INPUT")   # e.g. "768x432"
        if env_in:
            w_s, _, h_s = env_in.lower().partition("x")
            self.in_w, self.in_h = int(w_s), int(h_s)
        ckpt = torch.load(weights, map_location=device, weights_only=False)
        sd = ckpt["model_state_dict"]
        # A v4+ (motion-attention) checkpoint carries the motion-prompt params; build
        # the matching arch so plain v3/v21 checkpoints still load unchanged.
        motion = any(k.startswith("motion.") for k in sd)
        self.model = BallNet(motion_attention=motion)
        self.model.load_state_dict(sd, strict=True)
        self.model.eval().to(device)
        self._buf: deque = deque(maxlen=3)
        self.last_sub = None   # best sub-threshold response (tracker rescue)
        # The peak and its position REGARDLESS of the threshold. detect() picks
        # the peak by argmax and only THEN compares it to score_thresh, so the
        # location does not depend on the threshold at all — which means a
        # threshold sweep can be done in memory from one perception pass instead
        # of one GPU pass per threshold. Nothing in the pipeline reads these;
        # they exist so a benchmark can sweep honestly.
        self.last_score = 0.0
        self.last_pt = None

    def reset(self) -> None:
        self._buf.clear()
        self.last_sub = None
        self.last_score = 0.0
        self.last_pt = None

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
        self.last_score = float(hm[iy, ix])
        self.last_pt = pt
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


class RoiDetector:
    """Runs any ball detector on a FIXED crop at native resolution (Session E3f).

    The far ball measures 3.9 px across in a 1280x720 frame, and every heatmap
    detector here resizes the whole frame to 640x360 first — so the net is asked
    to find a **2 px** object. Cropping instead of scaling is the standard fix
    (SAHI: slice, infer per slice, merge), and on our own gold far-court frames it
    lifted the raw detector from 71.4% to 78.6% hit@10, matching an oracle crop
    centred on the human's click.

    This wraps a detector rather than changing one, so `BallTracker` can simply be
    handed [full_frame_detector, RoiDetector(tile_detector, tile)] and its existing
    fusion — "the candidate most consistent with the predicted path wins" — does
    the merging for free. The wrapped detector must be its OWN instance: these
    models keep a 3-frame buffer, and feeding one alternating full frames and
    crops would corrupt its motion cue.
    """

    def __init__(self, detector, roi):
        self.detector = detector
        self.x0, self.y0, self.x1, self.y1 = (int(v) for v in roi)
        self.weights_path = getattr(detector, "weights_path", None)
        self.last_sub = None

    def reset(self) -> None:
        self.detector.reset()
        self.last_sub = None

    def _shift(self, pt):
        return None if pt is None else (pt[0] + self.x0, pt[1] + self.y0)

    def detect(self, frame):
        h, w = frame.shape[:2]
        x0, y0 = max(0, self.x0), max(0, self.y0)
        x1, y1 = min(w, self.x1), min(h, self.y1)
        if x1 - x0 < 32 or y1 - y0 < 32:
            self.last_sub = None
            return None
        out = self.detector.detect(frame[y0:y1, x0:x1])
        self.last_sub = self._shift(getattr(self.detector, "last_sub", None))
        return self._shift(out)


def far_court_roi(homography, img_wh, *, runoff_m: float = 3.0, pad_px: float = 30.0):
    """Image-space crop covering the far half of the court, for `RoiDetector`.

    Derived from the homography so it follows the camera, and extended upward to
    cover an airborne ball (the far court's ground projection alone would clip a
    lob out of the crop). Returns (x0, y0, x1, y1) or None.
    """
    from . import calibration, court

    W, H = img_wh
    ground = [
        (-runoff_m, court.NET_Y), (court.DOUBLES_WIDTH + runoff_m, court.NET_Y),
        (-runoff_m, court.LENGTH + runoff_m),
        (court.DOUBLES_WIDTH + runoff_m, court.LENGTH + runoff_m),
    ]
    try:
        pts = np.asarray(calibration.court_to_image(homography, ground), float)
    except Exception:
        return None
    if not np.isfinite(pts).all():
        return None
    x0, y0 = pts[:, 0].min(), pts[:, 1].min()
    x1, y1 = pts[:, 0].max(), pts[:, 1].max()
    if not (x1 > x0 and y1 > y0):
        return None
    y0 -= 1.2 * (y1 - y0)                      # headroom for an airborne ball
    x0, y0 = max(0.0, x0 - pad_px), max(0.0, y0 - pad_px)
    x1, y1 = min(float(W), x1 + pad_px), min(float(H), y1 + pad_px)
    if x1 - x0 < 32 or y1 - y0 < 32:
        return None
    return int(x0), int(y0), int(x1), int(y1)


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
                 static_step_px: Optional[float] = None,
                 static_min_run: Optional[int] = None,
                 fps: float = 30.0, cam_xyz=None,
                 max_ball_height_m: float = 6.0):
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
        #
        # MEASURED: raising acquire_bound_m 4 -> 10 (matching continue) is NOT worth
        # it, despite a static analysis predicting it would be free. Evaluated at the
        # gold clicks, the 4 m envelope can seed from only 62.9% of real ball
        # positions and 0 of 13 far-court ones, versus 88.6% / 13 of 13 at 10 m — but
        # end to end on am_hard_utr that bought almost nothing, because a track
        # rejected on one frame re-acquires a frame or two later anyway:
        #     acquire 4 m   FULL recall 43.4%  far_geo 47.5%  false-fire 7.5%
        #     acquire 10 m  FULL recall 44.0%  far_geo 48.2%  false-fire 9.4%
        # +0.6 pt of recall for +1.9 pt of false-fire — and on 53 no-ball frames that
        # is literally one extra fire. Both inside noise. The acquire-rejection count
        # did halve (694 -> 308), which is why the static prediction looked good; it
        # simply is not the binding constraint. Per-gate counters (n_rej_court_acq et
        # al) exist now, so this is re-measurable rather than re-arguable.
        self.Hinv = None if homography is None else np.linalg.inv(np.asarray(homography, float))
        self.acquire_bound_m = acquire_bound_m
        self.continue_bound_m = continue_bound_m
        # Camera position in court metres (x, y, height) — lets the court gate
        # allow for ball height instead of assuming z=0. Without it the gate
        # degrades to the old ground-plane test.
        self.cam_xyz = None if cam_xyz is None else np.asarray(cam_xyz, float)
        self.max_ball_height_m = float(max_ball_height_m)
        self.bg = background
        self.inv_scale = inv_scale
        self.use_bgsub = use_bgsub and background is not None
        # Association radius, in pixels — so it depends on the frame size. 70 px was
        # tuned at 1280x720; at 1080p the same physical ball travels 1.5x as far
        # between frames, and a frozen radius rejects the fastest REAL balls as
        # off-path. Same failure the court-region gate had. Identity at 720p.
        self.gate = gate * (self.H / 720.0)
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
        #
        # BOTH thresholds are TIME quantities, expressed per frame (Session E3c).
        # They were hard-coded at 3 px/frame over 5 frames — values tuned on 30 fps
        # footage — and then applied unchanged at 60 fps, where the same physical
        # motion covers half the pixels per frame and the run fills in half the
        # time. Measured on yt_rally2 @60fps: 36.3% of far-court ball steps fall
        # under 3 px/frame (near court: 8.5%), so the gate was eating the far ball
        # exactly where it is hardest to see. The old comment claimed "moving balls
        # never trip it" — true at 30 fps, false at 60. Scaling by fps keeps a real
        # fixture (0 px/frame at any rate) caught while letting a slow-looking far
        # ball through.
        self.fps = float(fps) if fps and fps > 0 else 30.0
        self.static_step_px = (STATIC_STEP_PX_PER_S / self.fps
                               if static_step_px is None else static_step_px)
        self.static_min_run = (max(2, int(round(STATIC_MIN_RUN_S * self.fps)))
                               if static_min_run is None else static_min_run)
        self.static_run = 0
        self.static_anchors: list = []
        self.n_static = 0   # fixture zones found (for the analyze log)
        # WHY a frame produced no lock. The counters above all count successes, so
        # a missing ball was previously unattributable — the difference between
        # "the detector never saw it" and "we gated it away" had to be inferred.
        self.n_no_det = 0          # no detector fired at all
        self.n_rej_court_acq = 0   # a detection existed, court gate rejected it (acquiring)
        self.n_rej_court_cont = 0  # ...rejected while continuing a track
        self.n_rej_static = 0      # survived the court gate, failed the fixture test
        self.n_rej_vel = 0         # on-court and moving, but off the predicted path
        self.n_untracked = 0       # frames entered with no live track

    def _court_ok(self, pt, acquiring: bool) -> bool:
        """Court-plausibility of an image-space candidate, allowing for BALL HEIGHT.

        The old test back-projected the candidate to the ground plane and required
        that point to land near the court. But a ball in flight is not on the
        ground, and its ground back-projection lands far past the court — further
        the lower the camera and the further from it the ball is. `camera_height_m`
        warned about exactly this ("a LOW camera sends it tens of metres past"),
        and the pipeline's 3.0 m minimum was far too permissive: on yt_rally2 the
        camera is 3.31 m and this gate cost **22.9 points of ball recall**
        (measured, gate ablation: 49.2% -> 72.1% hit@10 with it disabled) — nearly
        the entire gap between the detector's output and our shipped track.

        The honest test is a cone, not a point. The true ball lies somewhere on the
        viewing ray; as its height z rises from 0 to `max_ball_height_m`, its court
        position slides linearly from the ground back-projection G toward the point
        directly under the camera. The candidate is plausible if ANY height on that
        segment puts it over the court. Crowd and scoreboard detections still fail
        it — no height puts them on the court — so the gate keeps its purpose.
        """
        if self.Hinv is None or pt is None:
            return True   # no homography available: gate disabled
        from . import court

        p = np.asarray([pt[0], pt[1], 1.0], dtype=float)
        q = self.Hinv @ p
        if abs(q[2]) < 1e-9:
            return False
        gx, gy = q[0] / q[2], q[1] / q[2]
        b = self.acquire_bound_m if acquiring else self.continue_bound_m

        def on_court(x, y):
            return (-b <= x <= court.DOUBLES_WIDTH + b) and (-b <= y <= court.LENGTH + b)

        if on_court(gx, gy):
            return True
        if self.cam_xyz is None:
            return False               # no camera pose: fall back to the plane test
        cx, cy, ch = self.cam_xyz
        if ch <= 0.2:
            return False
        # P(z) = C + ((h - z)/h) * (G - C); sample the segment z in [0, z_max].
        z_max = min(self.max_ball_height_m, 0.95 * ch)
        for i in range(1, 7):
            s = (ch - z_max * i / 6.0) / ch
            if on_court(cx + s * (gx - cx), cy + s * (gy - cy)):
                return True
        return False

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
        if acquiring:
            self.n_untracked += 1
        raw = [d for d in dets if d is not None]
        if not raw:
            self.n_no_det += 1
        # Court-plausibility gate: drop candidates whose ground back-projection is
        # nowhere near the court (crowd, scoreboard, birds) BEFORE the velocity
        # logic sees them — smooth off-court drift must never extend a track.
        on_court = [d for d in raw if self._court_ok(d, acquiring)]
        if raw and not on_court:
            # Attribute the loss to the mode that caused it: the ACQUIRE envelope is
            # much tighter than the continue one, so a frame rejected while acquiring
            # is a track that never got to start.
            if acquiring:
                self.n_rej_court_acq += 1
            else:
                self.n_rej_court_cont += 1
        model_cands = [d for d in on_court if self._static_ok(d)]
        if on_court and not model_cands:
            self.n_rej_static += 1
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
                else:
                    self.n_rej_vel += 1
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
