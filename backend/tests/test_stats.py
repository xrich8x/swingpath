"""Serve/rally statistics math (the logic layer over shots + rallies)."""

from swingvision import court, schema
from swingvision.schema import Rally, Shot


def _serve(id_, player, call, *, confident=True, bounce=None):
    """A serve Shot with just the fields the stats care about."""
    if bounce is None:
        # Default to a plainly-in bounce in the correct diagonal box.
        bounce = [court.X_CENTER - 1.0, 14.0] if player == "A" else [court.X_CENTER + 1.0, 9.0]
    return Shot(
        id=id_, rally_id=0, player=player, type="serve", t_hit_s=float(id_),
        speed_kmh=120.0, hit_xy=[court.X_CENTER, 0.3 if player == "A" else 23.4],
        bounce_xy=bounce, bounce_t_s=float(id_) + 0.4,
        is_in=(call == "in"), call=call, call_confident=confident,
    )


def _rally_shot(id_, player="A"):
    return Shot(
        id=id_, rally_id=0, player=player, type="forehand", t_hit_s=float(id_),
        speed_kmh=60.0, hit_xy=[5.0, 5.0], bounce_xy=[5.0, 16.0],
        bounce_t_s=float(id_) + 0.4, is_in=True, call="in",
    )


# --- First / second serve state machine ------------------------------------

def test_fault_then_serve_is_second():
    order = schema.derive_serve_order([_serve(0, "A", "out"), _serve(1, "A", "in")])
    assert order[0] == "first"
    assert order[1] == "second"


def test_double_fault_resets_next_to_first():
    shots = [_serve(0, "A", "out"), _serve(1, "A", "out"), _serve(2, "A", "in")]
    order = schema.derive_serve_order(shots)
    assert [order[0], order[1], order[2]] == ["first", "second", "first"]


def test_rally_play_between_serves_means_first():
    shots = [_serve(0, "A", "in"), _rally_shot(1, "B"), _serve(2, "A", "in")]
    order = schema.derive_serve_order(shots)
    assert order[0] == "first" and order[2] == "first"


def test_server_change_after_fault_is_first():
    # A faults, then B serves (different player) -> B's serve is a first serve.
    shots = [_serve(0, "A", "out"), _serve(1, "B", "in")]
    order = schema.derive_serve_order(shots)
    assert order[1] == "first"


def test_low_confidence_serve_is_unknown():
    shots = [_serve(0, "A", "out", confident=False), _serve(1, "A", "in")]
    order = schema.derive_serve_order(shots)
    # The first is unknown; because we won't guess it faulted, the next is first.
    assert order[0] == "unknown"
    assert order[1] == "first"


# --- Aggregation in compute_stats ------------------------------------------

def test_serve_split_counts():
    shots = [_serve(0, "A", "out"), _serve(1, "A", "in"),
             _serve(2, "A", "in")]
    rallies = [Rally(id=0, start_s=0.0, end_s=3.0, shot_ids=[0, 1, 2], winner="A")]
    stats = schema.compute_stats(shots, rallies)
    sp = stats.serve_split["A"]
    assert sp["first_total"] == 2 and sp["first_in"] == 1   # s0 (out) + s2 (in)
    assert sp["second_total"] == 1 and sp["second_in"] == 1  # s1
    assert sp["unknown"] == 0


def test_serve_placement_aggregation_and_faults_excluded():
    # Two in serves (T and wide, deuce court) + one fault (excluded from placement).
    t_serve = _serve(0, "A", "in", bounce=[court.X_CENTER - 0.3, 14.0])   # deuce T
    wide_serve = _serve(1, "A", "in", bounce=[court.X_LEFT_SINGLES + 0.3, 14.0])  # deuce wide
    fault = _serve(2, "A", "out", bounce=[court.X_CENTER - 1.0, 19.5])    # long: not placed
    rallies = [Rally(id=0, start_s=0.0, end_s=3.0, shot_ids=[0, 1, 2], winner="A")]
    stats = schema.compute_stats([t_serve, wide_serve, fault], rallies)
    pl = stats.serve_placement["A"]
    assert pl["deuce"]["T"] == 1
    assert pl["deuce"]["wide"] == 1
    assert pl["total"] == 2   # the fault is not placed


def test_serve_placement_skips_unconfident_call():
    s = _serve(0, "A", "in", confident=False, bounce=[court.X_CENTER - 0.3, 14.0])
    rallies = [Rally(id=0, start_s=0.0, end_s=1.0, shot_ids=[0], winner="A")]
    stats = schema.compute_stats([s], rallies)
    assert stats.serve_placement["A"]["total"] == 0


def test_rally_length_buckets():
    rallies = [
        Rally(id=0, start_s=0, end_s=1, shot_ids=[0, 1], winner="A"),          # 1-3
        Rally(id=1, start_s=0, end_s=1, shot_ids=list(range(5)), winner="A"),  # 4-6
        Rally(id=2, start_s=0, end_s=1, shot_ids=list(range(8)), winner="A"),  # 7-9
        Rally(id=3, start_s=0, end_s=1, shot_ids=list(range(12)), winner="A"), # 10+
    ]
    stats = schema.compute_stats([], rallies)
    assert stats.rally_length_buckets == {"1-3": 1, "4-6": 1, "7-9": 1, "10+": 1}


def test_shot_mix_by_player():
    shots = [_serve(0, "A", "in"), _rally_shot(1, "A"), _rally_shot(2, "B")]
    stats = schema.compute_stats(shots, [])
    assert stats.shot_mix_by_player["A"] == {"serve": 1, "forehand": 1}
    assert stats.shot_mix_by_player["B"] == {"forehand": 1}
