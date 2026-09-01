"""The rolling floor must be chunked, and chunking must change nothing.

`detect_impacts` builds an adaptive floor from `sliding_window_view` + median.
The view is free; `np.abs(sw - med[:, None])` is not - it materialises an
(n x win) array. Measured on a 28.2 min clip: ~1.7M envelope samples x a
1000-sample window is a **13.5 GB** peak allocation, to produce 1.7M floats.
Long clips are precisely what the offline analyzer exists for.

Chunking bounds that peak at CHUNK x win. It is an evaluation-order change and
nothing else, so the ONLY thing worth asserting is that it changed nothing:
these tests compare against the un-chunked expression directly, bit for bit.

Separate from the iOS question. Accelerate has no rolling-median primitive, so
the port needs a real streaming order statistic - that is
`tools/audio_ondevice_probe.streaming_med_mad`, pinned by
test_audio_streaming_floor.py. It is exact but slower than vectorised numpy, so
it is not what the desktop path should use.
"""

import numpy as np
import pytest

from swingvision import audio


def _unchunked(env, win):
    """The expression as it was before chunking."""
    n = env.size
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    sw = np.lib.stride_tricks.sliding_window_view(padded, win)[:n]
    med = np.median(sw, axis=1)
    mad = np.median(np.abs(sw - med[:, None]), axis=1) + 1e-9
    return med, mad


def _chunked(env, win, chunk_elems):
    n = env.size
    pad = win // 2
    padded = np.pad(env, pad, mode="edge")
    sw = np.lib.stride_tricks.sliding_window_view(padded, win)[:n]
    med = np.empty(n, dtype=np.float64)
    mad = np.empty(n, dtype=np.float64)
    chunk = max(1, int(chunk_elems // max(win, 1)))
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        block = sw[a:b]
        m = np.median(block, axis=1)
        med[a:b] = m
        mad[a:b] = np.median(np.abs(block - m[:, None]), axis=1)
    return med, mad + 1e-9


@pytest.mark.parametrize("win", [3, 8, 65, 256])
@pytest.mark.parametrize("chunk_elems", [64, 1000, 10_000_000])
def test_chunking_is_bit_identical(win, chunk_elems):
    """Every chunk size, including one so small it forces many slices, and one
    so large it degenerates to the original single pass."""
    rng = np.random.default_rng(5)
    env = np.abs(rng.standard_normal(1500))
    a_med, a_mad = _unchunked(env, win)
    b_med, b_mad = _chunked(env, win, chunk_elems)
    assert np.array_equal(a_med, b_med)
    assert np.array_equal(a_mad, b_mad)


def test_chunking_survives_spikes_and_constant_runs():
    """Impact-shaped input, and digital silence - long runs of identical values
    are where a median implementation's tie handling shows up."""
    rng = np.random.default_rng(9)
    env = np.abs(rng.standard_normal(2000)) * 0.01
    env[::137] += 5.0
    env[900:1000] = 0.0
    for win in (16, 33, 128):
        a = _unchunked(env, win)
        b = _chunked(env, win, 2000)
        assert np.array_equal(a[0], b[0]), win
        assert np.array_equal(a[1], b[1]), win


def test_the_chunk_bound_is_declared_and_sane():
    """A bound large enough to be pointless would silently restore the cliff."""
    assert hasattr(audio, "_FLOOR_CHUNK_ELEMS")
    assert 1e5 <= audio._FLOOR_CHUNK_ELEMS <= 5e7


def test_detect_impacts_still_finds_a_planted_impact():
    """End-to-end sanity: the floor is still a floor after the rewrite."""
    sr = 22050
    rng = np.random.default_rng(3)
    x = rng.standard_normal(sr * 3) * 0.002
    for t in (0.6, 1.5, 2.4):
        i = int(t * sr)
        n = int(0.01 * sr)
        x[i:i + n] += np.hanning(n) * rng.standard_normal(n) * 0.9
    ev = audio.detect_impacts(x, sr)
    assert ev, "planted impacts were not detected at all"
    for t in (0.6, 1.5, 2.4):
        assert any(abs(e - t) < 0.08 for e in ev), f"missed the impact at {t}s"
