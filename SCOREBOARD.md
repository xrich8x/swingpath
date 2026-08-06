# SCOREBOARD.md — the stack, the method, and what has actually worked

**This file is the living record. Update it in the same commit as the work it describes.**

CLAUDE.md's Status section is *chronological* — it tells you what happened in which
session. This file is the *consolidated* view: the stack we build on, the method we
hold ourselves to, and a flat list of what has and has not moved a number. If you
want the story, read CLAUDE.md. If you want the state of play, read this.

**This is enforced, not remembered.** `.claude/hooks/scoreboard-guard.sh` runs before
every `git commit`: if the commit changes code (`backend/`, `tools/`, `frontend/src/`,
`mobile/`, `ball_physics/`) and SCOREBOARD.md is not also modified, the commit is
refused with a reason. Doc-only, data-only and config-only commits pass untouched. For
a change that genuinely moves no number — a typo, a rename, a revert — put
`[no-scoreboard]` in the commit message.

**When to update:**
- shipped something that moved a measured number → add a row to **What has worked**
- measured something that did not work → add a row to **What has not worked**, with
  the number and the reason. A negative is a result; recording it is what stops it
  being re-proposed in three months.
- changed the stack (a model, a runtime, a piece of hardware) → update **The stack**
- got burned by a process mistake twice → add it to **Traps**

---

## The stack

| Layer | What we use | Notes |
|---|---|---|
| Ball detection | **BallNet v21** — in-house TrackNet-style heatmap CNN | 512×288 input, 3-frame stack, ~2 MB. Default detector. |
| Ball fallbacks | TrackNet (vendored), WASB | Kept for benchmarking; not the shipped path. |
| Player pose | YOLO-pose via ultralytics | `fast` preset (yolo11m@1280) default; `accurate` (yolo11x@1920) for the far player. |
| Court | Classical line-fit + consensus, CourtNet seam | Manual fallback via the setup tool; auto-detect is fragile on low cameras. |
| Geometry | Homography, ballistic fits — closed-form | Never learned. This is a hard architectural boundary. |
| Smoothing | Constant-acceleration Kalman + RTS smoother | Image space. Interpolates only, never extrapolates. |
| Backend | Python 3.12, NumPy/SciPy, OpenCV, PyTorch | `backend/.venv` (CPU) and `backend/.venv-train` (CUDA). |
| Frontend | React + Vite | Reads `match.json`; the schema is the only contract. |
| Training HW | One RTX 5060 Ti | **Single GPU — one job at a time.** Enforced by `lab_jobs.py`. |
| Shipped inference | CPU-first, ~0.7–1.1 s/frame | Offline-first by design; there is no real-time requirement. |
| Mobile | ONNX + int8, argmax baked into the graph | 0.9 MB / 11 MB. Call logic ported to JS, verified bit-identical. |

**Target footage:** amateur phone video on a fence or tripod, 720p–1080p, 30–60 fps,
often a low mount. Measured mounts: **1.38 m** and **1.74 m**. That is the constraint
that shapes everything — a low camera limits *measurable depth* to 22–32% of the court.

---

## The method

This is how work gets decided here, and it is the reason the numbers below can be
trusted. The full discipline is in ML_PRACTICES.md; this is the working summary.

1. **Score only against independent human labels.** 1201 human ball clicks and 204
   no-ball frames across 6 clips. Test-only, never trained on. A model never grades
   its own homework.
2. **Pre-register the gate before running the experiment.** Write the threshold down
   first, then measure. Do not move the gate to fit the result — Session G part 4 fails
   at 54.5% against a 60% gate and stays failed.
3. **Order the gates so the expensive one is checked first.** Recall before ghost-ball.
   In Session F the ghost-ball gate would have *passed* at threshold 0.6; only the
   recall gate, deliberately ordered first, caught it.
4. **Diagnose before adjusting.** Per-gate miss counters, not just success counts. That
   is what showed far-court was detector-shaped rather than gate-shaped.
5. **State what every number was measured against, in one sentence.** Every eval tool
   emits a `measured_against` field.
6. **A refactor must prove it changed nothing.** Re-run and diff, or pin with a test.
7. **Record negatives with their reason.** A dead end nobody wrote down gets
   re-proposed.

---

## What has worked

Ordered roughly by how much it moved. Every number is against human gold labels.

| Change | Effect | Where |
|---|---|---|
| **Hard-negative mining + retrain** (v21 became default) | no-ball false-fire pooled **14% → 6.0%** at flat recall | E5+ |
| **Occlusion augmentation + visibility-weighted loss** | gold **82.9 → 84.9**, occluded **84.2 → 89.7** | verified win |
| **Fixing the court gate for resolution** | far-ball retention at 1080p **15.4% → 100%** | E6 |
| **`suppress_false_locks`** (persistence + min-segment, image space) | false-fire **61.5% → 15.4%** on yt_rally2; costs 5.4–10 pts recall | E5+ |
| **Kalman smooth + forecast** | jerkiness **9.9 → 4.1 px/frame²** (2.4× smoother) at −1.6 pt hit@10 | E5+ |
| **Static-lock gate** (a lock that holds still is a fixture) | **zero** static junk locks; ball-only coverage went *up* | 2026-07-05 |
| **Scaling every pixel threshold by `frame_height/720`** | exact no-op at 720p, stops silent far-ball deletion at 1080p | E6 part 2 |
| **Roll-aware court snap** | 6.9 → **1.8 px** on a −2.4° clip; no-op when level | court work |
| **demo30 re-calibration** | **564.6 px → 0.5 px** fit residual — lowest in the repo | G part 2 |
| **Calibration audit + `_audit` stamp** | degenerate calibrations now warn on load instead of failing silently | G part 2 |
| **The gold benchmark itself** | turned every claim in this project from an opinion into a number | Session 2 |
| **Court TEST/TRAIN split + leak guard** | court numbers became measurable at all — 17 of 20 gold clips had been in training | 2026-08-06 |

---

## What has not worked

**Do not re-propose these.** Each was tried here and measured.

| Idea | What happened |
|---|---|
| Court + vertical cone gate for false alarms | Real far balls and fixtures overlap in court coords (real span −229..+1667 m). No envelope separates them. |
| Scaling the fixture radius 12 → 18 px | Halves false-fire (13.2 → 5.7%) but costs **4.3 pts** of far-court recall. |
| Offline live-ball trajectory filter | Net-negative once suppression runs; recall 50.2 → **40.5%**. Retired from the pipeline. |
| Detector fusion (TrackNet ∪ WASB) | Rescued **4 frames** and doubled the dominant cost. |
| Dead-time "silence" negatives | The wrong negatives. Confusers are not silence. |
| Depth-aware Kalman process noise | Median-referenced made false-fire **worse** (19 → 27%). |
| Raising detector score threshold | 0.6 and 0.7 both **fail the recall gate**; 0.7 removes ghosts the smoother puts straight back. |
| Shrinking smoother `max_gap_s` | Every value fails. Solid ghosts sit at **9 regardless** — the gap policy cannot touch them. |
| Motion attention (TrackNetV4) | **Skipped on evidence.** It suppresses *static* confusers; ours **move** (59.2% travel with a person). |
| Pose-proximity negative mining | **11.4%** catch at the 5% collateral ceiling vs a 60% gate. The racquet is **2.12 body heights** from the nearest keypoint — a skeleton has no racquet. |
| Racquet-box negation (COCO class 38) | **54.5%** catch at 4.5% collateral — 5.5 pts under gate. Right object, loose localiser. |
| Raising `acquire_bound_m` 4 → 10 m | Static analysis said free; end to end it bought +0.6 pt recall for +1.9 pt false-fire. |
| Blur augmentation alone | Dead end on its own; only pays off combined with occlusion work. |
| Lowering the court consensus bar 6/8 → 5/8 | **GATE FAILS.** Exactly one 5-vote clip exists and it is wrong by **68.7 px**, against 3.4–13.9 px for every clip at ≥6 votes. Nothing lands in the gap. The bar is empirically correct. |
| Improving CourtNet for auto-calibration | Wrong target. CourtNet is **Tier 2**; `courtfit` consensus is Tier 1 and beats it on this footage — CourtNet returns nothing on three clips courtfit nails at 8/8, 7/8 and 6/8. |

---

## Open, and what each is waiting on

| Item | Waiting on |
|---|---|
| **Far-court recall** (detector fires on nothing in 24–27% of frames) | A few hundred **human far-court labels**. Confirmed externally: label-efficient methods degrade *most* where visual cues are weakest. The Lab exists for this. |
| **9 solid ghost balls** | A detector trained not to fire on racquets. Next candidate: RacketVision 5-keypoint racket pose (MIT, weights released) — but its own finding warns that naive feature concatenation *degrades*, so it must condition the detector, not filter it. |
| **Bounce detection** | No true ball height from one camera. Unevaluated candidates: audio impact (module exists, unwired), monocular 3D. |
| **Speed coverage** | Downstream of ball recall. The −15% bias is average-vs-launch physics and must **never** be corrected away. |
| **Court auto-detection** | **Closed as a model problem.** Tier 1 (`courtfit` consensus) auto-accepts **11 of 20** gold clips with a perfect precision record (3.4–13.9 px, zero wrong courts ever accepted); the 6/8 bar is verified correct. The remaining 9 clips refuse, and refusal costs ~30 s in the setup tool. CourtNet (Tier 2, 20.2% held-out detect) is the weaker path and is not worth improving. |
| **8 court gold frames are mislabelled** | `am_indoor_hard1` frames 9204/10093/10982/11871/12760/13649/14538/15427 are marked `court: false` but plainly show a full usable court (3 of 3 inspected). Needs re-labelling in the Lab — a minute of human time. Until then that clip's `false%` is not a valid metric. |
| **Manual-correction UI** | Nothing. Needs no ML. Highest-value unbuilt product feature. |
| **Highlights / clip export** | Nothing. Self-contained, parallelisable. |

---

## Traps

Process failures this project has hit **more than once**. Each cost real work.

1. **Quoting a `--frame-step 1` number as shipped behaviour.** It doubles `fps_eff` and
   every time-threshold's frame count. Two wrong mechanism conclusions came from this —
   the second *after* the rule was written down. Use step 1 only for A/B deltas and for
   clips whose gold parity demands it.
2. **Trusting a stale cache.** Perception caches are calibration- and
   settings-dependent. A whole set of published figures was withdrawn over this.
   Re-perceive; the provenance stamp exists to catch it.
3. **Unscaled pixel constants.** Anything tuned at 720p silently deletes real balls at
   1080p. Scale by `frame_height/720` — except the fixture radius, where measurement
   says otherwise.
4. **A scorer that mis-aligns frames.** Gold frame `f` compared against track index
   `f//step` without checking `f` was processed understated the tracker for a whole
   session and forced a retraction.
5. **Measuring against a model instead of a human.** Every leaderboard this project
   built before the gold set was measuring its own reflection.
6. **Letting the test set into the training set.** The ball side has enforced a one-way
   gold/train split since Session 2. The COURT side never did: **17 of the 20
   hand-labelled court gold clips were also in `data/court_dataset/`**, and
   `train_courtnet.py` had no guard at all, so every figure in
   `data/gold/court_scores.md` was the model scored on its own homework. Fixed
   2026-08-06 with `data/gold/court_split.json` + `assert_no_court_gold_leak()`. The
   lesson generalises: a discipline enforced on one model is not enforced on the
   project. Check each new model for its own guard.
6. **Fanning out to parallel agents.** The bottleneck here is one GPU and one gold set,
   not context. Two multi-agent research runs burned ~971k tokens and returned **zero**
   results; the same research done inline took two searches and four fetches.
