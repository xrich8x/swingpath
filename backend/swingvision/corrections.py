"""corrections.py — let a human overrule the analyzer, and re-derive everything.

WHY THIS EXISTS
---------------
README's honest limitations have said from the start: "Scoring from vision alone
is brittle (the real app gets points wrong too); a manual-correction UI is a known
gap." This is the backend half of closing it.

The brittleness is structural, not a bug to detect harder. A rally winner is
inferred from a bounce that a single camera cannot always place, so some points
WILL be wrong, and no amount of model work removes that. The fix is to let the
person who watched the match say so — and then to recompute honestly rather than
patching one number.

WHAT A CORRECTION IS
--------------------
A small, auditable record: what was changed, on which object, from what to what.

    {"target": "rally.winner", "id": 3, "value": "B", "original": "A"}
    {"target": "shot.call",    "id": 7, "value": "out", "original": "in"}
    {"target": "shot.type",    "id": 7, "value": "backhand", "original": "forehand"}

`original` is carried so a correction is reversible and reviewable, and so a
corrections file applied to the WRONG match.json is detectable rather than silent.

THE RULE THIS FOLLOWS
---------------------
Corrections change FACTS, never derived values. Change a rally winner and the
score is REPLAYED through scoring.TennisScore; change a line call and the stats
are re-derived by schema.compute_stats. Nothing here re-implements scoring or
statistics — that would be a second source of truth, and the two would drift.
Geometry and logic stay where they are; this module only edits inputs and asks
the existing code for the answer again.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from . import scoring

#: Every correctable field. Anything else is refused — a typo in a target should
#: fail loudly, not silently do nothing.
TARGETS = ("rally.winner", "shot.call", "shot.type")


@dataclass
class CorrectionResult:
    applied: list[dict]
    skipped: list[dict]        # with a `reason`, so nothing disappears quietly

    @property
    def ok(self) -> bool:
        return not self.skipped


def _index(items: list[dict], key: str = "id") -> dict:
    return {it[key]: it for it in items if key in it}


def apply_corrections(match: dict, corrections: list[dict], *,
                      strict: bool = False) -> tuple[dict, CorrectionResult]:
    """Apply human corrections to a match dict and re-derive everything downstream.

    Returns (corrected_match, result). The input is not mutated.

    `strict` raises on any skipped correction instead of collecting it — use it in
    tests and CI, leave it off in the UI where a stale corrections file should
    report rather than abort.
    """
    import copy

    out = copy.deepcopy(match)
    shots = _index(out.get("shots", []))
    rallies = _index(out.get("rallies", []))
    applied: list[dict] = []
    skipped: list[dict] = []

    def skip(c, reason):
        rec = dict(c)
        rec["reason"] = reason
        skipped.append(rec)
        if strict:
            raise ValueError(f"correction refused: {reason}: {c}")

    for c in corrections:
        target, cid, value = c.get("target"), c.get("id"), c.get("value")
        if target not in TARGETS:
            skip(c, f"unknown target (expected one of {', '.join(TARGETS)})")
            continue
        obj = rallies.get(cid) if target.startswith("rally.") else shots.get(cid)
        if obj is None:
            skip(c, f"no {target.split('.')[0]} with id {cid} in this match.json")
            continue
        field = target.split(".", 1)[1]
        current = obj.get(field)
        # A corrections file carrying the wrong `original` is being applied to a
        # different analysis than it was written against. Refuse it: silently
        # "correcting" an already-different value is how two people end up with
        # the same file and different scores.
        if "original" in c and c["original"] != current and current != value:
            skip(c, f"stale: expected {field}={c['original']!r}, found {current!r}")
            continue
        if current == value:
            continue                       # idempotent: already says this
        obj[field] = value
        applied.append({**c, "was": current})

    if applied:
        _rederive(out)
    return out, CorrectionResult(applied=applied, skipped=skipped)


def _rederive(match: dict) -> None:
    """Replay score and recompute stats from the (now corrected) facts.

    Both are asked of the SAME code the pipeline uses. If this file ever grows a
    second implementation of tennis scoring, delete it.
    """
    rallies = match.get("rallies", [])
    shots = match.get("shots", [])

    # --- score: replay the state machine over the rally winners, in order ---
    players = [p.get("id") for p in match.get("players", [])][:2] or ["A", "B"]
    engine = scoring.TennisScore(player_a=players[0], player_b=players[1])
    timeline = []
    for r in sorted(rallies, key=lambda x: x.get("id", 0)):
        winner = r.get("winner")
        if winner not in players:
            continue
        res = engine.point(winner)
        sid = (r.get("shot_ids") or [None])[-1]
        timeline.append({
            "shot_id": sid, "rally_id": r.get("id"), "point_winner": winner,
            "display": res.display, "games_display": res.games_display,
            "sets_display": res.sets_display,
        })
    match["score"] = {
        "final": engine.final_str(),
        "sets": [list(s) for s in engine.completed_sets],
        "games": list(engine.games),
        "timeline": timeline,
    }

    # --- stats: hand the corrected shots/rallies back to the one implementation ---
    match["stats"] = _stats_from_dicts(shots, rallies, match.get("stats", {}))


def _stats_from_dicts(shots: list[dict], rallies: list[dict],
                      previous: dict) -> dict:
    """Re-derive the stats block via schema.compute_stats.

    schema.compute_stats takes dataclasses, and match.json holds dicts, so the
    rows are rehydrated first. Fields compute_stats does not own (serve
    placement, distance run — they need the ball track and pose, which a
    correction cannot change) are carried over from `previous` untouched.
    """
    from . import schema

    def mk(cls, d):
        keep = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in keep})

    s_objs = [mk(schema.Shot, s) for s in shots]
    r_objs = [mk(schema.Rally, r) for r in rallies]
    fresh = schema.compute_stats(s_objs, r_objs)
    out = fresh.__dict__.copy() if hasattr(fresh, "__dict__") else dict(fresh)

    # Carry forward what compute_stats does not derive from shots+rallies alone.
    # `player_track_coverage` travels WITH `distance_run_m` — it is the
    # denominator that explains why a distance may be None, so dropping it on a
    # correction replay would leave an unexplained "not tracked" in the UI.
    for k in ("serve_placement", "serve_split", "distance_run_m",
              "player_track_coverage", "distance_run_note",
              "rally_length_buckets", "shot_mix_by_player"):
        if k in previous and not out.get(k):
            out[k] = previous[k]
    return out


def diff_summary(before: dict, after: dict) -> dict:
    """What the corrections actually changed, for the user and for the log."""
    b, a = before.get("score", {}), after.get("score", {})
    bs, as_ = before.get("stats", {}), after.get("stats", {})
    return {
        "final_before": b.get("final"), "final_after": a.get("final"),
        "score_changed": b.get("final") != a.get("final"),
        "line_calls_before": bs.get("line_calls"),
        "line_calls_after": as_.get("line_calls"),
        "shot_mix_before": bs.get("shot_mix"),
        "shot_mix_after": as_.get("shot_mix"),
    }
