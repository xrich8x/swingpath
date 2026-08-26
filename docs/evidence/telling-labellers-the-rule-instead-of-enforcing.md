# Telling labellers the rule instead of enforcing it

> Evidence for the `telling-labellers-the-rule-instead-of-enforcing` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**MEASURED NEGATIVE, and it is the reason the far-court queue is now blocked on SELECTION rather than effort.** Session J ended by adding *"a ball in play is somewhere different on every frame"* as the lead rule on the labelling page. The commit landed at 21:20; `farcourt_cal1` was labelled at 21:50 — the first round under it — and is **WORSE than the round before** (47% vs 60% of gaps yielding ball-like click motion). **17 of its 49 gaps have the human clicking the IDENTICAL pixel on both frames**, which a ball in play cannot do. The pre-registered L2 gate (>=60%) FAILS at 47%, so the 4-5 hour labelling push does not run. A written instruction on the page is not a control — the test is now enforced mechanically in the converter (`MIN_MOTION_PX`), which only became defensible once the Session J threshold reproduced on these 49 independent gaps (bimodal, valley at 9-16 px). Evidence: data/output/farcourt_l2.md
