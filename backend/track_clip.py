"""General amateur-clip tracker: players (YOLO-pose, auto imgsz) + ball (TrackNet)
drawn onto a segment of any clip. Near/far roles are assigned by relative feet
position (no per-clip pixel thresholds), so it works across camera angles.

    python track_clip.py ../data/yt_match40.mp4 --start 5100 --limit 150 --out tag
"""

from __future__ import annotations

import argparse

import cv2

from swingvision import events, pose
from swingvision.ball import BallDetector, remove_outliers, smooth_and_fill

NEAR_COLOR, FAR_COLOR, BALL_COLOR = (255, 230, 0), (255, 0, 255), (0, 255, 255)


def draw_pose(frame, p, color, label):
    for a, b in pose.COCO_SKELETON:
        xa, ya, ca = p.keypoints[a]
        xb, yb, cb = p.keypoints[b]
        if ca > 0.25 and cb > 0.25:
            cv2.line(frame, (int(xa), int(ya)), (int(xb), int(yb)), color, 2, cv2.LINE_AA)
    x1, y1, x2, y2 = (int(v) for v in p.box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
    cv2.putText(frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--pose-every", type=int, default=2, dest="pose_every")
    ap.add_argument("--imgsz", default="auto", help="pose inference size (int or 'auto')")
    ap.add_argument("--out", default="clip")
    args = ap.parse_args()

    imgsz = None if args.imgsz == "auto" else int(args.imgsz)
    bd = BallDetector("weights/tracknet.pt")
    pe = pose.PoseEstimator(imgsz=imgsz)  # imgsz=None -> "fast" preset (1280)
    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.start)

    frames, raw_ball, players_by = [], [], []
    last = []
    src = 0
    while len(frames) < args.limit // args.step:
        ok, frame = cap.read()
        if not ok:
            break
        if src % args.step == 0:
            i = len(frames)
            raw_ball.append(bd.detect(frame))
            if i % args.pose_every == 0:
                last = pose.keep_players(pe.estimate(frame), max_players=2)
            players_by.append(list(last))
            frames.append(frame)
        src += 1
    cap.release()
    print(f"processed {len(frames)} frames; ball {sum(p is not None for p in raw_ball)}/{len(frames)}")

    smoothed = smooth_and_fill(remove_outliers(raw_ball, max_jump=max(w, h) * 0.06), 7, 2)
    track = [(i, float(smoothed[i, 0]), float(smoothed[i, 1])) for i in range(len(smoothed))]
    hit_idx = set(events.detect_hits(track, angle_thresh_deg=70, min_gap_s=0.2))

    writer = cv2.VideoWriter(
        f"../data/output/{args.out}_tracked.mp4",
        cv2.VideoWriter_fourcc(*"mp4v"), fps / args.step, (w, h),
    )
    near_trail, far_trail = [], []
    saved = []
    for i, frame in enumerate(frames):
        # Assign near/far by relative feet-y: the lower (larger y) player is near.
        ps = sorted(players_by[i], key=lambda p: p.feet()[1], reverse=True)
        for j, p in enumerate(ps):
            is_near = (j == 0)
            color = NEAR_COLOR if is_near else FAR_COLOR
            (near_trail if is_near else far_trail).append((int(p.feet()[0]), int(p.feet()[1])))
            draw_pose(frame, p, color, "near" if is_near else "far")
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
        cv2.putText(frame, "our tracker on amateur footage", (16, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
        if i in (15, 40, 65, 90):
            fn = f"../data/output/{args.out}_frame_{i:03d}.png"
            cv2.imwrite(fn, frame)
            saved.append(fn)
    writer.release()
    print("saved:", saved)


if __name__ == "__main__":
    main()
