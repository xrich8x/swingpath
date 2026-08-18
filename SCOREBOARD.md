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

1. **Score only against independent human labels.** 1851 human ball clicks and 308
   no-ball frames across 10 clips (the legacy six, 1201/204, is kept as a named subset
   so historical figures stay reproducible). Test-only, never trained on. A model never
   grades its own homework.
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
8. **Look at the errors, at the right zoom, before theorising about them.**
   `tools/false_fire_viewer.py` renders every false lock as a clickable context tile
   with a matching zoom, because the two questions need opposite crops: *what object is
   this attached to* needs 140 px of context, *is this literally a tennis ball* needs
   44 px blown up. Judging either from the wrong one produces confident nonsense — see
   Trap 18.
9. **And look at them MOVING.** `tools/false_fire_reel.py` renders ±0.5 s around each
   false fire with the detector run continuously and its lock drawn every frame. A still
   cannot separate a racquet head from a ball — both are ball-sized, ball-coloured blobs
   — and the thing that separates them is that one is on a short arc pinned to a person.
   Two sessions were spent proving the pipeline cannot make that call from geometry while
   the discriminator was motion, which no contact sheet shows. Annotation colour is
   **magenta on purpose**: the subject and every confuser are yellow-green, so a yellow
   marker hides inside the object it points at.
10. **A test set that PICKS a hyperparameter is a validation set wearing a test set's
    reputation, even if pre-registered.** External review (2026-08-16, P0-1): rule 1 says
    the gold set is never trained on, but `tools/tune_smoother.py` and
    `tools/tune_suppress.py` had both been sweeping `max_gap_s`, suppression segment
    thresholds, `score_thresh` and more directly against the same 1851 clicks that also
    produce every headline recall/false-fire number — over a dozen sweeps across six
    weeks. Pre-registering each individual gate (rule 2) limits cherry-picking within one
    sweep; it does not stop the cumulative drift of many sweeps against one fixed set.
    Two clips are now a permanent, ONE-WAY blind holdout (`tools/_goldset.py`'s
    `HOLDOUT`), structurally withdrawn from both tools' `--clip` choices — see the
    matching row below. They stay fully visible to `eval_gold.py` / `eval_detector_gold.py`
    / `eval_model_filters.py` for reporting; the rule is about what CHOSE a value, not
    about what gets measured.

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
| **Synthetic ground truth** (`tools/synth_truth.py`) | first ABSOLUTE accuracy this project has had — every other number is agreement with a human. Line calls **95.9%** correct, bounce **0.75 m** median, and the −15..−20% speed rule confirmed as physics (drag = **−21.7%**) | 2026-08-06 |
| **SwingVision scrub + trainer guard** | **A standing user rule turned into something the trainer enforces.** Five training clips (27% of the pool, 11,187 labels) carry a burned-in SwingVision overlay — mini-court radar, stroke/speed readout, score panel, and a watermark that is **a literal yellow tennis ball**. **83 pseudo-labels landed inside one of those graphics**: the labeller locking onto the watermark, and us teaching that it is a ball. `tools/scrub_swingvision.py` writes a per-dir mask; `BallWindows` paints the boxes **at load** (non-destructive — no JPEG is rewritten, so the scrub is re-applied every run and stays visible in the code) and drops the in-box labels; `assert_no_swingvision_leak` **refuses to train** on an unscrubbed overlay clip, same shape as the gold guard. Keeps the 11,104 good labels instead of binning a quarter of the pool. 6 tests, incl. proving the guard fires and that boxes are stored in FRAME space not source space (the unscaled-pixel bug this repo has hit repeatedly). | 2026-08-13 |
| **`am_hard_utr` finally has a perception cache** | **The clip that kills smoother tunings could never be used to test them.** The last two — `max_gap_s` at 60 fps and `reset_after` — both turned on this clip and neither could be measured on it, because no cache existed and a fresh pass was a multi-hour run nobody had spent. Built on **cuda** with thresh 0.5 to match the device and settings of the yt_match40 / yt_rally2 caches, so the three are comparable rather than a device confound (ML_PRACTICES: argmax can flip near-threshold decisions between devices): 14,499 frames at `frame_step 2`, hfov 86.3, 10,840 locks, 120 shots / 79 rallies. **It immediately earned its keep** — it is the clip that showed the post-bounce diagnosis is a smaller lever on amateur footage than on yt_match40 (see the `bounce_reset` row). Any future chain change can now be replicated on all three calibrated clips instead of two. | 2026-08-15 |
| **60 fps shipped as `--full-rate`** | **A measured lever that had no product surface.** `--frame-step 1` has always processed every frame, so the MECHANISM was never missing — but as a bare integer nothing said it is the largest measured accuracy gain in the tool, or what it costs. The decision (Session H parts 5-6, `data/output/fps_decision.md`) had sat in Open as "a product call, not more measurement" while remaining un-called. Now `--full-rate` states the trade in its own help: **+5.8 pts close-call accuracy at a 1.5 m mount, arc reproj 148 → 91 px, HUD speed error 38.9 → 33.1%, bounce error −24..−35%**, against **2× perception time** and a **wash-to-negative on DETECTION** — and prints the same at runtime, because a mode that doubles runtime must announce it. Mutually exclusive with `--frame-step` (passing both is a contradiction, not a preference). **Default unchanged at `auto`** — opt-in until a full match has been run at full rate. Verified end to end: yt_rally2 (60 fps) goes `frame_step=2 → 1`, demo30 (29 fps) reads `frame_step=1` **either way**, so the "no-op on 30fps" claim in the help is measured rather than asserted. Cache invalidation needed no work — `frame_step` was already stamped and checked, so the two rates cannot be silently mixed. 6 tests, 387 total | 2026-08-15 |
| **The two JS mirrors are enforced, not asked for** | **Trap 6 again, found before it bit.** `court.js` and `calls.js` are hand-copies of `court.py` and `calibration.py`, and both were guarded by a comment reading *"keep these in sync"* and by nothing else — the frontend has **no test runner**, so there was no side the check could run from. The failure mode is silent: correct a number in Python, every backend test passes, and the dashboard keeps showing the old value to the user. `tests/test_js_mirror_parity.py` reads the JS as text from the Python side (no Node, no new toolchain), **evaluates its arithmetic** so derived constants like `NET_Y` and `ALLEY` are compared as values rather than as source strings, and cross-checks `expected_call_accuracy` against the table the BROWSER holds at every knot plus both clamp ends. **The guards were proved to fail**: corrupting `LENGTH` 23.77 -> 23.78, one table row, and the floor 56.2 -> 50.0 each turned the suite red, and the files restored byte-identical. Also pins the court constants against **regulation** (23.77 / 10.97 / 8.23 / 6.40), because the mirror could agree and both be wrong. 6 tests, 381 total | 2026-08-15 |
| **Court TEST/TRAIN split + leak guard** | court numbers became measurable at all — 17 of 20 gold clips had been in training | 2026-08-06 |
| **Camera-height curve** (`tools/height_curve.py`) | turned the setup tool's *bound* into an *error*. Close-call accuracy by mount height, measured against known bounces: **54% at 1.0 m → 69% at 3 m → 81% at 8 m**, bounce error **3.81 m → 0.37 m**. A 1.0 m mount is **below the 56.2% majority-class floor** — its close calls carry no information. Now surfaced in every `setup_verdict` | 2026-08-07 |
| **Frame rate isolated from detector dropout** | 30 → 60 fps is worth **+5.8 pts** of close-call accuracy at 1.5 m, +3.2 at 3 m, +1.8 at 12 m, and cuts bounce error **24–35%** — holding at both dropout levels, so it is not dropout in disguise. For scale, a *perfect* detector buys +4.7 / +2.5 / +2.2 at the same heights: **doubling the frame rate we already have is worth about as much, and is free.** Confirmed end to end on yt_rally2 — arc reproj **148 → 91 px**, HUD speed MAE **38.9 → 33.1%** | 2026-08-07 |
| **Per-rally clips + highlights reel** (`run.py highlights`) | the last unbuilt product feature. Dead time disappears: every rally becomes a playable clip, ranked deterministically (shot count → top *confident* speed → duration), with a top-3 reel. ffmpeg **stream copy**, so cutting is I/O-bound rather than a 5–10× re-encode. The manifest records requested vs actual start, so "a clip never opens mid-rally" is **checked**, not asserted | 2026-08-08 |
| **Far court measured in METRES, not frame rows** | `FAR_FRAC` called the top 36% of the FRAME "far court" — a proxy for the far half of the COURT that only held for the framing it was written against. On the clips added 2026-08-11 it is wrong by **5-26x**: `tc8CGFxyRE8` puts **3.2% of its labels in the top 36% of the frame and 84.0% past the net**, `e8T34KoJzOw_s2` 5.0% vs 46.1%. A camera that frames the court well puts the far baseline LOWER in frame, so the proxy declared whole clips to have almost no far court and the label queue skipped them. Selecting past the net instead took the far-court queue **1,393 → 2,677 gaps** off the same footage. Only possible because every new clip now carries a homography | 2026-08-11 |
| **More labelled data, from more venues** | **+57% training frames (26,293 → 41,390) across 8 new venues buys +5.6 pts pooled detector recall** on the ten-clip benchmark (74.8 → **80.4%**, 4.1σ), far_px +6.5 (73.3 → 79.8%), far_geo +5.6. Recall is up on **9 of 10 clips, flat on 1, down on none**. It is generalisation rather than domain-matching: on the **legacy six alone** — venues sharing nothing with the new footage — recall goes 77.0 → **82.2%** (3.1σ), the highest ever recorded on that 1,201-frame set (shipped `ballnet_v21` reads 69.4%). Both arms `--seed 0`, one variable. **RECALL ONLY: false fire did not move** (57.1 → 53.9%, **0.8σ** on 308 no-ball frames; +0.5 pts on the legacy six). Not yet shipped and not yet a product number — see Open. Evidence: data/output/pool_ab.md | 2026-08-13 |
| **The height guidance actually reaches the user** (`run.py check` + Court Setup tab) | **The measurement existed for a week and shipped to nobody.** `calibration.expected_call_accuracy` and `CALL_MAJORITY_FLOOR_PCT` were computed, documented and pinned by 6 tests — and reachable only through `courtfit.setup_verdict`, which was called by exactly two files, both of them TOOLS (`court_setup_server.py`, `audit_new_clips.py`). `run.py check`, the command named *"pre-flight: grade your court framing"*, never called it; it ended at `elevation 2.68`, an unbounded proxy. The dashboard did not show it either. Now both do: check prints *"~58% of close calls correct / floor is 56%"* and shouts **THIS MOUNT ADDS NOTHING** at or below the floor, **each with the sentence saying what it was measured against** (rule 2 — it is a curve over camera HEIGHT from simulated flights, not a measurement of the user's clip, and it first shipped without that line); the Court Setup tab grades the mount live as you drag corners (green/amber/red), off the camera height `fitCamToQuad` already solves for the shape lock, so it costs no extra fitting. **`check` also stopped being a second opinion**: it used to read ONE frame through `detect_court_learned` -> `detect_court` while `analyze` runs `courtfit` consensus over 8 and accepts only >=6 — measured on demo30 with no keypoints, the old path returned a court and graded it POOR while analyze **REFUSES the clip** ("2 of 8 frames (needs 6)"). It now calls `pipeline.calibrate_video`, the same entry point, so the two cannot drift (trap 15). `--court-weights` removed from check: analyze has no such flag, and an override only check honoured would rebuild the divergence. JS mirror verified **EXACT against Python on 17 heights**. 8 tests, 373 total | 2026-08-14 |
| **Manual-correction UI** (Review tab + `run.py correct`) | closes the oldest known gap. Edits FACTS only; score is replayed through `scoring.TennisScore` and stats through `schema.compute_stats`, so there is no second implementation of the rules. Verified end to end: demo score 2-5 → 3-4, line calls 108/17 → 107/18, and re-applying the same file is a no-op | 2026-08-06 |
| **CourtNet training seeded** | closes an undocumented asymmetry flagged by the 2026-08-16 review (P2-1): `train_courtnet.py` had zero seeding while `train_ballnet.py` fully seeds random/np.random/torch/cuda plus the DataLoader shuffle generator. Now matches that exact discipline (same caveat as ballnet: pairs init/shuffle/augmentation draws, not full multi-worker bit-determinism) via a new `--seed` flag, so a future CourtNet A/B won't repeat the "arms differ by more than the flag under test" problem Trap 10 already fixed once for BallNet. No CourtNet number moved — this only removes a confound from the *next* comparison. | 2026-08-16 |
| **BallNet v21 vs TrackNet vs WASB, finally re-dated** (review P1-1) | The "beats TrackNet" claim in `pipeline.py`'s auto-select comment traced to numbers from before v21 (+57% data, hard-negative mining) and was **UNVERIFIED as current** per the review. Re-ran the existing harness (`ball_perception.py` + `eval_gold.py`, no new tool) across all 10 gold clips, one model at a time on the GPU: pooled hit@10 **BallNet 60.8% vs TrackNet 57.9% vs WASB 49.3%** — BallNet still wins, but by **+2.9 pts over TrackNet, not the +10.5 this comment used to claim**. Not a clean win: TrackNet beats BallNet outright on 2 of 10 clips, and BallNet false-fires the most under identical (non-suppressed) tracker gating (55.1% vs 31.5%/40.1% — **not comparable to the shipped ~6.0% pooled false-fire**, which is measured AFTER `suppress_false_locks`/`smooth_forecast`, absent here by design so the three detectors are compared on equal footing). `pipeline.py`'s comment now cites this dated evidence instead of an unsourced number; the stale "live-ball filter" reference in the same comment (retired E5+) is also corrected to `suppress_false_locks`. Two hiccups during the run, both diagnosed and fixed rather than papered over: `yt_match40` (native 29fps) rejected `--target-fps 30` as exceeding source — switched to the project's own `--frame-step` formula; `gold_L73ep7JHiJ4`'s tracknet cache was transiently rebuilt under a different decimation scheme than its wasb/ours caches (100-frame n_ball mismatch caught by comparing raw counts, not just percentages) and rebuilt to match. Evidence: data/output/ballnet_vs_baselines_p1_1.md | 2026-08-17 |

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
| Motion attention (TrackNetV4) | **CONCLUSION STANDS, and it has now been tested on the RIGHT population — the original evidence was not.** Session F skipped it because "it suppresses *static* confusers; ours **move** (59.2% travel with a person)" — but that 59.2% was measured on RAW detector locks, the population Session F itself declared *"not the product"*. Session I then found the 5 universal chain-surviving ghosts are **3 static / 2 person-attached**, the opposite split, so the dismissal looked like it had been scored on the wrong population. **RE-MEASURED 2026-08-15 using MotionPrompt's own criterion** (mean \|f0−f1\|+\|f1−f2\| in a patch at each lock), on the 20 SOLID ghosts that survive the whole chain and get drawn on a human no-ball frame, referenced against the same statistic at **532 human ball clicks**: real balls read p10 **1.17** / median 3.32 / p90 11.45; **only 5 of 20 ghosts (25%)** fall below the real-ball 10th percentile. **15 of 20 sit on things moving as much as a genuine ball.** So a motion gate tuned not to damage the dimmest decile of real sightings reaches **a quarter** of the problem. **Not worth the training run** — and this directly contradicts an independent review that called it "the single highest-value-per-hour item". NOTE the infrastructure is complete and unused: `_ballnet.MotionPrompt` is wired, `train_ballnet.py --motion-attention` exists, and **0 of 8 shipped weight files contain `motion.*` keys** — it has never once been trained. n=20 ghosts is small (trap 9), but it is 4x the n=5 the counter-argument rested on and the direction is unambiguous. |
| Pose-proximity negative mining | **11.4%** catch at the 5% collateral ceiling vs a 60% gate. The racquet is **2.12 body heights** from the nearest keypoint — a skeleton has no racquet. |
| Racquet-box negation (COCO class 38) | **Failed twice, and the second run found the reason.** Session G part 4: 54.5% catch at 4.5% collateral, 5.5 pts under gate. Re-scored on the Session K detector: **23.3% at 4.6%** — now 36.7 pts under. The control reproduces Session G digit for digit, so the harness is sound. **But the numerator is what matters**: the box catches ~12 locks in every population (12/22 → 12/32 → 7/30); the rate collapsed because 10 racquet locks were added when `gold_uR5q2cSM6AY` was classified and the box catches **0** of them. On all 10, the lock sits **737–869 px** from the nearest racket box — YOLO found the **near** player's racket (80–150 px, conf 0.46–0.83, low in frame) and missed the **far** player's, which the ball detector was firing on (high in frame; where a far racket *is* found it is 37×56 px at conf **0.12**). So *"a racket is found on 64–100% of frames"* — quoted in G part 4 as evidence the ceiling was the criterion — was true and useless: **it was finding the wrong racket.** COCO's racket class is trained on large sharp rackets, so racquet negation is structurally blind exactly where the confuser lives. Evidence: data/output/racquet_negation_k.md |
| Tightening it to the racket **HEAD** | **The head is not the discriminator.** On the wrist→head axis, racquet locks sit at median **0.57** and real balls at **0.55** — indistinguishable. Every tightening costs more catch than collateral (cut 0.5 → catch 36.4%, collateral only 4.5→2.6%). The whole box is the best version of the idea; 54.5%@4.5% is its ceiling. |
| Screening far-court gaps at SELECTION time | **GATE FAILS under cross-validation, and the null control is what makes it readable.** 41% of queued gaps contain no findable ball, so a screen must run before the human spends the effort — it cannot be the anchor control, which needs a human click by construction. Scored 7 queue-computable features on **79 gaps with a human verdict** (gate: keep ≥70% of usable, drop ≥60% of unusable). Best single feature: `anchor_disp_px`, keep 73.0% / drop **50.0%**. Every median is ordered the *right* way (usable gaps have more displacement, roam and vertical drop) and every distribution overlaps too much to act on. Sweeping **pairs** produces **569 passing combinations** — which is what ~500,000 candidate rules do to 79 points: cross-validated on the natural round split, **0–3% survive** (held-out keep 52.6–62.2%, drop 51.2–58.4%). **The null control is the useful part: the same search on SHUFFLED labels yields 0 passing pairs**, so the signal is real and simply far too weak to screen on. Also ruled out for free: the midpoint's tracker prior is **pure linear interpolation of its anchors (0 of 49 deviate >0.5 px)**, so any "is the midpoint consistent" feature is identically zero. Session J's roam criterion retested at n=79 (was 12) and still fails. **Fourth independent failure to make the far-court queue reliable** — the lever is blocked on an unsolved problem, not on labelling effort. Evidence: data/output/gap_findability.md |
| Raising `acquire_bound_m` 4 → 10 m | Static analysis said free; end to end it bought +0.6 pt recall for +1.9 pt false-fire. |
| Blur augmentation alone | Dead end on its own; only pays off combined with occlusion work. |
| Retuning `max_gap_s` for 60 fps | **GATE FAILS on replication.** 0.60 looks like a clean knee on yt_rally2 (ghost flat at 8 from 0.20–0.60, recall +1.9) and passes the gate there — then on am_hard_utr it costs **+5.6 pts false-fire and +3 ghosts for +0.5 recall**, with no flat region at all. 0.4 stays, and full-rate 60 fps therefore needs **no** rate-dependent gap policy. |
| Resetting the smoother on a DETECTED BOUNCE (`bounce_reset`) | **The mechanism version of the row below, and it FAILS the same gate.** Rather than counting rejections, the test is physical: in image pixels y grows downward, so a descending ball has vy > 0 and a bounce flips it — a rejection sitting ABOVE the prediction while the model still descends (with horizontal continuity, so an overhead false lock cannot trigger it) is a reflection, not an outlier, and resets on that frame. Same pre-registered gate (recall ≥−2, ghosts must not rise, `real_landing` ≥+5): **yt_match40 recall 52.7 → 53.8, ghosts 5 → 6, real_landing 70.9 → 74.5 (+3.6, short of +5)**; **yt_rally2 recall 42.2 → 41.5, ghosts 4 → 5, real_landing 80.0 → 80.0 (no headroom)**. **FAILS on both.** Directionally right where detections are sparse and inert where they are dense — **the third independent route to the same density dependence** (`max_gap_s`, `reset_after`, this). Kept as an off-by-default parameter with the numbers in the docstring so the measurement is not repeated; 4 tests pin that it is inert unless asked for. Ghost counts rest on 24/26 no-ball frames, inside sampling noise (trap 9) — the `real_landing` columns are load-bearing. **TWO FIXTURE BUGS worth remembering**: a synthetic "bounce" written as a parabola is exactly what a CA model predicts, so nothing is ever rejected and the flag looks inert; and even as a true velocity discontinuity, the model absorbs a **20 px/frame swing with zero rejections** — it takes 40 px to engage. |
| Bounce-aware smoother reset (`bounce_reset`), the MECHANISM version | **FAILS THE SAME GATE ON ALL THREE CALIBRATED CLIPS — and the third clip corrects the framing that motivated it.** The `reset_after` row below concluded a real fix must reset on a *detected bounce* rather than after N rejections. Built: the discriminator is physical, not a counter — in image pixels y grows downward, so a descending ball has `vy > 0` and a bounce flips it; a rejection sitting ABOVE the prediction while the model still descends (horizontal continuity required, so an overhead false lock cannot trigger it) resets on that frame. Same pre-registered gate (recall ≥−2, ghosts must not rise, real_landing ≥+5): **yt_match40 +3.6** real_landing (recall +1.1, ghosts +1), **yt_rally2 +0.0** (ghosts +1), **am_hard_utr +0.8** (recall +0.0, ghosts **−1**). Best case is 1.4 pts short of the bar. **Not shipped**; kept off-by-default with the numbers in the docstring. **THE CORRECTION:** the post-bounce loss was framed as one root cause with two payoffs, but on `am_hard_utr` — the 1.74 m amateur mount this project targets — `real_landing` is **already 74.2%** while speed is untrusted for **64 of 120** shots, and the printed reasons are dominated by *coverage* (`seen 10–49%<50%`) with "landing not tracked past bounce" in only ~20 of 64. On yt_match40 the landing cause dominates; on the target footage **the binding constraint is overall in-rally coverage, not the frames after the bounce.** Two attempts (threshold, then mechanism) failed to convert the diagnosis into a product gain, and the third clip says why it would not have paid much anyway. Evidence: data/output/post_bounce_chain.md (part 2) |
| Lowering the smoother's `reset_after` to keep the ball past a bounce | **GATE FAILS ON REPLICATION — and the DIAGNOSIS it came from stands and is the more useful half.** Attributing the post-bounce ball loss to a stage (stages *invoked*, not re-derived): in the 6-frame window after 196 landings on yt_match40, raw 965 locks -> `rectify` 949 -> `suppress` 877 -> court gate 877 -> **`smooth_forecast` 691**. **The smoother is 68% of the loss (−186 of −274), 2.6x suppression**, and disproportionate — 21% loss inside the window vs 14% clip-wide, i.e. bounce-specific. On the `real_landing` test that gates speed, shots passing go **177 -> 160 -> 139 of 196**: the smoother alone costs 21 shots. Mechanism is in its own docstring: a reset needs `reset_after` **consecutive gated detections**, so at a bounce the constant-acceleration model must **reject 3 real detections** before accepting the arc changed. `reset_after` had never been swept. Pre-registered gate (recall ≥−2 pts, ghosts must not rise, `real_landing` ≥+5). On **yt_match40** `reset_after=2` **PASSES all three** (recall +1.6, ghosts +0, real_landing +6.1). On **yt_rally2 it FAILS**: ghosts +1 and **real_landing +0.0**, because that clip is **already at 80% at every setting 1–3** — no headroom. **The prize exists only where detections are SPARSE; the ghost cost is paid everywhere.** Same shape as the `max_gap_s` finding by an independent route: **the optimal policy scales with detection density, so never tune it on one clip.** POWER: the ghost guard rests on 24/26 no-ball frames, well under the 74 the product gate uses (trap 9), so read this as *failed to replicate*, not *proved worse*; the `real_landing` columns are the stronger signal and disagree decisively. `am_hard_utr` has no perception cache and was NOT tested. **Stays at 3.** A real fix must reset on a *detected bounce* rather than after N rejections — a mechanism change, not a threshold change. Evidence: data/output/post_bounce_chain.md |
| Using a burned-in SCOREBOARD as ground truth for points/rallies | **BUILT, THEN REJECTED ON THE PREMISE — do not rebuild it.** A tool read the point-by-point boards on am_hard_utr and yt_match40 by per-field state clustering, every state labelled by eye, giving 36 and 43 points with **all 79 transitions legal tennis**, and put the rally over-split at 1.47x. **The user rejected the premise and it was reverted (afffb5a); the 1.47x is WITHDRAWN.** A burned-in scoreboard is **manual data entry** by a player, editor or app operator. It is genuinely INDEPENDENT of anything this project computes — and **independence is not truth**. The 79/79 check proves the scoreline is **self-consistent**, not that it matches the court: a diligently-kept *wrong* board passes it perfectly. That is internal consistency mistaken for external validity, a cousin of Trap 12. Worse, the intended use was tuning `gap_s` against point-BOUNDARY timestamps — i.e. **calibrating a rally threshold against when somebody pressed a button**, reaction lag included. Anything scoring this layer must take truth from the COURT (ball, players, bounces). |
| Single-frame court auto-seed in the setup tool | **MEASURED against 10 clips a human then calibrated by hand (2026-08-11): 2 seeds produced no lock and 5 were 174-438 px out** — a wrong RUNG (service line taken for the baseline, or the court next door), the remaining 3 still 107-128 px off. **7 of 10 were worse than starting from a blank rectangle**, and the user said so before it was measured. `verify_court` coverage does NOT separate them: the 221 px-wrong seed scored 61% of the template on real white paint and a 122 px-wrong one scored 94%, because a wrong-rung court still lies along real lines. **Only multi-frame consensus (>=6 of 8) tells the cases apart, and a single frame cannot run it** — so gallery mode now seeds ONLY clips consensus accepted. *(This row sat OUTSIDE both tables until 2026-08-15, formatted for "What has worked" and stranded below the Open table's rule, so the file's own dead-end list did not contain it. Its lesson had meanwhile recurred verbatim in `run.py check`, which was still doing single-frame court detection — see Trap 15.)* |
| Lowering the court consensus bar 6/8 → 5/8 | **GATE FAILS.** Exactly one 5-vote clip exists and it is wrong by **68.7 px**, against 3.4–13.9 px for every clip at ≥6 votes. Nothing lands in the gap. The bar is empirically correct. |
| Raising the detector's input resolution | **Gate B FAILS on both clips.** At the detector it looks like a large free win — 512x288 → 640x360 is **+8.2 pts far_px**, with operating points that dominate the shipped one outright (same precision for +5.4 recall, or same recall for −14.2 false-fire). End to end the shipped setting **dominates every variant**: the chain was already removing those false fires, so the precision gain is absorbed and the recall gain arrives as extra SOLID ghosts (5→7 on yt_rally2, 1→5 on am_hard_utr). E3f's "per-frame recall is not the bottleneck" still stands. Evidence: data/output/phase0_ball_ceiling.md |
| Making the smoother respect suppression (`blocked` mask) | **GATE FAILS on the recall guards, and the failure reframes `suppress_false_locks`.** The mechanism was real and visible: suppression cuts ghost fires and the Kalman puts them back (5 of 6 model x clip runs; am_hard_utr 9 -> 1 -> 6, every added one interpolated), because the two stages are blind to each other and a gap from *detector missed it* looks identical to a gap from *a lock was deleted as false*. Passing the removed-frame mask and refusing those bridges does cut ghosts — **19 -> 15 fires, solid held at 9, both primary gates PASS** — but pooled recall falls **66.9% -> 61.8% (-5.1 pts over 532 frames)** and far_geo **-7.2** on the worst clip. That is **~7 real ball frames lost per ghost frame removed**, which only makes sense if **the gaps suppression opens are majority REAL BALL, not ghost** — a sharper characterisation of that filter than we had. It also lands on the same ~1:1 recall trade Session F measured for `max_gap_s` by a fully independent route, so the exchange rate looks structural. Param + 4 tests kept in `ball.smooth_forecast`; the pipeline does not pass it. Evidence: data/output/smoother_coherence.md |
| Tightening the smoother gap to cut ghosting | Pooled, 0.10 s halves ghost frames (21.5% → 11.4%, zero interpolated) but drops recall to **60.3%** — at 60 fps that is the ball drawn on 36 of every 60 frames *during a rally*. It does not remove "insane", it relocates it from dead time to mid-point, where the user is actually looking. Also: single-digit false fire is **not reachable by tuning** — pooled floor is 11.4%, because the 9 solid ghosts are the detector. |
| Mining `suppress_false_locks`' rejections as hard negatives | **GATE FAILS, and it corrects an over-attribution.** A first estimate of 77.3% catch was withdrawn — it differenced raw against the FULL chain, crediting suppression with the tracker gates' work too. Measured in isolation on matched populations: persistence 7.5% catch / 5.7% collateral (it costs more real balls than confusers it catches — it detects things that hold still, and these move), min-segment 32.5% / **2.4%**, both 40.0% / 8.1%. Catch tops out 20 pts under the bar. **Three distinct automatic criteria have now failed** — skeleton position, racket box, trajectory plausibility — so there is no cheap automatic signal separating a swung racquet from a ball. Evidence: data/output/phase0_ball_ceiling.md |
| Mining whole-frame hard negatives at all | **Gate C fails, and it names the root cause.** Purity depends on the base rate, and the training clips are **88.5% ball-present** (they are extracted rally clips). Enrichment: persistence 1.4x, min-segment 6.0x, both 3.7x — against a 10x bar. At the real base rate a mined pool is **43.7% pure at best**, i.e. over half real-ball frames. Every route has died on the same fact: dead-time frames are pure but hold no confusers, and confuser-rich frames are frames with tennis being played. **The whole-frame negative format asks about the FRAME when the useful question is the LOCATION.** |
| Localised confuser weighting (Session I) | **PRODUCT GATE FAILS — pooled solid ghosts 14 → 15 (+1) at flat recall (69.2 → 69.0%).** Ninth failure at the ghost ball. **BUT THE DETECTOR IMPROVED, on 6 of 6 gold clips**: false fire 53.9 → **42.2%** pooled (−11.7 pts, 110 → 86 of 204 no-ball frames, 3.4σ) at *higher* recall (79.9 → 80.4%) and far_px (80.9 → 82.5%) — the operating point moved outward on both axes, not a precision-for-recall trade. **NOT ATTRIBUTABLE YET:** one training run per arm and the trainer had **no seed**, so the arms differ by initialisation and batch order as well as by the flag; the 6-clip sign test measures evaluation noise, not training noise. `--seed` now exists so a future pair is paired. Evidence: data/output/session_i_ab/results.md |
| Expecting a detector gain of ANY kind to reach the product | **Four for four now, and the second axis is new.** Input resolution, `score_thresh` and localised weighting each cut detector false fire substantially and arrived as nothing or worse. Session K adds the other axis: **+5.6 pts of detector RECALL arrives as +0.0 pts of chain recall**. On yt_match40 the extra recall is plainly there through the tracker gates (65.8 -> 75.5) and then absorbed — `suppress_false_locks` and the Kalman eat 7.5 of the 9.7 points. The chain, not the detector, is the binding constraint on what the user sees. **Stop scoring ball work at the detector on either axis**; justify the next idea by a chain-level mechanism or do not run it. |
| Telling labellers the rule instead of enforcing it | **MEASURED NEGATIVE, and it is the reason the far-court queue is now blocked on SELECTION rather than effort.** Session J ended by adding *"a ball in play is somewhere different on every frame"* as the lead rule on the labelling page. The commit landed at 21:20; `farcourt_cal1` was labelled at 21:50 — the first round under it — and is **WORSE than the round before** (47% vs 60% of gaps yielding ball-like click motion). **17 of its 49 gaps have the human clicking the IDENTICAL pixel on both frames**, which a ball in play cannot do. The pre-registered L2 gate (>=60%) FAILS at 47%, so the 4-5 hour labelling push does not run. A written instruction on the page is not a control — the test is now enforced mechanically in the converter (`MIN_MOTION_PX`), which only became defensible once the Session J threshold reproduced on these 49 independent gaps (bimodal, valley at 9-16 px). Evidence: data/output/farcourt_l2.md |
| Filling far-court labels by interpolating between anchors | **MEASURED NEGATIVE, and it closes a shortcut that looked free.** 89% of the 4,087 missing far-court training frames sit in bridges of ≤10 frames with a confident detection on *both* sides, so recovering them from the anchors would have cost no human time. Scored against human gold clicks (n=73 bridged positions, 3 calibrated clips): median error 5–9 px but **p90 46–95 px, max 396 px, and only 63% land within 10 px**. A label that wrong is a Gaussian on empty court — worse than no label. And accuracy is **flat across bridge length** (62 / 60 / 64% for 1-2 / 3-5 / 6-9 frames), so there is no short-gap subset to rescue. Human far-court labels are now *measured* to be required, not assumed. Evidence: data/output/farcourt_label_yield.md |
| Improving CourtNet for auto-calibration | Wrong target. CourtNet is **Tier 2**; `courtfit` consensus is Tier 1 and beats it on this footage — CourtNet returns nothing on three clips courtfit nails at 8/8, 7/8 and 6/8. |
| Finding burned-in graphics by any temporal statistic | **All three fail on this footage, in both directions.** These clips are edited compilations with cuts and auto-exposure, so per-pixel std has *nothing* below 6/255 on 3 of 12 clips (two of which carry an obvious scoreboard) while on the locked-off-camera clips **45–57% of the frame** is below it and a variance mask paints the COURT. Median-agreement is better and still splits the same way; correlation with global exposure — the principled version, since a composited graphic should not track auto-exposure — flags **26–65%** of the frame on 7 of 12, because any pixel a player walks through is dominated by the player. Adding geometry (small, border-flush, rigid-against-a-non-rigid-surround, structured) makes the rule *safe* but not *complete*: it finds the SwingVision watermark on every clip that has one and **none of the six score panels**, which sit over sky or dark stands. Twelve fixed clips, so the rest are hand-authored and verified by eye. Evidence: data/output/farcourt_hud_mask.md |
| Screening far-court gaps by lock kinematics | **Two measured negatives, and they are why the anchor control is label-time rather than selection-time.** Local roam (`inspect_false_locks.describe`, ±8 frames) over the 12 pilot gaps: confirmed anchors **14.0–220.2 px**, unconfirmed **13.2–238.8 px** — fully overlapping at both ends, because a genuine far ball's per-frame excursion is small. And `ball.suppress_false_locks` requiring both anchors to survive keeps **1 of 5** confirmed gaps: the min-segment test needs a run of consecutive locks and the frame after a gap starts a new short segment by construction, so anchor `b` is dropped on 8 of 12 gaps as an artefact of *being* an anchor. |

---

## Open, and what each is waiting on

| Item | Waiting on |
|---|---|
| **Far-court recall** (detector fires on nothing in 24–27% of frames) | **Human far-court labels — now measured, not assumed.** The hole is **4,087 frames** (not "a few hundred"), which would grow far-court training data 43% but costs 4–5 hours of clicking. Automating it is a **measured negative**: 89% of those frames are bridged by confident anchors, but interpolating between them lands within 10 px only **63%** of the time, flat across bridge length (data/output/farcourt_label_yield.md). So: **rank, don't complete** — one frame per gap (1,259 gaps, not 4,087 frames; every frame in a gap is a near-duplicate), round-robin across clips. `tools/select_farcourt_labels.py` builds the queue into `data/labels/`; **a 12-gap / 36-frame pilot is waiting in the Lab**, all at source resolution (720p/1080p from `data/train_clips/`, not the 512×288 network input where a far ball is ~1.6 px and unclickable). Run it before committing hours: spot checks show the missed ball landing on background its own colour (white ball on white signage, dark on dark wall), so it may not be visible even at full res. **PILOT RUN, and re-adjudicating it changed the diagnosis.** The frames ARE readable at source resolution. But the HUD story is **RETRACTED**: re-checking every click against the pixels, **5 of 36** landed inside a burned-in graphic — not "every click on the four HUD clips" — and two of the four clips that table blamed carry **no overlay at all**. What 11 of 29 ball clicks actually landed on is empty sky, foliage, flat court or a floodlight, and the reason is that **the ANCHORS bracketing those gaps were themselves false locks** on a wall, a hedge, a parked car. The queue selects a gap when the tracker is confident on both sides, and about half the time that is two false positives. Split by the human's own verdict on the anchors: **at least one anchor confirmed → 5 of 5 midpoints are on a real ball; neither confirmed → 0 of 7**. The queue already collected that control and nothing read it. Now enforced by `tools/farcourt_labels_to_dataset.py`, plus HUD masking (`tools/mask_hud.py`, gate passed on 19 boxes × 4 real frames) and a mechanical quarantine of the pilot's labels. Frame extraction was ruled out first: **0 of 36** queue frames mismatch their claimed source frame. Evidence: data/output/farcourt_anchor_audit.md, farcourt_hud_mask.md. **A 12-gap masked re-run is waiting in the Lab (`farcourt_pilot2`)** — same 12 gaps, so it is a controlled test of the mask. Any training run that follows must pre-register a **ghost-ball gate**: teaching the detector to fire where the ball can't be seen is one step from teaching it to hallucinate an arc. |
| **9 solid ghost balls — and we now know why nothing removes them** | **All 19 chain false locks have `run_len = 1`** (roam 208–829 px) — by the tool's own legend, *"a real ball scores high roam and short run; a fixture the reverse"*. Every survivor carries the kinematic signature of a real ball, so `suppress_false_locks` cannot touch them without also deleting single-frame real-ball sightings — the far-court balls we are already short of. That is why nine downstream attempts failed (all test for non-ball-like behaviour) and why detector work does not reach the product (this is the one-off *tail*, not the bulk error rate). Composition: **five frames defeat all three models** (yt_rally2 18/762/1494, yt_match40 4773, am_hard_utr 13276) and they are **not one object type** — 3 static scenery, 2 person-attached — so racket negation reaches 2 of 5. Two of the five may be *mislabels* (a ball-sized object beside a mid-swing player on a "no ball" frame); that is a Lab re-label question, not a model fix. **Read Trap 9 first**: at 74 no-ball frames the gate can only see a near-elimination. |
| **Confirming the localised-weighting detector win** | **~2h20m of GPU, and it is now well-motivated** — a −11.7 pt pooled false-fire effect on 6 of 6 clips is large enough to confirm or kill cleanly. Re-run the pair with the new `--seed 0` on both arms so the flag is the only difference, plus a third arm at `--seed 1 --hard-weight 1.0` (~1h10m) to measure how far two *identical* recipes drift — without that floor a paired difference still cannot be sized. Do NOT spend the ~12h on a 40-epoch pair until this comes back. |
| **~~Whether the +5.6 pt recall gain reaches the product~~ — ANSWERED: it does not** | Chain test run 2026-08-13 on all three calibrated clips (data/output/chain_ab.md). **GATE FAILS: pooled solid ghosts 9 -> 13**, chain recall **66.9% -> 66.9%** (exactly flat). `ballnet_v21.pt` stays the default; arm B is NOT shipped. v21's 9 reproduces the standing figure exactly, checking the measurement chain. The clip that collapses is **am_hard_utr, the 1.74 m 1080p amateur mount this project targets: 1 -> 7 solid ghosts**. Caveats the tool flags: the clips disagree in sign (+6/+1/-3) and only 4 of 18 ghost frames overlap, so this is "arm B did not clear the bar", not "more data makes ghosting worse". |
| **Whether more data is what actually caused it** | **n = 1 training run per arm.** `--seed 0` on both fixes initialisation and seeds the shuffle, which is a real improvement on Session I's unseeded pair, but the datasets differ in size so batch composition and augmentation draws still differ, and the 9-of-10 per-clip sign test measures *evaluation* noise. Also: each arm's checkpoint is its own best epoch on its **own** validation split (A epoch 6, B epoch 12), and B's val contains the new venues. A `--seed 1` replication of arm B (~1h52m) would size the run-to-run floor; the effect is 4.1σ against evaluation noise, so the question is whether training noise is anywhere near 5 pts. |
| **Whether a better detector can reach the ghost ball at all** | Three interventions have now cut detector false fire substantially and delivered nothing to the rendered output. Before the next detector idea, establish *which* stage absorbs it — the tracker gates and `suppress_false_locks` are the suspects, and `fire_frames_solid` plus the per-gate miss counters can answer it without new training. |
| **Second-disk copy of the training data — DONE 2026-08-15; off-machine still open** | **The figures in this row were badly stale and the risk was bigger than recorded**: measured, `data/train_clips/` is **20 videos / 2.73 GB** (not 12 / 1.06) and `data/ball_dataset/` is **73,098 files / 3.45 GB** (not 43,904 / 2.0). Both gitignored, tracked by nothing. The dataset is nominally regenerable from the videos (`relabel_train_clips.py`) but re-processing yields different pseudo-labels, so treat it as semi-irreplaceable too. **DONE — both now copied to `C:\SwingPath_Backup\`, a physically separate disk** (E: Gigabyte / C: Kingston, both NVMe): `train_clips` all **21 files verified by SHA256 manifest**, `ball_dataset` all **73,098 files / 3.45 GB verified by count and byte-sum**. That retires **single-disk failure**, the dominant risk. **STILL OPEN:** same machine, so fire, theft and ransomware are uncovered — needs an external drive or cloud target. (Gotcha for whoever repeats it: `robocopy` exits **1** on a successful copy, so a wrapper that trusts the exit code reports a false failure.) |
| **Bounce detection** | No true ball height from one camera. Unevaluated candidates: audio impact (module exists, unwired), monocular 3D. |
| **Speed coverage is CHAIN-shaped, and the two stages are named** — *the best-measured open target* | **ATTRIBUTED 2026-08-15 on the population that matters.** `seen_frac` over the whole hit→landing span must be ≥50% for a trusted speed. Counting it at every chain stage: on **am_hard_utr** mean coverage goes **raw 75.5% → 72.1 (rectify) → 64.9 (suppress) → 64.9 (court gate, ZERO cost) → 52.9 (smoother)**, and shots clearing the gate go **106 of 120 → 69**. **yt_match40 is the same shape** (79.3% → 59.7%, 182 → 124). So **the detector already covers 88% of shots on the target clip and only 58% survive the chain — 37 shots lose their speed to the chain, not the detector.** Per-stage, identical order on both clips: **`smooth_forecast` largest (−12.0 / −9.7 pts), `suppress_false_locks` second (−7.2 / −8.1), court gate exactly zero** (reproducing Session G part 3); the two own ~85%. This **supersedes the post-bounce framing** — that window is the minor failure mode worth 3–4 pts, this is worth **20–23**. NO FIX PROPOSED: two smoother attempts have already failed because loosening the gate buys coverage and pays in ghosts, and this measurement does not change that trade, only its size. A third attempt needs a mechanism that **separates** real from false better, not one that admits more of both. Evidence: data/output/post_bounce_chain.md (part 3) |
| ~~**Speed coverage — and it is CHAIN work, not detector work**~~ (superseded by the row above) | On yt_match40, **speed is not trusted for 95 of 196 shots (48%)**, the largest named reason being losing the ball *after* it lands, which closes the hit→landing span a path integral needs. **MEASURED 2026-08-15, and it settles the scoping question**: of those 95, **77 (81%) had the detector firing past the bounce and the chain discarded it**; only **18 (19%)** had a silent detector. Over ALL 196 shots the detector is present past the bounce on **90%**. (`ball_px` from the committed perception cache is the tracker's output BEFORE `suppress_false_locks` and before the Kalman, so this is exactly the "existed vs survived" split.) So this is **open chain work**, NOT the detector work the Session L stopping rule closed — and it shares a root cause with the dead second-bounce rule below. The −15% bias is average-vs-launch physics and must **never** be corrected away. |
| **Court auto-detection** | **Closed as a model problem.** Tier 1 (`courtfit` consensus) auto-accepts **11 of 20** gold clips with a perfect precision record (3.4–13.9 px, zero wrong courts ever accepted); the 6/8 bar is verified correct. The remaining 9 clips refuse, and refusal costs ~30 s in the setup tool. CourtNet (Tier 2, 20.2% held-out detect) is the weaker path and is not worth improving. |
| **8 court gold frames are mislabelled** | `am_indoor_hard1` frames 9204/10093/10982/11871/12760/13649/14538/15427 are marked `court: false` but plainly show a full usable court (3 of 3 inspected). Needs re-labelling in the Lab — a minute of human time. Until then that clip's `false%` is not a valid metric. |
| **Rally segmentation over-splits ~1.6x — and the layer has NO ground truth** | Researched 2026-08-13 (data/output/rally_scoring_research.md). `segment_rallies` splits on a hit-to-hit time gap and on a second-bounce force-break; on yt_match40 **62 of 62 breaks came from the time rule and 0 from the force rule**. The suspect is named: `pipeline.py:1868` overrides `gap_s` to **2.0 s**, and within-rally intervals run median 0.97 s, p90 1.69 s, **max exactly 2.00** — a distribution truncated at the threshold. 30 of the 62 breaks came from gaps of only 2-3 s, ordinary for a deep defensive ball. SIZE OF THE DEFECT, counted from the clip's own burned-in scoreboard (distinct panel pixel-states, no OCR): **~35-40 real points vs 63 rallies, so ~1.6x**. **WHY THE TENNIS RULE NEVER FIRES — measured 2026-08-15.** It is NOT structurally dead: `next_hit` is the next hit anywhere in the clip, so the window does span the dead time, and in **46%** of rallies the ball survives the rule's 0.25 s minimum. It **starves**. After a rally's final bounce the ball stays tracked for a median of **5 frames (0.17 s)** — p25 **1**, p75 16, p90 36 — and only **14%** of rallies keep it a full second, while registering a SECOND bounce needs the ball tracked through a whole down-up arc. **Same root cause as the speed-coverage row: the chain stops following the ball shortly after it lands.** Fixing that would let segmentation follow the actual tennis law instead of a 2 s timeout, and needs no ground truth to attempt. **THE BLOCKER FOR SCORING IT IS THAT NOTHING CAN SCORE THIS.** Ball has 1851 human clicks, court has 20 clips, speed has the HUD and synth_truth; rallies and score have **nothing** - no point boundary has ever been labelled. But **3 of 10 gold clips carry a burned-in point-by-point score** (am_hard_utr ANIRUDH/JACK games+points+server dot, yt_match40 D. Tan/Opponent, gold_sAjkpeRq4P4 FRANK), which is free exact truth for point boundaries, per-point winner, the score state machine AND who is serving - and `hud_ocr.py` already implements the right technique (fixed font, static panel, glyph templates, no OCR dep). Build the reference before touching `gap_s`. |
| **Trimming was the missing first step** | The Lab could *sample frames from inside* chosen time ranges but never *cut the video*, so an hour of phone footage stayed an hour and every perception pass decoded the warm-up and the breaks. `tools/trim_clip.py` + a Trim control in step 1 of the guided flow. It **re-encodes by default**: with `-ss` before `-i` and `-c copy`, ffmpeg snaps to the keyframe at or before the start, so the clip begins early *and ends early* — the exact bug already found once in the highlights cutter. Verified frame-accurate against the pixels (trim frame 0 == source frame 300 for a 5.0 s start at 60 fps, duration 7.00 s to the frame). `--fast` restores stream copy and says what it trades. |
| **Phone app shell** | App development, not ML. The model export and call logic are done and verified bit-identical in JS; no phone fps has ever been measured, so do not quote one. |
| ~~**Processing 60 fps clips at full rate**~~ — **DECIDED 2026-08-15: shipped opt-in as `--full-rate`** | The product call was made rather than measured further, because the measurement was already complete: `max_gap_s = 0.4` is correct at 60 fps on both native-60fps gold clips, so no re-tune was needed. 60 fps wins the MEASUREMENT (arc reproj 148 → 91 px, HUD speed MAE 38.9 → 33.1%, bounce error −24..−35%, +5.8 pts close-call accuracy at a 1.5 m mount) and is a wash-to-negative on DETECTION (yt_rally2 recall +2.7, far_geo −1.7, false-fire +7.7), at 2× perception cost. **Opt-in, not default** — the default stays `auto` until a full match has been run end to end at full rate. See "What has worked". |

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
5b. **Trusting the flat z=0 projection for an AIRBORNE ball.** Measured against
   simulated truth: back-projecting the whole arc onto the court plane and
   integrating path length reads **+72% median, p90 +25,000%** — a near-grazing ray
   runs to infinity. Under 1 m of height it is +15% bias. This is precisely why
   `gate_ball_to_court` and the physics arc fit exist, and why the `approx` speed
   path is a floor rather than a measurement.
6. **Letting the test set into the training set.** The ball side has enforced a one-way
   gold/train split since Session 2. The COURT side never did: **17 of the 20
   hand-labelled court gold clips were also in `data/court_dataset/`**, and
   `train_courtnet.py` had no guard at all, so every figure in
   `data/gold/court_scores.md` was the model scored on its own homework. Fixed
   2026-08-06 with `data/gold/court_split.json` + `assert_no_court_gold_leak()`. The
   lesson generalises: a discipline enforced on one model is not enforced on the
   project. Check each new model for its own guard.
7. **Fanning out to parallel agents.** The bottleneck here is one GPU and one gold set,
   not context. Two multi-agent research runs burned ~971k tokens and returned **zero**
   results; the same research done inline took two searches and four fetches.
8. **Scoring on a population where the decision is easy.** Pooled line-call agreement
   reads **87–99%** across camera heights from 1 m to 12 m — it cannot tell a worthless
   mount from a good one, because most simulated bounces land nowhere near a line and
   metres of error still call them correctly. Restricted to bounces within 0.5 m of a
   line it reads **54% → 81%** over the same range. This is the same shape as
   "per-frame false-fire is not the product" (Session F): *pick the population where
   the answer is actually in doubt.* And **always state the majority-class floor** — on
   that population, answering "in" every time scores 56.2%, so the 1 m camera's 54% is
   not "slightly better than chance", it is worse than a constant.
9. **Calling "no effect" without checking the test could have seen one.** The solid-ghost
   gate has been run **nine times** and never once alongside its own resolution. It is a
   count of ~14 out of **74** no-ball frames, where sampling alone moves the count by
   **±3.4**: near-elimination is detectable (needs 62 frames), but *halving* the ghost
   rate needs **212** frames and a 30% cut needs **656**. So nine null results license
   only "nothing has come close to eliminating the ghost ball" — not "none of these did
   anything". `tools/gate_verdict.py` now prints the required-n next to the verdict so
   the claim can never again outrun the evidence. Contrast the detector table, where 204
   no-ball frames over six clips resolved an 11.7-point effect comfortably: the method
   is fine, the *chain* metric is just restricted to three calibrated clips.
10. **Running an A/B with more than one variable.** `train_ballnet.py` had **no seed** —
   no `manual_seed`, no `random.seed` — so Session I's two arms differed by weight
   initialisation, batch order and augmentation draws as well as by the flag under test.
   The tell was the three clips disagreeing in **sign** on every axis. Same family as the
   `ballnet_v21.pt` provenance gap that forced the session to spend an hour training its
   own control. Fixed with `--seed` and `recipe_stamp`; the standing rule is that a
   checkpoint must say how it was made, and an arm must differ from its control in
   exactly one recorded way.
11. **Reading a clip-level correlation as the cause.** The far-court pilot's clips split
   cleanly into "human agreed with the tracker to 0.6–7.2 px" and "human was 112–645 px
   out", and the split was attributed to the four clips carrying a burned-in scoreboard.
   It was really the four clips where the tracker had been tracking a **ball** rather
   than a wall — two of the "HUD" clips have no overlay at all. The fix that followed
   from the wrong cause (mask the graphics) is worth 5 of 36 labels; the fix that follows
   from the right one is worth 21. **When a per-clip split explains a result, check the
   per-FRAME pixels before naming the variable** — clips differ in many ways at once, and
   n=12 clips is one observation of each.
17. **Trimming a clip renames it, and the gold guard matches on the NAME.** Caught
   live, not hypothetically: gold clip `hd_shortcourt_1` is `7 UTR vs 8 UTR
   [UHf0LeMU2pg].mp4`, a training set had been built from `UHf0LeMU2pg.mp4` — the same
   match, cut shorter — and `assert_no_gold_leak` reported **no leak**, because the
   filenames differ. Every one of the 12 clips trimmed that day carried the same hole,
   so the exam set was one training run away from being inside the revision. The guard
   was correct for the world it was written in, where `data/` held whole recordings
   under their own names; cutting clips created a lineage the identity check could not
   see. Fixed by recording {cut: source} in `data/train_clips/lineage.json` at cut time
   and expanding gold through it. **A provenance check keyed on a name breaks the moment
   the pipeline gains a step that renames things** — and the new step will not know it
   is supposed to tell the old check.
16. **A default that is silently wrong for a whole new pool.** `validate_new_clip`
   looked for a clip's video at `data/<tag>.mp4` only, and fell back to "assume 1280x720"
   when it missed. The new training footage lives in `data/train_clips/` and is all
   1080p, so every calibration the user hand-placed audited at the wrong resolution and
   came back **DEGENERATE, fit residual 15.9-56.3 px** — nine of them, i.e. the entire
   session's manual work. At the true 1920x1080 the same files read **0.3-6.5 px, six
   PASS and three LOW-CAMERA**. Corners are pixel coordinates, so every geometric check
   is resolution-dependent; the fallback was reasonable when `data/` held every clip and
   became a lie the moment a subdirectory appeared. It now searches the directories clips
   actually live in. **A fallback that cannot tell "not found" from "found and fine" will
   eventually indict good work** — and the tell was that ALL of them failed, which is
   almost never what a real quality problem looks like.
15. **Re-implementing the thing you are trying to predict.** `audit_new_clips.py` was
   written to tell a user which new clips will auto-calibrate. Its first version drove
   `auto_fit_frame`/`consensus` by hand instead of calling `pipeline._sample_calib_frames`
   + `courtfit.fit_video_frames`, and sampled 15-85% of the clip where the pipeline
   samples 2-98%. It reported **1 of 12** clips calibrating; the shipped path gets more,
   and two clips flipped from refuse to accept once it called the real code. An audit
   that disagrees with the product is worse than no audit — it sends you to hand-calibrate
   clips that calibrate themselves. **Predict a behaviour by invoking it, never by
   re-deriving it.** Related: the same tool first reported a confident camera height
   (4.35 m, close calls 74%) from a **2-of-8** consensus, against a bar measured at 6 —
   a wrong court yields a wrong height that looks exactly like a right one.
   **IT HAD ALREADY HAPPENED IN THE SHIPPED CLI, and nobody looked** (found 2026-08-14).
   `run.py check` — the user-facing pre-flight — read ONE frame through
   `detect_court_learned` -> `detect_court`, while `analyze` runs `courtfit`
   consensus over 8 frames and accepts only >=6 agreeing. Measured on demo30 with no
   keypoints: the old check returned a court and graded it `[POOR] elevation 2.68`,
   while analyze **refuses the clip outright**. So the pre-flight's verdict was about a
   court the product would never use, and a user could act on either answer. Fixed by
   calling `pipeline.calibrate_video` itself. **The tell was that the audit tool got
   this exact fix a session earlier and the CLI was never checked for the same shape** —
   when a trap is found in one caller, grep for the other callers of the thing it was
   re-deriving, because the pattern is a habit, not an incident.
14. **Judging a filter by what it KEPT.** Three versions of the play-segment finder
   were written for the nine new match uploads. Each reported a plausible kept-percentage
   and each was wrong in a way the percentage could not show: version 1 discarded real
   tennis on 6 of 9 clips, version 2 on 5 of 9 — including **ten minutes of rallies from
   one clip while reporting 58% kept**. Both were caught the same way, by rendering the
   frames they THREW AWAY rather than the ones they kept. The root cause was shared:
   "looks unlike the average frame" is not "is not tennis", and over half an hour outdoors
   shadows crawl and exposure drifts. The fix was to detect the thing being REMOVED (a
   face filling the frame) so the failure mode flips to keeping too much. Even that has
   blind spots the count cannot reveal — a face in profile, and a sponsor read that cuts
   to close-ups of a book with no face in it at all. **Always inspect the rejects.**
12. **Scoring a HUMAN against a model, which is self-grading wearing a disguise.** The
   far-court queue accepts a labelled gap when the human's click on an anchor agrees
   with the tracker's position there. On the masked re-run that agreement rate went
   **42% → 75% on the same twelve gaps** — and inspection showed at least two of the
   flips were the human clicking a static wall mark or a window, on one clip the *same*
   mark the tracker had locked onto, agreeing to 2–5 px. A labeller who cannot find the
   ball clicks the most ball-like thing in the frame, which is what the detector locked
   onto for the same reasons, so agreement rises while truth does not. The tell was
   motion: human clicks moved **1–8 px** across a gap where the tracker's own prior moved
   **60–583 px**. Rule 1 of ML_PRACTICES applies to human graders too — *what independent
   ground truth is this measured against?*
13. **Reusing a verification method across a change of scale.** The round-trip check for
   "is this built sample the frame the human labelled?" reached for the dHash that
   verified the window mapping in Session I. That question was ±1600 frames and a
   different scene; this one is ±1 frame on a 60 fps static court, where **every
   candidate frame reads 14 bits** and JPEG plus the 1080p→512×288 resize contribute 6–8
   of their own. The test would have passed identically whether the mapping was right or
   wrong. Replaced with an argmin of mean-abs-diff over ±3 frames, which resolves it —
   and which reports its margin, so a frozen scene declares itself unresolvable instead
   of quietly passing.
18. **Reading a crop as if it were the frame.** Reviewing arm B's 166 false fires from
   140 px context tiles, four `am_hard_utr` locks looked like close-ups of a face and
   were written up as "the clip cuts to commentary — footage no ball detector can be
   scored on", with a follow-on recommendation to trim the old gold clips. Pulling the
   **full** frames killed it: every one is an ordinary wide tennis shot with a player
   walking past the near corner, whose head fills a 140 px tile taken from 1920×1080.
   The shipped face test agreed — 0 big faces in all 308 no-ball frames — and the
   correct response was to believe it and go look, not to assume the cascade had missed
   a cap and sunglasses. Same shape as calling the user's hand calibrations misplaced
   from 560 px thumbnails, twice. **A crop is evidence about a crop.** Before any claim
   about what a frame *is* — a cutaway, an overlay, a scene cut — render the frame.
   (The overlay version of the same hypothesis was then killed by measurement rather
   than by eye: several gold clips do carry a burned-in scoreboard, but only **1 of 166**
   locks lands in the top-left corner where they sit, and 17 anywhere in the outer 12%
   band. Burned-in graphics are not where these false fires come from.)
19. **Reading a detection RATE as evidence the detector found the right thing.** Session G
   part 4 reported "stock racket detection genuinely works on this footage — a racket is
   found on 64–100% of sampled frames per clip, so the ceiling here is the CRITERION, not
   the detector", and that sentence shaped two sessions of follow-up. Re-measured: on the
   clip where racquet confusers dominate, a racket is found on 79.5% of frames and sits
   **737–869 px** from the lock every time. It was finding the near player's racket while
   the ball detector fired on the far player's. A coverage percentage answers *did the
   model output something*, never *did it output the thing this argument needs*. **Score
   the association, not the presence** — distance from the lock to the nearest box was one
   line of code and reverses the conclusion.
20. **Inferring a defect's SIZE from an assumption about the footage.** Rally
   segmentation was written up as "63 rallies where reality is 8–15 points, the score is
   badly wrong" — from a real symptom (0 of 62 inter-rally gaps ≥10 s) plus an unstated
   assumption that the clip contained unedited between-point dead time. It does not: only
   **12%** of yt_match40's human-labelled frames are no-ball, where an unedited match is
   mostly dead time. The clip's own burned-in scoreboard puts the truth at **~35–40
   points against 63 rallies — a 1.6× over-split, not 5×**. Two further numbers in the
   same write-up were artefacts: the "median gap 0.00 s" measured `start_s − end_s` where
   `end_s` is the last shot's *bounce*, not the criterion the code splits on. **Before
   sizing a defect, establish what the correct answer is** — here it was sitting in the
   pixels of three clips, free.
21. **Re-deriving a rule instead of sharing it — then trusting the copy over the pixels.**
   `build()` numbers each training triplet by its POSITION in the usable-frame list and drops
   `unsure` labels; the round-trip gate re-derived that list and KEPT them, so on any clip
   with an unsure label every later sample was checked against the wrong source frame. It
   presented as a clean, alarming **+2/+3 frame offset with a 20–30% lead** — exactly what a
   real data corruption looks like — and the first response was to write it up as one and
   plan to exclude the clips. What settled it was **sequential decode from frame 0**, the one
   read path that uses no seeking: `build()` was exact to **MAD 0.0000**. The tell had been
   free all along — the only two clips that failed were the only two with an `unsure` label,
   and all 19 with none passed. **When a checker and the thing it checks disagree, the checker
   is a suspect too**, and a rule with two implementations will eventually have two meanings.
   Now one function, `labels_to_dataset.usable_frames`, called by both, with an assertion in
   `build()` that it still selects exactly what gets written.
