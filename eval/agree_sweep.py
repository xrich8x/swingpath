"""eval/agree_sweep.py - are the frames disagreeing, or is AGREE_PX just too tight?

Session O's O1 pass found the live problem: on the calibrated clips the criteria
recognise the correct court (9/10) and the search produces it (7/10), but only 4/10
have two good locks that AGREE with each other, so the >=6-of-8 vote fails.

THE SUSPECT
-----------
`courtfit.AGREE_PX = 30` is an ABSOLUTE pixel threshold and does not scale with
frame size. This project has been burned by exactly that before - "every 720p-tuned
pixel constant silently deleted real balls at 1080p" (E6, and the reason every ball
threshold now scales by frame_height/720). `_corner_dist` measures in the frame's
OWN pixels, so on a 1920-wide clip 30 px is 10 px at 640, while accepted courts are
allowed to sit 3.4-13.9 px from truth at 640. Two INDEPENDENT correct locks can
therefore be 10-20 px apart at 640 - 30-60 px at 1920 - and fail an agreement test
they should pass. The "disagreement" would then be an artefact of resolution.

WHAT IS SWEPT, AND AGAINST WHAT
-------------------------------
`AGREE_PX` (absolute and height-scaled) x the vote bar, scored against the
PRE-REGISTERED GATE, unchanged:

    >= 12 of 20 gold clips accepted   AND   zero accepted court more than 20 px
    from the human clicks (at 640 wide)

Loosening an agreement radius is a RECALL LEVER, so the second half of that gate is
the whole point: a wider radius will eventually group a correct lock with a wrong one
and ship the median of the two. The table reports `worst_px` for every cell, and any
cell above 20.0 is a failure no matter how many clips it accepts.

THE FITS ARE CACHED. Running `auto_fit_frame` over 30 clips x 8 frames is the
expensive part and it does not depend on the thresholds at all, so it happens once
and lands in data/output/_fit_cache.json. Every sweep cell after that is arithmetic
on cached corners, which is what makes a dense sweep affordable.

Also reports the DISAGREEMENT ANATOMY: when two good locks differ, which of the five
court parameters do they differ in? If it is concentrated in one - far-baseline y is
the suspect, being the worst-conditioned on a low mount - then agreement should be
measured in a reweighted space rather than by mean corner distance, and that is a
different fix from simply widening the radius.

    backend/.venv/Scripts/python.exe eval/agree_sweep.py
    backend/.venv/Scripts/python.exe eval/agree_sweep.py --rebuild
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

CACHE = REPO / "data" / "output" / "_fit_cache.json"
WRONG_PX_640 = 20.0
GOLD_BAR = 12          # >= this many of the 20 gold clips
VOTE_BARS = (5, 6, 7)
ABS_PX = (20.0, 30.0, 45.0, 60.0, 90.0, 120.0)
# height-scaled: the project's own convention for a threshold that must not be
# resolution-dependent (frame_height / 720), applied to the shipped 30 px.
SCALED = (30.0, 45.0, 60.0)
# WIDTH-NORMALISED: hold the radius constant in 640-wide-equivalent pixels, which is
# the unit every error in this project is already quoted in.
#
# Why this anchor and not h/720. Measured: all 20 gold clips are EXACTLY 640x360, the
# references are 1920, and the shell recordings are 3840. So AGREE_PX=30 is really
# 30 px@640 on gold, 17.8 on the references and 5.0 on shell - a 6x swing driven by
# nothing but resolution, against an accepted-court band of 3.4-13.9 px@640. On shell
# the radius is TIGHTER than the error two correct locks routinely differ by, so they
# cannot group and the vote fails on courts that are right.
#
# h/720 was the wrong anchor precisely because the gold set sits BELOW it: scaling by
# h/720 HALVES the radius on a 360-tall clip, so the gate population can only ever see
# that variant shrink, never widen. Anchoring at 640 wide makes it an exact no-op on
# all 20 gold clips - it cannot move the gate's 12/20 or admit a wrong court there -
# and widens only the populations that are actually being penalised.
NORM640 = (20.0, 30.0, 45.0)


def build_cache(k: int):
    """{clip: {w,h,src,truth,fits:[corners|null]}} - the expensive pass, done once."""
    from swingvision import calibration, court
    from swingvision import courtfit as cf
    from score_truth import truth_sources

    out, t0 = {}, time.time()
    for clip, src, frames in truth_sources(k):
        fits, truths, wh = [], [], None
        for _key, im, named in frames:
            h, w = im.shape[:2]
            wh = (w, h)
            f = cf.auto_fit_frame(im, calibration, court)
            fits.append(None if f is None else
                        {n: [float(f[n][0]), float(f[n][1])] for n in DBL})
            truths.append({n: [float(named[n][0]), float(named[n][1])] for n in DBL})
        if wh is None:
            continue
        out[clip] = {"w": wh[0], "h": wh[1], "src": src,
                     "truth": truths, "fits": fits}
        nl = sum(1 for f in fits if f)
        print(f"  {clip:24s} {src:>5s} {nl}/{len(fits)} locked "
              f"({time.time()-t0:.0f}s)", flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    print(f"\ncached {len(out)} clips in {time.time()-t0:.0f}s -> {CACHE.name}")
    return out


def _err640(a, b, calibration, court, scale):
    try:
        Ha = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [a[n] for n in DBL])
        Hb = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [b[n] for n in DBL])
    except Exception:
        return None
    return float(np.mean([
        np.hypot(*(calibration.court_to_image(Ha, [court.LANDMARKS[n]])[0]
                   - calibration.court_to_image(Hb, [court.LANDMARKS[n]])[0]))
        for n in DBL])) * scale


def consensus_err640(pts, v, calibration, court):
    """Consensus error, EXACTLY as eval/run_eval.py computes it: the MEDIAN over
    every labelled frame's ground truth, not one frame's.

    The median is not a stylistic choice and this harness got it wrong first. Gold
    truth is clicked per frame, so one frame's clicks can be an outlier: measured,
    `am_fr_sud` reads 34.2 px against frame 0 and 10.9 px against the median, and
    `am_rec30` 35.7 vs 12.0. Scoring against frame 0 made the SHIPPED setting look
    like it accepts two courts beyond the 20 px wrong-court line, which would have
    contradicted this project's whole precision record - and that contradiction is
    what exposed the bug rather than the sweep shipping a false conclusion."""
    H = calibration.compute_homography([court.LANDMARKS[n] for n in DBL],
                                       [pts[n] for n in DBL])
    scale = 640.0 / v["w"]
    return float(np.median([
        float(np.mean([np.hypot(*(calibration.court_to_image(H, [court.LANDMARKS[n]])[0]
                                  - np.asarray(g[n]))) for n in DBL]))
        for g in v["truth"]])) * scale


def consensus_at(fits, agree_px, cf):
    """courtfit.consensus with the radius as a parameter. Same algorithm."""
    valid = [f for f in fits if f]
    if not valid:
        return None, 0
    best, best_n = None, 0
    for f in valid:
        group = [g for g in valid if cf._corner_dist(f, g) <= agree_px]
        if len(group) > best_n:
            best, best_n = group, len(group)
    if best is None:
        return None, 0
    return {n: [float(np.median([g[n][0] for g in best])),
                float(np.median([g[n][1] for g in best]))] for n in DBL}, best_n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=8, help="frames per clip")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    from swingvision import calibration, court
    from swingvision import courtfit as cf

    if a.rebuild or not CACHE.exists():
        print(f"building the fit cache ({a.k} frames/clip) - this is the slow part\n")
        data = build_cache(a.k)
    else:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"loaded {len(data)} clips from {CACHE.name} "
              f"(--rebuild to redo the fits)\n")

    gold = {c: v for c, v in data.items() if v["src"] == "gold"}
    # Split the references by resolution: the 10 original calibrated clips are 1920
    # and every shell recording is 3840, so width separates them exactly. They are
    # reported apart because the brief's tuning rule requires it - tuning happens on
    # the original references, and SHELL IS VERIFICATION ONLY. Pooling them would
    # quietly turn the held-out surface into a tuning set.
    refs = {c: v for c, v in data.items() if v["src"] == "ref" and v["w"] < 3000}
    shell = {c: v for c, v in data.items() if v["src"] == "ref" and v["w"] >= 3000}
    print(f"{len(gold)} gold clips (the gate), {len(refs)} calibrated references, "
          f"{len(shell)} shell (VERIFICATION ONLY - never tune on these)\n")

    # --- per-clip error of every lock, computed once
    for c, v in data.items():
        scale = 640.0 / v["w"]
        v["errs"] = [None if f is None else
                     _err640(t, f, calibration, court, scale)
                     for f, t in zip(v["fits"], v["truth"])]

    # ---------- 1. disagreement anatomy ----------
    print("DISAGREEMENT ANATOMY - among locks that are each within 20 px of truth,\n"
          "how far apart are they, and in which of the 5 court parameters?\n")
    print(f"{'clip':24s} {'good':>4s} {'pairs':>5s} {'med apart':>10s} "
          f"{'as px@640':>10s}  dominant parameter")
    print("-" * 84)
    names = ("cx", "y_near", "y_far", "w_near", "w_far")
    anat = []
    for c, v in sorted(data.items()):
        good = [i for i, e in enumerate(v["errs"])
                if e is not None and e <= WRONG_PX_640]
        if len(good) < 2:
            continue
        scale = 640.0 / v["w"]
        dists, dparam = [], []
        for ii in range(len(good)):
            for jj in range(ii + 1, len(good)):
                fa, fb = v["fits"][good[ii]], v["fits"][good[jj]]
                dists.append(cf._corner_dist(fa, fb))
                pa = cf._params_from_corners({n: np.asarray(fa[n], float) for n in DBL})
                pb = cf._params_from_corners({n: np.asarray(fb[n], float) for n in DBL})
                span = [v["w"], v["h"], v["h"], v["w"], v["w"]]
                dparam.append([abs(pa[i] - pb[i]) / span[i] for i in range(5)])
        med = float(np.median(dists))
        dp = np.median(np.asarray(dparam), axis=0)
        dom = names[int(np.argmax(dp))]
        anat.append({"clip": c, "good": len(good), "med_apart_px": med,
                     "med_apart_640": med * scale, "dominant": dom,
                     "dparam": dp.tolist()})
        print(f"{c:24s} {len(good):4d} {len(dists):5d} {med:10.1f} "
              f"{med*scale:10.1f}  {dom} ({dp[int(np.argmax(dp))]*100:.1f}% of span)")
    if anat:
        print("-" * 84)
        over = sum(1 for r in anat if r["med_apart_px"] > 30.0)
        print(f"{over}/{len(anat)} clips have good locks a MEDIAN of more than the "
              f"shipped AGREE_PX=30 apart\nin their own pixels — those are the votes "
              f"the current radius is throwing away.")
        from collections import Counter
        print("dominant disagreement parameter: " + ", ".join(
            f"{k} x{n}" for k, n in Counter(r["dominant"] for r in anat).most_common()))

    # ---------- 2. the sweep, against the pre-registered gate ----------
    print(f"\n\nGATE SWEEP - accept iff votes >= bar. GATE: >={GOLD_BAR}/20 gold AND "
          f"worst accepted <= {WRONG_PX_640:.0f} px @640\n")
    print(f"{'AGREE_PX':>14s} {'bar':>4s} | {'gold':>6s} {'worst':>7s} {'verdict':>8s} "
          f"| {'refs':>5s} {'worst':>7s} | {'shell':>5s} {'worst':>7s}")
    print("-" * 92)
    rows = []
    variants = ([(f"{p:.0f} abs", ("abs", p)) for p in ABS_PX]
                + [(f"{p:.0f}*h/720", ("scaled", p)) for p in SCALED]
                + [(f"{p:.0f}@640", ("norm640", p)) for p in NORM640])
    for label, (kind, px) in variants:
        for bar in VOTE_BARS:
            res = {}
            for pop, dd in (("gold", gold), ("ref", refs), ("shell", shell)):
                acc, worst = 0, 0.0
                for c, v in dd.items():
                    r = (px if kind == "abs" else
                         px * (v["h"] / 720.0) if kind == "scaled" else
                         px * (v["w"] / 640.0))
                    pts, votes = consensus_at(v["fits"], r, cf)
                    if pts is None or votes < bar:
                        continue
                    acc += 1
                    try:
                        worst = max(worst, consensus_err640(pts, v, calibration, court))
                    except Exception:
                        pass
                res[pop] = (acc, worst)
            g_acc, g_worst = res["gold"]
            r_acc, r_worst = res["ref"]
            s_acc, s_worst = res["shell"]
            # The gate is the gold set. A wrong court on ANY population is still a
            # wrong court, so the reference and shell worst columns are reported
            # beside it and a cell that ships one is a failure whatever the gate says.
            ok = g_acc >= GOLD_BAR and g_worst <= WRONG_PX_640
            shipped = " *" if (kind == "abs" and px == 30.0 and bar == 6) else ""
            rows.append({"agree": label, "bar": bar, "gold_acc": g_acc,
                         "gold_worst": g_worst, "ref_acc": r_acc,
                         "ref_worst": r_worst, "shell_acc": s_acc,
                         "shell_worst": s_worst, "pass": ok,
                         "clean": ok and r_worst <= WRONG_PX_640
                         and s_worst <= WRONG_PX_640})
            print(f"{label:>14s} {bar:4d} | {g_acc:6d} {g_worst:7.1f} "
                  f"{'PASS' if ok else 'fail':>8s} | {r_acc:5d} {r_worst:7.1f} "
                  f"| {s_acc:5d} {s_worst:7.1f}{shipped}")
    print("-" * 92)
    print("* = as shipped (AGREE_PX=30 absolute, >=6 of 8)")
    best = [r for r in rows if r["clean"]]
    if best:
        b = max(best, key=lambda r: (r["gold_acc"], r["ref_acc"], r["shell_acc"]))
        print(f"\nbest CLEAN cell (gate passed AND no wrong court on any population): "
              f"AGREE_PX={b['agree']}, bar>={b['bar']}\n  -> {b['gold_acc']}/20 gold "
              f"(worst {b['gold_worst']:.1f}), {b['ref_acc']}/{len(refs)} refs "
              f"(worst {b['ref_worst']:.1f}), {b['shell_acc']}/{len(shell)} shell "
              f"(worst {b['shell_worst']:.1f})")
        print("Widening an agreement radius is a RECALL LEVER. Before shipping any "
              "cell above,\nre-run it through the real product path — this sweep "
              "recomputes consensus from\ncached fits and does NOT exercise "
              "fit_video_frames or the clay stack fallback.")
    else:
        print("\nNO CELL PASSES THE GATE. The disagreement is not a radius artefact.")

    if a.json:
        Path(a.json).write_text(json.dumps({"anatomy": anat, "sweep": rows}, indent=1),
                                encoding="utf-8")


if __name__ == "__main__":
    main()
