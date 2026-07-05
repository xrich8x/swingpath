"""One-off demo: track the ball through a real clip with TrackNet, fill gaps,
mark hit/bounce events, and draw the ball + trail. Produces an annotated video
and sample frames.

    python ball_track_demo.py ../data/tennis_sample.mp4
"""

from __future__ import annotations

import sys
import time

import cv2
import numpy as np

from swingvision import events
from swingvision.ball import BallDetector, smooth_and_fill


def main(video_path: str):
    bd = BallDetector("weights/tracknet.pt")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frames = []
    raw = []
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
        raw.append(bd.detect(frame))
    cap.release()
    detected = sum(p is not None for p in raw)
    print(f"detected ball in {detected}/{len(frames)} frames ({time.time()-t0:.1f}s)")

    # Fill gaps + smooth the pixel trajectory.
    smoothed = smooth_and_fill(raw, window=7, polyorder=2)

    # Events: direction reversals = hits/bounces (pixel-space track, t in seconds).
    track = [(i / fps, float(smoothed[i, 0]), float(smoothed[i, 1])) for i in range(len(smoothed))]
    hit_idx = set(events.detect_hits(track, angle_thresh_deg=70, min_gap_s=0.25))
    bounce_idx = set(events.detect_bounces(track, min_speed_drop=0.55))
    print(f"events: {len(hit_idx)} hits, {len(bounce_idx)} bounces (pixel-track heuristic)")

    writer = cv2.VideoWriter(
        "../data/output/ball_tracked.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
    )
    saved = []
    for i, frame in enumerate(frames):
        # Trail: last ~12 smoothed points.
        for k in range(max(1, i - 12), i + 1):
            a = (int(smoothed[k - 1, 0]), int(smoothed[k - 1, 1]))
            b = (int(smoothed[k, 0]), int(smoothed[k, 1]))
            cv2.line(frame, a, b, (0, 255, 255), 2, cv2.LINE_AA)
        bx, by = int(smoothed[i, 0]), int(smoothed[i, 1])
        live = raw[i] is not None
        cv2.circle(frame, (bx, by), 7, (0, 255, 255) if live else (120, 120, 120), 2, cv2.LINE_AA)
        if i in hit_idx:
            cv2.circle(frame, (bx, by), 16, (60, 60, 255), 3, cv2.LINE_AA)
            cv2.putText(frame, "HIT", (bx + 18, by), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 60, 255), 2)
        elif i in bounce_idx:
            cv2.circle(frame, (bx, by), 14, (0, 200, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f"frame {i}  ball {'LIVE' if live else 'interp'}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        writer.write(frame)
        if i in (12, 30, 55, 80):
            fn = f"../data/output/ball_frame_{i:03d}.png"
            cv2.imwrite(fn, frame)
            saved.append(fn)
    writer.release()
    print("saved frames:", saved)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../data/tennis_sample.mp4")
