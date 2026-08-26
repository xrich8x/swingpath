"""eval/seed_reach.py - P1: where does the TRUE court die inside autodetect?

Session P step 1 (docs/archive/sessions/SESSION_P_search_reach.md). Session O established
that the scoring criteria recognise the correct court on 19 of 20 clips and the
search produces it on only 10 - so the failure is upstream of scoring. This finds
out where.

WHY A TRACE AND NOT ANOTHER SWEEP
----------------------------------
"The search does not produce the true court" has three causes with three different
fixes, and they are indistinguishable from the outside:

    no seed lands within refine reach of truth   -> reachability   -> P2 / P3
    a seed IS in reach but refine walks away     -> trapped optimiser
    a near candidate survives refine, a gate     -> that gate
      then rejects it

So: rebuild the exact seed set `autodetect` builds, find the seed NEAREST the human
court, and follow that one seed through every stage - even when it never ranks high
enough to be tried, which is itself a kill reason worth naming.

The output is a per-stage kill table in the shape of Session M's chain attribution,
which is the tool that worked the last time this project had to attribute a loss
across a pipeline rather than argue about it.

IT ALSO PREVIEWS P2, because that costs one extra refine per seed. Every seed is
refined twice: once at the shipped absolute `max_move_px=55`, and once at
`55*(w/640)`. On a 640-wide clip those are identical by construction; on 4K the
second can travel 6x further. If reach is the cause, the difference shows up here
before any product code is touched.

GROUND TRUTH IS HUMAN ONLY - the `"_exact": true` calibrations. Per the brief's
tuning rule the shell clips are VERIFICATION ONLY and are reported separately;
`mpc_tuesday` is excluded from truth entirely (its two independent labels disagree
by 25.4 px@640, above the wrong-court line).

    backend/.venv/Scripts/python.exe eval/seed_reach.py
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

TOPK = 12               # autodetect's own cap on how many seeds get refined
EXCLUDE_TRUTH = {"mpc_tuesday_p01", "mpc_tuesday_p07"}   # labels disagree 25.4 px

# The stages a candidate must survive, in the order autodetect applies them.
STAGES = ("in top-k", "refine", "degeneracy", "g>=.33", "sufficiency",
          "pose", "structure", "verify", "camera re-fit")


def build_seeds(frame, calibration, court, cf, dt, cos2, sin2, w, h, tol):
    """The EXACT seed set autodetect builds, in its own order.

    Reproduced rather than called because autodetect returns only a winner - there
    is no way to ask it what happened to a candidate it discarded. Mirrors
    courtfit.autodetect lines 645-668; if that changes, this drifts and the numbers
    here quietly stop describing the shipped search."""
    court_pts = [court.LANDMARKS[n] for n in DBL]
    prior = cf._load_prior()
    athr = 0.80

    coarse = cf.COARSE_GRID
    ax = tuple(np.asarray(v) * (w if i in (0, 3, 4) else h)
               for i, v in enumerate(coarse))
    ranked = cf._scan(ax, calibration, court, court_pts, dt, cos2, sin2,
                      w, h, tol, athr, prior)
    if prior:
        ranked += cf._prior_seeds(prior, calibration, court, court_pts,
                                  dt, cos2, sin2, w, h, tol, athr)
    ranked += cf._lowcam_seeds(calibration, court, court_pts,
                               dt, cos2, sin2, w, h, tol, athr)
    ranked.sort(key=lambda t: t[0], reverse=True)

    steps = [(coarse[i][1] - coarse[i][0]) * (w if i in (0, 3, 4) else h)
             for i in range(5)]
    seeds = []
    for t in ranked[:3]:
        p = t[3]
        local = tuple(np.array([p[i] - steps[i] / 2, p[i], p[i] + steps[i] / 2])
                      for i in range(5))
        seeds += cf._scan(local, calibration, court, court_pts, dt, cos2, sin2,
                          w, h, tol, athr, prior)
    seeds += ranked
    seeds.sort(key=lambda t: t[0], reverse=True)
    return seeds, prior


def trace_frame(im, named, calibration, court, cf):
    """Follow the truth-nearest seed through every stage. Returns a dict."""
    mf = calibration.court_line_mask
    dt, cos2, sin2, w, h, lines = cf._precompute(im, calibration, mf)
    tol = max(2.0, w * 0.006)
    scale = 640.0 / w
    court_pts = [court.LANDMARKS[n] for n in DBL]
    txy = np.array([named[n] for n in DBL], float)

    seeds, prior = build_seeds(im, calibration, court, cf,
                               dt, cos2, sin2, w, h, tol)
    if not seeds:
        return None

    # which seed is nearest the human court, and where does it sit in the ranking?
    dists = []
    for _r, _g, _nl, p, _m in seeds:
        c = cf._corners(*p)
        cand = np.array([c[n] for n in DBL], float)
        dists.append(float(np.mean(np.hypot(*(cand - txy).T))) * scale)
    j = int(np.argmin(dists))
    seed_err = dists[j]
    p = seeds[j][3]

    # WHY is that seed ranked where it is? `rank = g * exp(-0.5*maha/PRIOR_TEMP)`
    # (courtfit._score_seed), so a seed is demoted for being an implausible CAMERA
    # POSE regardless of how well it fits the paint. autodetect's own comment says
    # the learned prior "only knows elevated framings" and that a court-level camera
    # "fails the maha test through no fault of its own" - and it patches that in the
    # ACCEPT gate via pose_ok's escape hatch. The RANKING never got the same patch,
    # so the demotion still happens before anything reaches that gate.
    # Re-rank the same seeds by g alone to see what the prior weight is costing.
    truth = seeds[j]
    out_rank = {}
    for tag, key in (("g_only", lambda t: t[1]),
                     ("shipped", lambda t: t[0])):
        better = sum(1 for t in seeds if key(t) > key(truth))
        out_rank[tag] = better

    out = {"w": w, "h": h, "n_seeds": len(seeds), "seed_err": seed_err,
           "seed_rank": j, "in_topk": j < TOPK,
           "maha": float(truth[4]), "g_seed": float(truth[1]),
           "rank_g_only": out_rank["g_only"],
           "in_topk_g_only": out_rank["g_only"] < TOPK,
           "reach_shipped": 55.0 * scale, "reach_norm": 55.0 * (w / 640.0) * scale}

    # --- refine that seed, at the shipped reach and at a 640-normalised one
    for tag, mv in (("shipped", 55.0), ("norm", 55.0 * (w / 640.0))):
        try:
            Hs, ref, _ = calibration.refine_homography_bounded(
                im, cf._corners(*p), max_move_px=mv, mask_fn=mf)
        except Exception:
            out[f"refined_err_{tag}"] = None
            continue
        cand = np.array([ref[n] for n in DBL], float)
        out[f"refined_err_{tag}"] = float(
            np.mean(np.hypot(*(cand - txy).T))) * scale
        if tag == "shipped":
            out["_Hs"], out["_ref"] = Hs, ref

    Hs, ref = out.pop("_Hs", None), out.pop("_ref", None)
    if Hs is None:
        out["died"] = "refine"
        return out

    # --- the accept conjunction, term by term, in autodetect's own order
    p5 = cf._params_from_corners(ref)
    g, nl, _ev = cf._ori_detail(Hs, calibration, court, dt, cos2, sin2,
                                w, h, tol, 0.80)
    st, st_m, st_ev, n_across, n_len = cf._structure(Hs, lines, calibration,
                                                     dt, w, h, tol)
    maha = cf._maha(p5, w, h, prior)
    sufficient = (st_m >= 4 and n_across >= 2 and n_len >= 2) or nl >= 5
    pose_ok = (maha <= cf.PRIOR_MAHA_MAX
               or (st >= 0.70 and st_m >= 5 and n_across >= 2 and n_len >= 2))

    terms = {
        "in top-k": out["in_topk"],
        "refine": out.get("refined_err_shipped") is not None,
        "degeneracy": not (p5[3] * 2.0 < 0.15 * w or abs(p5[1] - p5[2]) < 0.06 * h),
        "g>=.33": g >= 0.33,
        "sufficiency": sufficient,
        "pose": pose_ok,
        "structure": st >= cf.STRUCT_MIN or st_ev < 3,
        "verify": bool(calibration.verify_court(im, Hs).ok),
    }
    cam = cf._cam_refine(im, ref, calibration, court, dt, w, h)
    terms["camera re-fit"] = cam is not None

    out["terms"] = terms
    out["g"] = g
    out["st"] = st
    out["died"] = next((k for k in STAGES if not terms.get(k, True)), None)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    # Both populations: the 20 GOLD clips (which ARE the gate, and carry per-frame
    # clicked keypoints) and the 20 human-calibrated references including shell. An
    # attribution run over only the references would describe the clips the gate does
    # not judge.
    srcs = truth_sources(a.frames)
    if a.clips:
        srcs = [s for s in srcs if s[0] in set(a.clips)]
    print(f"{len(srcs)} clips with human truth, {a.frames} frames each.\n"
          f"Following the seed NEAREST the human court through every stage.\n")
    print(f"{'clip':22s} {'px':>5s} {'seeds':>6s} {'nearest':>8s} {'reach':>6s} "
          f"{'rank':>5s} {'after refine':>13s}  died at")
    print("-" * 96)

    rows, t0 = [], time.time()
    for clip, src, frames in srcs:
        per = []
        for _key, im, named in frames:
            if not all(n in named for n in DBL):
                continue
            r = trace_frame(im, named, calibration, court, cf)
            if r:
                per.append(r)
        if not per:
            continue
        med = lambda k: float(np.median([x[k] for x in per if x.get(k) is not None])) \
            if any(x.get(k) is not None for x in per) else None    # noqa: E731
        died = [x.get("died") for x in per]
        # the stage that killed it on the most frames
        common = max(set(died), key=died.count) if died else None
        row = {"clip": clip, "w": per[0]["w"], "n_seeds": per[0]["n_seeds"],
               "seed_err": med("seed_err"), "reach": med("reach_shipped"),
               "reach_norm": med("reach_norm"), "rank": med("seed_rank"),
               "in_topk": sum(1 for x in per if x["in_topk"]),
               "refined": med("refined_err_shipped"),
               "refined_norm": med("refined_err_norm"),
               "maha": med("maha"), "g_seed": med("g_seed"),
               "rank_g": med("rank_g_only"),
               "topk_g": sum(1 for x in per if x["in_topk_g_only"]),
               "died": common, "frames": len(per), "src": src,
               "excluded": clip in EXCLUDE_TRUTH,
               "shell": per[0]["w"] >= 3000}
        rows.append(row)
        rf = "-" if row["refined"] is None else f"{row['refined']:.1f}"
        flag = "  (label excluded)" if row["excluded"] else ""
        print(f"{clip:22s} {row['w']:5d} {row['n_seeds']:6d} "
              f"{row['seed_err']:7.1f} {row['reach']:6.1f} {row['rank']:5.0f} "
              f"{rf:>13s}  {common or 'SURVIVED'}{flag}", flush=True)

    print("-" * 92)
    live = [r for r in rows if not r["excluded"]]
    print(f"{len(rows)} clips traced in {time.time()-t0:.0f}s "
          f"({len(rows)-len(live)} excluded from truth).\n")

    # --- the kill table: which stage loses the true court, and how often
    from collections import Counter
    for label, pop in (
            ("GOLD - the gate population", [r for r in live if r["src"] == "gold"]),
            ("ORIGINAL REFERENCES (1920)",
             [r for r in live if r["src"] == "ref" and not r["shell"]]),
            ("SHELL (verification only - never tune on these)",
             [r for r in live if r["shell"]])):
        if not pop:
            continue
        print(f"{label} - {len(pop)} clips")
        c = Counter(r["died"] or "SURVIVED" for r in pop)
        for stage in ("SURVIVED",) + STAGES:
            if c.get(stage):
                bar = "#" * c[stage]
                print(f"    {stage:14s} {c[stage]:3d}  {bar}")
        print()

    # --- P2 preview: does a 640-normalised refine reach change anything?
    unreach = [r for r in live if r["seed_err"] > r["reach"]]
    print(f"REACHABILITY: on {len(unreach)}/{len(live)} clips the nearest seed is "
          f"FARTHER from truth\nthan the shipped refine can travel.")
    if unreach:
        n2 = [r for r in unreach if r["seed_err"] <= r["reach_norm"]]
        print(f"  a 640-normalised reach would put {len(n2)} of those {len(unreach)} "
              f"in range.")
        imp = [r for r in unreach
               if r["refined_norm"] is not None and r["refined"] is not None
               and r["refined_norm"] < r["refined"] - 1.0]
        print(f"  refining at the normalised bound lands closer to truth on "
              f"{len(imp)}/{len(unreach)}.")
    # --- is the PRIOR WEIGHT what demotes the true court out of the top-k?
    print(f"\n\nTHE RANKING  `rank = g * exp(-0.5*maha/{cf.PRIOR_TEMP})`  vs  `g` alone\n")
    print(f"{'clip':22s} {'maha':>6s} {'rank now':>9s} {'by g':>7s}  into top-"
          f"{TOPK}?")
    print("-" * 68)
    won = already = 0
    for r in sorted(live, key=lambda r: r["rank_g"]):
        if r["rank"] < TOPK:
            v = "already in"; already += 1
        elif r["rank_g"] < TOPK:
            v = "YES"; won += 1
        else:
            v = "no"
        print(f"{r['clip']:22s} {r['maha']:6.1f} {r['rank']:9.0f} "
              f"{r['rank_g']:7.0f}  {v}")
    print("-" * 68)
    print(f"Dropping the prior weight from the RANKING promotes the true court into "
          f"the top-{TOPK}\non {won}/{len(live)} clips ({already} were already in).")
    print("\nautodetect ALREADY patches this prior for low mounts - but only in the "
          "ACCEPT gate\n(`pose_ok`'s escape hatch). The ranking that decides which "
          "seeds ever reach that\ngate never got the same patch.")

    print("\nA stage that kills the true court on many clips is the fix target. "
          "If the kills\nare spread evenly, no single change helps and the brief's "
          "stopping rule applies.")

    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
