"""highlights.py — turn a match into per-rally clips (the Logic layer).

WHY THIS EXISTS
---------------
Watching a recorded match means scrubbing past the dead time between points, and
dead time is most of a phone recording. Every rally boundary is already known
(`schema.Rally.start_s / end_s`), so cutting the video into playable rallies is
pure bookkeeping over data the pipeline already produced. No model goes anywhere
near it — ranking a rally is a deterministic rule, and that is the whole point of
keeping this in the Logic layer.

TWO THINGS THAT DECIDE THE DESIGN
---------------------------------
1. `rally.start_s` is the first CONTACT, not the start of the point (pipeline.py
   sets it from `raw_shots[0]["t_hit_s"]`). A clip cut exactly there opens
   mid-swing, with the serve toss already gone. So the pre-pad is SEMANTIC — it
   is what makes the clip watchable — and only incidentally covers the keyframe
   snap below.

2. ffmpeg stream copy (`-c copy`) is I/O-bound and near free, but can only cut on
   KEYFRAMES. "Just ask for the time you want and let it snap" is the obvious
   approach and it is WRONG, in a way that is invisible until you measure it:
   with `-ss` before `-i`, ffmpeg seeks back to the nearest keyframe, and `-t` is
   then counted from THERE. So a snap of dt shifts the whole window earlier by dt
   — the clip gains dt of lead-in and loses dt off the END. On the first real
   match cut here the keyframe interval was 5.52 s against rallies averaging ~5 s,
   so short points were losing their finish entirely.

   The fix is to stop guessing where the snap lands: `keyframe_times()` reads
   every keyframe in ONE pass (0.7 s for a 6-minute clip), and each clip starts on
   the last keyframe at or before the padded start. Nothing snaps, `-t` is exact,
   the rally is fully contained by construction, and the true lead-in is a number
   we can print rather than hope for.

   Re-encoding is frame-accurate but 5-10x slower than real time; it stays
   available (`exact=True`) for the share path and is not the default.

The manifest records the requested start, the keyframe actually used, and the
lead-in delivered — so "the clip contains the whole rally" is arithmetic anyone
can re-check, not a claim.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional, Sequence

# Lead-in / lead-out around a rally, in seconds. The lead-in is the semantic one
# (see the module docstring); the lead-out just avoids ending on the bounce frame.
PRE_PAD_S = 2.0
POST_PAD_S = 1.5


def ffmpeg_exe() -> Optional[str]:
    """Path to the bundled ffmpeg, or None if it cannot be resolved.

    `imageio-ffmpeg` is a declared dependency and ships the binary, which matters
    on Windows where there is usually no system ffmpeg on PATH. Shared with
    annotate._to_h264 rather than duplicated.
    """
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _shots_of(match: dict, rally: dict) -> list[dict]:
    by_id = {s["id"]: s for s in match.get("shots", [])}
    return [by_id[i] for i in rally.get("shot_ids", []) if i in by_id]


def _top_speed(shots: Sequence[dict]) -> float:
    """Fastest shot in the rally, preferring confidently-measured ones.

    Mirrors the rule the dashboard already uses (Rallies.jsx): filter to
    `speed_confident is not False`, and fall back to every shot only if that
    leaves nothing. Kept identical on purpose — a rally the UI calls the fastest
    and a reel that ranks a different one would be a bug nobody could see.
    """
    confident = [s for s in shots if s.get("speed_confident") is not False]
    pool = confident or list(shots)
    return max((float(s.get("speed_kmh") or 0.0) for s in pool), default=0.0)


def rank_rallies(match: dict, top_n: Optional[int] = None) -> list[dict]:
    """Rallies, best first. Deterministic — no model, no learned score.

    A rally is interesting when it lasted: shot count first, then the fastest
    confident shot, then duration as the tie-break. Winner and unforced-error
    reasoning are deliberately out of scope; they need information the pipeline
    does not have, and guessing would make the ranking unexplainable.

    Every entry carries a plain-English `why`, because a "top rally" a user
    cannot see the reason for reads as arbitrary.
    """
    ranked = []
    for rally in match.get("rallies", []):
        shots = _shots_of(match, rally)
        dur = float(rally.get("end_s", 0.0)) - float(rally.get("start_s", 0.0))
        speed = _top_speed(shots)
        ranked.append({
            "rally_id": rally.get("id"),
            "shot_count": len(shots),
            "top_speed_kmh": round(speed, 1),
            "duration_s": round(dur, 2),
        })

    # Sort by the stated key, then by rally id so ties never reorder run to run.
    ranked.sort(key=lambda r: (-r["shot_count"], -r["top_speed_kmh"],
                               -r["duration_s"], r["rally_id"]))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        bits = [f"{r['shot_count']} shot" + ("" if r["shot_count"] == 1 else "s")]
        if r["top_speed_kmh"] > 0:
            bits.append(f"top {r['top_speed_kmh']:.0f} km/h")
        bits.append(f"{r['duration_s']:.1f}s")
        r["why"] = ", ".join(bits)
    return ranked[:top_n] if top_n else ranked


def clip_bounds(rally: dict, duration_s: Optional[float] = None,
                pre_s: float = PRE_PAD_S, post_s: float = POST_PAD_S) -> tuple:
    """(start_s, end_s) for this rally's clip, clamped to the video.

    Clamping matters at both ends: the first rally of a clip can begin less than
    `pre_s` into the file, and the last can end inside `post_s` of the end. Both
    would otherwise ask ffmpeg for time that does not exist.
    """
    start = max(0.0, float(rally.get("start_s", 0.0)) - pre_s)
    end = float(rally.get("end_s", 0.0)) + post_s
    if duration_s is not None and duration_s > 0:
        end = min(end, float(duration_s))
    return start, max(end, start)


def _run(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


_PTS = re.compile(r"pts_time:([0-9.]+)")

# If keyframes cannot be enumerated we cannot cut ON one, so a snap becomes
# possible again — and a snap shortens the tail. Pad the requested duration by
# this much so the rally is still covered. Deliberately generous: an over-long
# clip is a cosmetic problem, a truncated point is a broken one.
FALLBACK_SNAP_GUARD_S = 12.0


def keyframe_times(video_path: str) -> list[float]:
    """Every keyframe timestamp in the video, ascending. Empty if unreadable.

    `-skip_frame nokey` makes this one cheap pass — the decoder throws away
    non-key frames — so a 6-minute clip enumerates in well under a second. This
    is what lets a cut land exactly on a keyframe instead of being snapped to one
    behind our back (see the module docstring).
    """
    ff = ffmpeg_exe()
    if ff is None:
        return []
    try:
        out = subprocess.run(
            [ff, "-skip_frame", "nokey", "-i", video_path, "-vf", "showinfo",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=900).stderr
    except Exception:
        return []
    return sorted({float(m) for m in _PTS.findall(out)})


def snap_to_keyframe(t: float, keys: Sequence[float]) -> Optional[float]:
    """Last keyframe at or before `t`, or None if there is none / none known.

    At or BEFORE is the whole point: a clip may open earlier than asked, never
    later, because later would mean opening inside the rally.
    """
    prev = None
    for k in keys:
        if k <= t + 1e-6:
            prev = k
        else:
            break
    return prev


def cut_clips(video_path: str, match: dict, out_dir: str, *,
              top_n: int = 3, reel: bool = False, exact: bool = False,
              pre_s: float = PRE_PAD_S, post_s: float = POST_PAD_S) -> dict:
    """Cut one mp4 per rally and write a manifest. Returns the manifest.

    `exact=True` re-encodes for a frame-accurate trim; the default stream-copies.
    """
    ff = ffmpeg_exe()
    if ff is None:
        raise RuntimeError(
            "ffmpeg not available — `pip install imageio-ffmpeg` (it is already "
            "in backend/requirements.txt and bundles the binary)")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    duration = float((match.get("video") or {}).get("duration_s") or 0.0) or None
    rank_by_id = {r["rally_id"]: r for r in rank_rallies(match)}
    # One pass for the whole video, not one probe per clip.
    keys = [] if exact else keyframe_times(video_path)

    clips = []
    for rally in match.get("rallies", []):
        rid = rally.get("id")
        shots = _shots_of(match, rally)
        if not shots:
            # A rally with no shots has no contact to anchor on, so its bounds are
            # meaningless. Skip it loudly rather than emit a clip of dead time.
            clips.append({"rally_id": rid, "skipped": "no shots in this rally"})
            continue

        start, end = clip_bounds(rally, duration, pre_s, post_s)
        if end - start <= 0.05:
            clips.append({"rally_id": rid, "skipped": "zero-length after clamping"})
            continue

        # Start ON a keyframe so nothing snaps behind us and `-t` stays exact —
        # a snap would shorten the TAIL, which is how a short rally loses its
        # finish. Without a keyframe list, pad the duration instead.
        cut = start if exact else snap_to_keyframe(start, keys)
        if cut is None:
            cut, span = start, (end - start) + FALLBACK_SNAP_GUARD_S
        else:
            span = end - cut

        name = f"rally_{(rid if rid is not None else len(clips)):02d}.mp4"
        dst = out / name
        cmd = [ff, "-y", "-ss", f"{cut:.3f}", "-i", video_path, "-t", f"{span:.3f}"]
        cmd += (["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast"]
                if exact else ["-c", "copy"])
        cmd += ["-movflags", "+faststart", str(dst)]

        ok = _run(cmd) and dst.exists() and dst.stat().st_size > 0
        info = rank_by_id.get(rid, {})
        clips.append({
            "rally_id": rid,
            "file": name,
            "rank": info.get("rank"),
            "why": info.get("why"),
            "shot_count": info.get("shot_count"),
            "top_speed_kmh": info.get("top_speed_kmh"),
            "rally_start_s": round(float(rally.get("start_s", 0.0)), 3),
            "rally_end_s": round(float(rally.get("end_s", 0.0)), 3),
            "requested_start_s": round(start, 3),
            "start_s": round(cut, 3),          # where the clip really begins
            "end_s": round(cut + span, 3),     # ...and really ends
            "lead_in_s": round(float(rally.get("start_s", 0.0)) - cut, 3),
            "on_keyframe": cut is not None and not exact and bool(keys),
            "ok": bool(ok),
        })

    manifest: dict[str, Any] = {
        "tool": "highlights",
        "video": os.path.basename(video_path),
        "mode": "re-encode (exact)" if exact else "stream copy (keyframe snap)",
        "pre_pad_s": pre_s,
        "post_pad_s": post_s,
        "keyframes": len(keys),
        "ranking": "shot count, then top confident speed, then duration",
        "clips": clips,
        "top": [c["rally_id"] for c in
                sorted((c for c in clips if c.get("ok")),
                       key=lambda c: c.get("rank") or 10**6)[:top_n]],
    }

    if reel:
        made = build_reel(out, manifest, top_n=top_n)
        manifest["reel"] = made

    (out / "highlights.json").write_text(json.dumps(manifest, indent=1),
                                         encoding="utf-8")
    return manifest


def build_reel(out_dir: Path, manifest: dict, *, top_n: int = 3) -> Optional[str]:
    """Concat the top-N clips into one reel, or None if it could not be made.

    The concat DEMUXER (not the filter) joins without re-encoding — the parts all
    came from one source so they share codec parameters, which is exactly the
    condition it requires. Near-instant.
    """
    ff = ffmpeg_exe()
    if ff is None:
        return None
    by_id = {c["rally_id"]: c for c in manifest["clips"] if c.get("ok")}
    picks = [by_id[i] for i in manifest["top"][:top_n] if i in by_id]
    if len(picks) < 2:
        return None                       # a reel of one clip is just that clip

    listing = out_dir / "_reel.txt"
    listing.write_text(
        "".join(f"file '{c['file']}'\n" for c in picks), encoding="utf-8")
    dst = out_dir / "highlights.mp4"
    ok = _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
               "-c", "copy", "-movflags", "+faststart", str(dst)])
    try:
        listing.unlink()
    except Exception:
        pass
    return dst.name if ok and dst.exists() and dst.stat().st_size > 0 else None
