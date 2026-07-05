"""annotate.py — draw the analysis back onto the source video (the SwingVision view).

Renders an overlay video from the CACHED perception (ball pixels + player keypoints)
plus the match.json events — no models re-run, so it's fast. Draws, per frame:
court lines (homography), both player skeletons, the ball with a motion trail, and a
shot-type + line-call label at each contact. This is what the dashboard's Broadcast
tab plays.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from . import overlay, pose
from .ball import smooth_and_fill

NEAR_COLOR, FAR_COLOR, BALL_COLOR = (255, 230, 0), (255, 0, 255), (0, 255, 255)
IN_COLOR, OUT_COLOR = (90, 220, 90), (60, 60, 255)


def _interp_kpts(kpts_list):
    """Smooth held-forward pose samples for rendering.

    Pose runs every Nth frame and the perception cache repeats the last sample in
    between, so skeletons stutter in 10 Hz steps. Find the frames where the pose
    actually changed (fresh samples) and linearly interpolate every confident
    keypoint between consecutive samples. Render-only — analysis data untouched.
    """
    n = len(kpts_list)
    fresh = [i for i in range(n)
             if kpts_list[i] is not None and (i == 0 or kpts_list[i] != kpts_list[i - 1])]
    out = list(kpts_list)
    for a, b in zip(fresh, fresh[1:]):
        ka, kb = kpts_list[a], kpts_list[b]
        if b - a < 2 or len(ka) != len(kb):
            continue
        for j in range(a + 1, b):
            t = (j - a) / (b - a)
            out[j] = [
                [ka[k][0] + (kb[k][0] - ka[k][0]) * t,
                 ka[k][1] + (kb[k][1] - ka[k][1]) * t,
                 min(ka[k][2], kb[k][2])]
                if ka[k][2] > 0.3 and kb[k][2] > 0.3 else ka[k]
                for k in range(len(ka))
            ]
    return out


def _kpts_box(kpts, shape, pad: int = 14):
    """Player body bbox from confident keypoints (frame-clamped), or None."""
    if not kpts:
        return None
    xs = [k[0] for k in kpts if k[2] > 0.3]
    ys = [k[1] for k in kpts if k[2] > 0.3]
    if not xs:
        return None
    h, w = shape[:2]
    return (max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad),
            min(w, int(max(xs)) + pad), min(h, int(max(ys)) + pad))


def _draw_skeleton(frame, kpts, color):
    import cv2

    if not kpts:
        return
    for a, b in pose.COCO_SKELETON:
        xa, ya, ca = kpts[a]
        xb, yb, cb = kpts[b]
        if ca > 0.3 and cb > 0.3:
            cv2.line(frame, (int(xa), int(ya)), (int(xb), int(yb)), color, 2, cv2.LINE_AA)
    xs = [k[0] for k in kpts if k[2] > 0.3]
    ys = [k[1] for k in kpts if k[2] > 0.3]
    if xs:
        cv2.rectangle(frame, (int(min(xs)) - 6, int(min(ys)) - 6),
                      (int(max(xs)) + 6, int(max(ys)) + 6), color, 1, cv2.LINE_AA)


# --- Shot-chart HUD (top-left) ----------------------------------------------
CHART_SCALE = 7.0        # mini-court px per metre
CHART_MARGIN_M = 1.0     # runoff drawn around the court so out-balls stay visible


def _draw_shot_chart(frame, shots, latest):
    """Top-left HUD: a top-down mini court accumulating every landing so far.
    Dots are colored by the hitter (A = near / B = far, matching the skeleton
    colors); out-balls get a red ring. The latest shot is highlighted and its
    player / type / speed / call are printed under the court."""
    import cv2

    from . import court as C

    s, m, pad = CHART_SCALE, CHART_MARGIN_M, 10
    cw = int((C.DOUBLES_WIDTH + 2 * m) * s)
    ch = int((C.LENGTH + 2 * m) * s)
    text_h = 44
    x0, y0 = 14, 14
    w_p = max(cw + 2 * pad, 152)
    h_p = ch + 2 * pad + text_h
    cx0 = x0 + (w_p - cw) // 2          # court area centered in the panel
    fh, fw = frame.shape[:2]
    if x0 + w_p >= fw or y0 + h_p >= fh:
        return
    roi = frame[y0:y0 + h_p, x0:x0 + w_p]
    frame[y0:y0 + h_p, x0:x0 + w_p] = (roi * 0.28).astype(roi.dtype)

    def to_px(xy):
        px = cx0 + (xy[0] + m) * s
        py = y0 + pad + (C.LENGTH + m - xy[1]) * s   # far baseline at the top
        return (int(min(max(px, cx0), cx0 + cw)),
                int(min(max(py, y0 + pad), y0 + pad + ch)))

    for a, b in C.LINES:
        thick = 2 if a[1] == b[1] == C.NET_Y else 1
        cv2.line(frame, to_px(a), to_px(b), (210, 210, 210), thick, cv2.LINE_AA)

    for sh in shots:
        pt = to_px(sh.bounce_xy)
        col = NEAR_COLOR if sh.player == "A" else FAR_COLOR
        cv2.circle(frame, pt, 3, col, -1, cv2.LINE_AA)
        if sh.call != "in":
            cv2.circle(frame, pt, 6, OUT_COLOR, 1, cv2.LINE_AA)

    ty = y0 + 2 * pad + ch + 4
    if latest is not None:
        cv2.circle(frame, to_px(latest.bounce_xy), 7, (255, 255, 255), 1, cv2.LINE_AA)
        col = NEAR_COLOR if latest.player == "A" else FAR_COLOR
        spd = (f"{latest.speed_kmh:.0f}" if getattr(latest, "speed_confident", True)
               else f"~{latest.speed_kmh:.0f}") + " km/h"
        call = ("IN" if latest.call == "in" else "OUT") + \
               ("" if getattr(latest, "call_confident", True) else "?")
        style = getattr(latest, "spin_style", "")
        stroke = f"{style} {latest.type}" if style and style != "flat" else latest.type
        cv2.putText(frame, f"{latest.player}  {stroke}", (x0 + pad, ty + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{spd}  {call}", (x0 + pad, ty + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    IN_COLOR if latest.call == "in" else OUT_COLOR, 1, cv2.LINE_AA)
    else:
        cv2.putText(frame, "shots", (x0 + pad, ty + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)


def _to_h264(src: str, dst: str) -> bool:
    """Transcode src to a browser-playable H.264 mp4 at dst using the bundled
    ffmpeg (OpenCV here can only write MPEG-4 Part 2, which browsers won't decode).
    Returns True on success."""
    import os
    import subprocess

    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return False
    try:
        subprocess.run([ff, "-y", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", dst],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(dst) and os.path.getsize(dst) > 0
    except Exception:
        return False


def render_match_video(
    video_path: str,
    H: np.ndarray,
    perception: dict,
    match,
    out_path: str,
    fps_eff: float,
    frame_step: int = 1,
    max_frames: Optional[int] = None,
) -> str:
    """Write an annotated overlay video to out_path (browser-playable H.264 when the
    bundled ffmpeg is available, else MPEG-4). `perception` is the cached dict
    (ball_px, near_kpts, far_kpts); `match` is the schema.Match."""
    import os

    import cv2

    from . import calibration

    ball_px = perception["ball_px"]
    ball_court = perception.get("ball_court")
    near_kpts = _interp_kpts(perception.get("near_kpts") or [None] * len(ball_px))
    far_kpts = _interp_kpts(perception.get("far_kpts") or [None] * len(ball_px))

    # Per-frame homographies: compose the calibrated H with the tracked camera
    # motion so the court overlay FOLLOWS a broadcast pan/zoom instead of drifting.
    n_all = len(ball_px)
    H_frames = [H] * n_all
    cam = perception.get("cam_motion")
    if cam and H is not None:
        H_frames = []
        for row in cam:
            A = np.eye(3)
            A[:2, :] = np.asarray(row, dtype=float).reshape(2, 3)
            H_frames.append(A @ H)
        H_frames += [H_frames[-1] if H_frames else H] * (n_all - len(H_frames))

    # Prefer the CLEANED court track (off-court/teleport detections already nulled)
    # projected back to image — so a far-court false lock can't draw the ball in the
    # crowd. `real` marks frames backed by a kept detection: solid marker near real
    # evidence, a faded GHOST marker across short interpolated gaps (the ball hasn't
    # gone anywhere — we just missed a few blurry frames), nothing on long gaps.
    if ball_court is not None and H is not None:
        sm_c = smooth_and_fill([tuple(p) if p else None for p in ball_court], window=7, polyorder=2)
        sm = np.array([calibration.court_to_image(H_frames[i], [sm_c[i]])[0]
                       for i in range(len(sm_c))]) if len(sm_c) else np.zeros((0, 2))
        real = [p is not None for p in ball_court]
    else:
        sm = smooth_and_fill([tuple(p) if p else None for p in ball_px], window=7, polyorder=2)
        real = [p is not None for p in ball_px]
    n_f = len(sm)
    drawable = [any(real[j] for j in range(max(0, i - 2), min(n_f, i + 3))) for i in range(n_f)]
    # Ghost: inside an interpolated gap of <= GAP_MAX frames bounded by real
    # detections on both sides (so the interpolation is anchored, not a guess).
    GAP_MAX = 8
    ghost = [False] * n_f
    real_idx = [i for i in range(n_f) if real[i]]
    for a, b in zip(real_idx, real_idx[1:]):
        if 1 < b - a <= GAP_MAX:
            for j in range(a + 1, b):
                if not drawable[j]:
                    ghost[j] = True

    # Map each shot to its processed-frame index + a label.
    labels: dict[int, tuple[str, str, bool, bool]] = {}
    for s in match.shots:
        fi = int(round(s.t_hit_s * fps_eff))
        spd = f"{s.speed_kmh:.0f} km/h" if getattr(s, "speed_confident", True) else f"~{s.speed_kmh:.0f} km/h"
        style = getattr(s, "spin_style", "")
        stroke = f"{style} {s.type}" if style and style != "flat" else s.type
        labels[fi] = (stroke, spd, s.call == "in", getattr(s, "call_confident", True))

    # Shot-chart HUD feed: shots in hit order; a shot appears on the chart the
    # moment it is struck and stays for the rest of the video.
    chart_shots = sorted(match.shots, key=lambda sh: sh.t_hit_s)
    chart_fis = [int(round(sh.t_hit_s * fps_eff)) for sh in chart_shots]

    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    raw_path = out_path + ".mp4v.mp4"   # OpenCV writes MPEG-4; transcoded below
    writer = cv2.VideoWriter(raw_path, cv2.VideoWriter_fourcc(*"mp4v"), fps_eff, (w, h))
    n = len(sm)
    idx = proc = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or (max_frames is not None and idx >= max_frames) or proc >= n:
                break
            if idx % frame_step == 0:
                # Occlusion-aware court: draw the lines on a layer, then restore the
                # original pixels inside each player's body region — lines passing
                # BEHIND players (like a real broadcast AR overlay) instead of
                # stamping across their legs, which reads as a floating sticker.
                court_layer = frame.copy()
                overlay.draw_court(court_layer, H_frames[proc], thickness=2, dots=False)
                for kp in (near_kpts[proc], far_kpts[proc]):
                    box = _kpts_box(kp, frame.shape)
                    if box is not None:
                        x1, y1, x2, y2 = box
                        court_layer[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
                frame = court_layer
                _draw_skeleton(frame, near_kpts[proc], NEAR_COLOR)
                _draw_skeleton(frame, far_kpts[proc], FAR_COLOR)
                # Ball trail — solid where both ends are reliably tracked, thin
                # through anchored short gaps, absent on long/unanchored gaps.
                for k in range(max(1, proc - 12), proc + 1):
                    a_ok = drawable[k - 1] or ghost[k - 1]
                    b_ok = drawable[k] or ghost[k]
                    if a_ok and b_ok:
                        thick = 2 if (drawable[k] and drawable[k - 1]) else 1
                        cv2.line(frame, (int(sm[k - 1, 0]), int(sm[k - 1, 1])),
                                 (int(sm[k, 0]), int(sm[k, 1])), BALL_COLOR, thick, cv2.LINE_AA)
                bx, by = int(sm[proc, 0]), int(sm[proc, 1])
                if drawable[proc]:
                    cv2.circle(frame, (bx, by), 7, BALL_COLOR, 2, cv2.LINE_AA)
                elif ghost[proc]:
                    cv2.circle(frame, (bx, by), 6, BALL_COLOR, 1, cv2.LINE_AA)
                if proc in labels and drawable[proc]:
                    st, spd, is_in, call_conf = labels[proc]
                    col = IN_COLOR if is_in else OUT_COLOR
                    cv2.circle(frame, (bx, by), 16, col, 3, cv2.LINE_AA)
                    tag = f"{st}  {spd}  {'IN' if is_in else 'OUT'}{'' if call_conf else '?'}"
                    cv2.putText(frame, tag, (bx + 20, by), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, col, 2, cv2.LINE_AA)
                # Shot chart owns the top-left; filename moves to the top-right.
                n_vis = sum(1 for f0 in chart_fis if f0 <= proc)
                _draw_shot_chart(frame, chart_shots[:n_vis],
                                 chart_shots[n_vis - 1] if n_vis else None)
                (tw, _), _ = cv2.getTextSize(match.video.filename,
                                             cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.putText(frame, f"{match.video.filename}", (w - tw - 20, 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                writer.write(frame)
                proc += 1
            idx += 1
    finally:
        cap.release()
        writer.release()

    if _to_h264(raw_path, out_path):
        os.remove(raw_path)
    else:
        os.replace(raw_path, out_path)   # no ffmpeg: keep the MPEG-4 (may not play in-browser)
    return out_path
