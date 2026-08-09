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

## RESULTS (2026-08-09) — gate FAILS at the product, detector improves 6/6

Full numbers and method: **[data/output/session_i_ab/results.md](../../data/output/session_i_ab/results.md)**.
Both arms trained (1h13m + 1h09m — faster than the 4h30m budgeted below, the JPEG
cache stayed warm on the second pass).

**Product gate: FAIL.** Pooled over the three calibrated clips (74 no-ball frames),
solid ghosts **14 → 15**, recall 69.2 → 69.0%. Ninth failure at the ghost ball.

**Detector: a large, consistent win.** Pooled over all six gold clips (204 no-ball),
false fire **53.9 → 42.2%** — down on **6 of 6 clips**, by 7.3 to 23.0 points — at
*higher* recall (79.9 → 80.4%) and far_px (80.9 → 82.5%). That is 110 → 86 false
fires, a 3.4σ shift, and the operating point moved outward on both axes rather than
trading one for the other.

**Three things this session got wrong, and fixed:**

1. **The A/B had two variables.** `train_ballnet.py` had no seed at all, so the arms
   differed by initialisation, batch order and augmentation draws as well as by the
   flag. The tell: the three clips disagree in *sign* on every axis. `--seed`
   (default 0) now pairs a run; `recipe_stamp` now writes args/seed/git/dataset
   counts into every checkpoint, closing the same gap that made `ballnet_v21.pt`
   unusable as a control here.
2. **The resume list below omitted `yt_match40`** — one of the three clips in a gate
   defined as *pooled*, and the two it did list disagree in sign.
3. **The gate has never been reported with its own resolution.** It is a count of
   ~14 out of 74 frames, where sampling alone moves the count ±3.4. Detecting a
   *halving* needs 212 no-ball frames; a 30% cut needs 656. Nine null results
   therefore license "nothing has come close to eliminating the ghost ball", not
   "none of these did anything". `tools/gate_verdict.py` now prints the required-n
   beside the verdict.

**What this does NOT support, and the discipline matters here:** the detector win is
n=1 per arm. Six clips are six measurements of the same two models, so the 6/6 sign
test speaks to *evaluation* noise; the unit of randomisation for the treatment
question is the training run. Do not record "localised weighting cuts detector false
fire by 11.7 points" as a result until the paired re-run says so.

**FIVE FRAMES DEFEAT EVERY MODEL TESTED.** Recording `fire_frames_solid` made the
ghost set inspectable for the first time. 9 of the 20 distinct solid-ghost frames
fire on both arms; scoring `ballnet_v21` the same way returns a pooled count of
**9** — reproducing the standing figure exactly — of which it shares **5** with the
arms: yt_rally2 18/762/1494, yt_match40 4773, am_hard_utr 13276. So the *count* is
stable across models and the *composition* is only about half shared. The ghost
floor is five universal frames plus a model-specific tail, not one immovable nine.

### Next, in order

1. **Look at the five.** Cheapest thing on this list by an order of magnitude, and
   nothing else is well-aimed until it is done:
   `py tools/inspect_false_locks.py --stage chain --clip yt_rally2 --clip yt_match40
   --clip am_hard_utr --weights weights/ballnet_v21.pt --contact-sheet <out>.png`.
   Every previous "what is the detector firing at" tally (Session F step 2) was over
   *raw* detector locks; these five are what survives the whole chain to be drawn.
2. **Paired re-run, ~2h20m.** Both arms at `--seed 0`, so the flag is the only
   difference. Plus a third arm `--seed 1 --hard-weight 1.0` (~1h10m) for the noise
   floor — without it a paired difference still cannot be sized.
3. **Only then** consider the 40-epoch pair (~12h).
4. **Independently:** work out which chain stage absorbs detector precision. Three
   interventions have now cut detector false fire substantially and delivered
   nothing to the rendered output (input resolution, `score_thresh`, this). That is
   answerable from `fire_frames_solid` and the per-gate miss counters with no new
   training, and it gates the value of every future detector idea.

---

## State on 2026-08-08 — plumbing SHIPPED, training PAUSED part-way

*(Superseded by the results above; kept for the cost figures and the method.)*

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
.venv-train/Scripts/python.exe ../tools/eval_model_filters.py --weights weights/ballnet_i_base.pt weights/ballnet_i_conf.pt --clip yt_match40 --device cuda
.venv-train/Scripts/python.exe ../tools/eval_detector_gold.py --weights weights/ballnet_i_base.pt weights/ballnet_i_conf.pt --device cuda
```

**All THREE calibrated clips.** An earlier draft of this list omitted `yt_match40`,
which would have decided a *pooled* gate on two thirds of its evidence — and the two
clips it did list disagree in sign, so the omission was not cosmetic.

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
