---
name: top2-margin-is-a-risk-gate-not-a-detector
description: The top-2 area*peak margin passes its pre-registered refusal bar on fp32 (5/5 at 2.1% collateral, nulls all p~0) but FAILS on int8 and has zero dropout signal; inside the close-race set it predicts nothing
metadata:
  type: project
---

Measured 2026-09-04 on the committed six-clip parity set (528 both-fire frames, 5 failures).
Full detail: `docs/evidence/top2-margin-refusal-signal.md`.

`margin = 1 - score_2/score_1` over the decode's own connected components (`area x peak`).

**PASS on fp32, as a screen.** `t = 0.10` catches 5/5 known >10 px failures at 11/523 =
2.1% collateral; the whole band `[0.077, 0.30]` passes identically, so the threshold is not
load-bearing. Nulls all separate: free permutation 0.0000 (exact hypergeometric 1.3e-08),
selection-adjusted 0.0000, cluster-preserving within-clip circular shift 0.0010 at
catch>=4. n=5 was NOT the limiting factor — low margins are rare (37/528 frames have a
second blob at all), which is what makes a random 5 landing inside 16-of-528 improbable.

**Three things that must travel with the pass:**

1. **FAILS on the int8 heatmap** — no threshold reaches 4/5. On frames int8 gets wrong,
   int8's OWN margin is wide (0.86, and 1.0000 = single blob). Quantisation *resolved* the
   race by eroding the true winner out of existence rather than leaving a close one. So
   the signal is computable only on the fp32 graph, never from the int8 graph's output.
2. **Zero dropout signal.** On the 27 null mismatches (fp32 fires, int8 does not) the fp32
   margin is median 1.0000, min 0.4421, 0% below 0.15. A dropout frame never had a
   runner-up, so a top-2 statistic cannot see it. Dropout needs a different signal —
   plausibly the winner's absolute `area x peak`, untested.
3. **It is a RISK gate, not a failure detector.** The 11 refused correct frames decode
   *perfectly* (max 0.318 px, three at exactly 0.000). At identical margin — including an
   exact 0.0000 tie — the decode is right 3 times in 4. Refusal precision 5/16 = 31%.
   The margin identifies the population at risk; it has no view on which member flips.

**Why:** the lead pre-registered this after the activation diff (`2110964`) refuted the
precision-boundary premise; the failure signature is a confident wrong lock with no
refusal signal, and the ~5% fp32 top-2 margin means the fp32 path is exposed too.

**How to apply:** do not describe this as failure detection or quote a catch rate as
accuracy. If it is ever proposed for a wider run, the question that decides it is a
*product* one — what happens downstream to a refused frame — not another measurement.
See [[ball-detector-choice-is-split]], [[int8-per-channel-is-a-noop-for-conv]],
[[null-controls-and-pre-registered-populations]].
