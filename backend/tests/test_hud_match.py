"""The HUD matcher — pins the cascade bug Session F found and fixed.

hud_compare.py used to pair shots with SwingVision HUD panels greedily, forward,
with a hard `lag >= 0` floor. That floor is not physical: our own t_hit_s carries
a +/-2-frame error, so a panel can be timestamped slightly BEFORE the hit it
describes. On data/output/rally2_seg10.json the consequence was measured — one
0.13 s timing error cascaded into two wrong verdicts and manufactured a phantom
out of a shot the human gold clicks exonerate.

These tests use the real timings from that clip, so a regression reproduces the
original failure rather than an abstraction of it.
"""

from hud_compare import match_monotonic


def shots(*ts):
    return [{"t_hit_s": t} for t in ts]


def readings(*ts):
    return [{"t_start_s": t} for t in ts]


# The exact frames of the cascade, from data/output/rally2_seg10.json and
# data/gold/hud_yt_rally2.json: two of our shots, two HUD panels.
CASCADE_SHOTS = shots(14.73, 15.73)
CASCADE_HUD = readings(14.60, 16.20)


def test_cascade_pairs_both_shots():
    """The bug: 14.73 could not take 14.60 (lag -0.13), so it took 16.20 and
    orphaned 15.73. Both must now pair, in order."""
    pairs = match_monotonic(CASCADE_SHOTS, CASCADE_HUD, -0.25, 2.0)
    assert [(i, j) for i, j, _ in pairs] == [(0, 0), (1, 1)]
    lags = [round(lag, 2) for _, _, lag in pairs]
    assert lags == [-0.13, 0.47]


def test_hard_zero_floor_still_loses_a_shot():
    """Guards the DIAGNOSIS, not just the fix.

    The 14.60 panel is unreachable from either shot under a `lag >= 0` floor, so
    the two shots are left competing for the single 16.20 panel and one of them
    MUST be orphaned no matter how clever the assignment is. That is why the
    window is the load-bearing change here and the monotonic algorithm alone
    would not have been enough: it fixes cascades, it cannot conjure a legal
    pairing that the window forbids.
    """
    assert len(match_monotonic(CASCADE_SHOTS, CASCADE_HUD, 0.0, 2.0)) == 1
    assert len(match_monotonic(CASCADE_SHOTS, CASCADE_HUD, -0.25, 2.0)) == 2


def test_matching_is_order_preserving():
    """A later stroke may never claim an earlier stroke's panel. This is the
    property that stops one mispairing from cascading down a whole rally."""
    pairs = match_monotonic(shots(1.0, 2.0, 3.0),
                            readings(1.5, 2.5, 3.5), -0.25, 2.0)
    idx = [(i, j) for i, j, _ in pairs]
    assert idx == sorted(idx)
    assert [j for _, j in idx] == sorted(j for _, j in idx)


def test_maximises_pair_count_not_greedy_first_fit():
    """Greedy-forward gives shot 0 the 2.9 s panel (the first inside a 2 s
    window), leaving shot 3.0 nothing. Maximum cardinality is 2."""
    pairs = match_monotonic(shots(1.0, 3.0), readings(2.9), -0.25, 2.0)
    assert len(pairs) == 1
    pairs = match_monotonic(shots(1.0, 3.0), readings(1.5, 3.4), -0.25, 2.0)
    assert len(pairs) == 2


def test_out_of_window_readings_are_never_paired():
    assert match_monotonic(shots(1.0), readings(9.0), -0.25, 2.0) == []
    assert match_monotonic(shots(9.0), readings(1.0), -0.25, 2.0) == []


def test_target_lag_breaks_ties_toward_the_observed_median():
    """Two panels are both legal for one shot; the second pass should prefer the
    one nearer the median lag the first pass measured, not the earlier one."""
    s, r = shots(10.0), readings(10.2, 10.8)
    early = match_monotonic(s, r, -0.25, 2.0)                    # target=None
    assert early[0][1] == 0
    late = match_monotonic(s, r, -0.25, 2.0, target_lag=0.8)
    assert late[0][1] == 1


def test_empty_inputs():
    assert match_monotonic([], readings(1.0), -0.25, 2.0) == []
    assert match_monotonic(shots(1.0), [], -0.25, 2.0) == []
