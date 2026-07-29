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

from . import analytics, court

SCHEMA_VERSION = "1.0"

# Typical |error| of an UNCONFIDENT ("approx") shot speed, per cent. Measured with
# tools/speed_band.py against the SwingVision HUD on yt_rally2: 10 matched
# groundstrokes, median |err| 19.2%, MAE 27.8%, bias -15.5%.
#
# Two things this number is not. It is not a guarantee — n=10 on ONE clip, and the
# HUD is itself a single-camera estimate, not radar. And the negative bias is NOT a
# calibration error to be corrected away: ours is the AVERAGE ball speed over the
# flight while a racquet-speed readout is the launch speed, and CLAUDE.md has
# recorded that ~15-20% gap as expected physics since before this was measured.
# "Fixing" it to match the HUD would be fitting to a number we do not trust.
SPEED_ESTIMATE_ERR_PCT = 25.0

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
    line_calls: dict[str, int]       # {"in": n, "out": m, "uncertain": k}
                                     # in/out = confident calls only; uncertain =
                                     # far-court bounces too perspective-amplified
                                     # to judge (see compute_stats)
    # True when avg/top speed fall back to unconfident ESTIMATES because no shot met
    # the strict bar — the normal case on an amateur-height camera. The UI must
    # label these as estimates, not present them as measurements.
    speed_estimated: bool = False
    # Typical |error| of an estimated speed, per cent, measured against the
    # SwingVision HUD (tools/speed_band.py). Calibration is thin — 10 groundstrokes
    # on ONE clip — so it is a band, not a guarantee.
    speed_err_pct: float = 0.0
    # Metres each player ran (court-plane path length), {"A": near, "B": far}. The
    # far player's value is approximate (perspective amplifies its position jitter).
    distance_run_m: dict[str, float] = field(default_factory=dict)
    # --- Serve + rally analytics (additive; older match.json simply omit these) --
    # Serve placement counts per server, by court side and lateral band. Only serves
    # that landed IN (and whose call we trust) are placed — a fault has no zone.
    #   {"A": {"deuce": {"T":n,"body":n,"wide":n}, "ad": {...}, "total": n}, "B": {...}}
    serve_placement: dict[str, Any] = field(default_factory=dict)
    # First vs second serve, derived from the point/fault sequence (see
    # derive_serve_order). "unknown" where the state can't be trusted.
    #   {"A": {"first_total","first_in","second_total","second_in","unknown"}, "B": {...}}
    serve_split: dict[str, Any] = field(default_factory=dict)
    # Rally-length histogram by shots-per-rally (Tennis Abstract buckets).
    rally_length_buckets: dict[str, int] = field(default_factory=dict)
    # Per-player shot-type mix, {"A": {"serve":n, "forehand":n, ...}, "B": {...}}.
    shot_mix_by_player: dict[str, dict[str, int]] = field(default_factory=dict)


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


# Rally-length buckets (shots per rally). Tennis Abstract convention.
RALLY_BUCKETS = ("1-3", "4-6", "7-9", "10+")


def _rally_bucket(n_shots: int) -> str:
    if n_shots <= 3:
        return "1-3"
    if n_shots <= 6:
        return "4-6"
    if n_shots <= 9:
        return "7-9"
    return "10+"


def _server_end(player: str) -> str:
    """Which baseline a server stands behind. Player A is always the near-half
    player (pipeline assigns 'A' to y < NET_Y), B the far player."""
    return "near" if player == "A" else "far"


def derive_serve_order(shots: list[Shot]) -> dict[int, str]:
    """Map each serve's shot id -> "first" | "second" | "unknown" (the logic layer).

    First vs second serve can't be read from one bounce — it's point state. A
    serve is a SECOND serve iff the previous serve, by the same player, was a fault
    (landed out) with no rally play in between. A groundstroke between two serves
    means a new point started, so the next serve is a first serve; a second serve
    (whether in or a double fault) always resets the next serve to first.

    Where a serve's line call isn't trustworthy (call_confident is False) we can't
    tell whether it faulted, so that serve — and the fault state it would set — is
    reported "unknown" rather than guessed. Shots are consumed in id/time order.
    """
    order: dict[int, str] = {}
    fault_pending_for: Optional[str] = None  # player whose last (first) serve faulted
    for s in sorted(shots, key=lambda sh: sh.id):
        if s.type != "serve":
            fault_pending_for = None  # rally play => the next serve begins a new point
            continue
        if not getattr(s, "call_confident", True):
            order[s.id] = "unknown"
            fault_pending_for = None  # unsure it faulted: don't propagate a guess
            continue
        if fault_pending_for == s.player:
            order[s.id] = "second"
            fault_pending_for = None  # point is decided after the second serve
        else:
            order[s.id] = "first"
            fault_pending_for = s.player if s.call == "out" else None
    return order


def compute_stats(shots: list[Shot], rallies: list[Rally]) -> Stats:
    """Derive the summary stats block from shots + rallies. Deterministic; the
    dashboard renders these directly."""
    # Headline avg/top speed prefer confidently-measured shots. When NONE are
    # confident we now fall back to the estimates rather than reporting 0.0.
    # Reporting 0.0 was indistinguishable from a broken pipeline, and it was the
    # normal case: on a low camera the strict bar is rarely met, yet the estimates
    # measure ~19% median error against the SwingVision HUD (tools/speed_band.py) —
    # as good as anything this project has recorded. `speed_estimated` tells the UI
    # to label the number as an estimate rather than present it as measured.
    # Serves are excluded from the fallback: their speed is a different quantity
    # (measured -57% vs the HUD) and the pipeline never marks them confident.
    speeds = [s.speed_kmh for s in shots if s.speed_kmh > 0 and getattr(s, "speed_confident", True)]
    speed_estimated = False
    if not speeds:
        speeds = [s.speed_kmh for s in shots
                  if s.speed_kmh > 0 and s.type != "serve"]
        speed_estimated = bool(speeds)
    shot_mix: dict[str, int] = {}
    for s in shots:
        shot_mix[s.type] = shot_mix.get(s.type, 0) + 1
    # Headline in/out count ONLY confident calls: a far-court bounce grazing the
    # horizon is perspective-amplified noise (the low-camera reality), so an
    # in/out verdict there isn't trustworthy. Such calls go to `uncertain` rather
    # than inflating the score line — the Court view still plots them, drawn
    # hollow. (Demo shots default call_confident=True, so uncertain == 0.)
    line_calls = {
        "in": sum(1 for s in shots if s.call == "in" and getattr(s, "call_confident", True)),
        "out": sum(1 for s in shots if s.call == "out" and getattr(s, "call_confident", True)),
        "uncertain": sum(1 for s in shots if not getattr(s, "call_confident", True)),
    }

    # Per-player shot-type mix.
    shot_mix_by_player: dict[str, dict[str, int]] = {}
    for s in shots:
        m = shot_mix_by_player.setdefault(s.player, {})
        m[s.type] = m.get(s.type, 0) + 1

    # Serve placement + first/second split. Placement counts only IN serves with a
    # trusted call (a fault has no meaningful zone); the split uses every serve.
    serve_order = derive_serve_order(shots)
    serve_placement: dict[str, Any] = {}
    serve_split: dict[str, Any] = {}
    for s in shots:
        if s.type != "serve":
            continue
        pl = serve_placement.setdefault(
            s.player,
            {"deuce": {"T": 0, "body": 0, "wide": 0},
             "ad": {"T": 0, "body": 0, "wide": 0}, "total": 0},
        )
        if s.is_in and getattr(s, "call_confident", True):
            side, band = analytics.serve_placement(s.bounce_xy, _server_end(s.player))
            pl[side][band] += 1
            pl["total"] += 1
        sp = serve_split.setdefault(
            s.player,
            {"first_total": 0, "first_in": 0, "second_total": 0,
             "second_in": 0, "unknown": 0},
        )
        which = serve_order.get(s.id, "unknown")
        if which == "first":
            sp["first_total"] += 1
            sp["first_in"] += int(s.is_in)
        elif which == "second":
            sp["second_total"] += 1
            sp["second_in"] += int(s.is_in)
        else:
            sp["unknown"] += 1

    rally_length_buckets = {b: 0 for b in RALLY_BUCKETS}
    for r in rallies:
        rally_length_buckets[_rally_bucket(len(r.shot_ids))] += 1

    return Stats(
        shot_count=len(shots),
        rally_count=len(rallies),
        speed_estimated=speed_estimated,
        speed_err_pct=SPEED_ESTIMATE_ERR_PCT if speed_estimated else 0.0,
        avg_speed_kmh=round(sum(speeds) / len(speeds), 1) if speeds else 0.0,
        top_speed_kmh=round(max(speeds), 1) if speeds else 0.0,
        shot_mix=shot_mix,
        line_calls=line_calls,
        serve_placement=serve_placement,
        serve_split=serve_split,
        rally_length_buckets=rally_length_buckets,
        shot_mix_by_player=shot_mix_by_player,
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
