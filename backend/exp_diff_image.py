"""Experiment 3c: side-by-side visual diff of the ARCHIVED demo30 ball track
(968 locks) vs the FRESH reproducible track (NEW781) at the frames where they
disagree hardest. Green circle = archive, red X = fresh. Each tile carries a
zoom inset so the eye can settle who is on the real ball.

Writes data/output/regression_diff.jpg (new file; nothing overwritten).
Run from backend/:  .venv\\Scripts\\python.exe exp_diff_image.py
"""

import json
import os

import cv2
import numpy as np

D = os.path.join("..", "data", "output")
VIDEO = os.path.join("..", "data", "yt_rally2.mp4")
OUT = os.path.join(D, "regression_diff.jpg")
FRAME_STEP = 2   # cache index i -> source frame 2*i (60fps source)
FPS = 60.0


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)["ball_px"]


def pick_frames(arch, new):
    """3 frames where both lock but far apart (worst first, >=3s apart),
    then 3 archive-only frames spread across the clip."""
    both_far, arch_only = [], []
    for i, (a, b) in enumerate(zip(arch, new)):
        if a and b:
            dist = float(np.hypot(a[0] - b[0], a[1] - b[1]))
            if dist > 25:
                both_far.append((dist, i))
        elif a and not b:
            arch_only.append(i)
    both_far.sort(reverse=True)
    chosen = []
    for _, i in both_far:
        if all(abs(i - j) > 90 for j, _ in chosen):   # >=3s apart
            chosen.append((i, "both locked, >25px apart"))
        if len(chosen) == 3:
            break
    for k in (0.2, 0.5, 0.8):
        target = int(len(arch) * k)
        i = min(arch_only, key=lambda x: abs(x - target))
        chosen.append((i, "archive locked, fresh has NOTHING"))
    return chosen


def draw_tile(frame, a, b, t_s, case):
    img = frame.copy()
    if a:
        cv2.circle(img, (int(a[0]), int(a[1])), 14, (0, 220, 0), 3)
    if b:
        x, y = int(b[0]), int(b[1])
        cv2.line(img, (x - 12, y - 12), (x + 12, y + 12), (0, 0, 255), 3)
        cv2.line(img, (x - 12, y + 12), (x + 12, y - 12), (0, 0, 255), 3)
    # Zoom inset (2x, 120px box) around each marked point, so the viewer can
    # tell a tennis ball from a HUD logo without squinting.
    h, w = img.shape[:2]
    corner_x = w - 250
    for pt, color, cy in ((a, (0, 220, 0), 10), (b, (0, 0, 255), 270)):
        if not pt:
            continue
        x, y = int(pt[0]), int(pt[1])
        x0, y0 = max(0, min(w - 120, x - 60)), max(0, min(h - 120, y - 60))
        crop = cv2.resize(frame[y0:y0 + 120, x0:x0 + 120], (240, 240),
                          interpolation=cv2.INTER_NEAREST)
        cv2.drawMarker(crop, (int((x - x0) * 2), int((y - y0) * 2)), color,
                       cv2.MARKER_CROSS, 30, 2)
        cv2.rectangle(crop, (0, 0), (239, 239), color, 4)
        if cy + 240 <= h - 10:
            img[cy:cy + 240, corner_x:corner_x + 240] = crop
    img = cv2.resize(img, (640, 360))
    bar = np.zeros((26, 640, 3), np.uint8)
    cv2.putText(bar, f"t={t_s:5.1f}s  {case}", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def main() -> int:
    arch = load("demo30.perception.json")
    new = load("demo30.perception.NEW781.json")
    chosen = pick_frames(arch, new)
    wanted = {i * FRAME_STEP: (i, case) for i, case in chosen}

    tiles = {}
    cap = cv2.VideoCapture(VIDEO)
    src = 0
    while wanted and src <= max(wanted):
        ok, frame = cap.read()
        if not ok:
            break
        if src in wanted:
            i, case = wanted.pop(src)
            tiles[i] = draw_tile(frame, arch[i], new[i], src / FPS, case)
        src += 1
    cap.release()

    order = [i for i, _ in chosen if i in tiles]
    row = lambda idxs: np.hstack([tiles[i] for i in idxs])
    grid = np.vstack([row(order[:3]), row(order[3:6])])
    header = np.zeros((34, grid.shape[1], 3), np.uint8)
    cv2.putText(header,
                "demo30 regression: GREEN circle = ARCHIVE (968 locks, unreproducible)"
                "   RED X = FRESH run (781 locks, bit-reproducible)",
                (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
                cv2.LINE_AA)
    cv2.imwrite(OUT, np.vstack([header, grid]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"[experiment] wrote {OUT} ({len(order)} disagreement frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
