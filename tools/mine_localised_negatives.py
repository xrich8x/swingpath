"""mine_localised_negatives.py — confuser LOCATIONS from frames we already labelled.

WHY THIS EXISTS
---------------
Whole-frame hard negatives are closed (Gate C, data/output/phase0_ball_ceiling.md):
they force every mining criterion to answer "does this frame contain a ball?", and
the training clips are 88.5% ball-present, so the best purity any criterion reached
was 43.7%.

The useful question is not about the frame, it is about the LOCATION. On a frame
whose ball position we already know, an argmax landing far from that label is a
CONFIRMED false fire at a KNOWN spot — no human input, no purity problem, and it
works on all 26,293 labelled frames rather than only the unlabelled remainder.

WHAT THIS IS NOT
----------------
It is not new information. The loss is BCEWithLogitsLoss on a Gaussian heatmap, so
the target is ALREADY zero at the racquet and the model is already penalised for
firing there. It does not learn because the racquet head is one pixel among
147,400, weighted the same as empty sky. What these locations enable is
RE-WEIGHTING — textbook hard-example mining. Describing it as new labels would be
wrong.

STEP 1 IS A GO/NO-GO. The detector was TRAINED on these frames, so it may already
fit them and yield nothing worth weighting. This tool reports the yield and writes
nothing unless asked. Check the yield before spending GPU time on a retrain.

    cd backend && .venv-train/Scripts/python.exe ../tools/mine_localised_negatives.py \
        --device cuda                      # yield only
    ... --write                            # also emit localised_negatives.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

IN_W, IN_H = 512, 288


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(REPO / "data/ball_dataset"))
    ap.add_argument("--weights", default=str(REPO / "backend/weights/ballnet_v21.pt"))
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--far-px", type=float, default=20.0,
                    help="distance from the known label, in 512x288 network pixels, "
                         "beyond which an argmax is unambiguously NOT the ball. "
                         "10 px of gold tolerance at 1280x720 is 4 px here, so 20 "
                         "is five times the hit radius — not a near miss")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--write", action="store_true",
                    help="emit localised_negatives.json per dataset dir. Omit to "
                         "report yield only — step 1 is a go/no-go")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    import cv2
    import numpy as np
    import torch

    from swingvision._ballnet import BallNet
    # The one-way gold split is enforced by the trainer; mining must respect it too,
    # or a gold clip's confusers would leak in through the back door.
    from train_ballnet import assert_no_gold_leak
    assert_no_gold_leak(args.data, exclude=())   # mine everything the trainer may use

    ckpt = torch.load(args.weights, map_location=args.device, weights_only=False)
    sd = ckpt["model_state_dict"]
    model = BallNet(motion_attention=any(k.startswith("motion.") for k in sd))
    model.load_state_dict(sd, strict=True)
    model.eval().to(args.device)

    def frame(d, i):
        img = cv2.imread(os.path.join(d, f"{max(i, 0):05d}.jpg"))
        return img if img is not None else cv2.imread(os.path.join(d, f"{0:05d}.jpg"))

    rows, tot_lab, tot_hit = [], 0, 0
    for d in sorted(glob.glob(os.path.join(args.data, "*", ""))):
        lp = os.path.join(d, "labels.json")
        if not os.path.isfile(lp):
            continue
        labels = (json.load(open(lp, encoding="utf-8")).get("labels") or {})
        items = sorted((int(k), v) for k, v in labels.items())
        if not items:
            continue

        found: dict[int, list] = {}
        buf_idx, buf_inp = [], []

        def flush():
            if not buf_inp:
                return
            with torch.no_grad():
                x = torch.from_numpy(np.stack(buf_inp)).float().to(args.device)
                hm = torch.sigmoid(model(x)[:, 0]).cpu().numpy()
            for (i, lx, ly), h in zip(buf_idx, hm):
                iy, ix = np.unravel_index(h.argmax(), h.shape)
                if math.dist((float(ix), float(iy)), (lx, ly)) > args.far_px:
                    found.setdefault(i, []).append([int(ix), int(iy)])
            buf_idx.clear()
            buf_inp.clear()

        for i, xy in items:
            fr = [frame(d, i), frame(d, i - 1), frame(d, i - 2)]
            if any(f is None for f in fr):
                continue
            arr = np.concatenate(fr, axis=2).astype(np.float32) / 255.0
            buf_inp.append(np.ascontiguousarray(np.rollaxis(arr, 2, 0)))
            buf_idx.append((i, float(xy[0]), float(xy[1])))
            if len(buf_inp) >= args.batch:
                flush()
        flush()

        name = os.path.basename(os.path.dirname(d))
        n_lab, n_hit = len(items), len(found)
        tot_lab += n_lab
        tot_hit += n_hit
        rows.append({"dataset": name, "labelled": n_lab, "confuser_frames": n_hit,
                     "pct": round(100.0 * n_hit / n_lab, 1) if n_lab else 0.0})
        print(f"  {name:22s} labelled {n_lab:6d}  confuser frames {n_hit:5d}  "
              f"({100.0*n_hit/max(n_lab,1):5.1f}%)", flush=True)

        if args.write and found:
            out = {"localised_negatives": {str(k): v for k, v in sorted(found.items())},
                   "provenance": {"tool": "mine_localised_negatives.py",
                                  "weights": os.path.basename(args.weights),
                                  "far_px": args.far_px,
                                  "note": "argmax further than far_px from the known "
                                          "label: a confirmed false fire at a known "
                                          "location. Locations, not frames."}}
            with open(os.path.join(d, "localised_negatives.json"), "w",
                      encoding="utf-8") as f:
                json.dump(out, f)

    print()
    print(f"TOTAL  labelled {tot_lab}  frames with a confuser {tot_hit} "
          f"({100.0*tot_hit/max(tot_lab,1):.1f}%)")
    print()
    print("GO/NO-GO. These frames were TRAINED ON, so a low yield means the model")
    print("already fits them and there is nothing to re-weight. A retrain is only")
    print("worth GPU time if this pool is large enough to shift the loss.")
    if not args.write:
        print("(yield only — pass --write to emit localised_negatives.json)")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "tool": "mine_localised_negatives",
            "measured_against":
                "the pseudo-label in each dataset's labels.json: an argmax further "
                f"than {args.far_px} px (512x288 space) from the known ball is a "
                "confirmed false fire at a known location.",
            "weights": os.path.basename(args.weights), "far_px": args.far_px,
            "total_labelled": tot_lab, "total_confuser_frames": tot_hit,
            "rows": rows,
        }, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
