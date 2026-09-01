"""audio.py — racket-impact detection from the clip's own soundtrack.

Session E3b. The events layer sees only the court-plane ball track, and on
amateur footage that track is broken exactly where events live (fast ball, small
far ball, motion blur at contact). The soundtrack carries an independent copy of
every hit: a racket-ball impact is a short broadband "pop" that survives video
compression and does not care how many pixels the ball subtends. This module
recovers those pops. It is perception, but classical DSP — no model, no weights.

Two stages, kept separate for testability:

  extract_audio(video)      -> (samples, sr)   decode via imageio-ffmpeg
  detect_impacts(samples)   -> [time_s, ...]   band-pass -> envelope ->
                                               adaptive threshold -> peaks

Design notes (chosen for amateur court recordings, indoor echo included):
- Impacts live well above crowd/footstep rumble: band-pass 1.5-7 kHz.
- The envelope threshold is a ROLLING median + k*MAD, not a global one — a
  passing car or HVAC hum shifts the local floor, and a 36 s rally clip is
  already non-stationary.
- Peaks are ranked by prominence over that local floor; a minimum separation
  de-duplicates the direct sound from its first echo.

The detector reports every percussive transient — hits, bounces, and the
occasional door slam. Telling hits from bounces is the FUSION layer's job
(a bounce is quieter and sits near a track speed-minimum; a hit is louder and
near a player). `fuse_hits` implements the conservative half of that: audio
only ADDS a hit where the ball track plausibly supports one and no visual hit
already claimed it.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import wave
from typing import Optional, Sequence

import numpy as np
from scipy.signal import butter, sosfiltfilt


def extract_audio(video_path: str, sr: int = 16000) -> Optional[tuple[np.ndarray, int]]:
    """Decode the video's audio track to mono float32 at `sr` Hz.

    Uses the ffmpeg binary bundled with imageio-ffmpeg (already a transitive
    dependency of our stack). Returns None — never raises — when the binary or
    an audio stream is missing, so callers can degrade to visual-only events.
    """
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        proc = subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-i", video_path,
             "-vn", "-ac", "1", "-ar", str(sr), "-f", "wav", tmp.name],
            capture_output=True, timeout=120)
        if proc.returncode != 0 or os.path.getsize(tmp.name) < 128:
            return None
        with wave.open(tmp.name, "rb") as w:
            n = w.getnframes()
            raw = w.readframes(n)
            width = w.getsampwidth()
            rate = w.getframerate()
        if width == 2:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif width == 4:
            samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        return samples, rate
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def impact_envelope(samples: np.ndarray, sr: int,
                    band_hz: tuple[float, float] = (1500.0, 7000.0),
                    smooth_s: float = 0.004) -> tuple[np.ndarray, int]:
    """Band-passed, rectified, smoothed energy envelope at ~1 kHz frame rate.

    Returns (envelope, env_rate). The envelope is what peaks are picked from;
    exposed separately so tests and diagnostics can look at it.
    """
    nyq = sr / 2.0
    hi = min(band_hz[1], 0.95 * nyq)
    sos = butter(4, [band_hz[0] / nyq, hi / nyq], btype="band", output="sos")
    x = sosfiltfilt(sos, samples.astype(np.float64))
    x = np.abs(x)
    # Smooth with a short moving average, then decimate to ~1 kHz.
    win = max(1, int(smooth_s * sr))
    kernel = np.ones(win) / win
    env = np.convolve(x, kernel, mode="same")
    dec = max(1, sr // 1000)
    return env[::dec].astype(np.float64), sr // dec


# Peak elements the rolling-floor deviation block may materialise at once.
# 8M float64 is ~64 MB, which keeps a 28.2 min clip off the 13.5 GB cliff
# without shrinking the window-vectorised median enough to matter.
_FLOOR_CHUNK_ELEMS = 8_000_000


def detect_impacts(samples: np.ndarray, sr: int, *,
                   band_hz: tuple[float, float] = (1500.0, 7000.0),
                   floor_win_s: float = 1.0,
                   k_mad: float = 6.0,
                   min_contrast: float = 4.0,
                   min_sep_s: float = 0.22,
                   max_events_per_s: float = 2.5) -> list[float]:
    """Times (s) of percussive transients — candidate hits AND bounces.

    A sample is a candidate when the envelope exceeds BOTH
      - a rolling median + `k_mad` * MAD floor (adapts to a drifting noise
        level), and
      - `min_contrast` * the clip's global median envelope (an absolute
        contrast test: rectified noise has a heavy enough upper tail that a
        purely relative threshold fires a few times per minute on silence —
        a real impact dwarfs the whole clip's typical level, noise never does).
    Candidates are grouped into events separated by `min_sep_s` (direct sound +
    first echo = one event), each stamped at its local envelope maximum. A
    degenerate, constantly-loud clip (music, wind on mic) yields more than
    `max_events_per_s` — then the detector declares itself useless and returns
    [] rather than spraying false hits into the events layer.
    """
    if samples.size < sr // 2:
        return []
    env, erate = impact_envelope(samples, sr, band_hz)
    n = env.size
    win = max(3, int(floor_win_s * erate))

    # Rolling median/MAD via strided windows on a padded copy.
    #
    # CHUNKED, because the one-shot form allocates O(n * win). `sliding_window_view`
    # is free — it is a view — but `np.abs(sw - med[:, None])` materialises the whole
    # thing: on a 28.2 min clip that is ~1.7M envelope samples x a 1000-sample window
    # = a 13.5 GB peak, measured, for a result that is 1.7M floats. Long clips are
    # exactly what the offline analyzer is for, so this is not a corner case.
    #
    # Chunking bounds the peak at CHUNK * win and is BIT-IDENTICAL: the same numpy
    # median over the same windows, just evaluated in slices. Pinned by
    # tests/test_audio_floor_chunking.py against the unchunked expression.
    #
    # This is the DESKTOP fix and deliberately not the iOS one. Accelerate has no
    # rolling-median primitive, so the port needs a genuine streaming order
    # statistic — `tools/audio_ondevice_probe.streaming_med_mad`, which is exact
    # against numpy and pinned by tests/test_audio_streaming_floor.py. That is a
    # rewrite, and it is slower than vectorised numpy here, so it does not belong
    # in this path.
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    sw = np.lib.stride_tricks.sliding_window_view(padded, win)[:n]
    med = np.empty(n, dtype=np.float64)
    mad = np.empty(n, dtype=np.float64)
    chunk = max(1, int(_FLOOR_CHUNK_ELEMS // max(win, 1)))
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        block = sw[a:b]
        m = np.median(block, axis=1)
        med[a:b] = m
        mad[a:b] = np.median(np.abs(block - m[:, None]), axis=1)
    mad += 1e-9
    floor_abs = min_contrast * float(np.median(env))
    above = (env > med + k_mad * mad) & (env > floor_abs)

    events: list[float] = []
    i = 0
    min_sep = int(min_sep_s * erate)
    while i < n:
        if not above[i]:
            i += 1
            continue
        seg_end = min(n, i + min_sep)
        peak = i + int(np.argmax(env[i:seg_end]))
        events.append(peak / erate)
        # Skip past the event plus the dead zone.
        i = peak + min_sep
    dur = samples.size / sr
    if dur > 2.0 and len(events) / dur > max_events_per_s:
        return []
    return events


def fuse_hits(visual_hit_idx: Sequence[int], audio_times_s: Sequence[float],
              track_ok: Sequence[bool], fps: float, *,
              match_window_s: float = 0.30,
              support_radius: int = 3) -> tuple[list[int], dict]:
    """Merge audio impact times into the visual hit list — conservatively.

    Policy (the honest half of audio/visual fusion):
      - every VISUAL hit is kept (the track actually turned there);
      - an AUDIO event within `match_window_s` of a visual hit is the same hit
        (audio confirms, adds nothing);
      - an unmatched audio event becomes a NEW hit only if the court track has
        real data near that frame (`track_ok` within `support_radius`) — a hit
        with no track at all cannot be turned into a shot downstream, and a
        transient with no ball anywhere near it is as likely a bounce or a
        neighbouring court.

    Returns (fused_hit_idx, stats) where stats counts confirmed / added /
    unsupported for the provenance trail.
    """
    n = len(track_ok)
    fused = sorted(int(h) for h in visual_hit_idx)
    stats = {"visual": len(fused), "audio": len(audio_times_s),
             "confirmed": 0, "added": 0, "unsupported": 0}
    for t in audio_times_s:
        f = int(round(t * fps))
        if f < 0 or f >= n:
            continue
        if any(abs(f - h) <= match_window_s * fps for h in fused):
            stats["confirmed"] += 1
            continue
        lo, hi = max(0, f - support_radius), min(n, f + support_radius + 1)
        if any(track_ok[lo:hi]):
            fused.append(f)
            stats["added"] += 1
        else:
            stats["unsupported"] += 1
    return sorted(fused), stats
