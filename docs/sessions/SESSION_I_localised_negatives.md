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

## State on 2026-08-08 — plumbing SHIPPED, training PAUSED part-way

**Everything except the retrain is done, tested and committed.** Pick this up by
running the two commands under "To resume" — no setup, no decisions pending.

Done:
- `tools/mine_localised_negatives.py` + confuser files emitted in all 14 dataset
  dirs. **Yield 3,336 / 26,293 labelled frames (12.7%)** — the go/no-go passed.
  Highest on the amateur clips (35.7%, 31.0%) vs 6-20% broadcast.
- `train_ballnet.py` per-pixel weight map, `--hard-weight` / `--conf-radius`,
  default OFF and an exact arithmetic no-op. 7 tests in
  `backend/tests/test_localised_negatives.py`; 268 total.
- Verified: 2,521 of 26,161 training samples carry confusers with the flag on,
  0 with it off.

**Stopped at Arm A epoch 6 of 15** (user needed the machine). Arm B never started.
`backend/weights/ballnet_i_base.pt` is a PARTIAL best-so-far from epoch 5 — it is
NOT a baseline arm, do not score it, and the resume command overwrites it.

**MEASURED COST, and it is worse than the single-epoch probe suggested.** The probe
said 6m48s; the real run settled at **8m30s-10m45s per epoch** (disk-bound: three
JPEG reads per sample). So budget:

| budget | per arm | both arms |
|---|---|---|
| 15 epochs (the screen) | ~2h15m | **~4h30m** |
| 40 epochs (default) | ~6h | ~12h |

### To resume

```
cd backend
.venv-train/Scripts/python.exe train_ballnet.py --epochs 15 --device cuda --out weights/ballnet_i_base.pt
.venv-train/Scripts/python.exe train_ballnet.py --epochs 15 --device cuda --hard-weight 8.0 --out weights/ballnet_i_conf.pt
```

Then score BOTH arms against the pre-registered gate:

```
.venv-train/Scripts/python.exe ../tools/eval_model_filters.py --weights weights/ballnet_i_base.pt weights/ballnet_i_conf.pt --clip yt_rally2 --device cuda
.venv-train/Scripts/python.exe ../tools/eval_model_filters.py --weights weights/ballnet_i_base.pt weights/ballnet_i_conf.pt --clip am_hard_utr --device cuda
.venv-train/Scripts/python.exe ../tools/eval_detector_gold.py --weights weights/ballnet_i_base.pt weights/ballnet_i_conf.pt --device cuda
```

### Two things the next session must not do

1. **Do not compare either arm against `ballnet_v21.pt`.** That checkpoint carries
   no provenance beyond its weights, so its recipe cannot be verified and the
   comparison would confound this change with whatever has drifted since. The
   baseline arm exists precisely so the A/B has one variable.
2. **Do not ship a 15-epoch checkpoint.** Both arms are undertrained by design.
   A treatment win means "spend the ~12h on the 40-epoch pair", not "make this the
   default detector".

### The gate, unchanged and pre-registered

- **solid ghosts must FALL** (pooled, calibrated clips). They have sat at 9 through
  eight attempts; not moving them means this is the ninth failure.
- pooled recall must not drop more than 2 pts — precision bought by going blind is
  not a win, and that is the specific risk of negative-weighting.
- far_geo must not drop more than 2 pts.

If the ghosts do not move, **record it and stop pursuing false fire from the
training side.** 9 would then be this detector's floor at this data scale, and what
remains costs real money: many more labelled clips, or a larger backbone.
