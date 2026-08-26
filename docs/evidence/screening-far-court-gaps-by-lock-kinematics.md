# Screening far-court gaps by lock kinematics

> Evidence for the `screening-far-court-gaps-by-lock-kinematics` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Two measured negatives, and they are why the anchor control is label-time rather than selection-time.** Local roam (`inspect_false_locks.describe`, ±8 frames) over the 12 pilot gaps: confirmed anchors **14.0–220.2 px**, unconfirmed **13.2–238.8 px** — fully overlapping at both ends, because a genuine far ball's per-frame excursion is small. And `ball.suppress_false_locks` requiring both anchors to survive keeps **1 of 5** confirmed gaps: the min-segment test needs a run of consecutive locks and the frame after a gap starts a new short segment by construction, so anchor `b` is dropped on 8 of 12 gaps as an artefact of *being* an anchor.
