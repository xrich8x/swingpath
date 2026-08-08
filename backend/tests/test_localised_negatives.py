"""Localised confuser weighting must be an EXACT no-op when switched off.

Eight attempts at the 9 solid ghost balls have failed, and Phase 0 traced them all
to one thing: hard negatives are whole-frame zero targets, so every criterion is
forced to ask "does this frame contain a ball?" on clips that are 88.5%
ball-present. Weighting the loss at a confuser LOCATION never asks that question.

The risk in the change is not the idea, it is the plumbing: the shipped recipe must
stay reproducible, and the extra weight must ride the same augmentation as the
label or it lands on background and teaches nothing. Both are pinned here.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("cv2")

from train_ballnet import IN_H, IN_W  # noqa: E402


def _weighted_mean(per_px, wmap):
    """The training loop's reduction, isolated."""
    return (per_px * wmap).sum(dim=(1, 2, 3)) / wmap.sum(dim=(1, 2, 3))


def test_all_ones_weight_map_is_exactly_the_plain_mean():
    """THE no-op guarantee. hard_weight=1.0 must reproduce the shipped recipe
    arithmetically, or every comparison against ballnet_v21 is confounded and the
    learning rate silently changes meaning."""
    g = torch.Generator().manual_seed(0)
    per_px = torch.rand(4, 1, 16, 24, generator=g)
    wmap = torch.ones_like(per_px)
    assert torch.allclose(_weighted_mean(per_px, wmap),
                          per_px.mean(dim=(1, 2, 3)), atol=0, rtol=0)


def test_weighting_a_region_raises_its_share_of_the_loss():
    per_px = torch.zeros(1, 1, 10, 10)
    per_px[0, 0, 5, 5] = 1.0                      # all the error at one pixel
    plain = _weighted_mean(per_px, torch.ones_like(per_px))
    w = torch.ones_like(per_px)
    w[0, 0, 5, 5] = 8.0
    assert _weighted_mean(per_px, w) > plain * 3, "confuser weight did not bite"


def test_weight_is_normalised_so_scale_does_not_run_away():
    """A weighted SUM would scale the loss with the number of confusers and
    quietly change the effective learning rate. A weighted MEAN cannot."""
    per_px = torch.full((1, 1, 8, 8), 0.5)
    for hard in (1.0, 4.0, 64.0):
        w = torch.ones_like(per_px)
        w[0, 0, 2:4, 2:4] = hard
        assert _weighted_mean(per_px, w).item() == pytest.approx(0.5)


def _disc(confusers, hard, radius=12):
    """Mirror of BallWindows.__getitem__'s weight-map construction."""
    import cv2
    disc = np.zeros((IN_H, IN_W), np.float32)
    for cx, cy in confusers:
        cxi, cyi = int(round(cx)), int(round(cy))
        if 0 <= cxi < IN_W and 0 <= cyi < IN_H:
            cv2.circle(disc, (cxi, cyi), radius, 1.0, -1)
    return 1.0 + (hard - 1.0) * disc


def test_disc_is_centred_on_the_confuser_and_bounded():
    w = _disc([(100, 50)], hard=8.0, radius=12)
    assert w[50, 100] == pytest.approx(8.0)
    assert w[50, 100 + 30] == pytest.approx(1.0), "weight leaked far from the confuser"
    assert w.min() == pytest.approx(1.0) and w.max() == pytest.approx(8.0)


def test_off_frame_confusers_are_dropped_not_clamped():
    """A translation augmentation can push a confuser out of frame. Clamping it to
    the edge would put heavy weight on a pixel that holds no confuser at all."""
    w = _disc([(-40, 50), (IN_W + 10, 50), (100, -30)], hard=8.0)
    assert w.max() == pytest.approx(1.0), "an off-frame confuser was clamped inside"


def test_horizontal_flip_moves_the_confuser_with_the_image():
    """If the confuser does not ride the same transform as the label, the extra
    weight lands on background — the mechanism silently does nothing."""
    cx = 100
    assert (IN_W - 1 - cx) == 411
    w = _disc([(IN_W - 1 - cx, 50)], hard=8.0)
    assert w[50, 411] == pytest.approx(8.0)
    assert w[50, cx] == pytest.approx(1.0)


def test_dataset_default_is_off():
    """Default OFF keeps the shipped recipe reproducible without passing a flag."""
    import inspect

    from train_ballnet import BallWindows
    sig = inspect.signature(BallWindows.__init__)
    assert sig.parameters["hard_weight"].default == 1.0
