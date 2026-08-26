# Rally segmentation / score — CLOSED BY DECISION 2026-08-20, not a work item

> Evidence for the `rally-segmentation-score` row in [docs/STATE.md](../../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**The user ruled this layer out of scope: it is not important and will not be worked on in any session.** It is therefore removed from the queue rather than left as an open problem. Nothing here is waiting on anything and nothing should be spent on it — not the `gap_s` override, not the second-bounce rule, not a ground-truth source for points. **Do not re-open it, and do not re-derive its diagnosis:** the burned-in-scoreboard route was already built, rejected on its premise and reverted (`afffb5a`), and that row stays in the dead-end table precisely so this cannot come back a third time. What already SHIPS keeps working and needs no further attention: `scoring.py` runs the state machine, the corrections replay uses it, and `stats.score_validation_note` labels the output unvalidated in the UI. Leave all of that alone.
