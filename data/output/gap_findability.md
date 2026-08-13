# Can anything predict a findable far-court gap before a human clicks? No.

**Date:** 2026-08-13 · **Tool:** `tools/eval_gap_findability.py` · **Evidence:**
`data/output/gap_findability.json`
**Measured against:** 79 far-court gaps from `farcourt_cal1` + `farcourt_pilot2`, each with a
human verdict (anchor-confirmed AND ball-like click motion). Every feature is computable
from the queue manifest or the pseudo-label track — i.e. **before any human sees the gap**.

## Why this was the blocker

41% of queued gaps contain nothing findable; the human clicks a wall mark, or the identical
pixel twice. Session J's fix — putting *"a ball in play is somewhere different on every
frame"* on the labelling page — **did not work**: the round labelled 30 minutes after it
shipped is worse than the one before. So the control has to be mechanical and it has to run
at selection time.

It cannot be the anchor control, which compares the *human's* click against the tracker and
therefore needs a human by construction. It has to come from the queue itself.

## Pre-registered gate

**Keep ≥70% of usable gaps while dropping ≥60% of unusable ones.** Below that a screen either
throws away the far-court data we are short of, or saves the labeller no time.

## One candidate died for free

The midpoint's own tracker prior looks like independent evidence about whether the anchors
are consistent. It is not: on all 49 `cal1` gaps it reproduces **pure linear interpolation
between the anchors, 0 of 49 deviating by more than 0.5 px**. Any "is the midpoint
consistent with its anchors" feature is identically zero. Ruled out before it cost anything.

## Single features — all fail

| feature | usable median | unusable median | best split |
|---|---|---|---|
| anchor_disp_px | 44.0 | 32.1 | keep 73.0% / drop **50.0%** |
| roam_max_px | 94.1 | 56.6 | keep 67.6% / drop 57.1% |
| speed_px_per_frame | 14.6 | 7.7 | keep 64.9% / drop 52.4% |
| anchor_y_drop | 20.2 | 7.8 | keep 64.9% / drop 57.1% |
| gap_frames | 4.0 | 3.0 | keep 54.1% / drop 64.3% |
| roam_min_px | 57.3 | 49.4 | keep 59.5% / drop 50.0% |
| anchor_y_mean | 216.6 | 221.8 | keep 56.8% / drop 45.2% |

**Every median is ordered the right way** — usable gaps really do have more tracker
displacement, more roam and more vertical drop. The distributions simply overlap far too
much to act on.

**Session J's roam criterion is retested and confirmed failing**, now on 79 gaps instead of
12: 67.6% / 57.1% at best.

## Pairs — 569 "pass", and that is the finding

Sweeping every pair of features and every threshold, **569 combinations clear the gate**.
That is not a result: the search evaluates roughly **500,000 candidate rules against 79 data
points**. So they were cross-validated on the natural split — fit on one round, test on the
other.

| | pass on the fit half | survive held-out |
|---|---|---|
| cal1 → pilot2 | 1,422 | **2 (0%)** |
| pilot2 → cal1 | 129 | **4 (3%)** |

Held-out means: **keep 52.6% / drop 58.4%** and **keep 62.2% / drop 51.2%**, both well under
the 70/60 bar. The in-sample winners were fitting noise.

**GATE FAILS.**

## The null control, which is what makes this interpretable

Re-running the identical search on **shuffled labels** produces **0 passing pairs**. So the
signal is *real* — random labels cannot manufacture even one rule where the true labels
manufacture 569 — it is simply far too weak to survive contact with a round it was not
fitted to.

That is a more useful statement than "no signal": **the queue's own geometry knows a little
about findability and not nearly enough to screen on.**

## Consequence

Four independent attempts have now failed to make the far-court queue produce usable labels
reliably:

1. local roam as a selection screen (Session J, n=12; **retested here at n=79**)
2. `ball.suppress_false_locks` as a selection screen (Session J)
3. instructing the labeller on the page (Session J → measured worse here)
4. any single feature or cross-validated pair of the seven available (this file)

The far-court label lever is **blocked on a problem nobody has solved**, not on labelling
effort. L3 does not run. Per the Session L brief's stopping-rule logic, the remaining levers
that are already quantified and need no model are **mount height** (54% → 81% close-call
accuracy from 1 m to 8 m) and **frame rate** (+5.8 pts at 1.5 m).

## What would change this

More gaps with a verdict. 79 is enough to show a weak effect does not generalise; it is not
enough to fit a multivariate screen. A round of ~200 labelled gaps would let the same search
be run with a real train/test split rather than a 49/30 one — but that is 2–3 hours of
clicking spent on tooling rather than on labels, and it should be a deliberate decision, not
a default.
