# Session B — Serve analytics + expanded match stats

**Kickoff prompt:** `Do Session B (docs/sessions/SESSION_B_serve_stats.md)`
**User brings:** nothing. (Any analyzed clip with serves benefits the demo.)

## Goal
First new user-visible feature since the court milestone: serve placement and
serve/rally statistics in the dashboard, computed from data match.json already
carries (shots with `bounce_xy`, `type == "serve"`, rallies).

## Researched definitions (use the standard tennis vocabulary, not invented zones)
Serve placement is classified per service box into three bands, judged by where
the serve BOUNCES relative to the box:
- **T** — a narrow band along the centre service line (standard coaching target
  ≈ one racquet-length wide, ~0.7 m from the centre line).
- **Wide** — the mirror band along the singles sideline (~0.7 m).
- **Body** — everything between (the remaining ~2.6 m of the 4.115 m-wide box).
Always crossed with the serving side: **deuce** vs **ad** court (which box the
bounce is in). Pro reference rates for sanity-checking output: ~25-30% T,
~25% wide — if our numbers are wildly different on real footage, suspect the
bounce data, not the definitions.

First vs second serve CANNOT be read from one bounce alone — it is point-state:
a serve bounce that lands OUT/at-net followed by another serve from the same
side without an intervening rally = fault → the next serve is a second serve.
Derive from the rally/score state machine (scoring.py + events); where the
state is ambiguous (mid-clip starts), label serves "unknown" honestly rather
than guessing.

Sources:
- [Tennis serve placement zones: T, wide, body (Ten-Fifty5)](https://www.ten-fifty5.com/post/tennis-serve-placement-zones-how-to-read-and-win-from-the-t-wide-and-body)
- [Serve target geometry (7 Shot Tennis)](https://www.7shottennis.com/tennis-court-visualization/tennis-serve-targets/)
- [Serve statistics conventions (Tennis Abstract / Heavy Topspin)](https://www.tennisabstract.com/blog/category/serve-statistics/)
- [Quantifying serve effectiveness (Wharton working paper)](https://wsb.wharton.upenn.edu/wp-content/uploads/2025/12/WIEAND-serve_performance.pdf)

## Plan
1. `analytics.serve_placement(bounce_xy, serving_side)` → (deuce|ad, T|body|wide)
   from court metres (court.py constants; the 0.7 m band widths as module
   constants with the source cited). Pure geometry — unit tests with hand-picked
   court coordinates on every band edge.
2. `schema.compute_stats` additions: serve placement counts per player/side,
   1st/2nd serve % (or "unknown"), rally-length histogram buckets (1-3, 4-6,
   7-9, 10+ — Tennis Abstract convention), per-player shot-type mix.
   Schema stays additive (don't fork the format — CLAUDE.md rule).
3. Statistics.jsx: serve-placement mini-court graphic (6 zones × count), serve %
   panel, rally-length bars. Reuse existing court-drawing lib + dataviz idioms.
4. Verify by hand: pick one analyzed clip, list its serves + bounces in a table,
   check each classification manually. Demo data (synthetic) must also render.
5. Commit + push; screenshot/proof for the user.

## Definition of done
- New panels render for BOTH demo and analyzed matches
- Every serve in the verification clip hand-checked against its zone
- Unit tests for zone edges + stats math; all tests pass; pushed

## Guardrails
- Report "unknown" over guessing (1st/2nd serve state, low-confidence bounces —
  `call_confident`/`speed_confident` flags already exist; respect them).
- Sparse-ball clips (worn clay) will have few serves — that's honest, not a bug.

## Results (fill in during the session)
- _pending_
