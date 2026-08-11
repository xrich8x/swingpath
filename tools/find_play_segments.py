"""find_play_segments.py — find the parts of a recording that are actually tennis.

WHY THIS EXISTS
---------------
`trim_clip.py` can cut a video once you know where to cut. On a 30-minute match
upload nobody knows: the tennis is interrupted by a piece to camera, a bench
chat, a title card, a slow-motion replay from a different angle. Sampling those
costs perception time and, worse, spends a human's label budget on frames with
no ball in them.

THE SIGNAL: DETECT WHAT IS BEING REMOVED, NOT WHAT IS BEING KEPT
----------------------------------------------------------------
The thing to cut out of a match upload is a PIECE TO CAMERA — the presenter
addressing the viewer, a bench chat, an intro. Its defining feature is a human
face occupying a large part of the frame. In a tennis wide shot the players are
2-4% of frame height and their faces are barely resolvable, so "is there a big
face here" separates the two cases directly.

TWO SCENE-SIMILARITY VERSIONS WERE TRIED FIRST AND BOTH FAILED, MEASURED
------------------------------------------------------------------------
The obvious approach is that a fixed camera makes every play frame look like
every other, so anything far from the clip's median frame is an interruption.

  1. Raw brightness distance from the temporal median. Over-cut on 6 of 9 clips.
     Cause, found by rendering the DISCARDED frames: an outdoor match runs half
     an hour, tree shadows crawl across the court and exposure drifts, so the
     same court at 10:15 is far from the same court at 3:09 in brightness while
     being identical in content.
  2. Correlation on a locally contrast-normalised high-pass, thresholded by Otsu
     and only applied when the score distribution is bimodal. Better — three
     clips that are tennis end to end were correctly left whole — but still cut
     genuine play on 5 of 9, and on one clip it discarded TEN MINUTES of rallies.
     Cause: a player near the camera, or a shadowed half-court, changes the frame
     structurally as much as a different scene does.

Both failures share a root: "looks unlike the average frame" is not the same
property as "is not tennis", and the gap between them is exactly where a
half-hour outdoor recording lives. Rather than tune a third threshold on the
same wrong quantity, this detects the interruption itself.

The face test is positive evidence, so its failure mode is the safe one: an
undetected face keeps footage that should have been cut, which costs a little
perception time, while the similarity versions DELETED rallies.

It does miss: a frontal cascade does not fire on a face in profile, so a bench
chat filmed side-on survives. `--drops` takes a JSON of hand-specified ranges
per clip, subtracted from whatever the detector found — the same "tool proposes,
human disposes" split used for the HUD masks, and for the same reason: on a
fixed pool of clips a person with a contact sheet is more reliable than a third
threshold, and the record of what was cut stays auditable either way.

    py tools/find_play_segments.py --dir data/incoming
    py tools/find_play_segments.py --dir data/incoming --write --out data/train_clips

Thumbnails are pulled with one sequential ffmpeg pass per clip at 1 fps and
480 px wide, so a 30-minute 1080p60 file costs seconds rather than a full decode.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

THUMB_W = 480           # faces need pixels; 160 was enough for the old scene test
MIN_SEG_S = 45.0        # shorter than this is a replay or a glitch, not a passage of play
MERGE_GAP_S = 20.0      # a changeover inside one passage is not a boundary
FACE_FRAC = 0.14        # a face taller than this share of the frame is someone
                        # talking to the camera. A player in a tennis wide shot is
                        # 2-4% of frame height in total, face far less.
PAD_S = 2.0             # drop a moment either side of an interruption: the cut to
                        # and from it is a swing, a stand-up, a walk toward the lens


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def thumbnails(video: Path, fps: float = 1.0):
    """[(second, gray array)] via one sequential ffmpeg pass."""
    import cv2
    import numpy as np

    with tempfile.TemporaryDirectory() as td:
        cmd = [ffmpeg_exe(), "-v", "error", "-i", str(video),
               "-vf", f"fps={fps},scale={THUMB_W}:-2", "-q:v", "6",
               str(Path(td) / "t%06d.jpg")]
        subprocess.run(cmd, check=True, capture_output=True)
        out = []
        for p in sorted(Path(td).glob("t*.jpg")):
            im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if im is not None:
                out.append(((int(p.stem[1:]) - 1) / fps, im.astype(np.float32)))
    return out


def face_fraction(thumbs):
    """Tallest detected face per second, as a fraction of frame height."""
    import cv2

    casc = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    out = []
    for _t, g in thumbs:
        u = g.astype("uint8")
        h = u.shape[0]
        # minSize keeps it off the players: a face 5% of frame height in a wide
        # tennis shot is noise, and scanning for it costs time as well as
        # precision.
        faces = casc.detectMultiScale(u, 1.15, 5,
                                      minSize=(int(0.07 * h), int(0.07 * h)))
        out.append(max((f[3] / h for f in faces), default=0.0))
    return out


def segments(thumbs, *, min_seg_s=MIN_SEG_S, merge_gap_s=MERGE_GAP_S,
             face_frac=FACE_FRAC, pad_s=PAD_S):
    """[(start_s, end_s)] of the passages with no piece to camera in them."""
    import numpy as np

    if len(thumbs) < 30:
        return [], []
    ts = np.array([t for t, _ in thumbs])
    ff = np.array(face_fraction(thumbs))
    bad = ff >= face_frac
    # Grow each interruption by pad_s so the walk toward the lens goes with it.
    if pad_s > 0 and bad.any():
        k = max(1, int(round(pad_s / max(ts[1] - ts[0], 1e-6))))
        grown = bad.copy()
        for i in np.flatnonzero(bad):
            grown[max(0, i - k):i + k + 1] = True
        bad = grown
    play = ~bad

    segs = []
    i = 0
    while i < len(play):
        if not play[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(play) and play[j + 1]:
            j += 1
        segs.append([float(ts[i]), float(ts[j])])
        i = j + 1
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] <= merge_gap_s:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [tuple(s) for s in merged if s[1] - s[0] >= min_seg_s], ff.tolist()


def subtract(segs, drops, *, min_seg_s=MIN_SEG_S):
    """Remove hand-specified ranges from the detected segments."""
    out = []
    for a, b in segs:
        pieces = [(a, b)]
        for da, db in drops:
            nxt = []
            for pa, pb in pieces:
                if db <= pa or da >= pb:
                    nxt.append((pa, pb))
                    continue
                if da > pa:
                    nxt.append((pa, da))
                if db < pb:
                    nxt.append((db, pb))
            pieces = nxt
        out += pieces
    return [s for s in out if s[1] - s[0] >= min_seg_s]


def hms(s: float) -> str:
    return f"{int(s) // 60}:{int(s) % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=str(REPO / "data/incoming"))
    ap.add_argument("--out", default=str(REPO / "data/train_clips"))
    ap.add_argument("--write", action="store_true",
                    help="actually cut the segments out with trim_clip.py")
    ap.add_argument("--fast", action="store_true", default=True,
                    help="stream copy. Correct HERE: the cut only has to drop a "
                         "piece to camera, and a boundary landing a keyframe early "
                         "costs nothing when the pipeline samples from the middle")
    ap.add_argument("--min-seg", type=float, default=MIN_SEG_S)
    ap.add_argument("--face-frac", type=float, default=FACE_FRAC)
    ap.add_argument("--drops", default=str(REPO / "data/play_drops.json"),
                    help="JSON {clip id: [[start_s, end_s], ...]} of ranges to cut that the face test misses - a profile view defeats a frontal cascade")
    ap.add_argument("--json", default=str(REPO / "data/output/play_segments.json"))
    args = ap.parse_args()

    dp = Path(args.drops)
    drops = json.loads(dp.read_text(encoding="utf-8")) if dp.is_file() else {}
    drops = {k: v for k, v in drops.items() if not k.startswith("_")}
    if drops:
        print(f"hand-specified drops for {sorted(drops)}")

    vids = [p for p in sorted(Path(args.dir).iterdir())
            if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi", ".webm")]
    report = {}
    for v in vids:
        yid = v.stem.split("[")[-1].rstrip("]") or v.stem[:16]
        th = thumbnails(v)
        segs, _d = segments(th, min_seg_s=args.min_seg,
                            face_frac=args.face_frac)
        if drops.get(yid):
            segs = subtract(segs, drops[yid], min_seg_s=args.min_seg)
        total = sum(b - a for a, b in segs)
        dur = th[-1][0] if th else 0.0
        report[yid] = {"source": v.name, "duration_s": round(dur, 1),
                       "segments": [[round(a, 1), round(b, 1)] for a, b in segs],
                       "kept_s": round(total, 1),
                       "kept_pct": round(100 * total / dur, 1) if dur else 0.0}
        print(f"{yid:<14} {hms(dur):>7} total -> {len(segs)} segment(s), "
              f"{hms(total)} kept ({report[yid]['kept_pct']:.0f}%)  "
              f"{[f'{hms(a)}-{hms(b)}' for a, b in segs]}")

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(
        {"tool": "find_play_segments.py", "created": time.strftime("%Y-%m-%d %H:%M:%S"),
         "params": {"min_seg_s": args.min_seg, "merge_gap_s": MERGE_GAP_S,
                    "face_frac": args.face_frac, "pad_s": PAD_S, "thumb_w": THUMB_W,
                    "manual_drops": drops},
         "clips": report}, indent=1), encoding="utf-8")
    print(f"\nwrote {args.json}")

    if not args.write:
        print("Analysis only. Check the segments, then re-run with --write.")
        return

    import trim_clip
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for yid, r in report.items():
        src = Path(args.dir) / r["source"]
        for k, (a, b) in enumerate(r["segments"], 1):
            name = f"{yid}.mp4" if len(r["segments"]) == 1 else f"{yid}_s{k}.mp4"
            dst = outdir / name
            print(f"  cutting {name}  {hms(a)}-{hms(b)}")
            trim_clip.trim(src, dst, a, b, fast=args.fast)
    print("\nDone. Register them in the Lab's Clips tab.")


if __name__ == "__main__":
    main()
