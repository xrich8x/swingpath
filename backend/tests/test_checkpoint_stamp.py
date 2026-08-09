"""A checkpoint must say how it was made.

`ballnet_v21.pt` — the shipped detector — holds nothing but its weights. Session I
could not A/B against it for that reason and had to spend an hour training its own
baseline arm, and the same session then discovered the trainer had no seed at all,
so its two arms differed by initialisation and data order as well as by the flag
under test. Both failures are cheap to prevent and expensive to notice late.

These pin the stamp's contract, not its values.
"""

import argparse
import json

import pytest

pytest.importorskip("torch")
pytest.importorskip("cv2")

from train_ballnet import recipe_stamp  # noqa: E402


def _args(**over):
    base = dict(data="../data/ball_dataset", epochs=15, batch=16, lr=1e-3,
                out="weights/x.pt", hard_weight=1.0, conf_radius=12, device="cuda",
                exclude=[], motion_attention=False, seed=0)
    base.update(over)
    return argparse.Namespace(**base)


def test_stamp_records_the_flag_under_test_and_the_seed():
    """The two things Session I could not recover after the fact."""
    s = recipe_stamp(_args(hard_weight=8.0, seed=3), 1_000_000, (10, 2, 3, 1), 2521)
    assert s["args"]["hard_weight"] == 8.0
    assert s["args"]["seed"] == 3
    assert s["confuser_samples"] == 2521


def test_confuser_count_distinguishes_a_treatment_run_from_a_no_op():
    """--hard-weight 8 with no confuser files IS the shipped recipe, arithmetically.
    Without this count the two are indistinguishable once the run has finished."""
    noop = recipe_stamp(_args(hard_weight=8.0), 1, (1, 0, 1, 0), 0)
    real = recipe_stamp(_args(hard_weight=8.0), 1, (1, 0, 1, 0), 2521)
    assert noop["confuser_samples"] == 0 and real["confuser_samples"] > 0


def test_stamp_is_json_serialisable():
    """It rides in a torch.save pickle, but it is only useful if a human or a tool
    can read it out without unpickling arbitrary objects."""
    json.dumps(recipe_stamp(_args(), 1, (1, 1, 1, 1), 0))


def test_stamp_says_the_checkpoint_is_not_the_last_epoch():
    """Selection is best-val, so 'trained 15 epochs' does not mean 'epoch 15'.
    Reading a stamp and assuming otherwise misdates every comparison."""
    assert "NOT the last epoch" in recipe_stamp(_args(), 1, (1, 1, 1, 1), 0)["selection"]


def test_seed_default_is_fixed_so_two_runs_are_paired_by_default():
    """An unseeded A/B cannot attribute a small effect to the flag under test —
    which is exactly what happened to Session I's first pair."""
    import train_ballnet
    src = open(train_ballnet.__file__, encoding="utf-8").read()
    assert '"--seed"' in src and "torch.manual_seed(args.seed)" in src
