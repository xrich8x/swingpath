"""hit_coverage_probe.py — why do we produce shots for only 5/17 strokes? (E3b)

Scores hit DETECTORS (not full shots) against the HUD stroke list, on the same
court-plane track the pipeline builds. Two contenders:

  angle    events.detect_hits — the shipping detector: court-plane turn >= 70 deg.
           Needs three consecutive good samples exactly at contact, which is
           precisely where amateur tracks break (fast ball, blur, far court).
  ysign    prototype: a hit is the court-Y VELOCITY changing sign (the ball
           starts travelling back toward the other baseline), with hysteresis
           (|vy| must exceed a floor on both sides, averaged over a small
           window) so far-court jitter and net-cord dribbles don't fire it.
           Rally tennis is 1-D in y; this needs far less local track quality.

Coverage: a HUD stroke is covered when a hit lands in [t_panel-1.6, t_panel-0.1].
Extras (hits outside every window) are the false-fire side; both numbers print.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\hit_coverage_probe.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import ball as ball_mod          # noqa: E402
from swingvision import calibration, court, events  # noqa: E402
from swingvision.ball import smooth_and_fill       # noqa: E402


def build_track(cache_path: str, kp_path: str, fps: float):
    """Rebuild the pipeline's court-plane track (minus lens/warp — this probe's
    clip is a static, manually calibrated camera)."""
    cache = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    kp = json.loads(Path(kp_path).read_text(encoding="utf-8"))
    names = ["near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles"]
    H = calibration.compute_homography([court.LANDMARKS[n] for n in names],
                                       [kp[n] for n in names])
    ball_px = cache["ball_px"]
    RUNOFF = 2.5
    ball_px = ball_mod.remove_outliers(ball_px, max_jump=1280 * 0.06)
    raw = []
    for px in ball_px:
        if px is None:
            raw.append(None)
            continue
        x, y = calibration.image_to_court(H, [px])[0]
        ok = (-RUNOFF <= x <= court.DOUBLES_WIDTH + RUNOFF
              and -RUNOFF <= y <= court.LENGTH + RUNOFF)
        raw.append([float(x), float(y)] if ok else None)
    raw = ball_mod.cap_court_jumps(raw, max_step_m=84.0 / fps)
    sm = smooth_and_fill(raw, window=7, polyorder=2)
    track = [(i / fps, float(sm[i, 0]), float(sm[i, 1])) for i in range(len(sm))]
    has_data = [r is not None for r in raw]
    return track, has_data


def detect_hits_ysign(track, has_data, fps, *, vy_floor: float = 2.0,
                      win_s: float = 0.15, min_gap_s: float = 0.4,
                      min_support: int = 3) -> list[int]:
    """Prototype: hits = sign changes of court-y velocity, with hysteresis.

    vy is averaged over `win_s` on each side of the candidate, both averages
    must exceed `vy_floor` m/s with opposite signs, and each side must contain
    `min_support` real detections (not interpolation) — so a gap bridged by
    smooth_and_fill can still yield a hit, but pure invention cannot.
    """
    y = np.array([p[2] for p in track])
    vy = np.gradient(y) * fps
    w = max(2, int(win_s * fps))
    n = len(track)
    cands = []
    for k in range(w, n - w):
        vin = float(np.mean(vy[k - w:k]))
        vout = float(np.mean(vy[k:k + w]))
        if vin * vout < 0 and abs(vin) >= vy_floor and abs(vout) >= vy_floor:
            if sum(has_data[k - w:k]) >= min_support and \
                    sum(has_data[k:k + w]) >= min_support:
                cands.append((k, abs(vin) + abs(vout)))
    hits: list[int] = []
    for k, strength in cands:
        if hits and (k - hits[-1]) / fps < min_gap_s:
            continue                       # first crossing of the reversal wins
        hits.append(k)
    return hits


def coverage(hit_times, hud_shots, lag=(0.1, 1.6)):
    used, cov = set(), 0
    for r in hud_shots:
        t = r["t_start_s"]
        cands = [(i, h) for i, h in enumerate(hit_times)
                 if i not in used and lag[0] <= t - h <= lag[1]]
        if cands:
            used.add(min(cands, key=lambda ih: t - ih[1])[0])
            cov += 1
    extras = len(hit_times) - len(used)
    return cov, extras


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", default=str(REPO / "data/output/fps/rally2_launch.perception.json"))
    ap.add_argument("--keypoints", default=str(REPO / "data/yt_rally2_pts.json"))
    ap.add_argument("--hud", default=str(REPO / "data/gold/hud_yt_rally2.json"))
    ap.add_argument("--fps", type=float, default=60.0)
    args = ap.parse_args()

    track, has_data = build_track(args.cache, args.keypoints, args.fps)
    hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))["shots"]
    print(f"track: {len(track)} frames @ {args.fps:g} fps, "
          f"{sum(has_data)} with real ball data; HUD strokes: {len(hud)}\n")

    cache = json.loads(Path(args.cache).read_text(encoding="utf-8"))
    near_c, far_c = cache.get("near_court") or [], cache.get("far_court") or []
    prox = events.detect_hits_by_proximity(track, near_c, far_c)
    detectors = {
        "angle70 (shipping)": [track[k][0] for k in
                               events.detect_hits(track, angle_thresh_deg=70,
                                                  min_gap_s=0.3)],
        "ysign (prototype)": [track[k][0] for k in
                              detect_hits_ysign(track, has_data, args.fps)],
        "proximity (E3d)": [track[k][0] for k in prox],
    }
    hdr = f"{'detector':<22} {'hits':>5} {'HUD covered':>12} {'extras':>7}"
    print(hdr)
    print("-" * len(hdr))
    for name, times in detectors.items():
        cov, extras = coverage(times, hud)
        print(f"{name:<22} {len(times):>5} {cov:>6}/{len(hud):<5} {extras:>7}")
    print()
    for name, times in detectors.items():
        print(f"{name}: " + ", ".join(f"{t:.2f}" for t in times))


if __name__ == "__main__":
    main()
