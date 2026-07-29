"""eval_smoother.py — A/B the ball smoother: constant vs depth-aware process noise.

`smooth_forecast` runs in image pixels, so one `sigma_jerk` is only correct at one
court depth. The depth-aware variant rescales it by the local metre/pixel scale.
This measures whether that actually helps, on two axes that pull against each other:

  hit@10 / false-fire   vs the HUMAN GOLD CLICKS (the only honest accuracy test)
  jerkiness             mean |second difference| of the drawn track, px/frame^2 —
                        the "janky trail" the user reported, lower is better

Works from a committed perception cache. That is legitimate HERE and only here:
both arms consume the identical raw locks, so the comparison is exact even though
the absolute recall reflects whatever commit built the cache. Never quote the
absolute numbers from this tool as current — use eval_model_filters.py for that.

  cd backend && .venv/Scripts/python.exe ../tools/eval_smoother.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import ball as B, calibration, court  # noqa: E402

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
# clip -> (perception cache, court pts, gold labels, frame w/h)
CASES = {
    "yt_rally2": ("data/output/yt_rally2_v2.perception.json", "data/yt_rally2_pts.json",
                  "data/gold/yt_rally2.labels.json", (1280, 720)),
}


def jerkiness(track):
    """Mean |p[i-1] - 2p[i] + p[i+1]| over consecutive emitted triples."""
    vals = []
    for i in range(1, len(track) - 1):
        a, b, c = track[i - 1], track[i], track[i + 1]
        if a is None or b is None or c is None:
            continue
        vals.append(math.hypot(a[0] - 2 * b[0] + c[0], a[1] - 2 * b[1] + c[1]))
    return float(np.mean(vals)) if vals else float("nan")


def score(track, ball, noball, step, far_y):
    # Only frames the decimation actually processed are scoreable — see
    # tools/eval_gold.py:cache_index. Scoring an odd gold frame against the
    # even frame before it counts a timing offset as a miss.
    def at(f):
        return (f // step) if (f % step == 0 and f // step < len(track)) else None

    hit = tot = fh = ft = 0
    for f, v in ball.items():
        pf = at(f)
        if pf is None:
            continue
        tot += 1
        p = track[pf]
        ok = p is not None and math.dist(p, (v["x"], v["y"])) <= 10.0
        hit += ok
        if v["y"] < far_y:
            ft += 1; fh += ok
    nb = [f for f in noball if at(f) is not None]
    fires = sum(1 for f in nb if track[at(f)] is not None)
    return (100 * hit / max(tot, 1), 100 * fh / max(ft, 1),
            100 * fires / max(len(nb), 1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", default="yt_rally2", choices=list(CASES))
    ap.add_argument("--far-frac", type=float, default=0.36)
    args = ap.parse_args()

    cache_rel, pts_rel, labels_rel, (W, Hh) = CASES[args.clip]
    cache = json.loads((REPO / cache_rel).read_text(encoding="utf-8"))
    raw = [None if p is None else [float(p[0]), float(p[1])] for p in cache["ball_px"]]
    step = int(cache.get("frame_step") or 1)
    fps_eff = 60.0 / step if args.clip == "yt_rally2" else 30.0

    kp = json.loads((REPO / pts_rel).read_text(encoding="utf-8"))
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                       [kp[n] for n in CORN])
    from swingvision import courtfit
    fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court, W, Hh,
                                allow_roll=True)
    hfov = 70.0 if fit is None else float(calibration.hfov_from_focal(fit[3][5], W))

    g = {int(k): v for k, v in json.loads((REPO / labels_rel).read_text(encoding="utf-8"))["labels"].items()}
    ball = {f: v for f, v in g.items() if v.get("ball") and not v.get("unsure")}
    noball = [f for f, v in g.items() if v.get("ball") is False and not v.get("unsure")]
    far_y = args.far_frac * Hh

    # Post-chain up to (not including) the smoother — identical for both arms.
    tr = B.remove_outliers(raw, max_jump=max(W, Hh) * 0.06)
    tr = B.rectify_track(tr, max_speed_px=3000.0 / fps_eff, resid_px=35.0)
    tr = B.suppress_false_locks(tr, fps_eff=fps_eff)
    tr = B.gate_ball_to_court(tr, H, (W, Hh), hfov_deg=hfov)

    scale = []
    for p in tr:
        try:
            scale.append(None if p is None else calibration.court_scale_m_per_px(H, p))
        except Exception:
            scale.append(None)
    known = [s for s in scale if s]
    print(f"{args.clip}: {len(raw)} frames, fps_eff={fps_eff:.0f}, hfov={hfov:.0f}deg, "
          f"{sum(p is not None for p in tr)} locks into the smoother")
    if known:
        print(f"  metre/pixel scale at the locks: median {np.median(known):.3f}, "
              f"p10 {np.percentile(known,10):.3f}, p90 {np.percentile(known,90):.3f}")
    print(f"  gold: {len(ball)} ball / {len(noball)} no-ball, far band y<{far_y:.0f}\n")

    print(f"{'smoother':<26}{'hit@10':>9}{'far':>9}{'false-fire':>12}{'jerk px/f^2':>13}")
    print("-" * 69)
    arms = [("constant sigma_jerk", None, 50.0),
            ("depth-aware (median ref)", scale, 50.0),
            ("depth-aware (p10 ref)", scale, 10.0),
            ("depth-aware (p2 ref)", scale, 2.0)]
    for name, sc, pct in arms:
        out, coasted, _ = B.smooth_forecast(tr, fps_eff=fps_eff, scale_m_per_px=sc,
                                            jerk_ref_pct=pct)
        r, fr, ff = score(out, ball, noball, step, far_y)
        print(f"{name:<26}{r:>8.1f}%{fr:>8.1f}%{ff:>11.1f}%{jerkiness(out):>13.2f}")
    print("\nAccuracy measured against human gold clicks; jerkiness is a property of "
          "the drawn track. Both arms consume identical pre-smoother locks.")


if __name__ == "__main__":
    main()
