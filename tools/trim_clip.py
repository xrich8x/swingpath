"""trim_clip.py — cut a long recording down to the part with tennis in it.

WHY THIS EXISTS
---------------
The Lab could sample frames from inside chosen time ranges, but it could never cut
the video, so an hour of phone footage stayed an hour: every perception pass
decoded the warm-up, the breaks and the walk back to the bench, and every frame
budget was spent proportionally on them. Trimming is the one operation that makes
everything downstream cheaper, and it had no button.

    py tools/trim_clip.py data/incoming/long.mp4 --start 2:00 --end 12:30

Writes alongside the input by default (`long_trim.mp4`), so the result lands in
whatever directory the Lab is already watching.

WHY IT RE-ENCODES BY DEFAULT, WHICH LOOKS LIKE THE SLOW CHOICE
--------------------------------------------------------------
With `-ss` before `-i`, ffmpeg seeks to the nearest keyframe AT OR BEFORE the
requested start. Under `-c copy` the cut therefore begins EARLY, and because the
duration is then counted from that earlier point, the clip also ENDS early — on a
5 s GOP that silently loses the last couple of seconds, which on a rally clip is
the shot you cared about. This exact bug was found and fixed once already in the
highlights cutter; it is not hypothetical.

Re-encoding makes the seek frame-accurate (ffmpeg decodes from the keyframe and
discards up to the requested time), so both ends land where asked. The fast seek
is kept, so only the requested span is encoded — a 10-minute cut out of an hour
costs about a minute, not an hour.

`--fast` restores stream copy for when speed matters more than the boundaries.
It prints what it is trading.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def parse_time(s: str) -> float:
    """Accept 90, 1:30, 01:30.5, 1:02:03 — the forms a person actually types."""
    s = (s or "").strip()
    if not s:
        raise ValueError("empty time")
    if not re.fullmatch(r"(\d+:)?(\d+:)?\d+(\.\d+)?", s):
        raise ValueError(f"cannot read time {s!r}; use 90, 1:30 or 1:02:03")
    parts = [float(p) for p in s.split(":")]
    total = 0.0
    for p in parts:                       # left to right: h, m, s (or m, s, or s)
        total = total * 60 + p
    return total


def hms(t: float) -> str:
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def trim(src: Path, dst: Path, start: float, end: float, fast: bool = False) -> None:
    if end <= start:
        raise SystemExit(f"end ({hms(end)}) must be after start ({hms(start)})")
    ff = ffmpeg_exe()
    dur = end - start
    if fast:
        print("WARNING --fast uses stream copy: the cut snaps to the nearest "
              "keyframe at or before the start, so the clip can begin early AND "
              "end early (by up to one GOP, often several seconds).")
        codec = ["-c", "copy"]
    else:
        codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart"]
    cmd = [ff, "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}",
           *codec, str(dst)]
    print(f"{src.name}  {hms(start)} -> {hms(end)}  ({hms(dur)})  ->  {dst}")
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True)
    tail = "\n".join((r.stdout or "").splitlines()[-12:])
    if r.returncode != 0 or not dst.is_file() or dst.stat().st_size == 0:
        raise SystemExit(f"ffmpeg failed (exit {r.returncode})\n{tail}")
    print(f"wrote {dst}  ({dst.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--start", default="0", help="0, 90, 1:30 or 1:02:03")
    ap.add_argument("--end", required=True, help="same formats as --start")
    ap.add_argument("--out", default=None,
                    help="default: <input>_trim.mp4 beside the input, so it lands "
                         "in the directory the Lab already watches")
    ap.add_argument("--fast", action="store_true",
                    help="stream copy instead of re-encoding: much faster, but "
                         "both ends can land early. See the module docstring")
    args = ap.parse_args()

    src = Path(args.video).resolve()
    if not src.is_file():
        raise SystemExit(f"no such video: {args.video}")
    dst = Path(args.out).resolve() if args.out else src.with_name(src.stem + "_trim.mp4")
    if dst == src:
        raise SystemExit("refusing to overwrite the source video")
    dst.parent.mkdir(parents=True, exist_ok=True)
    trim(src, dst, parse_time(args.start), parse_time(args.end), args.fast)


if __name__ == "__main__":
    main()
