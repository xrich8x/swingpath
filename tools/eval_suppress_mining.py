"""eval_suppress_mining.py — can suppression's own rejections be MINED as hard negatives?

WHY THIS EXISTS
---------------
The 9 solid ghost balls have survived six independent attempts (detector
threshold, smoother gap, input resolution, motion attention, pose proximity,
racquet-box negation). They are the detector firing on real objects — racquet
31%, player 28%, scenery 38% — so the only lever left is training data: HARD
NEGATIVES, the exact frames it fires wrongly on.

Both automatic miners tried so far reasoned about WHERE the lock is (near a
skeleton, inside a racket box) and both failed their gate. `suppress_false_locks`
reasons about HOW IT MOVES, and it demonstrably works at runtime — it takes
am_hard_utr from 37.5% false-fire to 4.2%. So its rejections are a candidate
mining pool that the position-based criteria never tested.

THE DANGER, AND IT IS THE POINT OF THE MEASUREMENT
--------------------------------------------------
Suppression also costs 5-10 pts of recall, so some of what it rejects is a REAL
BALL. Mining those would teach the detector to go blind — and unlike a runtime
filter deleting one detection, a mined negative is baked into the weights and
does not recover. Collateral is therefore the number that decides this, not catch.

TWO TESTS, MEASURED SEPARATELY, because they are mined differently:
  persistence  a lock that holds still => provably a fixture. Already mined by
               mine_hard_negatives.py; reaches only the static 38%.
  min-segment  a 1-4 frame flare that never forms a ball-plausible track. This
               is what a swung racquet looks like.

SAME POPULATIONS AND SAME GATE as eval_pose_proximity.py and
eval_racquet_negation.py, so all four criteria are directly comparable:
  catch       of the human-classified person-attached false locks (44 of 71 in
              data/output/g_falselocks_raw.json), what fraction does the test
              reject?
  collateral  of the frames where the raw detector CORRECTLY found a human-clicked
              ball, what fraction does the test reject? Restricting to correct
              locks is deliberate — rejecting an already-wrong lock is not
              collateral, it is the point.

WINDOWS, NOT WHOLE CLIPS. Suppression is temporal, so it needs a contiguous
track — but its span is small (static_run ~0.2 s, seg_len ~0.1 s), so a window of
+/-`--window` frames around each target frame is ample and makes all six clips
affordable. Overlapping windows are merged into contiguous spans and the detector
runs once per span.

    cd backend && .venv-train/Scripts/python.exe ../tools/eval_suppress_mining.py \
        --device cuda --json ../data/output/suppress_mining.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs  # noqa: E402

PERSON = {"racquet", "player", "held_ball"}
VARIANTS = ("persistence", "minseg", "both")


def spans(frames, window, last):
    """Merge +/-window around each frame into contiguous [a, b] spans."""
    if not frames:
        return []
    want = sorted({max(0, f - window) for f in frames} | {f for f in frames})
    out, a = [], None
    prev = None
    for f in sorted({x for fr in frames for x in range(max(0, fr - window),
                                                       min(last, fr + window) + 1)}):
        if a is None:
            a = prev = f
            continue
        if f == prev + 1:
            prev = f
            continue
        out.append((a, prev))
        a = prev = f
    if a is not None:
        out.append((a, prev))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--weights", default="weights/ballnet_v21.pt")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--window", type=int, default=20,
                    help="frames either side of a target; must exceed the "
                         "suppression span (~0.2 s) for the verdict to be stable")
    ap.add_argument("--hit-px", type=float, default=10.0)
    ap.add_argument("--locks", default=str(REPO / "data/output/g_falselocks_raw.json"))
    ap.add_argument("--catch-gate", type=float, default=60.0)
    ap.add_argument("--collateral-gate", type=float, default=5.0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    import cv2

    from swingvision.ball import OurBallDetector, suppress_false_locks

    locks = json.loads(Path(args.locks).read_text(encoding="utf-8"))["locks"]
    by_clip: dict[str, list] = {}
    for L in locks:
        by_clip.setdefault(L["clip"], []).append(L)

    det = OurBallDetector(args.weights, device=args.device)
    tally = {v: {"catch": 0, "catch_n": 0, "catch_r": 0, "catch_rn": 0,
                 "coll": 0, "coll_n": 0} for v in VARIANTS}
    per_clip = []

    for clip in gs.GOLD:
        # video_path, not name_video_calib()'s repo-relative string — this tool is
        # run from backend/ and a relative path silently opens nothing.
        video = str(gs.GOLD[clip].video_path)
        balls = gs.ball_frames(clip)
        flocks = by_clip.get(clip, [])
        targets = sorted(set(balls) | {L["frame"] for L in flocks})
        if not targets:
            continue

        cap = cv2.VideoCapture(video)
        n_src = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        # FAIL LOUDLY. The first run of this tool reported "0/0 -> fail" for every
        # clip because the paths were relative and nothing opened — a result that
        # looks like a measurement and is not one. An unopenable clip is a broken
        # run, not a negative finding.
        if not cap.isOpened() or n_src <= 0 or fps <= 0:
            cap.release()
            raise SystemExit(f"cannot read {video} (frames={n_src}, fps={fps}) — "
                             f"refusing to report a rate over zero frames")
        h_src = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        rs = gs.res_scale(h_src)
        # The clip is analysed at its SHIPPED effective rate, because both
        # suppression thresholds are times: judging at the wrong rate is the
        # frame-step trap this project has hit twice.
        step = max(1, round(fps / 30.0))
        fps_eff = fps / step

        lock_frames = {L["frame"]: L for L in flocks}
        clip_stat = {v: {"catch": 0, "catch_n": 0, "coll": 0, "coll_n": 0}
                     for v in VARIANTS}

        for a, b in spans(targets, args.window * step, max(0, n_src - 1)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, a)
            det.reset()
            idx, pos = [], []
            f = a
            while f <= b:
                ok, frame = cap.read()
                if not ok:
                    break
                if (f - a) % step == 0:
                    p = det.detect(frame)
                    idx.append(f)
                    pos.append(None if p is None else [float(p[0]), float(p[1])])
                f += 1
            if not idx:
                continue

            raw = {i: p for i, p in zip(idx, pos)}
            for v in VARIANTS:
                kept = suppress_false_locks(list(pos), fps_eff=fps_eff,
                                            res_scale=rs, tests=v)
                survive = {i: k for i, k in zip(idx, kept)}
                for fr in targets:
                    if fr not in raw or raw[fr] is None:
                        continue
                    killed = survive.get(fr) is None
                    if fr in lock_frames:
                        clip_stat[v]["catch_n"] += 1
                        clip_stat[v]["catch"] += int(killed)
                        if lock_frames[fr]["klass"] in PERSON:
                            tally[v]["catch_n"] += 1
                            tally[v]["catch"] += int(killed)
                        if lock_frames[fr]["klass"] == "racquet":
                            tally[v]["catch_rn"] += 1
                            tally[v]["catch_r"] += int(killed)
                    elif fr in balls:
                        # Collateral counts only locks that were RIGHT: the raw
                        # detector must already be on the human's click.
                        cx, cy = balls[fr]
                        if math.dist(raw[fr], (cx, cy)) <= args.hit_px:
                            clip_stat[v]["coll_n"] += 1
                            clip_stat[v]["coll"] += int(killed)
                            tally[v]["coll_n"] += 1
                            tally[v]["coll"] += int(killed)
        cap.release()
        per_clip.append({"clip": clip, "fps_eff": round(fps_eff, 2), **clip_stat})
        print(f"  {clip:14s} fps_eff {fps_eff:5.1f}  "
              + "  ".join(f"{v}: catch {clip_stat[v]['catch']}/{clip_stat[v]['catch_n']}"
                          f" coll {clip_stat[v]['coll']}/{clip_stat[v]['coll_n']}"
                          for v in VARIANTS), flush=True)

    def pct(a, b):
        return 100.0 * a / b if b else float("nan")

    rows = []
    print()
    print(f"{'test':>12} {'CATCH person':>13} {'CATCH racquet':>14} {'COLLATERAL':>11}  gate")
    for v in VARIANTS:
        t = tally[v]
        c, cr, co = (pct(t["catch"], t["catch_n"]), pct(t["catch_r"], t["catch_rn"]),
                     pct(t["coll"], t["coll_n"]))
        ok = c >= args.catch_gate and co <= args.collateral_gate
        print(f"{v:>12} {c:12.1f}% {cr:13.1f}% {co:10.1f}%  "
              f"{'PASS' if ok else 'fail'}")
        rows.append({"test": v, "catch_person_pct": round(c, 1),
                     "catch_racquet_pct": round(cr, 1), "collateral_pct": round(co, 1),
                     "catch_n": t["catch_n"], "collateral_n": t["coll_n"],
                     "passes_gate": ok})
    t = tally["both"]
    print(f"\npopulations: {t['catch_n']} person-attached false locks, "
          f"{t['coll_n']} correctly-located ball frames")
    print(f"gate: catch >= {args.catch_gate}% at collateral <= {args.collateral_gate}% "
          f"(same as eval_pose_proximity 11.4% and eval_racquet_negation 54.5%)")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "tool": "eval_suppress_mining",
            "measured_against":
                "human-classified false locks (data/output/g_falselocks_raw.json) for "
                "CATCH and human ball clicks the raw detector already found for "
                "COLLATERAL, over all six gold clips at each clip's shipped frame step.",
            "gate": {"catch_pct": args.catch_gate, "collateral_pct": args.collateral_gate},
            "window": args.window, "weights": args.weights,
            "rows": rows, "per_clip": per_clip,
        }, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
