"""split_by_serve.py — cut a long match recording into one clip per point.

A 25-minute upload is one court seen once. What downstream work wants is many
short clips, each starting just before a serve, so frame sampling lands on play
instead of on the walk back to the baseline.

THE SIGNAL: A POINT STARTS WHEN MOTION RISES OUT OF A LULL
-----------------------------------------------------------
Between points the players walk, collect balls and towel off — motion is low and
diffuse. A serve begins a burst that lasts until the point ends. So: build a
motion trace, find the lulls, and cut just before each rise out of one. The cut
point is the *end of the lull*, which is a serve to within a second or so.

This is deliberately NOT serve DETECTION. It never asks "is that a serve motion";
it asks "did the court go quiet and then busy". That is enough to start a clip at
a serve, and it degrades into "starts at the beginning of a rally" rather than
into nonsense.

WHY NOT THE BURNED-IN SCOREBOARD, WHICH WOULD BE EXACT
-------------------------------------------------------
These uploads carry a scoreline graphic, and it ticks over on every point — a
perfect boundary, free. It is out of bounds here for the reason CLAUDE.md gives:
that is somebody's data entry about the game, not a measurement of the court, it
encodes their latency and mistakes, and it does not exist on the phone clip this
project actually targets. A motion rule works on any footage.

    py tools/split_by_serve.py "data/incoming/Raw - Do Not Process/match.mp4" \\
        --out data/incoming/Shell --prefix mpc_mixed --n 12

Every cut records its source in data/incoming/lineage.json so that N clips of one
recording are never counted as N recordings — the double-count eval/recordings.py
exists to stop.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]


def _ascii(s: str) -> str:
    """YouTube titles carry glyphs a cp1252 console cannot encode. Printing must
    never be the thing that kills a 25-minute job - it already was, once."""
    return s.encode("ascii", "replace").decode("ascii")
LINEAGE = REPO / "data" / "incoming" / "lineage.json"

PROBE_W, PROBE_H = 160, 90      # motion needs shape, not detail
PROBE_FPS = 5.0


def probe(video: Path) -> tuple[float, float]:
    """(duration_s, fps) via ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=duration,avg_frame_rate",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    num, den = (st.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    return float(st.get("duration") or 0.0), fps


def motion_trace(video: Path) -> np.ndarray:
    """Mean absolute frame difference at PROBE_FPS, downscaled.

    ffmpeg does the decode and the scaling, which is far faster than pulling 4K
    frames into Python only to throw the pixels away."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(video),
           "-vf", f"fps={PROBE_FPS},scale={PROBE_W}:{PROBE_H}",
           "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    n = PROBE_W * PROBE_H
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=n * 64)
    prev, vals = None, []
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        f = np.frombuffer(buf, np.uint8).astype(np.int16).reshape(PROBE_H, PROBE_W)
        if prev is not None:
            vals.append(float(np.abs(f - prev).mean()))
        prev = f
    p.stdout.close(); p.wait()
    return np.asarray(vals, np.float32)


def point_starts(trace: np.ndarray, min_lull_s=1.5, min_point_s=2.0):
    """[(rise_index, end_index)] where motion rises out of a lull and stays up.

    Two details that were measured, not assumed, on a 20-minute doubles upload:

    CAMERA CUTS ARE CLIPPED OUT OF THE LEVEL ESTIMATE. A hard cut produces a
    frame difference an order of magnitude above any rally (p99 = 26.6 against a
    median of 1.5 on that clip), which drags a percentile threshold upward until
    real rallies read as quiet. Clipping at p99 before thresholding fixes it.

    THE THRESHOLD IS A PERCENTILE OF THIS RECORDING'S OWN TRACE. A dim indoor
    hall and a bright outdoor court sit at completely different absolute motion
    levels; a constant works on one and not the other.

    min_point_s=2.0 is the knob that sets how many clips you get: at 4.0 s that
    clip yielded 6 points, at 2.5 s it yielded 12, at 1.5 s it yielded 24. Short
    exchanges are still points, so the bar is low and `--n` does the selecting."""
    if trace.size < 10:
        return []
    t = np.minimum(trace, np.percentile(trace, 99.0))
    k = max(1, int(round(PROBE_FPS * 0.6)))
    sm = np.convolve(t, np.ones(k) / k, mode="same")
    lo, hi = np.percentile(sm, 35), np.percentile(sm, 70)
    busy = sm >= (lo + hi) / 2.0

    ml, mp = int(round(min_lull_s * PROBE_FPS)), int(round(min_point_s * PROBE_FPS))
    out, i, n = [], 0, len(busy)
    while i < n:
        if busy[i]:
            i += 1
            continue
        j = i
        while j < n and not busy[j]:
            j += 1                       # end of this lull
        if j - i >= ml and j < n:
            e = j
            while e < n and busy[e]:
                e += 1                   # end of the busy run
            if e - j >= mp:
                out.append((j, e))
            i = e
        else:
            i = j + 1
    return out


def cut(video: Path, out: Path, start_s: float, dur_s: float) -> bool:
    """Re-encode, never stream-copy.

    trim_clip.py records why: with -ss before -i and -c copy, ffmpeg snaps to the
    keyframe at or before the start, so the clip begins early AND ends early. A
    frame-accurate cut has to re-encode."""
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{start_s:.2f}", "-i", str(video),
         "-t", f"{dur_s:.2f}", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-c:a", "aac", "-movflags", "+faststart", str(out)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ffmpeg failed: {r.stderr.strip()[:200]}")
        return False
    return out.exists() and out.stat().st_size > 10_000


def record_lineage(entries: dict[str, str]) -> None:
    """{clip_filename: source_filename}. Keyed on BASENAME, matching
    data/train_clips/lineage.json and the ball gold-leak guard - a rename defeats
    both, so basename is the only safe identity."""
    doc = {"_why": [
        "Which recording each cut clip came from. N cuts of one video are ONE",
        "court, not N: counting them separately inflates any pass-rate, which is",
        "the double-count eval/recordings.py exists to stop. Keyed on basename",
        "because that is what the gold-leak guard keys on too (trap T17)."],
        "clips": {}}
    if LINEAGE.exists():
        try:
            doc = json.loads(LINEAGE.read_text(encoding="utf-8"))
            doc.setdefault("clips", {})
        except Exception:
            pass
    doc["clips"].update(entries)
    LINEAGE.parent.mkdir(parents=True, exist_ok=True)
    LINEAGE.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--out", required=True, help="destination directory")
    ap.add_argument("--prefix", required=True, help="clip name stem, e.g. mpc_mixed")
    ap.add_argument("--n", type=int, default=12, help="max clips to write")
    ap.add_argument("--pre", type=float, default=2.0, help="seconds kept before the serve")
    ap.add_argument("--max-len", type=float, default=30.0, dest="max_len")
    ap.add_argument("--min-len", type=float, default=6.0, dest="min_len")
    ap.add_argument("--min-point", type=float, default=2.0, dest="min_point",
                    help="shortest busy run that counts as a point (lower = more clips)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    video = Path(a.video)
    if not video.exists():
        raise SystemExit(f"no such video: {video}")
    dur, fps = probe(video)
    print(f"{_ascii(video.name)[:60]}  {dur/60:.1f} min")

    tr = motion_trace(video)
    pts = point_starts(tr, min_point_s=a.min_point)
    print(f"  {len(pts)} candidate points from the motion trace")
    if not pts:
        raise SystemExit("  no points found - the motion rule saw no lull/burst structure")

    # spread the picks across the whole recording rather than taking the first N,
    # so the clips sample the venue's lighting and camera drift, not just its start
    idx = np.linspace(0, len(pts) - 1, min(a.n, len(pts))).round().astype(int)
    picks = [pts[i] for i in sorted(set(idx.tolist()))]

    entries, made = {}, 0
    for k, (s, e) in enumerate(picks, 1):
        start = max(0.0, s / PROBE_FPS - a.pre)
        length = min(a.max_len, max(a.min_len, (e - s) / PROBE_FPS + a.pre))
        if start + length > dur:
            length = max(0.0, dur - start)
        if length < a.min_len:
            continue
        name = f"{a.prefix}_p{k:02d}.mp4"
        dst = Path(a.out) / name
        print(f"  {name}  {start/60:5.1f}min +{length:4.1f}s", flush=True)
        if a.dry_run:
            made += 1
            continue
        if cut(video, dst, start, length):
            entries[name] = video.name
            made += 1
    if entries:
        record_lineage(entries)
    print(f"  wrote {made} clips -> {a.out}"
          f"{'' if a.dry_run else ' (lineage recorded)'}")


if __name__ == "__main__":
    main()
