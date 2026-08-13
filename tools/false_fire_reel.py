"""false_fire_reel.py — watch each false fire happen, instead of looking at a still.

WHY VIDEO AND NOT ANOTHER CONTACT SHEET
---------------------------------------
Every classification this project has published was made from a frozen crop, and
a frozen crop cannot answer the question the classification turns on. A racquet
head and a ball are both ball-sized, ball-coloured blobs in one frame; what
separates them is that the racquet is on a short arc **pinned to a person** and
the ball is on a long free flight. Session G part 1 spent a GPU-free eval and
Session G part 4 spent another proving the pipeline cannot tell them apart from
geometry — and the whole time the discriminator was motion, which no still shows.

So this renders a short reel around each false fire: the detector run
CONTINUOUSLY across the window (not the 3-frame scoring stub), its lock drawn on
every frame, so you watch the lock either track a swinging racquet or sit on a
fence post. The labelled frame is flagged as it passes.

Two panes, for the same reason false_fire_viewer.py shows two crops: the wide
pane says what the object is attached to, the zoom pane says whether it is
literally a ball. Neither alone is enough.

WHAT IT IS NOT: a scorer. It renders what `inspect_false_locks.py --json` already
found. Nothing here changes a number.

  py tools/false_fire_reel.py --locks data/output/false_fires/new/locks.json \\
      --device cuda --out-dir data/output/false_fires/reels
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs  # noqa: E402

PRE_S, POST_S = 0.50, 0.50      # window around the labelled frame
HOLD_FRAMES = 8                 # freeze on the labelled frame so it registers
WIDE_SRC = 620                  # source px in the wide pane — a whole player
ZOOM_SRC = 110                  # source px in the zoom pane — the object itself
PANE = 620
BAR = 74
SLOW = 2                        # repeat each frame N times: these are fast events
#: Annotation colour. NOT yellow/green: the objects under review are a tennis
#: ball and the things mistaken for one, all of which are yellow-green, so a
#: yellow marker hides inside its own subject. Magenta occurs nowhere on court.
MARK = (255, 0, 255)


def _crop(im, x, y, src_px, out_px, interp):
    h, w = im.shape[:2]
    x0 = int(min(max(0, x - src_px // 2), max(0, w - src_px)))
    y0 = int(min(max(0, y - src_px // 2), max(0, h - src_px)))
    x1, y1 = min(w, x0 + src_px), min(h, y0 + src_px)
    c = im[y0:y1, x0:x1]
    if c.size == 0:
        return None, 0.0, 0.0
    sx, sy = out_px / max(x1 - x0, 1), out_px / max(y1 - y0, 1)
    c = cv2.resize(c, (out_px, out_px), interpolation=interp)
    return c, (x - x0) * sx, (y - y0) * sy


def _ring(img, cx, cy, colour, r=17, thick=2):
    """An open ring, never a filled dot. The pixels being judged stay visible —
    a marker that covers the evidence is how you end up classifying your own
    annotation."""
    cv2.circle(img, (int(cx), int(cy)), r, colour, thick, cv2.LINE_AA)
    cv2.circle(img, (int(cx), int(cy)), 1, colour, -1, cv2.LINE_AA)


def _text(img, s, xy, colour=(235, 235, 235), scale=0.52, thick=1):
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0),
                thick + 2, cv2.LINE_AA)
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, colour,
                thick, cv2.LINE_AA)


def build_segment(cap, det, clip, row, fps, tags):
    """One false fire, as a list of composed BGR frames.

    The detector is fed the window SEQUENTIALLY from three frames before the
    start, so every drawn lock comes from a warm 3-frame stack exactly as it
    would in the pipeline. `inspect_false_locks` deliberately uses an isolated
    3-frame stub because that is what the scorer does; here the question is what
    the lock DOES over time, which needs the continuous run.
    """
    f = row["frame"]
    pre, post = int(round(PRE_S * fps)), int(round(POST_S * fps))
    start = max(0, f - pre)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, start - 3))
    det.reset()

    # anchor the panes on the false lock so the object stays put while the
    # scene moves around it — a pane that chases the lock hides the motion
    ax, ay = row["x"], row["y"]
    out, n = [], 0
    while n < (start - max(0, start - 3)) + pre + post + 1:
        ok, im = cap.read()
        if not ok:
            break
        idx = max(0, start - 3) + n
        n += 1
        lock = det.detect(im)
        if idx < start:
            continue

        wide, wx, wy = _crop(im, ax, ay, WIDE_SRC, PANE, cv2.INTER_LINEAR)
        zoom, zx, zy = _crop(im, ax, ay, ZOOM_SRC, PANE, cv2.INTER_NEAREST)
        if wide is None or zoom is None:
            continue
        # where the labelled lock sits, on every frame — the fixed reference
        _ring(wide, wx, wy, (90, 90, 90), r=21, thick=1)
        _ring(zoom, zx, zy, (90, 90, 90), r=64, thick=1)
        # where the detector is firing on THIS frame
        if lock is not None:
            for pane, src, ox, oy in ((wide, WIDE_SRC, wx, wy),
                                      (zoom, ZOOM_SRC, zx, zy)):
                s = PANE / src
                px, py = ox + (lock[0] - ax) * s, oy + (lock[1] - ay) * s
                if -40 < px < PANE + 40 and -40 < py < PANE + 40:
                    _ring(pane, px, py, MARK,
                          r=int(17 * (1 if src == WIDE_SRC else 3.2)))
        _text(wide, "wide", (10, 22), (170, 170, 170), 0.5)
        _text(zoom, f"zoom {ZOOM_SRC}px", (10, 22), (170, 170, 170), 0.5)

        canvas = np.zeros((PANE + BAR, PANE * 2 + 6, 3), np.uint8)
        canvas[BAR:, :PANE] = wide
        canvas[BAR:, PANE + 6:] = zoom
        here = idx == f
        _text(canvas, f"{clip}:{f}", (12, 27), (255, 255, 255), 0.66, 2)
        _text(canvas, tags, (12, 52), (150, 190, 220), 0.48)
        off = idx - f
        _text(canvas, f"{off:+d} fr" if not here else "THIS FRAME  (human: no ball)",
              (PANE + 16, 27), (255, 255, 255) if here else (150, 150, 150),
              0.62, 2 if here else 1)
        _text(canvas, "grey ring = the labelled lock   magenta = detector, this frame",
              (PANE + 16, 52), (150, 150, 150), 0.44)
        if here:
            cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1,
                                           canvas.shape[0] - 1), (255, 255, 255), 3)
        reps = SLOW * (HOLD_FRAMES if here else 1)
        out.extend([canvas] * reps)
    return out


def encode(frames, path, fps):
    """Pipe to ffmpeg/libx264 rather than cv2.VideoWriter: mp4v writes a file
    most browsers refuse to play, and the point of this is watching it."""
    if not frames:
        return False
    h, w = frames[0].shape[:2]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
        stdin=subprocess.PIPE)
    for fr in frames:
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    return p.wait() == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--locks", required=True)
    ap.add_argument("--compare", action="append", default=[],
                    help="NAME=locks.json — annotates each clip with whether that "
                         "model also fires on the same frame")
    ap.add_argument("--only-new", action="append", default=[],
                    help="NAME — keep only fires this model has and NAME does not")
    ap.add_argument("--clip", action="append", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--fps", type=int, default=24, help="playback rate")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap segments per clip (for a quick look)")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    blob = json.loads(Path(args.locks).read_text(encoding="utf-8"))
    locks = blob["locks"]
    others = {}
    for spec in args.compare:
        name, _, path = spec.partition("=")
        ob = json.loads(Path(path).read_text(encoding="utf-8"))
        others[name] = {(r["clip"], r["frame"]) for r in ob["locks"]}
    for name in args.only_new:
        if name not in others:
            raise SystemExit(f"--only-new {name} needs a matching --compare {name}=...")
        locks = [r for r in locks if (r["clip"], r["frame"]) not in others[name]]

    os.environ["BALLNET_WEIGHTS"] = str(REPO / "backend" / blob["weights"])
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=args.device)

    by = {}
    for r in locks:
        by.setdefault(r["clip"], []).append(r)
    clips = args.clip or list(by)

    made = []
    for clip in clips:
        rows = sorted(by.get(clip, []), key=lambda r: r["frame"])
        if args.limit:
            rows = rows[:args.limit]
        if not rows:
            continue
        cap = cv2.VideoCapture(str(gs.GOLD[clip].video_path))
        if not cap.isOpened():
            print(f"  cannot open {clip}"); continue
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = []
        for i, r in enumerate(rows):
            tags = "  ".join(
                (f"also {n}" if (clip, r["frame"]) in s else f"NOT {n}")
                for n, s in others.items())
            if r.get("klass"):
                tags = f"class {r['klass']}   " + tags
            frames.extend(build_segment(cap, det, clip, r, fps, tags))
            print(f"    {clip} {i+1}/{len(rows)}  f{r['frame']}", flush=True)
        cap.release()
        out = Path(args.out_dir) / f"{clip}.mp4"
        if encode(frames, out, args.fps):
            mb = out.stat().st_size / 1e6
            secs = len(frames) / args.fps
            print(f"  wrote {out}  ({len(rows)} fires, {secs:.0f}s, {mb:.1f} MB)")
            made.append((clip, len(rows), secs, out))
        else:
            print(f"  ffmpeg failed for {clip}")

    print(f"\n{len(made)} reel(s), {sum(m[1] for m in made)} false fires, "
          f"{sum(m[2] for m in made)/60:.1f} min total")


if __name__ == "__main__":
    main()
