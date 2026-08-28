"""`bounce_hypothesis` — the fourth attempt on the smoother, and the first that
does not move a threshold.

These tests pin the two properties the pre-registered gate
(docs/evidence/ball-chain-gate.md) rests on:

  1. OFF is byte-identical to the shipped path, so turning it on is the only
     variable in the A/B (hard rule 7).
  2. It is NOT inert when on, so a null result is a real null and not a flag that
     never fired. `bounce_reset` needed exactly this test: its first fixture was a
     parabola, which is precisely what a constant-acceleration model predicts, so
     nothing was ever rejected and the flag looked inert when it was not.

And the property that makes it a SEPARATION mechanism rather than a looser gate:
a ghost far off the track must be rejected by BOTH hypotheses.
"""
from __future__ import annotations

import numpy as np
import pytest

from swingvision.ball import smooth_forecast


def _bouncing_track(n_down=14, n_up=14, vx=6.0, vy=9.0, g=0.9, e=0.75, x0=200.0, y0=120.0):
    """A ball descending under gravity, bouncing, then rising — in image pixels,
    where y grows DOWNWARD so a descending ball has vy > 0."""
    pts, x, y, v = [], x0, y0, vy
    for _ in range(n_down):
        pts.append([x, y])
        x += vx
        y += v
        v += g
    v = -v * e                      # the bounce: reflect and damp
    for _ in range(n_up):
        pts.append([x, y])
        x += vx
        y += v
        v += g
    return pts


def test_off_is_byte_identical_to_shipped_default():
    """The A/B must differ by the flag and nothing else."""
    track = _bouncing_track()
    base = smooth_forecast(track, fps_eff=30.0)
    off = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=False)
    assert base == off


def test_flag_is_not_inert_on_a_real_bounce():
    """A velocity discontinuity the CA model cannot follow must change the output.

    If this ever passes trivially the fixture is wrong, not the code — see the
    `bounce_reset` parabola mistake recorded in its own docstring.
    """
    track = _bouncing_track()
    off, off_coast, _ = smooth_forecast(track, fps_eff=30.0)
    on, on_coast, _ = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True)

    differing = sum(
        1 for a, b in zip(off, on)
        if (a is None) != (b is None)
        or (a is not None and b is not None and (abs(a[0] - b[0]) > 1e-6 or abs(a[1] - b[1]) > 1e-6))
    )
    assert differing > 0, "flag is inert on a genuine bounce — check the fixture"


def test_it_recovers_more_of_the_post_bounce_ball():
    """The mechanism's whole claim: fewer real detections dropped after a bounce."""
    track = _bouncing_track()
    bounce_i = 14

    def emitted_after_bounce(**kw):
        out, _, _ = smooth_forecast(track, fps_eff=30.0, **kw)
        return sum(1 for p in out[bounce_i:bounce_i + 6] if p is not None)

    assert emitted_after_bounce(bounce_hypothesis=True) >= emitted_after_bounce()


def test_a_ghost_is_rejected_by_BOTH_hypotheses():
    """The separation property, and the reason this cannot buy coverage with junk.

    Session I measured every one of the 19 chain false locks sitting 208-829 px
    off the track. A detection that far out must fail the reflected hypothesis
    exactly as it fails the continuing one — the gate is the same number.
    """
    track = _bouncing_track()
    ghost_i = 8
    with_ghost = [p[:] for p in track]
    with_ghost[ghost_i] = [track[ghost_i][0] + 400.0, track[ghost_i][1] - 300.0]

    on, _, _ = smooth_forecast(with_ghost, fps_eff=30.0, bounce_hypothesis=True)

    assert on[ghost_i] is None or abs(on[ghost_i][0] - with_ghost[ghost_i][0]) > 50.0, (
        "the ghost was adopted — the second hypothesis is acting as a looser gate"
    )


def test_an_upward_model_never_triggers_the_bounce_branch():
    """A ball already rising cannot be bouncing. Guards against a false lock
    overhead flipping the state."""
    rising = [[200.0 + 6.0 * i, 300.0 - 9.0 * i + 0.45 * i * i] for i in range(20)]
    rising[10] = [rising[10][0] + 250.0, rising[10][1] + 180.0]   # junk below

    off = smooth_forecast(rising, fps_eff=30.0)
    on = smooth_forecast(rising, fps_eff=30.0, bounce_hypothesis=True)
    assert off == on, "bounce branch fired while the model was ascending"


@pytest.mark.parametrize("res_scale", [1.0, 1.5])
def test_scales_with_resolution(res_scale):
    """Every pixel threshold in this file scales by frame_height/720 (trap T03).
    The band is a velocity ratio, so the branch must survive the scaling."""
    track = [[x * res_scale, y * res_scale] for x, y in _bouncing_track()]
    out, _, _ = smooth_forecast(
        track, fps_eff=30.0, bounce_hypothesis=True, res_scale=res_scale
    )
    assert any(p is not None for p in out)


# --- v2: `restitution_set`, the position fix -------------------------------
#
# v1 passed the separation bar but raised `wrong` on ball frames. The named
# cause was `restitution_band`: it adds (band*vy_prev)^2 to S[1,1], so at a large
# pre-bounce vy the y-gate widens exactly when the ball is fastest while the
# x-gate stays tight. v2 removes the inflation and enumerates e instead, each
# candidate tested at the UNMODIFIED S.
#
# Gate: docs/evidence/bounce-hypothesis-v2-gate.md. Result: FAILS (P2, P3, P6,
# P7). Off by default. These tests pin the mechanism, not the verdict.


def test_v2_absent_reproduces_v1_exactly():
    """Adding v2 must not have moved v1 — v1's committed numbers stay valid."""
    track = _bouncing_track()
    v1 = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True)
    v1_explicit = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True,
                                  restitution_set=None)
    assert v1 == v1_explicit


def test_v2_off_is_still_byte_identical_to_shipped():
    """A restitution_set with the flag OFF must do nothing at all."""
    track = _bouncing_track()
    base = smooth_forecast(track, fps_eff=30.0)
    off = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=False,
                          restitution_set=[0.6, 0.75, 0.9])
    assert base == off


def test_v2_is_not_inert():
    """A null result must be a real null, not a flag that never fired — the
    fixture trap `bounce_reset` and v1 both hit."""
    track = _bouncing_track()
    v1, _, _ = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True)
    v2, _, _ = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True,
                               restitution_set=[0.6, 0.75, 0.9])
    off, _, _ = smooth_forecast(track, fps_eff=30.0)
    assert any((a is None) != (b is None)
               or (a is not None and b is not None
                   and (abs(a[0] - b[0]) > 1e-9 or abs(a[1] - b[1]) > 1e-9))
               for a, b in zip(off, v2)), "v2 is inert vs OFF"


def test_the_synthetic_fixture_CANNOT_distinguish_v1_from_v2():
    """A GUARD AGAINST TUNING v2 ON A FIXTURE, and a recorded negative.

    The arithmetic is not in doubt: v1 gates against Sb = S + diag(0, c) with
    c = (band*vy_prev)^2 >= 0, and inflating a variance can only LOWER the chi2
    statistic, so v1 accepts a superset of what v2's unmodified S accepts. v2 is
    strictly tighter in y by construction.

    But that does NOT show up in this file's fixtures. Swept vy 18-42 px/frame
    against a post-bounce y-displacement of 6-44 px - 100 combinations - v1 and
    v2 emit an IDENTICAL number of real frames in every one, because a detection
    the bounce branch rejects is often re-seeded a frame or two later by the
    ordinary `reset_after` path, so emitted-frame count is a poor proxy for
    branch acceptance.

    So: do not measure this mechanism on a synthetic bounce. It discriminates
    only on real footage, where v1 and v2 differ substantially (gold_UHf0LeMU2pg
    -3 hits/+5 wrong under v1 vs 0/+3 under v2). The numbers live in
    docs/evidence/bounce-hypothesis-v2-gate.md. This test exists so that a future
    attempt does not "validate" a change here and conclude it is inert.
    """
    for vy in (18.0, 30.0, 42.0):
        for dy in (8, 20, 32, 44):
            track = _bouncing_track(vy=vy, g=1.2)
            track[14] = [track[14][0], track[14][1] + dy]

            def n_real(**kw):
                out, coast, _ = smooth_forecast(track, fps_eff=30.0, **kw)
                return sum(1 for i, p in enumerate(out) if p is not None and not coast[i])

            assert n_real(bounce_hypothesis=True, restitution=0.75) ==                    n_real(bounce_hypothesis=True, restitution_set=[0.75]), (
                f"vy={vy} dy={dy}: the fixture now DOES discriminate v1 from v2. "
                "That is a real finding - update this test rather than deleting it."
            )


def test_v2_picks_the_lowest_chi2_candidate_deterministically():
    """Enumeration must be order-independent, or the arms differ by more than
    the flag under test (hard rule 7)."""
    track = _bouncing_track()
    a, _, _ = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True,
                              restitution_set=[0.6, 0.75, 0.9])
    b, _, _ = smooth_forecast(track, fps_eff=30.0, bounce_hypothesis=True,
                              restitution_set=[0.9, 0.6, 0.75])
    assert a == b


def test_v2_still_rejects_a_ghost_far_off_the_track():
    """The separation property must survive the change.

    NOTE this fixture is a 400x300 px ghost against a clean model. The MEASURED
    result is that the reflected hypothesis does NOT reject every far ghost in
    the field: on gold_shell f226 a lock 502 px from the human click was admitted
    at the unmodified S, because reflecting vy moves the predicted position far
    enough to cover it. The second hypothesis has its own false-acceptance
    region. This test pins the easy case; it does not license the general claim.
    """
    track = _bouncing_track()
    ghost_i = 8
    with_ghost = [p[:] for p in track]
    with_ghost[ghost_i] = [track[ghost_i][0] + 400.0, track[ghost_i][1] - 300.0]
    on, _, _ = smooth_forecast(with_ghost, fps_eff=30.0, bounce_hypothesis=True,
                               restitution_set=[0.6, 0.75, 0.9])
    assert on[ghost_i] is None or abs(on[ghost_i][0] - with_ghost[ghost_i][0]) > 50.0
