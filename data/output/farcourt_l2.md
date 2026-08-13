# Session L, steps 1–2 — the far-court queue fails its yield gate, and the labelling rule did not work

**Date:** 2026-08-13 · **Evidence:** `data/output/{cal1,pilot2}_gaps.txt`, the converted dirs
under `data/ball_dataset/farcourt_*` · **Tool:** `tools/farcourt_labels_to_dataset.py`
**Measured against:** the human's own clicks — how far a click travels across a gap. A ball
in play is somewhere different on every frame; a static object is not.

## L2 result: GATE FAILS

Pre-registered in the session brief: **≥60% of gaps must yield a click whose motion exceeds
the static band** (Session J's separation: static 1–8 px, ball 17–116 px).

| round | n | median | ball-like ≥17 px | static ≤8 px | anchor-kept | passes BOTH |
|---|---|---|---|---|---|---|
| `farcourt_cal1` | 49 | 14 px | **47%** | 41% | 55% | **35%** |
| `farcourt_pilot2` | 30 | 28 px | 60% | 33% | 77% | 50% |

**`cal1` reads 47% against a 60% gate. FAIL — so L3, the 4–5 hour labelling push, does not
run as planned.**

### The corrective rule from Session J did not work

Session J ended by adding *"a ball in play is somewhere different on every frame"* as the
lead rule on the labelling page, on the strength of finding that the anchor control measures
agreement with the tracker rather than correctness. The commit landed at **21:20**;
`farcourt_cal1` was labelled at **21:50–21:59** — the first round under the new rule.

It is **worse than the round before it** (47% vs 60% ball-like). The clips differ, so this is
not a clean A/B, but it is decisively not the improvement the rule was added to produce.
**A written instruction on the page is not a control.**

### The distribution, which is the actionable part

`cal1` click motion, n=49:

```
0 px     █████████████████ 17      <- the IDENTICAL pixel, clicked twice
1-8      ███ 3
9-16     ██████ 6                  <- the valley
17-40    ███████████ 11
41-100   ██████████ 10
100+     ██ 2
```

**Seventeen of 49 gaps have the human clicking the same pixel on both frames.** A ball in
play cannot be in the same place two frames apart, so those are not noisy labels — they are
a static object, and training on them teaches the detector to fire on wall marks.

The bimodality also **independently confirms Session J's threshold**, which was the one thing
blocking its use: it was found post-hoc on 12 gaps, and a cutoff fitted to its own evidence
is a memory rather than a control. It has now reproduced on 49 gaps it was not derived from,
with only 6 in the 9–16 px valley. So the test is **now ENFORCED** in the converter
(`MIN_MOTION_PX = 9.0`, scaled by frame height, `--min-motion-px 0` restores the old
behaviour so earlier rounds stay re-adjudicable).

## L1 result: 34 labels banked, conversion INCOMPLETE

Converting the 173 collected labels under both filters (anchor control AND motion) hit two
genuine defects in the round-trip gate. Both are now fixed; the second is unresolved data.

**1. The gate counted a TIE as a mismatch.** `TilAFMPc0yg:2787` scores 2.575 against frame
2786 and 2.575 against 2787 — identical to three decimals, so `argmin` decided by dict
insertion order, not by pixels. That is the same *"on a frozen scene the argmin is noise"*
case the gate already reports as `unresolved_static`; it simply was not reached when the tie
fell the wrong way. Now judged on the same `min_margin`, so there is one notion of
too-close-to-call rather than two.

**2. A real frame offset, which the gate correctly refuses.** `VZWi6Vf-sX0` (4 frames) and
`RZ_wyJ9rI3Q` (1) show mean-abs falling **monotonically across the whole ±3 window** to a
minimum at +2 or +3:

| claimed | best | lead over claimed |
|---|---|---|
| 9252 | 9255 | 29.7% |
| 9256 | 9259 | 22.0% |
| 9390 | 9392 | 22.7% |
| 9392 | 9395 | 20.1% |
| 1231 | 1234 | 20.9% |

A 20–30% lead is not noise. The built sample is 2–3 frames later than the frame the human
labelled, on these clips only — others round-trip cleanly at margins of 0.13–0.71. **Cause
unknown and NOT bulldozed**; the gate is doing exactly its job.

**Also fixed:** the gate ran *after* `build()`, so a failure left an unverified directory in
the training pool — the precise hazard it exists to prevent, arriving through a different
door. It now removes the directory before exiting.

**State:** 6 clips converted and verified, **34 far-court labels** in the pool. The run
aborts at the first failing clip, so most clips in both rounds were never reached.

## What this means for the plan

The far-court lever is **not blocked on labelling effort — it is blocked on queue
selection**. 41% of gaps present the labeller with no findable ball, and telling them so on
the page did not change it. At a 35% both-filters yield, 300 defensible positives would need
~860 gaps ≈ 2,580 frames clicked, and the yield rate itself is a proxy for correctness, not
a measure of it.

Before any further human time is spent:

1. **Fix the frame offset** on `VZWi6Vf-sX0` / `RZ_wyJ9rI3Q`, or exclude those clips.
2. **Fix the queue**, so a gap is only offered when a ball is plausibly findable in it. The
   anchor control is applied at label time, after the human has already spent the effort;
   it needs to move earlier. Session J measured that local roam and `suppress_false_locks`
   both fail as selection-time screens, so this needs a new idea, not a re-tune.
3. Only then L3.

The 34 banked labels are 0.08% of the 41,390-label pool and cannot move a number on their
own. They are recorded, not tested.
