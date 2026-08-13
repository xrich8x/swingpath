# Racquet negation, re-measured — and the reason it fails is far court

**Date:** 2026-08-13 · **Tool:** `tools/eval_racquet_negation.py` · **Evidence:**
`data/output/racquet_negation_k.json`, control in `racquet_negation_control.json`
**Measured against:** human labels only — 30 racquet-class and 51 person-attached locks
from `data/gold/false_lock_classes.json` (6 clips) for CATCH; 1851 human ball clicks
across 10 gold clips for COLLATERAL. Detector is `pool_new_s0` (Session K arm B).

## The question

Session G part 4 tested "find the racket with COCO class 38 and negate locks on it" and
failed a pre-registered gate (60% catch at ≤5% collateral) by 5.5 points. The confuser mix
visible in Session K's false-fire review is far more racquet-dominated than the tally that
result was based on, so the criterion was re-scored on the current detector.

## Result — it got WORSE, not better

| margin @720p | catch (racquet) | catch (person-attached) | collateral |
|---|---|---|---|
| 0 px | **23.3%** | 19.6% | **4.6%** |
| 10 px | 23.3% | 23.5% | 7.1% |
| 50 px | 30.0% | 31.4% | 18.9% |

**GATE FAILS**, now by 36.7 points instead of 5.5.

**Control run first, and it reproduces Session G exactly.** Same tool, same gate, pointed
at the original `g_falselocks_raw.json`: 54.5% / 36.4% at margin 0 and 63.6% / 50.0% at
margin 50 — digit for digit. So the harness is sound and the change is attributable.

## But the headline overstates it — read the numerator

The catch *rate* is denominator-driven. The number of racquet locks the box actually
catches is nearly constant:

| population | caught / racquet locks | rate |
|---|---|---|
| Session G file (v21) | 12 / 22 | 54.5% |
| fresh v21 run | 12 / 32 | 37.5% |
| arm B | 7 / 30 | 23.3% |

The same ~12 locks are caught throughout. What changed is that **10 racquet-class locks
were added when `gold_uR5q2cSM6AY` was classified on 2026-08-11, and the racket box
catches 0 of them.** That one clip moves v21's own score from 54.5% to 37.5% without the
model changing at all. Arm B's further drop to 7 is real but small: on the 30 frames both
models fire, 19 are missed by **both**, 6 caught by both, 4 by v21 only, 1 by arm B only —
and the 4 v21-only cases have the two locks 59–596 px apart, i.e. the models are on
different objects and the shared "racquet" label does not describe both.

## Why the box misses them — this is the transferable part

On all 10 of the `gold_uR5q2cSM6AY` racquet locks, the detector's lock sits **737–869 px**
from the nearest detected racket box. Not a tight-box problem. A different racket.

| | detector lock | detected racket box |
|---|---|---|
| position | x ≈ 934–1012, **y ≈ 349–398** | x ≈ 200–1750, **y ≈ 767–904** |
| size | — | 80–150 px, conf **0.46–0.83** |

The locks are high in frame — the **far** player. The boxes are low in frame and large —
the **near** player. YOLO reliably finds the near racket and does not find the far one.
Frame 46 is the single exception and proves it: a far racket *is* detected there, at
**37×56 px and conf 0.12**, against the near racket's 91×91 px at conf 0.83.

So **"a racket is found on 64–100% of frames" is true and useless** — it was finding the
wrong racket. That per-clip detection rate was quoted in Session G part 4 as evidence the
ceiling was the criterion rather than the detector. On this population it is the detector,
and the failure is the same far-court failure as everything else in this project: COCO's
tennis racket is trained on large sharp rackets, and a far-court racket on a 3.3 m mount is
small and motion-blurred. Our ball detector is built for exactly that regime, so it fires
there; the racket detector cannot follow it.

**Racquet negation is structurally blind precisely where the confuser lives.**

## Consequence for a runtime filter

Independent of catch rate, excluding detections inside racket boxes is dangerous in a way
the pooled collateral figure hides: **at contact the ball is inside the racket box by
definition**, and contact frames drive hit detection, launch point for speed, and rally
segmentation. A 4.6% average collateral is not spread evenly — it concentrates on the
frames the product depends on most. Same shape as Session H part 4's finding that pooled
line-call agreement hides everything: score on the population where the answer is in doubt.

## What this does not close

Mining (using racket boxes to source hard negatives for training) has different economics
from filtering — a false catch costs a slightly-wrong training example, not a deleted
detection. But the numerator above caps it: the criterion reaches ~7–12 locks, and it
reaches **none** of the far-court racquets that the current confuser population is made of.

Also unchanged: Session I found the ghost balls that survive to the rendered output are
5 universal frames of which only 2 are person-attached, so even a perfect racquet negator
reaches 2 of 5 there.

## Free external baseline, refreshed

Stock COCO "sports ball" scores **35.4% recall @10px (656/1851)** against the same human
clicks, versus BallNet v21's 69.4% and arm B's 80.4%. Not like-for-like — COCO's ball class
is trained on large sharp balls — so read it as a floor. It was 32.1% on the six-clip set.
