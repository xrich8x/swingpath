"""audio.py: impact detection + conservative fusion (Session E3b).

The detector is scored on synthetic audio where the ground truth is exact:
clicks of known times buried in noise. No real-footage assertion lives here —
every YouTube clip in data/ was pulled without an audio stream, so the real
measurement (tools/audio_hits.py vs the HUD reference) waits on new footage.
"""
import numpy as np
import pytest

from swingvision import audio

SR = 16000


def synth(click_times, dur=10.0, noise=0.01, amp=0.6, seed=0):
    """White-ish noise floor + short 3 kHz bursts at the given times."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, noise, int(dur * SR))
    t_burst = np.arange(int(0.008 * SR)) / SR          # 8 ms pop
    burst = amp * np.sin(2 * np.pi * 3000 * t_burst) * np.hanning(t_burst.size)
    for t in click_times:
        i = int(t * SR)
        x[i:i + burst.size] += burst[:max(0, x.size - i)]
    return x.astype(np.float32)


def test_finds_every_click_and_nothing_else():
    truth = [1.0, 2.5, 4.2, 6.8, 9.1]
    got = audio.detect_impacts(synth(truth), SR)
    assert len(got) == len(truth)
    for t, g in zip(truth, sorted(got)):
        assert abs(t - g) < 0.02, f"click at {t}s detected at {g}s"


def test_silence_yields_nothing():
    assert audio.detect_impacts(synth([]), SR) == []


def test_close_pair_deduplicated_to_one():
    """Direct sound + echo 80 ms later must not become two hits."""
    got = audio.detect_impacts(synth([3.0, 3.08]), SR)
    assert len(got) == 1


def test_constant_racket_gives_up():
    """A pathologically event-dense signal must return [] (declare useless),
    not spray hundreds of hits into the events layer."""
    truth = [round(0.3 * k, 2) for k in range(1, 30)]   # ~3.3 events/s
    got = audio.detect_impacts(synth(truth, dur=10.0), SR)
    assert got == []


def test_nonstationary_floor():
    """Clicks stay detectable when the noise floor doubles mid-clip
    (rolling threshold; a global one fails this)."""
    x = synth([2.0, 8.0], noise=0.008)
    x[int(5 * SR):] += np.random.default_rng(1).normal(0, 0.02, x.size - int(5 * SR)).astype(np.float32)
    got = audio.detect_impacts(x, SR)
    assert len(got) == 2
    assert abs(got[0] - 2.0) < 0.02 and abs(got[1] - 8.0) < 0.02


class TestFuseHits:
    FPS = 60.0

    def test_audio_confirms_existing_hit(self):
        track_ok = [True] * 600
        fused, st = audio.fuse_hits([120], [2.01], track_ok, self.FPS)
        assert fused == [120]
        assert st["confirmed"] == 1 and st["added"] == 0

    def test_audio_adds_supported_hit(self):
        track_ok = [True] * 600
        fused, st = audio.fuse_hits([120], [5.0], track_ok, self.FPS)
        assert fused == [120, 300]
        assert st["added"] == 1

    def test_audio_without_track_support_is_dropped(self):
        track_ok = [False] * 600
        fused, st = audio.fuse_hits([], [5.0], track_ok, self.FPS)
        assert fused == []
        assert st["unsupported"] == 1

    def test_out_of_range_time_ignored(self):
        fused, st = audio.fuse_hits([], [99.0], [True] * 60, self.FPS)
        assert fused == []
        assert st["added"] == st["unsupported"] == 0
