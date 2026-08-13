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

## L1 result: COMPLETE — 105 labels, all round-trip verified

Converting the 173 collected labels under both filters (anchor control AND motion) hit two
genuine defects in the round-trip gate. Both are now fixed; the second is unresolved data.

**1. The gate counted a TIE as a mismatch.** `TilAFMPc0yg:2787` scores 2.575 against frame
2786 and 2.575 against 2787 — identical to three decimals, so `argmin` decided by dict
insertion order, not by pixels. That is the same *"on a frozen scene the argmin is noise"*
case the gate already reports as `unresolved_static`; it simply was not reached when the tie
fell the wrong way. Now judged on the same `min_margin`, so there is one notion of
too-close-to-call rather than two.

**2. NOT a frame offset — the gate's own index mapping. RESOLVED.**

The first read of this was wrong and is retracted below. `VZWi6Vf-sX0` (4 frames) and
`RZ_wyJ9rI3Q` (1) show mean-abs falling **monotonically across the whole ±3 window** to a
minimum at +2 or +3:

| claimed | best | lead over claimed |
|---|---|---|
| 9252 | 9255 | 29.7% |
| 9256 | 9259 | 22.0% |
| 9390 | 9392 | 22.7% |
| 9392 | 9395 | 20.1% |
| 1231 | 1234 | 20.9% |

A 20-30% lead is not noise, so this looked like a real 2-3 frame offset in the build. It is
not. **Sequential decode from frame 0 — the only ground truth, since it uses no seeking —
shows `build()` produces EXACTLY the frame it claims (MAD 0.0000), and that cv2 seeking on
these clips is exact at every index.**

The fault was in the gate. `build()` numbers each triplet by its POSITION in the usable-frame
list (sample `3k+2` carries the label for entry `k`), and it drops `unsure` frames. The gate
re-derived that list itself and KEPT the unsure ones, so on any clip with one, every later
sample was compared against the wrong source frame — an apparent offset the size of the
queue's frame spacing, which is 2-3.

It discriminated perfectly: **the only two clips that failed were the only two with an unsure
label, and all 19 with none passed.** The rule now lives once, in
`labels_to_dataset.usable_frames`, called by both, with an assertion in `build()` that it
still selects exactly what gets written. Two implementations of "which frames get written"
was one too many.

**Also fixed:** the gate ran *after* `build()`, so a failure left an unverified directory in
the training pool — the precise hazard it exists to prevent, arriving through a different
door. It now removes the directory before exiting.

**State:** with the mapping fixed, both rounds convert in full — **105 human far-court ball
labels across 21 dataset directories, every sample round-trip verified** (margins 0.09-0.71;
4 frames correctly reported as too static to resolve rather than passed or failed).

## What this means for the plan

The far-court lever is **not blocked on labelling effort — it is blocked on queue
selection**. 41% of gaps present the labeller with no findable ball, and telling them so on
the page did not change it. At a 35% both-filters yield, 300 defensible positives would need
~860 gaps ≈ 2,580 frames clicked, and the yield rate itself is a proxy for correctness, not
a measure of it.

Before any further human time is spent:

1. ~~Fix the frame offset~~ — **DONE**; it was the gate, not the data.
2. **Fix the queue**, so a gap is only offered when a ball is plausibly findable in it. The
   anchor control is applied at label time, after the human has already spent the effort;
   it needs to move earlier. Session J measured that local roam and `suppress_false_locks`
   both fail as selection-time screens, so this needs a new idea, not a re-tune.
3. Only then L3.

The 105 banked labels are **0.25%** of the 41,495-label pool. They are real, verified, and
cannot move a number on their own — recorded, not tested.
