"""tools/make_label_plates.py - clean-plate frames for hand-labelling a court.

A shell court has faded lines and two people standing on them. Clicking corners on
one raw frame means clicking around the players and guessing where paint continues.
A temporal median over frames spread across the clip removes anything that moved and
leaves the court alone, which is the same clean-plate trick the setup tool already
uses on video - this just writes it to disk so `--gallery` can queue many clips.

NATIVE RESOLUTION IS NOT OPTIONAL. The saved corners are in the IMAGE's pixels, and
eval/run_refs.py pairs a `<stem>_pts.json` with the VIDEO of the same stem and scores
in the video's own pixels. A 1920-wide plate of a 3840-wide video would put every
clicked corner out by exactly 2x - silently, and in a way that looks like a detector
error. So the plate is written at the source resolution, and the median runs in
horizontal strips to keep a 4K stack out of memory.

    py tools/make_label_plates.py --out eval/_shell_gallery \
        data/incoming/Shell/flexi_franz_p01.mp4 ...
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np

N_FRAMES = 15          # enough to outvote two moving players
STRIPS = 12            # median in bands so a 4K stack never lands in RAM at once


def plate(video: Path, n=N_FRAMES):
    import cv2
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release(); return None
    idx = np.linspace(int(0.08 * total), int(0.92 * total), n).round().astype(int)
    frames = []
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, im = cap.read()
        if ok:
            frames.append(im)
    cap.release()
    if len(frames) < 3:
        return None
    h, w = frames[0].shape[:2]
    out = np.empty((h, w, 3), np.uint8)
    step = max(1, h // STRIPS)
    for y0 in range(0, h, step):
        y1 = min(h, y0 + step)
        band = np.stack([f[y0:y1] for f in frames], axis=0)
        out[y0:y1] = np.median(band, axis=0).astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import cv2
    od = Path(a.out); od.mkdir(parents=True, exist_ok=True)
    for v in a.videos:
        p = Path(v)
        if not p.exists():
            print(f"  MISSING {p}"); continue
        im = plate(p)
        if im is None:
            print(f"  no frames  {p.name}"); continue
        dst = od / f"{p.stem}.jpg"
        cv2.imwrite(str(dst), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"  {dst.name:28s} {im.shape[1]}x{im.shape[0]}")
    print(f"\n{len(list(od.glob('*.jpg')))} plates in {od}")


if __name__ == "__main__":
    main()
