"""eval_pose_proximity.py — is "near a person" a safe hard-negative criterion? (Session G step 1)

Session F left one lever standing. The ghost ball at the shipped config is 19
fires over 74 no-ball frames, 9 SOLID and 10 faded, and both post-hoc knobs that
were swept (detector score threshold, smoother max_gap_s) trade recall ~1:1
against the faded half while leaving the solid 9 untouched at EVERY setting. The
only thing that stops the detector firing on a racquet is a detector trained not
to — and the human classification of all 71 raw false locks says 59.2% of them
MOVE WITH A PERSON (racquet 31.0%, player 28.2%), a population
mine_hard_negatives.py's static-lock criterion cannot reach.

So: mine "lock near a person" as a hard negative. This tool decides whether that
is safe BEFORE any GPU time is spent on mining or training, because the criterion
has an obvious way to be wrong — a real ball at contact is BY DEFINITION next to
a wrist, and a miner that negates those teaches the net to go blind exactly where
speed measurement begins.

TWO RATES, SCORED AGAINST HUMAN LABELS ONLY
-------------------------------------------
  catch       of the locks a human classified as person-attached
              (racquet + player + held_ball), what fraction does the criterion
              flag? This is the win.
  collateral  of the 1201 frames where a human CLICKED A REAL BALL, what fraction
              would the criterion have negated? This is the cost.

Both come from human labels (data/gold/*.labels.json and
data/gold/false_lock_classes.json). No model grades its own homework here: pose
supplies geometry, and every verdict is scored against a human.

NOTE ON THE COLLATERAL POPULATION: 1201, not the 617 quoted in the session plan.
617 is the CHAIN-level count (calibrated clips, scoreable at the shipped frame
step). A mining criterion is applied at detector level, on every labelled ball
frame, so 1201 is the population that can actually be harmed.

TWO WAYS TO SIZE THE RADIUS, AND THEY ARE NOT EQUIVALENT
--------------------------------------------------------
  --mode px    absolute pixels, scaled by res_scale = frame_height/720. This repo
               has twice shipped a 720p-tuned pixel threshold that silently
               deleted real balls at 1080p, so the scaling is not optional.
  --mode body  a multiple of THAT PERSON'S bounding-box height. Depth-adaptive
               for free: a far player's racquet sits fewer pixels from their
               wrist than a near player's, and one absolute radius cannot be
               right for both in the same frame.

Both are reported. Expect body-relative to dominate; if it does not, say so.

  cd backend && .venv-train/Scripts/python.exe ../tools/eval_pose_proximity.py \
      --device cuda --locks ../data/output/g_falselocks_raw.json

Pose is cached per clip (--pose-cache), so the radius sweep costs one pass.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

# Same six gold clips as eval_detector_gold.CLIPS. Only the video is needed here:
# the criterion is calibration-free, which is the whole point — it applies to
# every training clip, not just the three with a homography.
CLIPS = {
    "am_hard_utr": "data/am_hard_utr.mp4",
    "gold_shell": "data/gold_shell.mp4",
    "gold_clay": "data/gold_clay.mp4",
    "gold_am": "data/gold_am.mp4",
    "yt_rally2": "data/yt_rally2.mp4",
    "yt_match40": "data/yt_match40.mp4",
}

# COCO-17 indices. PlayerPose.feet() uses 15/16 for ankles, same convention.
KEYPOINT_SETS = {
    "wrists": (9, 10),
    "wrists_elbows": (7, 8, 9, 10),
    "upper_body": (5, 6, 7, 8, 9, 10),
}

# A lock a human called racquet/player/held_ball is person-attached. held_ball is
# a REAL ball not in play (held in the hand, on the strings) — it is attached to
# a person and it is a false fire, so the criterion should catch it.
PERSON_CLASSES = ("racquet", "player", "held_ball")


def gold_ball_frames(clip):
    """{frame: (x, y)} for every frame a human clicked a real ball on."""
    p = REPO / "data" / "gold" / f"{clip}.labels.json"
    labels = json.loads(p.read_text(encoding="utf-8"))["labels"]
    return {int(f): (float(v["x"]), float(v["y"]))
            for f, v in labels.items()
            if v.get("ball") is True and v.get("x") is not None}


def collect_pose(clip, video, frames, device, quality, cache_path):
    """Run pose on exactly the frames we need; cache so the sweep is free.

    Mirrors inspect_false_locks.raw_locks' seek pattern (CAP_PROP_POS_FRAMES +
    read) rather than decoding whole clips: the frames wanted are scattered over
    tens of thousands, so seeking is the cheap direction.
    """
    if cache_path and Path(cache_path).is_file():
        blob = json.loads(Path(cache_path).read_text(encoding="utf-8"))
        if blob.get("clip") == clip and blob.get("quality") == quality:
            return ({int(k): v for k, v in blob["poses"].items()},
                    tuple(blob["frame_wh"]))

    from swingvision.pose import PoseEstimator

    est = PoseEstimator(device=device, quality=quality)
    cap = cv2.VideoCapture(str(REPO / video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    frame_wh = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    poses = {}
    for n, f in enumerate(sorted(frames)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, im = cap.read()
        if not ok:
            continue
        # One record per detected person: keypoints + box height, which is the
        # per-person scale the body-relative mode needs.
        poses[f] = [{"kpts": [[float(x), float(y), float(c)] for x, y, c in pp.keypoints],
                     "box_h": float(pp.box[3] - pp.box[1])}
                    for pp in est.estimate(im)]
        if n % 100 == 0:
            print(f"    {clip}: pose {n}/{len(frames)}", flush=True)
    cap.release()

    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(
            {"clip": clip, "quality": quality, "frame_wh": list(frame_wh),
             "poses": poses}), encoding="utf-8")
    return poses, frame_wh


def nearest_keypoint(pt, persons, kset, kp_conf, mode):
    """Distance from pt to the nearest usable keypoint.

    In `body` mode the distance is divided by that person's box height, so the
    returned number is "fraction of a body height" and is directly comparable
    between a near player and a far one.
    """
    best = math.inf
    for person in persons:
        box_h = person["box_h"]
        if mode == "body" and box_h <= 1:
            continue
        for i in kset:
            x, y, c = person["kpts"][i]
            if c < kp_conf:
                continue
            d = math.hypot(pt[0] - x, pt[1] - y)
            if mode == "body":
                d /= box_h
            best = min(best, d)
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--locks", default="../data/output/g_falselocks_raw.json",
                    help="output of inspect_false_locks.py --stage raw --json")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--pose-quality", default="fast",
                    help="shipped default is fast; try accurate to test whether a "
                         "missed far player is what limits catch")
    ap.add_argument("--kp-conf", type=float, default=0.3,
                    help="ignore keypoints below this confidence")
    ap.add_argument("--px-radii", type=float, nargs="*",
                    default=[20, 30, 40, 50, 60, 80, 100])
    ap.add_argument("--body-radii", type=float, nargs="*",
                    default=[0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])
    ap.add_argument("--catch-gate", type=float, default=60.0)
    ap.add_argument("--collateral-gate", type=float, default=5.0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    locks = json.loads(Path(args.locks).read_text(encoding="utf-8"))["locks"]
    person_locks = [r for r in locks if r.get("klass") in PERSON_CLASSES]
    other_locks = [r for r in locks if r.get("klass") not in PERSON_CLASSES]
    print(f"locks: {len(locks)} total, {len(person_locks)} person-attached "
          f"({100*len(person_locks)/len(locks):.1f}%), {len(other_locks)} other")

    # Distances are computed ONCE per (point, keypoint-set, mode); the radius
    # sweep is then a comparison in memory. Same trick as the score-threshold
    # sweep: the expensive thing must not be repeated per operating point.
    dist = {m: {k: {"person": [], "other": [], "ball": []} for k in KEYPOINT_SETS}
            for m in ("px", "body")}
    per_clip = {}

    for clip, video in CLIPS.items():
        if not (REPO / video).is_file():
            print(f"  SKIP {clip}: {video} not found")
            continue
        balls = gold_ball_frames(clip)
        clip_locks = [r for r in locks if r["clip"] == clip]
        want = set(balls) | {r["frame"] for r in clip_locks}
        # Cache key carries the quality preset: an `accurate` pass must not
        # overwrite the `fast` one, or the A/B between them stops being free.
        cache = REPO / "data" / "output" / f"g_pose_{clip}_{args.pose_quality}.json"
        print(f"  {clip}: {len(want)} frames ({len(balls)} ball, {len(clip_locks)} locks)")
        poses, (fw, fh) = collect_pose(clip, video, want, args.device,
                                       args.pose_quality, str(cache))
        res_scale = fh / 720.0
        n_pose = sum(1 for f in want if poses.get(f))
        per_clip[clip] = {"frames": len(want), "balls": len(balls),
                          "locks": len(clip_locks), "res_scale": round(res_scale, 3),
                          "frame_wh": [fw, fh],
                          "frames_with_a_person": n_pose}

        for kname, kset in KEYPOINT_SETS.items():
            for mode in ("px", "body"):
                for r in clip_locks:
                    d = nearest_keypoint((r["x"], r["y"]), poses.get(r["frame"], []),
                                         kset, args.kp_conf, mode)
                    # px distances are normalised to 720p so one radius means the
                    # same physical thing on a 1080p clip as on a 720p one.
                    if mode == "px" and math.isfinite(d):
                        d /= res_scale
                    bucket = "person" if r.get("klass") in PERSON_CLASSES else "other"
                    dist[mode][kname][bucket].append(d)
                for f, pt in balls.items():
                    d = nearest_keypoint(pt, poses.get(f, []), kset, args.kp_conf, mode)
                    if mode == "px" and math.isfinite(d):
                        d /= res_scale
                    dist[mode][kname]["ball"].append(d)

    def rate(vals, r):
        return 100.0 * sum(1 for v in vals if v <= r) / max(len(vals), 1)

    rows = []
    print("\n" + "=" * 78)
    print("CATCH = % of human-classified person-attached locks flagged (the win)")
    print("COLL  = % of human-clicked REAL BALLS flagged (the cost)")
    print("OTHER = % of static-scenery locks flagged (harmless - still false locks)")
    print("=" * 78)
    for mode, radii, unit in (("px", args.px_radii, "px@720p"),
                              ("body", args.body_radii, "xbodyH")):
        print(f"\n--- mode={mode} ({unit}) ---")
        print(f"{'keypoints':14} {'radius':>8} {'CATCH':>7} {'COLL':>7} {'OTHER':>7}  gate")
        for kname in KEYPOINT_SETS:
            d = dist[mode][kname]
            for r in radii:
                c, co, ot = rate(d["person"], r), rate(d["ball"], r), rate(d["other"], r)
                ok = c >= args.catch_gate and co <= args.collateral_gate
                rows.append({"mode": mode, "keypoints": kname, "radius": r,
                             "catch_pct": round(c, 1), "collateral_pct": round(co, 1),
                             "other_pct": round(ot, 1), "passes_gate": ok})
                print(f"{kname:14} {r:8.2f} {c:6.1f}% {co:6.1f}% {ot:6.1f}%  "
                      f"{'PASS' if ok else ''}")

    # Headroom: if no row passes, this says whether it was close or hopeless.
    print("\n--- ball-to-nearest-keypoint distance percentiles (the headroom) ---")
    for mode, unit in (("px", "px@720p"), ("body", "xbodyH")):
        for kname in KEYPOINT_SETS:
            vals = sorted(v for v in dist[mode][kname]["ball"] if math.isfinite(v))
            if not vals:
                continue
            q = [vals[min(len(vals) - 1, int(len(vals) * p))] for p in (.01, .05, .10, .25, .50)]
            print(f"  {mode:5} {kname:14} p1={q[0]:7.2f} p5={q[1]:7.2f} p10={q[2]:7.2f} "
                  f"p25={q[3]:7.2f} p50={q[4]:7.2f}  ({unit})")

    winners = [r for r in rows if r["passes_gate"]]
    print("\n" + "=" * 78)
    if winners:
        best = max(winners, key=lambda r: r["catch_pct"])
        print(f"GATE PASSED by {len(winners)} configuration(s). Best catch: "
              f"{best['keypoints']} @ {best['radius']} ({best['mode']}) -> "
              f"catch {best['catch_pct']}%, collateral {best['collateral_pct']}%")
    else:
        print(f"GATE FAILED: no configuration reaches catch >= {args.catch_gate}% "
              f"at collateral <= {args.collateral_gate}%.")
        print("Per Session G step 1, STOP HERE. Write the numbers into the brief.")
    print("=" * 78)

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "eval_pose_proximity",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pose_quality": args.pose_quality, "kp_conf": args.kp_conf,
            "device": args.device,
            "measured_against":
                f"human labels only: {len(person_locks)} person-attached locks of "
                f"{len(locks)} human-classified false locks "
                f"(data/gold/false_lock_classes.json) for CATCH, and every frame a "
                f"human clicked a real ball on across 6 gold clips "
                f"(data/gold/*.labels.json) for COLLATERAL.",
            "n_person_locks": len(person_locks), "n_other_locks": len(other_locks),
            "n_ball_clicks": len(dist["px"]["wrists"]["ball"]),
            "gate": {"catch_pct": args.catch_gate, "collateral_pct": args.collateral_gate,
                     "passed": bool(winners)},
            "per_clip": per_clip, "rows": rows,
        }, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
