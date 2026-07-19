"""schema.py — the match.json contract (the single source of truth).

The frontend reads exactly the shape produced here. Change the data shape HERE
and update frontend/src/lib accordingly; never fork the format (see CLAUDE.md).

A match.json is:

{
  "schema_version": "1.0",
  "video":   {filename, fps, width, height, duration_s},
  "court":   {length_m, width_m},              # mirrors court.py
  "players": [{id, name}, ...],
  "shots":   [Shot, ...],
  "rallies": [Rally, ...],
  "score":   {sets: [...], games: [...], final, timeline: [...]},
  "stats":   {shot_count, rally_count, avg_speed_kmh, top_speed_kmh,
              shot_mix: {...}, line_calls: {in, out}}
}

Positions are court-plane metres [x, y]; speeds km/h; times seconds.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from . import court

SCHEMA_VERSION = "1.0"

# Shot type vocabulary used across backend + frontend.
SHOT_TYPES = ("serve", "forehand", "backhand", "volley", "overhead")


@dataclass
class Video:
    filename: str
    fps: float
    width: int
    height: int
    duration_s: float


@dataclass
class Player:
    id: str
    name: str


@dataclass
class Shot:
    id: int
    rally_id: int
    player: str          # player id
    type: str            # one of SHOT_TYPES
    t_hit_s: float       # time the ball was struck
    speed_kmh: float     # average ball speed of this shot
    hit_xy: list[float]  # where it was struck (court metres)
    bounce_xy: list[float]  # where it bounced (court metres)
    bounce_t_s: float    # time of the bounce
    is_in: bool          # did the bounce land in?
    call: str            # "in" | "out" (line call)
    # Physics-based readouts (ball_physics, bounce-anchored). 0 when unavailable.
    spin_rpm: float = 0.0        # total spin magnitude
    topspin_rpm: float = 0.0     # signed: + topspin, - backspin
    # Stroke style from the racket-hand swing path (events.classify_spin):
    # "topspin" | "slice" | "flat" | "" (undetermined). Physics topspin_rpm
    # overrides the pose heuristic when a reliable arc fit exists.
    spin_style: str = ""
    speed_source: str = "approx"  # "physics" (bounce-anchored fit) | "approx"
    # Confidence under perspective amplification (far court grazes the horizon, so a
    # few pixels of ball jitter become decimetres). False => far-court reading the
    # single camera can't pin down; excluded from the headline speed stats.
    speed_confident: bool = True
    call_confident: bool = True


@dataclass
class TrackPoint:
    t_s: float
    xy: list[float]      # ball position in court metres


@dataclass
class Rally:
    id: int
    start_s: float
    end_s: float
    shot_ids: list[int]
    winner: str          # player id
    ball_track: list[TrackPoint] = field(default_factory=list)


@dataclass
class ScoreEvent:
    shot_id: int
    rally_id: int
    point_winner: str
    display: str         # e.g. "30-15", "Deuce", "Game A"
    games_display: str   # e.g. "2-1"
    sets_display: str    # e.g. "1-0"


@dataclass
class Score:
    final: str
    sets: list[list[int]]            # [[a_games, b_games], ...] per completed set
    games: list[int]                 # current games in the in-progress set [a, b]
    timeline: list[ScoreEvent] = field(default_factory=list)


@dataclass
class Stats:
    shot_count: int
    rally_count: int
    avg_speed_kmh: float
    top_speed_kmh: float
    shot_mix: dict[str, int]
    line_calls: dict[str, int]       # {"in": n, "out": m}
    # Metres each player ran (court-plane path length), {"A": near, "B": far}. The
    # far player's value is approximate (perspective amplifies its position jitter).
    distance_run_m: dict[str, float] = field(default_factory=dict)


@dataclass
class Match:
    video: Video
    players: list[Player]
    shots: list[Shot]
    rallies: list[Rally]
    score: Score
    stats: Stats
    schema_version: str = SCHEMA_VERSION
    court: dict[str, float] = field(
        default_factory=lambda: {
            "length_m": court.LENGTH,
            "width_m": court.DOUBLES_WIDTH,
            "singles_width_m": court.SINGLES_WIDTH,
            "service_line_from_net_m": court.SERVICE_LINE_FROM_NET,
        }
    )
    # How the court was calibrated: {"corners": {landmark: [x_px, y_px]},
    # "source": ..., "hfov_deg": ..., "lens_k1": division-model radial
    # distortion (0.0 = none), "events": [{"frame", "kind"}]}. Optional -
    # demo matches have no camera. The dashboard's Court Setup seeds from it.
    calibration: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Plain dict ready for json.dump."""
        return asdict(self)


def compute_stats(shots: list[Shot], rallies: list[Rally]) -> Stats:
    """Derive the summary stats block from shots + rallies. Deterministic; the
    dashboard renders these directly."""
    # Headline avg/top speed use ONLY confidently-projected shots — a far-court
    # reading is perspective-amplified noise, so we report 0 ("—" in the UI) rather
    # than surface it as a measured number. (Demo shots default speed_confident=True.)
    speeds = [s.speed_kmh for s in shots if s.speed_kmh > 0 and getattr(s, "speed_confident", True)]
    shot_mix: dict[str, int] = {}
    for s in shots:
        shot_mix[s.type] = shot_mix.get(s.type, 0) + 1
    line_calls = {
        "in": sum(1 for s in shots if s.call == "in"),
        "out": sum(1 for s in shots if s.call == "out"),
    }
    return Stats(
        shot_count=len(shots),
        rally_count=len(rallies),
        avg_speed_kmh=round(sum(speeds) / len(speeds), 1) if speeds else 0.0,
        top_speed_kmh=round(max(speeds), 1) if speeds else 0.0,
        shot_mix=shot_mix,
        line_calls=line_calls,
    )


def validate(data: dict[str, Any]) -> list[str]:
    """Lightweight structural check. Returns a list of problems (empty == ok).
    Not a full JSON-schema validator — just guards the contract's invariants so
    a malformed match.json fails loudly instead of silently in the frontend."""
    problems: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(
            f"schema_version {data.get('schema_version')!r} != {SCHEMA_VERSION!r}"
        )
    for key in ("video", "players", "shots", "rallies", "score", "stats", "court"):
        if key not in data:
            problems.append(f"missing top-level key {key!r}")

    rally_ids = {r["id"] for r in data.get("rallies", [])}
    player_ids = {p["id"] for p in data.get("players", [])}
    for s in data.get("shots", []):
        if s.get("type") not in SHOT_TYPES:
            problems.append(f"shot {s.get('id')}: unknown type {s.get('type')!r}")
        if s.get("rally_id") not in rally_ids:
            problems.append(f"shot {s.get('id')}: rally_id not found")
        if s.get("player") not in player_ids:
            problems.append(f"shot {s.get('id')}: player not found")
        if s.get("call") not in ("in", "out"):
            problems.append(f"shot {s.get('id')}: call must be 'in' or 'out'")
    return problems
