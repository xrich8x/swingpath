"""eval_gated_gold.py — the false-fire ladder: raw model -> shipped gates (E5+).

eval_detector_gold.py scores the RAW detector (no tracker, no gates). That is the
67.5% false-fire number. But the product never shows raw output: every detection
passes the tracker's gates (fusion two-model agreement, court+vertical CONE gate,
static-lock gate, acquire bounds), then rectify, then the live-ball filter. This
tool measures what actually reaches the user by reading the SHIPPED gated tracks
(the perception caches) and sampling them at the gold frames — so we optimise the
number the product prints, not a scary raw stat.

Only yt_rally2 has a committed calibrated cache (court gate ACTIVE), so it is the
one clip where the user's "constrain to court + vertically" gate can be measured.
Base cache  = tracker gates (incl. court cone gate).  .live cache = + live filter.
Raw is recomputed on the same no-ball frames for a clean within-clip comparison.

  cd backend && .venv/Scripts/python.exe ../tools/eval_gated_gold.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

CLIP = "yt_rally2"
VIDEO = REPO / "data" / "yt_rally2.mp4"
LABELS = REPO / "data" / "gold" / "yt_rally2.labels.json"
BASE = REPO / "data" / "output" / "yt_rally2_v2.perception.json"
LIVE = REPO / "data" / "output" / "yt_rally2_v2.perception.live.json"
RADIUS = 10.0
FAR_Y = 260.0


def load_gold():
    g = {int(k): v for k, v in json.loads(LABELS.read_text(encoding="utf-8"))["labels"].items()}
    ball = {f: v for f, v in g.items() if v.get("ball") and not v.get("unsure")}
    noball = {f for f, v in g.items() if v.get("ball") is False and not v.get("unsure")}
    return ball, noball


def sample_track(cache_path, frames):
    """Return {orig_frame: (x,y)|None} sampled from a gated cache at gold frames."""
    c = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    step = int(c.get("frame_step", 1))
    bp = c["ball_px"]
    out = {}
    for f in frames:
        pf = f // step
        out[f] = tuple(bp[pf]) if 0 <= pf < len(bp) and bp[pf] is not None else None
    return out, step, len(bp)


def raw_detector_at(frames):
    """Run baseline BallNet on a 3-frame window ending at each frame (matches
    eval_detector_gold methodology) so raw vs gated is apples-to-apples."""
    os.environ.setdefault("BALLNET_WEIGHTS", "weights/ballnet.pt")
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=os.environ.get("EVAL_DEVICE", "cpu"))
    cap = cv2.VideoCapture(str(VIDEO))
    out = {}
    for f in sorted(frames):
        frs = []
        for j in (f - 2, f - 1, f):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, j))
            ok, im = cap.read()
            if ok:
                frs.append(im)
        if len(frs) < 3:
            out[f] = None
            continue
        det.reset()
        p = None
        for im in frs:
            p = det.detect(im)
        out[f] = tuple(p) if p is not None else None
    cap.release()
    return out


def ff(track, noball):
    fired = [f for f in noball if track.get(f) is not None]
    return 100 * len(fired) / max(len(noball), 1), sorted(fired)


def recall(track, ball):
    hit = far_hit = far_tot = 0
    for f, v in ball.items():
        p = track.get(f)
        ok = p is not None and math.dist(p, (v["x"], v["y"])) <= RADIUS
        hit += ok
        if v["y"] < FAR_Y:
            far_tot += 1
            far_hit += ok
    return (100 * hit / max(len(ball), 1),
            100 * far_hit / max(far_tot, 1), far_tot)


def main():
    ball, noball = load_gold()
    print(f"clip={CLIP}  {len(ball)} ball / {len(noball)} no-ball gold frames\n")

    raw = raw_detector_at(noball | set(ball))
    base, step, n = sample_track(BASE, noball | set(ball))
    live, _, _ = sample_track(LIVE, noball | set(ball))
    print(f"cache: frame_step={step}, {n} processed frames; mapping pf=f//{step}\n")

    rows = [
        ("RAW BallNet (no gates)", raw),
        ("+ tracker gates (court cone + static-lock + fusion)", base),
        ("+ live-ball filter (full shipped stack)", live),
    ]
    print(f"{'stage':<52}{'false-fire':>12}{'recall':>9}{'far-recall':>12}")
    print("-" * 85)
    for name, tr in rows:
        f_pct, fired = ff(tr, noball)
        r, fr, fn = recall(tr, ball)
        print(f"{name:<52}{f_pct:>11.1f}%{r:>8.1f}%{fr:>11.1f}%")
    print("-" * 85)
    print(f"(far-recall over {recall(base, ball)[2]} far-court ball frames; "
          f"radius={RADIUS:.0f}px)")

    # which no-ball frames survive each stage — names the actual confusers
    print("\nno-ball frames still firing after full stack:",
          ff(live, noball)[1] or "none")


if __name__ == "__main__":
    main()
