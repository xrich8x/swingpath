"""mine_hard_negatives.py — mine the frames where BallNet false-fires (E5).

BallNet finds the ball well (+8-12 pts vs off-the-shelf) but false-fires on
non-balls (~64% on no-ball gold frames, ungated) — its one documented weakness.
The fix the playbook + our own history name is HARD negatives: train it on the
exact frames it wrongly fires on, with a "no ball here" target. The prior
"negatives" were dead-time silence frames (the WRONG negatives); these are the
confusers.

The safe, high-confidence hard negative is a STATIC lock: a real ball is never
motionless, so anywhere BallNet fires on a spot that does not move for several
frames is provably a fixture (burned-in HUD, net post, logo, line marker) — a
false-fire. We mine those from the already-extracted training-clip frames
(data/ball_dataset/*/ JPGs), never touching yt_rally2 (the gold clip) or the raw
labels.json (written to a separate hard_negatives.json).

  cd backend
  .venv-train/Scripts/python.exe mine_hard_negatives.py --device cuda --contact-sheet
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Same weight-fingerprint helper the perception cache stamps with, so a mined
# negative set and a perception cache name their checkpoint the same way.
# pipeline's module-level imports are numpy + sibling modules only (no torch),
# so this stays cheap at import time.
from swingvision.pipeline import _file_fingerprint  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ball_dataset"))
STATIC_STEP_PX = 3.0     # a lock moving less than this per frame ...
STATIC_MIN_RUN = 6       # ... for at least this many frames is a fixture
LABEL_NEAR_PX = 40.0     # don't negate a static run that sits on the pseudo-label ball


def mine_clip(tag: str, det, args) -> dict:
    d = os.path.join(ROOT, tag)
    lp = os.path.join(d, "labels.json")
    if not os.path.isfile(lp):
        return {}
    meta = json.loads(open(lp, encoding="utf-8").read())
    n = meta["n_frames"]
    labels = {int(k): v for k, v in meta["labels"].items()}
    win_starts = set(meta.get("window_starts", []))

    det.reset()
    locks: list = [None] * n
    prev_start = -1
    for i in range(n):
        # frames are contiguous per dir but split into windows; reset the 3-frame
        # buffer at each window seam so motion cues stay valid.
        if i in win_starts:
            det.reset()
        img = cv2.imread(os.path.join(d, f"{i:05d}.jpg"))
        if img is None:
            continue
        locks[i] = det.detect(img)

    # find static-confident runs (a lock that barely moves for >= STATIC_MIN_RUN)
    hard: list[int] = []
    run: list[int] = []
    for i in range(n):
        p = locks[i]
        if p is not None and run and locks[run[-1]] is not None \
                and math.dist(p, locks[run[-1]]) <= STATIC_STEP_PX \
                and (i - run[-1]) <= 2:
            run.append(i)
        else:
            if len(run) >= STATIC_MIN_RUN:
                cx = float(np.mean([locks[j][0] for j in run]))
                cy = float(np.mean([locks[j][1] for j in run]))
                for j in run:
                    lab = labels.get(j)
                    if lab is not None and math.hypot(lab[0] - cx, lab[1] - cy) < LABEL_NEAR_PX:
                        continue          # a genuinely slow ball near its label: skip
                    hard.append(j)
            run = [i] if p is not None else []
    if len(run) >= STATIC_MIN_RUN:
        cx = float(np.mean([locks[j][0] for j in run]))
        cy = float(np.mean([locks[j][1] for j in run]))
        hard += [j for j in run
                 if not (labels.get(j) and math.hypot(labels[j][0] - cx, labels[j][1] - cy) < LABEL_NEAR_PX)]

    hard = sorted(set(hard))
    out = {"hard_negatives": hard, "n_frames": n,
           "provenance": {"tool": "mine_hard_negatives.py",
                          "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                          # Report what ACTUALLY loaded. This was the hardcoded
                          # string "BallNet (weights/ballnet.pt)" regardless of the
                          # detector it was handed, so any set mined after the
                          # default moved to ballnet_v21.pt carried a false
                          # attribution. score_thresh belongs here too: it decides
                          # which locks exist, so a set mined at one threshold is
                          # not a set for another.
                          "detector": "BallNet",
                          "weights": {"path": det.weights_path,
                                      "sha256": _file_fingerprint(det.weights_path)},
                          "score_thresh": det.score_thresh,
                          "device": det.device,
                          "static_step_px": STATIC_STEP_PX,
                          "static_min_run": STATIC_MIN_RUN,
                          "n_locks": sum(p is not None for p in locks)}}
    with open(os.path.join(d, "hard_negatives.json"), "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"{tag}: {sum(p is not None for p in locks)} locks -> {len(hard)} hard negatives",
          flush=True)
    return {"tag": tag, "dir": d, "hard": hard, "locks": locks}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--contact-sheet", action="store_true",
                    help="write a grid of example mined negatives for human review")
    args = ap.parse_args()

    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=args.device)

    tags = args.only or sorted(t for t in os.listdir(ROOT)
                               if os.path.isdir(os.path.join(ROOT, t)))
    total = 0
    sheet_crops = []
    for tag in tags:
        r = mine_clip(tag, det, args)
        if not r:
            continue
        total += len(r["hard"])
        if args.contact_sheet and r["hard"]:
            pick = r["hard"][:: max(1, len(r["hard"]) // 4)][:4]
            for j in pick:
                img = cv2.imread(os.path.join(r["dir"], f"{j:05d}.jpg"))
                p = r["locks"][j]
                if img is None or p is None:
                    continue
                cv2.circle(img, (int(p[0]), int(p[1])), 12, (0, 0, 255), 2)
                cv2.putText(img, f"{r['tag']} f{j}", (6, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                sheet_crops.append(img)
    print(f"TOTAL hard negatives mined: {total}")

    if args.contact_sheet and sheet_crops:
        cols = 4
        rows = [np.hstack(sheet_crops[i:i + cols] +
                          [np.zeros_like(sheet_crops[0])] * (cols - len(sheet_crops[i:i + cols])))
                for i in range(0, len(sheet_crops), cols)]
        out = os.path.abspath(os.path.join(ROOT, "..", "output", "hard_negatives_sheet.png"))
        cv2.imwrite(out, np.vstack(rows))
        print(f"contact sheet ({len(sheet_crops)} examples) -> {out}")


if __name__ == "__main__":
    main()
