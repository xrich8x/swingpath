"""Turn HUMAN ball labels into BallNet training data.

This closes the loop the project was missing. Until now human clicks could only
ever become a TEST set (data/gold), and the training set was entirely
pseudo-labels produced by the tracker itself. ML_PLAYBOOK calls that the
pseudo-label ceiling: a student cannot beat its teacher, and the teacher cannot
see the 2 px far-court ball, so no amount of retraining teaches it. The only fix
is human labels in the TRAINING set — which is what this script produces.

    py tools/labels_to_dataset.py --clip am_indoor2 \
        --video data/incoming/am_indoor2.mp4 \
        --labels data/labels/am_indoor2.labels.json

THE TRAIN/TEST LINE IS STILL ABSOLUTE
-------------------------------------
Human labels live in one of two places and they never mix:

    data/gold/    TEST. Hand-clicked, held out, the only honest scoreboard.
                  This script REFUSES to read from here.
    data/labels/  TRAIN. Also hand-clicked, but declared training material at
                  intake, and fair game for this converter.

Both are produced by the same labelling UI, so the clicking is identical; the
difference is which pool the clip was assigned to, which tools/lab_server.py
makes a one-way choice. As a second, independent check, the output carries
`provenance.video`, and train_ballnet.assert_no_gold_leak() reads exactly that
field — so if a gold clip ever reaches this script anyway, training still aborts.

WHY TRIPLETS
------------
BallNet consumes 3-frame windows and BallWindows._frame() reads i, i-1, i-2 as
consecutive files on disk. Its "missing predecessor" fallback re-reads the same
missing path and yields None, so a scattered set of labelled frames would feed
the model nothing. Human labels ARE scattered (stratified sampling picks frame
0, 116, 233...), so each labelled source frame f is written as a contiguous
triplet f-2, f-1, f at output indices 3k, 3k+1, 3k+2, and the label is attached
to 3k+2. That reproduces the window the model expects, with real motion in it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]

IN_W, IN_H = 512, 288      # BallNet's input size; must match train_ballnet.py
GOLD_DIR = REPO / "data" / "gold"


def refuse_if_contaminated(manifest_path: Path, *, force: bool = False) -> None:
    """Stop if a queue's manifest declares its labels unusable.

    Human labels are never deleted — they are ground truth, and the pilot's
    HUD clicks are the evidence for the masking work. But "there is a paragraph
    about this in an evidence file" is not a safeguard: nothing stops a future
    build consuming them, and a label placed on a scoreboard teaches the
    detector that a scoreboard is a ball. So the manifest carries the verdict
    and the converters refuse it mechanically.
    """
    p = Path(manifest_path)
    if not p.is_file():
        return
    try:
        why = json.loads(p.read_text(encoding="utf-8")).get("contaminated")
    except (json.JSONDecodeError, OSError):
        return
    if why and not force:
        raise SystemExit(
            f"REFUSING: {p.name} is marked contaminated.\n  {why}\n"
            "These labels are kept as evidence, not as training data. Re-label "
            "the queue (tools/select_farcourt_labels.py applies the HUD mask now) "
            "or pass --force if you have read the evidence and mean it.")


def _sibling_manifest(labels_path: Path) -> Path:
    """data/labels/<clip>.labels.json -> data/labels/<clip>.manifest.json"""
    name = labels_path.name
    stem = name[:-len(".labels.json")] if name.endswith(".labels.json") \
        else labels_path.stem
    return labels_path.with_name(f"{stem}.manifest.json")


def gold_videos() -> set[str]:
    """Source videos of every hand-labelled BALL gold clip, lower-cased.

    Same derivation as train_ballnet.gold_source_videos(), including its skip of
    *.court.manifest.json — court corners are not a ball benchmark.
    """
    out = set()
    for p in GOLD_DIR.glob("*.manifest.json"):
        if ".court." in p.name:
            continue
        try:
            man = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if man.get("video"):
            out.add(Path(man["video"]).name.lower())
    return out


def build(clip: str, video: Path, labels_path: Path, out_root: Path,
          quality: int = 92) -> dict:
    data = json.loads(labels_path.read_text(encoding="utf-8"))
    raw = data.get("labels", {})

    # Split the human verdicts. "unsure" is dropped outright: a frame a human
    # could not call is not ground truth, and training on it teaches noise.
    positives, negatives, unsure = {}, [], 0
    for k, v in raw.items():
        if v.get("unsure"):
            unsure += 1
        elif v.get("ball") and v.get("x") is not None:
            positives[int(k)] = (float(v["x"]), float(v["y"]))
        elif v.get("ball") is False:
            negatives.append(int(k))
    wanted = sorted(set(positives) | set(negatives))
    if not wanted:
        raise SystemExit(f"{labels_path} has no usable labels "
                         f"({unsure} unsure, {len(raw)} total)")

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sx, sy = IN_W / W, IN_H / H

    out_dir = out_root / clip
    out_dir.mkdir(parents=True, exist_ok=True)

    out_labels: dict[str, list[float]] = {}
    out_negs: list[int] = []
    written = skipped = 0

    for k, f in enumerate(wanted):
        base = 3 * k
        trip = []
        # Seek once to f-2 and read forward: three sequential reads are far
        # cheaper than three seeks, and they guarantee truly consecutive frames.
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, f - 2))
        for _ in range(3):
            ok, frame = cap.read()
            if not ok:
                break
            trip.append(frame)
        if len(trip) < 3:
            skipped += 1        # too close to the end of the clip
            continue
        for j, frame in enumerate(trip):
            cv2.imwrite(str(out_dir / f"{base + j:05d}.jpg"),
                        cv2.resize(frame, (IN_W, IN_H)),
                        [cv2.IMWRITE_JPEG_QUALITY, quality])
        written += 3
        newest = base + 2                     # the labelled frame itself
        if f in positives:
            x, y = positives[f]
            out_labels[str(newest)] = [round(x * sx, 2), round(y * sy, 2)]
        else:
            out_negs.append(newest)
    cap.release()

    meta = {
        "n_frames": written,
        "labels": out_labels,
        "negatives": sorted(out_negs),
        "provenance": {
            "tool": "labels_to_dataset.py",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            # train_ballnet.assert_no_gold_leak() reads this exact field.
            "video": Path(video).name,
            "source_labels": str(labels_path.relative_to(REPO))
            if labels_path.is_relative_to(REPO) else str(labels_path),
            "human_labels": True,
            "label_tool": data.get("tool"),
            "src_wh": [W, H],
            "layout": "triplet: each labelled frame f -> f-2,f-1,f at 3k,3k+1,3k+2",
            "unsure_dropped": unsure,
            "frames_skipped_at_clip_end": skipped,
        },
    }
    (out_dir / "labels.json").write_text(json.dumps(meta), encoding="utf-8")
    return {"clip": clip, "out": str(out_dir), "frames": written,
            "positives": len(out_labels), "negatives": len(out_negs),
            "unsure_dropped": unsure, "skipped": skipped}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clip", required=True, help="dataset dir name to create")
    ap.add_argument("--video", required=True)
    ap.add_argument("--labels", required=True,
                    help="a *.labels.json from data/labels (NOT data/gold)")
    ap.add_argument("--out", default="data/ball_dataset")
    ap.add_argument("--allow-gold", action="store_true",
                    help=argparse.SUPPRESS)   # escape hatch; deliberately hidden
    ap.add_argument("--force", action="store_true",
                    help="build even from a queue whose manifest is marked "
                         "contaminated")
    args = ap.parse_args()

    video = (REPO / args.video).resolve() if not Path(args.video).is_absolute() \
        else Path(args.video)
    labels = (REPO / args.labels).resolve() if not Path(args.labels).is_absolute() \
        else Path(args.labels)

    if not video.is_file():
        raise SystemExit(f"no such video: {video}")
    if not labels.is_file():
        raise SystemExit(f"no such labels file: {labels}")

    refuse_if_contaminated(_sibling_manifest(labels), force=args.force)

    # Refuse the benchmark, twice over: by where the labels live, and by whether
    # the video backs a gold manifest. Either one alone could be worked around
    # by moving a file; together they mean an accident has to be deliberate.
    if not args.allow_gold:
        try:
            in_gold_dir = labels.is_relative_to(GOLD_DIR)
        except ValueError:
            in_gold_dir = False
        if in_gold_dir:
            raise SystemExit(
                f"REFUSING: {labels} is in data/gold, which is the TEST set.\n"
                "Training on it would make every benchmark number meaningless.\n"
                "Label the clip into data/labels instead (declare it 'train' in "
                "the Lab).")
        if video.name.lower() in gold_videos():
            raise SystemExit(
                f"REFUSING: {video.name} is the source video of a gold clip.\n"
                "The same footage cannot be both the exam and the revision.")

    out_root = (REPO / args.out) if not Path(args.out).is_absolute() \
        else Path(args.out)
    res = build(args.clip, video, labels, out_root)
    print(json.dumps(res, indent=1))
    print(f"\n{res['positives']} human ball labels + {res['negatives']} negatives "
          f"-> {res['out']}")
    print("Now visible to train_ballnet.py as a dataset dir. Its gold guard will "
          "re-check the source video independently.")


if __name__ == "__main__":
    main()
