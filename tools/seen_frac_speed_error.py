"""seen_frac_speed_error.py — does `seen_frac >= 0.5` predict per-shot speed error?

The promoted version of the scratchpad harness behind
`docs/evidence/does-seen-frac-predict-speed-error.md`, plus QA's positive control
from `docs/evidence/seen-frac-gate-qa-verification.md`. Both lived in per-session
temp directories and neither was reproducible by anyone else; this is the one file
that reproduces both, and the ablation flags that explain why they disagreed.

WHAT EVERY NUMBER IS MEASURED AGAINST
-------------------------------------
`tools/synth_truth.py`'s simulator (drag + gravity + Magnus, projected through a
REAL clip's calibration) is the truth. It is compliant with project rule 11: no
scoreboard, no HUD, no burned-in graphic. The comparator is `avg_ground_kmh` —
synth_truth's ground-speed truth — chosen because `launch_kmh` would add the
shared -21.7% drag bias to BOTH bands and compress the ratio toward 1 (i.e. bias
the test toward the null). Launch-referenced error is reported as secondary only.

The measurement side is the SHIPPED speed chain, mirrored per flight from
`pipeline.analyze_video`:

    smooth_forecast -> image_to_court + runoff-box gate -> cap_court_jumps
    -> smooth_and_fill -> analytics.shot_speed_kmh

and `seen_frac` is computed exactly as pipeline's `real_fraction` closure does:
a frame counts as seen iff it was EMITTED and NOT COASTED (`pipeline.py:1460`).

THE ONE VARIABLE is per-flight `dropout`. Everything else is held fixed.

TWO ARMS (`--arm`)
------------------
  random      dropout ~ U(lo,hi) drawn independently of the flight. This is the
              experiment: is there a seen_frac -> error relationship at 0.5?
  correlated  QA's POSITIVE CONTROL. Same marginal dropout values, reassigned by
              RANK so the highest dropout lands on the highest-apex (`max_z`)
              flight — a real error-driving quantity, not an invented one. If the
              band ratio does not move under this arm, the harness is blind by
              construction and its null result is void. It is an option, not a
              fork, because the control is part of the experiment.

REPRODUCING THE TWO PRIOR IMPLEMENTATIONS
-----------------------------------------
Defaults reproduce the EVIDENCE FILE's configuration exactly:

    backend/.venv/Scripts/python.exe tools/seen_frac_speed_error.py \
        --n 1200 --seed 0 --json data/output/seen_frac_speed_error.json

QA's rebuild is the same tool with four flags flipped:

    ... --runoff-m 2.5 --min-alive 6 --rng-scheme split --track-mode compressed

`--runoff-m` is the load-bearing one. **The SHIPPED value is 2.5**
(`pipeline.py:1352`) and it is the DEFAULT here as of 2026-09-03. The evidence
file's original harness used 4.0, which was a fidelity defect in that harness,
not a free parameter; sections 4/5 of that file are reproducible only by passing
`--runoff-m 4.0` explicitly, and their numbers are SUPERSEDED by section 9.

Provenance is stamped from the RESOLVED argparse namespace, never from a preset
table, so a cache can never outlive its settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ball_physics"))
sys.path.insert(0, str(REPO / "tools"))

import synth_truth as ST  # noqa: E402
from swingvision import analytics, ball as ball_mod, calibration, court  # noqa: E402

CORNERS = ST.CORNERS

# clip -> (keypoint file, width, height). yt_match40 is EXCLUDED (T23: all four
# corner clicks off any court line, so its homography cannot carry a speed) and
# demo30 is EXCLUDED (docs/STATE.md: its speeds are never citable).
CLIPS = {
    "yt_rally2": ("yt_rally2_pts.json", 1280, 720),
    "am_hard_utr": ("am_hard_utr_pts.json", 1920, 1080),
    "yt_court": ("yt_court_pts.json", 1280, 720),
}
DEFAULT_CLIPS = ["yt_rally2", "am_hard_utr", "yt_court"]

#: These three are BURNED for the replacement-bar question — the verdict in
#: docs/evidence/does-seen-frac-predict-speed-error.md was measured on them, so a
#: threshold chosen on them would be chosen on its own training set. The §7
#: pre-registration requires held-out clips, hence resolve_clip() below.
BURNED_CLIPS = frozenset(DEFAULT_CLIPS)


def resolve_clip(name):
    """(keypoint file, w, h) for any audited calibration, not just the three above.

    Resolution comes from the calibration's own ``_audit.img_wh`` stamp rather than a
    hardcoded table, so a clip cannot silently be run at the wrong resolution — every
    pixel threshold in this project scales with frame height, and `img_wh_source`
    records whether the stamp read the real clip or assumed a default.

    REFUSES a calibration this project has already judged unusable, rather than
    letting a caller pass one by name: DEGENERATE stamps, `yt_match40` (T23 — all four
    corner clicks off any court line, so its homography cannot carry a speed) and
    `demo30` (docs/STATE.md: its speeds are never citable).
    """
    if name in CLIPS:
        return CLIPS[name]
    fn = f"{name}_pts.json" if not name.endswith(".json") else name
    # RAW load, deliberately: _load_kp strips `_`-prefixed keys (mirroring
    # pipeline.calibrate_video), which would drop the very `_audit` stamp this
    # function exists to read.
    raw = json.loads((REPO / "data" / fn).read_text(encoding="utf-8"))
    audit = raw.get("_audit") or {}
    verdict = str(audit.get("verdict", "")).upper()
    stem = fn.replace("_pts.json", "").replace(".json", "")
    if stem in ("yt_match40", "demo30"):
        raise SystemExit(f"{stem}: excluded by name — see this function's docstring")
    if verdict == "DEGENERATE":
        raise SystemExit(f"{fn}: stamped DEGENERATE ({audit.get('fit_residual_px')} px); refused")
    if not verdict:
        raise SystemExit(f"{fn}: no _audit stamp — run tools/validate_new_clip.py --audit --stamp")
    wh = audit.get("img_wh")
    if not wh:
        raise SystemExit(f"{fn}: _audit carries no img_wh; cannot resolve resolution")
    return (fn, int(wh[0]), int(wh[1]))

# The pre-registered bands, from the end of .claude/journals/lead.md. Do not edit
# these to fit a result: a failed bar stays failed.
BAND_LO = (0.35, 0.50)
BAND_HI = (0.50, 0.65)
MIN_BAND_N = 15


# --------------------------------------------------------------------------- #
# simulation                                                                    #
# --------------------------------------------------------------------------- #

def _hfov_for(kp, H, w, h):
    import height_curve
    f = height_curve.hfov_of(kp, H, w, h)
    return float(f) if f else 93.46


def _load_kp(fn):
    d = json.loads((REPO / "data" / fn).read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _draw_flights(kp, hfov, w, h, a):
    """Phase 1: simulate, filter, and DRAW every random quantity.

    All randomness is drawn here and stored, so `--arm correlated` can permute the
    dropout values without perturbing the random stream: the alive mask is a
    threshold on stored uniforms, so a different threshold reuses the same draws.
    That is what makes the two arms a genuine one-variable comparison.
    """
    xyz, uv, t, v0, rng, stride = ST.simulate(
        kp, hfov, w, h, a.n, a.fps, a.horizon_s, a.seed)
    pixel_noise = a.pixel_noise_px * (h / 720.0)   # 720p constant, scaled (project rule)

    if a.rng_scheme == "split":
        rng_d = np.random.default_rng(a.seed + 1000)
        dropout_draws = rng_d.uniform(a.dropout_lo, a.dropout_hi, len(xyz))
        rng_body = np.random.default_rng(a.seed + 2000)
    else:
        rng_body = rng

    flights = []
    for i in range(len(xyz)):
        tr = ST.truth_of(xyz[i], t)
        if tr is None:
            continue
        j = int(tr["i_bounce"])
        px_true = uv[i, : j + 1].astype(np.float64)
        inframe = (np.isfinite(px_true).all(axis=1)
                   & (px_true[:, 0] >= 0) & (px_true[:, 0] < w)
                   & (px_true[:, 1] >= 0) & (px_true[:, 1] < h))

        if a.rng_scheme == "split":
            # QA's ordering: eligibility screened on in-frame count BEFORE any
            # body draw; dropout indexed over the FILTERED flight list; noise
            # drawn before the alive uniforms, and only for in-frame points.
            if int(inframe.sum()) < a.min_alive:
                continue
            d = float(dropout_draws[len(flights) % len(dropout_draws)])
            idx = np.where(inframe)[0]
            noise = rng_body.normal(0, pixel_noise, (len(idx), 2))
            u = rng_body.random(len(idx))
        else:
            # Evidence-file ordering: eligibility screened on SPAN length, then
            # uniform -> alive-uniforms(j+1) -> noise(j+1), all off the single
            # stream `simulate` returned. Skipped flights consume no draws.
            if j + 1 < a.min_alive:
                continue
            d = float(rng_body.uniform(a.dropout_lo, a.dropout_hi))
            u = rng_body.random(j + 1)
            # LOAD-BEARING for exact reproduction: the evidence-file harness
            # `continue`d here, BEFORE drawing pixel noise, so a flight that
            # failed this screen consumed no normal() draws and every later
            # flight's stream position depends on it.
            if int(((u >= d) & inframe).sum()) < a.min_alive:
                continue
            noise = rng_body.normal(0, pixel_noise, px_true.shape)
            idx = np.arange(j + 1)

        flights.append(dict(
            i=int(i), j=j, px_true=px_true, inframe=inframe, idx=idx,
            noise=noise, u=u, dropout_draw=d, tr=tr,
            launch_kmh=float(np.linalg.norm(v0[i])) * 3.6,
            mean_z=float(np.mean(xyz[i, : j + 1, 2])),
            max_z=float(np.max(xyz[i, : j + 1, 2])),
        ))

    if a.arm == "correlated" and flights:
        # QA's positive control: same values, reassigned by rank of max_z.
        order = np.argsort([f["max_z"] for f in flights])
        vals = np.sort([f["dropout_draw"] for f in flights])
        for rank, k in enumerate(order):
            flights[k]["dropout"] = float(vals[rank])
    else:
        for f in flights:
            f["dropout"] = f["dropout_draw"]
    return flights


def _measure(f, H, a, w, h):
    """Phase 3: run ONE flight through the shipped speed chain."""
    j = f["j"]
    alive = f["u"] >= f["dropout"]
    positions = [None] * (j + 1)
    noisy = f["px_true"][f["idx"]] + f["noise"]
    for k, ii in enumerate(f["idx"]):
        if alive[k] and f["inframe"][ii]:
            positions[ii] = [float(noisy[k, 0]), float(noisy[k, 1])]
    n_alive = sum(p is not None for p in positions)
    if n_alive < a.min_alive:
        return None

    res_scale = h / 720.0
    ball_px, coasted, _conf = ball_mod.smooth_forecast(
        positions, fps_eff=a.fps, res_scale=res_scale)
    ball_seen = [p is not None and not coasted[k] for k, p in enumerate(ball_px)]
    # pipeline.real_fraction(hit, landing): denominator is the WHOLE span.
    seen_frac = float(sum(ball_seen)) / float(j + 1)

    ro = a.runoff_m
    raw, frames = [], []
    for k, p in enumerate(ball_px):
        if p is None:
            if a.track_mode == "full":
                raw.append(None)
                frames.append(k)
            continue
        x, y = calibration.image_to_court(H, [p])[0]
        inbox = (-ro <= x <= court.DOUBLES_WIDTH + ro
                 and -ro <= y <= court.LENGTH + ro)
        raw.append([float(x), float(y)] if inbox else None)
        frames.append(k)
    if not any(p is not None for p in raw):
        return None

    raw = ball_mod.cap_court_jumps(raw, max_step_m=a.max_speed_ms / a.fps)
    if not any(p is not None for p in raw):
        return None
    court_cov = float(np.mean([p is not None for p in raw]))
    sm = ball_mod.smooth_and_fill(raw, window=a.sg_window, polyorder=a.sg_polyorder)
    track = [(frames[k] / a.fps, float(sm[k, 0]), float(sm[k, 1]))
             for k in range(len(sm))]
    if len(track) < 2:
        return None
    est = float(analytics.shot_speed_kmh(track))
    if est <= 0:
        return None

    truth = float(f["tr"]["avg_ground_kmh"])
    if truth <= 0:
        return None
    gaps, run = [], 0
    for s in ball_seen:
        run = 0 if s else run + 1
        gaps.append(run)
    lk = f["launch_kmh"]
    return dict(
        flight=f["i"], seen_frac=seen_frac, dropout=f["dropout"],
        span_frames=j + 1, n_alive_det=n_alive, n_seen=int(sum(ball_seen)),
        n_court=int(sum(p is not None for p in raw)), court_cov=court_cov,
        max_gap_frames=int(max(gaps)) if gaps else 0,
        est_kmh=est, truth_ground_kmh=truth,
        truth_avg3d_kmh=float(f["tr"]["avg3d_kmh"]), launch_kmh=lk,
        mean_z_m=f["mean_z"], max_z_m=f["max_z"],
        abs_pct_err=abs(100.0 * (est - truth) / truth),
        signed_pct_err=100.0 * (est - truth) / truth,
        abs_kmh_err=abs(est - truth),
        abs_pct_err_launch=abs(100.0 * (est - lk) / lk) if lk > 0 else float("nan"),
    )


def run_clip(name, a):
    fn, w, h = resolve_clip(name)
    kp = _load_kp(fn)
    H = calibration.homography_from_landmarks({c: kp[c] for c in CORNERS})
    hfov = a.hfov if a.hfov else _hfov_for(kp, H, w, h)
    flights = _draw_flights(kp, hfov, w, h, a)
    rows = []
    for f in flights:
        r = _measure(f, H, a, w, h)
        if r is not None:
            r["clip"] = name
            rows.append(r)
    return rows, dict(pts=fn, w=w, h=h, hfov_deg=hfov, n_flights=len(flights),
                      n_usable=len(rows))


# --------------------------------------------------------------------------- #
# analysis                                                                      #
# --------------------------------------------------------------------------- #

def band_ratio(rows, key="abs_pct_err"):
    b1 = [r[key] for r in rows if BAND_LO[0] <= r["seen_frac"] < BAND_LO[1]]
    b2 = [r[key] for r in rows if BAND_HI[0] <= r["seen_frac"] < BAND_HI[1]]
    if not b1 or not b2:
        return None
    m1, m2 = float(np.median(b1)), float(np.median(b2))
    return dict(n1=len(b1), med1=m1, n2=len(b2), med2=m2,
                ratio=(m1 / m2) if m2 else float("nan"),
                floor_ok=bool(len(b1) >= MIN_BAND_N and len(b2) >= MIN_BAND_N))


def populations(rows, a):
    """Unrestricted, and the SHIPPED-SHOT restriction.

    pipeline.py:1759 drops `speed < MIN_SPEED_KMH` (5.0) unconditionally;
    pipeline.py:1761-1762 drops `disp < 0.8 or speed > 250.0` but ONLY for
    non-serves (`if not is_serve and (...)`). This harness has no serve/rally
    distinction, so `shipped_shot` applies the non-serve branch to everything —
    a stricter population than the pipeline's, stated rather than hidden.
    """
    return {
        "unrestricted": rows,
        "shipped_shot": [r for r in rows
                         if a.min_speed_kmh < r["est_kmh"] < a.max_speed_kmh],
    }


def classifier_table(rows):
    """Treat `seen_frac >= 0.5` as a binary classifier for "accurate".

    "Accurate" is defined as at or below the MEDIAN abs% error of the ACCEPTED
    set, so the gate is scored against the population it itself creates; the
    honest comparator is therefore the base rate, printed alongside.
    """
    acc = [r for r in rows if r["seen_frac"] >= 0.5]
    ref = [r for r in rows if r["seen_frac"] < 0.5]
    if not acc or not ref:
        return None
    thr = float(np.median([r["abs_pct_err"] for r in acc]))
    ok = lambda r: r["abs_pct_err"] <= thr  # noqa: E731
    a_ok = sum(1 for r in acc if ok(r))
    r_ok = sum(1 for r in ref if ok(r))
    return dict(
        threshold_abs_pct=thr, n_accepted=len(acc), n_refused=len(ref),
        accept_precision=a_ok / len(acc),
        base_rate=sum(1 for r in rows if ok(r)) / len(rows),
        refused_but_accurate=r_ok,
        refused_but_accurate_frac=r_ok / len(ref),
        accepted_but_inaccurate=len(acc) - a_ok,
        med_abs_pct_accepted=float(np.median([r["abs_pct_err"] for r in acc])),
        med_abs_pct_refused=float(np.median([r["abs_pct_err"] for r in ref])),
    )


def sweep_table(rows, lo=0.20, hi=0.90, step=0.05):
    """Accept-precision across candidate `seen_frac` thresholds — the §7 sweep.

    THE ACCURACY LABEL IS FIXED ACROSS THE SWEEP, and that is the whole point.
    `classifier_table` above defines "accurate" relative to the ACCEPTED set, which is
    fine at one fixed threshold but makes a sweep meaningless: the label would move with
    every candidate `t`, so precisions at different `t` would not be comparable. Here
    "accurate" is `<= the median abs% error of the WHOLE population`, computed ONCE. The
    base rate is then ~0.50 by construction and identical at every step, so the
    >=10-point margin means the same thing everywhere on the curve.

    Pre-registered in .claude/journals/lead.md before this ran. Do not "improve" this to
    a moving label to make a curve look better.
    """
    if len(rows) < 2:
        return None
    thr = float(np.median([r["abs_pct_err"] for r in rows]))
    ok = lambda r: r["abs_pct_err"] <= thr  # noqa: E731
    base = sum(1 for r in rows if ok(r)) / len(rows)
    out = []
    t = lo
    while t <= hi + 1e-9:
        acc = [r for r in rows if r["seen_frac"] >= t]
        ref = [r for r in rows if r["seen_frac"] < t]
        if acc and ref:
            prec = sum(1 for r in acc if ok(r)) / len(acc)
            out.append(dict(t=round(t, 2), n_accepted=len(acc), n_refused=len(ref),
                            accept_precision=prec, margin_pts=100.0 * (prec - base)))
        else:
            out.append(dict(t=round(t, 2), n_accepted=len(acc), n_refused=len(ref),
                            accept_precision=None, margin_pts=None))
        t += step
    return dict(fixed_accurate_threshold_abs_pct=thr, base_rate=base, curve=out)


def sweep_table_court_cov(rows, lo=0.20, hi=0.90, step=0.05):
    """The identical sweep on court-coverage instead of `seen_frac`.

    §7 requires the leading alternative to face the SAME held-out, swept, pre-registered
    bar rather than be swapped in on a correlation. NAMING IT IS NOT PROPOSING IT, and
    its correlation with error is PARTLY MECHANICAL: `analytics.shot_speed_kmh`
    integrates the path over exactly the points that survived court projection, so the
    estimate collapses toward zero by construction as court-coverage falls. Read any
    strong showing here with that confound in front of you.
    """
    if len(rows) < 2 or "court_cov" not in rows[0]:
        return None
    thr = float(np.median([r["abs_pct_err"] for r in rows]))
    ok = lambda r: r["abs_pct_err"] <= thr  # noqa: E731
    base = sum(1 for r in rows if ok(r)) / len(rows)
    out = []
    t = lo
    while t <= hi + 1e-9:
        acc = [r for r in rows if r["court_cov"] >= t]
        ref = [r for r in rows if r["court_cov"] < t]
        if acc and ref:
            prec = sum(1 for r in acc if ok(r)) / len(acc)
            out.append(dict(t=round(t, 2), n_accepted=len(acc), n_refused=len(ref),
                            accept_precision=prec, margin_pts=100.0 * (prec - base)))
        else:
            out.append(dict(t=round(t, 2), n_accepted=len(acc), n_refused=len(ref),
                            accept_precision=None, margin_pts=None))
        t += step
    return dict(fixed_accurate_threshold_abs_pct=thr, base_rate=base, curve=out)


def _spearman(x, y):
    from scipy.stats import spearmanr
    rho, p = spearmanr(x, y)
    return float(rho), float(p)


def analyse(rows_by_clip, a):
    out = {}
    for pop_name in ("unrestricted", "shipped_shot"):
        per_clip, pooled = {}, []
        sw_sf, sw_cc = {}, {}
        for clip, rows in rows_by_clip.items():
            pop = populations(rows, a)[pop_name]
            pooled += pop
            br = band_ratio(pop)
            entry = {"n": len(pop), "band": br}
            if len(pop) >= 3:
                entry["spearman_seen_frac_vs_abs_pct"] = _spearman(
                    [r["seen_frac"] for r in pop], [r["abs_pct_err"] for r in pop])
                entry["spearman_court_cov_vs_abs_pct"] = _spearman(
                    [r["court_cov"] for r in pop], [r["abs_pct_err"] for r in pop])
            # §7 sweep, per clip (the §7 bar is ">= 3 of the held-out CLIPS", so a
            # pooled curve would let one clip carry the others). Computed here from
            # `pop` rather than by stashing rows on the entry, which would bloat the
            # JSON with one record per synthetic flight.
            sw_sf[clip] = sweep_table(pop)
            sw_cc[clip] = sweep_table_court_cov(pop)
            per_clip[clip] = entry
        clears_G = [c for c, e in per_clip.items()
                    if e["band"] and e["band"]["ratio"] >= a.gate_g]
        clears_N = [c for c, e in per_clip.items()
                    if e["band"] and e["band"]["ratio"] <= a.gate_n]
        floor_ok = [c for c, e in per_clip.items() if e["band"] and e["band"]["floor_ok"]]
        out[pop_name] = dict(
            per_clip=per_clip, n_pooled=len(pooled),
            clips_clearing_G=clears_G, clips_clearing_N=clears_N,
            clips_clearing_floor=floor_ok,
            verdict=("UNDERPOWERED" if len(floor_ok) < 2
                     else "G" if len(clears_G) >= 2
                     else "N" if len(clears_N) >= 2 else "I"),
            classifier=classifier_table(pooled),
            # §7 sweep. Per-clip, because the §7 bar is ">= 3 of the held-out
            # CLIPS" — a pooled curve would let one clip carry the others.
            sweep_seen_frac=sw_sf,
            sweep_court_cov=sw_cc,
        )
    return out


# --------------------------------------------------------------------------- #

def provenance(a):
    """Stamped from the RESOLVED namespace — never a preset table."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    calib = {}
    for name in a.clips:
        fn = resolve_clip(name)[0]
        calib[name] = hashlib.sha256(
            (REPO / "data" / fn).read_bytes()).hexdigest()[:16]
    return dict(tool="tools/seen_frac_speed_error.py", commit=commit,
                python=sys.version.split()[0], numpy=np.__version__,
                resolved_config={k: (str(v) if isinstance(v, Path) else v)
                                 for k, v in sorted(vars(a).items())},
                calibration_sha256_16=calib,
                shipped_runoff_m=2.5, shipped_runoff_ref="pipeline.py:1352")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--clips", nargs="+", default=DEFAULT_CLIPS,
                   help="clip names; any audited calibration, not just the "
                        "three burned defaults (see resolve_clip)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n", type=int, default=1200, help="flights REQUESTED per clip")
    p.add_argument("--arm", choices=("random", "correlated"), default="random",
                   help="'correlated' is QA's positive control (dropout ranked onto max_z)")
    # --- ablation flags: evidence-file defaults; QA's rebuild flips all four ---
    p.add_argument("--runoff-m", type=float, default=2.5,
                   help="DEFAULT IS THE SHIPPED VALUE 2.5 (pipeline.py:1352). "
                        "Pass --runoff-m 4.0 to reproduce the SUPERSEDED numbers in "
                        "sections 4/5 of the evidence file, which used 4.0 - a "
                        "fidelity defect, corrected 2026-09-03.")
    p.add_argument("--min-alive", type=int, default=5)
    p.add_argument("--rng-scheme", choices=("single", "split"), default="single")
    p.add_argument("--track-mode", choices=("full", "compressed"), default="full")
    # --- held fixed unless deliberately ablated ---
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--horizon-s", type=float, default=2.0)
    p.add_argument("--dropout-lo", type=float, default=0.05)
    p.add_argument("--dropout-hi", type=float, default=0.80)
    p.add_argument("--pixel-noise-px", type=float, default=2.0,
                   help="720p-tuned; scaled by frame_height/720 at use")
    p.add_argument("--max-speed-ms", type=float, default=84.0)
    p.add_argument("--sg-window", type=int, default=7)
    p.add_argument("--sg-polyorder", type=int, default=2)
    p.add_argument("--min-speed-kmh", type=float, default=5.0)
    p.add_argument("--max-speed-kmh", type=float, default=250.0)
    p.add_argument("--hfov", type=float, default=None,
                   help="override; default is height_curve.hfov_of per clip")
    p.add_argument("--gate-g", type=float, default=1.5, help="pre-registered, do not edit")
    p.add_argument("--gate-n", type=float, default=1.1, help="pre-registered, do not edit")
    p.add_argument("--json", type=Path, default=None)
    p.add_argument("--rows", action="store_true", help="include per-flight rows in --json")
    a = p.parse_args(argv)

    rows_by_clip, meta = {}, {}
    for name in a.clips:
        rows, m = run_clip(name, a)
        rows_by_clip[name], meta[name] = rows, m
        print(f"{name}: hfov {m['hfov_deg']:.1f} deg, {len(rows)} usable flights",
              flush=True)

    res = analyse(rows_by_clip, a)
    for pop in ("unrestricted", "shipped_shot"):
        e = res[pop]
        print(f"\n[{pop}] n={e['n_pooled']}  verdict={e['verdict']}")
        for clip in a.clips:
            b = e["per_clip"][clip]["band"]
            if not b:
                print(f"  {clip:12s} band empty")
                continue
            print(f"  {clip:12s} n1={b['n1']:4d} med1={b['med1']:7.2f}  "
                  f"n2={b['n2']:4d} med2={b['med2']:7.2f}  ratio={b['ratio']:.3f}"
                  f"{'' if b['floor_ok'] else '  [BELOW n>=15 FLOOR]'}")
        c = e["classifier"]
        if c:
            print(f"  accept-precision={c['accept_precision']:.3f}  "
                  f"base_rate={c['base_rate']:.3f}  "
                  f"refused-but-accurate={c['refused_but_accurate_frac']:.3f}")

    payload = dict(provenance=provenance(a), clips=meta, results=res)
    if a.rows:
        payload["rows"] = [r for rows in rows_by_clip.values() for r in rows]
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print("wrote", a.json)
    return payload


if __name__ == "__main__":
    main()
