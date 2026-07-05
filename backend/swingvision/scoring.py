"""scoring.py — tennis scoring state machine (the logic layer).

Deterministic: feed it a sequence of point winners and it produces the running
score, game by game, set by set. No floating point, no model — scoring is rules,
and rules belong here (see CLAUDE.md). This is the kind of exact answer you must
never approximate with ML.

Implements standard tennis:
  - points 0, 15, 30, 40, deuce / advantage, win a game by 2
  - 6 games wins a set, win by 2
  - at 6-6 a 7-point tiebreak (win by 2) decides the set 7-6
  - best-of-3 sets by default (first to 2 sets)
"""

from __future__ import annotations

from dataclasses import dataclass

POINT_LABELS = {0: "0", 1: "15", 2: "30", 3: "40"}


@dataclass
class PointResult:
    """What happened after one point. The pipeline attaches shot_id / rally_id
    to build a schema.ScoreEvent."""
    point_winner: str
    display: str          # "30-15", "Deuce", "Advantage A", "Game A", "Set A", ...
    games_display: str    # current set, "2-1"
    sets_display: str     # sets won, "1-0"
    game_won: bool
    set_won: bool
    match_won: bool


class TennisScore:
    def __init__(
        self,
        player_a: str = "A",
        player_b: str = "B",
        best_of_sets: int = 3,
        tiebreak_at: int = 6,
        tiebreak_points: int = 7,
    ) -> None:
        self.pa = player_a
        self.pb = player_b
        self.sets_to_win = best_of_sets // 2 + 1
        self.tb_at = tiebreak_at
        self.tb_points = tiebreak_points

        self.points = [0, 0]          # points in the current game
        self.games = [0, 0]           # games in the current set
        self.sets_won = [0, 0]
        self.completed_sets: list[tuple[int, int]] = []
        self.in_tiebreak = False
        self.finished = False
        self.winner: str | None = None

    # -- public API ----------------------------------------------------------
    def point(self, winner: str) -> PointResult:
        """Record a point won by `winner` and return the resulting score."""
        if self.finished:
            raise RuntimeError("match is already finished")
        i = self._index(winner)
        j = 1 - i
        self.points[i] += 1
        was_tiebreak = self.in_tiebreak

        if not self._game_decided(i, j):
            return self._result(winner, self._point_display(), False, False, False)

        # --- game won ---
        self.games[i] += 1
        self.points = [0, 0]
        self.in_tiebreak = False

        if was_tiebreak:
            set_won = True                     # tiebreak winner takes the set 7-6
        else:
            set_won = self.games[i] >= 6 and self.games[i] - self.games[j] >= 2

        if not set_won:
            if self.games[0] == self.tb_at and self.games[1] == self.tb_at:
                self.in_tiebreak = True        # enter the tiebreak at 6-6
            return self._result(winner, f"Game {winner}", True, False, False)

        # --- set won ---
        self.completed_sets.append((self.games[0], self.games[1]))
        self.sets_won[i] += 1
        self.games = [0, 0]

        if self.sets_won[i] >= self.sets_to_win:
            self.finished = True
            self.winner = winner
            return self._result(winner, f"Game, set, match {winner}", True, True, True)
        return self._result(winner, f"Set {winner}", True, True, False)

    def play(self, winners: list[str]) -> list[PointResult]:
        """Convenience: record a whole sequence of point winners."""
        return [self.point(w) for w in winners]

    def final_str(self) -> str:
        """Scoreline like '6-4 3-6 7-5', including the in-progress set."""
        parts = [f"{a}-{b}" for a, b in self.completed_sets]
        if not self.finished and (any(self.games) or any(self.points)):
            parts.append(f"{self.games[0]}-{self.games[1]}")
        return " ".join(parts) if parts else "0-0"

    # -- internals -----------------------------------------------------------
    def _index(self, player: str) -> int:
        if player == self.pa:
            return 0
        if player == self.pb:
            return 1
        raise ValueError(f"unknown player {player!r}")

    def _game_decided(self, i: int, j: int) -> bool:
        threshold = self.tb_points if self.in_tiebreak else 4
        return self.points[i] >= threshold and self.points[i] - self.points[j] >= 2

    def _point_display(self) -> str:
        a, b = self.points
        if self.in_tiebreak:
            return f"{a}-{b}"
        if a >= 3 and b >= 3:
            if a == b:
                return "Deuce"
            return f"Advantage {self.pa if a > b else self.pb}"
        return f"{POINT_LABELS[a]}-{POINT_LABELS[b]}"

    def _result(
        self, winner: str, display: str, game: bool, set_: bool, match: bool
    ) -> PointResult:
        return PointResult(
            point_winner=winner,
            display=display,
            games_display=f"{self.games[0]}-{self.games[1]}",
            sets_display=f"{self.sets_won[0]}-{self.sets_won[1]}",
            game_won=game,
            set_won=set_,
            match_won=match,
        )
