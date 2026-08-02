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

### Step 0 — cleared before the session started

The provenance fix landed with the maintenance sweep: `mine_hard_negatives.py` now
reports the resolved checkpoint path + sha256 + `score_thresh` + device instead of the
hardcoded `"BallNet (weights/ballnet.pt)"`. The nine eval-ladder `.txt` results are
committed. So this session began at Step 1.

### Step 1 — MEASURED NEGATIVE. Pose proximity fails its gate, and not narrowly.

`tools/eval_pose_proximity.py`. Scored against human labels only: **44 person-attached
locks** (racquet 22, player 20, held_ball 2 — 62.0% of the 71 human-classified false
locks in `data/gold/false_lock_classes.json`) for CATCH, and **1201 frames where a human
clicked a real ball** across the six gold clips for COLLATERAL.

**Correction to the brief's population:** collateral is over **1201** ball clicks, not
the 617 the plan quoted. 617 is the CHAIN-level count (calibrated clips, scoreable at
the shipped frame step); a mining criterion is applied at detector level, on every
labelled ball frame, so 1201 is the population that can actually be harmed.

Sweeps: radius × keypoint set × two sizing modes (absolute px normalised to 720p, and
body-relative — a multiple of that person's own bbox height, which is depth-adaptive for
free). Best catch achievable **at or under the 5% collateral ceiling**:

| pose preset | best catch at collateral ≤ 5% | max catch anywhere | its collateral |
|---|---|---|---|
| fast (shipped) | **11.4%** | 38.6% | 22.5% |
| accurate (yolo11x@1920) | **11.4%** | 43.2% | 23.5% |

The gate wanted ≥ 60% catch at ≤ 5% collateral. It is off by a factor of five, and the
curve has no knee — catch and collateral rise together at roughly 2:1 across every
radius, keypoint set and mode tested.

**It is not a pose-quality limitation.** `accurate` was run as the pre-registered
sensitivity check and moved max catch 38.6 → 43.2% while *raising* collateral. Ruled
out.

### Why it fails — the racquet is not on the skeleton

Median distance from each lock to the nearest upper-body keypoint, body-relative
(pose=accurate):

| class | n | median | ≤ 0.20 bh | ≤ 0.50 bh |
|---|---|---|---|---|
| **racquet** | 22 | **2.12** | 36% | 41% |
| player | 20 | 0.76 | 25% | 35% |
| held_ball | 2 | 0.24 | 50% | 100% |

The largest confuser class sits **two body heights** from the nearest keypoint. That is
geometry, not noise: a pose skeleton has no racquet, and at contact the head of a 68 cm
racquet at arm's length is frequently further from the wrist than the ball is. Proximity
to a skeleton cannot describe the thing doing the confusing.

### The control that rules out the alternative explanation

Pose finds exactly **one** person on 1006 of 1272 frames, and none on 53. That is
structural, not a bug — five of the six gold clips are low or close cameras where the
far player is out of frame or unresolvable (`am_hard_utr` is the 1.74 m mount that does
not reach the net at 11.885 m). So most locks were scored against a skeleton covering
one of the two people on court, which is a confound.

`gold_shell` is the exception: 2+ people found on **192 of 201** frames. Restricted to
it:

| radius | catch | collateral |
|---|---|---|
| 0.20 bh | **20.0%** | 6.0% |
| 0.30 bh | **20.0%** | 9.2% |
| 0.50 bh | **20.0%** | 19.6% |

**Catch is flat at 20.0% while collateral more than triples.** With complete pose, eight
of ten person-attached locks are beyond half a body height from every upper-body
keypoint and no radius reaches them. The confound is real but it is not the cause — the
criterion fails on its own merits.

Also worth recording: on `am_hard_utr` collateral is **14.9% at R = 0.20 bh**, because on
a 1.74 m camera the ball spends most of its visible life close to a player's body in
image space. Any person-proximity rule is most dangerous exactly on the amateur footage
this project targets.

### Verdict and what it means for Steps 2–3

**Steps 2 and 3 are NOT run**, per this brief's own gate. Do not mine pose-proximity
negatives, and do not train v3.1 on them: at any setting that catches a useful share of
racquets, the same rule negates 20%+ of the frames where a human saw a real ball.

`mine_hard_negatives.py` is unchanged — no `--criterion` flag was added, because there
is no criterion worth adding. The static-lock miner still addresses only the 38% static
share, and that limitation stands unresolved.

**The next lever is not a proximity rule.** The confuser that matters is the racquet, and
nothing in the current stack localises a racquet. Candidates, in order of how well the
evidence supports them:

1. **Detect the racquet**, then negate locks on it. A racquet is a distinct, learnable
   object; the skeleton is the wrong proxy for it. Needs racquet labels, which the
   project does not have.
2. **Extended-limb ray** — the racquet lies roughly along elbow→wrist extended by
   ~0.5–1.0 body heights. Cheap to test with the pose already cached by
   `eval_pose_proximity.py`, and testable against the same 44 locks before any training.
   Note the racquet median of 2.12 bh sets a low prior on this working.
3. Accept that the 9 solid ghosts are the detector's floor at this training-data scale,
   and spend the effort on far-court recall instead, where E6 showed the gate — not the
   detector — was deleting real balls.

**Do not re-propose pose proximity** without new evidence that changes one of the two
measurements above.

### Artefacts

- `tools/eval_pose_proximity.py` — the gate, re-runnable; pose cached per clip and
  preset so a re-sweep is free.
- `data/output/g_falselocks_raw.json` — the 71 raw locks with human classes
  (reproduced Session F's tally exactly: 71 locks / 204 no-ball frames / 34.8%).
- `data/output/g_pose_proximity{,_accurate}.json` — both sweeps with `measured_against`.
