# Manual-correction UI (Review tab + run.py correct)

> Evidence for the `manual-correction-ui` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

closes the oldest known gap. Edits FACTS only; score is replayed through `scoring.TennisScore` and stats through `schema.compute_stats`, so there is no second implementation of the rules. Verified end to end: demo score 2-5 → 3-4, line calls 108/17 → 107/18, and re-applying the same file is a no-op | 2026-08-06
