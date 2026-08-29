"""Execute the PRE-REGISTERED gate in
docs/evidence/far-player-motion-contrast-hypothesis.md, section
"Pre-registered gate, before anything is built".

THIS SCRIPT DESIGNS NOTHING. The bar was written 2026-08-29 before any code and is
reproduced verbatim below. Rule 2: a failed gate stays failed.

    Population   P0-3's yt_match40 far-end contacts, restricted to those where the
                 POST-HOC crop192@640_x (yolo11x) arm found a far-sized non-near
                 person. That reference is POST-HOC and is labelled POST-HOC in
                 every number this script prints. Zero new human labelling.
    Method       eval/movers.py UNMODIFIED, foot_points as written. No homography
                 is touched anywhere in this file: yt_match40's calibration is
                 confirmed wrong (T23) so nothing may route through it.
    Metric       distance from the NEAREST returned foot point to the known
                 far-player box centroid, in box-heights.
    BAR          median <= 1.5 box-heights on >= 10 of 15 frames, AND the
                 random-blob null control FAILS that same bar.
    Kill         if the nearest-blob median exceeds 1.5 box-heights, or the random
                 control clears the bar about as often, the idea is dead.

WHAT EVERY NUMBER IS MEASURED AGAINST (rule 1): a POST-HOC far-player box taken
from P0-3's crop192@640_x pose detections - a model-derived reference, NOT a human
label. It is the closest thing to a far-player position that exists without new
labelling, and it is why nothing here may be quoted as accuracy.

THE NULL CONTROL IS THE POINT. movers' size/aspect filters pass a median ~9 blobs
per frame before MAX_PLAYERS caps them at 4, so "some blob is close" is nearly
guaranteed by chance. If random passes too, the real arm has proved nothing
regardless of its own number.

THE CONTRAST RIDER HAS NO GATE AND CANNOT PASS OR FAIL ANYTHING. Nobody has ever
measured far-player contrast on this footage, so there was nothing to pre-register.
It ships as a descriptive statistic, explicitly labelled characterisation.
Inventing a bar after seeing the number would be a rule-2 violation.

Two facts to carry forward whatever the outcome, both recorded in the evidence file:
  1. eval/movers.py lives in eval/, NOT in the shipped package, so the mobile-
     viability audit's "every cv2 symbol used exists in the mobile builds" does
     NOT cover it. Re-checking its calls is a prerequisite line item before any
     build - not done here.
  2. clean_plate needs a rolling buffer of up to PLATE_MAX = 31 frames. Harmless
     for the shipped record-then-process design; fatal for any live/real-time use,
     where it would be rebuilt, not ported.

Run from the repo root:
  ./backend/.venv/Scripts/python.exe eval/far_player_motion_gate.py \
      --probe data/output/p0_3_probe_yt_match40.json \
      --video data/incoming/Hardcourt/yt_match40.mp4 \
      --arm crop192@640_x --seed 0 \
      --out data/output/far_player_motion_gate.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import movers  # noqa: E402  - eval/movers.py, imported UNMODIFIED

# --- pre-registered constants. Do not tune. -------------------------------------
BAR_REL_H = 1.5          # box-heights
BAR_N_FRAMES = 10        # of 15
POP_N = 15               # the gate's own denominator

# movers' intended temporal footprint: clean_plate subsamples to PLATE_MAX = 31, so
# a 31-frame window centred on the contact is exactly one plate with no subsampling.
WINDOW_HALF = 15

# Contrast rider: the surround is the box grown by this many box-heights, minus the
# box itself. Descriptive only - no threshold is attached to it anywhere.
SURROUND_GROW = 1.0


def _edge_dist(box, pt):
    """Identical to tools/p0_3_tolerance_sweep.py::_edge_dist - the population must
    be selected by the same rule that produced the 15/25 figure."""
    x1, y1, x2, y2 = box
    dx = max(x1 - pt[0], 0.0, pt[0] - x2)
    dy = max(y1 - pt[1], 0.0, pt[1] - y2)
    return math.hypot(dx, dy)


def build_population(probe, arm):
    """The gate's population, reproduced by the sweep's own selection rule.

    NOTE A DISCREPANCY IN THE GATE DOC, recorded rather than silently resolved: it
    says "the 15 of 25 contacts ... within 1.5 box-heights". In the sweep JSON those
    are two different sets - 15 is `far_sized_candidate_found_anywhere_in_crop`, and
    `by_rel_box_h["1.5"]` is 14. The bar is written ">= 10 of 15", so 15 is the
    load-bearing denominator; the <=1.5 subset is reported alongside.
    """
    out = []
    for r in probe["contacts"]:
        pt = r["ball_px_at_contact"]
        a = r["arms"][arm]
        cands = [e for e in a["accepted"] + a["rejected"]
                 if e["small_enough"] and e["not_the_near_player"]]
        if not cands:
            continue
        e = min(cands, key=lambda c: _edge_dist(c["box"], pt))
        box = [float(v) for v in e["box"]]
        out.append({
            "shot_id": r["shot_id"],
            "source_frame": int(r["source_frame"]),
            "ball_px_at_contact": [float(pt[0]), float(pt[1])],
            "ref_box_POST_HOC": box,
            "ref_box_h_px": float(e["box_h_px"]),
            "ref_centroid_POST_HOC": [(box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0],
            "ref_score": e.get("score"),
            "anchor_edge_dist_px": round(_edge_dist(box, pt), 2),
            "anchor_edge_dist_rel_h": round(_edge_dist(box, pt) / float(e["box_h_px"]), 3),
            "near_player_box_full_frame": r.get("near_player_box_full_frame"),
            "contact_on_near_player": r.get("contact_on_near_player"),
        })
    return out


def _windows(pop, n_frames):
    return [(max(0, c["source_frame"] - WINDOW_HALF),
             min(n_frames - 1, c["source_frame"] + WINDOW_HALF)) for c in pop]


def contrast_stats(frame_bgr, box, grow=SURROUND_GROW):
    """DESCRIPTIVE ONLY. Luminance / chroma of the far-player box against the court
    ring around it, in CIELAB. No bar, no verdict, no pass, no fail."""
    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    bh = y2 - y1
    g = int(round(grow * bh))
    sx1, sy1 = max(0, x1 - g), max(0, y1 - g)
    sx2, sy2 = min(w, x2 + g), min(h, y2 + g)

    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    # OpenCV 8-bit Lab: L in 0..255 (=L*/100*255), a,b in 0..255 (= a*+128)
    lab[:, :, 0] *= 100.0 / 255.0
    lab[:, :, 1:] -= 128.0

    inner = lab[y1:y2, x1:x2].reshape(-1, 3)
    ring_mask = np.ones((sy2 - sy1, sx2 - sx1), bool)
    ring_mask[y1 - sy1:y2 - sy1, x1 - sx1:x2 - sx1] = False
    ring = lab[sy1:sy2, sx1:sx2][ring_mask]
    if len(inner) < 4 or len(ring) < 4:
        return None

    mi, mr = inner.mean(0), ring.mean(0)
    dL = float(mi[0] - mr[0])
    dchroma = float(math.hypot(mi[1] - mr[1], mi[2] - mr[2]))
    dE = float(np.linalg.norm(mi - mr))
    # Signal-to-noise form: |dL| over the ring's own luminance spread. A player is
    # only "in relative contrast to the court" if he stands out against how varied
    # that court patch already is.
    ring_sd_L = float(ring[:, 0].std())
    return {
        "box_mean_L": round(float(mi[0]), 2),
        "surround_mean_L": round(float(mr[0]), 2),
        "delta_L": round(dL, 2),
        "abs_delta_L": round(abs(dL), 2),
        "delta_chroma_ab": round(dchroma, 2),
        "delta_E": round(dE, 2),
        "surround_sd_L": round(ring_sd_L, 2),
        "abs_delta_L_over_surround_sd": round(abs(dL) / max(ring_sd_L, 1e-6), 2),
        "n_px_box": int(len(inner)),
        "n_px_surround": int(len(ring)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--arm", default="crop192@640_x")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--random-repeats", type=int, default=1000,
                    help="extra seeded draws for the null control's own stability; "
                         "the PRE-REGISTERED control is the single draw at --seed")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.probe, "r", encoding="utf-8") as f:
        probe = json.load(f)
    pop = build_population(probe, args.arm)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {args.video}")
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    wins = _windows(pop, n_frames)

    # Sequential decode only (AVAssetReader-shaped): one forward pass, grab() through
    # and retrieve() only what a window needs. Frames are dropped as soon as the last
    # window that wants them has been processed - 15 windows x 31 frames of 720p held
    # at once would be >1 GB.
    order = sorted(range(len(pop)), key=lambda i: wins[i][0])
    held, results = {}, {}
    cursor = 0
    last_needed = max(w[1] for w in wins) if wins else -1
    i = 0
    print(f"decoding {args.video}: {n_frames} frames, {fps:.2f} fps; "
          f"{len(pop)} windows, {2 * WINDOW_HALF + 1} frames each", flush=True)
    while i <= last_needed:
        if not cap.grab():
            break
        need = any(wins[k][0] <= i <= wins[k][1] for k in order[cursor:])
        if need:
            ok, fr = cap.retrieve()
            if ok:
                held[i] = fr
        # process any window now fully decoded
        while cursor < len(order) and wins[order[cursor]][1] <= i:
            k = order[cursor]
            a, b = wins[k]
            ims = [held[j] for j in range(a, b + 1) if j in held]
            results[k] = _score_window(pop[k], ims, a)
            cursor += 1
            still = min((wins[order[c]][0] for c in range(cursor, len(order))),
                        default=10 ** 9)
            for j in list(held):
                if j < still:
                    del held[j]
        i += 1
    cap.release()

    rng = np.random.default_rng(args.seed)
    rows = []
    for k, c in enumerate(pop):
        r = dict(c)
        r.update(results.get(k, {"error": "window not decoded"}))
        blobs = r.get("blobs_at_contact_frame") or []
        if blobs:
            j = int(rng.integers(len(blobs)))
            r["random_pick_index"] = j
            r["random_dist_px"] = round(blobs[j]["dist_px"], 2)
            r["random_dist_rel_h"] = round(blobs[j]["dist_px"] / r["ref_box_h_px"], 3)
        else:
            r["random_pick_index"] = None
            r["random_dist_px"] = None
            r["random_dist_rel_h"] = None
        rows.append(r)

    def _verdict(key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        n_within = sum(1 for v in vals if v <= BAR_REL_H)
        med = float(np.median(vals)) if vals else None
        return {
            "n_with_a_blob": len(vals),
            "median_rel_h": round(med, 3) if med is not None else None,
            "n_within_1.5_box_heights": n_within,
            "n_population": POP_N,
            "passes_bar": bool(med is not None and med <= BAR_REL_H
                               and n_within >= BAR_N_FRAMES),
        }

    nearest = _verdict("nearest_dist_rel_h")
    random_ctl = _verdict("random_dist_rel_h")

    # Null control stability: the PRE-REGISTERED control is the single seeded draw
    # above. This repeat is descriptive - it says whether that draw was a fluke.
    rep = []
    r2 = np.random.default_rng(args.seed + 1)
    for _ in range(args.random_repeats):
        vals = []
        for r in rows:
            blobs = r.get("blobs_at_contact_frame") or []
            if blobs:
                vals.append(blobs[int(r2.integers(len(blobs)))]["dist_px"] / r["ref_box_h_px"])
        if vals:
            rep.append((float(np.median(vals)), sum(1 for v in vals if v <= BAR_REL_H)))
    rand_repeat = None
    if rep:
        meds = np.array([x[0] for x in rep])
        cnts = np.array([x[1] for x in rep])
        rand_repeat = {
            "repeats": len(rep),
            "median_of_medians_rel_h": round(float(np.median(meds)), 3),
            "median_rel_h_p5_p95": [round(float(np.percentile(meds, 5)), 3),
                                    round(float(np.percentile(meds, 95)), 3)],
            "mean_n_within_1.5": round(float(cnts.mean()), 2),
            "pct_of_draws_that_pass_the_bar": round(
                100.0 * float(((meds <= BAR_REL_H) & (cnts >= BAR_N_FRAMES)).mean()), 1),
        }

    sub14 = [r for r in rows if r["anchor_edge_dist_rel_h"] <= 1.5]
    v14 = [r["nearest_dist_rel_h"] for r in sub14 if r.get("nearest_dist_rel_h") is not None]

    contrasts = [r["contrast_DESCRIPTIVE"] for r in rows if r.get("contrast_DESCRIPTIVE")]

    def _dist(key):
        v = np.array([c[key] for c in contrasts], float)
        if not len(v):
            return None
        return {"n": int(len(v)), "min": round(float(v.min()), 2),
                "p25": round(float(np.percentile(v, 25)), 2),
                "median": round(float(np.median(v)), 2),
                "p75": round(float(np.percentile(v, 75)), 2),
                "max": round(float(v.max()), 2),
                "mean": round(float(v.mean()), 2)}

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        commit = commit + ("-dirty" if dirty else "")
    except Exception:
        commit = "unknown"

    out = {
        "experiment": "far-player MOTION gate, pre-registered "
                      "docs/evidence/far-player-motion-contrast-hypothesis.md",
        "measured_against": (
            "a POST-HOC far-player box from P0-3's crop192@640_x (yolo11x) pose "
            "detections - a MODEL-DERIVED reference, not a human label. No number "
            "here is accuracy against ground truth."),
        "homography": "NEVER TOUCHED. movers.feet_in_court and calibration.image_to_court "
                      "are not called anywhere in this run (T23: yt_match40's H is wrong).",
        "pre_registered_bar": {
            "metric": "distance from the NEAREST movers.foot_points foot point to the "
                      "POST-HOC far-player box centroid, in box-heights",
            "bar": f"median <= {BAR_REL_H} box-heights on >= {BAR_N_FRAMES} of {POP_N} "
                   f"frames, AND the random-blob control fails the same bar",
        },
        "resolved_config": {
            "probe": args.probe, "video": args.video, "arm": args.arm,
            "seed": args.seed, "window_half_frames": WINDOW_HALF,
            "window_frames": 2 * WINDOW_HALF + 1,
            "movers_WORK_W": movers.WORK_W, "movers_PLATE_MAX": movers.PLATE_MAX,
            "movers_MAX_PLAYERS": movers.MAX_PLAYERS,
            "movers_AREA_MIN_FRAC": movers.AREA_MIN_FRAC,
            "movers_AREA_MAX_FRAC": movers.AREA_MAX_FRAC,
            "movers_MIN_H_OVER_W": movers.MIN_H_OVER_W,
            "movers_modified": False,
            "surround_grow_box_heights": SURROUND_GROW,
            "random_repeats_descriptive": args.random_repeats,
        },
        "provenance": {
            "git_commit": commit, "cv2": cv2.__version__, "numpy": np.__version__,
            "video_frames": n_frames, "video_fps": round(fps, 3),
            "probe_provenance": probe.get("provenance"),
            "probe_calibration_sha": probe.get("calibration", {}).get("keypoints_sha256"),
        },
        "population": {
            "n_far_contacts_total": len(probe["contacts"]),
            "n_selected": len(pop),
            "selection": f"nearest small_enough & not_the_near_player candidate in "
                         f"{args.arm}; POST-HOC",
            "doc_discrepancy": (
                "the gate doc says '15 ... within 1.5 box-heights'; in the sweep JSON "
                "15 is found-anywhere and by_rel_box_h['1.5'] is 14. The bar's "
                "denominator 15 is load-bearing, so found-anywhere is primary and the "
                "14-frame <=1.5 subset is reported alongside."),
        },
        "RESULT_nearest_blob": nearest,
        "RESULT_random_blob_null_control": random_ctl,
        "random_control_stability_DESCRIPTIVE": rand_repeat,
        "subset_anchor_within_1.5_box_heights": {
            "n": len(sub14),
            "median_rel_h": round(float(np.median(v14)), 3) if v14 else None,
            "n_within_1.5_box_heights": sum(1 for v in v14 if v <= BAR_REL_H),
        },
        "CONTRAST_RIDER_DESCRIPTIVE_NO_GATE": {
            "warning": "NO pre-registered bar exists for contrast. This is "
                       "characterisation. It cannot pass or fail anything.",
            "abs_delta_L": _dist("abs_delta_L"),
            "delta_L_signed": _dist("delta_L"),
            "delta_chroma_ab": _dist("delta_chroma_ab"),
            "delta_E": _dist("delta_E"),
            "surround_sd_L": _dist("surround_sd_L"),
            "abs_delta_L_over_surround_sd": _dist("abs_delta_L_over_surround_sd"),
        },
        "per_contact": rows,
    }

    print(json.dumps({k: v for k, v in out.items() if k != "per_contact"}, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"\nwrote {args.out}")


def _score_window(c, ims, first_idx):
    """movers.foot_points on the window, UNMODIFIED, then the pre-registered metric."""
    if len(ims) < 3:
        return {"error": f"only {len(ims)} frames decoded"}
    feet = movers.foot_points(ims)
    local = c["source_frame"] - first_idx
    cx, cy = c["ref_centroid_POST_HOC"]
    blobs = []
    for (i, x, y, af) in feet:
        if i != local:
            continue
        blobs.append({"x": round(float(x), 1), "y": round(float(y), 1),
                      "area_frac": round(float(af), 6),
                      "dist_px": math.hypot(float(x) - cx, float(y) - cy)})
    blobs.sort(key=lambda b: b["dist_px"])
    for b in blobs:
        b["dist_px"] = round(b["dist_px"], 2)
    res = {
        "n_blobs_at_contact_frame": len(blobs),
        "n_foot_points_in_window": len(feet),
        "blobs_at_contact_frame": blobs,
        "nearest_dist_px": blobs[0]["dist_px"] if blobs else None,
        "nearest_dist_rel_h": (round(blobs[0]["dist_px"] / c["ref_box_h_px"], 3)
                               if blobs else None),
    }
    mid = ims[local] if 0 <= local < len(ims) else None
    res["contrast_DESCRIPTIVE"] = (contrast_stats(mid, c["ref_box_POST_HOC"])
                                   if mid is not None else None)
    return res


if __name__ == "__main__":
    main()
