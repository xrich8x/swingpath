> **STATUS: RUN 2026-08-01** — stamped 2026-08-15 during doc cleanup.
> Steps 1-3 run, 4-5 gated and not run. Key result: the confusers MOVE (59.2% with a person).
> This file is the PRE-REGISTERED BRIEF, kept for its gate and reasoning.
> For what actually happened and the current state of play, read
> [SCOREBOARD.md](../../../SCOREBOARD.md) — not this file.

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
> docs/archive/sessions/SESSION_F_false_fire.md. We are cutting ball false-fire without
> giving back the recall E6 bought. Do Step 1 and Step 2 first and show me the
> tally before proposing a fix — the per-gate counters say the static-lock gate
> never fires on am_hard_utr, so I do not want to assume the confusers are
> fixtures. Then Step 3 (the score-threshold sweep has never been done). Steps 4
> and 5 depend on what Step 2 finds.

## Results

Ran 2026-08-01. Steps 1–3; Steps 4 and 5 gated on Step 2 and reported below.
Every number is measured against human gold clicks (`data/gold/*.labels.json`)
or the SwingVision HUD (`data/gold/hud_yt_rally2.json`), and says which.

### Step 1 — the product metric. Two of four candidates survived contact.

**MEASURED, and it kills a metric: "phantom speed" is identically zero.** The 17
HUD readings in `hud_yt_rally2.json` tile source frames 62–2214 with a constant
2-frame gap (the step=2 decimation). The HUD is a persistent *panel* showing the
last stroke until the next replaces it, not a sparse event list, so there is no
instant at which it "has no reading" and every shot we emit falls inside some
panel. Dropped. Replaced by `surplus_shots`, tie-break evidence only.

**"Visible ghost ball" already existed** — it is the eval ladder's FULL-row
`fires`. `annotate.py` draws a ball iff `ball_px[i] is not None` on the same
post-`smooth_forecast` track the ladder scores. Only the split was missing: the
renderer draws a real detection as a solid disc and an interpolated one as a
faded ring, so a change that converts solid ghosts to faded ones has removed
nothing. Now printed as `fires=6 (5 solid, 1 faded)`.

**`hud_compare.py`'s matcher was wrong, and fixing it moves a published number.**
Greedy-forward with a hard `lag >= 0` floor — but our `t_hit_s` carries its own
±2-frame error, so a panel can be stamped slightly *before* the hit it describes.
MEASURED on `rally2_seg10`: the shot at t=14.73 could not claim the 14.60 panel
(lag −0.13 s), took the 16.20 one instead (+1.47 s vs a typical +0.5–0.9), and
orphaned the real shot at t=15.73 — which gold clicks independently exonerate.
One 0.13 s error cascaded into two wrong verdicts and manufactured a phantom.
Replaced with an order-preserving assignment; window −0.25..2.0. Coverage on that
file 11/17 → 12/17. **Every coverage figure quoted before this fix is void.**

`tools/event_audit.py` adjudicates hits and landings against the clicks. It runs
on **yt_rally2 only** — gold is a uniform grid and the share of frames with a
decided label within ±3 is 64.7% there versus **5.5% on am_hard_utr**, the clip
with the worst false-fire. Two honesty properties: an event with no decided label
within k leaves the *denominator*; and landings that coincide with a hit
(5 of 12 here — every shot carries a `bounce_t_s` whether or not a bounce was
detected) leave the landing denominator, because counting both lists naively
reported the single t=26.6 phantom twice.

Baseline at this commit — yt_rally2, shipped `frame_step`:

    per-frame FF 23.1% at 72.5% recall | ghost 6/26 (5 solid, 1 faded) |
    phantom hits 1/8 | phantom landings 1/4 | surplus shots 3/12 (1 conf) |
    HUD 9/17

Power, stated up front: n=8 adjudicable hits; 2/12 carries a 95% Wilson CI of
[5%, 45%]. A phantom-rate claim needs the raw **count** to move by ≥3.

### Step 2 — the tally. The confusers MOVE.

All 71 raw false locks on human-labelled no-ball frames, all six gold clips,
viewed as cross-haired crops (`tools/inspect_false_locks.py --contact-sheet`).
The pooled 34.8% reproduces `data/output/gold_v21_e6.txt` clip for clip.

| what it fired at | n | % |
|---|---|---|
| **racquet** | 22 | 31.0% |
| **player** | 20 | 28.2% |
| background | 8 | 11.3% |
| fence | 7 | 9.9% |
| court_line | 5 | 7.0% |
| court_surface | 4 | 5.6% |
| held_ball | 2 | 2.8% |
| signage | 2 | 2.8% |
| net | 1 | 1.4% |

**Moving with a person 59.2% · static scenery 38.0% · real ball not in play 2.8%.**
Through the shipped chain (3 calibrated clips, `--frame-step 1`) 24 of 103
survive at 23.3% and the mix barely shifts: 54.2% / 45.8% / 0%.

A correction made mid-analysis, recorded because it reversed the answer:
am_hard_utr has a tight image-space cluster (5 locks in an 11×14 px box across
frames 9666–28531) and on a fixed camera that reads as a world-fixed object.
First pass called it spare balls at the net base. **Wrong** — frames 12338–12350
show it sweeping upward with the ball-feeder's arm. It is the light-coloured head
of a swung racquet. Classification is data:
`data/gold/false_lock_classes.json`.

**Step 5 (motion attention) is SKIPPED, on this evidence.** The brief conditions
it on the survivors being static or low-motion. They are not. The largest single
class — a racquet head at 31% — is a ball-sized, frequently ball-coloured object
travelling on an arc, which is precisely what a motion-difference gate cannot
separate from a ball. `_ballnet.MotionPrompt` stays untrained.

**Step 4's mining criterion needs rethinking, not just re-running.** "A lock that
does not move for several frames is provably a fixture" reaches at most the 38%
scenery slice, and the kinematic alternative (never joins a multi-frame track) is
no better — a swung racquet forms a perfectly smooth track. The signal that
separates 59% of these is that they are **attached to a person**, and the
pipeline already runs pose. Recorded for a future session; the parity re-mine is
still worth doing and the gap is wider than the brief states — four dirs are
under-mined, not two: `yt_am_dbl_classb` 3%, `yt_col_hard_zheng` 6%,
`yt_ewqSn18xdsY` 9%, `yt_tC0z7FYvMks` 9%, against a legacy tier of 15–26%.

Nothing here is a live-ball problem: stationary real balls are 2.8% raw and 0%
through the chain.

### Step 3 — the score-threshold sweep, done for the first time.

`score_thresh = 0.5` was hardcoded in four places, threaded from no caller,
exposed by no CLI, and absent from the provenance stamp. It is now a dial on
`eval_detector_gold`, `eval_model_filters`, `ball_perception`, `tune_suppress`
and `run.py analyze`, and it is stamped and mismatch-checked.

**The sweep costs one GPU pass, not one per threshold.** `detect()` takes the
heatmap argmax and only *then* compares to the threshold, so the peak's position
is threshold-independent; recording the peak value makes every threshold an
in-memory comparison. Exact, not approximate — pinned by
`tests/test_score_thresh.py` against a real per-threshold pass, and the swept
0.50 row reproduces `gold_v21_e6.txt` digit for digit on all six clips.

Raw detector, `ballnet_v21`, pooled over all six gold clips (1201 ball / 204
no-ball frames), vs human gold clicks:

| thresh | recall | far_px | far_geo | false-fire | recall−ff |
|---|---|---|---|---|---|
| 0.30 | 71.3% | 71.5% | 74.5% | 46.6% | 24.7 |
| 0.40 | 70.4% | 70.0% | 73.4% | 38.7% | 31.7 |
| **0.50** | **69.4%** | **68.8%** | **72.5%** | **34.8%** | **34.6** |
| 0.60 | 68.0% | 67.8% | 70.8% | 30.9% | 37.1 |
| 0.70 | 66.1% | 65.9% | 69.1% | 23.0% | 43.1 |
| 0.80 | 62.9% | 60.8% | 65.1% | 16.7% | 46.2 |
| 0.90 | 56.0% | 53.2% | 58.8% | 9.8% | 46.2 |

There is a real curve and 0.5 is not on its knee: 0.5 → 0.7 buys 11.8 points of
false-fire for 3.3 of recall, and the trade turns bad after (0.8 → 0.9 is 6.9 for
6.9). `recall − false-fire` is a **shortlisting device only** — it cannot see
whether a lock became a drawn ball or an event. 0.6 and 0.7 went to the chain
A/B and were picked on the product metric.

#### Chain A/B verdict: MEASURED NEGATIVE. The threshold stays at 0.5.

Baseline, 0.6 and 0.7 through the full shipped chain, all three calibrated clips
at `--frame-step 1` (so every gold label is scoreable — am_hard_utr is 48.6% odd
frames), same commit, same session. Gates applied by `tools/score_thresh_gates.py`
in their pre-registered order.

| arm | clip | recall | far_geo | false-fire | ghost fires |
|---|---|---|---|---|---|
| base | am_hard_utr | 54.9% | 61.0 | 17.0% | 9 (5 solid, 4 faded) |
| base | yt_match40 | 65.2% | 66.9 | 29.2% | 7 (3 solid, 4 faded) |
| base | yt_rally2 | 75.2% | 72.6 | 30.8% | 8 (4 solid, 4 faded) |
| 0.6 | am_hard_utr | 51.4% | 57.4 | 13.2% | 7 (4 solid, 3 faded) |
| 0.6 | yt_match40 | 64.7% | 66.2 | 20.8% | 5 (1 solid, 4 faded) |
| 0.6 | yt_rally2 | 74.0% | 70.9 | 26.9% | 7 (2 solid, 5 faded) |
| 0.7 | am_hard_utr | 46.9% | 52.5 | 13.2% | 7 (3 solid, 4 faded) |
| 0.7 | yt_match40 | 60.9% | 61.9 | 20.8% | 5 (1 solid, 4 faded) |
| 0.7 | yt_rally2 | 69.0% | 63.1 | 26.9% | 7 (0 solid, 7 faded) |

Pooled recall over 617 labelled ball frames: **66.5% → 64.8% at 0.6 → 60.3% at
0.7.** Both **FAIL Gate 1** (limit −1.0 pt pooled, −2.0 pt far_geo on any clip):
0.6 loses 1.6 pooled and 3.6 far_geo on am_hard_utr; 0.7 loses 6.1 pooled and
5.0–9.5 far_geo on **every** clip.

**Gate ordering earned its keep.** At 0.6 the ghost-ball criterion (Gate 2)
would have PASSED — solid fires fall on all three clips, 5→4, 3→1, 4→2, and rise
on none. Reading the table in any other order, that looks like the win this
session was for. Gate 1 is first precisely so a recall regression cannot be
rationalised away by a precision number that improved.

**Raising the threshold does not remove ghost balls**, because `smooth_forecast`
fills the gaps a stricter detector creates. On yt_rally2 at 0.7 the chain reaches
**zero** false fires after `suppress_false_locks` — tracker-gates-only false-fire
falls 30.8% → 3.8%, suppression takes it to 0 — and then the smoother puts back 7.
Total ghosts move 8 → 7, which is noise, while recall pays 6.2 points and far_geo
9.5. The per-frame false-fire number (30.8% → 26.9%) makes 0.7 look like a modest
win; the ghost count shows it is not one.

> **RETRACTED — the sentence that used to follow.** This section originally
> concluded "the ghost ball is not a detector-precision problem at all — it is the
> smoother interpolating through dead time", on the strength of that 0.7 arm
> reading **0 solid, 7 faded**. That was measured at `--frame-step 1`, where
> fps_eff is 60 and `max_gap_s = 0.4` bridges **24** frames. The shipped config is
> fps_eff 30 and bridges **12**. At the shipped rate the same clip reads **5
> solid, 1 faded** — the opposite composition. This is the identical trap
> CLAUDE.md already records from E6 part 3, and it was walked into anyway. The
> A/B verdict above is unaffected: all three arms were measured at step 1, so the
> comparison is internally valid and 0.6/0.7 do fail Gate 1.

`score_thresh` stays at **0.5**. The dial, the provenance stamp and the sweep
tooling ship anyway — the value of 0.5 is now measured rather than inherited, and
the next person can re-sweep in one GPU pass.

Confirmed no-op: re-running `run.py analyze` on yt_rally2 at the shipped settings
after all of this session's `ball.py` changes reproduces the pre-change
match.json exactly — same 12 shots, 6 rallies, identical stats and score.

### Steps 4 and 5 — not run, and why

- **Step 5 (motion attention v4): skipped on Step 2's evidence**, as the brief's
  own condition directs. The survivors move.
- **Step 4 (re-mine + v3.1): deferred, and its criterion needs redesign first.**
  The parity gap is real and wider than the brief states, but re-mining to parity
  with the *existing* static-lock criterion would only deepen a negative set that
  Step 2 shows addresses ≤38% of the confusers. The pose-proximity criterion is
  the change worth making, and it is a session of its own.

### Step 3, follow-on — the smoother gap policy is a SECOND measured negative

`smooth_forecast`'s `max_gap_s = 0.4` had also never been swept. Like the
suppress parameters and unlike the score threshold it lives at the *end* of the
chain, so one perception pass scores every value (`tools/tune_smoother.py`).

Swept at each clip's **shipped** frame step this time, not step 1. Pooled over
532 scoreable ball frames and 74 no-ball frames on the three calibrated clips
(am_hard_utr contributes only 90 of its 175 ball and 24 of its 53 no-ball frames,
because at the shipped step=2 its 48.6%-odd labels are unscoreable):

| max_gap_s | pooled recall | Δ recall | worst Δ far_geo | ghost | solid | faded |
|---|---|---|---|---|---|---|
| 0.00 | 61.1% | −5.8 | −8.6 | 11 | **11** | 0 |
| 0.10 | 61.1% | −5.8 | −8.6 | 10 | **9** | 1 |
| 0.15 | 61.1% | −5.8 | −8.6 | 12 | **9** | 3 |
| 0.20 | 62.0% | −4.9 | −6.1 | 13 | **9** | 4 |
| 0.30 | 66.2% | −0.8 | −2.8 | 16 | **9** | 7 |
| **0.40** (shipped) | **66.9%** | — | — | 19 | **9** | 10 |

Every value fails Gate 1. **0.4 stays.**

**The invariant is the finding: solid fires are 9 at every setting from 0.10 to
0.40.** The gap policy cannot touch them — they are the detector genuinely firing
on a racquet, a player or a fence during dead time, which is precisely the Step 2
tally. All the policy moves is the faded count (10 → 0), and it charges 5.8 points
of pooled recall and up to 8.6 of far_geo to do it. (At 0.00 solid *rises* to 11:
shorter gaps end segments more often, so more detections get re-seeded and emitted
as real.)

So the ghost ball at the shipped config is **19 fires over 74 no-ball frames, 9
solid and 10 faded**, and the two post-hoc knobs now swept — detector threshold
and smoother gap — each trade recall roughly one-for-one against the faded half
while leaving the solid half untouched.

**Nothing downstream of the detector can remove a solid ghost.** The only thing
that stops the detector firing on a racquet head is a detector trained not to,
which makes Step 4 with a **pose-proximity** criterion the next real work — not a
filter, not a threshold, and not motion attention.

### For the next session

1. **Pose-proximity hard-negative mining.** Addresses the 59% and the 9 immovable
   solid ghosts. Calibration-free, so all 13 training clips qualify. This is the
   only remaining lever the evidence supports.
2. Re-mine the four under-mined training dirs to parity — after (1), not before;
   deepening the current static-lock negatives addresses ≤38% of the confusers.
3. `mine_hard_negatives.py` hardcodes `"detector": "BallNet (weights/ballnet.pt)"`
   in its provenance regardless of what actually loaded. Fix before any re-mine.
4. Standing measurement rule, now violated twice in this repo: **never quote a
   `--frame-step 1` number as shipped behaviour.** Use step 1 only for A/B deltas
   and for clips whose gold parity demands it, and re-measure at the shipped step
   before drawing a mechanism conclusion.
