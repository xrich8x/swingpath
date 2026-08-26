# Whether the +5.6 pt recall gain reaches the product — ANSWERED: it does not

> Evidence for the `whether-the-5-6-pt-recall-gain` row in [docs/STATE.md](../../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

Chain test run 2026-08-13 on all three calibrated clips (data/output/chain_ab.md). **GATE FAILS: pooled solid ghosts 9 -> 13**, chain recall **exactly flat** against the shipped baseline stated in the **Making the smoother respect suppression** row. `ballnet_v21.pt` stays the default; arm B is NOT shipped. v21's 9 reproduces the standing figure exactly, checking the measurement chain. The clip that collapses is **am_hard_utr, the 1.74 m 1080p amateur mount this project targets: 1 -> 7 solid ghosts**. Caveats the tool flags: the clips disagree in sign (+6/+1/-3) and only 4 of 18 ghost frames overlap, so this is "arm B did not clear the bar", not "more data makes ghosting worse".
