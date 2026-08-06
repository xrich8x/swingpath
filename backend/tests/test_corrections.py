"""Human corrections must change facts and RE-DERIVE everything downstream.

README has listed a manual-correction UI as a known gap since the start, because
vision scoring is brittle by construction: a rally winner rests on a bounce a
single camera cannot always place. The danger in fixing it is subtle — patching a
displayed score instead of replaying it would leave the match.json internally
inconsistent, which is worse than being wrong in a knowable way.

So these tests pin the property that matters: correct a FACT, and the derived
values follow from the same code the pipeline uses.
"""

import pytest

from swingvision import corrections


def _match():
    """Two rallies, A wins both — 30-0 in the first game."""
    return {
        "players": [{"id": "A"}, {"id": "B"}],
        "shots": [
            {"id": 1, "rally_id": 1, "player": "A", "type": "forehand",
             "t_hit_s": 1.0, "speed_kmh": 80.0, "hit_xy": [0, 0],
             "bounce_xy": [1, 10], "bounce_t_s": 1.5, "is_in": True, "call": "in"},
            {"id": 2, "rally_id": 2, "player": "A", "type": "forehand",
             "t_hit_s": 5.0, "speed_kmh": 90.0, "hit_xy": [0, 0],
             "bounce_xy": [1, 10], "bounce_t_s": 5.5, "is_in": True, "call": "in"},
        ],
        "rallies": [
            {"id": 1, "start_s": 0.0, "end_s": 2.0, "shot_ids": [1], "winner": "A"},
            {"id": 2, "start_s": 4.0, "end_s": 6.0, "shot_ids": [2], "winner": "A"},
        ],
        "score": {"final": "", "sets": [], "games": [0, 0], "timeline": []},
        "stats": {},
    }


def test_correcting_a_rally_winner_replays_the_score():
    m = _match()
    fixed, res = corrections.apply_corrections(
        m, [{"target": "rally.winner", "id": 2, "value": "B", "original": "A"}])
    assert len(res.applied) == 1 and res.ok
    winners = [e["point_winner"] for e in fixed["score"]["timeline"]]
    assert winners == ["A", "B"], "score was not replayed from the corrected winner"
    assert fixed["score"]["timeline"][-1]["display"] != \
        m["score"].get("final"), "score block was not re-derived"


def test_input_is_not_mutated():
    m = _match()
    corrections.apply_corrections(
        m, [{"target": "rally.winner", "id": 2, "value": "B"}])
    assert m["rallies"][1]["winner"] == "A", "apply_corrections mutated its input"


def test_correcting_a_line_call_re_derives_stats():
    m = _match()
    fixed, res = corrections.apply_corrections(
        m, [{"target": "shot.call", "id": 1, "value": "out", "original": "in"}])
    assert res.ok and len(res.applied) == 1
    assert fixed["stats"]["line_calls"]["out"] >= 1, "line-call stats not recomputed"


def test_correcting_a_shot_type_re_derives_the_mix():
    m = _match()
    fixed, _ = corrections.apply_corrections(
        m, [{"target": "shot.type", "id": 1, "value": "backhand", "original": "forehand"}])
    assert fixed["stats"]["shot_mix"].get("backhand") == 1


def test_is_idempotent():
    m = _match()
    c = [{"target": "rally.winner", "id": 2, "value": "B", "original": "A"}]
    once, _ = corrections.apply_corrections(m, c)
    twice, res2 = corrections.apply_corrections(once, c)
    assert res2.applied == [], "re-applying the same correction changed something"
    assert once["score"]["final"] == twice["score"]["final"]


def test_stale_correction_is_refused_not_silently_applied():
    """A corrections file written against a different analysis must not be
    applied blind — that is how two people get the same file and different scores."""
    m = _match()
    _, res = corrections.apply_corrections(
        m, [{"target": "rally.winner", "id": 1, "value": "B", "original": "B"}])
    assert not res.ok
    assert "stale" in res.skipped[0]["reason"]


def test_unknown_target_and_missing_id_are_reported():
    m = _match()
    _, res = corrections.apply_corrections(m, [
        {"target": "shot.speed_kmh", "id": 1, "value": 100},
        {"target": "rally.winner", "id": 99, "value": "B"},
    ])
    assert len(res.skipped) == 2
    assert "unknown target" in res.skipped[0]["reason"]
    assert "no rally with id 99" in res.skipped[1]["reason"]


def test_strict_raises_instead_of_collecting():
    m = _match()
    with pytest.raises(ValueError):
        corrections.apply_corrections(
            m, [{"target": "nope", "id": 1, "value": "x"}], strict=True)


def test_diff_summary_reports_the_score_change():
    m = _match()
    fixed, _ = corrections.apply_corrections(
        m, [{"target": "rally.winner", "id": 2, "value": "B", "original": "A"}])
    d = corrections.diff_summary(m, fixed)
    assert d["score_changed"] is True
    assert d["final_after"] == fixed["score"]["final"]
