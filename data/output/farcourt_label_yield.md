> **SUPERSEDED / READ WITH CARE** — stamped 2026-08-15.
> Its clip-level HUD attribution was RETRACTED by farcourt_anchor_audit.md (only 5 of 36 clicks were inside a graphic). The real blocker was false-lock anchors, and the whole lever was later closed by Session L's stopping rule - see gap_findability.md.

# Far-court labels: how many are missing, and can they be filled without a human?

Two questions asked before spending any of the user's labelling time. Both are
answered with numbers, and the second one closes a shortcut that looked free.

Evidence: `data/output/session_i_ab/coast_*.json` (eval_model_filters, shipped
chain, `ballnet_v21`, each clip at its shipped frame step).

---

## 1. The gap is 4,087 frames, not "a few hundred"

SCOREBOARD has said far-court recall is waiting on "a few hundred human far-court
labels" for several sessions. Counting the actual hole in the training set:

A training frame is a far-court miss when the pseudo-labeller (the tracker) has a
confident position on both sides but nothing on the frame itself, and the
interpolated position falls in the top 36% of the frame — the project's
resolution-comparable `far_px` band.

| | frames |
|---|---|
| far-court positions the training set already has | 9,609 of 26,293 (36.5%) |
| far-court frames the tracker MISSED, bracketed both sides | **4,087** |

So filling them would grow far-court training data by **43%** — a real prize — but
at a few seconds per click it is **4-5 hours of human time**. That is almost
certainly why it has never started, and it means the task has to be *ranked*, not
completed.

**89% of those misses sit in gaps of 10 frames or fewer:**

| bridge length | far-court frames | cumulative |
|---|---|---|
| 1-2 | 1,080 | 23.5% |
| 3-5 | 1,587 | 58.0% |
| 6-10 | 1,420 | 88.9% |
| 11-20 | 410 | 97.8% |
| 21+ | 101 | 100% |

The tracker does not lose the far ball for long stretches. It **flickers** — and
every flicker is anchored by a confident detection on both sides.

## 2. Those anchors are NOT accurate enough to fill the gap. MEASURED NEGATIVE.

If a bracketed position could be recovered from its anchors plus the ball's motion,
those 4,087 frames would be free labels and no human would be needed. The pipeline
already does exactly that interpolation at inference (`smooth_forecast`), so the
question is only whether the result is accurate enough to *train* on.

Scored against human gold clicks — every frame where a human clicked a ball and the
chain only had an interpolated position, 3 calibrated clips:

| clip | n | median err | p90 | max | within 10 px |
|---|---|---|---|---|---|
| yt_rally2 | 32 | 6.5 px | 46 px | 80 px | 59% |
| yt_match40 | 29 | 5.3 px | 95 px | **396 px** | 69% |
| am_hard_utr | 12 | 8.6 px | 69 px | 77 px | 58% |
| **pooled** | **73** | | | | **63%** |

**About 37% of interpolated positions are more than 10 px wrong.** As a training
target that is not a slightly noisy label, it is a Gaussian placed on empty court —
actively teaching the detector that a patch of grass is a ball. Worse than no label.

### And there is no safe subset to carve out

The obvious rescue is "only use short bridges". Pooled by bridge length:

| bridge | n | within 5 px | within 10 px |
|---|---|---|---|
| 1-2 | 13 | 46% | 62% |
| 3-5 | 20 | 45% | 60% |
| 6-9 | 36 | 39% | 64% |
| 10+ | 4 | 25% | 75% |

**Flat.** Accuracy does not improve as the bridge shortens, so there is no
threshold that separates trustworthy interpolations from bad ones. (Bins of 4-36
are small and the ordering within them is noise — but the *absence* of a trend
across a 5x range of bridge lengths is the finding, and it is enough to kill the
subset idea.)

CAVEAT on n: 73 interpolated positions is a small sample, set by how often a human
click and a bridged frame coincide. It is ample for "63% is not good enough for a
label" and too small for a precise figure. Do not quote the per-bin percentages.

## 2b. PILOT RESULT — the frames are labelable, but a HUD ball icon poisons them

12 gaps / 36 frames, one per clip, at source resolution (`data/labels/
farcourt_pilot.*`). The labeller found a ball on **10 of 12 gap frames** and 19 of
24 anchors, so the frames ARE readable at 720p/1080p — the earlier 512x288 attempt
failed on resolution, not on the ball being absent.

**But split by clip, the result is two different results.** On the four clips with
a burned-in scoreboard graphic, every click landed on the little **tennis-ball icon
inside the scoreboard** (top-left, 200-300 px), 400-650 px from the real ball. On
the clips without one, the human landed **0.6-7.2 px** from the tracker:

| clip | HUD? | human vs tracker |
|---|---|---|
| yt_6jp23ghDY9Q, yt_8-BkpjFFIhQ, yt_RZ_wyJ9rI3Q, yt_WjHZrIYteDA | yes | 112-645 px |
| yt_am_dbl_classb, yt_col_hard_zheng, yt_nQan0M5JDM8, yt_tC0z7FYvMks | no | **0.6-7.2 px** |

Two consequences.

1. **These pilot labels must NOT be built into a dataset.** Roughly a third of them
   place a ball on a scoreboard graphic, which is precisely the confuser the
   detector already fires on. They are kept as evidence, not as training data.
2. **The queue must mask or crop burned-in graphics before a human sees it.** This
   is the same HUD-confuser family the project has known about since the demo30
   investigation; it had simply never been on the *labelling* side before. Until
   that exists, a labelling session on HUD footage produces negative value.

The clean-clip agreement is the genuinely good news: where nothing impersonates the
ball, a human and the tracker agree to within a few pixels, so the anchors are
sound and the exercise is worth repeating once masking is in.

## 3. What follows

1. **Human far-court labels are genuinely required.** That was an assumption in
   SCOREBOARD; it is now measured. The automation was tried and fails on accuracy.
2. **Rank, do not complete.** 4,087 frames is five hours. A few hundred, stratified
   across clips and conditions, is 30-40 minutes and buys most of the diversity —
   labelling 300 frames from one rally teaches far less than 300 spread wide.
3. **A ghost-ball gate must be pre-registered on any far-court training run.**
   Teaching a detector to fire where the ball currently cannot be seen is one step
   from teaching it to hallucinate a plausible arc, which is precisely the failure
   mode Session I characterised (every drawn ghost has `run_len = 1` and looks
   kinematically like a real ball). More far-court recall bought with more phantom
   balls is not a win.
