---
name: top2-margin-is-a-risk-gate-not-a-detector
description: The top-2 area*peak margin passes its refusal bar on fp32 (5/5, 2.1% collateral) AND on int8 once the grid is widened past 0.30 (4/5, 3.8%); both are risk gates at 14-31% precision, neither sees dropout
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

1. **int8 CAN police itself — the earlier "FAILS on int8" was a GRID artefact, corrected
   2026-09-04 in the same day's second run.** The int8 sweep reused the fp32 grid, which
   stops at `t = 0.30`; one bad frame's int8 margin is 0.86 and sat above it. Widened:
   `margin_int8 <= 0.90` catches **4/5 at 3.82%** collateral (precision 16.7%), and the
   equivalent int8-only rule **`blob_count >= 2`** catches 4/5 at 4.78% (precision 13.8%) —
   `margin <= 0.99` and `blob_count >= 2` refuse the *identical* 29 frames. Nulls all
   separate (hypergeometric 1.6e-5 / 3.6e-5; selection-adjusted over the full 148-rule grid
   0.0000; cluster-preserving 0.0010). **The two graphs' signals are different in kind:**
   fp32 is a *closeness* test (all its content is below margin 0.077), int8 is a *presence*
   test (is there a runner-up blob at all). int8 misses `yt_rally2/0108`, where
   quantisation merged the ball and its confuser into ONE blob.
   **The three "small winner" candidates are dead, and not narrowly** — on every bad frame
   int8's winner is a *perfectly ordinary* blob: area 12-13 vs median 12, peak 242 which is
   the distribution's MAX and mode, score 2904-3146 vs median 2904. Catching 4/5 on any of
   them costs 82-100% collateral. int8 does not hesitate; it is confidently wrong.
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

**A method trap this cost, worth more than the result:** an A/B arm that inherits the
OTHER arm's threshold grid can manufacture a FAIL. The fp32 discriminating band was
[0.05, 0.077] so the grid stopped at 0.30; int8's signal lives at 0.86-0.99. Always sweep
the *full range the quantity can take* on each arm, not the range that mattered on the arm
you did first.

**How to apply:** do not describe this as failure detection or quote a catch rate as
accuracy. If it is ever proposed for a wider run, the question that decides it is a
*product* one — what happens downstream to a refused frame — not another measurement.
See [[ball-detector-choice-is-split]], [[int8-per-channel-is-a-noop-for-conv]],
[[null-controls-and-pre-registered-populations]].
