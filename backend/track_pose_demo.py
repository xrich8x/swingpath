"""One-off demo: track both players through a real clip with YOLO-pose and draw
skeletons + movement trails. Produces an annotated video and sample frames.

    python track_pose_demo.py ../data/tennis_sample.mp4

This is a demonstration script (not part of the library API yet). It shows the
pose stage working on real footage before it's folded into analyze_video.
"""

from __future__ import annotations

import sys

import cv2
import numpy as np

from swingvision import pose

# Court framing for THIS broadcast clip (would come from calibration in general).
SPLIT_Y = 500
CENTER_X = 955
COURT_POLY = [[380, 185], [1470, 190], [1850, 960], [120, 960]]
NEAR_COLOR = (255, 230, 0)   # cyan-ish (BGR)
FAR_COLOR = (255, 0, 255)    # magenta
EVERY = 3                    # process every Nth frame (CPU budget)


def draw_pose(frame, p, color, label):
    for a, b in pose.COCO_SKELETON:
        xa, ya, ca = p.keypoints[a]
        xb, yb, cb = p.keypoints[b]
        if ca > 0.3 and cb > 0.3:
            cv2.line(frame, (int(xa), int(ya)), (int(xb), int(yb)), color, 2, cv2.LINE_AA)
    for x, y, c in p.keypoints:
        if c > 0.3:
            cv2.circle(frame, (int(x), int(y)), 3, color, -1, cv2.LINE_AA)
    x1, y1, x2, y2 = (int(v) for v in p.box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
    cv2.putText(frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)


def main(video_path: str):
    pe = pose.PoseEstimator(weights="yolo11x-pose.pt", conf=0.20, imgsz=1920)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    writer = cv2.VideoWriter(
        "../data/output/pose_tracked.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps / EVERY, (w, h)
    )

    near_trail: list[tuple[int, int]] = []
    far_trail: list[tuple[int, int]] = []
    saved = []
    idx = 0
    processed = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % EVERY == 0:
            poses = pe.estimate(frame)
            players = pose.select_two_players(poses, SPLIT_Y, CENTER_X, COURT_POLY)
            for p in players:
                fx, fy = p.feet()
                if fy >= SPLIT_Y:
                    near_trail.append((int(fx), int(fy)))
                    draw_pose(frame, p, NEAR_COLOR, "near")
                else:
                    far_trail.append((int(fx), int(fy)))
                    draw_pose(frame, p, FAR_COLOR, "far")
            for trail, color in ((near_trail, NEAR_COLOR), (far_trail, FAR_COLOR)):
                for i in range(1, len(trail)):
                    cv2.line(frame, trail[i - 1], trail[i], color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"frame {idx}/{n}  players={len(players)}",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            writer.write(frame)
            if processed in (0, 10, 20, 30):
                fn = f"../data/output/pose_frame_{processed:02d}.png"
                cv2.imwrite(fn, frame)
                saved.append(fn)
            processed += 1
            print(f"  frame {idx}: {len(players)} players", flush=True)
        idx += 1
    cap.release()
    writer.release()
    print(f"processed {processed} frames; near trail {len(near_trail)} pts, far trail {len(far_trail)} pts")
    print("saved:", saved)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../data/tennis_sample.mp4")
