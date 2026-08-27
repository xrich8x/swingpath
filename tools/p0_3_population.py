"""P0-3 population: which ball contacts are FAR-END hits, from the ball's IMAGE
y-track alone.

WHY THIS EXISTS. The first P0-3 probe selected its population with
`hit_xy[1] > court.NET_Y` — the ball contact back-projected through the GROUND
homography. The ball at contact is ~1 m in the air and the camera sits behind the
near baseline, so a near-player contact's ground ray lands well PAST the net. On
yt_match40 that criterion labelled 193 of 196 contacts "far", which no real match
produces. The population was the probe's first fatal defect; this module replaces
it with a criterion that never touches the homography.

THE CRITERION. In IMAGE space the ball recedes UP the frame as it travels away
from a camera behind the near baseline (depth dominates the ~2 m of ball height
over the ~12-24 m of court depth). So a far-end contact is a local MINIMUM of the
ball's image y: y falling before the contact, rising after. A near-end contact is
the local maximum. Ball-derived, homography-free, immune to the projection
artefact.

Slopes come from a least-squares line fit on each side of the contact, using the
RAW per-frame detections in the perception cache (`ball_px`), not the smoothed
court track — the smoother is fitted in court metres and would reintroduce the
projection.

INDEXING, which the old probe also got wrong. `match["video"]["fps"]` is the
EFFECTIVE (processed) frame rate, not the source rate, so
    processed_index = round(t_hit_s * fps_eff)
indexes the perception-cache arrays directly, and
    source_frame = processed_index * frame_step
is the frame to decode. On am_hard_utr (60 fps source, frame_step 2) the old
probe's `cap.set(POS_FRAMES, t*fps)` seeked to half the intended time.
"""

from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

# Window, in PROCESSED frames, either side of the contact used to fit the ball's
# image-y slope. ~5 frames is ~0.17 s at 30 fps effective: long enough that a
# stray detection cannot flip the sign, short enough to stay inside one flight
# segment (the shortest far-court exchanges here are ~0.6 s).
WINDOW = 5
MIN_SAMPLES = 3           # valid ball detections needed on EACH side to decide
MIN_SLOPE_PX_720 = 0.8    # px per processed frame at 720p; scaled by height/720


def _fit_slope(pts):
    """Least-squares dy/di for [(i, y), ...]. None if fewer than 2 points."""
    n = len(pts)
    if n < 2:
        return None
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    den = n * sxx - sx * sx
    if abs(den) < 1e-9:
        return None
    return (n * sxy - sx * sy) / den


def _ball_at(ball_px, i, search=2):
    """Ball image xy at processed index i, or the nearest detection within
    +/- `search` frames. None if the ball was unseen through the whole window."""
    n = len(ball_px)
    for d in range(search + 1):
        for j in (i - d, i + d):
            if 0 <= j < n and ball_px[j] is not None:
                return (float(ball_px[j][0]), float(ball_px[j][1])), j
    return None, None


def classify_contacts(match, perception, window=WINDOW,
                      min_samples=MIN_SAMPLES):
    """Label every shot in `match` near-end / far-end / undecided from the ball's
    image y-track. Returns a list of dicts, one per shot, in shot order."""
    fps_eff = float(match["video"]["fps"])
    height = float(match["video"]["height"])
    frame_step = int(perception.get("frame_step", 1))
    ball_px = perception["ball_px"]
    n = len(ball_px)
    min_slope = MIN_SLOPE_PX_720 * (height / 720.0)

    out = []
    for s in match["shots"]:
        pi = int(round(float(s["t_hit_s"]) * fps_eff))
        rec = {
            "shot_id": s["id"],
            "rally_id": s.get("rally_id"),
            "t_hit_s": s["t_hit_s"],
            "processed_index": pi,
            "source_frame": pi * frame_step,
            "pipeline_player": s.get("player"),
            "hit_xy_court": s.get("hit_xy"),
            "end": "undecided",
            "reason": "",
        }
        if not (0 <= pi < n):
            rec["reason"] = "index outside the perception cache"
            out.append(rec)
            continue

        pre = [(j - pi, float(ball_px[j][1]))
               for j in range(max(0, pi - window), pi) if ball_px[j] is not None]
        post = [(j - pi, float(ball_px[j][1]))
                for j in range(pi + 1, min(n, pi + window + 1)) if ball_px[j] is not None]
        rec["n_pre"] = len(pre)
        rec["n_post"] = len(post)
        if len(pre) < min_samples or len(post) < min_samples:
            rec["reason"] = "too few ball detections around the contact"
            out.append(rec)
            continue

        sp, sq = _fit_slope(pre), _fit_slope(post)
        rec["slope_pre_px_per_frame"] = None if sp is None else round(sp, 3)
        rec["slope_post_px_per_frame"] = None if sq is None else round(sq, 3)
        if sp is None or sq is None:
            rec["reason"] = "degenerate slope fit"
            out.append(rec)
            continue

        if sp < -min_slope and sq > min_slope:
            rec["end"] = "far"
        elif sp > min_slope and sq < -min_slope:
            rec["end"] = "near"
        else:
            rec["reason"] = (f"no clean image-y reversal "
                             f"(pre {sp:+.2f}, post {sq:+.2f}, "
                             f"threshold {min_slope:.2f} px/frame)")

        ball, used = _ball_at(ball_px, pi)
        rec["ball_px_at_contact"] = None if ball is None else [round(ball[0], 1), round(ball[1], 1)]
        rec["ball_px_frame_used"] = used
        out.append(rec)
    return out


def alternation_report(records):
    """Cross-check: within a rally, ends should ALTERNATE. Reports the fraction of
    consecutive decided pairs that do. This is a consistency check on the
    criterion, not ground truth."""
    by_rally = {}
    for r in records:
        by_rally.setdefault(r["rally_id"], []).append(r)
    pairs = alt = 0
    for rid, rs in by_rally.items():
        rs = [r for r in sorted(rs, key=lambda z: z["t_hit_s"]) if r["end"] != "undecided"]
        for a, b in zip(rs, rs[1:]):
            pairs += 1
            if a["end"] != b["end"]:
                alt += 1
    return {"decided_consecutive_pairs": pairs,
            "alternating": alt,
            "alternating_pct": round(100.0 * alt / pairs, 1) if pairs else None}


def pipeline_agreement(records):
    """How often the ball-derived end matches the pipeline's own `player` field.
    NOT an independent check — `pipeline.py` sets `striker = "A" if track[h][2] <
    NET_Y else "B"`, i.e. from the same ground-projected contact that produced the
    artefact this module exists to avoid. Reported to SIZE the artefact."""
    n = agree = 0
    pl_far = 0
    for r in records:
        if r["end"] == "undecided" or r["pipeline_player"] is None:
            continue
        n += 1
        expect = "B" if r["end"] == "far" else "A"
        if r["pipeline_player"] == expect:
            agree += 1
        if r["pipeline_player"] == "B":
            pl_far += 1
    return {"decided": n, "agree": agree,
            "agree_pct": round(100.0 * agree / n, 1) if n else None,
            "pipeline_called_far": pl_far,
            "pipeline_called_far_pct": round(100.0 * pl_far / n, 1) if n else None}


def load(match_path, perception_path=None):
    with open(match_path, "r", encoding="utf-8") as f:
        match = json.load(f)
    if perception_path is None:
        perception_path = os.path.splitext(match_path)[0] + ".perception.json"
    with open(perception_path, "r", encoding="utf-8") as f:
        perception = json.load(f)
    return match, perception


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--perception", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    match, perception = load(args.match, args.perception)
    recs = classify_contacts(match, perception)
    counts = {}
    for r in recs:
        counts[r["end"]] = counts.get(r["end"], 0) + 1
    result = {
        "match": os.path.basename(args.match),
        "video": match["video"],
        "frame_step": perception.get("frame_step"),
        "pose_model": perception.get("provenance", {}).get("pose_model"),
        "criterion": ("far-end hit = local MINIMUM of the ball's raw IMAGE y-track "
                      f"(least-squares slope over +/-{WINDOW} processed frames, "
                      f"min |slope| {MIN_SLOPE_PX_720} px/frame scaled by height/720, "
                      f"min {MIN_SAMPLES} detections per side). No homography."),
        "counts": counts,
        "alternation_check": alternation_report(recs),
        "pipeline_player_agreement": pipeline_agreement(recs),
        "records": recs,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    summary = dict(result)
    summary.pop("records")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
