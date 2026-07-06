"""Build the ball-detection training set from OUR pipeline's pseudo-labels.

For each (video, perception.json) pair: every frame where the tracker locked the
ball (ball_px non-null) becomes a training sample — the 512x288-resized frame is
written once as JPEG, and the label is the lock position scaled to 512x288. The
model consumes 3-frame windows assembled at train time, so all processed frames
are exported (a labeled frame needs its two predecessors as context).

    python build_ball_dataset.py            # uses the default clip list below
Output: ../data/ball_dataset/{clip}/{frame:05d}.jpg + labels.json
"""

from __future__ import annotations

import json
import os
import sys

import cv2

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ball_dataset"))
IN_W, IN_H = 512, 288

# (video, perception cache, tag). Add clips here as more footage gets analyzed —
# every new analyzed video is free training data.
CLIPS = [
    ("../data/tennis_sample.mp4", "../data/output/real_match.perception.json", "highangle"),
    ("../data/yt_rally.mp4", "../data/output/yt_match.perception.json", "amateur"),
    # NOTE: yt_rally2 is the human gold BALL benchmark clip (data/gold/) — it must
    # NEVER be added here as training data (train/test leak). Removed 2026-07-07.
]


def build_clip(video_path: str, cache_path: str, tag: str) -> int:
    with open(cache_path, "r", encoding="utf-8") as f:
        c = json.load(f)
    ball_px = c["ball_px"]
    frame_step = int(c.get("frame_step", 1))
    out_dir = os.path.join(OUT, tag)
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sx, sy = IN_W / W, IN_H / H

    labels = {}
    idx = proc = 0
    while proc < len(ball_px):
        ok, frame = cap.read()
        if not ok:
            break
        if idx % frame_step == 0:
            cv2.imwrite(os.path.join(out_dir, f"{proc:05d}.jpg"),
                        cv2.resize(frame, (IN_W, IN_H)),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            p = ball_px[proc]
            if p is not None and proc >= 2:
                labels[str(proc)] = [round(p[0] * sx, 2), round(p[1] * sy, 2)]
            proc += 1
        idx += 1
    cap.release()
    with open(os.path.join(out_dir, "labels.json"), "w", encoding="utf-8") as f:
        json.dump({"n_frames": proc, "labels": labels}, f)
    print(f"{tag}: {proc} frames exported, {len(labels)} pseudo-labeled")
    return len(labels)


if __name__ == "__main__":
    total = 0
    for video, cache, tag in CLIPS:
        if not (os.path.exists(video) and os.path.exists(cache)):
            print(f"skip {tag}: missing {video if not os.path.exists(video) else cache}")
            continue
        total += build_clip(video, cache, tag)
    print(f"total labeled samples: {total}")
