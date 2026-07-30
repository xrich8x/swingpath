# Session F — false fire: fix the precision we just spent

## Goal

Cut false ball detections **without giving back the recall Session E6 bought**, and
measure it on something that actually reaches the user.

## Why now

E6 part 4 re-tuned `suppress_false_locks` (`seg_dur_s` 0.15 → 0.10) and deliberately
traded per-frame precision for coverage. That was the right call on the evidence —
groundstroke speed error against the HUD fell 29.9% → 20.3% — but it leaves
precision as the open axis. This session pays that back.

## Baseline to beat (committed evidence, measured vs human gold clicks)

Raw detector, `ballnet_v21`, no tracker (`data/output/gold_v21_e6.txt`):

| clip | recall | false-fire | no-ball frames |
|---|---|---|---|
| am_hard_utr (1080p) | 62.3% | **45.3%** | 53 |
| gold_shell | 77.2% | 30.9% | 55 |
| gold_clay | 51.6% | **7.1%** | 14 |
| gold_am | 72.9% | 37.5% | 32 |
| yt_rally2 | 76.7% | 26.9% | 26 |
| yt_match40 | 76.1% | 41.7% | 24 |
| **POOLED** | **69.4%** | **34.8%** | 204 |

Full shipped chain after the E6 re-tune: yt_rally2 **23.1%**, am_hard_utr **25.0%**.

Note the spread — 7.1% on clay to 45.3% on am_hard_utr. Whatever fires is
clip-specific, which is itself a clue.

---

## Step 1 — Decide which false fire matters (do this FIRST, it is cheap)

**Per-frame false-fire is not the product.** Measured in E6 part 4: raising it from
19.2% to 23.1% on yt_rally2 produced **zero** extra phantom events — identical 14
hits, 8 bounces, 14 shots — because `events.drop_events_without_ball` and
`smooth_forecast`'s segment logic absorb locks that never form a trajectory.

So optimising the per-frame number can burn a whole session improving something the
user never sees. Define and instrument the product metric before touching anything:

- **phantom shots** — shots whose hit frame has no human-labelled ball nearby
- **phantom bounces** — same for landings
- **phantom speed** — a confident speed on a shot the HUD has no stroke for
- **visible ghost ball** — frames drawn in the annotated video during gold no-ball frames

`tools/hud_compare.py` already reports unmatched strokes in both directions; extend
it to count our shots the HUD has no reading for. Gate: report both the per-frame
number and the product number for every experiment below, and pick on the product
number.

## Step 2 — Characterise the survivors (blocks Steps 4 and 5)

**Do not assume the false locks are fixtures.** The new per-gate counters say
`fixture = 0` on am_hard_utr across 28,998 frames — the static-lock gate never fires
there, because that clip has no burned-in HUD. Yet its raw false-fire is the worst
of any clip at 45.3%. So the confusers are **moving**, and the entire existing
hard-negative mining criterion (see Step 4) is built on static locks and therefore
cannot address them.

Extend `tools/inspect_false_locks.py` (already reports position, court projection,
local roam radius, run length) to the am_hard_utr and yt_match40 gold no-ball
frames, and classify each surviving lock by eye from a contact sheet:

- player body / racquet / shoe
- court line, marker, or paint edge
- fence, net cord, net post, windscreen
- shadow, water bottle, ball on the ground (a *stationary real ball* is a
  legitimately hard case — it IS a ball, just not in play)
- adjacent court, spectator, background motion

**Gate:** a one-page tally with counts. Every later step is chosen from this table.
If the survivors are mostly *stationary real balls*, the answer is not precision at
all — it is the live-ball question, and Step 5 is the wrong tool.

## Step 3 — Sweep the detector score threshold (cheapest possible win)

`score_thresh = 0.5` is hardcoded in four places (`ball.py:923, 942, 996, 1005`) and
exposed by **no** tool or CLI flag. It has never been swept. It is the most direct
precision dial in the stack and costs no training.

- Add `--score-thresh` to `tools/ball_perception.py` and `tools/tune_suppress.py`.
- Sweep 0.4 / 0.5 / 0.6 / 0.7 / 0.8 on the calibrated gold clips, reporting recall,
  far_geo and false-fire — reuse the `tune_suppress.py` pattern (one GPU perception
  pass per threshold; the threshold is applied inside the detector so it cannot be
  swept in memory).
- **Gate:** ship only a point that beats the current one on the Step 1 product
  metric. Expect a real curve here; the detector emits a sigmoid heatmap and 0.5 is
  an inherited default, not a measured choice.

## Step 4 — Close the hard-negative gap, and widen the criterion

The two new 1080p training clips are badly under-mined relative to the legacy tier:

| dataset | labels | hard negatives | as % of labels |
|---|---|---|---|
| legacy 720p clips (10) | 1572–2478 | 205–493 | 9–26% |
| yt_col_hard_zheng | 2296 | **136** | **6%** |
| yt_am_dbl_classb | 2065 | **52** | **3%** |

This is the quantified cause of the v3 regression (best composite 20.9 vs v21's
23.7, false-fire 64–67% vs 57.7–60.2%): adding the new tier *diluted* the
hard-negative fraction that the whole E5 effort existed to build.

Two things to do, in order:

1. **Re-mine to parity.** `backend/mine_hard_negatives.py --device cuda
   --contact-sheet`. Target ~15–20% of labels per clip, matching the legacy tier.
2. **Widen the mining criterion based on Step 2.** The miner's current definition of
   a safe hard negative is "a lock that does not move for several frames ⇒ provably
   a fixture". That is sound but narrow, and Step 2 will likely show it misses the
   actual confusers. Candidate extensions, in order of how well-founded they are:
   - **Geometric:** a lock outside `ball.play_volume_polygon` is provably not a ball
     in play. This is a *geometry* label, not a model label, so it does not violate
     the never-grade-your-own-homework rule. Needs a calibration per training clip.
   - **Kinematic:** a lock that never joins a multi-frame trajectory (the
     min-segment test) — same logic as `suppress_false_locks`, applied at mining
     time.
   - Do **not** mine "frames the pipeline decided had no ball" — that is the model
     grading its own homework and will bake in its own errors.

**Gate:** retrain (v3.1) and measure with `tools/eval_detector_gold.py`. Must beat
v21's composite (`hit@10 − false-fire`) of 23.7, and must not lose pooled recall.

## Step 5 — Motion attention (v4) — CONDITIONAL on Step 2

`_ballnet.MotionPrompt` is implemented, unit-tested, and auto-detected at load time
from `motion.*` checkpoint keys — but **no checkpoint has ever been trained with
it**. It derives `|f0−f1|` and `|f1−f2|` from the three frames the net already
receives and gates the heatmap in logit space (TrackNetV4, arXiv:2409.14543).

Train it **only if Step 2 shows the survivors are static or low-motion**. That is
precisely what it suppresses, and it is the literature's own answer. If Step 2 shows
they are moving (players, shadows), motion attention will not help and training it
is a wasted GPU hour — say so and skip it.

    cd backend && .venv-train/Scripts/python.exe train_ballnet.py \
        --epochs 40 --motion-attention --out weights/ballnet_v4.pt --device cuda

**Gate:** compare v4 to v3.1 on gold, one variable at a time — same data, only the
architecture differs.

## Measured dead ends — do NOT re-propose

Every one of these was tried and measured in this repo.

- **Court + vertical cone gate for false alarms** — a real airborne far ball's z=0
  projection spans court-y −229..+1667 m and overlaps the confusers completely.
- **Scaling `static_radius_px`** 12 → 18 px — halves false-fire (13.2 → 5.7%) but
  costs 4.3 pts of far-court recall.
- **The offline live-ball filter** — 4.0% false-fire but recall 50.2 → 40.5%.
- **Detector fusion** (TrackNet ∪ WASB) — rescued 4 frames, doubles the dominant cost.
- **Dead-time "silence" negatives** — the wrong negatives; that is what v1 had.
- **Depth-aware Kalman process noise** — median-referenced made false-fire *worse*
  (19 → 27%).
- **`seg_gap_s`** (bridging a detector blink) — real mechanism, but a no-op at the
  shipped ~30 fps; only bites at 60.

## Verification

Every number stated against **human gold clicks** (`data/gold/*.labels.json`) or the
**SwingVision HUD** (`data/gold/hud_yt_rally2.json`), and each stated with which one.
Gold is TEST-only and never trained on — `train_ballnet.py`'s derived gold guard
enforces this and will refuse to start on a leak.

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
```

```bash
cd backend && .venv-train/Scripts/python.exe ../tools/eval_detector_gold.py --weights weights/ballnet_v21.pt weights/ballnet_v31.pt --device cuda
```

```bash
cd backend && .venv-train/Scripts/python.exe ../tools/tune_suppress.py --clip am_hard_utr --device cuda
```

```bash
backend/.venv/Scripts/python.exe tools/hud_compare.py --match data/output/rally2_seg10.json --hud data/gold/hud_yt_rally2.json
```

Two traps this project has already fallen into — avoid both:

- **Never trust a stale perception cache** for a current-state number. Re-perceive.
- **Check gold-frame parity** before quoting a decimated run. `yt_rally2` is 100%
  even frames; `am_hard_utr` is 48.6% odd, so at `step=2` half its labels are
  unscoreable. Use `--frame-step 1` when the sample matters.

## Kickoff prompt

> Read CLAUDE.md, ML_PRACTICES.md and ML_PLAYBOOK.md, then
> docs/sessions/SESSION_F_false_fire.md. We are cutting ball false-fire without
> giving back the recall E6 bought. Do Step 1 and Step 2 first and show me the
> tally before proposing a fix — the per-gate counters say the static-lock gate
> never fires on am_hard_utr, so I do not want to assume the confusers are
> fixtures. Then Step 3 (the score-threshold sweep has never been done). Steps 4
> and 5 depend on what Step 2 finds.

## Results

_(fill in as it ships)_
