"""Pooling the gate across clips is a weighted question, not an average.

The calibrated gold clips contribute 26, 24 and 53 no-ball frames. Every session
before Session I pooled the ghost gate by hand from printed tables, and that
invited two specific errors: averaging three percentages as if the clips were the
same size, and — in Session I's own resume list — quietly dropping one of the three
clips from a gate defined as pooled.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

gate_verdict = pytest.importorskip("gate_verdict")


def _row(clip, weights, *, noball, scored, fires_real, recall, far_geo=70.0):
    return {"weights": weights, "clip": clip, "stage": gate_verdict.STAGE,
            "n_noball": noball, "n_scored": scored, "fires_real": fires_real,
            "fires": fires_real, "recall": recall, "far_geo": far_geo}


def test_pooling_weights_clips_by_size_not_equally():
    """A 10-frame clip at 90% and a 90-frame clip at 10% is 18%, not 50%."""
    pooled = gate_verdict.pool({
        "small": _row("small", "w", noball=10, scored=10, fires_real=9, recall=90.0),
        "big": _row("big", "w", noball=90, scored=90, fires_real=9, recall=10.0),
    })
    assert pooled["recall"] == pytest.approx(18.0)
    assert pooled["n_noball"] == 100 and pooled["solid"] == 18


def test_solid_ghosts_pool_as_a_sum_of_counts():
    pooled = gate_verdict.pool({
        c: _row(c, "w", noball=25, scored=100, fires_real=n, recall=70.0)
        for c, n in (("a", 4), ("b", 6), ("c", 4))
    })
    assert pooled["solid"] == 14


def test_far_geo_uses_the_worst_clip_not_the_mean():
    """The gate says far_geo may not drop >2 pts. A mean would let a big gain on an
    easy clip pay for a collapse on the hard one — which is the clip that matters."""
    pooled = gate_verdict.pool({
        "easy": _row("easy", "w", noball=10, scored=10, fires_real=0,
                     recall=80.0, far_geo=90.0),
        "hard": _row("hard", "w", noball=10, scored=10, fires_real=0,
                     recall=50.0, far_geo=40.0),
    })
    assert pooled["far_geo_worst_clip"] == 40.0


def test_required_sample_size_grows_as_the_effect_shrinks():
    """The resolution figures printed next to the verdict. A near-elimination is
    cheap to detect; a 30% cut is an order of magnitude dearer. Getting this
    backwards would make an underpowered null look conclusive."""
    p1 = 14 / 74
    eliminate = gate_verdict.n_per_arm(p1, 0.5 / 74)
    halve = gate_verdict.n_per_arm(p1, p1 / 2)
    cut30 = gate_verdict.n_per_arm(p1, p1 * 0.7)
    assert eliminate < halve < cut30
    assert eliminate < 74 < halve, "74 frames should see an elimination but not a halving"


def test_identical_arms_need_infinite_samples():
    assert gate_verdict.n_per_arm(0.2, 0.2) == float("inf")
