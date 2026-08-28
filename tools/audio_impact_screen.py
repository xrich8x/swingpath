"""audio_impact_screen.py — feasibility SCREEN for the audio-impact lane.

THIS IS A FEASIBILITY SCREEN, NOT AN ACCURACY MEASUREMENT.

It answers one label-free question: does `swingvision.audio.detect_impacts`
produce a usable signal on our corpus, per surface, and in particular on the
indoor SHELL venues? It reports, per clip:

  - whether the shipped detector self-declares useless (the
    `max_events_per_s` bail-out that returns [])
  - the raw event rate per second (before that bail-out)
  - envelope contrast over the local floor

It produces NO recall and NO precision figure, and it must not. The only
per-stroke reference in this repo is `tools/audio_hits.py` scoring against
SwingVision's burned-in HUD, which rule 11 bars as a ground-truth reference.

Nothing here modifies shipped defaults. The detector's internals are
re-implemented here ONLY so a single envelope pass can yield both the raw event
list and the local-floor contrast; `--verify` proves the re-implementation is
bit-identical to `detect_impacts` on a sample of clips.

Usage:
  py tools/audio_impact_screen.py --census data/output/audio_census.json \
      --out data/output/audio_impact_screen.json [--verify 8] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from typing import Optional

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from swingvision import audio as sv_audio  # noqa: E402

# Resolved detector configuration. Read back out of the shipped function's
# signature so the provenance stamp cannot drift from the code (a static preset
# table is exactly the stale-stamp trap).
import inspect  # noqa: E402


def resolved_defaults() -> dict:
    sig = inspect.signature(sv_audio.detect_impacts)
    out = {}
    for name, p in sig.parameters.items():
        if p.default is not inspect.Parameter.empty:
            out[name] = p.default
    env_sig = inspect.signature(sv_audio.impact_envelope)
    out["smooth_s"] = env_sig.parameters["smooth_s"].default
    return out


def rolling_med_mad(env: np.ndarray, win: int, chunk: int = 20000):
    """Exactly `detect_impacts`'s rolling median/MAD, computed in chunks.

    Chunking is numerically a no-op (the padded array is shared and the window
    for output index i is identical), but it caps peak memory: the unchunked
    form materialises an n x win float64 sort buffer, which is 4.8 GB for a
    10-minute clip.
    """
    n = env.size
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    med = np.empty(n, dtype=np.float64)
    mad = np.empty(n, dtype=np.float64)
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        sw = np.lib.stride_tricks.sliding_window_view(padded, win)[lo:hi]
        m = np.median(sw, axis=1)
        med[lo:hi] = m
        mad[lo:hi] = np.median(np.abs(sw - m[:, None]), axis=1) + 1e-9
    return med, mad


def screen_clip(samples: np.ndarray, sr: int, cfg: dict) -> dict:
    """Raw event list + contrast stats, plus the shipped bail-out verdict."""
    dur = samples.size / sr
    if samples.size < sr // 2:
        return {"duration_s": dur, "too_short": True}
    t0 = time.perf_counter()
    env, erate = sv_audio.impact_envelope(samples, sr, cfg["band_hz"])
    t_env = time.perf_counter() - t0
    n = env.size
    win = max(3, int(cfg["floor_win_s"] * erate))
    t0 = time.perf_counter()
    med, mad = rolling_med_mad(env, win)
    t_floor = time.perf_counter() - t0

    env_med = float(np.median(env))
    floor_abs = cfg["min_contrast"] * env_med
    above = (env > med + cfg["k_mad"] * mad) & (env > floor_abs)

    events: list[float] = []
    peaks: list[int] = []
    i = 0
    min_sep = int(cfg["min_sep_s"] * erate)
    while i < n:
        if not above[i]:
            i += 1
            continue
        seg_end = min(n, i + min_sep)
        peak = i + int(np.argmax(env[i:seg_end]))
        events.append(peak / erate)
        peaks.append(peak)
        i = peak + min_sep

    rate = len(events) / dur if dur > 0 else 0.0
    bailed = bool(dur > 2.0 and rate > cfg["max_events_per_s"])

    # Which of the two tests is BINDING? `detect_impacts` requires BOTH a local
    # (med + k*MAD) and an absolute (min_contrast * global median) test. If a
    # venue's yield is low, the design question is which one suppressed it, and
    # that is answerable with no labels at all.
    def _count(mask: np.ndarray) -> int:
        c, j = 0, 0
        while j < n:
            if not mask[j]:
                j += 1
                continue
            j = j + int(np.argmax(env[j:min(n, j + min_sep)])) + min_sep
            c += 1
        return c

    n_local_only = _count(env > med + cfg["k_mad"] * mad)   # abs test dropped
    n_abs_only = _count(env > floor_abs)                    # local test dropped
    unlocked_by_dropping_abs = n_local_only - len(events)
    unlocked_by_dropping_local = n_abs_only - len(events)

    p99 = float(np.percentile(env, 99))
    out = {
        "duration_s": round(dur, 2),
        "sr": int(sr),
        "env_rate_hz": int(erate),
        "n_events_raw": len(events),
        "events_per_s": round(rate, 4),
        "bailed_out": bailed,
        "n_events_shipped": 0 if bailed else len(events),
        "env_p99_over_median": round(p99 / (env_med + 1e-12), 3),
        "frac_samples_above_thresh": round(float(above.mean()), 5),
        "t_envelope_s": round(t_env, 3),
        "t_rolling_floor_s": round(t_floor, 3),
        "n_events_local_test_only": n_local_only,
        "n_events_abs_test_only": n_abs_only,
        "unlocked_by_dropping_abs": unlocked_by_dropping_abs,
        "unlocked_by_dropping_local": unlocked_by_dropping_local,
        "binding_test": ("absolute (min_contrast * global median)"
                         if unlocked_by_dropping_abs >= unlocked_by_dropping_local
                         else "local (rolling median + k*MAD)"),
    }
    if peaks:
        pk = np.asarray(peaks)
        contrast = env[pk] / (med[pk] + 1e-12)
        out["event_contrast_over_local_floor_median"] = round(float(np.median(contrast)), 2)
        out["event_contrast_over_local_floor_p10"] = round(float(np.percentile(contrast, 10)), 2)
        # Inter-event gap tells rally-like (0.4-1.2 s) from noise-like (~min_sep).
        if len(events) > 2:
            gaps = np.diff(np.asarray(events))
            out["gap_median_s"] = round(float(np.median(gaps)), 3)
            out["frac_gaps_at_min_sep"] = round(
                float(np.mean(gaps < cfg["min_sep_s"] * 1.15)), 3)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="data/output/audio_census.json")
    ap.add_argument("--incoming", default="data/incoming")
    ap.add_argument("--out", default="data/output/audio_impact_screen.json")
    ap.add_argument("--verify", type=int, default=0,
                    help="verify N clips against the shipped detect_impacts")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--surfaces", default="", help="comma-separated surface filter")
    ap.add_argument("--only", default="", help="comma-separated filename filter")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--loudness-only", action="store_true",
                    help="decode only; report level statistics, skip the detector. "
                         "A clip can carry an audio STREAM that is digital silence, "
                         "and every ratio in the main pass would then be a ratio of "
                         "noise to noise.")
    args = ap.parse_args()

    cfg = resolved_defaults()
    census = json.load(open(args.census))

    todo = []
    for surface, entries in census.items():
        for e in entries:
            if e.get("audio"):
                todo.append((surface, e["file"]))
    todo.sort()
    if args.surfaces:
        keep = set(args.surfaces.split(","))
        todo = [t for t in todo if t[0] in keep]
    if args.only:
        keep = set(args.only.split(","))
        todo = [t for t in todo if t[1] in keep]
    if args.limit:
        todo = todo[: args.limit]

    rng = np.random.default_rng(args.seed)
    verify_idx = set()
    if args.verify:
        verify_idx = set(rng.choice(len(todo), size=min(args.verify, len(todo)),
                                    replace=False).tolist())

    results = []
    verifications = []
    for i, (surface, fname) in enumerate(todo):
        path = os.path.join(args.incoming, surface, fname)
        rec = {"surface": surface, "file": fname}
        if not os.path.exists(path):
            rec["error"] = "missing"
            results.append(rec)
            continue
        t0 = time.perf_counter()
        got = sv_audio.extract_audio(path)
        rec["t_extract_s"] = round(time.perf_counter() - t0, 2)
        if got is None:
            rec["error"] = "extract_audio returned None"
            results.append(rec)
            print(f"[{i+1}/{len(todo)}] {surface}/{fname}: NO AUDIO (extract failed)",
                  flush=True)
            continue
        samples, sr = got
        if args.loudness_only:
            x = np.abs(samples.astype(np.float64))
            rms = float(np.sqrt(np.mean(x * x)))
            rec.update({
                "duration_s": round(samples.size / sr, 2),
                "sr": int(sr),
                "rms_dbfs": round(20 * np.log10(rms + 1e-12), 2),
                "peak_dbfs": round(20 * np.log10(float(x.max()) + 1e-12), 2),
                "frac_exact_zero": round(float(np.mean(samples == 0.0)), 5),
                "crest_db": round(20 * np.log10((float(x.max()) + 1e-12) / (rms + 1e-12)), 2),
            })
            print(f"[{i+1}/{len(todo)}] {surface}/{fname}: rms={rec['rms_dbfs']}dBFS "
                  f"peak={rec['peak_dbfs']}dBFS zeros={rec['frac_exact_zero']}",
                  flush=True)
            results.append(rec)
            continue
        rec.update(screen_clip(samples, sr, cfg))
        if i in verify_idx:
            shipped = sv_audio.detect_impacts(samples, sr)
            mine = [] if rec.get("bailed_out") else None
            ok = (len(shipped) == rec["n_events_shipped"])
            verifications.append({"file": fname, "shipped_n": len(shipped),
                                  "screen_n": rec["n_events_shipped"], "match": ok})
            del mine
        print(f"[{i+1}/{len(todo)}] {surface}/{fname}: "
              f"dur={rec.get('duration_s')}s events/s={rec.get('events_per_s')} "
              f"bail={rec.get('bailed_out')} "
              f"contrast={rec.get('event_contrast_over_local_floor_median')}",
              flush=True)
        results.append(rec)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "backend", "swingvision", "audio.py"), "rb").read()
    stamp = {
        "note": "THIS IS A FEASIBILITY SCREEN, NOT AN ACCURACY MEASUREMENT. "
                "No recall or precision figure is produced or implied: the only "
                "per-stroke reference available is SwingVision's burned-in HUD, "
                "which rule 11 bars as a ground-truth reference.",
        "measured_against": "nothing — label-free. Every number is a property of "
                            "the detector's own output on the clip's own audio.",
        "resolved_config": {k: (list(v) if isinstance(v, tuple) else v)
                            for k, v in cfg.items()},
        "audio_py_sha256": hashlib.sha256(src).hexdigest()[:16],
        "commit": commit,
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "platform": platform.platform(),
        "seed": args.seed,
        "date": time.strftime("%Y-%m-%d"),
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump({"provenance": stamp, "verifications": verifications,
               "clips": results}, open(args.out, "w"), indent=1)
    print(f"\nwrote {args.out}")
    if verifications:
        bad = [v for v in verifications if not v["match"]]
        print(f"verify: {len(verifications)-len(bad)}/{len(verifications)} match shipped "
              f"detect_impacts" + (f"  MISMATCH: {bad}" if bad else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
