# More data, measured: +57% labelled frames across 8 new venues

**Date:** 2026-08-13 · **Evidence:** `data/output/pool_ab.json` · **Tool:** `tools/eval_detector_gold.py`
**Measured against:** human gold clicks on the ten-clip benchmark (1,851 ball frames, 308 no-ball
frames). Hit = detector peak within 10 px of the click. Detector-level, raw argmax — **not** the chain.

## The question

The eight clips ingested on 2026-08-11 added 15,097 labelled frames (26,293 → 41,390, **+57%**) from
eight venues the pool had never seen. Does that move the detector, and does it move it on footage
unrelated to the new venues?

## The two arms

| | arm A `pool_old_s0.pt` | arm B `pool_new_s0.pt` |
|---|---|---|
| dataset dirs | 14 (8 new clips excluded) | 22 (everything) |
| train pos / neg | 21,039 / 5,122 | 33,120 / 7,381 |
| epochs | 15, `--seed 0` | 15, `--seed 0` |
| best epoch (own val) | 6 | 12 |
| wall clock | 1h16m | 1h52m |

Same recipe, same seed, one variable: the eight directories. Scoring both took 13 min on CUDA.

**Gold guard verified before believing any of this.** `train_ballnet.gold_source_videos()` knows 11
gold source videos — including the lineage alias `7 utr vs 8 utr [uhf0lemu2pg].mp4` that trap 17 was
about — and `assert_no_gold_leak` confirms none of them appear in the 22 dataset dirs. The four clips
promoted to gold on 2026-08-11 are absent from the training pool entirely, so the gain is not a leak.

## Result

Pooled by summing numerators and denominators (never a mean of percentages — Session I §5).

### All ten clips

| metric | arm A | arm B | Δ | z |
|---|---|---|---|---|
| recall | 74.8% (1384/1851) | **80.4%** (1488/1851) | **+5.6** | +4.1 |
| far_px | 73.3% (632/862) | **79.8%** (688/862) | **+6.5** | +3.2 |
| far_geo | 74.0% (687/929) | **79.5%** (739/929) | **+5.6** | +2.9 |
| false-fire | 57.1% (176/308) | 53.9% (166/308) | −3.2 | **−0.8** |

### The legacy six alone — venues unrelated to the eight new clips

| metric | arm A | arm B | Δ | z |
|---|---|---|---|---|
| recall | 77.0% (925/1201) | **82.2%** (987/1201) | **+5.2** | +3.1 |
| far_px | 78.6% (383/487) | **84.4%** (411/487) | +5.7 | +2.3 |
| far_geo | 79.5% (365/459) | 84.1% (386/459) | +4.6 | +1.8 |
| false-fire | 56.4% (115/204) | 56.9% (116/204) | +0.5 | +0.1 |

### The four clips added 2026-08-11

| metric | arm A | arm B | Δ | z |
|---|---|---|---|---|
| recall | 70.6% (459/650) | **77.1%** (501/650) | +6.5 | +2.7 |
| far_px | 66.4% (249/375) | 73.9% (277/375) | +7.5 | +2.2 |
| far_geo | 68.5% (322/470) | 75.1% (353/470) | +6.6 | +2.2 |
| false-fire | 58.7% (61/104) | 48.1% (50/104) | −10.6 | −1.5 |

Per-clip recall: **up on 9 of 10, flat on 1** (`gold_L73ep7JHiJ4`, 83.9 → 83.9), **down on none**.

## What this does and does not say

**IT IS A RECALL RESULT.** +5.6 pts pooled at 4.1σ, and it holds at +5.2 pts on the legacy six —
clips whose venues share nothing with the new footage — so it is generalisation, not domain-matching
to the batch that was added. On the historical 1,201-frame benchmark this is the highest detector
recall recorded (82.2%; the shipped `ballnet_v21` reads 69.4%, the Session I arms 79.9/80.4%).

**FALSE FIRE DID NOT MOVE.** −3.2 pts pooled is **0.8σ** on 308 no-ball frames, and on the legacy six
it is +0.5 pts — flat. Do not describe this as a precision gain. The apparent −10.6 on the new four is
1.5σ on 104 frames and is not separable from noise either.

**IT IS NOT THE PRODUCT.** Detector-level recall is not the rendered output. Session I established
that detector precision and chain precision are close to decoupled and that a detector gain has failed
to reach the product three times; that finding was about *precision*, and this is *recall*, so it does
not transfer automatically in either direction. The chain test (`tools/eval_model_filters.py` on the
calibrated clips, scoring solid ghosts and chain recall) **has not been run**, and until it is, the
correct statement is "the detector finds more ball", not "the product improved".

**THE DEFAULT DETECTOR IS UNCHANGED.** `ballnet_v21.pt` remains shipped. Session I measured its
15-epoch arms at 14–15 solid ghosts against v21's 9 despite better detector recall; arm B is also a
15-epoch run and would repeat that mistake if promoted on a detector number alone.

## Caveats that limit the claim

1. **n = 1 training run per arm.** The unit of randomisation for "does more data help" is the training
   run, and there is one of each. `--seed 0` on both fixes initialisation and seeds the shuffle — a
   real improvement on Session I's unseeded arms — but the datasets differ in size, so batch
   composition and augmentation draws still differ. The 9-of-10 per-clip sign test measures
   *evaluation* noise, not training noise.
2. **Model selection differed.** Each arm's checkpoint is its own best epoch on its own validation
   split, and arm B's validation set contains the new venues. That is an honest part of the treatment
   "train on more data", but the two were not selected against the same criterion.
3. **`far_geo` is not "far court".** It is the part of each clip that cannot be measured in, and on a
   low camera that is most of the frame. Compare it only between clips of similar measurable depth.

## Reproduce

```
cd backend && .venv-train/Scripts/python.exe train_ballnet.py --epochs 15 --seed 0 \
    --out weights/pool_new_s0.pt
.venv-train/Scripts/python.exe ../tools/eval_detector_gold.py \
    --weights weights/pool_old_s0.pt weights/pool_new_s0.pt --device cuda \
    --json ../data/output/pool_ab.json
```

Arm A additionally passes `--exclude yt_A7vXlWIlyrI yt_CYqapSq5llo yt_e8T34KoJzOw_s1
yt_e8T34KoJzOw_s2 yt_HoHxFSX_gLk_s1 yt_HoHxFSX_gLk_s2 yt_HoHxFSX_gLk_s3 yt_tc8CGFxyRE8`.
