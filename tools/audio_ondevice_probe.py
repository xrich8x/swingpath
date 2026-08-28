"""audio_ondevice_probe.py — the three on-device line items for `audio.py`.

Companion to tools/audio_impact_screen.py. THIS IS A FEASIBILITY SCREEN, NOT AN
ACCURACY MEASUREMENT — it measures cost and numerical parity, never detection
quality.

A. COMPLEXITY. Time `impact_envelope`'s band-pass against `detect_impacts`'s
   rolling median/MAD floor, and vary n and win independently to confirm or
   refute that the floor is O(n * win), not O(n).

B. FILTER PARITY. Pin the exact scipy contract a vDSP biquad cascade has to
   reproduce: sos coefficients, sosfiltfilt's padtype/padlen, and the initial
   condition. These are the numbers a parity harness asserts against.

C. STREAMING MAD. Prototype an exact O(log win) streaming order-statistic MAD
   and prove it reproduces np.median's answer bit-for-bit, so the iOS rewrite
   is a known algorithm rather than an open question.

Usage:
  py tools/audio_ondevice_probe.py --clip data/incoming/Clay/CYqapSq5llo.mp4 \
     --out data/output/audio_ondevice_probe.json
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import platform
import subprocess
import sys
import time

import numpy as np
from scipy.signal import butter, sosfilt_zi, sosfiltfilt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from swingvision import audio as sv_audio  # noqa: E402


# ---------------------------------------------------------------- A. complexity
def time_floor(env: np.ndarray, win: int, chunk: int = 20000) -> float:
    """Exactly the shipped rolling median/MAD, chunked so peak memory is bounded."""
    n = env.size
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    t0 = time.perf_counter()
    for lo in range(0, n, chunk):
        hi = min(n, lo + chunk)
        sw = np.lib.stride_tricks.sliding_window_view(padded, win)[lo:hi]
        m = np.median(sw, axis=1)
        _ = np.median(np.abs(sw - m[:, None]), axis=1) + 1e-9
    return time.perf_counter() - t0


def complexity_study(env: np.ndarray, sr: int, samples: np.ndarray) -> dict:
    out: dict = {}
    # Band-pass + envelope, for the cost ratio.
    t0 = time.perf_counter()
    sv_audio.impact_envelope(samples, sr)
    out["t_impact_envelope_s"] = round(time.perf_counter() - t0, 3)
    out["n_env_samples"] = int(env.size)

    out["vary_n_win1000"] = []
    for n in [50_000, 100_000, 200_000, 400_000, 800_000]:
        if n > env.size:
            break
        t = time_floor(env[:n], 1000)
        out["vary_n_win1000"].append({"n": n, "t_s": round(t, 3),
                                      "us_per_env_sample": round(1e6 * t / n, 3)})
    out["vary_win_n200000"] = []
    n = min(200_000, env.size)
    for win in [125, 250, 500, 1000, 2000]:
        t = time_floor(env[:n], win)
        out["vary_win_n200000"].append({"win": win, "t_s": round(t, 3),
                                        "us_per_env_sample": round(1e6 * t / n, 3)})
    # Full clip at shipped settings.
    t = time_floor(env, 1000)
    out["full_clip"] = {"n": int(env.size), "win": 1000, "t_s": round(t, 2),
                        "element_visits": int(env.size) * 1000 * 2}
    out["unchunked_peak_alloc_bytes_full_clip"] = int(env.size) * 1000 * 8
    return out


# ------------------------------------------------------------- B. filter parity
def filter_parity(sr: int = 16000, band_hz=(1500.0, 7000.0)) -> dict:
    nyq = sr / 2.0
    hi = min(band_hz[1], 0.95 * nyq)
    sos = butter(4, [band_hz[0] / nyq, hi / nyq], btype="band", output="sos")
    n_sections = sos.shape[0]
    # scipy's sosfiltfilt default padlen (scipy/signal/_signaltools.py):
    #   ntaps = 2 * n_sections + 1
    #   ntaps -= min((sos[:, 2] == 0).sum(), (sos[:, 5] == 0).sum())
    #   padlen = 3 * ntaps
    ntaps = 2 * n_sections + 1
    ntaps -= min(int((sos[:, 2] == 0).sum()), int((sos[:, 5] == 0).sum()))
    padlen = 3 * ntaps
    zi = sosfilt_zi(sos)

    # Empirical confirmation: sosfiltfilt with the derived padlen must equal the
    # default call bit-for-bit.
    rng = np.random.default_rng(0)
    x = rng.standard_normal(4096)
    a = sosfiltfilt(sos, x)
    b = sosfiltfilt(sos, x, padlen=padlen, padtype="odd")
    same = bool(np.array_equal(a, b))
    # And show what getting the padding wrong costs, at the clip edges.
    c = sosfiltfilt(sos, x, padtype="constant", padlen=padlen)
    d = sosfiltfilt(sos, x, padtype=None)
    edge = slice(0, padlen)
    scale = float(np.max(np.abs(a))) + 1e-30
    return {
        "sos_shape": list(sos.shape),
        "n_sections": n_sections,
        "sos_float64": [[float(v) for v in row] for row in sos],
        "scipy_default_padtype": "odd",
        "derived_padlen": int(padlen),
        "derived_padlen_matches_default": same,
        "sosfilt_zi_float64": [[float(v) for v in row] for row in zi],
        "rel_err_if_padtype_constant_edge": round(
            float(np.max(np.abs(c[edge] - a[edge]))) / scale, 6),
        "rel_err_if_padtype_constant_interior": round(
            float(np.max(np.abs(c[padlen:-padlen] - a[padlen:-padlen]))) / scale, 9),
        "rel_err_if_no_padding_edge": round(
            float(np.max(np.abs(d[edge] - a[edge]))) / scale, 6),
        "note": "sosfiltfilt is a zero-phase DOUBLE pass (forward, reverse) with "
                "odd-symmetric edge extension of padlen samples and per-section "
                "initial state sosfilt_zi * x[0]. A vDSP biquad cascade reproduces "
                "the sections trivially and the padding not at all unless it is "
                "written out explicitly; the two disagree hardest inside the first "
                "and last padlen samples, which is where a rally starts.",
    }


# ------------------------------------------------------------ C. streaming MAD
def _kth_of_two_sorted(A, B, k: int) -> float:
    """k-th smallest (0-based) of the merge of two ascending lists, O(log n).

    Standard partition search: cut A after `i` elements and B after `j = k+1-i`,
    and accept the cut when every element left of it is <= every element right of
    it. Written out because the naive "compare B[j-1] to A[i]" shortcut is wrong
    whenever the two sequences interleave — caught by
    tests/test_audio_streaming_floor.py::test_kth_of_two_sorted_merge.
    """
    NEG, POS = float("-inf"), float("inf")
    lo = max(0, k + 1 - len(B))
    hi = min(k + 1, len(A))
    while lo <= hi:
        i = (lo + hi) // 2
        j = k + 1 - i
        a_left = A[i - 1] if i > 0 else NEG
        a_right = A[i] if i < len(A) else POS
        b_left = B[j - 1] if j > 0 else NEG
        b_right = B[j] if j < len(B) else POS
        if a_left > b_right:
            hi = i - 1
        elif b_left > a_right:
            lo = i + 1
        else:
            return max(a_left, b_left)
    raise ValueError(f"k={k} out of range for |A|={len(A)}, |B|={len(B)}")


class _DevBelow:
    """Ascending |deviation| for the window entries at or below the median."""

    __slots__ = ("s", "m", "p")

    def __init__(self, s, m, p):
        self.s, self.m, self.p = s, m, p

    def __len__(self):
        return self.p

    def __getitem__(self, i):
        return self.m - self.s[self.p - 1 - i]


class _DevAbove:
    """Ascending |deviation| for the window entries above the median."""

    __slots__ = ("s", "m", "p")

    def __init__(self, s, m, p):
        self.s, self.m, self.p = s, m, p

    def __len__(self):
        return len(self.s) - self.p

    def __getitem__(self, i):
        return self.s[self.p + i] - self.m


def streaming_med_mad(env: np.ndarray, win: int, n_out: int):
    """Exact rolling median + MAD from a maintained sorted window.

    The median is the order statistic of the sorted window. The MAD is the
    order statistic of the MERGE of two already-sorted deviation sequences
    (below-median reversed, above-median forward), so it costs O(log win) with
    no second sort — this is the piece Accelerate has no primitive for and the
    reason the iOS port is a rewrite, not a translation.

    Honest about what this prototype is: the deviation sequences are index views,
    so the MAD really is O(log win) per output. Window maintenance here uses
    `bisect.insort` on a Python list, which is O(win) memmove — a real port uses
    an order-statistic tree or a bucketed histogram for O(log win). The point of
    this function is EXACTNESS against numpy, not speed.
    """
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    w = padded[:win].tolist()
    s = sorted(w)
    med = np.empty(n_out)
    mad = np.empty(n_out)
    half = win // 2
    for t in range(n_out):
        if t > 0:
            old = padded[t - 1]
            new = padded[t - 1 + win]
            s.pop(bisect.bisect_left(s, old))
            bisect.insort(s, new)
        if win % 2:
            m = s[half]
        else:
            m = 0.5 * (s[half - 1] + s[half])
        med[t] = m
        # Split point: number of entries <= m. The two deviation sequences are
        # index VIEWS onto the sorted window, not materialised lists — building
        # them would be O(win) per step and would quietly undo the whole point.
        p = bisect.bisect_right(s, m)
        below = _DevBelow(s, m, p)    # ascending: m - s[p-1], m - s[p-2], ...
        above = _DevAbove(s, m, p)    # ascending: s[p] - m, s[p+1] - m, ...
        if win % 2:
            mad[t] = _kth_of_two_sorted(below, above, half)
        else:
            mad[t] = 0.5 * (_kth_of_two_sorted(below, above, half - 1)
                            + _kth_of_two_sorted(below, above, half))
    return med, mad


def streaming_check(env: np.ndarray, win: int = 1000, n_out: int = 3000) -> dict:
    n_out = min(n_out, env.size)
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    sw = np.lib.stride_tricks.sliding_window_view(padded, win)[:n_out]
    ref_med = np.median(sw, axis=1)
    ref_mad = np.median(np.abs(sw - ref_med[:, None]), axis=1)
    t0 = time.perf_counter()
    got_med, got_mad = streaming_med_mad(env, win, n_out)
    t_stream = time.perf_counter() - t0
    # Scaling in win is the whole argument: numpy's form is O(win) per output,
    # the streaming form is O(log win). Same machine, same data, same n_out.
    scaling = []
    for w in (125, 250, 500, 1000, 2000):
        t0 = time.perf_counter()
        streaming_med_mad(env, w, min(2000, env.size))
        t_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        pad = w // 2
        padded = np.pad(env, pad, mode="edge")
        sw = np.lib.stride_tricks.sliding_window_view(padded, w)[:min(2000, env.size)]
        m = np.median(sw, axis=1)
        np.median(np.abs(sw - m[:, None]), axis=1)
        t_np = time.perf_counter() - t0
        scaling.append({"win": w,
                        "us_per_out_streaming_python": round(1e6 * t_s / min(2000, env.size), 2),
                        "us_per_out_numpy_sliding": round(1e6 * t_np / min(2000, env.size), 2)})
    return {
        "scaling_in_win_n_out2000": scaling,
        "n_out": int(n_out), "win": int(win),
        "median_exact_match": bool(np.array_equal(ref_med, got_med)),
        "mad_max_abs_diff": float(np.max(np.abs(ref_mad - got_mad))),
        "mad_exact_match": bool(np.array_equal(ref_mad, got_mad)),
        "t_streaming_python_s": round(t_stream, 3),
        "note": "The streaming form is O(log win) per sample and exact. The "
                "Python timing is interpreter overhead, not the algorithm's cost; "
                "it is here to prove equivalence, not to be a speed claim.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default="data/incoming/Clay/CYqapSq5llo.mp4")
    ap.add_argument("--out", default="data/output/audio_ondevice_probe.json")
    args = ap.parse_args()

    got = sv_audio.extract_audio(args.clip)
    if got is None:
        print("no audio", file=sys.stderr)
        return 1
    samples, sr = got
    env, erate = sv_audio.impact_envelope(samples, sr)
    print(f"clip {args.clip}: {samples.size/sr:.1f}s, env {env.size} @ {erate} Hz",
          flush=True)

    res = {
        "provenance": {
            "note": "THIS IS A FEASIBILITY SCREEN, NOT AN ACCURACY MEASUREMENT.",
            "measured_against": "wall-clock on this machine, and numpy/scipy's own "
                                "output as the numerical reference. No detection "
                                "quality is measured or implied.",
            "clip": args.clip,
            "clip_duration_s": round(samples.size / sr, 2),
            "commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "date": time.strftime("%Y-%m-%d"),
        },
    }
    print("A. complexity...", flush=True)
    res["complexity"] = complexity_study(env, sr, samples)
    print("B. filter parity...", flush=True)
    res["filter_parity"] = filter_parity(sr)
    print("C. streaming MAD...", flush=True)
    res["streaming_mad"] = streaming_check(env)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(res, open(args.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "provenance"},
                     indent=1)[:4000])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
