"""inspect_false_locks.py — characterise every false lock on yt_rally2 no-ball
frames, so false-alarm fixes are targeted, not speculative. Zero GPU: reads the
shipped gated cache + homography only.

For each no-ball gold frame that the tracker locks, report:
  - image position and court projection (in/out of bounds)
  - local motion: how far the lock roams over a +/-R-frame neighbourhood (a real
    ball traverses; a fixture/persistent false lock stays put)
  - run length: how many consecutive processed frames form this near-static lock
"""
from __future__ import annotations
import json, sys, math
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import numpy as np
from swingvision import calibration, court

H = calibration.compute_homography(
    [court.LANDMARKS[n] for n in ("near_bl_doubles","near_br_doubles","far_bl_doubles","far_br_doubles")],
    [json.load(open(REPO/"data/yt_rally2_pts.json"))[n] for n in
     ("near_bl_doubles","near_br_doubles","far_bl_doubles","far_br_doubles")])

g = {int(k): v for k, v in json.load(open(REPO/"data/gold/yt_rally2.labels.json"))["labels"].items()}
noball = sorted(f for f, v in g.items() if v.get("ball") is False and not v.get("unsure"))
c = json.load(open(REPO/"data/output/yt_rally2_v2.perception.json"))
bp = c["ball_px"]; step = c["frame_step"]; n = len(bp)


def run_len(pf, radius=15.0):
    """consecutive processed frames around pf whose lock stays within `radius`."""
    if bp[pf] is None: return 0
    c0 = bp[pf]; L = 1
    for d in (1, -1):
        j = pf + d
        while 0 <= j < n and bp[j] is not None and math.dist(bp[j], c0) <= radius:
            L += 1; j += d
    return L


def roam(pf, R=8):
    """max displacement of the lock over +/-R processed frames (px)."""
    pts = [bp[j] for j in range(max(0,pf-R), min(n,pf+R+1)) if bp[j] is not None]
    if len(pts) < 2: return 0.0
    return max(math.dist(a, b) for a in pts for b in pts)


print(f"{'frame':>6} {'img(x,y)':>13} {'court(x,y)m':>14} {'inCourt':>8} {'roam±8':>7} {'runLen':>7}")
print("-"*70)
fires = 0
for f in noball:
    pf = f // step
    if pf >= n or bp[pf] is None:
        continue
    fires += 1
    p = bp[pf]
    cx, cy = calibration.image_to_court(H, [p])[0]
    ind = court.is_in_doubles(cx, cy, 3.0)
    print(f"{f:>6} ({p[0]:>6.0f},{p[1]:>4.0f}) ({cx:>6.1f},{cy:>6.1f}) {('IN' if ind else 'OUT'):>8}"
          f" {roam(pf):>7.0f} {run_len(pf):>7}")
print("-"*70)
print(f"{fires} false locks on {len(noball)} no-ball frames "
      f"({100*fires/len(noball):.1f}% base-cache false-fire)")
