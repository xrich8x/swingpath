"""`span_sink` — the observability hook the per-stage speed-coverage probe uses.

`seen_frac = real_fraction(hit, landing)` is the number that gates a reported
speed, and it is computed inside `_build_match_from_events` as a closure over
`ball_seen`. `tools/eval_speed_coverage_chain.py` reads it out through
`span_sink` rather than re-deriving the span logic outside the function, because
a re-derived ladder is how an attribution table stops describing the shipped
pipeline (trap T15).

Three things are pinned here:
  1. the hook is INERT — passing a sink cannot change a single emitted value;
  2. it reports the same `seen_frac` the confidence test used, not a lookalike;
  3. changing `ball_seen` moves `seen_frac` WITHOUT moving the shot population,
     which is the assumption the whole per-stage table rests on (every row must
     score the same shots or the deltas mean nothing).
"""
from __future__ import annotations

import pytest

from swingvision import court, pipeline

N = 60
FPS = 30.0


def _fixture(seen):
    """A two-contact synthetic rally: serve at 0 landing at 30, reply at 50."""
    track = [(i / FPS, court.DOUBLES_WIDTH / 2,
              2.0 + (court.LENGTH - 4.0) * (i / (N - 1))) for i in range(N)]
    near = [(court.DOUBLES_WIDTH / 2, 1.0)] * N
    far = [(court.DOUBLES_WIDTH / 2, court.LENGTH - 1.0)] * N
    return dict(track=track, hit_idx=[0, 50], bounce_idx=[30],
                near_court=near, far_court=far, ball_seen=list(seen))


def _run(seen, sink=None):
    f = _fixture(seen)
    return pipeline._build_match_from_events(
        f["track"], f["hit_idx"], f["bounce_idx"], f["near_court"],
        f["far_court"], FPS, 1280, 720, "synthetic.mp4",
        ball_seen=f["ball_seen"], span_sink=sink)


def test_span_sink_is_inert():
    """Default None vs a live sink must emit a byte-identical match."""
    seen = [True] * N
    without = _run(seen).to_dict()
    with_sink = _run(seen, sink=[]).to_dict()
    assert without == with_sink


def test_span_sink_reports_the_span_the_confidence_test_used():
    seen = [True] * N
    sink = []
    match = _run(seen, sink=sink)
    assert len(sink) == len(match.shots)
    # Spans are hit -> landing, and the landing of the first shot is the bounce.
    assert sink[0]["h"] == 0 and sink[0]["land"] == 30
    assert sink[0]["seen_frac"] == pytest.approx(1.0)
    # `speed_confident` in the sink is the value the emitted shot carries, not a
    # recomputation: a serve is never speed-confident however well it was seen.
    assert sink[0]["is_serve"] is True
    assert sink[0]["speed_confident"] is False
    assert sink[1]["speed_confident"] is True


def test_blanking_half_a_span_halves_seen_frac_and_keeps_the_population():
    """The per-stage table hands the SAME spans a different `ball_seen` mask.

    That is only a valid attribution if the shot list does not move with the
    mask — otherwise consecutive rows describe different shots.
    """
    full = []
    _run([True] * N, sink=full)

    half = [True] * N
    for i in range(0, 16):          # blank the first half of the serve's span
        half[i] = False
    part = []
    _run(half, sink=part)

    assert len(part) == len(full)                       # population unmoved
    assert [(s["h"], s["land"]) for s in part] == \
           [(s["h"], s["land"]) for s in full]          # spans unmoved
    # 16 of the 31 frames in [0, 30] are now unseen.
    assert part[0]["seen_frac"] == pytest.approx(15 / 31.0)
    assert part[0]["seen_frac"] < full[0]["seen_frac"]
    # A span nowhere near the blanked frames is untouched.
    assert part[1]["seen_frac"] == pytest.approx(full[1]["seen_frac"])


def test_coasted_frames_do_not_count_as_seen():
    """A drawn-but-forecast frame is a physics guess, not a measurement.

    This is the whole reason `smooth_forecast` can raise per-frame recall (which
    counts an interpolated position within 10 px of a human click as a hit) and
    lower speed coverage at the same time.
    """
    seen_all = []
    _run([True] * N, sink=seen_all)
    # ball_seen already excludes coasted frames upstream, so the equivalent here
    # is simply marking those frames unseen — coverage must fall, never hold.
    coasted = [True] * N
    for i in range(51, 60):
        coasted[i] = False
    partial = []
    _run(coasted, sink=partial)
    assert partial[1]["seen_frac"] < seen_all[1]["seen_frac"]
