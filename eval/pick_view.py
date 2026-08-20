"""eval/pick_view.py - choose WHICH camera angle of a cut recording to test.

A broadcast recording is several cameras: the elevated top-down view that shows the
whole court, a tight low camera behind the baseline that shows only the near half,
serve cams, close-ups. `collect_frames.py`'s dominant-view cluster keeps whichever
has the most airtime, which on a highlight reel mixes them - and a half-court angle
is a different detection problem from the top-down one, so pooling them measures
nothing.

Only the top-down view is worth testing: it is the clearest, it shows the whole
court, and it is the one a court fit should be able to determine.

Two steps, with a human in the middle:

  1. propose - dump N numbered candidates as a contact sheet
       py eval/pick_view.py --clip 45VdNMtbulA --propose 24
  2. keep    - write the ones that ARE the top-down view
       py eval/pick_view.py --clip 45VdNMtbulA --keep 3,5,8,11,14,17,20,23

The selection is a human ruling on camera angle, made from the pixels. It is NOT
the detector's opinion: asking `courtfit` which frames to keep would hand the test
set to the thing under test. Choices are appended to eval/clip_classes.json so the
denominator stays auditable.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DROP = REPO / "eval" / "frames"
SHEETS = REPO / "eval" / "sheets"
CACHE = REPO / "eval" / "_candidates"
CLASSES = REPO / "eval" / "clip_classes.json"


def _videos(clip: str):
    import sys
    sys.path.insert(0, str(REPO / "eval"))
    from collect_frames import discover
    return discover().get(clip, [])


def propose(clip: str, n: int, cols: int = 6, tile: int = 300):
    import cv2
    import numpy as np

    vids = _videos(clip)
    if not vids:
        raise SystemExit(f"no video found for group {clip}")
    cache = CACHE / clip
    if cache.exists():
        shutil.rmtree(cache)
    cache.mkdir(parents=True, exist_ok=True)

    per = max(1, n // len(vids))
    idx = 0
    cells = []
    for v in vids:
        cap = cv2.VideoCapture(str(v))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            cap.release()
            continue
        lo, hi = int(0.05 * total), int(0.95 * total)
        for pos in np.linspace(lo, hi, per).round().astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
            ok, img = cap.read()
            if not ok:
                continue
            cv2.imwrite(str(cache / f"c{idx:03d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            th = int(tile * img.shape[0] / img.shape[1])
            cell = cv2.resize(img, (tile, th))
            for col, w in (((0, 0, 0), 6), ((60, 255, 90), 2)):
                cv2.putText(cell, str(idx), (8, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, w, cv2.LINE_AA)
            cells.append(cell)
            idx += 1
        cap.release()

    if not cells:
        raise SystemExit("no frames decoded")
    hh = min(c.shape[0] for c in cells)
    rows = []
    for i in range(0, len(cells), cols):
        band = [c[:hh] for c in cells[i:i + cols]]
        while len(band) < cols:
            band.append(np.zeros((hh, tile, 3), np.uint8))
        rows.append(np.hstack(band))
    SHEETS.mkdir(parents=True, exist_ok=True)
    out = SHEETS / f"pick_{clip}.jpg"
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"{idx} candidates -> {cache}\nsheet -> {out}")
    print(f"then: py eval/pick_view.py --clip {clip} --keep <comma-separated indices>")


def keep(clip: str, which: list[int], note: str):
    cache = CACHE / clip
    if not cache.exists():
        raise SystemExit(f"run --propose first (no {cache})")
    dest = DROP / clip
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in which:
        src = cache / f"c{i:03d}.jpg"
        if src.exists():
            shutil.copy2(src, dest / f"v{i:03d}.jpg")
            n += 1
    print(f"{clip}: kept {n} frames -> {dest}")

    rec = json.loads(CLASSES.read_text(encoding="utf-8")) if CLASSES.exists() else {}
    rec.setdefault("view_selection", {
        "_what": "Human ruling on WHICH camera angle of a cut recording is under test. "
                 "Only the top-down view that shows the whole court is kept; half-court "
                 "cameras, serve cams and close-ups are a different problem and pooling "
                 "them measures nothing. Chosen from eval/sheets/pick_<clip>.jpg by eye, "
                 "never by asking the detector."})
    rec["view_selection"][clip] = {"kept": which, "note": note}
    CLASSES.write_text(json.dumps(rec, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", required=True)
    ap.add_argument("--propose", type=int, default=0)
    ap.add_argument("--keep", default=None)
    ap.add_argument("--note", default="top-down view only")
    a = ap.parse_args()
    if a.propose:
        propose(a.clip, a.propose)
    elif a.keep:
        keep(a.clip, [int(x) for x in a.keep.split(",") if x.strip() != ""], a.note)
    else:
        ap.error("pass --propose N or --keep i,j,k")


if __name__ == "__main__":
    main()
