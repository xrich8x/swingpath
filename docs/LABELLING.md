# LABELLING.md — the gold-label schema and the rules that produce it

The benchmark this whole project is scored against is **1,851 human ball clicks
and 308 no-ball frames across 10 clips**. Everything downstream — every recall
figure, every false-fire rate, every claim that a change helped — is a
comparison against those clicks. This file writes down what a label *means*,
because until 2026-08-17 the only statement of it lived in an HTML footer inside
`tools/gold_label_server.py`, where nobody would find it without opening the
tool's source (review finding P2-3).

## The schema

A label is one of exactly **three** states, per frame. There is no fourth.

| State | Recorded as | Means |
|---|---|---|
| **Ball** | `{"ball": true, "x": <px>, "y": <px>}` | A human saw the ball in play and clicked its centre. |
| **No ball** | `{"ball": false}` | A human looked and there is no ball in play to click. |
| **Unsure** | `{"unsure": true}` | A human looked and genuinely cannot decide. |

Coordinates are **source-resolution image pixels**, not network input pixels —
at the 512x288 detector input a far-court ball is ~1.6 px and unclickable.

**"Unsure" is excluded from both denominators.** It is neither a ball frame nor a
no-ball frame; it is removed before any rate is computed. That is why the pooled
counts (1851 / 308) do not sum to the number of frames presented.

### What the schema deliberately does NOT have

There is **no human-assigned occlusion or visibility class** (review finding
P1-3). `occluded=True` exists in `train_ballnet.py` but is set only when
*training-time augmentation pastes an occlusion patch* — it is synthetic and
never a human judgement. So the benchmark can be stratified by court depth,
serve, and model disagreement (the manifest buckets), but **not** by "how hard
was this frame to see". Anyone quoting a per-difficulty breakdown is quoting
something that does not exist.

## The one rule that changed a measured outcome

> **It has to move.** Arrow left and right before you commit. A ball in play is
> somewhere different on every frame; a pale dot in the *same* place on three
> frames is a wall mark, a light, a bag, or a ball lying on the net.

This is not style advice. Session J found that **17 of 49 gaps in one labelling
round had the human clicking the identical pixel on both frames**, which a ball
in play cannot do — and that round scored *worse* than the round before it
(47% vs 60% of gaps yielding usable motion).

The lesson recorded in TRAPS.md is sharper than the rule itself: **writing the
rule on the page did not work.** The instruction was added at 21:20 and the very
first round labelled under it was the bad one. What worked was enforcing it
mechanically in the converter (`MIN_MOTION_PX` in
`tools/farcourt_labels_to_dataset.py`). Treat the text below as an explanation of
a check that already runs, not as the check.

**`N` and `S` beat a guess.** Nothing counts how many balls you found. A labeller
who cannot find the ball and clicks the most ball-like thing in frame produces a
label that agrees with the detector's own mistake — raising measured agreement
while lowering truth. That failure mode has its own trap.

## What makes a labelling session valid

- **Blind.** The UI never shows a model prediction or the frame's selection
  bucket. If it did, the labels would not be independent of the thing they grade.
- **One-way clip assignment.** A clip is gold (TEST, never trained on) or train,
  decided at intake and never reversed. Enforced by the Lab, and independently by
  `train_ballnet.assert_no_gold_leak()`.
- **Source resolution.** Frames are served at the clip's native resolution.

## Known gap: reliability has never been measured

All 2,159 labels come from **one person, one pass, with no second pass and no
second labeller** (review finding P0-2). There is therefore no measurement of how
self-consistent the ground truth is, and no way to distinguish "the model got
worse" from "the labels drifted" if a future number looks surprising.

The fix is cheap and has not been done: re-label 50-100 already-labelled frames
blind and compare. `tools/relabel_consistency.py` builds that pass and scores it;
it needs a human to do the clicking.

## Files

| Path | What it holds |
|---|---|
| `data/gold/<clip>.labels.json` | the labels themselves |
| `data/gold/<clip>.manifest.json` | which frames were selected, and their bucket |
| `tools/gold_label_server.py` | the labelling UI |
| `tools/_goldset.py` | the clip registry, and the blind holdout |
