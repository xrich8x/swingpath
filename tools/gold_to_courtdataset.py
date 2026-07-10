"""Convert human COURT gold labels into CourtNet training data.

Each gold-labeled frame already carries all 14 court keypoints (in the frame's
pixel space). This turns the TRAIN clips into data/court_dataset/<clip>/ entries
(640x360 jpgs + labels.json in COURT_KP_LANDMARKS order) that train_courtnet.py
consumes directly — a much stronger signal than the single-calibration projection
build_court_dataset.py uses.

The court TEST clips are HARD-EXCLUDED so the retrain can never see them
(train/test leak guard). Off-frame keypoints are kept as-is: train_courtnet's
heatmap builder zeroes targets that fall far outside the frame and its evaluator
masks them, so CourtNet simply isn't supervised on corners it can't represent.

  backend/.venv/Scripts/python.exe tools/gold_to_courtdataset.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
from swingvision.calibration import COURT_KP_LANDMARKS  # noqa: E402

GOLD = REPO / "data" / "gold"
OUT = REPO / "data" / "court_dataset"
IN_W, IN_H = 640, 360

# Held-out court TEST set — NEVER add these to training (see court-tracking-priorities).
TEST_CLIPS = {"am_ntrp45_courtlevel", "am_rec30", "am_beginner"}


def convert(clip: str) -> int:
    man = json.loads((GOLD / f"{clip}.court.manifest.json").read_text(encoding="utf-8"))
    labs = json.loads((GOLD / f"{clip}.court.labels.json").read_text(encoding="utf-8"))["labels"]
    W, H = man["width"], man["height"]
    sx, sy = IN_W / W, IN_H / H
    out_dir = OUT / clip
    out_dir.mkdir(parents=True, exist_ok=True)

    labels: dict[str, list] = {}
    seq = 0
    for frame_no in sorted(int(k) for k in labs):
        v = labs[str(frame_no)]
        if v.get("court") is not True:
            continue  # skip unusable frames
        kp = v["keypoints"]
        if not all(n in kp for n in COURT_KP_LANDMARKS):
            continue
        img = cv2.imread(str(GOLD / "frames" / clip / f"f{frame_no:05d}.jpg"))
        if img is None:
            continue
        cv2.imwrite(str(out_dir / f"{seq:05d}.jpg"),
                    cv2.resize(img, (IN_W, IN_H)), [cv2.IMWRITE_JPEG_QUALITY, 92])
        labels[str(seq)] = [[round(kp[n][0] * sx, 2), round(kp[n][1] * sy, 2)]
                            for n in COURT_KP_LANDMARKS]
        seq += 1

    (out_dir / "labels.json").write_text(json.dumps({
        "n_frames": seq, "kp_names": list(COURT_KP_LANDMARKS), "labels": labels,
        "source": f"gold {clip} (human court labels)",
    }), encoding="utf-8")
    return seq


def main() -> None:
    clips = sorted(p.name[:-len(".court.labels.json")]
                   for p in GOLD.glob("*.court.labels.json"))
    train = [c for c in clips if c not in TEST_CLIPS]
    print(f"TEST (excluded): {sorted(TEST_CLIPS)}")
    total = 0
    for c in train:
        n = convert(c)
        total += n
        print(f"  {c:22s} -> {n} training frames")
    print(f"total amateur training frames: {total}")


if __name__ == "__main__":
    main()
