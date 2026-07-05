"""Composite 'ML in action' frame for a clip: court-line overlay + both player
positions + the ball with a rough hit estimate (call + approx speed).

    python show_in_action.py <video> <keypoints.json> <frame_idx> <out.png>
"""

from __future__ import annotations

import json
import sys

import cv2
import numpy as np

from swingvision import analytics, calibration, court, overlay, pose
from swingvision.ball import BallDetector

NEAR_COLOR, FAR_COLOR, BALL = (255, 230, 0), (255, 0, 255), (0, 255, 255)


def draw_player(frame, p, color, label):
    for a, b in pose.COCO_SKELETON:
        xa, ya, ca = p.keypoints[a]
        xb, yb, cb = p.keypoints[b]
        if ca > 0.25 and cb > 0.25:
            cv2.line(frame, (int(xa), int(ya)), (int(xb), int(yb)), color, 2, cv2.LINE_AA)
    x1, y1, x2, y2 = (int(v) for v in p.box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    fx, fy = p.feet()
    cv2.circle(frame, (int(fx), int(fy)), 5, color, -1, cv2.LINE_AA)
    cv2.rectangle(frame, (x1, y1 - 22), (x1 + 11 * len(label), y1), color, -1)
    cv2.putText(frame, label, (x1 + 3, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)


def main(video, keypoints, frame_idx, out, singles=True):
    with open(keypoints, "r", encoding="utf-8") as f:
        H = calibration.homography_from_landmarks(json.load(f))
    fps_default = 30.0

    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or fps_default
    start = max(0, frame_idx - 11)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    frames = []
    for _ in range(frame_idx - start + 1):
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    target = frames[-1].copy()

    # 1) Court lines from the homography.
    overlay.draw_court(target, H, color=(60, 255, 255), thickness=2, dots=False)

    # 2) Both players (accurate preset so the small far player is resolved).
    pe = pose.PoseEstimator(quality="accurate")
    poses = pe.estimate(frames[-1])
    chosen = pose.select_players_on_court(poses, H)
    if len(chosen) < 2:
        chosen = [(p, tuple(calibration.image_to_court(H, [p.feet()])[0]))
                  for p in pose.keep_players(poses, max_players=2)]
    for p, cxy in chosen:
        near = cxy[1] < court.NET_Y
        draw_player(target, p, NEAR_COLOR if near else FAR_COLOR,
                    f"Player {'A (near)' if near else 'B (far)'}")

    # 3) Ball trail + rough hit estimate (call + approx speed from court motion).
    bd = BallDetector("weights/tracknet.pt")
    track_px = []
    for fr in frames:
        track_px.append(bd.detect(fr))
    pts = [(i, p) for i, p in enumerate(track_px) if p]
    for k in range(1, len(pts)):
        cv2.line(target, tuple(map(int, pts[k - 1][1])), tuple(map(int, pts[k][1])), BALL, 2, cv2.LINE_AA)
    if pts:
        bx, by = pts[-1][1]
        cv2.circle(target, (int(bx), int(by)), 8, BALL, 2, cv2.LINE_AA)
        cxy = calibration.image_to_court(H, [(bx, by)])[0]
        call = analytics.line_call((float(cxy[0]), float(cxy[1])), singles=singles)
        est = ""
        if len(pts) >= 2:
            (i0, p0), (i1, p1) = pts[-2], pts[-1]
            c0 = calibration.image_to_court(H, [p0])[0]
            c1 = calibration.image_to_court(H, [p1])[0]
            dt = (i1 - i0) / fps
            if dt > 0:
                kmh = np.hypot(c1[0] - c0[0], c1[1] - c0[1]) / dt * 3.6
                est = f"  ~{min(kmh,230):.0f} km/h"
        label = f"ball hit: {call.upper()}{est}"
        color = (80, 220, 80) if call == "in" else (60, 60, 240)
        cv2.rectangle(target, (int(bx) + 12, int(by) - 16), (int(bx) + 12 + 14 * len(label), int(by) + 8), color, -1)
        cv2.putText(target, label, (int(bx) + 16, int(by) + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 2, cv2.LINE_AA)

    cv2.putText(target, "court lines + players + ball (SwingVision-clone ML)", (16, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(out, target)
    print(f"wrote {out}  | players drawn: {len(chosen)} | ball points: {len(pts)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
