"""The physics arc gate: reprojection alone must not certify a shot (Session E1).

Measured on ground truth (tools/arc_observability.py): one true 87 km/h ball
admits fitted speeds from 55 to 152 km/h, all reprojecting under 0.15 px. And on
real footage, yt_rally2 @60fps produced an arc at reproj 3.5 px claiming 110 km/h
with 10,361 rpm. So `ok` now requires a physical plausibility check as well.
"""
from types import SimpleNamespace

import pytest

from swingvision import speedspin


def readout(speed_kmh, spin_rpm, topspin_rpm=None):
    return SimpleNamespace(speed_kmh=speed_kmh, spin_rpm=spin_rpm,
                           topspin_rpm=spin_rpm if topspin_rpm is None else topspin_rpm)


def test_sane_striker_pinned_arc_is_ok():
    r = speedspin._readout(10, 40, readout(95.0, 2400.0), reproj=3.5, fps=60.0,
                           reproj_max_px=6.0, launch_source="striker_launch")
    assert r["ok"] is True
    assert r["reject_reason"] is None


def test_bounce_only_arc_is_never_ok():
    """E1: with only the bounce pinned, launch depth is free and speed slides
    over a 23.8x range at <0.15px. A clean reprojection proves nothing there."""
    r = speedspin._readout(10, 40, readout(95.0, 2400.0), reproj=1.0, fps=60.0,
                           reproj_max_px=6.0, launch_source="bounce_only")
    assert r["ok"] is False
    assert "striker" in r["reject_reason"]


def test_absurd_spin_is_rejected_even_at_low_reprojection():
    """The real yt_rally2 arc: 3.5px, 110 km/h, 10361 rpm. Pixels loved it."""
    r = speedspin._readout(932, 940, readout(110.0, 10361.0), reproj=3.5, fps=60.0,
                           reproj_max_px=6.0)
    assert r["ok"] is False
    assert "spin" in r["reject_reason"]


def test_absurd_speed_is_rejected_even_at_low_reprojection():
    r = speedspin._readout(10, 40, readout(410.0, 1200.0), reproj=1.0, fps=60.0,
                           reproj_max_px=6.0)
    assert r["ok"] is False
    assert "speed" in r["reject_reason"]


def test_high_reprojection_still_rejected_and_says_so():
    r = speedspin._readout(10, 40, readout(95.0, 2400.0), reproj=125.1, fps=60.0,
                           reproj_max_px=6.0)
    assert r["ok"] is False
    assert "reproj" in r["reject_reason"]


@pytest.mark.parametrize("spin", [3499.0, -3499.0])
def test_band_edges_are_inclusive(spin):
    assert speedspin._readout(0, 10, readout(100.0, spin), 1.0, 60.0, 6.0,
                              launch_source="striker_launch")["ok"]
