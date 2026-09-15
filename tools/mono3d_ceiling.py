"""mono3d_ceiling.py — the CEILING on monocular 3D bounce placement. Measured.

WHY THIS EXISTS
---------------
v1 is an engine: a 3D court map, a drag+Magnus 3D trajectory, and a bounce
triangulated by intersecting that trajectory with the ground plane. SPEC §3 asks
for **10 cm on >=90% of contested calls** and SPEC §4 for **+/-1 frame**.
Monocular 3D has NEVER been measured in this project. This is the instrument.

It is a MEASUREMENT, not a feature. Nothing here is tuned to reach a bar.

WHAT IS COMPARED — TWO ARMS ON THE SAME PIXELS
----------------------------------------------
Both arms see the identical seeded flights and the identical noisy pixel track
(they share `synth_truth.noisy_pixels`, so the rng draw order cannot diverge):

  CONTROL (what ships today) — `synth_truth.control_bounce_xy`: back-project each
      noisy pixel to the court plane with the 4-corner homography and take the
      LAST point as the bounce. DEPTH IS PINNED BY: the assumption z=0 for every
      observation, plus the regulation doubles rectangle behind the homography.
      A ball one metre in the air lands further down-court than it really is.

  MONO 3D (the v1 engine) — fit (p0, v0, omega) to the noisy 2D track with
      `trajectory_fit.fit_arc(camera=..., physical_bounds=True)`, then integrate
      that fitted arc forward and take its FIRST z=0 crossing.
      DEPTH IS PINNED BY: known g = 9.81; the drag+Magnus model with CD and
      CL(S) held at their defaults; the EXACT hfov (focal length); the 6-DOF
      camera pose recovered from four known doubles corners, i.e. the regulation
      court dimensions; `physical_bounds`' plausibility box on p0/v0/omega; and
      the ground plane z=0 for the intersection itself. A single camera does not
      OBSERVE depth — that list is what IMPOSES it (CLAUDE.md hard rule 7).

Scored against `synth_truth.truth_of()` — the EXACT interpolated z=0 crossing of
the simulated flight. No human labels, no HUD, no model grading itself.

A REPROJECTION RESIDUAL CERTIFIES NOTHING and is never used as a gate here; it is
recorded only as a covariate. `docs/evidence/arc-fit-observability.md` has a
23.8x span error that passes reproj_px, and the first eight fits this tool ever
ran came back at 1.9 px rmse against 2.0 px of injected noise — a perfect image
fit — with bounce errors of 1.5 to 10 METRES.

TWO READS ON THE BOUNCE TIME, BECAUSE THE RIG LEAKS THE SEGMENTATION
--------------------------------------------------------------------
The rig truncates the observed track at the true bounce, which bounds t_b to
within one frame before the fitter does anything. So:
  B1  segmentation GIVEN — fit all in-air frames up to the true last in-air one.
      B1 passing is an UPPER BOUND, not evidence v1 hits +/-1 frame.
  B2  segmentation WITHHELD — drop the last 3 observations and extrapolate the
      fitted arc to z=0. This is the read that tests whether the physics
      actually predicts the crossing, and its position error is a second read on
      the 10 cm bar.

DENOMINATORS — a fitter that discards its hard cases is grading itself
----------------------------------------------------------------------
`presented` = flights the detector handed the estimator a usable track for.
Non-convergence and arcs that never cross z=0 are FAILURES inside it, not
exclusions. `all_truth` additionally includes flights the RIG dropped (ball never
enough in frame); those drops are identical for both arms, so they cancel in the
comparison. Both rates are reported for every configuration.

    cd backend && .venv/Scripts/python.exe ../tools/mono3d_ceiling.py --suite all
    cd backend && .venv/Scripts/python.exe ../tools/mono3d_ceiling.py --suite dt-ab
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ball_physics"))
sys.path.insert(0, str(REPO / "tools"))

import synth_truth as ST                                        # noqa: E402
from height_curve import HFOV_DEG, SETBACK_M, frame_the_court   # noqa: E402

OUT_DIR = REPO / "data" / "output" / "mono3d_ceiling"

# The fitter's own coefficients, read from the modules it actually uses, so the
# provenance stamp reports the RESOLVED configuration and not a preset table.
def fitter_aero() -> dict:
    from tennis_tracker.physics.aerodynamics import DragModel, LiftModel
    d, l = DragModel(), LiftModel()
    return {"cd": d.cd, "cl_max": l.cl_max, "cl_sat": l.sat}


def simulator_aero() -> dict:
    from tennis_tracker.physics import simulator_torch as S
    return {"cd": S.CD_DEFAULT, "cl_max": S.CL_MAX, "cl_sat": S.CL_SAT}


# --------------------------------------------------------------------------
# the monocular 3D arm
# --------------------------------------------------------------------------
def ground_intersection(p0, v0, omega, t_max, dt=2e-3, drag=None, lift=None):
    """First z=0 crossing of the fitted arc, or None if it never crosses.

    `physics.simulate(..., bounces=0)` terminates EXACTLY at the interpolated
    crossing and records it in `bounce_indices`, so this is a lookup, not a
    second root-find. Always integrated at dt=2e-3 regardless of the dt the FIT
    used, so the integrator step cannot leak into the reported accuracy.

    `drag` / `lift` default to the fitter's own models; they are overridable so
    the crossing extraction can be pinned against a closed-form vacuum parabola.
    """
    from tennis_tracker.physics import simulate
    tr = simulate(np.asarray(p0, float), np.asarray(v0, float),
                  np.asarray(omega, float), dt=dt, t_max=float(t_max),
                  bounces=0, drag=drag, lift=lift)
    if not tr.bounce_indices:
        return None
    k = tr.bounce_indices[0]
    return np.asarray(tr.pos[k], float), float(tr.t[k])


def fit_job(job: dict) -> dict:
    """One monocular 3D fit + ground intersection. Top-level for Windows spawn.

    The expensive half of the run, so it is what gets distributed. The flights
    and their noisy pixels are built SEQUENTIALLY in the parent — parallelising
    that would reorder the rng draws and unpair the arms.
    """
    from tennis_tracker.data.camera import Camera
    from tennis_tracker.estimation.trajectory_fit import fit_arc

    cam = Camera(K=np.asarray(job["K"]), R=np.asarray(job["R"]),
                 t=np.asarray(job["t"]), width=job["w"], height=job["h"])
    tm = np.asarray(job["tm"], float)
    px = np.asarray(job["px"], float)
    t0 = time.time()
    kw = dict(camera=cam, physical_bounds=True, spin_free=job["spin_free"],
              dt=job["dt"])
    if job.get("p0_anchor") is not None:
        kw.update(p0_init=np.asarray(job["p0_anchor"], float), fix_p0=True)
    fit = fit_arc(tm, px, **kw)
    # Integrate well past the last observation so a WITHHELD tail (B2) still has
    # room to reach the ground; 2 s is longer than any flight the rig draws.
    hit = ground_intersection(fit.p0, fit.v0, fit.omega, float(tm[-1]) + 2.0)
    out = {"key": job["key"], "arm": job["arm"], "flight": job["flight"],
           "converged": bool(fit.success), "rmse_px": float(fit.rmse),
           "fit_s": round(time.time() - t0, 3),
           "p0": [float(x) for x in fit.p0], "v0": [float(x) for x in fit.v0],
           "spin_rpm": float(np.linalg.norm(fit.omega)) * 60.0 / (2.0 * np.pi),
           "crossed": hit is not None}
    if hit is not None:
        xyz, tb = hit
        out["bounce_xy"] = list(ST.to_court_xy(xyz[:2]))
        out["t_b"] = tb
    return out


# --------------------------------------------------------------------------
# flights: simulate, truth, and the one noisy pixel track both arms score
# --------------------------------------------------------------------------
def _inframe_count(uv_i, i_bounce, stride, width, height) -> tuple:
    """(in-frame samples, total samples) on the decimated grid — DIAGNOSTIC ONLY.

    Used to characterise the flights the rig never presents (rule 11: always
    inspect the rejects). The tracks that ARE presented come from
    `synth_truth.noisy_pixels`; this never feeds an estimator.
    """
    m = np.arange(0, i_bounce + 1, stride)
    px = uv_i[m]
    ok = (np.isfinite(px).all(axis=1) & (px[:, 0] >= 0) & (px[:, 0] < width)
          & (px[:, 1] >= 0) & (px[:, 1] < height))
    return int(ok.sum()), int(len(m))


def build_flights(kp, cfg) -> tuple:
    """Simulate, take exact truth, and build the ONE noisy track per flight.

    Returns (flights, tally). `flights` carries the truth, the noisy pixels and
    the 2D control arm's answer; the 3D fits are dispatched afterwards.
    """
    from swingvision import calibration
    from gen_synth_camera import draw_launch

    w, h, fps = cfg["width"], cfg["img_height"], cfg["fps"]
    H = calibration.homography_from_landmarks({c: kp[c] for c in ST.CORNERS})
    xyz, uv, t, v0, rng, stride = ST.simulate(
        kp, cfg["hfov"], w, h, cfg["n"], fps, cfg["horizon_s"], cfg["seed"],
        cfg["truth_fps"], cd=cfg["sim_cd"], cl_max=cfg["sim_cl_max"],
        cl_sat=cfg["sim_cl_sat"])

    # Recover the launch draw for the rejects covariates WITHOUT touching
    # simulate()'s signature: draw_launch is its first rng consumer, so the same
    # seed reproduces it exactly. Asserted, never assumed.
    v0b, omega, p0 = draw_launch(np.random.default_rng(cfg["seed"]), cfg["n"])
    assert np.allclose(v0b, v0), "launch draw did not reproduce — rng order moved"

    flights, tally = [], {"n_sim": int(len(xyz)), "no_truth": 0, "rig_drop": 0}
    rig_drops = []
    for i in range(len(xyz)):
        tr = ST.truth_of(xyz[i], t)
        if tr is None:                       # never comes down inside the horizon
            tally["no_truth"] += 1
            continue
        j = tr["i_bounce"]
        got = ST.noisy_pixels(uv[i], t, j, stride, w, h, rng,
                              pixel_noise=cfg["pixel_noise"],
                              dropout=cfg["dropout"], min_len=cfg["min_len"])
        spd = float(np.linalg.norm(v0[i]))
        cov = {
            "flight": i,
            "launch_speed_ms": spd,
            "launch_elev_deg": math.degrees(math.asin(float(v0[i][2]) / spd)),
            "spin_rpm": float(np.linalg.norm(omega[i])) * 60.0 / (2.0 * np.pi),
            "launch_z_m": float(p0[i][2]),
            "launch_p0": [float(x) for x in p0[i]],
            "true_bounce_xy": [float(v) for v in tr["bounce_xy"]],
            # float() is not decoration: the truth grid comes off a float32
            # torch tensor, and an un-cast np.float32 is not JSON serialisable.
            "true_t_b": float(tr["t_b"]),
            "dur_s": float(tr["dur_s"]),
            "apex_z_m": float(np.max(xyz[i, : j + 1, 2])),
            # depth is the physics-frame X of the bounce: metres from the near
            # baseline, i.e. how far from the camera the call has to be made.
            "depth_m": float(tr["bounce_xy"][1]),
        }
        if got is None:
            nin, ntot = _inframe_count(uv[i], j, stride, w, h)
            tally["rig_drop"] += 1
            rig_drops.append({**cov, "inframe": nin, "grid": ntot,
                              "inframe_frac": nin / max(ntot, 1)})
            continue
        px, tm, idx = got
        court_xy = calibration.image_to_court(H, px)
        ctrl = ST.control_bounce_xy(court_xy)
        nin, ntot = _inframe_count(uv[i], j, stride, w, h)
        flights.append({
            **cov,
            "n_obs": int(len(px)),
            "grid": ntot,
            "inframe_frac": nin / max(ntot, 1),
            "seen_frac": len(px) / max(ntot, 1),
            "obs_span_s": float(tm[-1] - tm[0]),
            "last_obs_t": float(tm[-1]),
            "tm": tm.tolist(),
            "px": px.tolist(),
            "ctrl_bounce_xy": ctrl,
            "ctrl_err_m": math.dist(tr["bounce_xy"], ctrl),
            # the control's bounce TIME is the last observation, which the rig's
            # truncation already bounds to one frame. Recorded, not credited.
            "ctrl_dt_frames": (float(tm[-1]) - tr["t_b"]) * fps,
        })
    return flights, tally, rig_drops


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------
def score(flights, fits, tally, *, fps, bar_m=0.10) -> dict:
    """Bar rates for one arm, with failures inside the denominator."""
    by = {(f["arm"], f["flight"]): f for f in fits}
    arms = sorted({a for a, _ in by})
    n_pres = len(flights)
    n_all = n_pres + tally["rig_drop"] + tally["no_truth"]
    out = {"n_presented": n_pres, "n_all_truth": n_pres + tally["rig_drop"],
           "n_sim": tally["n_sim"], "no_truth": tally["no_truth"],
           "rig_drop": tally["rig_drop"], "n_all": n_all}

    ctrl = np.array([f["ctrl_err_m"] for f in flights], float)
    out["control_2d"] = {
        "within_bar_pct_presented": 100.0 * float((ctrl <= bar_m).mean()),
        "within_bar_pct_all_truth":
            100.0 * float((ctrl <= bar_m).sum()) / max(out["n_all_truth"], 1),
        "err_median_m": float(np.median(ctrl)),
        "err_p90_m": float(np.percentile(ctrl, 90)),
        "dt_frames_abs_median":
            float(np.median(np.abs([f["ctrl_dt_frames"] for f in flights]))),
    }

    for arm in arms:
        err, dtf, nconv, ncross, nmiss = [], [], 0, 0, 0
        for f in flights:
            r = by.get((arm, f["flight"]))
            if r is None:
                nmiss += 1            # too few observations to attempt the fit
                continue
            if not r["converged"]:
                nconv += 1
            if not r["crossed"]:
                ncross += 1
                continue
            err.append(math.dist(f["true_bounce_xy"], r["bounce_xy"]))
            dtf.append((r["t_b"] - f["true_t_b"]) * fps)
        err_a, dtf_a = np.array(err, float), np.abs(np.array(dtf, float))
        # FAILURES SIT IN THE DENOMINATOR: a flight with no crossing, or no fit
        # at all, is counted as outside every bar rather than dropped.
        out[arm] = {
            "n_fitted": len(err) + ncross,
            "n_no_fit": nmiss,
            "n_not_converged": nconv,
            "n_no_ground_crossing": ncross,
            "within_bar_pct_presented":
                100.0 * float((err_a <= bar_m).sum()) / max(n_pres, 1),
            "within_bar_pct_all_truth":
                100.0 * float((err_a <= bar_m).sum()) / max(out["n_all_truth"], 1),
            "err_median_m": float(np.median(err_a)) if len(err_a) else None,
            "err_p90_m": float(np.percentile(err_a, 90)) if len(err_a) else None,
            "within_1_frame_pct":
                100.0 * float((dtf_a <= 1.0).sum()) / max(n_pres, 1),
            "within_2_frame_pct":
                100.0 * float((dtf_a <= 2.0).sum()) / max(n_pres, 1),
            "dt_frames_abs_median": float(np.median(dtf_a)) if len(dtf_a) else None,
            "dt_frames_abs_p90":
                float(np.percentile(dtf_a, 90)) if len(dtf_a) else None,
            "dt_frames_bias": float(np.mean(dtf)) if len(dtf) else None,
        }
    return out


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True,
                              timeout=15).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def stamp(cfg, kp, pitch_deg) -> dict:
    """Provenance from the RESOLVED configuration, not a preset table."""
    return {
        "tool": "tools/mono3d_ceiling.py",
        "commit": git_sha(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "measured_against":
            "EXACT simulated truth: the interpolated z=0 crossing of a "
            "drag+gravity+Magnus flight (synth_truth.truth_of). No human "
            "labels, no HUD, no model output.",
        "depth_pinned_by": {
            "control_2d": "z=0 assumed for EVERY observation + the 4-corner "
                          "homography onto the regulation doubles rectangle",
            "mono3d": "known g=9.81; drag+Magnus with CD/CL fixed at the "
                      "fitter's defaults; EXACT hfov; 6-DOF camera pose from "
                      "four known doubles corners (regulation court "
                      "dimensions); fit_arc physical_bounds box; ground plane "
                      "z=0 for the intersection",
        },
        "config": dict(cfg),
        "camera": {"corners_px": kp, "pitch_deg": pitch_deg,
                   "setback_m": cfg["setback_m"], "hfov_deg": cfg["hfov"]},
        "fitter_aero": fitter_aero(),
        "simulator_aero_default": simulator_aero(),
        "physics_models_agree": fitter_aero() == simulator_aero(),
    }


def make_cfg(**kw) -> dict:
    cfg = {"tag": "cfg", "mount_m": 3.0, "setback_m": SETBACK_M,
           "hfov": HFOV_DEG, "width": 1920, "img_height": 1080, "fps": 60.0,
           "truth_fps": 240.0, "horizon_s": 2.0, "n": 500, "seed": 0,
           "pixel_noise": 2.0, "dropout": 0.30, "min_len": 5, "bar_m": 0.10,
           "withhold": 3, "dt": 6e-3, "spin_free": True, "p0_anchored": False,
           "sim_cd": None, "sim_cl_max": None, "sim_cl_sat": None,
           "arms": ("b1",)}
    cfg.update(kw)
    return cfg


def run_config(cfg, pool=None, *, keep_rows=True) -> dict:
    """One configuration, both arms, paired. Returns the full result record."""
    got = frame_the_court(cfg["mount_m"], cfg["setback_m"], cfg["hfov"],
                          cfg["width"], cfg["img_height"])
    if got is None:
        return {"tag": cfg["tag"], "error":
                f"mount {cfg['mount_m']} m cannot frame all four corners at "
                f"hfov {cfg['hfov']} / setback {cfg['setback_m']} m"}
    kp, pitch_deg = got

    t0 = time.time()
    flights, tally, rig_drops = build_flights(kp, cfg)

    from tennis_tracker.bridge import camera_from_court_corners
    cam, _ = camera_from_court_corners({c: kp[c] for c in ST.CORNERS},
                                       (cfg["width"], cfg["img_height"]),
                                       hfov_deg=cfg["hfov"])
    cam_wire = {"K": cam.K.tolist(), "R": cam.R.tolist(), "t": cam.t.tolist(),
                "w": cfg["width"], "h": cfg["img_height"]}
    cam_height_m = float((-np.asarray(cam.R).T @ np.asarray(cam.t))[2])

    jobs = []
    for f in flights:
        for arm in cfg["arms"]:
            k = len(f["tm"]) - (cfg["withhold"] if arm == "b2" else 0)
            if k < cfg["min_len"]:
                continue          # scored as n_no_fit, i.e. a failure
            jobs.append({**cam_wire, "key": f"{cfg['tag']}:{arm}:{f['flight']}",
                         "arm": arm, "flight": f["flight"],
                         "tm": f["tm"][:k], "px": f["px"][:k],
                         "dt": cfg["dt"], "spin_free": cfg["spin_free"],
                         # the TRUE launch point — stronger than the pose-lifted
                         # one arc-fit-observability measured, and v1 has
                         # neither (SPEC §9 tossed all pose). Descriptive only.
                         "p0_anchor": (f["launch_p0"]
                                       if cfg["p0_anchored"] else None)})
    fits = list(pool.imap_unordered(fit_job, jobs, chunksize=1)) if pool else \
        [fit_job(j) for j in jobs]

    res = score(flights, fits, tally, fps=cfg["fps"], bar_m=cfg["bar_m"])
    res.update(tag=cfg["tag"], wall_s=round(time.time() - t0, 1),
               n_jobs=len(jobs), camera_height_m=cam_height_m,
               provenance=stamp(cfg, kp, pitch_deg))
    if keep_rows:
        light = [{k: v for k, v in f.items() if k not in ("tm", "px")}
                 for f in flights]
        res["flights"] = light
        res["rig_drops"] = rig_drops
        res["fits"] = fits
    return res


# --------------------------------------------------------------------------
# suites
# --------------------------------------------------------------------------
HEIGHTS_D = (1.0, 1.5, 2.5, 4.0, 8.0)
NOISE_E = (0.0, 1.0, 2.0, 4.0)
KILL_HEIGHTS = (1.0, 1.5, 2.5, 3.0, 4.0, 8.0)


def suite_configs(name, n, seed):
    base = dict(n=n, seed=seed)
    if name == "barA":          # bars A + B (B1 and B2 both)
        return [c for c in suite_configs("noise", n, seed)
                if c["pixel_noise"] == 2.0]
    if name == "noise":         # bar E. The 2.0 px rung IS bar A's setting, so
        #                         it is not run twice — it carries both tags.
        return [make_cfg(tag=("barA_noise2px_3.0m" if px == 2.0
                              else f"noise{px:g}px_3.0m"), pixel_noise=px,
                         arms=("b1", "b2") if px == 2.0 else ("b1",), **base)
                for px in NOISE_E]
    if name == "height":        # bar D
        return [make_cfg(tag=f"height{h:g}m", mount_m=h, **base)
                for h in HEIGHTS_D]
    if name == "kill":          # bar C: PERFECT detections at every height
        return [make_cfg(tag=f"kill{h:g}m_perfect", mount_m=h, pixel_noise=0.0,
                         dropout=0.0, **base) for h in KILL_HEIGHTS]
    if name == "barF":          # the self-grading control
        fa = fitter_aero()
        return [make_cfg(tag=f"barF_{s:+.0%}".replace("%", "pct"),
                         sim_cd=fa["cd"] * (1 + s),
                         sim_cl_max=fa["cl_max"] * (1 + s),
                         arms=("b1", "b2"), **base) for s in (0.20, -0.20)]
    if name == "barA-verify":   # bar A again at the SHIPPED integrator step, so
        #                         the 3x speedup cannot be blamed for the verdict
        return [make_cfg(tag="barAverify_dt2e-3", arms=("b1", "b2"), dt=2e-3,
                         **base)]
    if name == "p0anchor":      # descriptive secondary: needs pose, v1 has none
        return [make_cfg(tag="p0anchored_3.0m", p0_anchored=True, **base)]
    raise SystemExit(f"unknown suite {name}")


SUITES = ("noise", "height", "kill", "barF")   # "noise" carries bar A's rung


def dt_ab(n, seed, workers):
    """Is the integrator step a free speedup? PAIRED, one variable, seeded.

    The fit's cost is (t_max / dt) RK4 steps per residual evaluation, so dt is
    the only speed lever a 10,000-fit study has. It is legitimate only if the
    ANSWER does not move, so this fits the same flights at the shipped 2e-3 and
    at the candidates and reports the paired difference in bounce error.
    """
    import multiprocessing as mp
    cfg = make_cfg(tag="dt_ab", n=n, seed=seed)
    got = frame_the_court(cfg["mount_m"], cfg["setback_m"], cfg["hfov"],
                          cfg["width"], cfg["img_height"])
    kp, _ = got
    flights, tally, _ = build_flights(kp, cfg)
    from tennis_tracker.bridge import camera_from_court_corners
    cam, _ = camera_from_court_corners({c: kp[c] for c in ST.CORNERS},
                                       (cfg["width"], cfg["img_height"]),
                                       hfov_deg=cfg["hfov"])
    wire = {"K": cam.K.tolist(), "R": cam.R.tolist(), "t": cam.t.tolist(),
            "w": cfg["width"], "h": cfg["img_height"]}
    steps = (2e-3, 6e-3, 1e-2)
    jobs = [{**wire, "key": f"{d}:{f['flight']}", "arm": f"dt{d:g}",
             "flight": f["flight"], "tm": f["tm"], "px": f["px"], "dt": d,
             "spin_free": True, "p0_anchor": None}
            for d in steps for f in flights]
    with mp.Pool(workers) as pool:
        fits = list(pool.imap_unordered(fit_job, jobs, chunksize=1))
    truth = {f["flight"]: f for f in flights}
    per = {}
    for r in fits:
        f = truth[r["flight"]]
        e = (math.dist(f["true_bounce_xy"], r["bounce_xy"])
             if r["crossed"] else None)
        per.setdefault(r["arm"], {})[r["flight"]] = (e, r["fit_s"])
    ref = per[f"dt{2e-3:g}"]
    out = {"n_flights": len(flights), "seed": seed, "steps": list(steps),
           "measured_against": "the same EXACT simulated truth; this table is a "
                               "PAIRED comparison of the fitter against itself.",
           "arms": {}}
    for d in steps:
        a = per[f"dt{d:g}"]
        common = [k for k in a if a[k][0] is not None and ref[k][0] is not None]
        d_err = [abs(a[k][0] - ref[k][0]) for k in common]
        out["arms"][f"dt{d:g}"] = {
            "median_fit_s": float(np.median([a[k][1] for k in a])),
            "n_crossed": sum(1 for k in a if a[k][0] is not None),
            "median_err_m": float(np.median([a[k][0] for k in a
                                             if a[k][0] is not None])),
            "paired_abs_delta_vs_2e-3_median_m":
                float(np.median(d_err)) if d_err else None,
            "paired_abs_delta_vs_2e-3_max_m":
                float(np.max(d_err)) if d_err else None,
            "n_paired": len(common),
        }
    return out


COVARIATES = ("launch_speed_ms", "launch_elev_deg", "spin_rpm", "launch_z_m",
              "apex_z_m", "depth_m", "dur_s", "n_obs", "grid", "seen_frac",
              "inframe_frac", "obs_span_s")


def rejects(res, arm="b1", bar_m=0.10) -> dict:
    """RULE 11: inspect what the estimator LOST, not what it kept.

    Splits the presented flights into inside-the-bar / outside-the-bar / never
    reached the ground, and reports the median of every covariate for each. The
    p-values are Mann-Whitney U on inside-vs-outside, DESCRIPTIVE ONLY: twelve
    covariates are tested at once and nothing here was pre-registered, so read
    them as a ranking of suspects, not as findings.
    """
    from scipy.stats import mannwhitneyu
    by = {f["flight"]: f for f in res.get("flights", [])}
    fits = [f for f in res.get("fits", []) if f["arm"] == arm]
    inside, outside, nocross, notconv = [], [], [], []
    for r in fits:
        f = by.get(r["flight"])
        if f is None:
            continue
        if not r["crossed"]:
            nocross.append(f)
            continue
        e = math.dist(f["true_bounce_xy"], r["bounce_xy"])
        (inside if e <= bar_m else outside).append(f)
        if not r["converged"]:
            notconv.append(f)
    fitted = {r["flight"] for r in fits}
    no_fit = [f for f in res.get("flights", []) if f["flight"] not in fitted]

    groups = {"inside_bar": inside, "outside_bar": outside,
              "no_ground_crossing": nocross, "not_converged": notconv,
              "no_fit_too_few_obs": no_fit,
              "rig_drop_never_presented": res.get("rig_drops", [])}
    out = {"arm": arm, "bar_m": bar_m,
           "n": {k: len(v) for k, v in groups.items()},
           "median": {}, "mannwhitney_p_inside_vs_outside": {}}
    for cov in COVARIATES:
        out["median"][cov] = {
            k: (float(np.median([f[cov] for f in v])) if v and cov in v[0]
                else None) for k, v in groups.items()}
        a = [f[cov] for f in inside if cov in f]
        b = [f[cov] for f in outside if cov in f]
        if len(a) >= 5 and len(b) >= 5:
            out["mannwhitney_p_inside_vs_outside"][cov] = float(
                mannwhitneyu(a, b, alternative="two-sided").pvalue)
    return out


def report(out_dir: Path) -> None:
    """Rebuild every table from the committed per-config JSONs. No refitting."""
    files = sorted(p for p in out_dir.glob("*.json") if p.name != "dt_ab.json")
    rows = []
    for p in files:
        r = json.loads(p.read_text(encoding="utf-8"))
        if "error" in r:
            print(f"{p.stem:26s} SKIPPED {r['error']}")
            continue
        rows.append(r)
    hdr = (f"{'config':26s} {'mount':>5s} {'noise':>5s} {'drop':>4s} "
           f"{'n':>4s} {'<=10cm':>7s} {'all':>6s} {'med m':>7s} {'p90 m':>8s} "
           f"{'1fr':>6s} {'2fr':>6s} {'nox':>4s} {'2D<=10cm':>9s} {'2D med':>7s}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        c, ct = r["provenance"]["config"], r["control_2d"]
        for arm in ("b1", "b2"):
            if arm not in r:
                continue
            a = r[arm]
            print(f"{r['tag'] + '/' + arm:26s} {c['mount_m']:5.1f} "
                  f"{c['pixel_noise']:5.1f} {c['dropout']:4.2f} "
                  f"{r['n_presented']:4d} {a['within_bar_pct_presented']:6.1f}% "
                  f"{a['within_bar_pct_all_truth']:5.1f}% "
                  f"{a['err_median_m']:7.3f} {a['err_p90_m']:8.2f} "
                  f"{a['within_1_frame_pct']:5.1f}% {a['within_2_frame_pct']:5.1f}% "
                  f"{a['n_no_ground_crossing']:4d} "
                  f"{ct['within_bar_pct_presented']:8.1f}% "
                  f"{ct['err_median_m']:7.3f}")
    for r in rows:
        if not r["tag"].startswith("barA"):
            continue
        print(f"\nREJECTS — {r['tag']}")
        print(json.dumps(rejects(r), indent=1))


def main() -> None:
    import multiprocessing as mp

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--suite", default="all",
                    help="all | report | dt-ab | barA | p0anchor | "
                         + " | ".join(SUITES))
    ap.add_argument("--n", type=int, default=500,
                    help="flights SIMULATED per configuration; ~82%% are "
                         "presented, so 500 keeps every arm above n=400")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=11)
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.suite == "report":
        report(out_dir)
        return
    if args.suite == "dt-ab":
        res = dt_ab(args.n, args.seed, args.workers)
        (out_dir / "dt_ab.json").write_text(json.dumps(res, indent=1, default=float),
                                            encoding="utf-8")
        print(json.dumps(res["arms"], indent=1))
        return

    names = list(SUITES) if args.suite == "all" else [args.suite]
    cfgs = [c for nm in names for c in suite_configs(nm, args.n, args.seed)]
    print(f"{len(cfgs)} configurations, {args.workers} workers")
    with mp.Pool(args.workers) as pool:
        for cfg in cfgs:
            res = run_config(cfg, pool)
            (out_dir / f"{cfg['tag']}.json").write_text(
                json.dumps(res, indent=1, default=float), encoding="utf-8")
            if "error" in res:
                print(f"{cfg['tag']:24s} SKIPPED: {res['error']}")
                continue
            for arm in cfg["arms"]:
                a = res[arm]
                print(f"{cfg['tag']:24s} {arm} n={res['n_presented']:4d} "
                      f"<=10cm {a['within_bar_pct_presented']:5.1f}% "
                      f"med {a['err_median_m']:7.3f} m  "
                      f"+/-1fr {a['within_1_frame_pct']:5.1f}% "
                      f"+/-2fr {a['within_2_frame_pct']:5.1f}%  "
                      f"nocross {a['n_no_ground_crossing']:3d} "
                      f"[{res['wall_s']:.0f}s]")
            c = res["control_2d"]
            print(f"{'':24s} 2D control        "
                  f"<=10cm {c['within_bar_pct_presented']:5.1f}% "
                  f"med {c['err_median_m']:7.3f} m")


if __name__ == "__main__":
    main()
