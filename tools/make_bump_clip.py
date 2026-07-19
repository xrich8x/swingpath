"""Synthesize a CAMERA BUMP into an existing clip (watchdog validation).

Real bumped-mid-recording footage is rare, so make some: re-encode a segment
where every frame after --bump-at is crop-shifted by (--shift-x, --shift-y) px,
exactly what a knocked tripod/fence mount does to the image. Output frames are
(w-shift_x, h-shift_y) so pre- and post-bump frames share one size.

PREFER --pad (default): output keeps the source frame size, pre-bump frames
are the source VERBATIM, and post-bump frames are shifted with a black fill at
the vacated edge (like a pan revealing unseen area). Measured lesson from the
--crop mode: cropping changes the framing itself - a 40px horizontal crop of
yt_deNCnfQjfoU cut the near-right corner (x=612 of 640) out of the pre-bump
half (8/8 consensus votes -> 2/8), and even a bottom-only 40px crop broke the
framing the camera-angle prior expects (8/8 -> 4/8). Padding has neither
problem.

  backend/.venv/Scripts/python.exe tools/make_bump_clip.py \
      data/amateur_clips/yt_deNCnfQjfoU.mp4 --start 800 --frames 900 \
      --bump-at 450 --shift-y 40 --out data/amateur_clips/bump_ntrp30b.mp4

Then analyze with pre-bump keypoints and expect the pipeline to print
"camera change detected ... court RE-ACQUIRED" once the bump passes.
"""

from __future__ import annotations

import argparse


def main():
    import cv2

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--start", type=int, default=0, help="first source frame")
    ap.add_argument("--frames", type=int, default=900, help="frames to keep")
    ap.add_argument("--bump-at", type=int, default=450,
                    help="output frame index where the camera gets bumped")
    ap.add_argument("--shift-x", type=int, default=0, help="bump size in x, px")
    ap.add_argument("--shift-y", type=int, default=40, help="bump size in y, px")
    ap.add_argument("--crop", action="store_true",
                    help="legacy mode: shrink the frame instead of padding")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import numpy as np

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sx, sy = args.shift_x, args.shift_y
    if sx <= 0 and sy <= 0:
        raise SystemExit("need a nonzero --shift-x and/or --shift-y")
    ow, oh = (w - sx, h - sy) if args.crop else (w, h)
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.start)
    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (ow, oh))
    n = 0
    while n < args.frames:
        ok, frame = cap.read()
        if not ok:
            break
        if args.crop:
            out = frame[0:oh, 0:ow] if n < args.bump_at else frame[sy:h, sx:w]
        elif n < args.bump_at:
            out = frame
        else:
            out = np.zeros_like(frame)
            out[0:h - sy, 0:w - sx] = frame[sy:h, sx:w]
        writer.write(out)
        n += 1
    cap.release()
    writer.release()
    print(f"wrote {args.out}: {n} frames @ {fps:.2f}fps, {ow}x{oh} "
          f"({'crop' if args.crop else 'pad'} mode), "
          f"bump (+{sx}px x, +{sy}px y) at output frame {args.bump_at}")


if __name__ == "__main__":
    main()
