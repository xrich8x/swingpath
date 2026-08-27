"""SUPERSEDED 2026-08-28 — DO NOT RUN. Use `tools/p0_3_crop_probe.py`.

This probe's 78.8% is withdrawn. Three defects, all fatal:
  1. it selected its population with `hit_xy[1] > court.NET_Y`, the ball's
     GROUND-projected contact, which calls 193 of 196 yt_match40 contacts "far";
  2. its detection test asked "does ANY person box overlap the region", which the
     near player satisfies almost regardless on a 448 px box;
  3. it indexed frames as `t_hit_s * match["video"]["fps"]`, but that field is the
     EFFECTIVE frame rate, so on a 60 fps clip it seeked to half the intended time.
Kept only so the defects stay legible next to their replacement.
See docs/evidence/p0-3-crop-around-contact.md.
"""

"""P0-3 — does a native-resolution CROP around the ball contact find the far player
where a full frame does not?

P0-2 measured full-frame downscaling as a dead end for the far player (yt_match40
11.0% @1280 -> 0.1% @640 -> 0.0% @384). pm-agent's other mitigation is to crop
around the known contact location at native resolution instead, which is also the
lever `docs/evidence/the-far-player-is-a-detection-problem.md` named and never
tested ("a far-court tile detector for POSE analogous to --far-ball-tile").

The A/B, on the SAME frames and the SAME image region:
  control : pose on the FULL frame at imgsz=1280; does any detected person overlap
            the region where we expect the striker?
  crop    : pose on just that region, cropped at native resolution and fed at
            imgsz=640 (so the player fills far more of the input tensor).

Contacts come from an existing analyzed match.json (`hit_xy` is ball-derived, so it
does not depend on the pose stage this probe is measuring — no self-grading).
Far-half contacts are selected geometrically (court y > NET_Y), not from the `player`
field, so a mis-attribution cannot pick the population.

Run from backend/:
  POSE_IMGSZ unset; this script sets imgsz explicitly per arm.
  ../backend/.venv-train/Scripts/python.exe ../tools/probe_crop_pose.py \
      --match ../data/output/p0_1280_yt_match40.json \
      --video ../data/incoming/Hardcourt/yt_match40.mp4 \
      --keypoints ../data/yt_match40_pts.json \
      --out ../data/output/p0_3_crop_yt_match40.json --device cuda
"""

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from swingvision import calibration, court, pose as pose_mod
from swingvision.pipeline import calibrate_video

CROP_SIZES = [192, 320, 448]   # native px, square, centred on the projected contact
CROP_IMGSZ = 640               # what the crop is fed to the model at
FULL_IMGSZ = 1280              # the control, matching the P0-2 baseline


def _person_boxes(poses):
    """(x1,y1,x2,y2) for every detected person."""
    out = []
    for p in poses:
        pts = [(x, y) for x, y, c in p.keypoints if c > 0.3]
        if pts:
            xs = [q[0] for q in pts]
            ys = [q[1] for q in pts]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def _overlaps(box, region):
    ax1, ay1, ax2, ay2 = box
    bx1, by1, bx2, by2 = region
    return not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--limit", type=int, default=None, help="first N contacts (smoke test)")
    args = ap.parse_args()

    match = json.load(open(args.match))
    fps = match["video"]["fps"]
    H, _, _, _, _, _, _ = calibrate_video(args.video, args.keypoints, None)

    contacts = [s for s in match["shots"] if s["hit_xy"][1] > court.NET_Y]
    if args.limit:
        contacts = contacts[: args.limit]

    cap = cv2.VideoCapture(args.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    full_est = pose_mod.PoseEstimator(device=args.device, imgsz=FULL_IMGSZ)
    crop_est = pose_mod.PoseEstimator(device=args.device, imgsz=CROP_IMGSZ)

    hits = {"full": 0, **{f"crop{c}": 0 for c in CROP_SIZES}}
    n = 0
    for s in contacts:
        fi = int(round(s["t_hit_s"] * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        px, py = calibration.court_to_image(H, [s["hit_xy"]])[0]
        if not (0 <= px < W and 0 <= py < Hh):
            continue
        n += 1

        # Control: full frame, does any person overlap the largest crop region?
        r = CROP_SIZES[-1] // 2
        region = (px - r, py - r, px + r, py + r)
        if any(_overlaps(b, region) for b in _person_boxes(full_est.estimate(frame))):
            hits["full"] += 1

        # Crop arms: native-resolution crop, fed at CROP_IMGSZ.
        for c in CROP_SIZES:
            h = c // 2
            x1, y1 = int(max(0, px - h)), int(max(0, py - h))
            x2, y2 = int(min(W, px + h)), int(min(Hh, py + h))
            if x2 - x1 < 32 or y2 - y1 < 32:
                continue
            if _person_boxes(crop_est.estimate(frame[y1:y2, x1:x2])):
                hits[f"crop{c}"] += 1

    cap.release()
    result = {
        "measured_against": (
            "ball-derived contact locations from an existing analyzed match.json, "
            "projected through the manual court calibration; NOT against human pose "
            "labels — this measures DETECTION RATE at a known location, not pose accuracy"
        ),
        "video": os.path.basename(args.video),
        "contacts_evaluated": n,
        "full_imgsz": FULL_IMGSZ,
        "crop_imgsz": CROP_IMGSZ,
        "detected": hits,
        "rate_pct": {k: (round(100.0 * v / n, 1) if n else None) for k, v in hits.items()},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
