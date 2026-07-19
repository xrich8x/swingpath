"""Synthesize a CAMERA BUMP into an existing clip (watchdog validation).

Real bumped-mid-recording footage is rare, so make some: re-encode a segment
where every frame after --bump-at is crop-shifted by --shift px (diagonally),
exactly what a knocked tripod/fence mount does to the image. Output frames are
(w-shift, h-shift) so pre- and post-bump frames share one size.

  backend/.venv/Scripts/python.exe tools/make_bump_clip.py \
      data/amateur_clips/yt_deNCnfQjfoU.mp4 --start 800 --frames 900 \
      --bump-at 450 --shift 40 --out data/amateur_clips/bump_ntrp30.mp4

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
    ap.add_argument("--shift", type=int, default=40, help="bump size in px")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    s = args.shift
    ow, oh = w - s, h - s
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.start)
    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (ow, oh))
    n = 0
    while n < args.frames:
        ok, frame = cap.read()
        if not ok:
            break
        if n < args.bump_at:
            writer.write(frame[0:oh, 0:ow])
        else:
            writer.write(frame[s:h, s:w])
        n += 1
    cap.release()
    writer.release()
    print(f"wrote {args.out}: {n} frames @ {fps:.2f}fps, {ow}x{oh}, "
          f"bump (+{s}px x/y) at output frame {args.bump_at}")


if __name__ == "__main__":
    main()
