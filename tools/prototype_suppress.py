"""prototype_suppress.py — dial in RECALL-SAFE, image-space false-lock suppressors
on the cached yt_rally2 track (zero GPU). The court-projection approach was proven
a dead end (real far balls and false locks overlap completely in court coords, so
any court-envelope that kills the false locks also kills the far ball). These
filters never touch the court projection — they use only on-screen kinematics,
where a real ball ALWAYS moves and a fixture does not.

  persistence : a lock staying within RADIUS px for >= RUN_MIN consecutive
                processed frames is a fixture (real balls traverse the screen).
  isolated    : a lock with no neighbour within STEP px at +/-1 frame has no
                trajectory continuation -> a one-frame blip.

Reported at every setting: false-fire AND recall AND far-recall, so we never buy
precision with recall. base cache = 61.5% ff / 47.7% rec / 26.1% far.
"""
from __future__ import annotations
import json, sys, math
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

g = {int(k): v for k, v in json.load(open(REPO/"data/gold/yt_rally2.labels.json"))["labels"].items()}
ball = {f: v for f, v in g.items() if v.get("ball") and not v.get("unsure")}
noball = sorted(f for f, v in g.items() if v.get("ball") is False and not v.get("unsure"))
c = json.load(open(REPO/"data/output/yt_rally2_v2.perception.json"))
step = c["frame_step"]; BASE = list(c["ball_px"])


def f_persist(tr, radius, run_min):
    out = list(tr); n = len(tr); i = 0
    while i < n:
        if tr[i] is None: i += 1; continue
        j = i + 1
        while j < n and tr[j] is not None and math.dist(tr[j], tr[i]) <= radius:
            j += 1
        if j - i >= run_min:
            for k in range(i, j): out[k] = None
        i = j
    return out


def f_isolated(tr, step_px):
    out = list(tr); n = len(tr)
    for i, p in enumerate(tr):
        if p is None: continue
        prv = tr[i-1] if i > 0 else None
        nxt = tr[i+1] if i+1 < n else None
        near = ((prv is not None and math.dist(p, prv) <= step_px) or
                (nxt is not None and math.dist(p, nxt) <= step_px))
        if not near: out[i] = None
    return out


def measure(tr, tag):
    fires = [f for f in noball if (f//step) < len(tr) and tr[f//step] is not None]
    ff = 100*len(fires)/len(noball)
    hit = far_hit = far_tot = 0
    for f, v in ball.items():
        pf = f//step; p = tr[pf] if pf < len(tr) else None
        ok = p is not None and math.dist(p, (v["x"], v["y"])) <= 10.0
        hit += ok
        if v["y"] < 260.0: far_tot += 1; far_hit += ok
    rec = 100*hit/len(ball); far = 100*far_hit/max(far_tot,1)
    print(f"{tag:<44}{ff:>7.1f}%{rec:>9.1f}%{far:>10.1f}%   fires={len(fires)}")
    return fires


def f_minseg(tr, step_px, min_len):
    """keep a lock only if it belongs to a run of >= min_len consecutive locks
    each within step_px of the previous (a ball-plausible trajectory segment)."""
    out = [None]*len(tr); n = len(tr); i = 0
    while i < n:
        if tr[i] is None: i += 1; continue
        j = i + 1
        while j < n and tr[j] is not None and math.dist(tr[j], tr[j-1]) <= step_px:
            j += 1
        if j - i >= min_len:
            for k in range(i, j): out[k] = tr[k]
        i = j
    return out


def f_smooth(tr, step_px, min_len, max_accel):
    """within each ball-plausible segment of length>=min_len, require bounded
    per-frame acceleration (|second difference|). Chaotic short excursions (a
    mislock jumping around a player) fail; smooth arcs pass."""
    seg = f_minseg(tr, step_px, min_len)
    out = list(seg); n = len(seg); i = 0
    while i < n:
        if seg[i] is None: i += 1; continue
        j = i + 1
        while j < n and seg[j] is not None: j += 1
        run = list(range(i, j))
        if len(run) >= 3:
            accels = []
            for k in range(1, len(run)-1):
                a, b, c2 = seg[run[k-1]], seg[run[k]], seg[run[k+1]]
                ax = a[0]-2*b[0]+c2[0]; ay = a[1]-2*b[1]+c2[1]
                accels.append(math.hypot(ax, ay))
            if accels and (sum(accels)/len(accels)) > max_accel:
                for k in run: out[k] = None
        i = j
    return out


print(f"{'setting':<44}{'false-fire':>7}{'recall':>9}{'far-rec':>10}")
print("-"*82)
measure(BASE, "base cache")
print("- persistence r=12 (the clean win) -----------")
P = f_persist(BASE, 12.0, 6)
measure(P, "  persist r=12 run>=6")
print("- min-segment length on top of persistence ---")
for ml in (3, 4, 5):
    measure(f_minseg(P, 220.0, ml), f"  +minseg step<=220 len>={ml}")
print("- smoothness on top of persistence -----------")
for ml in (3, 4):
    for ma in (60.0, 40.0):
        measure(f_smooth(P, 220.0, ml, ma), f"  +smooth len>={ml} accel<={ma:.0f}")
print("-"*82)
best = f_minseg(P, 220.0, 4)
print("survivors after persist+minseg(4):",
      [f for f in noball if (f//step)<len(best) and best[f//step] is not None])
