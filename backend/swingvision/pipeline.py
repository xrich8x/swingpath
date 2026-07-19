"""pipeline.py — orchestrator + synthetic demo generator.

Two entry points:
  - generate_demo_match(): builds a believable match.json with no model weights,
    by simulating rallies on the real court geometry and running them through the
    real analytics (speed, line calls) and scoring. This is what `run.py demo`
    writes for the dashboard.
  - analyze_video(): the real path. Calibration (geometry) is ready; the
    per-frame perception loop (ball + pose) is the stubbed seam.

The demo is deliberately built on the *real* layers — court geometry,
analytics.line_call, analytics.shot_speed_kmh, scoring.TennisScore — so the data
exercises the same code a real clip would.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from . import analytics, calibration, court, scoring
from .schema import (
    Match,
    Player,
    Rally,
    Score,
    ScoreEvent,
    Shot,
    TrackPoint,
    Video,
    compute_stats,
    validate,
)

_OTHER = {"A": "B", "B": "A"}


def _rand(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(rng.uniform(lo, hi))


# Demo serve-placement mix — roughly pro reference (~30% T, ~25% wide, rest body).
# Just for believable synthetic data; the real placement stat is measured, not set.
_SERVE_BANDS = (("T", 0.30), ("wide", 0.25), ("body", 0.45))


def _serve_band_x(rng, x_lo: float, x_hi: float) -> float:
    """Sample an in-serve x inside one service box, biased to realistic bands.

    The box spans [x_lo, x_hi] (one half of the singles width). T hugs the centre
    service line, wide hugs the singles sideline, body is the middle — each ~0.7 m,
    matching analytics.serve_placement's definition so the demo's placement stats
    land in the band it aimed for.
    """
    left_box = x_lo < court.X_CENTER
    r, cum, band = rng.random(), 0.0, "body"
    for name, p in _SERVE_BANDS:
        cum += p
        if r <= cum:
            band = name
            break
    if band == "T":
        b_lo, b_hi = (court.X_CENTER - 0.7, court.X_CENTER) if left_box else \
                     (court.X_CENTER, court.X_CENTER + 0.7)
    elif band == "wide":
        b_lo, b_hi = (court.X_LEFT_SINGLES, court.X_LEFT_SINGLES + 0.7) if left_box else \
                     (court.X_RIGHT_SINGLES - 0.7, court.X_RIGHT_SINGLES)
    else:  # body — the ~2.6 m between the two bands
        b_lo, b_hi = (court.X_LEFT_SINGLES + 0.7, court.X_CENTER - 0.7) if left_box else \
                     (court.X_CENTER + 0.7, court.X_RIGHT_SINGLES - 0.7)
    return _rand(rng, b_lo + 0.08, b_hi - 0.08)   # small inset keeps it clearly in


def _serve_box(rng, striker: str, out: bool) -> list[float]:
    """Bounce target for a serve: a realistic spot in the diagonal service box.

    The server alternates deuce/ad court; the cross-court serve lands in the
    matching box. A faulted serve lands long past the service line.
    """
    serve_side = "deuce" if rng.random() < 0.5 else "ad"
    if striker == "A":                 # near player, serving to the far boxes
        y_lo, y_hi = court.NET_Y, court.Y_FAR_SERVICE
        long_y = y_hi + _rand(rng, 0.3, 1.0)
        left_box = serve_side == "deuce"   # A's deuce court -> far LEFT box
    else:                              # far player, serving to the near boxes
        y_lo, y_hi = court.Y_NEAR_SERVICE, court.NET_Y
        long_y = y_lo - _rand(rng, 0.3, 1.0)
        left_box = serve_side == "ad"      # B's ad court -> near LEFT box
    x_lo, x_hi = (court.X_LEFT_SINGLES, court.X_CENTER) if left_box else \
                 (court.X_CENTER, court.X_RIGHT_SINGLES)
    if out:
        return [_rand(rng, x_lo, x_hi), long_y]   # long fault (not placed)
    return [_serve_band_x(rng, x_lo, x_hi), _rand(rng, y_lo + 0.5, y_hi - 0.4)]


def _groundstroke_bounce(rng, striker: str, out: bool) -> list[float]:
    """Bounce target for a rally shot: the opponent's half (or out)."""
    if striker == "A":
        y_lo, y_hi = court.NET_Y + 0.4, court.Y_FAR_BASELINE
        long_y = court.Y_FAR_BASELINE + _rand(rng, 0.2, 0.9)
    else:
        y_lo, y_hi = court.Y_NEAR_BASELINE, court.NET_Y - 0.4
        long_y = court.Y_NEAR_BASELINE - _rand(rng, 0.2, 0.9)
    if out:
        if rng.random() < 0.5:  # long
            return [_rand(rng, court.X_LEFT_SINGLES, court.X_RIGHT_SINGLES), long_y]
        # wide
        if rng.random() < 0.5:
            x = court.X_RIGHT_SINGLES + _rand(rng, 0.2, 0.7)
        else:
            x = court.X_LEFT_SINGLES - _rand(rng, 0.2, 0.7)
        return [x, _rand(rng, y_lo, y_hi)]
    return [
        _rand(rng, court.X_LEFT_SINGLES + 0.3, court.X_RIGHT_SINGLES - 0.3),
        _rand(rng, y_lo, y_hi - 0.5),
    ]


def _hit_origin(rng, striker: str, is_serve: bool) -> list[float]:
    """Where the striker contacts the ball, near their baseline."""
    x = _rand(rng, 1.4, 9.5)
    if striker == "A":
        y = 0.3 if is_serve else _rand(rng, 0.2, 3.5)
    else:
        y = court.LENGTH - 0.3 if is_serve else _rand(rng, court.LENGTH - 3.5, court.LENGTH - 0.2)
    return [x, y]


def _simulate_point(rng, server: str, clock: float):
    """Simulate one point. Returns (shots, winner, end_clock).

    `shots` are dicts with raw fields; the caller assigns global ids. Speed and
    the in/out call come from the real analytics functions, so the demo data is
    consistent with how a real clip would be measured.
    """
    striker = server
    shots: list[dict] = []
    t = clock
    winner: Optional[str] = None
    max_shots = 9

    for k in range(max_shots):
        is_serve = k == 0
        if is_serve:
            shot_type = "serve"
            p_out = 0.12
        else:
            shot_type = "forehand" if rng.random() < 0.6 else "backhand"
            p_out = 0.13
        out = rng.random() < p_out

        hit_xy = _hit_origin(rng, striker, is_serve)
        bounce_xy = (
            _serve_box(rng, striker, out) if is_serve else _groundstroke_bounce(rng, striker, out)
        )

        dist = float(np.hypot(bounce_xy[0] - hit_xy[0], bounce_xy[1] - hit_xy[1]))
        target_ms = _rand(rng, 34, 42) if is_serve else _rand(rng, 20, 30)
        flight = max(0.30, dist / target_ms)
        t_hit = t
        bounce_t = t_hit + flight

        speed = analytics.shot_speed_kmh([(t_hit, *hit_xy), (bounce_t, *bounce_xy)])
        call = analytics.line_call(bounce_xy, shot_type=shot_type, singles=True)

        shots.append(
            {
                "player": striker,
                "type": shot_type,
                "t_hit_s": round(t_hit, 2),
                "speed_kmh": round(speed, 1),
                "hit_xy": [round(hit_xy[0], 3), round(hit_xy[1], 3)],
                "bounce_xy": [round(bounce_xy[0], 3), round(bounce_xy[1], 3)],
                "bounce_t_s": round(bounce_t, 2),
                "is_in": call == "in",
                "call": call,
            }
        )

        # Resolve the outcome of this shot.
        if call == "out":
            winner = _OTHER[striker]  # error: the striker loses the point
            break
        if not is_serve and rng.random() < 0.20:
            winner = striker  # clean winner the opponent can't return
            break

        # Ball is in and returned: opponent moves to it and becomes the striker.
        t = bounce_t + _rand(rng, 0.35, 0.65)
        striker = _OTHER[striker]

    if winner is None:
        winner = striker  # rally hit the length cap; last striker wins
    return shots, winner, t + _rand(rng, 0.4, 0.8)


def _ball_track(shots: list[dict]) -> list[TrackPoint]:
    """Sample a continuous ball track (10 Hz) through a point's waypoints."""
    ts: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    for s in shots:
        ts += [s["t_hit_s"], s["bounce_t_s"]]
        xs += [s["hit_xy"][0], s["bounce_xy"][0]]
        ys += [s["hit_xy"][1], s["bounce_xy"][1]]
    if len(ts) < 2:
        return []
    sample_t = np.arange(ts[0], ts[-1] + 1e-6, 0.1)
    sx = np.interp(sample_t, ts, xs)
    sy = np.interp(sample_t, ts, ys)
    return [
        TrackPoint(t_s=round(float(t), 2), xy=[round(float(x), 3), round(float(y), 3)])
        for t, x, y in zip(sample_t, sx, sy)
    ]


def generate_demo_match(seed: int = 7, max_points: int = 42) -> Match:
    """Build a synthetic but realistic match.json (no model weights)."""
    rng = np.random.default_rng(seed)
    players = [Player(id="A", name="Player A"), Player(id="B", name="Player B")]
    score = scoring.TennisScore(player_a="A", player_b="B")

    shots: list[Shot] = []
    rallies: list[Rally] = []
    timeline: list[ScoreEvent] = []

    clock = 2.0
    shot_id = 0
    server = "A"

    for rally_id in range(max_points):
        raw_shots, winner, clock_end = _simulate_point(rng, server, clock)

        rally_shot_ids: list[int] = []
        start_s = raw_shots[0]["t_hit_s"]
        end_s = raw_shots[-1]["bounce_t_s"]
        for rs in raw_shots:
            shots.append(
                Shot(
                    id=shot_id,
                    rally_id=rally_id,
                    player=rs["player"],
                    type=rs["type"],
                    t_hit_s=rs["t_hit_s"],
                    speed_kmh=rs["speed_kmh"],
                    hit_xy=rs["hit_xy"],
                    bounce_xy=rs["bounce_xy"],
                    bounce_t_s=rs["bounce_t_s"],
                    is_in=rs["is_in"],
                    call=rs["call"],
                )
            )
            rally_shot_ids.append(shot_id)
            shot_id += 1

        rallies.append(
            Rally(
                id=rally_id,
                start_s=round(start_s, 2),
                end_s=round(end_s, 2),
                shot_ids=rally_shot_ids,
                winner=winner,
                ball_track=_ball_track(raw_shots),
            )
        )

        result = score.point(winner)
        timeline.append(
            ScoreEvent(
                shot_id=rally_shot_ids[-1],
                rally_id=rally_id,
                point_winner=winner,
                display=result.display,
                games_display=result.games_display,
                sets_display=result.sets_display,
            )
        )

        # Server changes each game; rotate when a game was just won.
        if result.game_won:
            server = _OTHER[server]
        clock = clock_end + _rand(rng, 6.0, 12.0)  # changeover / walk between points
        if score.finished:
            break

    duration = round(clock, 1)
    video = Video(
        filename="demo_synthetic.mp4",
        fps=30.0,
        width=1920,
        height=1080,
        duration_s=duration,
    )
    score_block = Score(
        final=score.final_str(),
        sets=[list(s) for s in score.completed_sets],
        games=list(score.games),
        timeline=timeline,
    )
    stats = compute_stats(shots, rallies)
    return Match(
        video=video,
        players=players,
        shots=shots,
        rallies=rallies,
        score=score_block,
        stats=stats,
    )


def write_demo_match(out_path: str, seed: int = 7) -> Match:
    """Generate the demo match and write it to `out_path` as JSON."""
    match = generate_demo_match(seed=seed)
    data = match.to_dict()
    problems = validate(data)
    if problems:
        raise ValueError("demo match failed schema validation:\n  " + "\n  ".join(problems))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return match


# --- Real analysis ----------------------------------------------------------
def _read_first_frame(video_path: str):
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path!r}")
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"could not read a frame from {video_path!r}")
    return frame


def _cam_row_to_A(row):
    """Stored cam_motion row -> 3x3 camera-motion matrix. Rows are 6 numbers
    (affine, older caches) or 9 (full 3x3 - watchdog rebases after a detected
    camera change are projective)."""
    vals = np.asarray(row, dtype=float)
    if vals.size == 9:
        return vals.reshape(3, 3)
    A = np.eye(3)
    A[:2, :] = vals.reshape(2, 3)
    return A


def _sample_calib_frames(video_path: str, k: int = 8):
    """K frames spread across the clip (2%..98%) for consensus calibration."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    idxs = (np.linspace(0.02 * n, max(0.02 * n, 0.98 * n - 1), k).astype(int)
            if n > k else [0])
    frames = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, im = cap.read()
        if ok:
            frames.append(im)
    cap.release()
    return frames


def _estimate_lens_k1(video_path, first_frame, H):
    """Clip-level lens estimate for calibrate_video: the first frame plus a few
    sampled ones, court-line-matched through H, judged by the cross-frame
    honesty gate (calibration.estimate_k1_frames - a real lens reads the same
    on every frame; scatter is speckle and gets refused). Prints the verdict."""
    frames = [first_frame] + _sample_calib_frames(video_path, k=4)
    k1, meds = calibration.estimate_k1_frames(frames, H=H)
    if k1:
        print(f"[calibration] lens: radial distortion k1={k1:+.3f} (consistent "
              f"over {len(meds)} frames) - projections are lens-corrected")
    elif meds:
        print(f"[calibration] lens: no consistent radial distortion (per-frame "
              f"reads {min(meds):+.3f}..{max(meds):+.3f}) - no correction")
    return k1


def calibrate_video(
    video_path: str,
    keypoints_path: Optional[str] = None,
    overlay_path: Optional[str] = None,
):
    """Calibrate a clip: manual keypoints JSON, else tiered auto-detection
    (consensus line-fit -> learned -> classical -> refuse). Optionally writes an
    overlay preview. Returns (H, reprojection_error_px, source, named_corners,
    cam_hfov_deg, lens_k1, H_und):
      * H / named_corners live in the frame's real (distorted) pixel space -
        everything that compares against pixels (lock step, watchdog, masks)
        keeps using them;
      * lens_k1 is the division-model radial distortion read off the court's
        own lines (0.0 = none detected / refused as inconsistent);
      * H_und (only when lens_k1 != 0) is the PINHOLE homography fitted on the
        undistorted corners - metric projections should undistort points and
        use it (see analyze_video);
      * cam_hfov_deg is the lens field-of-view from the physical camera lock
        (None when the lock could not be applied)."""
    from . import calibration, courtfit

    frame = _read_first_frame(video_path)
    source = "manual"
    named = None

    manual_exact = False
    if keypoints_path:
        with open(keypoints_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # "_exact": the overlay tool's shape-lock-OFF save — the user deliberately
        # placed these corners (e.g. a wide lens bends the real lines away from
        # any pinhole view). Their placement is final: no snap, no shape lock.
        manual_exact = bool(raw.pop("_exact", False))
        named = {k: v for k, v in raw.items() if not k.startswith("_")}
    else:
        # TIER 1: line-fit CONSENSUS auto-calibration (courtfit; the measured
        # best on amateur footage). The court is static, so fit K frames
        # independently and trust only a court that reproduces. >=6/8 agreeing
        # frames has always been a correct court on the gold set + cold tests;
        # anything below is NOT auto-accepted (overlay confirm instead).
        frames = _sample_calib_frames(video_path, k=8)
        pts, votes, tag = None, 0, None
        if frames:
            print(f"[calibration] auto-detecting the court on {len(frames)} "
                  "frames (one-time)...")
            pts, votes, tag = courtfit.fit_video_frames(frames, calibration, court)
        if pts is not None and tag == "vote" and votes >= 6:
            named = pts
            source = f"auto-court({votes}/{len(frames)})"
        else:
            # TIER 2 fallbacks: learned keypoint model (broadcast framings;
            # self-rejects when unsure) -> classical detector -> refuse with the
            # exact overlay-tool command (it opens PRE-FITTED, so confirming a
            # low-confidence court takes seconds).
            det = None
            try:
                det = calibration.detect_court_learned(frame)
            except FileNotFoundError:
                det = None
            if det is not None:
                named = {n: list(xy) for n, xy in det.keypoints.items()}
                source = "learned"
            else:
                detected = calibration.detect_court_keypoints(frame)
                if detected is None:
                    hint = (
                        f"the best court was confirmed on only {votes} of "
                        f"{len(frames)} frames (needs 6)" if pts is not None
                        else "no court could be confirmed across frames")
                    raise ValueError(
                        f"auto court calibration did not reach high confidence "
                        f"({hint}). Set the court once with the overlay tool:\n"
                        f'  backend/.venv/Scripts/python.exe tools/court_setup_server.py '
                        f'--video "{video_path}" --out court_pts.json\n'
                        "(opens pre-fitted - drag to adjust, Snap, Save), then "
                        "re-run with --keypoints court_pts.json"
                    )
                named = {n: list(xy) for n, xy in detected.items()}
                source = "auto-classical"

    H = calibration.homography_from_landmarks(named)
    cam_hfov_deg = None
    k1, H_und = 0.0, None
    w_img, h_img = frame.shape[1], frame.shape[0]

    def _undistorted_H(pts):
        und = {n: [float(v) for v in
                   calibration.undistort_points([xy], k1, (w_img, h_img))[0]]
               for n, xy in pts.items()}
        return calibration.homography_from_landmarks(und)

    if manual_exact:
        source = "manual-exact"
        print("[calibration] exact manual calibration (user-placed corners are "
              "final; snap and shape lock skipped)")
        k1 = _estimate_lens_k1(video_path, frame, H)
        if k1:
            H_und = _undistorted_H(named)   # corners stay final; lens still honest
    else:
        # Snap the corners onto the real lines (amateur-robust), guarded: white
        # lines first, then the hue-agnostic CLAY retry when white refuses (worn
        # or colour-tinted paint), kept only if coverage clears the bar under
        # the same mask. Halves court error on hard/indoor (eval_court_snap).
        H_snap, named_snap, snapped, snap_tag, cov1 = courtfit.snap_court(
            frame, named, calibration, court)
        if snapped:
            H, named = H_snap, named_snap
            source += "+" + snap_tag
            print(f"[calibration] snapped to lines ({snap_tag}): coverage {cov1:.2f}")
        else:
            print(f"[calibration] line-snap not applied (coverage {cov1:.2f}); "
                  "using clicks as-is")

        # LENS: read radial distortion off the paint the snap just aligned to.
        # On a k1 lens the on-paint corners are NOT a pinhole camera's view, so
        # undistort them BEFORE the shape lock - locking first would force a
        # pinhole shape onto bent evidence and displace the whole court.
        k1 = _estimate_lens_k1(video_path, frame, H)

        # HARD SHAPE RULE (every source, manual clicks included): never ship a
        # court no real camera could see. Applied in pinhole space (undistorted
        # corners) when a lens was measured, directly otherwise. The lock also
        # yields the honest lens zoom (focal_from_homography is degenerate on
        # telephoto views).
        lock = courtfit.shape_lock(_undistorted_H(named) if k1 else H,
                                   calibration, court, w_img, h_img)
        if lock["applied"]:
            cam_hfov_deg = lock["hfov_deg"]
            if k1:
                H_und = lock["H"]
                # machinery H / stored corners = the locked pinhole court seen
                # back through the measured lens (real, distorted pixel space)
                named = {n: [float(v) for v in calibration.distort_points(
                    [calibration.court_to_image(H_und, [court.LANDMARKS[n]])[0]],
                    k1, (w_img, h_img))[0]] for n in named}
                H = calibration.homography_from_landmarks(named)
            else:
                H = lock["H"]
            if lock["moved_max"] > 3.0:
                print(f"[calibration] shape-locked to a physical camera view "
                      f"(corners moved up to {lock['moved_max']:.1f}px - the "
                      "input shape was not quite a real camera's view of a "
                      "regulation court)")
        else:
            # No physical camera lands near this shape. The placement stays
            # authoritative - but say so plainly rather than silently
            # "correcting" toward a possibly-wrong court.
            if k1:
                H_und = _undistorted_H(named)
            gap = (f" (nearest physical view is {lock['gap_px']:.0f}px away)"
                   if lock["gap_px"] is not None else "")
            print("[calibration] WARNING: this court shape could not be verified "
                  f"as a real camera's view of a regulation court{gap}; keeping "
                  "it as given - re-check the overlay preview")

    err = calibration.reprojection_error(
        H, [court.LANDMARKS[n] for n in named], [named[n] for n in named]
    )
    print(f"[calibration] source={source}; reprojection error = {err:.2f} px")

    if overlay_path:
        from . import overlay as overlay_mod

        overlay_mod.render_overlay_image(frame, H_und if k1 else H,
                                         overlay_path, k1=k1)
        print(f"[calibration] overlay preview -> {overlay_path}")
    return H, err, source, named, cam_hfov_deg, k1, H_und


def _probe_ball_model(video_path, ball_weights, device, frame_step, max_frames,
                      n_windows: int = 8, window: int = 6):
    """Pick the ball detector empirically for THIS footage: run TrackNet and WASB
    over a few short frame windows spread across the clip and keep whichever fires
    more (ties -> fusion). ~30s once, instead of a long run with a blind model."""
    import cv2

    from .ball import BallDetector, WASBDetector

    dets = {"tracknet": BallDetector(ball_weights, device=device),
            "wasb": WASBDetector(device=device)}
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    last = (min(total, max_frames) if max_frames else total) - 1
    starts = np.linspace(0, max(0, last - window * frame_step), n_windows).astype(int)
    scores = {k: 0 for k in dets}
    for s in starts:
        for d in dets.values():
            d.reset()
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(s))
        fed = 0
        while fed < window:
            ok, frame = cap.read()
            if not ok:
                break
            for k, d in dets.items():
                # First two frames only fill the 3-frame buffers; score the rest.
                if d.detect(frame) is not None and fed >= 2:
                    scores[k] += 1
            fed += 1
    cap.release()
    print(f"[analyze] ball-model probe: tracknet={scores['tracknet']} "
          f"wasb={scores['wasb']} (of ~{n_windows * (window - 2)} chances)")
    if abs(scores["tracknet"] - scores["wasb"]) <= n_windows // 2:
        return "fusion"   # close call: run both
    return max(scores, key=scores.get)


def _reject_static_player(positions, kpts, label, min_move_px: float = 12.0):
    """Null a player track that barely moves over the clip.

    Selection can fall back to a person-shaped static object (poster, fixture)
    when the real player is undetectable; movement is the discriminator — over a
    rally even a lazy player shifts tens of pixels. Measured in IMAGE space from
    the keypoints (court-metre displacement is useless here: far-court m/px
    amplification turns pose jitter on a fixture into fake metres). Below
    `min_move_px` (90th-percentile displacement from the median body centre) the
    whole track is wiped.
    """
    idx, centres = [], []
    for i, k in enumerate(kpts):
        if not k:
            continue
        pts = [(x, y) for x, y, c in k if c > 0.3]
        if pts:
            idx.append(i)
            centres.append(np.mean(pts, axis=0))
    if len(centres) < 10:
        return positions, kpts
    arr = np.asarray(centres, dtype=float)
    n = len(arr)
    # A fixture shows up as MANY samples piled in one small image neighbourhood.
    # A real player pauses between points but never spends >35% of a clip within
    # ~20 px, and never revisits the exact ±8 px spot across long spans. Null the
    # frames in such neighbourhoods; keep the rest (tracks can be mixtures of the
    # real player and a fixture the selector fell back to).
    drop = set()
    frames = np.asarray(idx)
    coverage = n / max(len(kpts), 1)
    for j in range(n):
        d = np.hypot(arr[:, 0] - arr[j, 0], arr[:, 1] - arr[j, 1])
        near20 = d < 20.0
        near8 = d < 8.0
        # ±8 px recurrence across a long span flags a fixture — but only on SPARSE
        # tracks (fixtures are fallbacks that appear when the real player is
        # missed). A well-tracked real player legitimately returns to the same
        # ready position all clip, so dense tracks skip this rule.
        span8 = frames[near8].max() - frames[near8].min() if near8.sum() >= 2 else 0
        if near20.sum() > 0.35 * n or (coverage < 0.5 and near8.sum() >= 4 and span8 > 240):
            drop.add(idx[j])
    if drop:
        print(f"[analyze] {label} player: dropped {len(drop)}/{n} static-fixture frames")
        positions = [None if i in drop else p for i, p in enumerate(positions)]
        kpts = [None if i in drop else k for i, k in enumerate(kpts)]
    # After cleanup, a track seen in <15% of frames is detection noise, not a
    # player (a genuinely visible player tracks at 60%+): drop the remnants
    # rather than let a handful of misfires drive skeletons and movement stats.
    remaining = sum(1 for k in kpts if k)
    if 0 < remaining < 0.15 * len(kpts):
        print(f"[analyze] {label} player: only {remaining}/{len(kpts)} frames left -> "
              f"track dropped (not reliably visible)")
        return [None] * len(positions), [None] * len(kpts)
    return positions, kpts


def _estimate_cam_step(prev_gray, gray, boxes, scale: float = 0.25):
    """Frame-to-frame camera motion as a 3x3 similarity (pan/zoom).

    DENSE ECC alignment on downscaled frames, players masked out. Dense is the
    point: sparse corner features latch onto STATIC UI graphics burned into
    consumer footage (scoreboards, watermarks — e.g. SwingVision's own overlay),
    and RANSAC then reports "no motion" while the scene pans/zooms underneath.
    ECC weighs every pixel, so the bulk scene dominates a few UI regions.
    Returns identity on failure — a wrong step is worse than assuming stillness.
    """
    import cv2

    try:
        h, w = prev_gray.shape
        sw, sh = int(w * scale), int(h * scale)
        p = cv2.resize(prev_gray, (sw, sh)).astype(np.float32)
        g = cv2.resize(gray, (sw, sh)).astype(np.float32)
        mask = np.full((sh, sw), 255, dtype=np.uint8)
        for b in boxes or []:
            if b is None:
                continue
            x1, y1, x2, y2 = (int(v * scale) for v in b)
            mask[max(0, y1 - 5):y2 + 5, max(0, x1 - 5):x2 + 5] = 0
        warp = np.eye(2, 3, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 1e-5)
        _, warp = cv2.findTransformECC(p, g, warp, cv2.MOTION_AFFINE, criteria,
                                       inputMask=mask, gaussFiltSize=5)
        A = np.eye(3)
        A[:2, :] = warp
        # Rescale the translation back to full resolution (rotation is scale-free).
        A[0, 2] /= scale
        A[1, 2] /= scale
        return A
    except Exception:
        return np.eye(3)


# --- Perception-cache provenance --------------------------------------------
# The archived demo30 cache (HANDOFF.md §6) could not be traced back to the
# model/device/calibration that built it. Every cache written from now on
# records how it was built; loading one under different settings warns out loud
# instead of silently reusing a track the current settings would not reproduce.

COURT_GATE_MIN_CAM_H = 3.0  # metres; court-plausibility gate needs this camera height


def _file_fingerprint(path):
    """Short sha256 (12 hex chars) of a file, or None if it can't be read."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:12]
    except OSError:
        return None


def _homography_fingerprint(H):
    """Short sha256 of the normalized court homography — ties a cache to the
    exact calibration it was built under (homographies are scale-free, so
    normalize by H[2,2] before hashing)."""
    Hn = np.asarray(H, dtype=np.float64)
    if Hn[2, 2]:
        Hn = Hn / Hn[2, 2]
    return hashlib.sha256(np.round(Hn, 6).tobytes()).hexdigest()[:12]


def _git_commit():
    """Repo commit id ('-dirty' suffix if there are uncommitted edits), or None."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty"],
                             cwd=root, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:
        return None


def _build_provenance(ball_model, weight_files, pose_model, device,
                      camera_hfov_deg, cam_h, gate_on, H,
                      static_gate=(3.0, 5)):
    """The 'how was this cache built' stamp stored inside every new cache."""
    return {
        "ball_model": ball_model,
        "pose_model": pose_model,
        "weights": {name: {"path": p, "sha256": _file_fingerprint(p)}
                    for name, p in weight_files.items() if p},
        "device": device,
        "camera_hfov_deg": round(float(camera_hfov_deg), 2),
        "court_gate_min_cam_h_m": COURT_GATE_MIN_CAM_H,
        "static_gate_step_px_min_run": [float(static_gate[0]), int(static_gate[1])],
        "camera_height_m": round(float(cam_h), 2) if cam_h is not None else None,
        "court_gate_on": bool(gate_on),
        "homography_sha256": _homography_fingerprint(H),
        "git_commit": _git_commit(),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _provenance_mismatches(prov, device, camera_hfov_deg, H):
    """Compare a cache's recorded build parameters against the current run.
    Returns plain-English difference lines (empty list = everything matches)."""
    diffs = []
    if prov.get("device") and prov["device"] != device:
        diffs.append(f"device: cache was built on {prov['device']}, "
                     f"this run uses {device}")
    rec_hfov = prov.get("camera_hfov_deg")
    if rec_hfov is not None and abs(rec_hfov - float(camera_hfov_deg)) > 0.05:
        diffs.append(f"camera hfov: cache was built at {rec_hfov} deg, "
                     f"this run uses {float(camera_hfov_deg):.2f} deg")
    rec_gate = prov.get("court_gate_min_cam_h_m")
    if rec_gate is not None and abs(rec_gate - COURT_GATE_MIN_CAM_H) > 1e-9:
        diffs.append(f"court-gate height threshold: cache used {rec_gate} m, "
                     f"the code now uses {COURT_GATE_MIN_CAM_H} m")
    rec_h = prov.get("homography_sha256")
    if rec_h and rec_h != _homography_fingerprint(H):
        diffs.append("court calibration: the homography/keypoints differ from "
                     "the ones the cache was built under")
    for name, w in (prov.get("weights") or {}).items():
        if w.get("sha256") and w.get("path"):
            now = _file_fingerprint(w["path"])
            if now is not None and now != w["sha256"]:
                diffs.append(f"model weights: {name} ({w['path']}) has CHANGED "
                             f"on disk since the cache was built")
    return diffs


def _perceive(video_path, H, ball_weights, pose_quality, pose_every, device,
              max_frames, frame_step, cache_path, use_bgsub=True, ball_model="tracknet",
              camera_hfov_deg=70.0):
    """Run ball + pose over every `frame_step`-th frame (or load a cached run).
    Returns (ball_px, near_court, far_court) for the processed frames.

    Stepping keeps the frames fed to TrackNet consecutive *among themselves* — at
    frame_step=2 on 60fps footage that's 30fps, which is TrackNet's training rate.

    Ball detection fuses TrackNet with a fixed-camera background-subtraction
    fallback (BallTracker) when use_bgsub is set, recovering the fast motion-blurred
    frames TrackNet misses (locked-ball rate ~75% -> ~95% on a static camera).
    """
    import time

    import cv2

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            c = json.load(f)
        if (c.get("frame_step") == frame_step and c.get("max_frames") == max_frames
                and c.get("bgsub", False) == bool(use_bgsub)
                and c.get("pose_quality") == pose_quality
                and (ball_model == "auto" or c.get("ball_model", "tracknet") == ball_model)
                and "cam_motion" in c):
            print(f"[analyze] loaded cached perception <- {cache_path}")
            prov = c.get("provenance")
            if not prov:
                print("[analyze] NOTE: this cache predates provenance stamping - "
                      "there is no record of the model/device/calibration that "
                      "built it, so reproducibility cannot be checked.")
            else:
                diffs = _provenance_mismatches(prov, device, camera_hfov_deg, H)
                if diffs:
                    print("[analyze] WARNING: reusing a cached perception that "
                          "was built under DIFFERENT settings:")
                    for d in diffs:
                        print(f"[analyze]   - {d}")
                    print(f"[analyze] The cached ball/player track may not match "
                          f"what this run would produce. Delete {cache_path} to "
                          f"redo perception under the current settings.")
                cur = _git_commit()
                if prov.get("git_commit") and cur and prov["git_commit"] != cur:
                    print(f"[analyze] note: cache was built at code version "
                          f"{prov['git_commit']}; you are now on {cur}")
            tup = lambda v: tuple(v) if v else None
            n = len(c["ball_px"])
            return ([tup(p) for p in c["ball_px"]],
                    [tup(p) for p in c["near_court"]],
                    [tup(p) for p in c["far_court"]],
                    c.get("near_kpts", [None] * n),
                    c.get("far_kpts", [None] * n),
                    c["cam_motion"],
                    c.get("player_counts", []),
                    c.get("court_events", []))

    from .ball import BallDetector, WASBDetector, BallTracker, median_background
    from . import pose as pose_mod

    # Ball model(s): TrackNet, WASB (HRNet, faster), fusion of both, or "auto" —
    # probe a few frame windows with each and keep the one that actually fires on
    # THIS footage. The models have opposite domain biases (TrackNet ~75% broadcast
    # / ~16% amateur-720p; WASB ~50% broadcast / ~71% amateur), so a 30s probe
    # saves a blind quarter-hour run with the wrong model.
    if ball_model == "auto":
        ball_model = _probe_ball_model(video_path, ball_weights, device,
                                       frame_step, max_frames)
    detectors = []
    weight_files = {}   # name -> weight file actually loaded (provenance stamp)
    if ball_model in ("tracknet", "fusion", "all"):
        d = BallDetector(ball_weights, device=device)
        detectors.append(d)
        weight_files["tracknet"] = getattr(d, "weights_path", ball_weights)
    if ball_model in ("wasb", "fusion", "all"):
        d = WASBDetector(device=device)
        detectors.append(d)
        weight_files["wasb"] = getattr(d, "weights_path", None)
    if ball_model in ("ours", "all"):
        from .ball import OurBallDetector
        d = OurBallDetector(device=device)
        detectors.append(d)
        weight_files["ballnet"] = getattr(d, "weights_path", None)
    if not detectors:
        raise ValueError(f"unknown ball_model {ball_model!r}")
    print(f"[analyze] ball model: {ball_model} ({len(detectors)} detector(s))")
    estimator = pose_mod.PoseEstimator(quality=pose_quality, device=device)
    pose_w, pose_imgsz = pose_mod.QUALITY_PRESETS.get(
        pose_quality, pose_mod.QUALITY_PRESETS["fast"])
    pose_model = f"{pose_w}@{pose_imgsz}"
    weight_files["pose"] = pose_w  # auto-downloaded next to run.py on first use
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    bg, inv = (median_background(video_path, frame_step, max_frames) if use_bgsub else (None, 2.0))
    # With players masked out of the background candidates, the bridge can run
    # longer without drifting onto a body — but only if pose actually finds the
    # far player (accurate preset). Otherwise keep the conservative short bridge.
    bg_run_cap = 12 if pose_quality == "accurate" else 5
    # Court-plausibility gating is only sound from a HIGH camera (broadcast): from a
    # low phone mount (~2 m) an airborne ball's ground projection legitimately lands
    # tens of metres past the court, so the gate would eat real detections (measured
    # -30 pts recall on the amateur clip). The velocity gate + the renderer's
    # drawable mask still protect the low-camera case.
    # Threshold 3.0 m: tuned as 4.0 when heights came from an assumed 70° hfov;
    # focal self-calibration reads the same mounts ~25% lower (yt_rally2:
    # 4.4 -> 3.3 m), and the gate is empirically sound there — while a true phone
    # mount (~2 m) still reads well below 3.
    cam_h = calibration.camera_height_m(H, (width, height), camera_hfov_deg)
    gate_H = H if (cam_h is not None and cam_h >= COURT_GATE_MIN_CAM_H) else None
    print(f"[analyze] camera height ~{cam_h:.1f} m -> court gate "
          f"{'ON' if gate_H is not None else 'OFF (low camera)'}"
          if cam_h is not None else "[analyze] camera height unknown -> court gate OFF")
    tracker = BallTracker(detectors, (width, height), background=bg, inv_scale=inv,
                          use_bgsub=use_bgsub, max_bg_run=bg_run_cap, homography=gate_H)
    if use_bgsub and bg is not None:
        print(f"[analyze] background model built (fixed-camera ball recovery on, "
              f"player-masked, bridge<={bg_run_cap})")
    from . import courtfit

    ball_px, near_court, far_court = [], [], []
    near_kpts, far_kpts = [], []   # striker keypoints (image px) for shot-type classification
    cam_motion = []                # per-frame camera motion vs frame 0 (full 3x3 stored)
    player_counts = []             # (near, far) on-court people per pose frame -> singles/doubles
    court_events = []              # camera-change detections: reacquired / lost
    watchdog = courtfit.CourtWatchdog(calibration, court)
    WATCH_EVERY = 30               # coverage check cadence (processed frames)
    A = np.eye(3)
    last_near = last_far = None
    last_near_kp = last_far_kp = None
    last_boxes: list = []
    idx = processed = 0
    t0 = time.time()
    print(f"[analyze] perceiving (pose={pose_quality}, frame_step={frame_step}, pose_every={pose_every})...")
    while True:
        ok, frame = cap.read()
        if not ok or (max_frames is not None and idx >= max_frames):
            break
        if idx % frame_step == 0:
            # Camera motion first: virtual/broadcast cameras pan and zoom, and one
            # fixed homography drifts off the real lines. Global motion estimators
            # (sparse LK, dense ECC) both fail on consumer footage — burned-in UI
            # graphics dominate them — so track the COURT ITSELF: snap the running
            # homography onto the white lines each frame (bounded correction).
            # On watchdog frames build the line mask ONCE and share it between
            # the lock step (which zeroes player boxes in its own copy) and the
            # coverage check - the mask is the expensive part of both.
            wmask = (calibration.line_ridge_mask(frame)
                     if processed % WATCH_EVERY == 0 else None)
            step, _ = calibration.court_lock_step(frame, A @ H, last_boxes,
                                                  mask=wmask)
            A = step @ A
            H_t = A @ H
            # WATCHDOG: the lock step only absorbs small drift. A real camera
            # change (bump / re-mount / zoom) collapses line coverage under the
            # tracked H -> re-run full detection and REBASE the motion track
            # (projective A = H_new @ H0^-1; the stored rows carry a full 3x3).
            if wmask is not None and watchdog.check(frame, H_t, mask=wmask) == "changed":
                res = courtfit.autodetect(frame, calibration, court)
                if res is not None:
                    A = res[0] @ np.linalg.inv(H)
                    A = A / A[2, 2]
                    H_t = A @ H
                    court_events.append({"frame": int(idx), "kind": "reacquired"})
                    print(f"[analyze] camera change detected ~frame {idx} -> "
                          "court RE-ACQUIRED (motion track rebased)")
                else:
                    court_events.append({"frame": int(idx), "kind": "lost"})
                    print(f"[analyze] WARNING: camera appears to have moved ~frame {idx} "
                          "and the court could not be re-acquired - positions after "
                          "this point may be off; re-check the overlay for this section")
                watchdog.rebase()
            cam_motion.append([float(v) for v in A.ravel()])
            # Pose next so the ball tracker can mask players this frame (boxes
            # carry forward between pose frames; players move little in ~3 frames).
            if processed % pose_every == 0:
                last_near = last_far = None
                last_near_kp = last_far_kp = None
                last_boxes = []
                _poses = estimator.estimate(frame)
                player_counts.append(list(pose_mod.count_on_court(_poses, H_t)))
                for p, cxy in pose_mod.select_players_on_court(_poses, H_t):
                    last_boxes.append(tuple(float(v) for v in p.box))
                    if cxy[1] < court.NET_Y:
                        last_near = cxy
                        last_near_kp = [[float(x), float(y), float(c)] for x, y, c in p.keypoints]
                    else:
                        last_far = cxy
                        last_far_kp = [[float(x), float(y), float(c)] for x, y, c in p.keypoints]
            ball_px.append(tracker.update(frame, last_boxes))
            near_court.append(last_near)
            far_court.append(last_far)
            near_kpts.append(last_near_kp)
            far_kpts.append(last_far_kp)
            processed += 1
        idx += 1
    cap.release()
    elapsed = time.time() - t0
    if processed:
        print(f"[analyze] perceived {processed} frames in {elapsed:.0f}s "
              f"({processed / elapsed:.2f} fps, {elapsed / processed:.2f}s/frame)")
    print(f"[analyze] ball locked via model={tracker.n_tnet}, "
          f"background-recovered={tracker.n_bg}, "
          f"static-fixtures-suppressed={tracker.n_static}")

    if cache_path:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "frame_step": frame_step,
                    "max_frames": max_frames,
                    "bgsub": bool(use_bgsub),
                    "pose_quality": pose_quality,
                    "ball_model": ball_model,
                    "provenance": _build_provenance(
                        ball_model, weight_files, pose_model, device,
                        camera_hfov_deg, cam_h, gate_H is not None, H,
                        static_gate=(tracker.static_step_px, tracker.static_min_run)),
                    "ball_px": [list(p) if p else None for p in ball_px],
                    "near_court": [list(p) if p else None for p in near_court],
                    "far_court": [list(p) if p else None for p in far_court],
                    "near_kpts": near_kpts,
                    "far_kpts": far_kpts,
                    "cam_motion": cam_motion,
                    "player_counts": player_counts,
                    "court_events": court_events,
                },
                f,
            )
        print(f"[analyze] cached perception -> {cache_path}")
    return (ball_px, near_court, far_court, near_kpts, far_kpts, cam_motion,
            player_counts, court_events)


def analyze_video(
    video_path: str,
    keypoints_path: Optional[str] = None,
    out_path: Optional[str] = None,
    ball_weights: str = "weights/tracknet.pt",
    pose_quality: str = "fast",
    pose_every: int = 3,
    device: str = "cpu",
    max_frames: Optional[int] = None,
    frame_step="auto",
    camera_hfov_deg: Optional[float] = None,
    use_bgsub: bool = True,
    ball_model: str = "tracknet",
    annotate: bool = False,
    doubles: bool = False,
) -> Match:
    """Analyze a real clip into a match.json — the full real pipeline.

    calibrate (geometry) -> perceive ball + players (ML) -> project to court
    metres (geometry) -> events/speed/line-calls (geometry) -> rallies + scoring
    (logic) -> schema. Everything downstream of perception is the same code the
    synthetic demo exercises; here it runs on real tracks.

    Player selection and the near/far split are derived from the homography (in
    court metres), so this works for amateur footage (a phone mounted a little
    above and behind a baseline), not just a TV angle.
    """
    import cv2

    from . import analytics, calibration, events
    from . import ball as ball_mod
    from .ball import smooth_and_fill
    from . import pose as pose_mod

    overlay_path = os.path.splitext(out_path)[0] + ".overlay.png" if out_path else None
    H, err, source, named_corners, cam_hfov_deg, lens_k1, H_und = calibrate_video(
        video_path, keypoints_path, overlay_path)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Field of view priority: explicit --camera-hfov (a phone whose fov the user
    # knows) > the PHYSICAL CAMERA LOCK's focal (works on every view, including
    # the telephoto broadcasts where focal_from_homography is degenerate) >
    # focal self-calibration from H > the old fixed 70° guess.
    if camera_hfov_deg is None and cam_hfov_deg is not None:
        camera_hfov_deg = float(cam_hfov_deg)
        print(f"[analyze] lens from the physical camera fit -> "
              f"hfov {camera_hfov_deg:.1f}deg")
    if camera_hfov_deg is None:
        f_est = calibration.focal_from_homography(H, (width, height)) if H is not None else None
        if f_est:
            camera_hfov_deg = calibration.hfov_from_focal(f_est, width)
            print(f"[analyze] self-calibrated focal {f_est:.0f}px "
                  f"-> hfov {camera_hfov_deg:.1f}deg")
        else:
            camera_hfov_deg = 70.0
            print("[analyze] focal self-calibration degenerate -> assuming hfov 70deg")

    if frame_step == "auto":
        # Target ~30fps (TrackNet's training rate) — halves work on 60fps phones.
        frame_step = max(1, round(fps / 30.0))
    frame_step = int(frame_step)
    fps_eff = fps / frame_step  # processed-frame rate (track times use this)
    if frame_step > 1:
        print(f"[analyze] {fps:.0f}fps source -> processing every {frame_step} frames ({fps_eff:.0f}fps)")

    # Perception (ball + pose) is the expensive part — cache it next to the output
    # so downstream tuning (events/speed/scoring) doesn't re-run inference.
    cache_path = (os.path.splitext(out_path)[0] + ".perception.json") if out_path else None
    (ball_px, near_court, far_court, near_kpts, far_kpts, cam_motion,
     player_counts, court_events) = _perceive(
        video_path, H, ball_weights, pose_quality, pose_every, device,
        max_frames, frame_step, cache_path, use_bgsub, ball_model, camera_hfov_deg
    )
    # Singles vs doubles: --doubles forces it; otherwise auto-detect from how many
    # players are on court (2 each side => doubles). Only the line-call boundary
    # changes; player tracking stays two-slot (near/far).
    from . import pose as _pose
    auto_doubles = _pose.infer_doubles(player_counts)
    use_doubles = bool(doubles) or auto_doubles
    print(f"[analyze] match type: {'doubles' if use_doubles else 'singles'}"
          f"{' (auto-detected)' if auto_doubles and not doubles else ''}"
          f"{' (forced)' if doubles else ''}")
    # A "player" that never moves is a person-shaped fixture (poster, bag, chair)
    # that selection fell back to when the real player was missed — a real player
    # never stands still for a whole clip. Wipe such tracks (positions + keypoints).
    near_court, near_kpts = _reject_static_player(near_court, near_kpts, "near")
    far_court, far_kpts = _reject_static_player(far_court, far_kpts, "far")
    # Per-frame inverse camera motion: un-warp a frame-t pixel back to frame-0
    # space so the one calibrated homography stays valid under broadcast pan/zoom.
    cam_inv = [np.linalg.inv(_cam_row_to_A(row)) for row in cam_motion or []]

    def unwarp(px, i):
        if not cam_inv or i >= len(cam_inv):
            return px
        q = cam_inv[i] @ np.array([px[0], px[1], 1.0])
        return (q[0] / q[2], q[1] / q[2])

    # LENS: metric projections go through pinhole space when a lens was
    # measured - undistort the observed pixel, project with the pinhole H_und.
    # With lens_k1 == 0 (the common case) both helpers are exact no-ops and
    # every code path below is unchanged.
    H_metric = H_und if lens_k1 else H

    def und(px):
        if not lens_k1 or px is None:
            return px
        q = calibration.undistort_points([px], lens_k1, (width, height))[0]
        return (float(q[0]), float(q[1]))

    if lens_k1:
        # Player court positions were projected in DISTORTED pixel space during
        # perception; redo them lens-corrected from the cached keypoints (ankle
        # midpoint - the same contact point pose.PlayerPose.feet uses). Frames
        # whose feet came from the box-bottom fallback (ankles unseen; the box
        # is not cached) keep their perceived value.
        def _feet(kp):
            pts = [(x, y) for x, y, c in (kp[15], kp[16]) if c > 0.2]
            if not pts:
                return None
            return (float(np.mean([p[0] for p in pts])),
                    float(np.mean([p[1] for p in pts])))

        def _relens(courts, kpts):
            out = list(courts)
            for i, kp in enumerate(kpts):
                if not kp or i >= len(out) or out[i] is None:
                    continue
                f = _feet(kp)
                if f is None:
                    continue
                x, y = calibration.image_to_court(H_metric, [und(unwarp(f, i))])[0]
                out[i] = (float(x), float(y))
            return out

        near_court = _relens(near_court, near_kpts)
        far_court = _relens(far_court, far_kpts)
    n = len(ball_px)
    print(f"[analyze] {n} frames; ball detected in {sum(p is not None for p in ball_px)}")

    # Reject single-frame teleports, project to court metres, drop off-court
    # projections, then fill + smooth. Two single-camera realities are handled
    # here (geometry, not ML): (1) a realistic runoff bound — a few metres behind
    # each baseline, not the old 10 m which let a far airborne ball overshoot to
    # y~30 and inflate its speed; (2) a per-frame court-displacement cap that drops
    # perspective-amplified far-court jitter. We also record the local metre/pixel
    # scale per frame (ball_conf) so far-court speeds/calls can be flagged.
    RUNOFF_M = 2.5
    ball_px = ball_mod.remove_outliers(ball_px, max_jump=max(width, height) * 0.06)
    ball_court_raw: list[Optional[list[float]]] = []
    ball_conf: list[Optional[float]] = []
    for i, px in enumerate(ball_px):
        if px is None:
            ball_court_raw.append(None)
            ball_conf.append(None)
            continue
        p0 = und(unwarp(px, i))   # camera-motion compensation + lens correction
        x, y = calibration.image_to_court(H_metric, [p0])[0]
        if (-RUNOFF_M <= x <= court.DOUBLES_WIDTH + RUNOFF_M
                and -RUNOFF_M <= y <= court.LENGTH + RUNOFF_M):
            ball_court_raw.append([float(x), float(y)])
            ball_conf.append(calibration.court_scale_m_per_px(H_metric, p0))
        else:
            ball_court_raw.append(None)
            ball_conf.append(None)
    ball_court_raw = ball_mod.cap_court_jumps(ball_court_raw, max_step_m=2.8)
    smoothed = smooth_and_fill(ball_court_raw, window=7, polyorder=2)
    track = [(i / fps_eff, float(smoothed[i, 0]), float(smoothed[i, 1])) for i in range(n)]

    hit_idx = sorted(events.detect_hits(track, angle_thresh_deg=70, min_gap_s=0.3))
    bounce_idx = sorted(events.detect_bounces(track, min_speed_drop=0.55))
    if not hit_idx:
        hit_idx = [0]  # degenerate clip: treat the start as the only contact

    # Physics-based speed + spin (ball_physics): build a metric camera from the
    # court corners, classify bounces by player proximity, anchor each hit->bounce
    # arc on the court plane, invert the flight physics. Best-effort — skipped if
    # the framework/corners aren't available.
    # The physics camera is built from frame-0 corner pixels, so feed it ball
    # pixels un-warped to frame-0 space too (camera-motion consistency). With a
    # measured lens everything physics sees moves to pinhole space: undistorted
    # ball pixels, undistorted corners, the pinhole H (the physics camera model
    # IS a pinhole - feeding it bent pixels was the systematic error).
    ball_px_cam0 = [None if p is None else und(unwarp(p, i))
                    for i, p in enumerate(ball_px)]
    corners_metric = named_corners
    if lens_k1 and named_corners:
        corners_metric = {
            n: [float(v) for v in
                calibration.undistort_points([xy], lens_k1, (width, height))[0]]
            for n, xy in named_corners.items()}
    physics_shots = _estimate_speed_spin(
        ball_px_cam0, near_court, far_court, corners_metric, H_metric,
        (width, height), fps_eff, camera_hfov_deg, hit_idx, bounce_idx
    )

    match = _build_match_from_events(
        track, hit_idx, bounce_idx, near_court, far_court, fps_eff, width, height,
        video_path, physics_shots, ball_conf, near_kpts, far_kpts, H_metric,
        singles=not use_doubles, lens_k1=lens_k1
    )
    # Carry the calibration in the match: the dashboard's Court Setup seeds its
    # adjustable overlay from these corners, and camera-change events tell the
    # user which sections were re-acquired (or need a manual re-check).
    match.calibration = {
        "corners": {k: [float(v[0]), float(v[1])] for k, v in named_corners.items()},
        "source": source,
        "hfov_deg": (round(float(camera_hfov_deg), 2)
                     if camera_hfov_deg is not None else None),
        "lens_k1": round(float(lens_k1), 4),
        "events": court_events,
    }

    if out_path:
        data = match.to_dict()
        problems = validate(data)
        if problems:
            raise ValueError("analyzed match failed validation:\n  " + "\n  ".join(problems))
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[analyze] wrote {out_path}")

    if annotate:
        from . import annotate as annotate_mod
        ann_path = (os.path.splitext(out_path)[0] + ".annotated.mp4") if out_path \
            else "annotated.mp4"
        # Render the ball from the CLEANED court track (off-court/jumpy detections
        # already rejected), not the raw image detections — otherwise a far-court
        # false lock draws the ball flying into the crowd.
        perception = {"ball_px": ball_px, "ball_court": ball_court_raw,
                      "near_kpts": near_kpts, "far_kpts": far_kpts,
                      "cam_motion": cam_motion}
        annotate_mod.render_match_video(video_path, H, perception, match, ann_path,
                                        fps_eff, frame_step, max_frames)
        print(f"[analyze] wrote annotated video -> {ann_path}")
    return match


def _estimate_speed_spin(ball_px, near_court, far_court, named_corners, H, img_wh,
                         fps, hfov_deg, hit_idx=None, bounce_idx=None):
    """Project players to image and run the ball_physics speed/spin estimator.
    Returns a list of arc readouts, or [] if anything is unavailable."""
    from . import calibration

    def to_img(court_list):
        out = []
        for c in court_list:
            if c is None:
                out.append(None)
            else:
                p = calibration.court_to_image(H, [c])[0]
                out.append((float(p[0]), float(p[1])))
        return out

    # The physics camera needs the four doubles corners as pixels. Rather than rely
    # on the calibrator exposing them, derive them straight from H (project the known
    # court-space corners) — accurate whenever the homography is, so spin/speed runs
    # on any well-calibrated clip, not just ones whose detector named those corners.
    corners = dict(named_corners) if named_corners else {}
    for name in ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles"):
        if name not in corners:
            p = calibration.court_to_image(H, [court.LANDMARKS[name]])[0]
            corners[name] = [float(p[0]), float(p[1])]

    try:
        from . import speedspin
        near_img = to_img(near_court)
        far_img = to_img(far_court)
        shots = speedspin.estimate(ball_px, near_img, far_img, corners,
                                   img_wh, fps, hfov_deg=hfov_deg,
                                   hit_idx=hit_idx, bounce_idx=bounce_idx)
        ok = sum(s["ok"] for s in shots)
        print(f"[analyze] speed/spin: {ok}/{len(shots)} reliable shot arcs "
              f"(physics, hfov={hfov_deg:.0f}deg)")
        for s in shots:
            print(f"    arc f{s['start_frame']}-{s['end_frame']}: "
                  f"{s['speed_kmh']:.0f} km/h, {s['spin_rpm']:.0f} rpm, "
                  f"reproj {s['reproj_px']}px {'OK' if s['ok'] else 'rejected'}")
        return shots
    except Exception as e:  # framework missing / camera failure -> approx speeds only
        print(f"[analyze] speed/spin estimation skipped: {e}")
        return []


def _build_match_from_events(
    track, hit_idx, bounce_idx, near_court, far_court, fps, width, height, video_path,
    physics_shots=None, ball_conf=None, near_kpts=None, far_kpts=None, H=None, singles=True,
    lens_k1=0.0,
) -> Match:
    """Turn ball track + contacts + player positions into a schema.Match.

    Each hit is a shot; the next bounce before the following hit is its landing.
    The striker is the player on the ball's side at contact; speed and the in/out
    call come from the real analytics on court metres.

    `ball_conf` is the per-frame metre/pixel scale (calibration.court_scale_m_per_px);
    where it is large (the far court grazing the horizon) speeds and line calls are
    flagged low-confidence rather than reported as fact.
    """
    from . import analytics, calibration, events

    # 1 px of ball-centroid error beyond this many court-metres is too noisy to
    # trust for speed / an in-or-out call (~ the far-baseline band on a baseline cam).
    UNRELIABLE_SCALE = 0.09

    players = [Player(id="A", name="Player A (near)"), Player(id="B", name="Player B (far)")]
    shots: list[Shot] = []

    def court_at(i):
        return [round(track[i][1], 3), round(track[i][2], 3)]

    def scale_at(i):
        return ball_conf[i] if ball_conf and 0 <= i < len(ball_conf) else None

    n_track = len(track)

    def real_fraction(a, b):
        """Fraction of frames in [a, b] backed by a real (non-interpolated)
        detection — interpolated/edge-filled spans carry no speed information."""
        a = max(0, a); b = min(n_track - 1, b)
        span = [scale_at(i) for i in range(a, b + 1)]
        return sum(v is not None for v in span) / max(len(span), 1)

    def real_continuation(i, win=5):
        """Fraction of the few frames after a landing backed by real detections. A
        true bounce keeps being tracked into the next shot; a detection drop-out
        (the ball lost mid-flight, edge-filled) has none — which would otherwise read
        as a fast mid-flight 'bounce'. The bounce frame itself is often interpolated
        (the exact contact falls between detections), so we look just past it."""
        return real_fraction(i + 1, i + win)

    MIN_FLIGHT_S = 0.12  # a struck ball can't land in <~4 frames; closer "bounces"
                         # are jitter minima at the contact, not the landing.
    MIN_SPEED_KMH = 5.0  # slower "shots" are interpolation artifacts on a flat
                         # (lost-ball) track segment, not strokes anyone played.
    # PHASE 1 — gather each plausible stroke's geometry. Classification happens in
    # phase 2, after handedness has been inferred from the whole match.
    pending: list[dict] = []
    for k, h in enumerate(hit_idx):
        next_hit = hit_idx[k + 1] if k + 1 < len(hit_idx) else len(track) - 1
        bounces_after = [b for b in bounce_idx
                         if h < b <= next_hit and track[b][0] - track[h][0] >= MIN_FLIGHT_S]
        land = bounces_after[0] if bounces_after else next_hit

        hit_xy = court_at(h)
        bounce_xy = court_at(land)
        is_serve = len(pending) == 0
        disp = float(np.hypot(bounce_xy[0] - hit_xy[0], bounce_xy[1] - hit_xy[1]))
        # If the chosen bounce barely moved (a residual jitter minimum), fall back
        # to the next contact as the landing before judging this as non-stroke.
        if disp < 0.8 and land != next_hit:
            land = next_hit
            bounce_xy = court_at(land)
            disp = float(np.hypot(bounce_xy[0] - hit_xy[0], bounce_xy[1] - hit_xy[1]))
        speed = analytics.shot_speed_kmh(track[h : land + 1])
        # Drop jitter (tiny direction wiggles), physically impossible segments (a
        # leftover tracking spike), and near-motionless ghosts — not real strokes.
        if speed < MIN_SPEED_KMH:
            continue
        if not is_serve and (disp < 0.8 or speed > 250.0):
            continue

        striker = "A" if track[h][2] < court.NET_Y else "B"
        player_xy = (near_court[h] if striker == "A" else far_court[h])
        px = player_xy[0] if player_xy else hit_xy[0]
        # Volley = struck out of the air in the forecourt: no bounce between the
        # previous contact and this one, AND the striker is near the net (a baseline
        # contact with a missed bounce is a groundstroke, not a volley).
        prev_hit = hit_idx[k - 1] if k > 0 else -1
        near_net = abs(hit_xy[1] - court.NET_Y) < 5.0
        volleyed = (k > 0) and near_net and not any(prev_hit < b < h for b in bounce_idx)
        kp_list = (near_kpts if striker == "A" else far_kpts) or []
        striker_kpts = kp_list[h] if (h < len(kp_list)) else None
        kpts_window = [kp_list[j] if 0 <= j < len(kp_list) else None
                       for j in range(h - 3, h + 4)]
        contact_xy_img = None
        if H is not None:
            # Striker keypoints are real (distorted) pixels, so a measured lens
            # must bend the projected contact point back before comparing.
            cpt = calibration.court_to_image(H, [hit_xy])[0]
            if lens_k1:
                cpt = calibration.distort_points([cpt], lens_k1, (width, height))[0]
            contact_xy_img = (float(cpt[0]), float(cpt[1]))
        # Tennis rule: a SECOND bounce before the next contact ends the point —
        # whatever "hit" follows is a pickup/feed, so the rally must break here.
        # Require real time/court separation from the landing so one physical
        # bounce's jitter minima can't read as two.
        second_bounce = any(
            land < b2 <= next_hit
            and track[b2][0] - track[land][0] >= 0.25
            and float(np.hypot(track[b2][1] - bounce_xy[0],
                               track[b2][2] - bounce_xy[1])) >= 0.3
            for b2 in bounce_idx
        ) if land != next_hit else False
        pending.append(dict(
            h=h, land=land, hit_xy=hit_xy, bounce_xy=bounce_xy, is_serve=is_serve,
            speed=speed, striker=striker, px=px, volleyed=volleyed,
            striker_kpts=striker_kpts, kpts_window=kpts_window,
            contact_xy_img=contact_xy_img, ends_point=second_bounce,
        ))

    # Infer each player's handedness from the match's contact sides (majority =
    # forehand side; conservative fallback to right). Serves/volleys excluded —
    # they don't discriminate the sides.
    sides: dict[str, list] = {"A": [], "B": []}
    for p in pending:
        if p["is_serve"] or p["volleyed"]:
            continue
        s = events.contact_side(p["striker_kpts"], p["contact_xy_img"],
                                p["hit_xy"][0], p["px"])
        if s is not None:
            sides[p["striker"]].append(s)
    handed = {pid: events.infer_handedness(sides[pid], facing_away=(pid == "A"))
              for pid in ("A", "B")}
    for pid in ("A", "B"):
        if handed[pid] == "left":
            print(f"[analyze] player {pid}: inferred LEFT-handed "
                  f"({len(sides[pid])} groundstroke contacts)")

    # PHASE 2 — classify and emit the shots.
    force_break: list[int] = []
    for p in pending:
        h, land = p["h"], p["land"]
        shot_type = events.classify_shot(
            p["hit_xy"][0], p["px"], handedness=handed[p["striker"]],
            facing_away=(p["striker"] == "A"),
            is_serve=p["is_serve"], volleyed=p["volleyed"],
            striker_kpts=p["striker_kpts"], contact_xy_img=p["contact_xy_img"],
        )
        spin_style = ""
        if shot_type in ("forehand", "backhand"):
            spin_style = events.classify_spin(p["kpts_window"], p["contact_xy_img"])
        speed = min(p["speed"], 230.0)  # cap: single-camera projection inflates fast balls
        call = analytics.line_call(p["bounce_xy"], shot_type=shot_type, singles=singles)
        # Confidence. Speed is trustworthy only if the stroke was observed end to
        # end: the segment is mostly REAL detections AND the ball is still tracked a
        # few frames past the landing — otherwise the "bounce" is a detection
        # drop-out (the track freezes, speed dips, mimicking a bounce) and the speed
        # captures only a fast mid-flight fragment. The line call is trustworthy only
        # if the bounce itself is a real detection in the reliable (low metre/pixel)
        # court band, not a far-baseline frame grazing the horizon.
        land_scale = scale_at(land)
        real_landing = land < n_track - 1 and real_continuation(land) >= 0.4  # bounce, not drop-out
        # Without a physics fit (which needs the true camera FOV — see
        # speed-physics-diagnosis: monocular optics are ill-conditioned on arbitrary
        # footage), the naive average OVER-reads airborne balls (a serve/lob projects
        # long on the flat ground) and any implausibly fast shot on one camera. Trust
        # it only for a well-observed, plausible GROUND shot; a validated physics arc
        # (below) re-confirms speed it actually measured.
        PLAUSIBLE_KMH = 160.0   # amateur ground strokes rarely exceed this on a phone
        speed_confident = (real_fraction(h, land) >= 0.5 and real_landing
                           and not p["is_serve"] and speed <= PLAUSIBLE_KMH)
        call_confident = (land_scale is not None and land_scale <= UNRELIABLE_SCALE
                          and real_landing)
        if p["ends_point"]:
            force_break.append(len(shots))
        shots.append(
            Shot(
                id=len(shots),
                rally_id=0,  # set below
                player=p["striker"],
                type=shot_type,
                t_hit_s=round(track[h][0], 2),
                speed_kmh=round(speed, 1),
                hit_xy=p["hit_xy"],
                bounce_xy=p["bounce_xy"],
                bounce_t_s=round(track[land][0], 2),
                is_in=call == "in",
                call=call,
                spin_style=spin_style,
                speed_confident=speed_confident,
                call_confident=call_confident,
            )
        )

    # Attach physics-based speed + spin: match each shot to the reliable flight
    # arc whose bounce time is closest (the bounce-anchored fit pins the speed).
    if physics_shots:
        for s in shots:
            best, best_dt = None, 0.4
            for ps in physics_shots:
                dt = abs(ps["t_bounce_s"] - s.bounce_t_s)
                if ps["ok"] and dt < best_dt:
                    best, best_dt = ps, dt
            if best is not None:
                s.speed_kmh = best["speed_kmh"]
                s.spin_rpm = best["spin_rpm"]
                s.topspin_rpm = best["topspin_rpm"]
                s.speed_source = "physics"
                s.speed_confident = True   # a bounce-anchored fit is a real measurement
                # A measured arc outranks the pose heuristic for stroke style.
                if s.type in ("forehand", "backhand") and abs(best["topspin_rpm"]) > 300:
                    s.spin_style = "topspin" if best["topspin_rpm"] > 0 else "slice"

    # Segment shots into rallies by the gap between consecutive hits — and break
    # unconditionally after any shot whose SECOND bounce ended the point.
    groups = events.segment_rallies([s.t_hit_s for s in shots], gap_s=2.0,
                                    force_break_after=force_break)
    rallies: list[Rally] = []
    for rid, group in enumerate(groups):
        rshots = [shots[i] for i in group]
        for s in rshots:
            s.rally_id = rid
        start = rshots[0].t_hit_s
        end = rshots[-1].bounce_t_s
        # Sub-sampled court ball-track for the dashboard scrubber (~10 Hz).
        step = max(1, int(round(fps / 10)))
        bt = [
            TrackPoint(t_s=round(track[i][0], 2), xy=[round(track[i][1], 3), round(track[i][2], 3)])
            for i in range(0, len(track), step)
            if start - 0.2 <= track[i][0] <= end + 0.2
        ]
        last = rshots[-1]
        winner = (last.player if last.call == "in" else ("B" if last.player == "A" else "A"))
        rallies.append(
            Rally(
                id=rid,
                start_s=start,
                end_s=end,
                shot_ids=[s.id for s in rshots],
                winner=winner,
                ball_track=bt,
            )
        )

    # Scoring from rally winners (best-effort; vision scoring is brittle).
    score_engine = scoring.TennisScore(player_a="A", player_b="B")
    timeline: list[ScoreEvent] = []
    for r in rallies:
        res = score_engine.point(r.winner)
        timeline.append(
            ScoreEvent(
                shot_id=r.shot_ids[-1],
                rally_id=r.id,
                point_winner=r.winner,
                display=res.display,
                games_display=res.games_display,
                sets_display=res.sets_display,
            )
        )
    score_block = Score(
        final=score_engine.final_str(),
        sets=[list(s) for s in score_engine.completed_sets],
        games=list(score_engine.games),
        timeline=timeline,
    )

    video = Video(
        filename=os.path.basename(video_path),
        fps=round(fps, 2),
        width=width,
        height=height,
        duration_s=round(track[-1][0], 1) if track else 0.0,
    )
    stats = compute_stats(shots, rallies)
    stats.distance_run_m = {
        "A": _distance_run_m(near_court, fps),
        "B": _distance_run_m(far_court, fps),
    }
    return Match(
        video=video,
        players=players,
        shots=shots,
        rallies=rallies,
        score=score_block,
        stats=stats,
    )


def _distance_run_m(positions, fps) -> float:
    """Court-plane distance a player ran (metres) from their per-frame positions.

    Gaps are forward-filled, the path is lightly smoothed, then summed at ~4 Hz with
    a per-sample sanity cap (a player can't cross >2 m in 0.25 s) so perspective
    jitter — worst for the far player — doesn't inflate the total. Best-effort.
    """
    last = None
    filled = []
    for p in positions:
        if p is not None:
            last = p
        if last is not None:
            filled.append((float(last[0]), float(last[1])))
    if len(filled) < 2:
        return 0.0
    arr = np.asarray(filled, dtype=float)
    k = min(5, len(arr))
    if k >= 2:
        ker = np.ones(k) / k
        arr[:, 0] = np.convolve(arr[:, 0], ker, mode="same")
        arr[:, 1] = np.convolve(arr[:, 1], ker, mode="same")
    step_n = max(1, int(round(fps / 4.0)))
    samp = arr[::step_n]
    dist = 0.0
    for i in range(1, len(samp)):
        s = float(np.hypot(samp[i, 0] - samp[i - 1, 0], samp[i, 1] - samp[i - 1, 1]))
        if s <= 2.0:
            dist += s
    return round(dist, 1)
