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

"""Render what the P0-3 crop probe actually saw, so a human can check it.

`probe_crop_pose.py` reports "a person was detected near the projected contact".
That is a COUNT, and a count cannot tell you WHICH person — the far player, the
near player leaking in, a spectator, or a line judge. Trap T18: a claim about what
a frame contains is not evidence until somebody renders the frame.

Each tile is one far-half contact, cropped to the 448 px probe region at native
resolution and blown up, with:
  magenta cross  the projected ball-contact point (where we EXPECT the striker)
  green box      a person found by the FULL-FRAME pass (the control arm)
  cyan box       a person found by the CROP pass
Magenta/cyan on purpose: the subject and every confuser on a tennis court are
yellow-green, so a yellow marker hides inside the thing it points at (rule 9).

Run from backend/:
  ../backend/.venv-train/Scripts/python.exe ../tools/render_crop_probe.py \
      --match ../data/output/p0_1280_yt_match40.json \
      --video ../data/incoming/Hardcourt/yt_match40.mp4 \
      --keypoints ../data/yt_match40_pts.json \
      --out ../data/output/p0_3_crop_sheet.png --device cuda
"""

import argparse
import os
import sys
import json

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from swingvision import calibration, court, pose as pose_mod
from swingvision.pipeline import calibrate_video

CROP = 448
TILE = 320          # rendered tile size
COLS = 4


def _boxes(poses):
    out = []
    for p in poses:
        pts = [(x, y) for x, y, c in p.keypoints if c > 0.3]
        if pts:
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--n", type=int, default=16, help="tiles to render (evenly spaced)")
    args = ap.parse_args()

    match = json.load(open(args.match))
    fps = match["video"]["fps"]
    H, _, _, _, _, _, _ = calibrate_video(args.video, args.keypoints, None)
    contacts = [s for s in match["shots"] if s["hit_xy"][1] > court.NET_Y]
    step = max(1, len(contacts) // args.n)
    contacts = contacts[::step][: args.n]

    cap = cv2.VideoCapture(args.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    full_est = pose_mod.PoseEstimator(device=args.device, imgsz=1280)
    crop_est = pose_mod.PoseEstimator(device=args.device, imgsz=640)

    tiles = []
    for s in contacts:
        fi = int(round(s["t_hit_s"] * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok:
            continue
        px, py = calibration.court_to_image(H, [s["hit_xy"]])[0]
        h = CROP // 2
        x1, y1 = int(max(0, px - h)), int(max(0, py - h))
        x2, y2 = int(min(W, px + h)), int(min(Hh, py + h))
        if x2 - x1 < 32 or y2 - y1 < 32:
            continue
        sub = frame[y1:y2, x1:x2].copy()

        # full-frame arm: draw any person overlapping this region, in region coords
        for (bx1, by1, bx2, by2) in _boxes(full_est.estimate(frame)):
            if not (bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2):
                cv2.rectangle(sub, (int(bx1 - x1), int(by1 - y1)),
                              (int(bx2 - x1), int(by2 - y1)), (0, 255, 0), 2)
        # crop arm
        for (bx1, by1, bx2, by2) in _boxes(crop_est.estimate(frame[y1:y2, x1:x2])):
            cv2.rectangle(sub, (int(bx1), int(by1)), (int(bx2), int(by2)),
                          (255, 255, 0), 1)
        # expected contact point
        cx, cy = int(px - x1), int(py - y1)
        cv2.drawMarker(sub, (cx, cy), (255, 0, 255), cv2.MARKER_CROSS, 26, 2)

        sub = cv2.resize(sub, (TILE, TILE), interpolation=cv2.INTER_NEAREST)
        cv2.putText(sub, f"t={s['t_hit_s']:.1f}s f{fi}", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)
        tiles.append(sub)
    cap.release()

    if not tiles:
        print("no tiles rendered")
        return
    rows = []
    for i in range(0, len(tiles), COLS):
        row = tiles[i:i + COLS]
        while len(row) < COLS:
            row.append(np.zeros_like(tiles[0]))
        rows.append(np.hstack(row))
    sheet = np.vstack(rows)
    legend = np.zeros((34, sheet.shape[1], 3), np.uint8)
    cv2.putText(legend, "magenta=expected contact  green=FULL-frame person  cyan=CROP person",
                (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(args.out, np.vstack([legend, sheet]))
    print(f"wrote {args.out}  ({len(tiles)} tiles)")


if __name__ == "__main__":
    main()
