"""Court auto-calibration: line-fit + camera prior + regulation-structure matching.

The perception stage that finds the court in amateur footage WITHOUT a learned
model: detect distinct straight lines, score candidate courts by orientation-aware
line support, rank poses by a camera prior learned from labeled courts, demand the
REGULATION STRUCTURE (each court line claiming its own real line, both directions),
and hard-gate every output through a physical 6-DOF camera re-fit — the module can
never emit a shape that is not a real camera's view of a regulation tennis court.

Developed and measured against the hand-labeled gold set (scorecards in git; the
eval harness lives in tools/eval_court_autodetect.py and tools/
eval_court_consensus.py and imports this module). Multi-frame consensus voting +
the clay/shell evidence-stacking rescue live here too, plus the two pipeline
entry points:

  auto_fit_frame(frame, calibration, court)   -> corners or None (one frame)
  fit_video_frames(frames, calibration, court) -> (corners, votes, tag) (a clip)

Confidence law (held on every clip incl. cold tests): >=6/8 agreeing frames has
always been a correct court; every wrong lock had <=4 votes. Callers auto-accept
only tag=="vote" with votes>=6; anything else goes to the overlay confirm tool.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
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


def _detect_lines(mask, w):
    """The REAL straight lines in the frame, as distinct infinite lines.

    Hough gives segments; segments of the same painted line are merged into ONE line
    (normal form rho/theta) so we can ask the structural question: does each court
    line land on its OWN real line? Returns [(theta, rho, weight)]."""
    import cv2
    segs = cv2.HoughLinesP(mask, 1, np.pi/180, threshold=45,
                           minLineLength=max(25, int(w*0.05)), maxLineGap=12)
    if segs is None:
        return []
    raw = []
    for x1, y1, x2, y2 in segs[:, 0]:
        th = np.arctan2(y2-y1, x2-x1)              # direction
        n = th + np.pi/2.0                         # normal
        rho = x1*np.cos(n) + y1*np.sin(n)
        if rho < 0:                                # canonical sign
            n, rho = n + np.pi, -rho
        raw.append((np.mod(n, np.pi), rho, float(np.hypot(x2-x1, y2-y1))))
    merged = []
    for n, rho, wt in sorted(raw, key=lambda r: -r[2]):
        for i, (mn, mr, mw) in enumerate(merged):
            dth = abs(np.mod(n - mn + np.pi/2, np.pi) - np.pi/2)
            if dth < np.deg2rad(4) and abs(rho - mr) < max(6.0, w*0.012):
                tot = mw + wt
                merged[i] = ((mn*mw + n*wt)/tot, (mr*mw + rho*wt)/tot, tot)
                break
        else:
            merged.append((n, rho, wt))
    return merged


def _clay_mask(frame, calibration):
    """Hue-agnostic, structure-cleaned line mask for clay/shell.

    Two problems with clay: (1) the default mask demands sat<90 ("must be WHITE") and
    clay lines are lighter-but-ORANGE, so it sees nothing; (2) the clay surface itself
    is speckly, so a permissive mask returns the lines PLUS a storm of texture noise.
    Fix (1) with sat_max=255. Fix (2) by trusting STRUCTURE: court lines are long and
    continuous, texture noise is short and isolated — so keep only pixels that belong
    to a long straight segment (Hough), which erases the speckle and leaves clean
    lines for the snap to lock onto."""
    import cv2
    raw = calibration.line_ridge_mask(frame, tau=12, sat_max=255)
    segs = cv2.HoughLinesP(raw, 1, np.pi/180, threshold=50,
                           minLineLength=max(40, int(frame.shape[1] * 0.08)), maxLineGap=14)
    clean = np.zeros_like(raw)
    if segs is not None:
        for x1, y1, x2, y2 in segs[:, 0]:
            cv2.line(clean, (int(x1), int(y1)), (int(x2), int(y2)), 255, 2)
    return clean


def _precompute(frame, calibration, mask_fn=None):
    """Per-frame maps: distance-to-line, the local LINE ORIENTATION (double-angle
    cos/sin, so 0 and 180deg are the same line), and the DISTINCT real lines."""
    import cv2
    mask = (mask_fn or calibration.line_ridge_mask)(frame)
    h, w = mask.shape[:2]
    dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    lang = np.arctan2(gy, gx) + np.pi / 2.0        # line dir = perpendicular to gradient
    return dt, np.cos(2*lang), np.sin(2*lang), w, h, _detect_lines(mask, w)


EVID_BAND = 5.0     # "is there ANY paint near this line?" band, in units of tol
EVID_MIN = 0.20     # a line counts as measurable if this much of it has paint nearby


def _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr):
    """Returns (agreement, n_lines_supported, n_lines_with_evidence).

    EVIDENCE-BASED, not model-recall. A court is a regulation shape, so a line with
    no paint (worn clay, covered, repainted over) is MISSING EVIDENCE — not proof the
    fit is wrong. Scoring "what fraction of my lines did I find?" punishes a faded
    court for being faded. So:
      * a line with NO paint anywhere near it is UNMEASURABLE -> excluded entirely
      * among lines that DO have paint, we score how well the paint agrees
    A sample agrees if it sits on a line pixel (<=tol) AND the local ridge
    orientation matches the projected line. Absence of evidence is never a penalty;
    disagreeing evidence is."""
    S, lid, EA, EB = _court_samples(court)
    P = calibration.court_to_image(H, S)
    pa = calibration.court_to_image(H, EA)
    pb = calibration.court_to_image(H, EB)
    ang = np.arctan2(pb[:, 1]-pa[:, 1], pb[:, 0]-pa[:, 0])
    c2, s2 = np.cos(2*ang)[lid], np.sin(2*ang)[lid]
    x, y = np.round(P[:, 0]).astype(int), np.round(P[:, 1]).astype(int)
    inb = (x >= 0) & (x < w) & (y >= 0) & (y < h)
    if int(inb.sum()) < len(P) * 0.30:
        return 0.0, 0, 0
    xi, yi = np.clip(x, 0, w-1), np.clip(y, 0, h-1)
    align = cos2[yi, xi]*c2 + sin2[yi, xi]*s2
    d = dt[yi, xi]
    sup = inb & (d <= tol) & (align >= athr)      # paint here, and it agrees
    near = inb & (d <= tol * EVID_BAND)           # paint anywhere near -> measurable
    nL = int(lid.max()) + 1
    inb_cnt = np.bincount(lid, weights=inb.astype(float), minlength=nL)
    sup_cnt = np.bincount(lid, weights=sup.astype(float), minlength=nL)
    near_cnt = np.bincount(lid, weights=near.astype(float), minlength=nL)
    seen = inb_cnt >= 3                                   # line meaningfully in frame
    ev = seen & (near_cnt / np.maximum(inb_cnt, 1) >= EVID_MIN)   # paint exists here
    if not ev.any():
        return 0.0, 0, 0
    agree = float(sup_cnt[ev].sum()) / float(max(1.0, inb_cnt[ev].sum()))
    frac = np.where(seen, sup_cnt / np.maximum(inb_cnt, 1), 0.0)
    return agree, int((frac >= 0.5).sum()), int(ev.sum())


def _corners(cx, yn, yf, wn, wf):
    return {"near_bl_doubles": [cx-wn, yn], "near_br_doubles": [cx+wn, yn],
            "far_br_doubles": [cx+wf, yf], "far_bl_doubles": [cx-wf, yf]}


def court_centrality_ok(frame, H, calibration, min_centrality: float = 0.55):
    """Pose sanity for the clay path (verify_court is white-mask-blind there)."""
    return calibration.court_centrality(frame, H) >= min_centrality


# --- Structure: a court is 4 lines ACROSS and 4 lines LENGTHWISE, in a known order.
# Every one must land on its OWN real line. A shifted/wrong-rung court fails this:
# its baseline lands on the real SERVICE line, so two model lines fight over one
# real line and the outer ones match nothing. Pure line-support can't see that;
# distinct correspondence can.
STRUCT_LINES = [
    ((0, 0), (10.97, 0)),              # near baseline
    ((1.37, 5.485), (9.6, 5.485)),     # near service line
    ((1.37, 18.285), (9.6, 18.285)),   # far service line
    ((0, 23.77), (10.97, 23.77)),      # far baseline
    ((0, 0), (0, 23.77)),              # left doubles sideline
    ((1.37, 0), (1.37, 23.77)),        # left singles sideline
    ((9.6, 0), (9.6, 23.77)),          # right singles sideline
    ((10.97, 0), (10.97, 23.77)),      # right doubles sideline
]


def _norm_form(pa, pb):
    """Image line through 2 points -> canonical (theta_normal, rho)."""
    n = np.arctan2(pb[1]-pa[1], pb[0]-pa[0]) + np.pi/2.0
    rho = pa[0]*np.cos(n) + pa[1]*np.sin(n)
    if rho < 0:
        n, rho = n + np.pi, -rho
    return float(np.mod(n, np.pi)), float(rho)


def _structure(H, lines, calibration, dt, w, h, tol):
    """Do the court's structural lines each claim their OWN distinct real line?

    EVIDENCE-BASED (see _ori_detail): a structural line with no paint anywhere near
    it is UNMEASURABLE and is skipped — a worn clay line is missing evidence, not a
    wrong fit. Only lines that HAVE paint are judged, and each must match a distinct
    real line (greedy) — a shifted court that piles its baseline onto the real
    service line loses, because two of its lines fight over one real line.

    Returns (agreement, n_matched, n_measurable, n_across, n_lengthwise). The last
    two give the SUFFICIENCY test: 4 lines with >=2 in each direction is the
    geometric minimum that determines a homography."""
    if not lines:
        return 0.0, 0, 0, 0, 0
    used, matched, measurable = set(), 0, 0
    n_across = n_len = 0
    ang_tol, rho_tol = np.deg2rad(7), max(8.0, w * 0.018)
    ts = np.linspace(0.0, 1.0, 30)[:, None]
    for i, (a, b) in enumerate(STRUCT_LINES):
        pa = calibration.court_to_image(H, [a])[0]
        pb = calibration.court_to_image(H, [b])[0]
        mid = (pa + pb) / 2.0
        if not (-w*0.1 <= mid[0] <= w*1.1 and -h*0.1 <= mid[1] <= h*1.1):
            continue                      # not really in frame -> can't be judged
        pts = pa + ts * (pb - pa)         # the projected line is straight
        xs = np.round(pts[:, 0]).astype(int)
        ys = np.round(pts[:, 1]).astype(int)
        ok = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
        if ok.sum() < 5:
            continue
        painted = (dt[np.clip(ys, 0, h-1), np.clip(xs, 0, w-1)][ok]
                   <= tol * EVID_BAND).mean()
        if painted < EVID_MIN:
            continue                      # no paint here at all -> unmeasurable
        measurable += 1
        n, rho = _norm_form(pa, pb)
        best, bestd = None, 1e9
        for j, (ln, lr, _lw) in enumerate(lines):
            if j in used:
                continue
            dth = abs(np.mod(n - ln + np.pi/2, np.pi) - np.pi/2)
            drho = abs(rho - lr)
            if dth <= ang_tol and drho <= rho_tol and drho < bestd:
                best, bestd = j, drho
        if best is not None:
            used.add(best)
            matched += 1
            if i < 4:
                n_across += 1
            else:
                n_len += 1
    return ((matched / measurable if measurable else 0.0),
            matched, measurable, n_across, n_len)


# --- Camera-angle prior (tools/build_pose_prior.py) -------------------------
_PRIOR_PATH = REPO / "data" / "court_pose_prior.json"
_PRIOR = None
PRIOR_TEMP = 6.0        # softens the plausibility weight used for ranking
PRIOR_MAHA_MAX = 55.0   # reject camera poses this far outside the learned spread
PRIOR_SAMPLES = 500     # Monte-Carlo court seeds drawn from the learned prior
STRUCT_MIN = 0.55       # min fraction of court lines that must match their OWN real line


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


def _lowcam_seeds(calibration, court, court_pts, dt, cos2, sin2, w, h, tol, athr):
    """SYNTHETIC court-level seed mode — computed, not learned.

    The learned prior only knows elevated framings (what people upload), so a
    chest-height camera looks 'implausible' and never gets seeded. But a camera is
    just position+height+lens: project the court through phone-like poses at
    1.0-2.6m height, 1-7m behind the baseline, and we get exactly the trapezoids a
    court-level recording produces. Pure geometry — no training data needed."""
    import itertools
    out = []
    L, Wd = 23.77, 10.97
    for cam_h, back, f_px in itertools.product(
            (1.0, 1.6, 2.6), (1.0, 3.0, 7.0), (w*0.7, w*1.1)):
        # camera on the court's centreline, `back` metres behind the near baseline,
        # looking at the far half. Court frame: X across [0,10.97], Y depth.
        cx3, cy3 = Wd/2.0, -back
        look_y = L*0.45
        import numpy as _np
        fwd = _np.array([0.0, look_y-cy3, -cam_h]); fwd /= _np.linalg.norm(fwd)
        right = _np.array([1.0, 0.0, 0.0])
        up = _np.cross(fwd, right); up /= _np.linalg.norm(up)
        def proj(X, Y):
            p = _np.array([X-cx3, Y-cy3, 0.0-cam_h])
            z = p @ fwd
            if z <= 0.1:
                return None
            return (w/2.0 + f_px*(p@right)/z, h/2.0 - f_px*(p@up)/z)
        cs = [proj(*court.LANDMARKS[n]) for n in DBL]
        if any(c is None for c in cs):
            continue
        corners = dict(zip(DBL, [[c[0], c[1]] for c in cs]))
        # keep only poses where a useful part of the court is actually in frame
        xs = [c[0] for c in cs]; ys = [c[1] for c in cs]
        if max(ys) < h*0.5 or min(ys) > h*1.6 or max(xs)-min(xs) < w*0.5:
            continue
        try:
            H = calibration.compute_homography(court_pts, [corners[n] for n in DBL])
        except Exception:
            continue
        g, nl, _ = _ori_detail(H, calibration, court, dt, cos2, sin2, w, h, tol, athr)
        if g > 0:
            p = _params_from_corners(corners)
            out.append((g, g, nl, p, 0.0))    # rank by support; maha not applicable
    return out


def _cam_corners(p, w, h, court):
    """Project the 4 doubles corners through a PHYSICAL camera: position (Cx,Cy,Cz)
    in court metres, yaw, pitch (roll=0 — phones are mounted level), focal f_px.
    Returns {corner:[u,v]} or None if any corner is behind the camera."""
    Cx, Cy, Cz, yaw, pitch, f = p
    sy, cy_ = math.sin(yaw), math.cos(yaw)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd = np.array([sy*ct, cy_*ct, -st])
    right = np.array([cy_, -sy, 0.0])
    up = np.array([sy*st, cy_*st, ct])
    out = {}
    for n in DBL:
        X, Y = court.LANDMARKS[n]
        d = np.array([X-Cx, Y-Cy, -Cz])
        zc = d @ fwd
        if zc < 0.5:
            return None
        out[n] = [w/2.0 + f*(d@right)/zc, h/2.0 - f*(d@up)/zc]
    return out


def _cam_refine(frame, quad, calibration, court, dt, w, h):
    """Re-fit the snapped quad as a PHYSICAL CAMERA VIEW of a regulation court.

    The corner snap moves 4 corners independently (8 DOF) — it keeps the template
    rigid in court space but allows warps no real camera produces (skewed quads,
    tilted baselines), which is exactly the 'shape distortion' seen on weak-evidence
    courts. A real camera has ~6 DOF (position, pan, tilt, zoom; roll~0). Stage 1
    fits camera params to the quad; stage 2 polishes them on the line-distance map.
    Every candidate shape is then a legal view of a regulation court by
    construction. Returns (H, corners) or None."""
    from scipy.optimize import minimize
    target = np.array([quad[n] for n in DBL])
    f0 = None
    try:
        Hq = calibration.compute_homography([court.LANDMARKS[n] for n in DBL], target)
        f0 = calibration.focal_from_homography(Hq, (w, h))
    except Exception:
        pass
    x0 = np.array([court.DOUBLES_WIDTH/2.0, -6.0, 4.0, 0.0, 0.25,
                   float(f0) if f0 else w*0.9])

    def cost_quad(p):
        c = _cam_corners(p, w, h, court)
        if c is None:
            return 1e6
        return float(np.mean(np.hypot(*(np.array([c[n] for n in DBL]) - target).T)))

    r1 = minimize(cost_quad, x0, method="Nelder-Mead",
                  options={"maxiter": 1200, "xatol": 1e-3, "fatol": 1e-3})
    if not np.isfinite(r1.fun) or r1.fun > 40.0:
        return None                       # quad too non-physical to be a camera view
    S = _court_samples(court)[0]

    def cost_dt(p):
        c = _cam_corners(p, w, h, court)
        if c is None:
            return 1e6
        try:
            H = calibration.compute_homography(
                [court.LANDMARKS[n] for n in DBL], [c[n] for n in DBL])
        except Exception:
            return 1e6
        P = calibration.court_to_image(H, S)
        xs = np.clip(P[:, 0], 0, w-1).astype(int)
        ys = np.clip(P[:, 1], 0, h-1).astype(int)
        inb = (P[:, 0] >= 0) & (P[:, 0] < w) & (P[:, 1] >= 0) & (P[:, 1] < h)
        if inb.sum() < len(P)*0.3:
            return 1e6
        return float(dt[ys[inb], xs[inb]].mean())

    r2 = minimize(cost_dt, r1.x, method="Nelder-Mead",
                  options={"maxiter": 600, "xatol": 1e-3, "fatol": 1e-3})
    # TETHERED polish (same fix as cam_fit_quad): dt sinks far from the court
    # (banner/fence rows) can drag the polish into a collapsed sliver. A polish
    # that moves the corners >30px mean is no longer polishing - discard it.
    use_x = r1.x
    if np.isfinite(r2.fun) and r2.fun < cost_dt(r1.x):
        c1 = _cam_corners(r1.x, w, h, court)
        c2 = _cam_corners(r2.x, w, h, court)
        if c1 is not None and c2 is not None and float(np.mean(
                [math.hypot(c2[n][0]-c1[n][0], c2[n][1]-c1[n][1])
                 for n in DBL])) <= 30.0:
            use_x = r2.x
    c = _cam_corners(use_x, w, h, court)
    if c is None:
        return None
    try:
        H = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [c[n] for n in DBL])
    except Exception:
        return None
    return H, {n: [float(c[n][0]), float(c[n][1])] for n in DBL}


def _seed_from_quad(target, court):
    """Closed-form camera guess from the quad's own geometry (assumes a roughly
    centre-line camera behind the near baseline). Distance from the near/far
    width ratio, focal from the pinhole relation, height from the vertical
    extent — good enough to seed Nelder-Mead for ANYTHING from a phone at the
    fence to a broadcast telephoto (measured: a ~4400px-focal TV view that all
    fixed seeds missed by 88px fits <2px from this seed)."""
    nbl, nbr, fbr, fbl = target
    wn = float(np.hypot(*(nbr - nbl)))
    wf = float(np.hypot(*(fbr - fbl)))
    if wf <= 1.0 or wn <= wf:
        return None
    Wd = court.DOUBLES_WIDTH
    L = float(court.LANDMARKS["far_bl_doubles"][1])
    r = wf / wn
    Dn = r * L / (1.0 - r)                    # camera -> near baseline (ground)
    if not (1.0 <= Dn <= 200.0):
        return None
    f = wn * Dn / Wd
    dy = max((nbl[1] + nbr[1]) / 2.0 - (fbl[1] + fbr[1]) / 2.0, 1.0)
    Cz = dy / (f * (1.0 / Dn - 1.0 / (Dn + L)))
    Cz = float(np.clip(Cz, 0.5, 60.0))
    pitch = math.atan2(Cz, Dn + L / 2.0)
    return np.array([Wd / 2.0, -Dn, Cz, 0.0, pitch, f])


def cam_fit_quad(quad, calibration, court, w, h, dt=None):
    """Lock an ARBITRARY 4-corner court placement onto the closest physical
    camera view of a regulation court (position, pan, tilt, zoom; roll=0).

    Manual-path counterpart of _cam_refine: the overlay tool lets a human drag
    corners freely (8 DOF), which can produce shapes no real camera ever sees.
    This projects that quad onto the 6-DOF camera manifold, so the result is
    ALWAYS a legal view of a regulation court, as close as possible to where the
    user put it. Unlike _cam_refine it never refuses a fittable quad (a hand
    placement must resolve to the nearest legal shape, not be rejected), and it
    multi-starts because hand placements can be far from the elevated-TV pose
    _cam_refine's single seed assumes. _cam_refine is deliberately left alone:
    the detector's gate behaviour is measurement-frozen (scorecards in git).

    dt: optional line-distance map; when given, a second stage polishes the
    camera onto the paint (use for Snap, omit for a pure shape lock on Save).

    Returns (H, corners, fit_px, cam_params) or None. fit_px = mean px between
    the input quad and the nearest physical view: ~0 when the input was already
    a real camera shape, large when it was impossible and got corrected.
    cam_params = (Cx, Cy, Cz, yaw, pitch, focal_px) - the actual camera; the
    focal is the honest lens zoom (feeds speed physics downstream)."""
    from scipy.optimize import minimize
    target = np.array([quad[n] for n in DBL], float)

    f0 = None
    try:
        Hq = calibration.compute_homography([court.LANDMARKS[n] for n in DBL], target)
        f0 = calibration.focal_from_homography(Hq, (w, h))
    except Exception:
        pass
    f_guess = float(f0) if f0 else w * 0.9
    Wd = court.DOUBLES_WIDTH
    starts = [
        np.array([Wd/2.0, -6.0, 4.0, 0.0, 0.25, f_guess]),   # elevated behind baseline
        np.array([Wd/2.0, -3.0, 1.6, 0.0, 0.10, f_guess]),   # court-level phone
        np.array([Wd/2.0, -12.0, 8.0, 0.0, 0.35, f_guess]),  # high stands
        np.array([Wd/2.0, -6.0, 4.0, 0.0, 0.25, w*1.4]),     # long lens
    ]
    seed = _seed_from_quad(target, court)
    if seed is not None:
        starts.insert(0, seed)   # data-driven guess first (covers broadcast poses)

    def cost_quad(p):
        c = _cam_corners(p, w, h, court)
        if c is None:
            return 1e6
        return float(np.mean(np.hypot(*(np.array([c[n] for n in DBL]) - target).T)))

    best = None
    for x0 in starts:
        r = minimize(cost_quad, x0, method="Nelder-Mead",
                     options={"maxiter": 1200, "xatol": 1e-3, "fatol": 1e-3})
        if np.isfinite(r.fun) and r.fun < 1e5 and (best is None or r.fun < best.fun):
            best = r
    if best is None:
        return None
    # one restart from the winner: Nelder-Mead's simplex collapses on long-lens
    # poses before converging; a fresh simplex there finishes the job cheaply
    r = minimize(cost_quad, best.x, method="Nelder-Mead",
                 options={"maxiter": 1200, "xatol": 1e-3, "fatol": 1e-3})
    if np.isfinite(r.fun) and r.fun < best.fun:
        best = r
    fit_px, px = float(best.fun), best.x

    if dt is not None:
        S = _court_samples(court)[0]

        def cost_dt(p):
            c = _cam_corners(p, w, h, court)
            if c is None:
                return 1e6
            try:
                H = calibration.compute_homography(
                    [court.LANDMARKS[n] for n in DBL], [c[n] for n in DBL])
            except Exception:
                return 1e6
            P = calibration.court_to_image(H, S)
            xs = np.clip(P[:, 0], 0, w-1).astype(int)
            ys = np.clip(P[:, 1], 0, h-1).astype(int)
            inb = (P[:, 0] >= 0) & (P[:, 0] < w) & (P[:, 1] >= 0) & (P[:, 1] < h)
            if inb.sum() < len(P)*0.3:
                return 1e6
            return float(dt[ys[inb], xs[inb]].mean())

        r2 = minimize(cost_dt, px, method="Nelder-Mead",
                      options={"maxiter": 600, "xatol": 1e-3, "fatol": 1e-3})
        # TETHERED polish: the dt map has sinks far from the court (banner and
        # fence edge rows) - an unbounded polish can walk the camera to one and
        # collapse the court to a sliver (seen live). Keep the polish only if
        # it stays a POLISH: corners move <=30px mean from the stage-1 shape.
        if np.isfinite(r2.fun) and r2.fun < cost_dt(px):
            c1 = _cam_corners(px, w, h, court)
            c2 = _cam_corners(r2.x, w, h, court)
            if c1 is not None and c2 is not None:
                drift = float(np.mean([math.hypot(c2[n][0]-c1[n][0],
                                                  c2[n][1]-c1[n][1]) for n in DBL]))
                if drift <= 30.0:
                    px = r2.x

    c = _cam_corners(px, w, h, court)
    if c is None:
        return None
    try:
        H = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [c[n] for n in DBL])
    except Exception:
        return None
    return (H, {n: [float(c[n][0]), float(c[n][1])] for n in DBL}, fit_px,
            tuple(float(v) for v in px))


def autodetect(frame, calibration, court, *, grid=4, topk=12,
               athr=0.80, accept=0.33, use_prior=True, mask_fn=None, _fallback=True):
    """Prior-sampled + grid seeds -> local refine -> snap -> structural+plausibility
    gate. Returns (H, score, corners) or None (falls back to manual).

    If the default "white lines" mask yields nothing acceptable, retries ONCE with a
    hue-agnostic mask (clay/shell). Only safe because the verifier is STRUCTURAL: a
    court must claim 4 distinct real lines at regulation spacing with a plausible
    camera pose, so the extra noise a permissive mask lets in is rejected on
    geometry, not on colour."""
    mf = mask_fn or calibration.line_ridge_mask
    dt, cos2, sin2, w, h, lines = _precompute(frame, calibration, mf)
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
    ranked += _lowcam_seeds(calibration, court, court_pts,
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
                frame, _corners(*p), max_move_px=55.0, mask_fn=mf)
        except Exception:
            continue
        # DEGENERACY FLOOR (the "not even remotely a court" rule applied to
        # SCALE): near a frame's horizon, banner/fence edges can satisfy the
        # structural gates because every court line collapses into the same
        # horizontal band (seen live: a 70x3px "court" on the fence banners).
        # A usable recording shows the court at size - floor the apparent
        # near-baseline width and depth.
        p5 = _params_from_corners(ref)
        if p5[3] * 2.0 < 0.15 * w or abs(p5[1] - p5[2]) < 0.06 * h:
            continue
        g, nl, n_ev = _ori_detail(Hs, calibration, court, dt, cos2, sin2, w, h, tol, athr)
        maha = _maha(p5, w, h, prior)
        st, st_m, st_ev, n_across, n_len = _structure(Hs, lines, calibration, dt, w, h, tol)
        # Accept gate, evidence-based. We never punish a line for having no paint —
        # a regulation court's lines exist whether or not the surface still shows
        # them. We require instead:
        #   SUFFICIENCY  enough VISIBLE lines to actually determine the shape:
        #                4 matched with >=2 in each direction (the geometric minimum
        #                for a homography). This replaces "found most of my lines".
        #   AGREEMENT    where paint IS visible, it agrees (g, st)
        #   PLAUSIBILITY a sane camera pose (prior) + coverage/centrality check
        sufficient = (st_m >= 4 and n_across >= 2 and n_len >= 2) or nl >= 5
        if mask_fn is not None:
            # STRUCTURE-PRIMARY clay path (user's principle: once lines are matched
            # as court lines, regulation spacing determines everything). On clay the
            # per-pixel agreement g and the white-mask verify_court are BLIND — but
            # the true court still claims 6+ distinct straight lines at regulation
            # spacing, which speckle can't fake. Judged by structure + pose only, so
            # the bar is HIGHER than the white path (measured: the true clay court
            # matches 6 lines at 0.86 agreement; hallucinations on no-court frames
            # scrape 4 — requiring 5+ at 0.70 separates them).
            rankv = st
            ok = (sufficient and st_m >= 5 and st >= 0.70
                  and n_across >= 2 and n_len >= 2
                  and maha <= PRIOR_MAHA_MAX
                  and court_centrality_ok(frame, Hs, calibration))
        else:
            ok_struct = st >= STRUCT_MIN or st_ev < 3   # can't judge with <3 measurable
            rankv = g * (0.5 + 0.5 * st)
            # The learned prior only knows elevated framings. A COURT-LEVEL camera
            # fails the maha test through no fault of its own, so a pose outside
            # the prior is allowed IF the court structure is unambiguous (5+ lines
            # each on their own real line, both directions) — prior breaks ties,
            # overwhelming structure overrides it.
            pose_ok = (maha <= PRIOR_MAHA_MAX
                       or (st >= 0.70 and st_m >= 5 and n_across >= 2 and n_len >= 2))
            ok = (g >= accept and sufficient and pose_ok and ok_struct
                  and calibration.verify_court(frame, Hs).ok)
        if ok and (best is None or rankv > best[1]):
            best = (Hs, rankv, ref)
    if best is not None:
        # HARD RULE: the output must be a real camera's view of a regulation court.
        # Re-fit the winner as camera pose+zoom (roll~0); if NO physical camera can
        # produce this quad (stage-1 residual > 40px), REFUSE rather than ship a
        # shape that isn't remotely a tennis court. No free-quad fallback.
        cam = _cam_refine(frame, best[2], calibration, court, dt, w, h)
        best = (cam[0], best[1], cam[1]) if cam is not None else None
    if best is None and _fallback and mask_fn is None:
        # nothing with the "white lines" mask -> the surface may be clay/shell.
        # Retry hue-agnostic; the structure verifier keeps this honest.
        return autodetect(frame, calibration, court, grid=grid, topk=topk, athr=athr,
                          accept=accept, use_prior=use_prior,
                          mask_fn=lambda f: _clay_mask(f, calibration), _fallback=False)
    return best


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


def stacked_clay_fit(imgs, calibration, court):
    """Clay/shell rescue: STACK line evidence across frames, then fit ONCE.

    Per-frame clay fits wobble because each frame's Hough pass recovers a different
    subset of the broken orange lines. But the court is static and its lines are
    straight, so accumulating the cleaned masks across frames makes the true lines
    reinforce while players/shadows/per-frame noise wash out. Fit on a synthetic
    frame whose 'paint' is the pixels seen as line in >=30% of frames."""
    import cv2

    acc = None
    for _k, im in imgs:
        m = (_clay_mask(im, calibration) > 0).astype(np.float32)
        acc = m if acc is None else acc + m
    if acc is None:
        return None
    stable = ((acc / len(imgs)) >= 0.30).astype(np.uint8) * 255
    if int(stable.sum() // 255) < 200:
        return None
    synth = np.zeros((*stable.shape, 3), np.uint8)
    synth[stable > 0] = 255                       # white paint on black
    res = autodetect(synth, calibration, court,
                        mask_fn=lambda f: cv2.cvtColor(f, cv2.COLOR_BGR2GRAY),
                        _fallback=False)
    return None if res is None else res[2]


def snap_court(frame, named, calibration, court, *,
               min_coverage=0.40, max_move_px=30.0):
    """Guarded corner snap with a CLAY retry.

    White/ridge lines first (the measured default). When that path REFUSES —
    worn or colour-tinted paint has no white signal, exactly the case where a
    stack-fit court sits ~15px off its faintest sideline — retry with the
    hue-agnostic clay mask, judged under the SAME mask it refined with (the
    guard still demands coverage >= min_coverage and no decrease). The snap
    stays bounded (+-max_move_px), so the worst it can do is tighten onto
    nearby clay texture; callers re-lock the shape afterwards regardless.

    Returns (H, named_out, snapped, tag, coverage) — tag "snap", "snap-clay",
    or None when both paths refused (named_out is then the input)."""
    H, out, snapped, _c0, c1 = calibration.snap_to_lines(
        frame, named, min_coverage=min_coverage, max_move_px=max_move_px)
    if snapped:
        return H, out, True, "snap", c1
    H2, out2, snapped2, _c0, c2 = calibration.snap_to_lines(
        frame, named, min_coverage=min_coverage, max_move_px=max_move_px,
        mask_fn=lambda f: _clay_mask(f, calibration))
    if snapped2:
        return H2, out2, True, "snap-clay", c2
    return H, named, False, None, c1


def auto_fit_frame(frame, calibration, court):
    """The full single-frame recipe: line-fit autodetect -> guarded corner snap
    -> physical shape re-lock. Returns {corner:[x,y]} or None (no lock)."""
    res = autodetect(frame, calibration, court)
    if res is None:
        return None
    ref = res[2]
    named = {k: [float(ref[k][0]), float(ref[k][1])] for k in DBL}
    _, out, _snapped, _c0, _c1 = calibration.snap_to_lines(
        frame, named, min_coverage=0.0, max_move_px=60.0)
    use = out if all(k in out for k in DBL) else named
    # the free corner-snap can undo the physical gate; re-lock to a camera view
    h, w = frame.shape[:2]
    dt = _precompute(frame, calibration)[0]
    r = cam_fit_quad(use, calibration, court, w, h, dt=dt)
    return r[1] if r is not None else use


def fit_video_frames(frames, calibration, court):
    """Consensus auto-calibration over sampled frames of ONE clip.

    Fits each frame independently, keeps the largest agreeing group (the court is
    static; wrong-rung locks don't reproduce), falls back to the clay/shell
    evidence stack when nothing agrees. Returns (corners, votes, tag):
      tag "vote"  - corners = per-corner median of `votes` agreeing frames
      tag "stack" - clay rescue fit (single fit on stacked line evidence)
      (None, votes, None) - refused; votes = best agreement seen."""
    fits = [auto_fit_frame(f, calibration, court) for f in frames]
    pts, votes = consensus(fits)
    if pts is not None:
        return pts, votes, "vote"
    if len(frames) >= 6:
        pts = stacked_clay_fit(list(enumerate(frames)), calibration, court)
        if pts is not None:
            return pts, 1, "stack"
    return None, votes, None
