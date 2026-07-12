"""Pull court-labeling frames straight from YouTube (no ffmpeg, no full download).

We only need a handful of STILL frames per clip to label the court, so this reads
the 360p progressive stream URL (yt-dlp -f 18) with OpenCV and seeks to the frames
it wants — a few MB of range requests, not the whole match.

Two modes:
  --probe            grab 2 sample frames per candidate -> data/amateur_clips/_probe/
                     (so a human/Claude can eyeball framing before committing to label)
  --extract CLIP...  build the gold label set for the named keeper clips:
                     data/gold/frames/<clip>/f<NNNNN>.jpg + <clip>.court.manifest.json
                     (identical layout to court_gold_frames.py -> gold_label_server.py)

Candidates were found by web search for amateur matches across surfaces/angles.
Usage (repo root):
  backend/.venv/Scripts/python.exe tools/court_youtube_frames.py --probe
  backend/.venv/Scripts/python.exe tools/court_youtube_frames.py --extract am_wingfield_clay am_grass1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# clip_name -> (youtube_id, "surface / notes"). Names avoid clashing with the
# existing gold clips (am_ntrp30, am_usta45, ...).
CANDIDATES: dict[str, tuple[str, str]] = {
    "am_wingfield_clay": ("5JllDa0tjlI", "clay, elevated behind-baseline (Wingfield)"),
    "am_indoor_hard1":   ("a2L6RQS3c1A", "indoor hard, amateur singles"),
    "am_fr_sud":         ("Z_ns84WcgMo", "French amateur 'le Sud' (likely clay)"),
    "am_indoor_hard2":   ("_Dbwk4bxr8U", "indoor league match"),
    "am_grass1":         ("hzU462In0Tk", "grass court, amateur"),
    "am_usta40":         ("tg17W0Yvm8Q", "USTA 4.0 singles, outdoor hard"),
    "am_usta45final":    ("PDBe5CuAA1Q", "USTA 4.5 singles final, outdoor hard"),
    "am_lk35":           ("Ln4RWFDsAhU", "amateur LK / NTRP 3.5 full match"),
    "am_ntrp45w":        ("a6szrqcFT6c", "NTRP 4.5/4.0 women's singles"),
    "am_ntrp50":         ("aOmoEClVnQw", "NTRP 5.0 singles full set"),
    "am_ntrp35m":        ("w3GrCpNxzPE", "USTA NTRP 3.5 male player"),
    "am_usta60":         ("pg7jA45MBmM", "amateur vs USTA 6.0"),
    "am_clay_test":      ("e6FldS-3MMU", "artificial clay court"),
}

_FMT = "18/bestvideo[height<=480][vcodec^=avc1]/best[height<=480]"


def stream_url(vid: str) -> str | None:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "-f", _FMT, "-g",
             f"https://www.youtube.com/watch?v={vid}"],
            capture_output=True, text=True, timeout=90)
        url = out.stdout.strip().splitlines()
        return url[0] if url and url[0].startswith("http") else None
    except Exception:
        return None


def open_stream(vid: str):
    import cv2
    url = stream_url(vid)
    if not url:
        return None
    # Force the FFMPEG backend: some googlevideo URLs contain substrings OpenCV
    # mistakes for an image-sequence printf pattern and routes to CAP_IMAGES,
    # which then fails to open the stream.
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return None
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cap, n, fps, w, h


def probe(clips: list[str]) -> None:
    import cv2
    outdir = REPO / "data" / "amateur_clips" / "_probe"
    outdir.mkdir(parents=True, exist_ok=True)
    for clip in clips:
        vid, notes = CANDIDATES[clip]
        st = open_stream(vid)
        if st is None:
            print(f"  {clip:18s} FAILED to open ({vid}) - {notes}")
            continue
        cap, n, fps, w, h = st
        for tag, frac in (("a", 0.35), ("b", 0.62)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * frac) if n else 3000)
            ok, im = cap.read()
            if ok:
                cv2.imwrite(str(outdir / f"{clip}_{tag}.jpg"), im)
        cap.release()
        print(f"  {clip:18s} OK  {w}x{h} {n/fps/60:.1f}min  - {notes}")
    print(f"\nprobe frames -> {outdir}")


def extract(clips: list[str], n_frames: int) -> None:
    import cv2
    import numpy as np
    gold = REPO / "data" / "gold"
    for clip in clips:
        vid, notes = CANDIDATES[clip]
        st = open_stream(vid)
        if st is None:
            print(f"  {clip}: FAILED to open ({vid})")
            continue
        cap, n, fps, w, h = st
        lo, hi = int(0.02 * n), max(int(0.98 * n) - 1, 1)
        frame_nums = sorted(set(int(x) for x in
                                np.linspace(lo, max(lo, hi), n_frames).round().astype(int)))
        frames_dir = gold / "frames" / clip
        frames_dir.mkdir(parents=True, exist_ok=True)
        got = 0
        for fn in frame_nums:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
            ok, im = cap.read()
            if ok:
                cv2.imwrite(str(frames_dir / f"f{fn:05d}.jpg"), im,
                            [cv2.IMWRITE_JPEG_QUALITY, 92])
                got += 1
        cap.release()
        manifest = {
            "clip": clip, "kind": "court",
            "video": f"https://www.youtube.com/watch?v={vid}",
            "source": "youtube-stream", "youtube_id": vid, "notes": notes,
            "width": w, "height": h, "fps": fps, "video_frames": n,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "params": {"n": n_frames, "sampling": "uniform"},
            "frames": [{"frame": fn, "bucket": "court"} for fn in frame_nums],
        }
        (gold / f"{clip}.court.manifest.json").write_text(
            json.dumps(manifest, indent=1), encoding="utf-8")
        print(f"  {clip:18s} {got}/{len(frame_nums)} frames  {w}x{h}  - {notes}")
    print("\nNext: py tools/gold_label_server.py  ->  \"Court quality\" page")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="grab 2 sample frames per candidate")
    ap.add_argument("--extract", nargs="*", default=None, help="build label sets for these clips")
    ap.add_argument("--n", type=int, default=18, help="frames per clip on extract (default 18)")
    ap.add_argument("--only", nargs="*", default=None, help="restrict --probe to these clips")
    args = ap.parse_args()

    if args.extract is not None:
        bad = [c for c in args.extract if c not in CANDIDATES]
        if bad:
            raise SystemExit(f"unknown clips: {bad}\nknown: {list(CANDIDATES)}")
        extract(args.extract, args.n)
    elif args.probe:
        probe(args.only or list(CANDIDATES))
    else:
        print("known candidates:")
        for c, (vid, notes) in CANDIDATES.items():
            print(f"  {c:18s} {vid}  {notes}")
        print("\npass --probe to sample frames, or --extract CLIP... to build label sets")


if __name__ == "__main__":
    main()
