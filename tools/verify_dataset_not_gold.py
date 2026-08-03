"""verify_dataset_not_gold.py — prove a training dataset is not gold-derived.

THE HOLE THIS CLOSES
--------------------
train_ballnet.py's gold guard is `if vid and ...`: it reads the source video from
a dataset's labels.json provenance and refuses to train on anything that shares a
video with a gold manifest. Two committed datasets — data/ball_dataset/amateur
(241 labels) and highangle (100) — record NO source video. They predate the
convention. The guard therefore passes them SILENTLY, which reads as approval in
the log, and the Lab tickets them into training by default.

CLAUDE.md records that the previous guard (`--exclude indoor_elev`) matched no
directory at all and "had been protecting nothing". An unverifiable dataset is
the same shape of problem: not known-bad, but not checked either.

A missing filename is not the only way to answer the question. The frames
themselves are on disk, and so are the gold videos. If a dataset were cut from a
gold clip its frames would BE that clip's frames, so compare the pixels.

METHOD
------
64-bit difference hash (dHash) per frame — 9x8 grayscale, compare each pixel to
its right neighbour. Robust to the resize and JPEG recompression that stand
between a 1280x720 video frame and a 512x288 dataset JPG, which a checksum is
not. Every dataset frame is compared against every 5th frame of every gold video;
consecutive video frames differ by only a bit or two, so a 5-frame stride cannot
step over a match.

READING THE NUMBER: the same frame, resized and re-encoded, lands at Hamming
distance 0-4. Different scenes sit above 10. The gap is wide and there is nothing
in between, so this is a verdict, not a judgement call.

RESULT (2026-08-03, recorded in each labels.json under provenance.gold_check):
amateur and highangle both score a MINIMUM of 12 against all six gold clips —
am_hard_utr 15, gold_shell 22, gold_clay 12, gold_am 17, yt_rally2 19,
yt_match40 12 for amateur. Neither is gold-derived. They are safe to train on.

    py tools/verify_dataset_not_gold.py --stamp
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
BALL_DATASET = REPO / "data" / "ball_dataset"
GOLD_DIR = REPO / "data" / "gold"

# Same frame, resized + re-encoded, lands at 0-4. Different scenes are 10+.
MATCH_MAX = 6


def dhash(im) -> bytes:
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    return np.packbits(g[:, 1:] > g[:, :-1]).tobytes()


def hamming(a: bytes, b: bytes) -> int:
    return bin(int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).count("1")


def gold_videos() -> list[Path]:
    """Every video a gold manifest names, so the list cannot drift from the
    benchmark the way a hardcoded one would."""
    vids = []
    for m in sorted(GOLD_DIR.glob("*.manifest.json")):
        try:
            blob = json.loads(m.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        v = blob.get("video") or (blob.get("provenance") or {}).get("video")
        if v:
            p = REPO / v if not Path(v).is_absolute() else Path(v)
            if p.is_file():
                vids.append(p)
        # fall back to the manifest's clip id
        tag = blob.get("clip") or m.name.split(".")[0]
        cand = REPO / "data" / f"{tag}.mp4"
        if cand.is_file():
            vids.append(cand)
    return sorted(set(vids))


def check(ds: Path, vids: list[Path], stride: int) -> dict:
    hashes = []
    for f in sorted(glob.glob(str(ds / "*.jpg"))):
        im = cv2.imread(f)
        if im is not None:
            hashes.append(dhash(im))
    if not hashes:
        return {"error": "no frames"}
    per_video, overall = {}, 64
    for v in vids:
        cap = cv2.VideoCapture(str(v))
        i, best = 0, 64
        while cap.grab():
            if i % stride == 0:
                ok, im = cap.retrieve()
                if ok:
                    h = dhash(im)
                    for dh in hashes:
                        d = hamming(h, dh)
                        if d < best:
                            best = d
            i += 1
        cap.release()
        per_video[v.stem] = best
        overall = min(overall, best)
        print(f"    vs {v.stem:16} min_hamming={best}", flush=True)
    return {"n_frames": len(hashes), "min_hamming": overall,
            "per_video": per_video,
            "verdict": "GOLD-DERIVED" if overall <= MATCH_MAX else "not gold"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--datasets", nargs="*",
                    help="dataset dir names (default: those with no source video)")
    ap.add_argument("--stride", type=int, default=5,
                    help="compare every Nth video frame (5 is safe: adjacent "
                         "frames differ by a bit or two)")
    ap.add_argument("--stamp", action="store_true",
                    help="write the result into each labels.json provenance")
    args = ap.parse_args()

    vids = gold_videos()
    if not vids:
        sys.exit("no gold videos found — is data/gold/*.manifest.json present?")
    print(f"gold clips: {', '.join(v.stem for v in vids)}\n")

    names = args.datasets
    if not names:
        names = []
        for d in sorted(p for p in BALL_DATASET.iterdir() if p.is_dir()):
            lp = d / "labels.json"
            if not lp.is_file():
                continue
            prov = (json.loads(lp.read_text(encoding="utf-8")).get("provenance") or {})
            if not prov.get("video"):
                names.append(d.name)
        print(f"datasets with NO recorded source video: {', '.join(names) or '(none)'}\n")

    rc = 0
    for name in names:
        ds = BALL_DATASET / name
        print(f"[{name}]", flush=True)
        res = check(ds, vids, args.stride)
        if res.get("error"):
            print(f"    {res['error']}")
            continue
        print(f"  -> min_hamming={res['min_hamming']} over {res['n_frames']} "
              f"frames: {res['verdict']}")
        if res["verdict"] == "GOLD-DERIVED":
            rc = 1
        if args.stamp:
            lp = ds / "labels.json"
            blob = json.loads(lp.read_text(encoding="utf-8"))
            blob.setdefault("provenance", {})["gold_check"] = {
                "tool": "verify_dataset_not_gold.py",
                "date": time.strftime("%Y-%m-%d"),
                "method": f"64-bit dHash vs every {args.stride}th frame of every gold clip",
                "checked_against": sorted(res["per_video"]),
                "min_hamming": res["min_hamming"],
                "match_threshold": MATCH_MAX,
                "verdict": res["verdict"],
            }
            lp.write_text(json.dumps(blob), encoding="utf-8")
            print(f"  -> stamped provenance.gold_check")
    sys.exit(rc)


if __name__ == "__main__":
    main()
