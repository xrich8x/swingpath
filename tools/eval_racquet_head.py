"""eval_racquet_head.py — is it the racket, or specifically the racket HEAD? (Session H)

WHY THIS EXISTS
---------------
Session G part 4 measured racquet-BOX negation: a lock inside a stock COCO
"tennis racket" box. It reached 54.5% catch at 4.5% collateral against a
pre-registered 60%/5% gate — 4.8x better than pose proximity, and 5.5 points short.

The obvious next move is a tighter localiser. RacketVision (arXiv 2511.17045)
publishes 5-keypoint racket pose (top, bottom, handle, left, right) under MIT with
weights — but it needs the OpenMMLab stack pinned at mmcv==2.1.0 / mmdet==3.3.0 /
mmpose==1.3.2, and mmcv 2.1.0 will not even build its requirements against this
project's torch. Standing up a legacy environment is hours of dependency work to
test a hypothesis that can be approximated from data already on disk.

THE APPROXIMATION, and what it can and cannot tell us
-----------------------------------------------------
A racket is an oriented object: a handle held at the hand, and a head at the far
end. The ball-sized, ball-coloured confuser is the HEAD. We already have, cached:
  - the racket box            (COCO class 38, tools/eval_racquet_negation.py)
  - the player's wrists       (pose, tools/eval_pose_proximity.py)
So the head end is the end of the box furthest from the nearest wrist, and any
point can be scored on a 0..1 axis: 0 at the wrist end, 1 at the far end.

If the racket-pose hypothesis is right, racquet-class false locks should sit near
1 while real ball clicks inside racket boxes should not — and a "far fraction of
the box" criterion should beat the whole box.

THIS IS AN APPROXIMATION OF ORIENTATION, NOT A RACKET POSE. It infers direction
from the wrist, so it is undefined when pose finds nobody, and it cannot see the
racket's tilt within the box. A negative here does not refute RacketVision's
model; it says the cheap version of the idea does not pay, which is what decides
whether the legacy install is worth an afternoon.

    py tools/eval_racquet_head.py

Reads only cached JSON. No GPU, no video, seconds to run.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs  # noqa: E402

RACKET_CLS = 38
PERSON_CLASSES = ("racquet", "player", "held_ball")
WRISTS = (9, 10)          # COCO
UPPER = (5, 6, 7, 8, 9, 10)


def load_boxes(clip, imgsz=1280):
    p = REPO / "data" / "output" / f"h_yolodet_{clip}_{imgsz}.json"
    if not p.is_file():
        return None, None
    b = json.loads(p.read_text(encoding="utf-8"))
    return {int(k): v for k, v in b["data"].items()}, tuple(b["frame_wh"])


def load_pose(clip, quality="accurate"):
    p = REPO / "data" / "output" / f"g_pose_{clip}_{quality}.json"
    if not p.is_file():
        return None
    b = json.loads(p.read_text(encoding="utf-8"))
    return {int(k): v for k, v in b["data"].items()}


def nearest_wrist(pt, persons, kp_conf=0.3):
    """Closest wrist (falling back to any upper-body keypoint) to a point."""
    best, bd = None, math.inf
    for kset in (WRISTS, UPPER):
        for person in persons:
            for i in kset:
                x, y, c = person["kpts"][i]
                if c < kp_conf:
                    continue
                d = math.hypot(pt[0] - x, pt[1] - y)
                if d < bd:
                    best, bd = (x, y), d
        if best is not None:
            return best
    return None


def head_axis_position(pt, box, wrist):
    """Where `pt` sits on the wrist->far-end axis of `box`, as 0..1.

    The axis runs from the box corner NEAREST the wrist to the corner FURTHEST
    from it — the best orientation estimate available without a real racket pose.
    Returns None when the point is outside the box or the axis is degenerate.
    """
    x1, y1, x2, y2 = box
    if not (x1 <= pt[0] <= x2 and y1 <= pt[1] <= y2):
        return None
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    near = min(corners, key=lambda c: math.hypot(c[0] - wrist[0], c[1] - wrist[1]))
    far = max(corners, key=lambda c: math.hypot(c[0] - wrist[0], c[1] - wrist[1]))
    ax, ay = far[0] - near[0], far[1] - near[1]
    L2 = ax * ax + ay * ay
    if L2 < 1e-6:
        return None
    t = ((pt[0] - near[0]) * ax + (pt[1] - near[1]) * ay) / L2
    return max(0.0, min(1.0, t))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--locks", default="data/output/g_falselocks_raw.json")
    ap.add_argument("--cuts", type=float, nargs="*",
                    default=[0.0, 0.3, 0.4, 0.5, 0.6, 0.7],
                    help="keep the far fraction of the box beyond this cut")
    ap.add_argument("--catch-gate", type=float, default=60.0)
    ap.add_argument("--collateral-gate", type=float, default=5.0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    locks = json.loads((REPO / args.locks).read_text(encoding="utf-8"))["locks"]
    racq_t, person_t, ball_t = [], [], []
    n_racq_total = sum(1 for r in locks if r.get("klass") == "racquet")
    n_person_total = sum(1 for r in locks if r.get("klass") in PERSON_CLASSES)
    n_ball_total = 0
    skipped = {"no_cache": 0, "no_wrist": 0, "outside_box": 0}

    for clip in gs.videos():
        boxes, wh = load_boxes(clip)
        poses = load_pose(clip)
        if boxes is None or poses is None:
            skipped["no_cache"] += 1
            continue

        def axis_of(pt, frame):
            ds = boxes.get(frame, [])
            ps = poses.get(frame, [])
            rk = [d for d in ds if d["cls"] == RACKET_CLS]
            if not rk or not ps:
                return "no_wrist"
            w = nearest_wrist(pt, ps)
            if w is None:
                return "no_wrist"
            best = None
            for d in rk:
                t = head_axis_position(pt, d["xyxy"], w)
                if t is not None:
                    best = t if best is None else max(best, t)
            return best if best is not None else "outside_box"

        for r in locks:
            if r["clip"] != clip or r.get("klass") not in PERSON_CLASSES:
                continue
            t = axis_of((r["x"], r["y"]), r["frame"])
            if isinstance(t, str):
                skipped[t] += 1
                continue
            person_t.append(t)
            if r.get("klass") == "racquet":
                racq_t.append(t)

        for f, pt in gs.ball_frames(clip).items():
            n_ball_total += 1
            t = axis_of(pt, f)
            if isinstance(t, str):
                continue
            ball_t.append(t)

    print(f"racquet locks inside a racket box with a wrist: {len(racq_t)}/{n_racq_total}")
    print(f"person-attached likewise:                       {len(person_t)}/{n_person_total}")
    print(f"real ball clicks inside a racket box:            {len(ball_t)}/{n_ball_total}")
    print(f"skipped: {skipped}")

    def pos(vals, cut):
        return sum(1 for v in vals if v >= cut)

    print("\n" + "=" * 74)
    print("KEEP ONLY THE FAR (HEAD) FRACTION OF THE RACKET BOX")
    print("cut=0.0 is the whole box — the Session G part 4 criterion, for reference")
    print("=" * 74)
    print(f"{'cut':>6} {'CATCH racquet':>14} {'CATCH person':>13} {'COLLATERAL':>11}  gate")
    rows = []
    for cut in args.cuts:
        c_r = 100.0 * pos(racq_t, cut) / max(n_racq_total, 1)
        c_p = 100.0 * pos(person_t, cut) / max(n_person_total, 1)
        co = 100.0 * pos(ball_t, cut) / max(n_ball_total, 1)
        ok = c_r >= args.catch_gate and co <= args.collateral_gate
        rows.append({"cut": cut, "catch_racquet_pct": round(c_r, 1),
                     "catch_person_pct": round(c_p, 1),
                     "collateral_pct": round(co, 1), "passes_gate": ok})
        print(f"{cut:6.1f} {c_r:13.1f}% {c_p:12.1f}% {co:10.1f}%  {'PASS' if ok else ''}")

    if racq_t and ball_t:
        rs = sorted(racq_t)
        bs = sorted(ball_t)
        print(f"\nwhere they sit on the wrist->head axis (0 = hand end, 1 = far end):")
        print(f"  racquet locks  median {rs[len(rs)//2]:.2f}  (n={len(rs)})")
        print(f"  real balls     median {bs[len(bs)//2]:.2f}  (n={len(bs)})")
        print("  If the head hypothesis holds, the racquet median sits ABOVE the ball median.")

    gs.report_gate(rows, "catch_racquet_pct", "collateral_pct",
                   args.catch_gate, args.collateral_gate, label=" (racket-head)")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps({
            "tool": "eval_racquet_head",
            "measured_against":
                f"human labels only: {n_racq_total} racquet-class and {n_person_total} "
                f"person-attached locks from data/gold/false_lock_classes.json for CATCH; "
                f"{n_ball_total} human ball clicks for COLLATERAL. Head direction is "
                f"APPROXIMATED from the COCO racket box plus the nearest wrist, not a "
                f"real racket pose.",
            "n_racquet": n_racq_total, "n_person": n_person_total,
            "n_ball": n_ball_total, "rows": rows,
        }, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
