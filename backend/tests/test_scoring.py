"""Tennis scoring state machine: points, deuce/advantage, games, sets, tiebreak."""

from swingvision.scoring import TennisScore


def test_love_game_progression():
    sc = TennisScore()
    assert sc.point("A").display == "15-0"
    assert sc.point("A").display == "30-0"
    assert sc.point("A").display == "40-0"
    res = sc.point("A")
    assert res.display == "Game A"
    assert res.game_won and not res.set_won
    assert sc.games == [1, 0]


def test_deuce_and_advantage():
    sc = TennisScore()
    sc.play(["A", "B", "A", "B", "A"])      # 40-30
    assert sc.point("B").display == "Deuce"  # 40-40
    assert sc.point("A").display == "Advantage A"
    assert sc.point("B").display == "Deuce"  # back to deuce
    assert sc.point("B").display == "Advantage B"
    res = sc.point("B")
    assert res.display == "Game B"
    assert sc.games == [0, 1]


def test_shutout_match():
    sc = TennisScore()
    # 4 points * 6 games * 2 sets = 48 points, all A.
    results = sc.play(["A"] * 48)
    assert sc.finished
    assert sc.winner == "A"
    assert sc.completed_sets == [(6, 0), (6, 0)]
    assert sc.final_str() == "6-0 6-0"
    assert results[-1].match_won
    assert results[-1].display == "Game, set, match A"


def test_cannot_play_after_finish():
    sc = TennisScore()
    sc.play(["A"] * 48)
    try:
        sc.point("A")
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError after match finished")


def test_set_won_six_four():
    sc = TennisScore()
    # A wins 6 games, B wins 4, no tiebreak. Win games by feeding 4 points each.
    for _ in range(4):
        sc.play(["A"] * 4)
        sc.play(["B"] * 4)
    # 4-4 now
    sc.play(["A"] * 4)   # 5-4
    res = sc.play(["A"] * 4)[-1]  # 6-4, set over
    assert res.set_won and not res.match_won
    assert sc.completed_sets[-1] == (6, 4)
    assert sc.sets_won == [1, 0]


def test_tiebreak():
    sc = TennisScore()
    for _ in range(6):
        sc.play(["A"] * 4)   # A wins a game
        sc.play(["B"] * 4)   # B wins a game
    assert sc.games == [6, 6]
    assert sc.in_tiebreak
    # Tiebreak: A wins 7-0.
    res = sc.play(["A"] * 7)[-1]
    assert res.set_won
    assert sc.completed_sets[-1] == (7, 6)
    assert sc.sets_won == [1, 0]
