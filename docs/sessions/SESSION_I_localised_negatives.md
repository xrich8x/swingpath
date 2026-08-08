# Session I — localised hard negatives: stop asking about the frame

**Kickoff prompt:** `Do Session I (docs/sessions/SESSION_I_localised_negatives.md)`
**User brings:** nothing. No labelling, no new footage.

## Why this exists

The 9 solid ghost balls have now survived **eight** independent attempts: detector
threshold, smoother gap, input resolution, motion attention, pose proximity,
racquet-box negation, suppression-rejection mining (catch/collateral), and
suppression-rejection mining (purity). Evidence:
[data/output/phase0_ball_ceiling.md](../../data/output/phase0_ball_ceiling.md).

They all failed for one structural reason, which Phase 0 finally isolated.

## The root cause

Hard negatives in `train_ballnet.py` are **whole-frame all-zero targets**, and the
guard is correct for that format:

> *"never use a frame that HAS a labeled ball as an all-zero-target negative, even
> if the fixture fire was elsewhere in it"*

That forces every mining criterion to answer *"does this frame contain a ball?"*,
and the answer is almost always yes: **the training clips are 88.5% ball-present**
(26,293 labelled ball frames vs 3,409 no-ball — they are extracted rally clips).

So the pool splits into two useless halves:

| | pure? | contains confusers? |
|---|---|---|
| dead-time frames | yes | **no** — already a measured negative |
| confuser-rich frames | **no** (88.5% hold a ball) | yes |

Best measured purity across all criteria: **43.7%**.

## What is actually missing — and it is NOT new labels

The loss is `BCEWithLogitsLoss(pos_weight=100)` on a Gaussian heatmap
(`train_ballnet.py:334`, `gaussian_heatmap` at :62). **The target is already zero
at the racquet.** The model is already penalised for firing there. The reason it
does not learn is weighting:

| | pixels | weight each |
|---|---|---|
| ball (Gaussian) | ~50 | 100x |
| everything else | ~147,400 | 1x |

The racquet head is one pixel among 147,400, weighted identically to empty sky.

**So this is re-weighting, not new information.** Do not describe it as new labels
— it is textbook hard-example mining, and the honest claim is emphasis.

## The change

A third sample kind alongside positives and whole-frame negatives: a labelled
frame **plus a list of confuser locations**. Target stays the Gaussian at the
known ball; the per-pixel loss weight is raised in a small disc at each confuser.

```
sample = (dir, idx, x, y, confusers=[(cx, cy), ...])
weight = 1 + (HARD_W - 1) * disc(confusers, r=CONF_R)     # 1.0 everywhere else
loss   = (BCE(pred, gauss(x, y)) * weight).mean()
```

`train_ballnet` already multiplies a per-sample weight (`per_sample * w` at :351),
so the hook exists — it becomes per-pixel rather than per-sample.

**Where the confuser locations come from, with no human input:** run the current
detector over the 26,293 labelled training frames and record every argmax that
lands further than `--far-px` from the known label. That is a confirmed false fire
at a known location on a frame whose ball position is already known.

## Plan

1. `tools/mine_localised_negatives.py` — detector over labelled training frames,
   emit `localised_negatives.json` per dataset dir: `{frame: [[x, y], ...]}`.
   **Report the yield first and stop if it is small** — the model trained on these
   frames, so it may already fit them. Yield is the go/no-go.
2. `train_ballnet.py` — per-pixel weight map; `--hard-weight` and `--conf-radius`.
   Default OFF so the shipped recipe is unchanged and reproducible.
3. Retrain with the flag on, identical everything else. **One variable.**
4. Score with `tools/eval_model_filters.py` on the 3 calibrated gold clips, and
   `eval_detector_gold.py` on all 6.

## Pre-registered gate

Ghost ball is the product metric, so it decides. Against the shipped `ballnet_v21`:

- **solid ghosts must FALL** — pooled across the calibrated clips. They have sat at
  9 through eight attempts; not moving them means this failed too.
- **pooled recall must not drop more than 2 points.** Precision bought by going
  blind is not a win, and that is the specific risk of negative-weighting.
- far_geo must not drop more than 2 points.

If solid ghosts do not move, **record it and stop pursuing false fire from the
training side.** At that point the honest read is that 9 is this detector's floor
at this data scale, and the remaining routes cost real money: many more labelled
clips, or a larger backbone.

## Guardrails

- `assert_no_gold_leak()` still applies — gold clips never enter training.
- The shipped recipe must remain reproducible: flag defaults OFF, and confirm the
  default path is unchanged before training anything.
- Do not re-propose whole-frame mining. Three criteria and two gates have failed;
  the format is the problem, not the criterion.

## Results (fill in during the session)
- _pending_
