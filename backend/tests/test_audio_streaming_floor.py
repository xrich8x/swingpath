"""The streaming rolling-median/MAD floor, pinned against numpy.

`audio.detect_impacts` builds its adaptive floor with
`sliding_window_view` + `np.median`, which is O(n * win) — ~1000 element visits
per envelope sample for the median and another ~1000 for the MAD. Desktop numpy
hides that behind a vectorised C median; Accelerate/vDSP has no rolling-median
primitive at all, so the iOS port has to be a genuine streaming order-statistic
rewrite rather than a translation.

`tools/audio_ondevice_probe.streaming_med_mad` is that rewrite's reference
implementation: a maintained sorted window for the median, and — the part that
is easy to get wrong — the MAD as an order statistic of the MERGE of two
already-sorted deviation sequences, which costs O(log win) and needs no second
sort. This test is the parity harness for it. Anything the port does must
reproduce numpy's answer EXACTLY, including the even-window mean-of-two-middles
convention, or the floor drifts and the threshold drifts with it.

Measured against: numpy's own `np.median` over the same windows. No detection
quality is asserted here.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

probe = pytest.importorskip("audio_ondevice_probe")


def _reference(env, win, n_out):
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    sw = np.lib.stride_tricks.sliding_window_view(padded, win)[:n_out]
    med = np.median(sw, axis=1)
    mad = np.median(np.abs(sw - med[:, None]), axis=1)
    return med, mad


@pytest.mark.parametrize("win", [3, 7, 8, 64, 101, 256])
def test_streaming_matches_numpy_exactly(win):
    rng = np.random.default_rng(7)
    env = np.abs(rng.standard_normal(900))
    n_out = 500
    ref_med, ref_mad = _reference(env, win, n_out)
    got_med, got_mad = probe.streaming_med_mad(env, win, n_out)
    assert np.array_equal(ref_med, got_med)
    assert np.array_equal(ref_mad, got_mad)


def test_streaming_handles_impact_like_spikes():
    """Heavy-tailed, spiky input — the actual shape of an impact envelope."""
    rng = np.random.default_rng(11)
    env = np.abs(rng.standard_normal(2000)) * 0.01
    env[::137] += 5.0            # impacts
    env[900:1000] += 0.3         # a drifting local floor
    ref_med, ref_mad = _reference(env, 128, 1200)
    got_med, got_mad = probe.streaming_med_mad(env, 128, 1200)
    assert np.array_equal(ref_med, got_med)
    assert np.array_equal(ref_mad, got_mad)


def test_streaming_handles_ties_and_constant_runs():
    """Digital silence is a long run of identical values; ties break the naive
    two-pointer split unless the split point is a bisect_right on the median."""
    env = np.concatenate([np.zeros(300), np.ones(50) * 0.5, np.zeros(300)])
    for win in (16, 33, 100):
        ref_med, ref_mad = _reference(env, win, 400)
        got_med, got_mad = probe.streaming_med_mad(env, win, 400)
        assert np.array_equal(ref_med, got_med), win
        assert np.array_equal(ref_mad, got_mad), win


def test_kth_of_two_sorted_merge():
    rng = np.random.default_rng(3)
    for _ in range(200):
        a = sorted(rng.integers(0, 20, size=int(rng.integers(0, 12))).tolist())
        b = sorted(rng.integers(0, 20, size=int(rng.integers(0, 12))).tolist())
        if not a and not b:
            continue
        merged = sorted(a + b)
        for k in range(len(merged)):
            assert probe._kth_of_two_sorted(a, b, k) == merged[k], (a, b, k)


def test_chunked_floor_equals_unchunked():
    """The screen chunks the shipped floor to bound peak memory; chunking must be
    numerically a no-op (the unchunked form allocates n*win*8 bytes = 4.8 GB for
    a 10-minute clip, which is its own on-device problem)."""
    screen = pytest.importorskip("audio_impact_screen")
    rng = np.random.default_rng(5)
    env = np.abs(rng.standard_normal(5000))
    win = 101
    ref_med, ref_mad = _reference(env, win, env.size)
    got_med, got_mad = screen.rolling_med_mad(env, win, chunk=317)
    assert np.array_equal(ref_med, got_med)
    assert np.allclose(ref_mad + 1e-9, got_mad, rtol=0, atol=0)
