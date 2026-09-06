"""eval/near_line_precision.py - the falsifier for the near-baseline + net solve.

Measures, against HUMAN-CLICKED corners only, the detected-vs-truth error of the FOUR
observables the `net-baseline-solve-without-far-line` geometry consumes:

    (a) near baseline ROW      (b) net line ROW
    (c) near baseline WIDTH    (d) court WIDTH at the net

then feeds the DETECTED four into the solver and reports where the EXTRAPOLATED FAR
BASELINE lands against the human far baseline. Protocol + pre-registered bar:
docs/evidence/near-line-detection-precision.md.

Units are px@640 throughout. Detector is the shipped one, unchanged
(`calibration.court_line_mask` -> `courtfit._detect_lines`). Matching is TRUTH-SEEDED
(`corr_attrib._match_line`, ang 6 deg): this measures LOCALISATION, not search.

    backend/.venv/Scripts/python.exe eval/near_line_precision.py --out data/output/near_line_precision.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

from swingvision import calibration, court  # noqa: E402
from swingvision import courtfit as cf  # noqa: E402
from swingvision.courtfit import DBL  # noqa: E402

W_M = court.DOUBLES_WIDTH        # 10.97
NET_Y = court.NET_Y              # 11.885
LEN_M = court.LENGTH             # 23.77

MODEL = {
    "near_baseline": ((0.0, 0.0), (W_M, 0.0)),
    "net_ground":    ((0.0, NET_Y), (W_M, NET_Y)),
    "left_side":     ((0.0, 0.0), (0.0, LEN_M)),
    "right_side":    ((W_M, 0.0), (W_M, LEN_M)),
    "far_baseline":  ((0.0, LEN_M), (W_M, LEN_M)),
}


def _match_rho(n0, r0, lines, scale, ang_deg=6.0, rho640=8.0):
    """corr_attrib's SHIPPED rule, copied. Gates on |rho| from the image ORIGIN.

    Kept for comparison only: it is a weak gate for long oblique lines, because a
    6 deg angle difference about a point near the origin moves the line by
    ~sin(6 deg) * (distance along it) at the far end while barely moving rho. Measured
    2026-09-06: it accepts right-sideline matches sitting 150-320 px@640 off the truth
    segment. See docs/evidence/near-line-detection-precision.md."""
    best, bd = None, 1e18
    for k, (ln, lr, _lw) in enumerate(lines):
        dth = abs(np.mod(n0 - ln + np.pi / 2, np.pi) - np.pi / 2)
        if dth <= np.deg2rad(ang_deg) and abs(r0 - lr) * scale <= rho640 \
                and abs(r0 - lr) < bd:
            best, bd = k, abs(r0 - lr)
    return best


def _perp(l, p):
    d = l / np.hypot(l[0], l[1])
    return abs(float(d[0] * p[0] + d[1] * p[1] + d[2]))


def _match_line(n0, r0, lines, scale, pa, pb, ang_deg=6.0, gate640=12.0):
    """THE PROTOCOL RULE: nearest detected line by MEAN PERPENDICULAR DISTANCE at the
    truth segment's two endpoints, angle tol 6 deg, gate 12 px@640. Returns (k, perp)."""
    best, bd = None, 1e18
    for k, (ln, lr, _lw) in enumerate(lines):
        dth = abs(np.mod(n0 - ln + np.pi / 2, np.pi) - np.pi / 2)
        if dth > np.deg2rad(ang_deg):
            continue
        l = _homog(ln, lr)
        d = 0.5 * (_perp(l, pa) + _perp(l, pb)) * scale
        if d <= gate640 and d < bd:
            best, bd = k, d
    return best, (None if best is None else bd)


def _homog(n, r):
    """Infinite line (theta_normal, rho) -> homogeneous [a, b, c] with a x + b y + c = 0."""
    return np.array([np.cos(n), np.sin(n), -r], float)


def _meet(l1, l2):
    p = np.cross(l1, l2)
    if abs(p[2]) < 1e-9:
        return None
    return np.array([p[0] / p[2], p[1] / p[2]], float)


def _row_at(l, x):
    a, b, c = l
    if abs(b) < 1e-9:
        return None
    return float(-(a * x + c) / b)


def solve_from_observables(r_near, r_net, w_near, w_net):
    """The four-observable solve. Returns (D, f, cy, H, r_far) or None."""
    k = w_near / w_net
    if not np.isfinite(k) or k <= 1.0 + 1e-6:
        return None
    D = NET_Y / (k - 1.0)
    f = w_near * D / W_M
    cy = (r_near - k * r_net) / (1.0 - k)
    Hm = (r_near - cy) * D / f
    r_far = cy + f * Hm / (D + LEN_M)
    return dict(D=D, f=f, cy=cy, H=Hm, r_far=r_far, k=k)


def run_frame(im, named):
    w = im.shape[1]
    scale = 640.0 / w
    dt, cos2, sin2, w, h, lines = cf._precompute(
        im, calibration, calibration.court_line_mask)
    H_true = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])

    out = {"w": w, "h": h, "scale": scale, "n_lines": len(lines), "lines": {}}

    truth_pts, det_lines, truth_lines = {}, {}, {}
    for name, (p0, p1) in MODEL.items():
        pa = calibration.court_to_image(H_true, [p0])[0]
        pb = calibration.court_to_image(H_true, [p1])[0]
        truth_pts[name] = (np.asarray(pa, float), np.asarray(pb, float))
        n0, r0 = cf._norm_form(pa, pb)
        truth_lines[name] = _homog(n0, r0)
        rec = {}
        kr = _match_rho(n0, r0, lines, scale)
        rec["match_shipped_rho"] = None if kr is None else int(kr)
        for gate in (8.0, 12.0):
            k, d = _match_line(n0, r0, lines, scale, pa, pb, gate640=gate)
            rec[f"match{int(gate)}"] = (None if k is None else int(k))
            rec[f"perp{int(gate)}"] = d
        k12 = rec["match12"]
        if k12 is not None:
            ln, lr, lw = lines[k12]
            det_lines[name] = _homog(ln, lr)
            rec["perp_a"] = _perp(det_lines[name], pa) * scale
            rec["perp_b"] = _perp(det_lines[name], pb) * scale
            rec["perp"] = 0.5 * (rec["perp_a"] + rec["perp_b"])
            rec["weight"] = float(lw)
        if kr is not None:
            lr_ = _homog(lines[kr][0], lines[kr][1])
            rec["perp_shipped_rho"] = 0.5 * (_perp(lr_, pa) + _perp(lr_, pb)) * scale
        out["lines"][name] = rec

    # ---- the net TAPE, as a separate object (there is NO painted line at the net)
    tape = calibration.project_court_3d(
        H_true, (w, h),
        [(0.0, NET_Y, court.NET_HEIGHT_POST), (W_M, NET_Y, court.NET_HEIGHT_POST)])
    out["tape"] = {}
    if tape is not None:
        n0, r0 = cf._norm_form(tape[0], tape[1])
        out["tape"]["truth_row"] = float(0.5 * (tape[0][1] + tape[1][1]))
        kt, dt_ = _match_line(n0, r0, lines, scale, tape[0], tape[1], gate640=12.0)
        out["tape"]["match12"] = None if kt is None else int(kt)
        out["tape"]["perp"] = dt_
        # how far apart ARE the two rows on this clip?
        gr = 0.5 * (truth_pts["net_ground"][0][1] + truth_pts["net_ground"][1][1])
        out["tape"]["ground_row"] = float(gr)
        out["tape"]["tape_minus_ground_px640"] = (out["tape"]["truth_row"] - gr) * scale

    # ---- the four observables, truth and detected
    def obs_from(pl, pr, la, lb):
        """(row, width) from an across-line meeting the two sidelines."""
        a = _meet(la, lb[0]); b = _meet(la, lb[1])
        if a is None or b is None:
            return None
        return 0.5 * (a[1] + b[1]), abs(a[0] - b[0])

    res = {}
    for row_name, key in (("near_baseline", "near"), ("net_ground", "net")):
        pa, pb = truth_pts[row_name]
        res[f"r_{key}_true"] = float(0.5 * (pa[1] + pb[1]))
        res[f"w_{key}_true"] = float(abs(pa[0] - pb[0]))
    pa, pb = truth_pts["far_baseline"]
    res["r_far_true"] = float(0.5 * (pa[1] + pb[1]))

    have_sides = "left_side" in det_lines and "right_side" in det_lines
    for row_name, key in (("near_baseline", "near"), ("net_ground", "net")):
        if row_name in det_lines and have_sides:
            got = obs_from(None, None, det_lines[row_name],
                           (det_lines["left_side"], det_lines["right_side"]))
            if got is not None:
                res[f"r_{key}_det"], res[f"w_{key}_det"] = float(got[0]), float(got[1])

    for key in ("near", "net"):
        if f"r_{key}_det" in res:
            res[f"err_r_{key}"] = abs(res[f"r_{key}_det"] - res[f"r_{key}_true"]) * scale
            res[f"err_w_{key}"] = abs(res[f"w_{key}_det"] - res[f"w_{key}_true"]) * scale

    # ---- end to end: solve from TRUTH observables (model control) and from DETECTED
    st = solve_from_observables(res["r_near_true"], res["r_net_true"],
                                res["w_near_true"], res["w_net_true"])
    if st:
        res["solve_truth"] = st
        res["err_far_truth_obs"] = abs(st["r_far"] - res["r_far_true"]) * scale
    if all(f"{p}_{k}_det" in res for p in ("r", "w") for k in ("near", "net")):
        sd = solve_from_observables(res["r_near_det"], res["r_net_det"],
                                    res["w_near_det"], res["w_net_det"])
        if sd:
            res["solve_det"] = sd
            res["err_far_det_obs"] = abs(sd["r_far"] - res["r_far_true"]) * scale
    out["obs"] = res
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=1)
    ap.add_argument("--out", default="data/output/near_line_precision.json")
    a = ap.parse_args()

    from score_truth import truth_sources
    srcs = truth_sources(a.frames)
    rows = []
    for clip, src, frames in srcs:
        for key, im, named in frames:
            try:
                r = run_frame(im, named)
            except Exception as e:              # never silently drop
                rows.append({"clip": clip, "src": src, "frame": str(key),
                             "error": f"{type(e).__name__}: {e}"})
                continue
            r["clip"], r["src"], r["frame"] = clip, src, str(key)
            rows.append(r)
            o = r.get("obs", {})
            print(f"{clip:24s} {src:5s} lines={r['n_lines']:3d} "
                  f"nb={o.get('err_r_near', float('nan')):6.2f} "
                  f"net={o.get('err_r_net', float('nan')):6.2f} "
                  f"wnb={o.get('err_w_near', float('nan')):6.2f} "
                  f"wnet={o.get('err_w_net', float('nan')):6.2f} "
                  f"far_det={o.get('err_far_det_obs', float('nan')):7.2f} "
                  f"far_truthobs={o.get('err_far_truth_obs', float('nan')):7.2f}",
                  flush=True)
    outp = REPO / a.out
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nwrote {outp}  n={len(rows)}")


if __name__ == "__main__":
    main()
