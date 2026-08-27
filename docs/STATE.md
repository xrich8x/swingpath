# STATE.md - the state of play

**This file is the living record. Update it in the same commit as the work it
describes.** Split out of SCOREBOARD.md on 2026-08-26: the verdicts stayed here,
the mechanisms and war stories moved to [evidence/](evidence/).

**Never create a new markdown file to record a result.** A result is a row here plus
a file in evidence/. If you are about to write NOTES.md, FINDINGS.md, SESSION_N.md
or SUMMARY.md, you want one of those two places. New top-level docs require a line
in CLAUDE.md's doc map, and that file has a hard cap - so a new doc costs an old one.

**This is enforced, not remembered.** `.claude/hooks/state-guard.sh` runs before
every `git commit`: if the commit changes code (`backend/`, `tools/`, `frontend/src/`,
`mobile/`, `ball_physics/`) and this file is not also modified, the commit is refused.
Doc-only, data-only and config-only commits pass. For a change that genuinely moves no
number, put `[no-state]` in the commit message.

**When to update:** shipped something that moved a number -> a row in *What has worked*.
Measured something that did not -> a row in *What has not worked*, with the number and
the reason. Changed a model/runtime/hardware -> *The stack*. Got burned by a process
mistake twice -> [TRAPS.md](TRAPS.md).

**The one formatting rule**, and it exists because ignoring it cost three corrections:
an **Open** row may NOT restate a number another table owns - it cites the row instead.
One number, one home.

## How to read every number here

- **Measured against independent human labels**: 1851 ball clicks + 308 no-ball frames
  across 10 clips, test-only, never trained on. A model never grades its own homework.
- **One declared exception:** rows quoting a *HUD MAE* or *HUD speed error* are measured
  against SwingVision's burned-in MPH panel. Those are **agreement with another
  estimator, not accuracy**. `tools/synth_truth.py` is the compliant speed reference and
  the only source of absolute accuracy here. Do not add new HUD-referenced numbers.
- The full discipline, including the 11 working rules this file used to carry, is in
  [ML_PRACTICES.md](../ML_PRACTICES.md).

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

**Footage layout (reorganised 2026-08-20):** every source video lives under
`data/incoming/<surface>/` - **Clay 9, Hardcourt 38, Shell 6, Grass 4**, plus
`Raw - Do Not Process` (9 full-length downloads whose trims are already in the surface
folders; the eval skips it by rule, because sweeping both counts the same court twice).
`data/amateur_clips`, `data/train_clips`, `data/gold_clips` and `data/highlights` are gone.
**FILENAMES ARE NEVER CHANGED** - the ball gold-leak guard and `lineage.json` key on
basename, so a rename silently defeats both (trap T17); only directories moved.
`tools/backup_offmachine.py` TARGETS moved with the footage - a backup target pointing at
an emptied directory reports a clean backup while covering nothing. **One safety cue was
traded for documentation:** `data/gold_clips` used to keep gold videos out of the training
pool by LOCATION; filed by surface they now sit beside training footage, so
`data/incoming/README.md` lists all 19 gold files explicitly. The guard still catches a
leak (it derives from the manifests, not a folder) but a human has no visual warning.

**Target footage:** amateur phone video on a fence or tripod, 720p–1080p, 30–60 fps,
often a low mount. Measured mounts: **1.38 m** and **1.74 m**. That is the constraint
that shapes everything — a low camera limits *measurable depth* to 22–32% of the court.


---

## What has worked

Ordered roughly by how much it moved.

| Change | Effect | Evidence |
|---|---|---|
| **Calibration auditor finds videos recursively** | shell calibrations **0 pass / 5 fail -> 4 pass / 6 LOW-CAMERA / 0 fail**; residuals 41-117 px -> **0.0-2.5 px**, the best band in the repo | [evidence/making-the-calibration-auditor-find-videos-recursively.md](evidence/making-the-calibration-auditor-find-videos-recursively.md) |
| **Court refiner reach scales with resolution** (`max_move_px` 55 -> `55*w/640`) | **moves no number** (gold 12/20 -> 12/20); shipped as a correctness fix, an exact no-op on the gate | [evidence/scaling-the-court-refiner-s-reach-with.md](evidence/scaling-the-court-refiner-s-reach-with.md) |
| **Hard-negative mining + retrain** (v21 became default) | no-ball false-fire pooled **14% -> 6.0%** at flat recall | - |
| **Occlusion augmentation + visibility-weighted loss** | gold **82.9 -> 84.9**, occluded **84.2 -> 89.7** | - |
| **Fixing the court gate for resolution** | far-ball retention at 1080p **15.4% -> 100%** | - |
| **`suppress_false_locks`** (persistence + min-segment) | false-fire **61.5% -> 15.4%** on yt_rally2; costs 5.4-10 pts recall | - |
| **Kalman smooth + forecast** | jerkiness **9.9 -> 4.1 px/frame2** at -1.6 pt hit@10 | - |
| **Static-lock gate** | **zero** static junk locks; ball-only coverage went up | - |
| **Scaling every pixel threshold by `frame_height/720`** | exact no-op at 720p; stops silent far-ball deletion at 1080p | - |
| **Roll-aware court snap** | **6.9 -> 1.8 px** on a -2.4 deg clip; no-op when level | - |
| **demo30 re-calibration** | **564.6 px -> 0.5 px** fit residual - lowest in the repo | - |
| **Calibration audit + `_audit` stamp** | degenerate calibrations warn on load instead of failing silently | - |
| **The gold benchmark itself** | turned every claim in this project from an opinion into a number | - |
| **Synthetic ground truth** (`tools/synth_truth.py`) | the only **ABSOLUTE** accuracy here: line calls **95.9%**, bounce **0.75 m** median, drag **-21.7%** | [evidence/synthetic-ground-truth.md](evidence/synthetic-ground-truth.md) |
| **SwingVision scrub + trainer guard** | **83 pseudo-labels** sat inside overlay graphics; the guard refuses to train on an unscrubbed clip; keeps 11,104 of 11,187 labels | [evidence/swingvision-scrub-trainer-guard.md](evidence/swingvision-scrub-trainer-guard.md) |
| **`am_hard_utr` perception cache** | the clip that kills smoother tunings is testable at last - 14,499 frames, 10,840 locks, 120 shots / 79 rallies | [evidence/am-hard-utr-finally-has-a-perception.md](evidence/am-hard-utr-finally-has-a-perception.md) |
| **60 fps shipped as `--full-rate`** | **+5.8 pts** close-call accuracy at 1.5 m, arc reproj **148 -> 91 px**, against **2x perception time**. Opt-in; default unchanged | [evidence/60-fps-shipped-as-full-rate.md](evidence/60-fps-shipped-as-full-rate.md) |
| **The two JS mirrors are enforced, not asked for** | `tests/test_js_mirror_parity.py`; each guard **proved to fail** before being trusted | [evidence/the-two-js-mirrors-are-enforced-not.md](evidence/the-two-js-mirrors-are-enforced-not.md) |
| **Court TEST/TRAIN split + leak guard** | court numbers became measurable at all - **17 of 20** gold clips had been in training | - |
| **Camera-height curve** (`tools/height_curve.py`) | close calls **54% at 1.0 m -> 69% at 3 m -> 81% at 8 m** against a **56.2%** majority-class floor; bounce error 3.81 -> 0.37 m | [evidence/camera-height-curve.md](evidence/camera-height-curve.md) |
| **Frame rate isolated from detector dropout** | 30 -> 60 fps worth **+5.8 / +3.2 / +1.8 pts** at 1.5 / 3 / 12 m; bounce error **-24..-35%**. A *perfect* detector buys about the same | [evidence/frame-rate-isolated-from-detector-dropout.md](evidence/frame-rate-isolated-from-detector-dropout.md) |
| **Per-rally clips + highlights reel** (`run.py highlights`) | ffmpeg **stream copy**; deterministic ranking; the manifest records requested vs actual start | [evidence/per-rally-clips-highlights-reel.md](evidence/per-rally-clips-highlights-reel.md) |
| **Far court measured in METRES, not frame rows** | the `FAR_FRAC` proxy was wrong by **5-26x**; far-court queue **1,393 -> 2,677 gaps** off the same footage | [evidence/far-court-measured-in-metres-not-frame.md](evidence/far-court-measured-in-metres-not-frame.md) |
| **More labelled data, from more venues** | +57% frames buys **+5.6 pts** pooled recall (74.8 -> **80.4%**, 4.1 sigma), up on 9 of 10 clips. **False fire did not move. NOT shipped** - the chain test later failed | [evidence/more-labelled-data-from-more-venues.md](evidence/more-labelled-data-from-more-venues.md) |
| **The height guidance actually reaches the user** | `run.py check` + Court Setup tab now surface it; `check` calls `pipeline.calibrate_video` so it can no longer disagree with `analyze` (trap T15) | [evidence/the-height-guidance-actually-reaches-the-user.md](evidence/the-height-guidance-actually-reaches-the-user.md) |
| **Manual-correction UI** (Review tab + `run.py correct`) | edits FACTS only; score replayed through the one state machine. demo 2-5 -> 3-4; re-applying is a no-op | [evidence/manual-correction-ui.md](evidence/manual-correction-ui.md) |
| **Score and rally count stop pretending to be measured** | that layer has **no ground truth of any kind**; it now reports which rule split it - yt_rally2 **5 timeout / 0 tennis-rule** | [evidence/the-score-and-rally-count-stop-pretending.md](evidence/the-score-and-rally-count-stop-pretending.md) |
| **P/R/F1 at the field's threshold** | **reverses a verdict shipped hours earlier**: F1@4 **tracknet 57.8 / ours 48.5 / wasb 47.5**, TrackNet wins **9 of 10** clips. Ours is a recall-first detector, not a better one | [evidence/p-r-f1-at-the-field-s.md](evidence/p-r-f1-at-the-field-s.md) |
| **The environment that produced the numbers is written down** (`tools/freeze_env.py`) | exposed that the two venvs are an **opencv MAJOR version apart** - no experiment here has ever separated device from libraries | [evidence/the-environment-that-produced-the-numbers-is.md](evidence/the-environment-that-produced-the-numbers-is.md) |
| **CourtNet training seeded** | **no number moved**; removes a confound from the *next* A/B (trap T10) | [evidence/courtnet-training-seeded.md](evidence/courtnet-training-seeded.md) |
| **`distance_run_m` stops inventing a number** | the dashboard read a confident **0.0 m** for player B integrated over **0.0%** coverage. Now **None below the >=50% bar, never 0.0**, and refused outright in doubles | [evidence/player-movement-stats-stop-inventing-a-number.md](evidence/player-movement-stats-stop-inventing-a-number.md) |
| **BallNet v21 vs TrackNet vs WASB, re-dated** | pooled hit@10 **60.8 / 57.9 / 49.3** - **+2.9 pts, not the +10.5** an undated comment claimed; TrackNet wins outright on 2 of 10 | [evidence/ballnet-v21-vs-tracknet-vs-wasb-finally.md](evidence/ballnet-v21-vs-tracknet-vs-wasb-finally.md) |

---

## What has not worked

**Do not re-propose these.** Each was tried here and measured.

| Idea | Verdict | Evidence |
|---|---|---|
| **Building the court quad from the DETECTED LINES** | **Wrong in principle, not mis-tuned** - under perspective the two doubles sidelines converge, so they form no angular cluster. Best constructed quad **68-256 px** from truth vs the lattice's 7-20 | [evidence/building-the-court-quad-from-the-detected.md](evidence/building-the-court-quad-from-the-detected.md) |
| **Snapping a near-correct court onto the detected lines** | median distance from truth: seed 9.8 -> refiner **8.4** -> snap **70.5**. Needs JOINT line-to-model assignment, untested here | [evidence/snapping-a-near-correct-court-onto-the.md](evidence/snapping-a-near-correct-court-onto-the.md) |
| **Raising `topk` so more seeds get refined** | topk 12 -> 40 -> 150 moves no clip and costs **7x compute** (32 s -> 229 s per 4 frames) | [evidence/raising-topk-so-more-seeds-get-refined.md](evidence/raising-topk-so-more-seeds-get-refined.md) |
| **Removing the pose-prior weight from the seed RANKING** | no clip improves; the prior is not what buries the true seed | [evidence/removing-the-pose-prior-weight-from-the.md](evidence/removing-the-pose-prior-weight-from-the.md) |
| **Reachability** - that refinement cannot travel from seed to true court | **STOPPING RULE FIRED.** On **31 of 38** clips the nearest seed is already within reach. The brief predicted the opposite in advance | [evidence/reachability.md](evidence/reachability.md) |
| **Narrowing `EVID_BAND`** | **The band is INERT** - the hypothesis the whole brief was built around is refuted | [evidence/narrowing-evid-band-so-clutter-near-a.md](evidence/narrowing-evid-band-so-clutter-near-a.md) |
| **Observability from geometry instead of nearby paint** | **+0.000 margin** | [evidence/observability-from-geometry-instead-of-nearby-paint.md](evidence/observability-from-geometry-instead-of-nearby-paint.md) |
| **Behind-camera projection inflating the denominator** | **0.0%** of samples affected | [evidence/behind-camera-projection-inflating-the-denominator.md](evidence/behind-camera-projection-inflating-the-denominator.md) |
| **The low true-court score being human click error** | swept `tol` x0.5 -> x4; no clip shows the steep threshold a click-error explanation needs | [evidence/the-low-true-court-score-being-human.md](evidence/the-low-true-court-score-being-human.md) |
| **Player-foot gate + survivor-based vote rule** | **converts zero reference clips** | [evidence/player-foot-gate-a-survivor-based-vote.md](evidence/player-foot-gate-a-survivor-based-vote.md) |
| **The player-foot gate as a wrong-court negation criterion** | **DEAD - no discriminative power** | [evidence/the-player-foot-gate-as-a-wrong.md](evidence/the-player-foot-gate-as-a-wrong.md) |
| **Widening / height-scaling `AGREE_PX`** | the resolution artefact is real but widening does not recover the disagreement | [evidence/widening-height-scaling-agree-px-to-recover.md](evidence/widening-height-scaling-agree-px-to-recover.md) |
| **The horizon crop (`movers.crop_row`) at `k = 1.0`** | **safe but inert** | [evidence/the-horizon-crop-at-the-pre-registered.md](evidence/the-horizon-crop-at-the-pre-registered.md) |
| Court + vertical cone gate for false alarms | real far balls and fixtures overlap in court coords (real span **-229..+1667 m**) | - |
| Scaling the fixture radius 12 -> 18 px | halves false-fire (13.2 -> 5.7%) but costs **4.3 pts** far-court recall | - |
| Offline live-ball trajectory filter | net-negative once suppression runs; recall 50.2 -> **40.5%**. Retired | - |
| Detector fusion (TrackNet + WASB) | rescued **4 frames** and doubled the dominant cost | - |
| Dead-time "silence" negatives | the wrong negatives - confusers are not silence | - |
| Depth-aware Kalman process noise | median-referenced made false-fire **worse** (19 -> 27%) | - |
| Raising detector score threshold | 0.6 and 0.7 both **fail the recall gate** | - |
| Shrinking smoother `max_gap_s` | every value fails; solid ghosts sit at **9 regardless** | - |
| **Motion attention (TrackNetV4)** | conclusion stands on the right population: **59.2%** of false locks travel with a person, only 38.0% are static scenery | [evidence/motion-attention.md](evidence/motion-attention.md) |
| **Depth-invariant static-player guard** (`body_relative`) | **GATE FAILS on 1 of 3** calibrated clips | [evidence/depth-invariant-static-player-guard.md](evidence/depth-invariant-static-player-guard.md) |
| **`--pose-quality accurate` for the far player** | **MEASURED NEGATIVE**, gate pre-registered before the run | [evidence/pose-quality-accurate-for-the-far-player.md](evidence/pose-quality-accurate-for-the-far-player.md) |
| Pose-proximity negative mining | **11.4%** catch at the 5% collateral ceiling vs a 60% gate - a skeleton has no racquet (**2.12 body heights** away) | - |
| **Racquet-box negation (COCO class 38)** | **failed twice**; the second run found why - COCO finds the *near* player's racquet while the detector fires on the *far* player's | [evidence/racquet-box-negation.md](evidence/racquet-box-negation.md) |
| **Tightening it to the racket HEAD** | **the head is not the discriminator** | [evidence/tightening-it-to-the-racket-head.md](evidence/tightening-it-to-the-racket-head.md) |
| **Screening far-court gaps at SELECTION time** | **GATE FAILS under cross-validation**; 569 passing feature pairs cross-validate to **0-3%**. The shuffled-label null control returns **0** passing pairs, so the signal is real and far too weak | [evidence/screening-far-court-gaps-at-selection-time.md](evidence/screening-far-court-gaps-at-selection-time.md) |
| Raising `acquire_bound_m` 4 -> 10 m | +0.6 pt recall for +1 ghost | - |
| Blur augmentation alone | dead end on its own; only pays combined with occlusion work | - |
| **Retuning `max_gap_s` for 60 fps** | **GATE FAILS on replication** - clean on yt_rally2, collapses on am_hard_utr. The optimal gap policy scales with detection density; never tune it on one clip | [evidence/retuning-max-gap-s-for-60-fps.md](evidence/retuning-max-gap-s-for-60-fps.md) |
| **A second bounce HYPOTHESIS in the smoother** (`bounce_hypothesis`) | **GATE FAILS on P2 and P6**, measured over all 10 gold clips (1658 clicks, 272 no-ball frames). Recall PASSES (47.0 -> 48.1%, +18 hits) and **separation PASSES at 9.00:1 against a >7 bar** - so it DOES beat the structural exchange rate. It fails because ghosts rise on **5 of 10** clips and recall *falls* on `gold_UHf0LeMU2pg` (-3 hits, +5 wrong). Off by default. | [evidence/bounce-hypothesis.md](evidence/bounce-hypothesis.md) |
| **Bounce-aware smoother reset** (`bounce_reset`) | **FAILS gate on all 3 clips**; best case **1.4 pts short** of `real_landing` +5. Off by default | [evidence/bounce-reset.md](evidence/bounce-reset.md) |
| **Lowering the smoother's `reset_after`** | **GATE FAILS on replication** | [evidence/lowering-the-smoother-s-reset-after-to.md](evidence/lowering-the-smoother-s-reset-after-to.md) |
| **A burned-in SCOREBOARD as ground truth for points/rallies** | **BUILT, THEN REJECTED ON THE PREMISE** and reverted (`afffb5a`) - it is somebody's data entry, not the court. Do not rebuild | [evidence/using-a-burned-in-scoreboard-as-ground.md](evidence/using-a-burned-in-scoreboard-as-ground.md) |
| **Single-frame court auto-seed in the setup tool** | **7 of 10 worse than starting from a blank rectangle**; only multi-frame consensus separates the cases | [evidence/single-frame-court-auto-seed-in-the.md](evidence/single-frame-court-auto-seed-in-the.md) |
| **Lowering the court consensus bar 6/8 -> 5/8** | **GATE FAILS** - the one 5-vote clip is wrong by 68.7 px | [evidence/lowering-the-court-consensus-bar-6-8.md](evidence/lowering-the-court-consensus-bar-6-8.md) |
| **Raising the detector's input resolution** | **Gate B FAILS on both clips** | [evidence/raising-the-detector-s-input-resolution.md](evidence/raising-the-detector-s-input-resolution.md) |
| **Making the smoother respect suppression** (`blocked` mask) | **GATE FAILS on the recall guards** | [evidence/making-the-smoother-respect-suppression.md](evidence/making-the-smoother-respect-suppression.md) |
| **Tightening the smoother gap to cut ghosting** | 0.10 s halves ghost frames but the trade is ~1:1 against recall, and only for FADED ghosts | [evidence/tightening-the-smoother-gap-to-cut-ghosting.md](evidence/tightening-the-smoother-gap-to-cut-ghosting.md) |
| **Mining `suppress_false_locks`' rejections as hard negatives** | **GATE FAILS**, and it corrects an over-attribution | [evidence/mining-suppress-false-locks-rejections-as-hard.md](evidence/mining-suppress-false-locks-rejections-as-hard.md) |
| **Mining whole-frame hard negatives at all** | **Gate C fails**, and it names the root cause | [evidence/mining-whole-frame-hard-negatives-at-all.md](evidence/mining-whole-frame-hard-negatives-at-all.md) |
| **Localised confuser weighting** (Session I) | **PRODUCT GATE FAILS** - pooled solid ghosts **14 -> 15** while the detector improved on 6 of 6 clips. Unattributable: the trainer had no seed | [evidence/localised-confuser-weighting.md](evidence/localised-confuser-weighting.md) |
| **Expecting a detector gain of ANY kind to reach the product** | **four for four** | [evidence/expecting-a-detector-gain-of-any-kind.md](evidence/expecting-a-detector-gain-of-any-kind.md) |
| **Telling labellers the rule instead of enforcing it** | **MEASURED NEGATIVE** | [evidence/telling-labellers-the-rule-instead-of-enforcing.md](evidence/telling-labellers-the-rule-instead-of-enforcing.md) |
| **Filling far-court labels by interpolating between anchors** | **MEASURED NEGATIVE** - the anchors bracketing the gaps were themselves false locks | [evidence/filling-far-court-labels-by-interpolating-between.md](evidence/filling-far-court-labels-by-interpolating-between.md) |
| Improving CourtNet for auto-calibration | wrong target - CourtNet is **Tier 2**; `courtfit` consensus is Tier 1 and beats it | - |
| **Finding burned-in graphics by any temporal statistic** | **all three fail on this footage, in both directions** | [evidence/finding-burned-in-graphics-by-any-temporal.md](evidence/finding-burned-in-graphics-by-any-temporal.md) |
| **Screening far-court gaps by lock kinematics** | **two measured negatives** - and they are why the anchor control exists | [evidence/screening-far-court-gaps-by-lock-kinematics.md](evidence/screening-far-court-gaps-by-lock-kinematics.md) |
| **Downscaling the pose INPUT to afford it on an A13** (P0-2) | **GATE FAILS by ~11 pts.** Far player on `yt_match40` **11.0% @1280 -> 0.1% @640 -> 0.0% @384** against a 2-pt bar; `am_hard_utr` 1.0 -> 0.0 -> 0.0. Near player barely moves (80.3 -> 78.1 -> 72.5), so it is the distant player specifically, not the model. Crop-around-contact (P0-3) remains UNMEASURED - its first probe was invalidated on inspection | [evidence/pose-downscale-far-player.md](evidence/pose-downscale-far-player.md) |

---

## Withdrawn figures

Numbers this project published and later retracted. **This table is machine-read:**
`.claude/hooks/withdrawn-guard.sh` refuses any commit where one of these strings
still appears in a live doc without a withdrawal marker in the same block. Add a row
the moment you withdraw a number — that is what stops a stale copy surviving
somewhere else, which has now happened three times.

| Figure | What it claimed | Withdrawn because | Date |
|---|---|---|---|
| `1.47x` | rally segmentation over-split vs real points | read off a burned-in scoreboard; the user rejected that premise and the tool was reverted (`afffb5a`) | 2026-08-15 |
| `1.6x` | the same over-split, re-counted | same source, same rejected premise — it should have gone with the 1.47x and did not, surviving in the Open table and in Trap T20 | 2026-08-17 |
| `1.6×` | as above, unicode-multiplication-sign spelling | registered separately because a literal-string check cannot see it otherwise | 2026-08-17 |
| `4.50:1` | the `bounce_hypothesis` separation ratio, said to be below the >7 bar and therefore worse than the structural exchange rate | a two-event denominator; re-measured over all 10 gold clips (272 no-ball frames) it is **9.00:1**, which passes | 2026-08-27 |
| `4.50 : 1` | as above, spaced spelling | registered separately because a literal-string check cannot see it otherwise | 2026-08-27 |
| `0.18–0.31` | the true court's agreement score, said to fall below the 0.33 accept gate on 5 of 10 calibrated clips — cited as proof that "the criteria reject the correct answer even when handed it" | it scored the human's four clicked corners **exactly**, but the gate defines correct as anything within 20 px @640. A court a median **5.8 px** from the clicks clears the gate on **9 of 10** clips, not 5 (`eval/truth_neighbourhood.py`). It measured our labelling, not the criteria — and it had already gone out in an external research brief, which ranked its recommendations on the strength of it | 2026-08-24 |
| `0.18-0.31` | as above, ASCII-hyphen spelling | registered separately because a literal-string check cannot see it otherwise | 2026-08-24 |

Not covered here on purpose: `docs/archive/HANDOFF.md`, `docs/archive/sessions/`, `docs/REVIEW-*` and
`data/output/*` are point-in-time records. They are SUPPOSED to still contain the old
number — that is what a dated record is. The guard skips them.

---

## Open, and what each is waiting on

| Item | Waiting on | Evidence |
|---|---|---|
| **Joint line-to-model correspondence - GATE PRE-REGISTERED 2026-08-27** | Nothing. Unblocked. The one build Session P named and did **not** test. All five failed branches assumed the line-to-model assignment can be settled BEFORE the homography; this solves both together. Bars: zero wrong accepts, gold **12/20 -> >=15**, no accuracy loss on the 12 that work, and the chosen correspondence shown rather than inferred. Carries a stopping rule. | [evidence/court-correspondence-gate.md](evidence/court-correspondence-gate.md) |
| **`bounce_hypothesis` v2 - GATE PRE-REGISTERED 2026-08-27** | Nothing. Unblocked. v1's defect is NAMED: `wrong` rises on ball frames (+5 on `gold_UHf0LeMU2pg`), so the reflected state is accepted at the wrong POSITION - a loosening hiding inside the `restitution_band` variance inflation. Adds **P7: `wrong` must not rise on any clip**. Carries a stopping rule. | [evidence/bounce-hypothesis-v2-gate.md](evidence/bounce-hypothesis-v2-gate.md) |
| **Court detection: frames that find the RIGHT court disagree about its WIDTH** | Nothing. Unblocked and unaddressed. Subordinate to the search problem | [evidence/court-detection-frames-that-each-find-the.md](evidence/court-detection-frames-that-each-find-the.md) |
| **Indoor shell courts** - ground truth exists; the failure is the SEARCH | Nothing. Unblocked. 10 human calibrations arrived and are good | [evidence/indoor-shell-courts.md](evidence/indoor-shell-courts.md) |
| **`AGREE_PX` is 6x tighter on 4K than on the gate** | The wrong-court / search problem - it cannot ship before that | [evidence/agree-px-is-6-tighter-on-4k.md](evidence/agree-px-is-6-tighter-on-4k.md) |
| **Far-court recall** (detector fires on nothing in 24-27% of frames) | Human far-court labels: **4,087 frames**, 4-5 hours of clicking. Automating the selection is a measured dead end | [evidence/far-court-recall.md](evidence/far-court-recall.md) |
| **9 solid ghost balls, and why nothing removes them** | A better detector. All 19 chain false locks have `run_len = 1` - every survivor carries a real ball's kinematic signature | [evidence/9-solid-ghost-balls.md](evidence/9-solid-ghost-balls.md) |
| **Confirming the localised-weighting detector win** | ~2h20m of GPU | [evidence/confirming-the-localised-weighting-detector-win.md](evidence/confirming-the-localised-weighting-detector-win.md) |
| **Whether more data is what actually caused the recall gain** | **n = 1 training run per arm**; the datasets differ in size so batch composition differs too | [evidence/whether-more-data-is-what-actually-caused.md](evidence/whether-more-data-is-what-actually-caused.md) |
| **Whether a better detector can reach the ghost ball at all** | Establishing which stage absorbs a detector gain, before the next detector idea | [evidence/whether-a-better-detector-can-reach-the.md](evidence/whether-a-better-detector-can-reach-the.md) |
| **Off-machine backup** | Second disk verified 2026-08-17; off-machine still open | [evidence/off-machine-backup.md](evidence/off-machine-backup.md) |
| **The far player is a DETECTION problem on the target footage** | Settled 2026-08-17; `--far-player-rescue` recovers frames the shipped guard then deletes | [evidence/the-far-player-is-a-detection-problem.md](evidence/the-far-player-is-a-detection-problem.md) |
| **Bounce detection** | No true ball height from one camera. Unevaluated: audio impact (module exists, unwired), monocular 3D | - |
| **Speed coverage is CHAIN-shaped, and the two stages are named** - the best-measured open target | Nothing. `smooth_forecast` costs -12.0 pts, `suppress_false_locks` -7.2, `gate_ball_to_court` exactly zero | [evidence/speed-coverage-is-chain-shaped-and-the.md](evidence/speed-coverage-is-chain-shaped-and-the.md) |
| **Ball-chain work is NOT closed — the stopping rule did not fire** | **Nothing. Unblocked.** The rule triggers if a separating mechanism lands at or below ~7:1; at full power `bounce_hypothesis` lands at **9.00:1**, so the premise that the exchange rate is a property of the SIGNAL is disproved. A second hypothesis beats it. What fails is position accuracy on one clip, which is a fixable mechanism problem, not a closed lane. | [evidence/bounce-hypothesis.md](evidence/bounce-hypothesis.md) |
| **8 court gold frames are mislabelled** | A minute of human re-labelling in the Lab. Deliberately not quietly edited | [evidence/8-court-gold-frames-are-mislabelled.md](evidence/8-court-gold-frames-are-mislabelled.md) |
| **Trimming was the missing first step** | Nothing - `tools/trim_clips.py` exists | [evidence/trimming-was-the-missing-first-step.md](evidence/trimming-was-the-missing-first-step.md) |
| **Core ML export requires macOS** (`coreml-export-requires-macos`) - found 2026-08-27 running P0-0 | A Mac to run `tools/export_coreml_p0.py` on. `coremltools`'s Windows wheel is pure Python; the native libs that serialize an `mlprogram`'s weights (`BlobWriter`) are absent, so export fails, not just the on-device measurement | [evidence/p0-0-coreml-export.md](evidence/p0-0-coreml-export.md) |
| **Mobile viability is SPLIT, not uniform** - audited 2026-08-27 | Nothing. Unblocked. Live line calls are a straightforward port and largely done; the offline analyzer is a **rebuild** - its Kalman+RTS smoother is non-causal by construction and it runs whole-video passes. No Windows paths, no highgui, and every cv2 symbol used exists in the mobile builds. Two defects found en route: mobile bundles a TrackNet export while the shipped default is BallNet v21, and `modules.md` overclaimed (corrected) | [evidence/mobile-viability-audit.md](evidence/mobile-viability-audit.md) |
| **Phone app shell** | App development, not ML. No phone fps has ever been measured, so do not quote one | [evidence/mobile-viability-audit.md](evidence/mobile-viability-audit.md) |

---

## Recently closed

Answered, and kept only as a pointer so the answer is not re-derived.
Full text in [archive/resolved/](archive/resolved/).

| Item | Answer | Evidence |
|---|---|---|
| **Court auto-detection** | CLOSED AGAIN 2026-08-25 - five branches measured, none survives. The detector FINDS the court's lines but cannot assemble them. The correct next build is joint line-to-model correspondence, and it was NOT tested | [archive/resolved/court-auto-detection.md](archive/resolved/court-auto-detection.md) |
| **Court auto-detection as a MASK problem** | Superseded by the row above | [archive/resolved/court-auto-detection-2.md](archive/resolved/court-auto-detection-2.md) |
| **Whether the +5.6 pt recall gain reaches the product** | ANSWERED 2026-08-13: it does not. Solid ghosts 9 -> 13 at flat chain recall | [archive/resolved/whether-the-5-6-pt-recall-gain.md](archive/resolved/whether-the-5-6-pt-recall-gain.md) |
| **Speed coverage as detector work** | Superseded - it is CHAIN work; see the Open row | [archive/resolved/speed-coverage.md](archive/resolved/speed-coverage.md) |
| **Rally segmentation / score** | CLOSED BY DECISION 2026-08-20 - the user ruled this layer out of scope. Not a work item | [archive/resolved/rally-segmentation-score.md](archive/resolved/rally-segmentation-score.md) |
| **Processing 60 fps clips at full rate** | DECIDED 2026-08-15: shipped opt-in as `--full-rate` | [archive/resolved/processing-60-fps-clips-at-full-rate.md](archive/resolved/processing-60-fps-clips-at-full-rate.md) |
