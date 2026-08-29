---
name: founder-rulings-2026-08-29
description: Founder decisions of 2026-08-29 — TrackNet ships in v1, line calling parked, P0-3 accepted, a TrackNet idea withheld — plus the new surprising-result-goes-to-researcher-first process rule
metadata:
  type: project
---

Four binding rulings and one process rule, all dated 2026-08-29.

**1. v1 ships TrackNet.** The chain test was SPLIT, so this was a product call, not a
measurement: TrackNet's failure mode (fewer phantom balls, −8 real hits) was preferred
over BallNet v21's, and TrackNet is the only detector with a Core ML path today. BallNet
v21 remains the upgrade path and its Core ML conversion is a scoped line item, not a
footnote.

**2. Line calling is PARKED and the refusal band is NOT chosen.** The 0.15 m / 0.20 m
choice is open and belongs to the founder, not a measurement. `live.py`'s shipped
`line_margin_m = 0.05` sits inside the unreliable zone and is UNCHANGED. See
[[line-call-numbers-assume-perfect-bounce]].
*Consequence to state whenever it comes up:* anything justified by improving line-call
accuracy — far-court recall labelling above all — is improving a parked feature, and
loses to work on a shipping requirement.

**3. P0-3's substituted identity test is ACCEPTED.** The pre-registered test routed
through `yt_match40`'s broken homography and was unexecutable; backend-dev substituted a
calibration-free person-specific test and flagged the swap rather than making it quietly.
*The precedent worth keeping:* declaring a substitution gets it accepted; making it
silently would not have.

**4. The founder holds a TrackNet improvement idea, not yet shared.** Ball-chain work does
not start until it lands, because it may redirect that lane.
**Why this matters more than it looks:** the best-measured open target in the repo (speed
coverage, which names its two costly stages) is CHAIN work, and rule 6 closes only
DETECTOR work. If the withheld idea is detector-side, the chain lane can start
immediately. **Always ask which side it touches before accepting the whole lane as
parked** — the answer unparks the strongest item on the board.

**Process rule (new, now in CLAUDE.md): a surprising result goes to `researcher` FIRST,
then to pm.** pm sequences around a finished investigation and is explicitly not asked to
re-do it. **How to apply:** when handed a researcher verdict, interrogate its confidence
and its cost, and spend your judgement on the trade-off researcher deliberately left open
— that is the part that is yours.
