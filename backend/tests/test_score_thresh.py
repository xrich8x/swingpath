"""The detector's score threshold: reachable, recorded, and sweepable in memory.

`score_thresh = 0.5` was hardcoded in four places in ball.py, reachable from no
tool or CLI, absent from the perception-cache provenance, and had never been
swept in this project's history. Session F made it a dial. These tests pin the
three properties that make the dial trustworthy.

The load-bearing one is EQUIVALENCE: eval_detector_gold sweeps thresholds in
memory from a single GPU pass, which is only legitimate because detect() takes
the heatmap argmax BEFORE comparing to the threshold — so the peak's position
does not depend on the threshold. If anyone ever makes the peak selection
threshold-aware, the sweep silently starts lying, and this test is what catches
it.
"""

import numpy as np
import pytest

from swingvision import ball as B


class FakeNet:
    """Stands in for BallNet: emits a logit map with one controllable peak."""

    def __init__(self, peak):
        self.peak = peak

    def __call__(self, inp):
        import torch
        hm = torch.full((1, 1, 288, 512), -20.0)
        # sigmoid(logit) == peak
        p = min(max(self.peak, 1e-6), 1 - 1e-6)
        hm[0, 0, 100, 200] = float(np.log(p / (1 - p)))
        return hm

    def eval(self):
        return self

    def to(self, device):
        return self

    def parameters(self):
        return iter(())


def make_det(peak, thresh):
    det = B.OurBallDetector.__new__(B.OurBallDetector)
    det.device = "cpu"
    det.score_thresh = thresh
    det.model = FakeNet(peak)
    det.last_sub = None
    det.last_score = 0.0
    det.last_pt = None
    from collections import deque
    det._buf = deque(maxlen=3)
    return det


def run(det, n=3):
    frame = np.zeros((720, 1280, 3), np.uint8)
    out = None
    for _ in range(n):
        out = det.detect(frame)
    return out


def test_peak_position_does_not_depend_on_the_threshold():
    """THE claim the in-memory sweep rests on."""
    pts = []
    for th in (0.1, 0.4, 0.5, 0.8, 0.95):
        det = make_det(0.9, th)
        run(det)
        pts.append(det.last_pt)
    assert len(set(pts)) == 1
    assert pts[0] is not None


def test_sweeping_in_memory_equals_a_real_pass_at_each_threshold():
    """Score the probe (pt, peak) against a threshold and compare to what the
    detector itself returns when built at that threshold. Any divergence means
    the sweep is reporting a pipeline nobody runs."""
    probe = make_det(0.62, 0.0)
    run(probe)
    pt, score = probe.last_pt, probe.last_score
    for th in (0.4, 0.5, 0.6, 0.7, 0.8):
        in_memory = pt if score >= th else None
        real = run(make_det(0.62, th))
        assert (in_memory is None) == (real is None), th
        if real is not None:
            assert in_memory == pytest.approx(real)


def test_threshold_actually_gates():
    assert run(make_det(0.62, 0.5)) is not None
    assert run(make_det(0.62, 0.7)) is None


def test_last_score_is_recorded_even_when_rejected():
    """The reject path must still leave evidence, or a sweep can only ever move
    the threshold DOWN from whatever the probe ran at."""
    det = make_det(0.31, 0.7)
    assert run(det) is None
    assert det.last_score == pytest.approx(0.31, abs=1e-3)
    assert det.last_pt is not None


def test_env_hook_overrides_the_default(monkeypatch):
    """Same pattern as BALLNET_WEIGHTS: point a benchmark at a different
    operating point without threading an argument through every call site."""
    import inspect
    sig = inspect.signature(B.OurBallDetector.__init__)
    assert sig.parameters["score_thresh"].default == 0.5

    from swingvision import pipeline
    monkeypatch.setenv("BALLNET_SCORE_THRESH", "0.65")
    assert pipeline._ball_score_thresh() == pytest.approx(0.65)
    monkeypatch.delenv("BALLNET_SCORE_THRESH")
    assert pipeline._ball_score_thresh() == pytest.approx(0.5)


def test_provenance_records_and_flags_a_threshold_change(monkeypatch):
    """A cache built at one threshold is not a cache for another. Before this,
    a sweep would have silently re-read the previous arm's perception."""
    from swingvision import pipeline
    H = np.eye(3)
    prov = pipeline._build_provenance("ours", {}, "pose", "cpu", 70.0, 3.0,
                                      True, H)
    assert prov["ball_score_thresh"] == pytest.approx(0.5)
    assert pipeline._provenance_mismatches(prov, "cpu", 70.0, H) == []
    monkeypatch.setenv("BALLNET_SCORE_THRESH", "0.7")
    diffs = pipeline._provenance_mismatches(prov, "cpu", 70.0, H)
    assert any("score threshold" in d for d in diffs)
