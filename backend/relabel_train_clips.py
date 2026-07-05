"""Regenerate ball pseudo-labels for the training clips — gated, with negatives.

Replaces session 1's lost scratchpad labeler (label_train_clips.py). Differences
that matter (HANDOFF §10-11):

  * the BallTracker STATIC-LOCK GATE is on (default since commit e8a1fea), so
    fixture junk (burned-in HUD boxes, logos, net posts) no longer enters the
    labels — v1 learned that junk from ungated labels;
  * NEGATIVE frames are recorded: sustained tracker silence (no lock within
    ±3 processed frames) becomes an all-zero-heatmap training target. Every
    such frame still contains the burned-in HUD, so "HUD is not a ball" is
    taught for free. Capped at a fraction of the positive count per clip.

yt_rally2 is deliberately NOT relabeled: it is the human gold benchmark clip
(data/gold/) and must stay out of v2 training entirely.

    .venv-train/Scripts/python.exe relabel_train_clips.py --device cuda
    .venv-train/Scripts/python.exe relabel_train_clips.py --smoke   # 1 short window

Output: ../data/ball_dataset/yt_<id>/{idx:05d}.jpg + labels.json
        {"n_frames", "labels": {idx: [x, y]}, "negatives": [idx, ...],
         "window_starts": [...], "provenance": {...}}
Frame indices are contiguous per directory; the first 2 indices of each window
are excluded from labels/negatives (no valid 3-frame context across the seam).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ball_dataset"))
CLIPS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "train_clips"))
IN_W, IN_H = 512, 288
NEG_GUARD = 3          # a negative needs silence at +/- this many processed frames
NEG_MAX_FRAC = 0.25    # negatives capped at this fraction of positives per clip


def label_clip(video_path: str, tag: str, device: str,
               n_windows: int, window_len: int) -> tuple[int, int]:
    from swingvision.ball import BallDetector, BallTracker, WASBDetector

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, round(fps / 30.0))    # TrackNet's native rate

    # windows spread across the middle of the clip (skip intros/outros)
    span = window_len * step
    starts = np.linspace(0.15 * total, max(0.15 * total, 0.85 * total - span),
                         n_windows).astype(int).tolist()

    out_dir = os.path.join(OUT, tag)
    os.makedirs(out_dir, exist_ok=True)

    labels: dict[str, list[float]] = {}
    locked: list[bool] = []            # per processed frame, was there a lock
    window_starts: list[int] = []      # processed-index of each window seam
    sx, sy = IN_W / W, IN_H / H
    idx = 0                            # processed-frame index, contiguous per dir

    for w_start in starts:
        window_starts.append(idx)
        detectors = [BallDetector("weights/tracknet.pt", device=device),
                     WASBDetector(device=device)]
        tracker = BallTracker(detectors, (W, H), use_bgsub=False)
        cap.set(cv2.CAP_PROP_POS_FRAMES, w_start)
        for k in range(window_len):
            for _ in range(step - 1 if k else 0):   # skip to the sampled rate
                cap.grab()
            ok, frame = cap.read()
            if not ok:
                break
            pt = tracker.update(frame)
            cv2.imwrite(os.path.join(out_dir, f"{idx:05d}.jpg"),
                        cv2.resize(frame, (IN_W, IN_H)),
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            in_window = k >= 2
            if pt is not None and in_window:
                labels[str(idx)] = [round(pt[0] * sx, 2), round(pt[1] * sy, 2)]
            locked.append(pt is not None or not in_window)  # seam frames never negative
            idx += 1
    cap.release()

    # negatives: sustained silence (no lock within +/- NEG_GUARD), spread evenly
    silent = [i for i in range(idx)
              if not any(locked[max(0, i - NEG_GUARD):i + NEG_GUARD + 1])]
    cap_n = max(1, int(len(labels) * NEG_MAX_FRAC))
    if len(silent) > cap_n:
        pick = np.linspace(0, len(silent) - 1, cap_n).round().astype(int)
        silent = [silent[i] for i in sorted(set(pick.tolist()))]

    meta = {
        "n_frames": idx,
        "labels": labels,
        "negatives": silent,
        "window_starts": window_starts,
        "provenance": {
            "tool": "relabel_train_clips.py",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ball_model": "fusion (tracknet+wasb)",
            "static_gate": "default (step<3px x5 -> fixture)",
            "bgsub": False,
            "device": device,
            "video": os.path.basename(video_path),
            "frame_step": step,
            "neg_guard": NEG_GUARD, "neg_max_frac": NEG_MAX_FRAC,
        },
    }
    with open(os.path.join(out_dir, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    print(f"{tag}: {idx} frames, {len(labels)} labels, {len(silent)} negatives",
          flush=True)
    return len(labels), len(silent)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--windows", type=int, default=3)
    ap.add_argument("--window-len", type=int, default=1200)
    ap.add_argument("--only", nargs="*", default=None,
                    help="clip ids (default: every mp4 in data/train_clips)")
    ap.add_argument("--smoke", action="store_true",
                    help="1 clip, 1 window of 120 frames — plumbing check")
    args = ap.parse_args()

    ids = args.only or sorted(
        f[:-4] for f in os.listdir(CLIPS_DIR) if f.endswith(".mp4"))
    if args.smoke:
        ids, args.windows, args.window_len = ids[:1], 1, 120

    t0 = time.time()
    tot_l = tot_n = 0
    for cid in ids:
        video = os.path.join(CLIPS_DIR, f"{cid}.mp4")
        if not os.path.exists(video):
            print(f"skip {cid}: no video", flush=True)
            continue
        nl, nn = label_clip(video, f"yt_{cid}", args.device,
                            args.windows, args.window_len)
        tot_l += nl
        tot_n += nn
    print(f"TOTAL: {tot_l} labels + {tot_n} negatives "
          f"in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
