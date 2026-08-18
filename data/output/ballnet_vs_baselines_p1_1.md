# BallNet v21 vs TrackNet vs WASB, re-measured on the current 10-clip gold set

**Date:** 2026-08-17 · **Tool:** `tools/ball_perception.py --ball-model {tracknet,wasb,ours}` + `tools/eval_gold.py` (both pre-existing) · **Driver:** a one-off batch script, not a new tool (review finding P1-1 asked for a re-run, not new engineering)

## Why

The 2026-08-16 review (finding P1-1) found no dated re-run of the BallNet-vs-TrackNet-vs-WASB comparison since the detector changed substantially (v1 -> v21, +57% training data, hard-negative mining). The only recently-refreshed external baseline was COCO's generic sports-ball class (data/output/racquet_negation_k.md). This closes that gap using the harness that already existed.

**Measured against:** human gold clicks, hit@10px, on all 10 gold clips (1851 ball clicks / 308 no-ball frames). Two of the ten (`gold_UHf0LeMU2pg`, `gold_sAjkpeRq4P4`) are the blind holdout carved out today (P0-1) -- they are measured here like every other clip (this is a reporting run, not a sweep that picks a parameter), and flagged in the table so the distinction stays visible.

Decimated to ~30fps effective on every clip (`--frame-step max(1, round(src_fps/30))`, same formula tune_smoother.py/tune_suppress.py use) so 60fps and 30fps sources are on equal footing. Court gate ON where a clip has a calibration, OFF otherwise -- same per-clip condition for all three models, so the comparison stays apples-to-apples within a clip even though conditions differ across clips (ball_perception.py's own documented caveat).

## Pooled result

| model | hit@10 | wrong>10 | miss | med.err | FP (no-ball) | n_ball | n_noball |
|---|---|---|---|---|---|---|---|
| tracknet | 57.9% | 17.8% | 24.3% | – | 31.5% | 1558 | 267 |
| wasb | 49.3% | 22.8% | 27.9% | – | 40.1% | 1558 | 267 |
| ballnet_v21 (ours) | 60.8% | 21.6% | 17.7% | – | 55.1% | 1558 | 267 |

Pooled by summing raw hit/miss/fp counts across clips (weighted by each clip's labelled-ball count, same convention as tools/score_thresh_gates.py), not by averaging per-clip percentages.

**Read the FP column carefully.** `ball_perception.py`'s BallTracker applies bgsub
and the static/velocity gates, but NOT `suppress_false_locks` / `gate_ball_to_court`
/ `smooth_forecast` — the suppression chain the shipped pipeline runs afterward and
that v21's `score_thresh=0.5` was tuned around. So 55.1% is NOT comparable to the
shipped ~6.0% pooled false-fire figure in SCOREBOARD.md; it's the RELATIVE
precision of the three raw-ish detectors under identical conditions, which is the
correct question for a baseline comparison, just not the product number.

## Reading this honestly

**BallNet v21 still wins on hit@10, but by a much smaller margin than the
undated "+10.5 pts" claim that lived in `pipeline.py`'s auto-select comment**
(now corrected to point here): +2.9 pts pooled over TrackNet (60.8 vs 57.9),
+11.5 over WASB (60.8 vs 49.3). It also still false-fires the most of the
three (55.1% vs 31.5% / 40.1%) — expected, since v21 is tuned to run WITH the
suppression chain, not standalone, and that tradeoff is exactly why the
pipeline gates BallNet behind "only when calibrated."

**Not a universal win.** TrackNet beats BallNet outright on 2 of 10 clips
(gold_clay 58.9 vs 46.7, gold_L73ep7JHiJ4 67.3 vs 61.3) and both external
baselines struggle on the same hard clips BallNet struggles on
(am_hard_utr — the 1.74m low-mount clip — and the holdout gold_sAjkpeRq4P4,
where all three sit at 16-29%). That co-movement is a point in favor of
"this footage is hard," not "our detector is broken."

**So the honest one-line answer to "is the custom model still worth its
training cost":** yes on raw hit-rate, by a real but modest margin over
TrackNet and a clear one over WASB — but the bigger, well-established lever
remains what the suppression chain buys on top, not detector choice alone.

## Per clip

| clip | holdout | tracknet hit@10 | wasb hit@10 | ballnet_v21 hit@10 | n_ball |
|---|---|---|---|---|---|
| am_hard_utr |  | 31.5% | 19.1% | 36.0% | 89 |
| gold_shell |  | 67.4% | 63.6% | 69.0% | 184 |
| gold_clay |  | 58.9% | 47.7% | 46.7% | 107 |
| gold_am |  | 53.0% | 44.8% | 66.3% | 181 |
| yt_rally2 |  | 65.1% | 53.5% | 68.6% | 258 |
| yt_match40 |  | 64.1% | 48.4% | 64.1% | 184 |
| gold_UHf0LeMU2pg | YES | 64.3% | 50.6% | 58.9% | 168 |
| gold_sAjkpeRq4P4 | YES | 16.1% | 26.8% | 28.6% | 56 |
| gold_uR5q2cSM6AY |  | 46.0% | 48.5% | 64.4% | 163 |
| gold_L73ep7JHiJ4 |  | 67.3% | 57.1% | 61.3% | 168 |

Total wall-clock: 0.0 min.

Per-clip bucket breakdowns: `data/output/p1_1_rerun/<clip>_compare.md`. Raw perception caches and per-run logs: `data/output/p1_1_rerun/`.