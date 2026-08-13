"""eval_racquet_negation.py — can an off-the-shelf racquet box do what the skeleton could not?

WHY THIS EXISTS
---------------
Session G step 1 killed pose proximity as a hard-negative criterion: at the 5%
collateral ceiling it caught 11.4% of person-attached false locks, against a 60%
gate. The reason was geometric, not a tuning failure — THE RACQUET IS NOT ON THE
SKELETON. Median distance from a racquet-class false lock to the nearest
upper-body keypoint is 2.12 BODY HEIGHTS.

The obvious follow-up is to localise the racquet itself. That normally means
labels we do not have — except COCO already has one: class 38, "tennis racket",
present in every stock ultralytics detection checkpoint. So the criterion can be
tested with ZERO new annotation, against the same human labels the pose criterion
was scored on.

TWO RATES, SAME POPULATIONS AND SAME GATE AS eval_pose_proximity.py, so the two
criteria are directly comparable:
  catch       of the locks a human classified as racquet (and, reported
              separately, all person-attached: racquet + player + held_ball),
              what fraction lands inside a detected racket box?
  collateral  of the frames where a human CLICKED A REAL BALL, what fraction
              would this negate? A ball at contact is inches from the strings, so
              this is the real risk and it is why `--margin` is swept.

FREE SIDE-BENEFIT: the same pass measures COCO class 32, "sports ball", against
our gold clicks. That is an off-the-shelf ball detector scored on the same
frames as BallNet — an external baseline this project has never had. It is NOT a
like-for-like comparison (COCO's sports ball is trained on large, sharp balls,
not a 2-4 px blurred far-court one) and it should be read as a floor, not a rival.

    cd backend && .venv-train/Scripts/python.exe ../tools/eval_racquet_negation.py \
        --device cuda --locks ../data/output/g_falselocks_raw.json

Detections are cached per clip and imgsz, so sweeping the margin costs one pass.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs  # noqa: E402  — the gold clip registry + shared eval scaffolding

RACKET_CLS = 38        # COCO "tennis racket"
BALL_CLS = 32          # COCO "sports ball"
PERSON_CLASSES = ("racquet", "player", "held_ball")


def detect_frames(clip, frames, device, imgsz, conf, cache_path):
    """Stock YOLO detection on exactly the frames we need. Cached per clip+imgsz."""
    from ultralytics import YOLO
    model = YOLO("yolo11m.pt")

    def detect(im):
        r = model.predict(im, imgsz=imgsz, conf=conf, device=device,
                          classes=[RACKET_CLS, BALL_CLS], verbose=False)[0]
        return [{"cls": int(b.cls.item()), "conf": float(b.conf.item()),
                 "xyxy": [float(v) for v in b.xyxy[0].tolist()]} for b in r.boxes]

    return gs.collect_over_frames(clip, frames, detect, cache_path=cache_path,
                                  cache_key=f"yolo11m:{imgsz}:{conf}", label=clip)


def dist_to_boxes(pt, dets, cls, res_scale):
    """0 if the point is inside a box of this class, else px distance (720p-normalised)
    to the nearest such box. inf when the class was not detected on the frame."""
    best = math.inf
    for d in dets:
        if d["cls"] != cls:
            continue
        x1, y1, x2, y2 = d["xyxy"]
        dx = max(x1 - pt[0], 0.0, pt[0] - x2)
        dy = max(y1 - pt[1], 0.0, pt[1] - y2)
        best = min(best, math.hypot(dx, dy) / res_scale)
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--locks", default="../data/output/g_falselocks_raw.json")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.10,
                    help="low, deliberately: a missed racquet cannot negate anything, "
                         "and precision is not what this criterion needs")
    ap.add_argument("--margins", type=float, nargs="*",
                    default=[0, 5, 10, 20, 30, 50],
                    help="px beyond the box edge, normalised to 720p")
    ap.add_argument("--catch-gate", type=float, default=60.0)
    ap.add_argument("--collateral-gate", type=float, default=5.0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    locks = json.loads(Path(args.locks).read_text(encoding="utf-8"))["locks"]
    racq = [r for r in locks if r.get("klass") == "racquet"]
    person = [r for r in locks if r.get("klass") in PERSON_CLASSES]
    print(f"locks: {len(locks)} total | racquet {len(racq)} | person-attached {len(person)}")

    d_racq, d_person, d_ball = [], [], []
    ball_seen = ball_total = 0
    per_clip = {}

    for clip, video in gs.videos().items():
        if not (REPO / video).is_file():
            print(f"  SKIP {clip}")
            continue
        balls = gs.ball_frames(clip)
        clip_locks = [r for r in locks if r["clip"] == clip]
        want = set(balls) | {r["frame"] for r in clip_locks}
        cache = REPO / "data" / "output" / f"h_yolodet_{clip}_{args.imgsz}.json"
        print(f"  {clip}: {len(want)} frames", flush=True)
        dets, (fw, fh) = detect_frames(clip, want, args.device,
                                       args.imgsz, args.conf, str(cache))
        rs = gs.res_scale(fh)
        n_rack = sum(1 for f in want if any(d["cls"] == RACKET_CLS for d in dets.get(f, [])))
        # criterion distances
        for r in clip_locks:
            d = dist_to_boxes((r["x"], r["y"]), dets.get(r["frame"], []), RACKET_CLS, rs)
            if r.get("klass") == "racquet":
                d_racq.append(d)
            if r.get("klass") in PERSON_CLASSES:
                d_person.append(d)
        for f, pt in balls.items():
            d_ball.append(dist_to_boxes(pt, dets.get(f, []), RACKET_CLS, rs))
            # free baseline: does stock COCO "sports ball" find the human's ball?
            ball_total += 1
            if dist_to_boxes(pt, dets.get(f, []), BALL_CLS, rs) <= 10.0:
                ball_seen += 1
        per_clip[clip] = {"frames": len(want),
                          "frames_with_a_racket": n_rack,
                          "racket_detect_rate": round(100.0 * n_rack / max(len(want), 1), 1)}
        print(f"    racket detected on {n_rack}/{len(want)} frames "
              f"({100.0*n_rack/max(len(want),1):.1f}%)", flush=True)

    rate = gs.rate_at
    rows = []
    print("\n" + "=" * 76)
    print("RACQUET-BOX NEGATION — same populations and gate as eval_pose_proximity")
    print("=" * 76)
    print(f"{'margin_px@720p':>14} {'CATCH racquet':>14} {'CATCH person':>13} {'COLLATERAL':>11}  gate")
    for m in args.margins:
        c_r, c_p, co = rate(d_racq, m), rate(d_person, m), rate(d_ball, m)
        ok = c_r >= args.catch_gate and co <= args.collateral_gate
        rows.append({"margin_px": m, "catch_racquet_pct": round(c_r, 1),
                     "catch_person_pct": round(c_p, 1),
                     "collateral_pct": round(co, 1), "passes_gate": ok})
        print(f"{m:14.0f} {c_r:13.1f}% {c_p:12.1f}% {co:10.1f}%  {'PASS' if ok else ''}")

    winners = [r for r in rows if r["passes_gate"]]
    print("\n" + "=" * 76)
    if winners:
        b = max(winners, key=lambda r: r["catch_racquet_pct"])
        print(f"GATE PASSED at margin {b['margin_px']}px: catch(racquet) "
              f"{b['catch_racquet_pct']}%, collateral {b['collateral_pct']}%")
    else:
        print(f"GATE FAILED: no margin reaches catch >= {args.catch_gate}% on racquet "
              f"locks at collateral <= {args.collateral_gate}%.")
    print("=" * 76)
    print(f"\nFREE BASELINE — stock COCO 'sports ball' (class 32) vs the same human clicks:")
    print(f"  {ball_seen}/{ball_total} = {100.0*ball_seen/max(ball_total,1):.1f}% recall @10px  "
          f"(BallNet v21 scores 69.4% on this set)")
    print("  NOT like-for-like: COCO's sports ball is trained on large sharp balls, not a")
    print("  2-4 px blurred far-court one. Read it as a floor, not a rival.")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "eval_racquet_negation",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "yolo11m.pt (COCO)", "imgsz": args.imgsz, "conf": args.conf,
            # The clip counts are DERIVED, not written down. They were hardcoded
            # as "6 gold clips" and stayed that way after the benchmark grew to
            # ten, so the field that exists to say what a number was measured
            # against was quietly saying the wrong thing. Note the two
            # populations legitimately differ in width: CATCH can only be scored
            # where a human classified a lock, and false_lock_classes.json covers
            # fewer clips than the gold set does.
            "measured_against":
                f"human labels only: {len(racq)} racquet-class and {len(person)} "
                f"person-attached locks from data/gold/false_lock_classes.json "
                f"across {len({r['clip'] for r in racq})} clip(s) for CATCH; "
                f"{ball_total} human ball clicks across {len(gs.GOLD)} gold clips "
                f"for COLLATERAL.",
            "n_racquet_locks": len(racq), "n_person_locks": len(person),
            "n_ball_clicks": ball_total,
            "gate": {"catch_pct": args.catch_gate, "collateral_pct": args.collateral_gate,
                     "passed": bool(winners)},
            "coco_sports_ball_recall_pct": round(100.0 * ball_seen / max(ball_total, 1), 1),
            "per_clip": per_clip, "rows": rows,
        }, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
