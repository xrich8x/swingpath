"""Line-fit AUTO court detection (project B), measured on the court gold labels.

No per-court model. The pipeline is generate -> score -> snap -> verify:
  1. GUESS GRID: sweep plausible behind-baseline court shapes, parameterised as a
     trapezoid (near/far baseline height, half-widths, centre). Widths/heights may
     exceed the frame, so OFF-FRAME corners are represented for free.
  2. SCORE cheaply: each guess's projected court lines vs a distance-transform of
     the amateur line mask (line_ridge_mask) — pick the top-K by coverage.
  3. SNAP the top-K onto the lines (refine_homography_bounded, ridge mask).
  4. VERIFY (verify_court): keep the best that clears the coverage+centrality gate;
     if none clears it, return None (falls back to manual — never a wrong court).

Scored against the human gold labels (same metrics as eval_court):
  detect%   fraction of usable frames an auto court was returned + verified
  corner    median px error of the 4 baseline corners vs the human clicks
  kp_err    median px error over all 14 keypoints
  IoU       court-outline overlap with the human court
  false%    unusable frames that wrongly returned a court (must stay ~0)

  backend/.venv/Scripts/python.exe tools/eval_court_autodetect.py --all --per-clip 3
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

GOLD = REPO / "data" / "gold"
DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


def _quad_iou(a, b):
    """Convex-quad IoU via shoelace + Sutherland-Hodgman (self-contained)."""
    def area(p):
        s = 0.0
        for i in range(len(p)):
            x1, y1 = p[i]; x2, y2 = p[(i + 1) % len(p)]
            s += x1 * y2 - x2 * y1
        return abs(s) / 2.0

    def clip(sub, clp):
        def inside(p, aa, bb):
            return (bb[0]-aa[0])*(p[1]-aa[1]) - (bb[1]-aa[1])*(p[0]-aa[0]) >= 0

        def isect(p1, p2, aa, bb):
            x1, y1 = p1; x2, y2 = p2; x3, y3 = aa; x4, y4 = bb
            den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
            if abs(den) < 1e-9:
                return p2
            t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / den
            return (x1 + t*(x2-x1), y1 + t*(y2-y1))
        s = 0.0
        for i in range(len(clp)):
            x1, y1 = clp[i]; x2, y2 = clp[(i+1) % len(clp)]
            s += x1*y2 - x2*y1
        if s < 0:
            clp = clp[::-1]
        out = sub
        for i in range(len(clp)):
            aa, bb = clp[i], clp[(i+1) % len(clp)]
            inp, out = out, []
            for j in range(len(inp)):
                cur, prv = inp[j], inp[j-1]
                if inside(cur, aa, bb):
                    if not inside(prv, aa, bb):
                        out.append(isect(prv, cur, aa, bb))
                    out.append(cur)
                elif inside(prv, aa, bb):
                    out.append(isect(prv, cur, aa, bb))
            if not out:
                return []
        return out
    inter = clip(a, b)
    if len(inter) < 3:
        return 0.0
    ai = area(inter)
    return ai / (area(a) + area(b) - ai + 1e-9)


# Court line samples + endpoints (court metres), cached — H-independent.
_S = _LINE_ID = _EA = _EB = None


def _court_samples(court):
    global _S, _LINE_ID, _EA, _EB
    if _S is None:
        S, lid, EA, EB = [], [], [], []
        for i, (a, b) in enumerate(court.LINES):
            EA.append(a); EB.append(b)
            n = max(2, int(math.hypot(b[0]-a[0], b[1]-a[1]) * 3))
            for t in np.linspace(0, 1, n):
                S.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))); lid.append(i)
        _S, _LINE_ID = np.asarray(S), np.asarray(lid)
        _EA, _EB = np.asarray(EA), np.asarray(EB)
    return _S, _LINE_ID, _EA, _EB


def _precompute(frame, calibration):
    """Per-frame maps: distance-to-line + the local LINE ORIENTATION (double-angle
    cos/sin, so 0 and 180deg are the same line) from image gradients."""
    import cv2
    mask = calibration.line_ridge_mask(frame)
    h, w = mask.shape[:2]
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    lang = np.arctan2(gy, gx) + np.pi / 2.0        # line dir = perpendicular to gradient
    return dt, np.cos(2*lang), np.sin(2*lang), w, h


def _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr):
    """Returns (global_score, n_lines_supported, n_lines_in_frame).

    A projected court-line sample is SUPPORTED if it lands on a real line pixel
    (<=tol) AND the local ridge orientation matches the projected line's direction
    (align>=athr). global_score = supported fraction. Per court line we also compute
    its own supported fraction; n_lines_supported counts distinct lines that clear
    0.5 — a structural check a court hallucinated onto clutter can't fake, because
    it would need MANY differently-oriented lines to line up at once."""
    S, lid, EA, EB = _court_samples(court)
    P = calibration.court_to_image(H, S)
    pa = calibration.court_to_image(H, EA)
    pb = calibration.court_to_image(H, EB)
    ang = np.arctan2(pb[:, 1]-pa[:, 1], pb[:, 0]-pa[:, 0])
    c2, s2 = np.cos(2*ang)[lid], np.sin(2*ang)[lid]
    x, y = np.round(P[:, 0]).astype(int), np.round(P[:, 1]).astype(int)
    inb = (x >= 0) & (x < w) & (y >= 0) & (y < h)
    nin = int(inb.sum())
    if nin < len(P) * 0.30:
        return 0.0, 0, 0
    xi, yi = np.clip(x, 0, w-1), np.clip(y, 0, h-1)
    align = cos2[yi, xi]*c2 + sin2[yi, xi]*s2
    sup = inb & (dt[yi, xi] <= tol) & (align >= athr)
    nL = int(lid.max()) + 1
    inb_cnt = np.bincount(lid, weights=inb.astype(float), minlength=nL)
    sup_cnt = np.bincount(lid, weights=sup.astype(float), minlength=nL)
    seen = inb_cnt >= 3                                   # line meaningfully in frame
    frac = np.where(seen, sup_cnt / np.maximum(inb_cnt, 1), 0.0)
    return float(sup.sum()) / nin, int((frac >= 0.5).sum()), int(seen.sum())


def _corners(cx, yn, yf, wn, wf):
    return {"near_bl_doubles": [cx-wn, yn], "near_br_doubles": [cx+wn, yn],
            "far_br_doubles": [cx+wf, yf], "far_bl_doubles": [cx-wf, yf]}


# --- Camera-angle prior (tools/build_pose_prior.py) -------------------------
_PRIOR_PATH = REPO / "data" / "court_pose_prior.json"
_PRIOR = None
PRIOR_TEMP = 6.0        # softens the plausibility weight used for ranking
PRIOR_MAHA_MAX = 55.0   # reject camera poses this far outside the learned spread
PRIOR_SAMPLES = 500     # Monte-Carlo court seeds drawn from the learned prior


def _load_prior():
    global _PRIOR
    if _PRIOR is None:
        if _PRIOR_PATH.exists():
            d = json.loads(_PRIOR_PATH.read_text())
            mu, cov = np.asarray(d["mean"]), np.asarray(d["cov"])
            _PRIOR = (mu, np.linalg.inv(cov), cov)   # mean, inverse-cov, cov
        else:
            _PRIOR = False
    return _PRIOR


def _maha(params, w, h, prior):
    """Mahalanobis distance of a candidate camera pose (params=(cx,yn,yf,wn,wf) in
    PIXELS) from the learned prior. 0 when no prior -> no effect."""
    if not prior:
        return 0.0
    cx, yn, yf, wn, wf = params
    p = np.array([cx/w, yn/h, yf/h, wn/w, wf/w]) - prior[0]
    return float(p @ prior[1] @ p)


def _params_from_corners(c):
    nbl, nbr, fbr, fbl = (np.asarray(c[k], float) for k in DBL)
    return ((nbl[0]+nbr[0]+fbr[0]+fbl[0])/4.0, (nbl[1]+nbr[1])/2.0,
            (fbl[1]+fbr[1])/2.0, (nbr[0]-nbl[0])/2.0, (fbr[0]-fbl[0])/2.0)


def _scan(axes, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr, prior):
    """Score every trapezoid. Returns [(rank, support, nlines, params, maha)] where
    rank = line-support x plausibility weight (so a plausible camera pose wins ties
    over an equally-well-fitting but implausible wrong-rung court)."""
    out = []
    for cx in axes[0]:
        for yn in axes[1]:
            for yf in axes[2]:
                if yf >= yn - 20:
                    continue
                for wn in axes[3]:
                    for wf in axes[4]:
                        if wf >= wn:
                            continue
                        try:
                            H = calibration.compute_homography(
                                court_pts, [_corners(cx, yn, yf, wn, wf)[n] for n in DBL])
                        except Exception:
                            continue
                        g, nl, _ = _ori_detail(H, calibration, court, dt, cos2, sin2,
                                               w, h, tol, athr)
                        if g > 0:
                            m = _maha((cx, yn, yf, wn, wf), w, h, prior)
                            rank = g * np.exp(-0.5 * m / PRIOR_TEMP)
                            out.append((rank, g, nl, (cx, yn, yf, wn, wf), m))
    out.sort(key=lambda t: t[0], reverse=True)
    return out


def _prior_seeds(prior, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr):
    """Monte-Carlo court seeds drawn straight from the learned camera-angle prior,
    so most seeds already sit on a plausible court -> far higher lock rate on the
    typical amateur framings than a blind grid, and each is already plausible."""
    rng = np.random.default_rng(0)
    out = []
    for s in rng.multivariate_normal(prior[0], prior[2], PRIOR_SAMPLES):
        cx, yn, yf = s[0]*w, s[1]*h, s[2]*h
        wn, wf = s[3]*w, s[4]*w
        if yf >= yn - 20 or wf >= wn or wn <= 0:
            continue
        try:
            H = calibration.compute_homography(
                court_pts, [_corners(cx, yn, yf, wn, wf)[n] for n in DBL])
        except Exception:
            continue
        g, nl, _ = _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr)
        if g > 0:
            m = _maha((cx, yn, yf, wn, wf), w, h, prior)
            out.append((g * np.exp(-0.5 * m / PRIOR_TEMP), g, nl, (cx, yn, yf, wn, wf), m))
    return out


def autodetect(frame, calibration, court, *, grid=4, topk=12,
               athr=0.80, accept=0.33, use_prior=True):
    """Prior-sampled + grid seeds -> local refine -> snap -> structural+plausibility
    gate. Returns (H, score, corners) or None (falls back to manual)."""
    dt, cos2, sin2, w, h = _precompute(frame, calibration)
    tol = max(2.0, w * 0.006)
    court_pts = [court.LANDMARKS[n] for n in DBL]
    prior = _load_prior() if use_prior else False

    coarse = ([0.40, 0.47, 0.53, 0.60], [0.74, 0.85, 0.95, 1.06],
              [0.18, 0.28, 0.38, 0.48], [0.40, 0.51, 0.61, 0.72],
              [0.20, 0.27, 0.35, 0.42])
    ax = tuple(np.asarray(v) * (w if i in (0, 3, 4) else h) for i, v in enumerate(coarse))
    ranked = _scan(ax, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr, prior)
    if prior:
        ranked += _prior_seeds(prior, calibration, court, court_pts,
                               dt, cos2, sin2, w, h, tol, athr)
        ranked.sort(key=lambda t: t[0], reverse=True)

    # coarse-to-fine: local grid around the top-3 (plausibility-ranked) coarse seeds
    steps = [(coarse[i][1]-coarse[i][0]) * (w if i in (0, 3, 4) else h) for i in range(5)]
    seeds = []
    for t in ranked[:3]:
        p = t[3]
        local = tuple(np.array([p[i]-steps[i]/2, p[i], p[i]+steps[i]/2]) for i in range(5))
        seeds += _scan(local, calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr, prior)
    seeds += ranked
    seeds.sort(key=lambda t: t[0], reverse=True)

    best = None
    tried = 0
    for _rank, _g, _nl, p, _m in seeds:
        if tried >= topk:
            break
        tried += 1
        try:
            Hs, ref, _ = calibration.refine_homography_bounded(
                frame, _corners(*p), max_move_px=55.0, mask_fn=calibration.line_ridge_mask)
        except Exception:
            continue
        g, nl, nseen = _ori_detail(Hs, calibration, court, dt, cos2, sin2, w, h, tol, athr)
        maha = _maha(_params_from_corners(ref), w, h, prior)
        # accept gate: enough DISTINCT court lines (>=40% in-frame, min 4), a
        # PLAUSIBLE camera pose (prior), and the coverage/centrality check. Tuned to
        # LOCK often (the overlay lets the user nudge a rough fit) while still
        # refusing true non-court frames (they support few oriented lines).
        need = max(4, int(0.4 * nseen))
        if g >= accept and nl >= need and maha <= PRIOR_MAHA_MAX \
                and calibration.verify_court(frame, Hs).ok and (best is None or g > best[1]):
            best = (Hs, g, ref)
    return best


def score_clip(clip, per_clip, grid, topk, use_prior=True):
    lab_path = GOLD / f"{clip}.court.labels.json"
    if not lab_path.exists():
        return None
    import cv2
    from swingvision import calibration, court

    labs = json.loads(lab_path.read_text(encoding="utf-8"))["labels"]
    frames_dir = GOLD / "frames" / clip
    usable = [k for k, v in labs.items()
              if v.get("court") is True and all(n in v.get("keypoints", {}) for n in DBL)]
    unusable = [k for k, v in labs.items() if v.get("court") is False]
    if per_clip:
        usable = usable[:: max(1, len(usable) // per_clip)][:per_clip]
        unusable = unusable[:per_clip]

    det = 0
    corner_e, kp_e, ious = [], [], []
    for k in usable:
        img = cv2.imread(str(frames_dir / f"f{int(k):05d}.jpg"))
        if img is None:
            continue
        res = autodetect(img, calibration, court, grid=grid, topk=topk, use_prior=use_prior)
        if res is None:
            continue
        det += 1
        H = res[0]
        gk = labs[k]["keypoints"]
        corner_e += [float(np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                      - np.array(gk[n])))) for n in DBL]
        kp_e += [float(np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                  - np.array(gk[n])))) for n in gk if n in court.LANDMARKS]
        pc = [tuple(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]) for n in DBL]
        ious.append(_quad_iou(pc, [tuple(gk[n]) for n in DBL]))

    false = 0
    for k in unusable:
        img = cv2.imread(str(frames_dir / f"f{int(k):05d}.jpg"))
        if img is None:
            continue
        if autodetect(img, calibration, court, grid=grid, topk=topk) is not None:
            false += 1

    return {"clip": clip, "usable": len(usable), "det": det,
            "detect_pct": 100 * det / len(usable) if usable else 0.0,
            "corner": median(corner_e) if corner_e else None,
            "kp": median(kp_e) if kp_e else None,
            "iou": median(ious) if ious else None,
            "unusable": len(unusable),
            "false_pct": 100 * false / len(unusable) if unusable else None}


def fmt(x, s="{:.1f}"):
    return "  -  " if x is None else s.format(x)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--per-clip", type=int, default=3, help="frames per clip (0=all)")
    ap.add_argument("--grid", type=int, default=4, help="guesses per axis")
    ap.add_argument("--topk", type=int, default=8, help="candidates to snap+verify")
    ap.add_argument("--no-prior", action="store_true", help="disable the camera-angle prior")
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))
    print(f"camera-angle prior: {'OFF' if args.no_prior else 'ON'}")

    hdr = (f"{'clip':22s} {'frm':>3s} {'detect%':>7s} {'corner':>6s} "
           f"{'kp_err':>6s} {'IoU':>5s} {'false%':>6s}")
    print(hdr); print("-" * len(hdr))
    agg = {"det": [], "cor": [], "iou": [], "false": []}
    for c in clips:
        r = score_clip(c, args.per_clip if args.per_clip else 0, args.grid, args.topk,
                       use_prior=not args.no_prior)
        if r is None:
            continue
        print(f"{r['clip']:22s} {r['usable']:3d} {fmt(r['detect_pct']):>7s} "
              f"{fmt(r['corner']):>6s} {fmt(r['kp']):>6s} "
              f"{fmt(r['iou'],'{:.2f}'):>5s} {fmt(r['false_pct']):>6s}")
        agg["det"].append(r["detect_pct"])
        if r["corner"] is not None:
            agg["cor"].append(r["corner"])
        if r["iou"] is not None:
            agg["iou"].append(r["iou"])
        if r["false_pct"] is not None:
            agg["false"].append(r["false_pct"])
    print("-" * len(hdr))
    print(f"{'MEAN':22s} {'':3s} {fmt(np.mean(agg['det'])):>7s} "
          f"{fmt(np.median(agg['cor']) if agg['cor'] else None):>6s} "
          f"{'':6s} {fmt(np.median(agg['iou']) if agg['iou'] else None,'{:.2f}'):>5s} "
          f"{fmt(np.mean(agg['false']) if agg['false'] else None):>6s}")


if __name__ == "__main__":
    main()
