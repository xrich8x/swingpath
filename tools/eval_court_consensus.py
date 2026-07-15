"""MULTI-FRAME AGREEMENT: keep the court that reproduces across frames.

A clip is video of a court that doesn't move, so the SAME court should be found in
every frame. A wrong-rectangle lock (service box / adjacent court) is unstable — it
depends on which stray lines a particular frame happened to offer, so it won't be
reproduced. The true court is found again and again in the same place.

So: auto-fit K frames independently, group the results that agree (mean corner
distance <= AGREE_PX), take the LARGEST agreeing group, and return its per-corner
median. If nothing agrees, refuse. This turns the single biggest quality problem
(wrong-rung locks) into a vote, and recovers locks on frames where players happened
to hide the lines.

  backend/.venv/Scripts/python.exe tools/eval_court_consensus.py --all --k 8
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

GOLD = REPO / "data" / "gold"
DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
AGREE_PX = 30.0     # two courts "agree" when their corners sit within this
MIN_VOTES = 2       # need at least this many frames agreeing to trust a court


def _corner_dist(a, b):
    return float(np.mean([np.hypot(a[n][0]-b[n][0], a[n][1]-b[n][1]) for n in DBL]))


def consensus(fits):
    """fits: list of {corner:[x,y]} (or None). Returns (court, votes) or (None, 0)."""
    valid = [f for f in fits if f]
    if not valid:
        return None, 0
    best, best_n = None, 0
    for f in valid:
        group = [g for g in valid if _corner_dist(f, g) <= AGREE_PX]
        if len(group) > best_n:
            best, best_n = group, len(group)
    if best_n < MIN_VOTES:
        return None, best_n
    return {n: [float(np.median([g[n][0] for g in best])),
                float(np.median([g[n][1] for g in best]))] for n in DBL}, best_n


def score_clip(clip, k, save_dir=None):
    import cv2
    from swingvision import calibration, court
    import court_setup_server as cs

    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        return None
    labs = json.loads(lab_path.read_text())["labels"]
    usable = {kk: v for kk, v in labs.items()
              if v.get("court") is True and all(n in v.get("keypoints", {}) for n in DBL)}
    if not usable:
        return None
    keys = sorted(usable, key=lambda x: int(x))
    pick = keys[:: max(1, len(keys) // k)][:k]

    fits, imgs = [], []
    for kk in pick:
        im = cv2.imread(str(GOLD / "frames" / clip / f"f{int(kk):05d}.jpg"))
        if im is None:
            continue
        imgs.append((kk, im))
        fits.append(cs.auto_fit(im))
    n_lock_single = sum(1 for f in fits if f)
    court_pts, votes = consensus(fits)

    if court_pts is None:
        return {"clip": clip, "lock": False, "err": None, "votes": votes,
                "frames": len(fits), "single": n_lock_single}

    H = calibration.compute_homography([court.LANDMARKS[n] for n in DBL],
                                       [court_pts[n] for n in DBL])
    errs = [float(np.mean([np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                      - np.asarray(v["keypoints"][n]))) for n in DBL]))
            for v in usable.values()]
    if save_dir and imgs:
        vis = imgs[len(imgs)//2][1].copy()
        for a, b in court.LINES:
            pa = calibration.court_to_image(H, [a])[0]
            pb = calibration.court_to_image(H, [b])[0]
            cv2.line(vis, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])),
                     (90, 235, 120), 2, cv2.LINE_AA)
        cv2.imwrite(str(save_dir / f"{clip}_lock.jpg"), vis)
    return {"clip": clip, "lock": True, "err": float(np.median(errs)), "votes": votes,
            "frames": len(fits), "single": n_lock_single}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--k", type=int, default=8, help="frames to fit per clip")
    ap.add_argument("--save", default=None)
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))
    save_dir = Path(args.save) if args.save else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    print(f"{'clip':22s} {'lock':>5s} {'err_px':>7s} {'votes':>6s}")
    print("-" * 45)
    for c in clips:
        r = score_clip(c, args.k, save_dir)
        if r is None:
            continue
        rows.append(r)
        print(f"{r['clip']:22s} {'yes' if r['lock'] else 'no':>5s} "
              f"{('%.1f' % r['err']) if r['err'] is not None else '  -  ':>7s} "
              f"{r['votes']}/{r['frames']:>3}")
    if save_dir:
        (save_dir / "results.json").write_text(json.dumps(rows, indent=1))
    lock = [r for r in rows if r["lock"]]
    good = [r for r in lock if r["err"] < 35]
    print("-" * 45)
    if lock:
        print(f"locked {len(lock)}/{len(rows)} clips | usable (<35px) {len(good)}/{len(rows)} | "
              f"median err {np.median([r['err'] for r in lock]):.1f}px")


if __name__ == "__main__":
    main()
