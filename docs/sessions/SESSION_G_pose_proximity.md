# Session G — pose-proximity hard negatives: the last lever the evidence supports

## Goal

Stop the detector firing on racquets and players. Session F proved this cannot be
fixed downstream, and named the one remaining lever. Ship a detector that removes
**solid** ghost balls without giving back recall.

## Why now

Session F ended on an invariant, not an opinion. The ghost ball at the shipped
config is **19 fires over 74 no-ball frames — 9 solid, 10 faded**. Two independent
post-hoc knobs were swept for the first time (detector score threshold, smoother
`max_gap_s`), and both did the same thing: traded pooled recall roughly one-for-one
against the *faded* half while leaving the solid 9 **completely untouched** at every
setting. The solid count is 9 at `max_gap_s` 0.10, 0.20, 0.30 and 0.40 alike.

That is the detector genuinely firing on a racquet, a player or a fence during dead
time. Nothing downstream can remove it. And Step 2 classified all 71 raw false locks
by eye: **59.2% move with a person** (racquet 31.0%, player 28.2%), 38.0% static
scenery, 2.8% a real ball not in play. The miner that built the current hard
negatives only recognises a *static* lock as safe — so the entire existing negative
set addresses at most that 38%, and the majority class has never been mined at all.

Pose-proximity is calibration-free, so all 14 training clips qualify, and the
pipeline already runs pose. This is the change Session F deferred, and it is a
session of its own.

## Baseline to beat (committed evidence, vs human gold clicks)

| Measure | Value | Where |
|---|---|---|
| Detector pooled recall (v21, 1201 ball frames) | **69.4%** | CLAUDE.md E6 |
| Detector far_px / far_geo | 68.8% / 72.5% | CLAUDE.md E6 |
| Detector false-fire | 34.8% | CLAUDE.md E6 |
| Detector composite (`hit@10 − false-fire`) — **v21** | **23.7** | Session F Step 4 |
| Detector composite — v3 (the regression) | 20.9 | Session F Step 4 |
| Chain pooled recall (617 labelled ball frames) | 66.5% | Session F Step 3 |
| **Ghost ball (shipped)** | **19 fires / 74 no-ball frames = 9 solid + 10 faded** | Session F Step 3b |

The number this session exists to move is **9 solid**. Recall and composite are the
things it must not break.

## Two findings that make Step 1 nearly free

1. **The committed perception caches already carry pose.** Every
   `data/output/*.perception.json` has `near_kpts` / `far_kpts` — 17 COCO keypoints
   per player per frame as `[x, y, conf]`, wrists at indices 9 and 10. No schema work.
2. **The validation set already exists and is human-made.**
   `data/gold/false_lock_classes.json` holds all 71 raw false locks across 6 gold
   clips, each hand-classified into 9 categories, as `clip → {frame: class}`. The
   lock coordinates are recoverable — `detect()` is deterministic and pinned by tests.

So the criterion can be scored against human labels **before** any GPU time is spent.
Pose is only needed at ~71 false-lock frames plus the gold ball-click frames — a few
hundred frames, not a re-perception of every clip.

## Step 0 — Hygiene, 15 minutes, blocks the re-mine

`backend/mine_hard_negatives.py` writes
`"detector": "BallNet (weights/ballnet.pt)"` into its provenance **regardless of what
actually loaded**. Every existing `hard_negatives.json` therefore carries a possibly
false attribution — the current sets were mined while `ballnet.pt` was default, so they
are probably right, but "probably" is not provenance. Fix it to report the real path
and sha256 before mining anything new, or this session's outputs inherit the same lie.

Also commit the 9 eval-ladder `.txt` files under `data/output/` (9 KB). `.gitignore`
re-includes `!data/output/*.json` but not `*.txt`, so results the docs cite by name —
`data/output/gold_v21_e6.txt` is quoted in CLAUDE.md — are not in the repo. Add
`!data/output/*.txt`.

## Step 1 — Validate the criterion against human labels (do this FIRST)

Write `tools/eval_pose_proximity.py`. For a radius `R` and a keypoint set `K`, the
criterion is: *a lock within `R` px of any keypoint in `K` on either player is
person-attached*.

Score it two ways on the same sweep of `R`:

- **Catch rate** — of the 71 human-classified locks, what fraction of the
  `racquet` + `player` + `held_ball` classes (59.2% + 2.8%) does it flag? This is the
  win.
- **Collateral rate** — of the **617 human-clicked real ball positions**, what fraction
  falls inside the same radius? This is the cost, and it is not small: a real ball at
  contact is *by definition* next to a wrist. Report it split by "within 5 frames of a
  detected hit" vs not.

Sweep `R` and `K` together. `K` candidates, narrowest first: wrists only (9, 10);
wrists + elbows (7–10); all upper-body (5–10). Scale `R` by `res_scale =
frame_height/720` — this repo has been burned twice by unscaled pixel thresholds.

**Gate:** a configuration must catch **≥ 60%** of person-attached locks while keeping
collateral on real balls **≤ 5%**. If nothing clears that, the criterion is dead —
**say so, write the numbers into the Results section, and stop.** Do not proceed to
mining on a criterion that failed its own gate. A negative here is a real result and
costs one afternoon instead of a GPU day.

## Step 2 — Mine, with the guard that keeps real balls out

Extend `mine_hard_negatives.py` with `--criterion {static,pose,both}`, keeping
`static` as the default so existing behaviour is bit-identical and re-runnable.

Pose mining needs YOLO-pose over the `data/ball_dataset/*/` JPGs (26,293 labelled
frames across 14 clips). Cache the keypoints per clip — that pass should happen once,
not once per radius.

Two guards, both mandatory:
- The existing `LABEL_NEAR_PX = 40` rule — never negate a lock sitting on the clip's
  pseudo-label ball.
- A **hit-window exclusion** derived from Step 1's collateral split: skip frames within
  N frames of a labelled ball that is itself near a wrist. Without this the miner
  teaches the net to go blind exactly at contact, which is where speed measurement
  starts.

Do **not** mine "frames the pipeline decided had no ball" — that is the model grading
its own homework, and it is the rule this repo exists to keep.

Then re-mine the under-mined clips to parity in the same pass. Current fractions:
`yt_am_dbl_classb` 52 negatives on 2065 labels (**3%**) and `yt_col_hard_zheng` 136 on
2296 (**6%**), against 9–26% across the legacy tier — the quantified cause of the v3
regression. Target 15–20% per clip. **Order matters: widen the criterion first, then
re-mine.** Deepening the static set alone addresses ≤38% of the confusers, which is
exactly the mistake Session F declined to make.

## Step 3 — Train v3.1 and score it honestly

    cd backend && .venv-train/Scripts/python.exe train_ballnet.py \
        --epochs 40 --out weights/ballnet_v31.pt --device cuda

`train_ballnet.py`'s gold guard derives excluded clips from the `data/gold` manifests,
so the gold clips stay out of training — verify that in the run log, do not assume it.

**Gate, in this order — the first one that fails kills the candidate:**
1. **Recall gate first.** Pooled chain recall must not drop below the 66.5% baseline by
   more than 1 point. Ordering this first is what saved the score-threshold decision in
   Session F: at 0.6 the ghost-ball gate would have *passed*.
2. **Composite.** `tools/eval_detector_gold.py` composite must beat v21's **23.7**.
3. **The number this session is for.** Solid ghost fires must drop below **9** on the
   3 calibrated clips at each clip's **shipped** frame step.

## Step 4 — Independent cheap win, if time remains

`data/demo30_pts.json` has a **565 px** fit residual — the worst in the repo by two
orders of magnitude, a 0.2 m camera height, and floored speeds. It is also the
canonical dashboard clip. Re-calibrate it with `tools/court_setup_server.py` and audit
with `tools/validate_new_clip.py --audit`; known-good clips sit under 2.5 px. This is
unrelated to the ball work, so it is safe to defer or hand to a separate session.

## Measured dead ends — do NOT re-propose

Session F's list stands in full (court+vertical cone gate, scaling
`static_radius_px`, the live-ball filter, detector fusion, dead-time silence
negatives, depth-aware Kalman noise, `seg_gap_s`). Session F added three more:

- **Motion attention (v4)** — skipped on evidence, not on effort. It suppresses
  *static* confusers; the majority class moves on an arc. Do not revive it without new
  evidence that the confuser mix has changed.
- **Raising the score threshold** — 0.6 and 0.7 both fail the recall gate, and at 0.7
  the smoother puts 7 fires back. 0.5 stays.
- **Shrinking `max_gap_s`** — every value 0.00–0.30 fails the recall gate and none
  touches a solid ghost.

## Standing rules for this session

- **Never quote a `--frame-step 1` number as shipped behaviour.** This repo has drawn
  two wrong mechanism conclusions that way, the second *after* writing the rule down.
  Use step 1 for A/B deltas only, and re-measure at the shipped step before concluding.
- Gold labels are TEST-only. Never train on them.
- State in one sentence what every number was measured against.
- `far_geo` on `am_hard_utr` is recall, never measurement — a 1.74 m camera is
  measurable to only 7.5 m of 23.77. Only compare it between clips of similar depth.
- Use `py`, not `python` — the Store shims are broken on this machine.

## Verification

1. `py -m pytest backend/tests/` — 209 tests pass.
2. Step 1 gate table written into Results, with the human-label counts it was scored
   against, whether it passed or failed.
3. `tools/eval_detector_gold.py` composite for v31 vs v21, same command, both rows shown.
4. Ghost-ball solid/faded split at each clip's shipped frame step, before and after.
5. End-to-end `run.py analyze` on `yt_rally2` still produces a sane match.json.

## Kickoff prompt

> Read CLAUDE.md, ML_PRACTICES.md and ML_PLAYBOOK.md, then
> docs/sessions/SESSION_G_pose_proximity.md. Start at Step 0, then do Step 1 and show
> me the gate table before writing any mining code. If Step 1 fails its gate, stop and
> tell me — do not proceed to Step 2.

## Results

*(fill in as each step lands — numbers, what they were measured against, and the
verdict including negatives)*
