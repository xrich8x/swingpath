"""eval/corr_ls_fit.py - least squares over ALL matched line correspondences, against
the exact 4-point fit, GIVEN THE TRUE line-to-model assignment.

Executes the lead's pre-registration of 2026-09-04. `eval/corr_attrib.py` established
that where the true correspondence survives every screen, the reconstruction is a
median 17.1 px@640 from the human court, because the homography is solved from exactly
FOUR line intersections and each line's few-px error is amplified where the court is
most foreshortened. This asks whether using EVERY matched line's evidence moves that.

ONE VARIABLE: the fit. Same clips, same frames, same detected lines, same true
assignment, same screens. Only how the homography is computed changes.

THE CONTROL GATES EVERYTHING. The exact-4-point median is recomputed here in the same
run and must reproduce ~17.1 px (and the per-clip values in data/output/corr_attrib.json).
If it does not, this harness is not measuring what that row measured and nothing else
in the run is trustworthy.

TWO LEAST-SQUARES VARIANTS, both reported:
  LS-DLT   dual (line-correspondence) DLT. Each matched line contributes its two world
           endpoints, each of which must image ONTO that line: l^T H p = 0. Hartley
           conditioning on both sides, null vector by SVD. Algebraic residual.
  LS-geom  LS-DLT as initialisation, then nonlinear least squares on the TRUE geometric
           point-to-line distance (l^T H p) / (H p)_3. This removes the DLT's implicit
           depth weighting - which is the foreshortening the 17.1 px row blames.

    backend/.venv/Scripts/python.exe eval/corr_ls_fit.py --json data/output/corr_ls_fit.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

from swingvision.courtfit import DBL  # noqa: E402
from pencils import find_pencils, _homog  # noqa: E402
from correspondence import _meet, _quad_ok, _quad_convex, X_POS, Y_POS, TAU, N_PENCILS  # noqa: E402
from corr_attrib import LENGTHWISE, ACROSS, _match_line, EXCLUDE_TRUTH  # noqa: E402


# ----------------------------------------------------------------- the LS fits
#
# THE OBJECTIVE, AND WHY IT RUNS MODEL -> IMAGE AND NOT THE OTHER WAY.
#
# The obvious point-on-line residual - take the world endpoints of each court line and
# ask how far their images sit from the detected line - is BROKEN on this footage, and
# measurably so: on `hillsborough_p02` its rms under the HUMAN homography is 204 px@640.
# A low mount puts the far baseline at or beyond the vanishing line, so a world endpoint
# projects with a near-zero (or sign-flipped) depth and the distance explodes. An
# objective that the TRUE answer does not minimise cannot test anything, so it is not
# used. Recorded because it is the exact trap the 17.1 px row is about.
#
# The direction that is always finite is the other one: project the MODEL line into the
# image as l_i = H^-T l_w (a linear map of a line, no division by depth), and measure the
# distance from points that lie ON THE DETECTED LINE. Those points are real image points,
# they are inside the frame by construction, and they sample the line only where it was
# actually seen. This is still a point-on-line least squares over every matched line -
# it is just posed on the side where the geometry is well conditioned.

def _line_of_model(kind, coord):
    """Homogeneous world line: lengthwise x = coord, or across y = coord."""
    return (np.array([1.0, 0.0, -coord]) if kind == "x"
            else np.array([0.0, 1.0, -coord]))


def _frame_samples(l, w, h, n=5):
    """n points on the detected image line, spread across its span INSIDE the frame."""
    a, b, c = float(l[0]), float(l[1]), float(l[2])
    pts = []
    if abs(b) > 1e-9:
        for x in (0.0, float(w)):
            y = -(a * x + c) / b
            if -1e-6 <= y <= h + 1e-6:
                pts.append((x, y))
    if abs(a) > 1e-9:
        for y in (0.0, float(h)):
            x = -(b * y + c) / a
            if -1e-6 <= x <= w + 1e-6:
                pts.append((x, y))
    if len(pts) < 2:
        return []
    P = np.asarray(pts, float)
    t = P @ np.array([-b, a])
    A, B = P[int(np.argmin(t))], P[int(np.argmax(t))]
    if np.hypot(*(B - A)) < 1.0:
        return []
    return [np.array([q[0], q[1], 1.0]) for q in (A + (B - A) * s
                                                  for s in np.linspace(0, 1, n))]


def _corr_rows(fl, fa, L, w, h):
    """[(world_line, [image points on the detected line])] over EVERY matched line."""
    out = []
    for coord, k in fl:
        sm = _frame_samples(L[k], w, h)
        if sm:
            out.append((_line_of_model("x", coord), sm))
    for coord, k in fa:
        sm = _frame_samples(L[k], w, h)
        if sm:
            out.append((_line_of_model("y", coord), sm))
    return out


def _geom_resid(H, rows):
    """Point-to-projected-line distance in pixels, one entry per sample point."""
    try:
        Hit = np.linalg.inv(H).T
    except np.linalg.LinAlgError:
        return np.full(sum(len(s) for _l, s in rows), 1e6)
    out = []
    for lw, sm in rows:
        li = Hit @ lw
        nrm = float(np.hypot(li[0], li[1]))
        if nrm < 1e-12 or not np.isfinite(nrm):
            out.extend([1e6] * len(sm))
            continue
        li = li / nrm
        for q in sm:
            out.append(float(li @ q))
    return np.asarray(out, float)


def _world_norm(scale_m=12.0):
    s = 1.0 / scale_m
    return np.array([[s, 0, -s * 5.485], [0, s, -s * 11.885], [0, 0, 1.0]])


def _img_norm(w, h):
    f = max(w, h) / 2.0
    return np.array([[1.0 / f, 0, -w / (2.0 * f)],
                     [0, 1.0 / f, -h / (2.0 * f)], [0, 0, 1.0]])


def _skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]], float)


def ls_dlt(fl, fa, L, w, h):
    """Dual (line-correspondence) DLT, init-free. l_w ~ H^T l_i for every matched line.

    Two independent linear equations per line from the cross product, conditioned on
    both sides. This is the closed-form least-squares fit over ALL matched lines."""
    S = _world_norm()
    T = _img_norm(w, h)
    Si, Ti = np.linalg.inv(S), np.linalg.inv(T)
    pairs = ([(_line_of_model("x", c), L[k]) for c, k in fl]
             + [(_line_of_model("y", c), L[k]) for c, k in fa])
    if len(pairs) < 4:
        return None
    A = []
    for lw, li in pairs:
        lwn = Si.T @ lw                       # world line in conditioned world coords
        lin = Ti.T @ li                       # image line in conditioned image coords
        lwn = lwn / max(np.linalg.norm(lwn), 1e-12)
        lin = lin / max(np.linalg.norm(lin), 1e-12)
        # (H'^T l_i')_j = sum_i H'_ij l_i'  ->  M x, with x = vec(H') row-major
        M = np.zeros((3, 9))
        for i in range(3):
            for j in range(3):
                M[j, i * 3 + j] = lin[i]
        E = _skew(lwn) @ M
        A.append(E[0])
        A.append(E[1])
    try:
        _u, _s, vt = np.linalg.svd(np.asarray(A, float))
    except np.linalg.LinAlgError:
        return None
    Hn = vt[-1].reshape(3, 3)
    H = Ti @ Hn @ S
    if not np.isfinite(H).all() or abs(H[2, 2]) < 1e-12:
        return None
    return H / H[2, 2]


def ls_geom(rows, inits):
    """Nonlinear least squares on the point-on-line distances, over all matched lines.

    Started from every init offered (the dual DLT and the exact 4-point fit) and the run
    with the LOWEST OBJECTIVE is kept - objective only, never truth, so no leak."""
    try:
        from scipy.optimize import least_squares
    except Exception:
        return None
    best, bcost = None, np.inf
    for H0 in inits:
        if H0 is None or not np.isfinite(H0).all():
            continue
        x0 = H0.ravel() / np.linalg.norm(H0.ravel())
        try:
            r = least_squares(lambda x: _geom_resid(x.reshape(3, 3), rows), x0,
                              method="trf", max_nfev=6000, xtol=1e-14, ftol=1e-14)
        except Exception:
            continue
        H = r.x.reshape(3, 3)
        if not np.isfinite(H).all() or abs(H[2, 2]) < 1e-12:
            continue
        if r.cost < bcost:
            best, bcost = H / H[2, 2], float(r.cost)
    return best


# ----------------------------------------------------------------- the harness

def run_clip(im, named, calibration, court, cf):
    """Both fits from the identical true assignment. Mirrors corr_attrib.trace for
    the exact-4-point arm; the per-clip `err_exact` is the control."""
    dt, cos2, sin2, w, h, lines = cf._precompute(
        im, calibration, calibration.court_line_mask)
    tol = max(2.0, w * 0.006)
    scale = 640.0 / w
    out = {"n_lines": len(lines), "died": None, "w": int(w), "h": int(h)}
    if len(lines) < 4:
        out["died"] = "pencil supply"
        return out

    H_true = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])

    def found(fam):
        got = []
        for coord, p0, p1 in fam:
            pa = calibration.court_to_image(H_true, [p0])[0]
            pb = calibration.court_to_image(H_true, [p1])[0]
            n0, r0 = cf._norm_form(pa, pb)
            k = _match_line(n0, r0, lines, scale)
            if k is not None:
                got.append((coord, k))
        return got

    fl, fa = found(LENGTHWISE), found(ACROSS)
    out["n_len"], out["n_acr"] = len(fl), len(fa)
    # a detected line claimed by two different model lines is a fidelity limit of the
    # TRUE assignment itself, not of either fit. Recorded, never repaired.
    out["dup_len"] = len(fl) - len({k for _c, k in fl})
    out["dup_acr"] = len(fa) - len({k for _c, k in fa})
    if len(fl) < 2 or len(fa) < 2:
        out["died"] = "pencil supply"
        return out

    pens = find_pencils(lines, max_pencils=N_PENCILS, tau=TAU)
    out["n_pen"] = len(pens)
    if len(pens) < 2:
        out["died"] = "two pencils"
        return out
    pl = [p for p, (_v, idx) in enumerate(pens)
          if len({k for _c, k in fl} & set(idx)) >= 2]
    pa_ = [p for p, (_v, idx) in enumerate(pens)
           if len({k for _c, k in fa} & set(idx)) >= 2]
    out["sep"] = bool(pl and pa_ and set(pl) != set(pa_))
    if not out["sep"]:
        out["died"] = "two pencils"
        return out

    L = _homog(lines)
    txy = np.array([named[n] for n in DBL], float)

    def corner_err(H):
        try:
            c = np.array([calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                          for n in DBL], float)
        except Exception:
            return None, None
        if not np.isfinite(c).all():
            return None, c
        return float(np.mean(np.hypot(*(c - txy).T))) * scale, c

    # ---- ARM A: the exact 4-point fit, byte-for-byte the corr_attrib construction
    (xa, la), (xb, lb) = fl[0], fl[-1]
    (yc, lc), (yd, ld) = fa[0], fa[-1]
    P4 = [_meet(L[la], L[lc]), _meet(L[la], L[ld]),
          _meet(L[lb], L[ld]), _meet(L[lb], L[lc])]
    if any(p is None for p in P4):
        out["died"] = "no intersection"
        return out
    if not _quad_convex(P4):
        out["died"] = "not convex"
        return out
    try:
        H4 = calibration.compute_homography([(xa, yc), (xa, yd), (xb, yd), (xb, yc)], P4)
    except Exception:
        out["died"] = "homography failed"
        return out
    e4, c4 = corner_err(H4)
    out["err_exact"] = e4
    if c4 is None or not np.isfinite(c4).all() or not _quad_ok(c4, w, h):
        out["died"] = "corner screen"
        return out

    prior = cf._load_prior()
    p5 = cf._params_from_corners({n: c4[i] for i, n in enumerate(DBL)})
    maha = cf._maha(p5, w, h, prior)
    g, _nl, _ev = cf._ori_detail(H4, calibration, court, dt, cos2, sin2, w, h, tol, 0.80)
    st, st_m, _se, n_ac, n_ln = cf._structure(H4, lines, calibration, dt, w, h, tol)
    out.update({"maha": float(maha), "g": float(g), "st": float(st)})
    if not (maha <= cf.PRIOR_MAHA_MAX
            or (st >= 0.70 and st_m >= 5 and n_ac >= 2 and n_ln >= 2)):
        out["died"] = "pose"
        return out
    if g <= 0:
        out["died"] = "g>0"
        return out
    try:
        if not calibration.verify_court(im, H4).ok:
            out["died"] = "verify"
            return out
    except Exception:
        out["died"] = "verify"
        return out
    if cf._cam_refine(im, {n: [float(c4[i][0]), float(c4[i][1])] for i, n in enumerate(DBL)},
                      calibration, court, dt, w, h) is None:
        out["died"] = "camera re-fit"
        return out

    # ---- ARM B: least squares over EVERY matched line, same assignment
    rows = _corr_rows(fl, fa, L, w, h)
    out["n_corr"] = len(rows)
    Hd = ls_dlt(fl, fa, L, w, h)
    Hg = ls_geom(rows, [Hd, H4])
    out["err_lsdlt"], _cd = corner_err(Hd) if Hd is not None else (None, None)
    out["err_lsgeom"], _cg = corner_err(Hg) if Hg is not None else (None, None)

    # the objective each fit actually optimises, so we can tell a FIT ceiling from a
    # LINE-EVIDENCE ceiling: rms geometric point-to-line distance over ALL matched
    # lines, in px@640, for each H - including the HUMAN homography.
    def rms(H):
        if H is None:
            return None
        r = _geom_resid(H, rows)
        return float(np.sqrt(np.mean(np.square(r)))) * scale

    out["rms_exact"] = rms(H4)
    out["rms_lsdlt"] = rms(Hd)
    out["rms_lsgeom"] = rms(Hg)
    out["rms_truth"] = rms(H_true)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=1)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips. ONE VARIABLE: the fit. Same clips, same true assignment.\n")
    print(f"{'clip':22s} {'len/acr':>8s} {'exact':>7s} {'lsdlt':>7s} {'lsgeom':>7s} "
          f"{'rmsE':>6s} {'rmsG':>6s} {'rmsT':>6s}  died")
    print("-" * 96)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            r = run_clip(im, named, calibration, court, cf)
            r.update({"clip": clip, "src": src, "shell": im.shape[1] >= 3000,
                      "excluded": clip in EXCLUDE_TRUTH})
            rows.append(r)
            f = lambda k, p=".1f": ("-" if r.get(k) is None else f"{r[k]:{p}}")  # noqa: E731
            print(f"{clip:22s} {r.get('n_len', 0):3d}/{r.get('n_acr', 0):<4d} "
                  f"{f('err_exact'):>7s} {f('err_lsdlt'):>7s} {f('err_lsgeom'):>7s} "
                  f"{f('rms_exact'):>6s} {f('rms_lsgeom'):>6s} {f('rms_truth'):>6s}  "
                  f"{r['died'] or 'SURVIVED'}", flush=True)
            break

    print("-" * 96)
    live = [r for r in rows if not r["excluded"]]
    surv = [r for r in live if r["died"] is None and r.get("err_exact") is not None]
    print(f"{len(rows)} clips in {time.time()-t0:.0f}s; survivors n={len(surv)}\n")
    med = lambda k, pop: (float(np.median([x[k] for x in pop if x.get(k) is not None]))  # noqa: E731
                          if any(x.get(k) is not None for x in pop) else None)
    print("POOLED MEDIAN px@640 over the survivor set (the population 17.1 px was on):")
    for k, lab in (("err_exact", "CONTROL exact 4-point"),
                   ("err_lsdlt", "LS-DLT (all lines)"),
                   ("err_lsgeom", "LS-geom (all lines)")):
        v = med(k, surv)
        print(f"    {lab:24s} {'-' if v is None else f'{v:.2f}'}")
    print("\nand the line-fit objective each one optimises (rms px@640):")
    for k in ("rms_exact", "rms_lsdlt", "rms_lsgeom", "rms_truth"):
        v = med(k, surv)
        print(f"    {k:24s} {'-' if v is None else f'{v:.2f}'}")
    for lab, pop in (("TUNE", [r for r in surv if not r["shell"]]),
                     ("SHELL", [r for r in surv if r["shell"]])):
        if pop:
            print(f"\n{lab} n={len(pop)}: exact {med('err_exact', pop):.2f}  "
                  f"lsdlt {med('err_lsdlt', pop):.2f}  lsgeom {med('err_lsgeom', pop):.2f}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
