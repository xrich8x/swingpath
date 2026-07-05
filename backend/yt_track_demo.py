"""Test our tracker on real amateur footage (phone behind a baseline, a bit
above the player) downloaded from YouTube. No court calibration needed — this
runs in pixel space to show players + ball tracking on realistic footage.

    python yt_track_demo.py ../data/yt_rally.mp4
"""

from __future__ import annotations

import sys
import time

import cv2

from swingvision import events, pose
from swingvision.ball import BallDetector, remove_outliers, smooth_and_fill

SPLIT_Y = 480           # near/far divider in pixels (between the two players)
NEAR_COLOR, FAR_COLOR, BALL_COLOR = (255, 230, 0), (255, 0, 255), (0, 255, 255)
STEP = 2                # process every 2nd frame (60fps source)
POSE_EVERY = 3          # pose every Nth processed frame
LIMIT = 240             # source frames to cover (~4s)


def draw_pose(frame, p, color, label):
    for a, b in pose.COCO_SKELETON:
        xa, ya, ca = p.keypoints[a]
        xb, yb, cb = p.keypoints[b]
        if ca > 0.25 and cb > 0.25:
            cv2.line(frame, (int(xa), int(ya)), (int(xb), int(yb)), color, 2, cv2.LINE_AA)
    x1, y1, x2, y2 = (int(v) for v in p.box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
    cv2.putText(frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main(video_path: str):
    bd = BallDetector("weights/tracknet.pt")
    pe = pose.PoseEstimator(weights="yolo11x-pose.pt", conf=0.12, imgsz=1920)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames, raw_ball, poses_by = [], [], []
    last = []
    t0 = time.time()
    src_idx = 0
    while len(frames) < LIMIT // STEP:
        ok, frame = cap.read()
        if not ok:
            break
        if src_idx % STEP == 0:
            i = len(frames)
            raw_ball.append(bd.detect(frame))
            if i % POSE_EVERY == 0:
                last = pose.keep_players(pe.estimate(frame), max_players=2)  # indoors: just 2 people
            poses_by.append(list(last))
            frames.append(frame)
        src_idx += 1
    cap.release()
    print(f"processed {len(frames)} frames in {time.time()-t0:.0f}s; "
          f"ball {sum(p is not None for p in raw_ball)}/{len(frames)}")

    cleaned = remove_outliers(raw_ball, max_jump=max(w, h) * 0.06)
    smoothed = smooth_and_fill(cleaned, window=7, polyorder=2)
    track = [(i / (fps / STEP), float(smoothed[i, 0]), float(smoothed[i, 1])) for i in range(len(smoothed))]
    hit_idx = set(events.detect_hits(track, angle_thresh_deg=70, min_gap_s=0.25))

    writer = cv2.VideoWriter(
        "../data/output/yt_tracked.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps / STEP, (w, h)
    )
    near_trail, far_trail = [], []
    saved = []
    for i, frame in enumerate(frames):
        for p in poses_by[i]:
            fx, fy = p.feet()
            if fy >= SPLIT_Y:
                near_trail.append((int(fx), int(fy)))
                draw_pose(frame, p, NEAR_COLOR, "near")
            else:
                far_trail.append((int(fx), int(fy)))
                draw_pose(frame, p, FAR_COLOR, "far")
        for trail, color in ((near_trail, NEAR_COLOR), (far_trail, FAR_COLOR)):
            for k in range(1, len(trail)):
                cv2.line(frame, trail[k - 1], trail[k], color, 2, cv2.LINE_AA)
        for k in range(max(1, i - 10), i + 1):
            cv2.line(frame, (int(smoothed[k - 1, 0]), int(smoothed[k - 1, 1])),
                     (int(smoothed[k, 0]), int(smoothed[k, 1])), BALL_COLOR, 2, cv2.LINE_AA)
        bx, by = int(smoothed[i, 0]), int(smoothed[i, 1])
        cv2.circle(frame, (bx, by), 6, BALL_COLOR, 2, cv2.LINE_AA)
        if i in hit_idx:
            cv2.circle(frame, (bx, by), 14, (60, 60, 255), 3)
            cv2.putText(frame, "HIT", (bx + 16, by), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 60, 255), 2)
        cv2.putText(frame, "our tracker on amateur footage", (16, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
        if i in (20, 45, 70, 95):
            fn = f"../data/output/yt_frame_{i:03d}.png"
            cv2.imwrite(fn, frame)
            saved.append(fn)
    writer.release()
    print("saved:", saved)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../data/yt_rally.mp4")
