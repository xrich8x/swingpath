"""Build the court-keypoint training set from every calibrated clip.

The continuous-learning loop for amateur court detection: each clip with a
confirmed calibration (a user's Court Setup corners, or a gate-passing learned
fit) contributes per-frame keypoint labels — the 14 court landmarks projected
through that clip's homography, composed with the tracked per-frame camera
motion. Add a clip + its corners below (or via the Court Setup tab), rerun this,
retrain: the model learns every new camera angle it meets.

    python build_court_dataset.py
Output: ../data/court_dataset/{clip}/{frame:05d}.jpg (640x360) + labels.json
"""

from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swingvision import calibration, court

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "court_dataset"))
IN_W, IN_H = 640, 360
FRAME_EVERY = 5   # sample every Nth processed frame (adjacent frames are near-identical)

# (video, corners JSON or "learned", perception cache with cam_motion, tag)
CLIPS = [
    ("../data/tennis_sample.mp4", "learned", "../data/output/real_match.perception.json", "highangle"),
    ("../data/yt_rally.mp4", "../data/yt_court_pts.json", "../data/output/yt_match.perception.json", "indoor_low"),
    ("../data/yt_rally2.mp4", "../data/yt_rally2_pts.json", "../data/output/demo30.perception.json", "indoor_elev"),
]


def base_homography(video_path, source):
    if source == "learned":
        from swingvision import pipeline
        H, err, src, _, _ = pipeline.calibrate_video(video_path)
        print(f"  learned base H ({src}, {err:.1f}px)")
        return H
    with open(source, "r", encoding="utf-8") as f:
        return calibration.homography_from_landmarks(json.load(f))


def build_clip(video_path, cal_source, cache_path, tag):
    H = base_homography(video_path, cal_source)
    cam = None
    frame_step = 1
    if cache_path and os.path.exists(cache_path):
        c = json.load(open(cache_path))
        cam = c.get("cam_motion")
        frame_step = int(c.get("frame_step", 1))

    out_dir = os.path.join(OUT, tag)
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sx, sy = IN_W / W, IN_H / Hh
    court_pts = [court.LANDMARKS[n] for n in calibration.COURT_KP_LANDMARKS]

    labels = {}
    idx = proc = kept = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % frame_step == 0:
            if proc % FRAME_EVERY == 0:
                A = np.eye(3)
                if cam and proc < len(cam):
                    A[:2, :] = np.asarray(cam[proc], dtype=float).reshape(2, 3)
                H_t = A @ H
                pts = calibration.court_to_image(H_t, court_pts)
                kps = [[round(float(p[0]) * sx, 2), round(float(p[1]) * sy, 2)] for p in pts]
                cv2.imwrite(os.path.join(out_dir, f"{kept:05d}.jpg"),
                            cv2.resize(frame, (IN_W, IN_H)), [cv2.IMWRITE_JPEG_QUALITY, 92])
                labels[str(kept)] = kps
                kept += 1
            proc += 1
        idx += 1
    cap.release()
    with open(os.path.join(out_dir, "labels.json"), "w", encoding="utf-8") as f:
        json.dump({"n_frames": kept, "kp_names": calibration.COURT_KP_LANDMARKS, "labels": labels}, f)
    print(f"{tag}: {kept} labeled frames")
    return kept


if __name__ == "__main__":
    total = 0
    for video, cal, cache, tag in CLIPS:
        if not os.path.exists(video) or (cal != "learned" and not os.path.exists(cal)):
            print(f"skip {tag}: missing inputs")
            continue
        total += build_clip(video, cal, cache, tag)
    print(f"total labeled frames: {total}")
