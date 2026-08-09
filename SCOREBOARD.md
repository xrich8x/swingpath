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
| **Synthetic ground truth** (`tools/synth_truth.py`) | first ABSOLUTE accuracy this project has had — every other number is agreement with a human. Line calls **95.9%** correct, bounce **0.75 m** median, and the −15..−20% speed rule confirmed as physics (drag = **−21.7%**) | 2026-08-06 |
| **Court TEST/TRAIN split + leak guard** | court numbers became measurable at all — 17 of 20 gold clips had been in training | 2026-08-06 |
| **Camera-height curve** (`tools/height_curve.py`) | turned the setup tool's *bound* into an *error*. Close-call accuracy by mount height, measured against known bounces: **54% at 1.0 m → 69% at 3 m → 81% at 8 m**, bounce error **3.81 m → 0.37 m**. A 1.0 m mount is **below the 56.2% majority-class floor** — its close calls carry no information. Now surfaced in every `setup_verdict` | 2026-08-07 |
| **Frame rate isolated from detector dropout** | 30 → 60 fps is worth **+5.8 pts** of close-call accuracy at 1.5 m, +3.2 at 3 m, +1.8 at 12 m, and cuts bounce error **24–35%** — holding at both dropout levels, so it is not dropout in disguise. For scale, a *perfect* detector buys +4.7 / +2.5 / +2.2 at the same heights: **doubling the frame rate we already have is worth about as much, and is free.** Confirmed end to end on yt_rally2 — arc reproj **148 → 91 px**, HUD speed MAE **38.9 → 33.1%** | 2026-08-07 |
| **Per-rally clips + highlights reel** (`run.py highlights`) | the last unbuilt product feature. Dead time disappears: every rally becomes a playable clip, ranked deterministically (shot count → top *confident* speed → duration), with a top-3 reel. ffmpeg **stream copy**, so cutting is I/O-bound rather than a 5–10× re-encode. The manifest records requested vs actual start, so "a clip never opens mid-rally" is **checked**, not asserted | 2026-08-08 |
| **Manual-correction UI** (Review tab + `run.py correct`) | closes the oldest known gap. Edits FACTS only; score is replayed through `scoring.TennisScore` and stats through `schema.compute_stats`, so there is no second implementation of the rules. Verified end to end: demo score 2-5 → 3-4, line calls 108/17 → 107/18, and re-applying the same file is a no-op | 2026-08-06 |

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
| Tightening it to the racket **HEAD** | **The head is not the discriminator.** On the wrist→head axis, racquet locks sit at median **0.57** and real balls at **0.55** — indistinguishable. Every tightening costs more catch than collateral (cut 0.5 → catch 36.4%, collateral only 4.5→2.6%). The whole box is the best version of the idea; 54.5%@4.5% is its ceiling. |
| Raising `acquire_bound_m` 4 → 10 m | Static analysis said free; end to end it bought +0.6 pt recall for +1.9 pt false-fire. |
| Blur augmentation alone | Dead end on its own; only pays off combined with occlusion work. |
| Retuning `max_gap_s` for 60 fps | **GATE FAILS on replication.** 0.60 looks like a clean knee on yt_rally2 (ghost flat at 8 from 0.20–0.60, recall +1.9) and passes the gate there — then on am_hard_utr it costs **+5.6 pts false-fire and +3 ghosts for +0.5 recall**, with no flat region at all. 0.4 stays, and full-rate 60 fps therefore needs **no** rate-dependent gap policy. |
| Lowering the court consensus bar 6/8 → 5/8 | **GATE FAILS.** Exactly one 5-vote clip exists and it is wrong by **68.7 px**, against 3.4–13.9 px for every clip at ≥6 votes. Nothing lands in the gap. The bar is empirically correct. |
| Raising the detector's input resolution | **Gate B FAILS on both clips.** At the detector it looks like a large free win — 512x288 → 640x360 is **+8.2 pts far_px**, with operating points that dominate the shipped one outright (same precision for +5.4 recall, or same recall for −14.2 false-fire). End to end the shipped setting **dominates every variant**: the chain was already removing those false fires, so the precision gain is absorbed and the recall gain arrives as extra SOLID ghosts (5→7 on yt_rally2, 1→5 on am_hard_utr). E3f's "per-frame recall is not the bottleneck" still stands. Evidence: data/output/phase0_ball_ceiling.md |
| Tightening the smoother gap to cut ghosting | Pooled, 0.10 s halves ghost frames (21.5% → 11.4%, zero interpolated) but drops recall to **60.3%** — at 60 fps that is the ball drawn on 36 of every 60 frames *during a rally*. It does not remove "insane", it relocates it from dead time to mid-point, where the user is actually looking. Also: single-digit false fire is **not reachable by tuning** — pooled floor is 11.4%, because the 9 solid ghosts are the detector. |
| Mining `suppress_false_locks`' rejections as hard negatives | **GATE FAILS, and it corrects an over-attribution.** A first estimate of 77.3% catch was withdrawn — it differenced raw against the FULL chain, crediting suppression with the tracker gates' work too. Measured in isolation on matched populations: persistence 7.5% catch / 5.7% collateral (it costs more real balls than confusers it catches — it detects things that hold still, and these move), min-segment 32.5% / **2.4%**, both 40.0% / 8.1%. Catch tops out 20 pts under the bar. **Three distinct automatic criteria have now failed** — skeleton position, racket box, trajectory plausibility — so there is no cheap automatic signal separating a swung racquet from a ball. Evidence: data/output/phase0_ball_ceiling.md |
| Mining whole-frame hard negatives at all | **Gate C fails, and it names the root cause.** Purity depends on the base rate, and the training clips are **88.5% ball-present** (they are extracted rally clips). Enrichment: persistence 1.4x, min-segment 6.0x, both 3.7x — against a 10x bar. At the real base rate a mined pool is **43.7% pure at best**, i.e. over half real-ball frames. Every route has died on the same fact: dead-time frames are pure but hold no confusers, and confuser-rich frames are frames with tennis being played. **The whole-frame negative format asks about the FRAME when the useful question is the LOCATION.** |
| Localised confuser weighting (Session I) | **PRODUCT GATE FAILS — pooled solid ghosts 14 → 15 (+1) at flat recall (69.2 → 69.0%).** Ninth failure at the ghost ball. **BUT THE DETECTOR IMPROVED, on 6 of 6 gold clips**: false fire 53.9 → **42.2%** pooled (−11.7 pts, 110 → 86 of 204 no-ball frames, 3.4σ) at *higher* recall (79.9 → 80.4%) and far_px (80.9 → 82.5%) — the operating point moved outward on both axes, not a precision-for-recall trade. **NOT ATTRIBUTABLE YET:** one training run per arm and the trainer had **no seed**, so the arms differ by initialisation and batch order as well as by the flag; the 6-clip sign test measures evaluation noise, not training noise. `--seed` now exists so a future pair is paired. Evidence: data/output/session_i_ab/results.md |
| Expecting a detector precision gain to reach the product | **Three for three, and the mechanism is consistent.** Input resolution (Phase 0 gate B), `score_thresh` (Session F step 3), and now localised weighting: each cut detector false fire substantially and each arrived at the rendered output as nothing or worse. On yt_rally2 the detector's false fire nearly halved (61.5 → 38.5%) while the same clip's tracker-gates-only row went the **wrong way** (30.8 → 38.5%). The chain's gates already remove the false fires a better detector removes — those are the easy ones — so what survives to be drawn is a different, harder population. **Detector precision and chain precision are close to decoupled.** Stop scoring ghost-ball work at the detector. |
| Filling far-court labels by interpolating between anchors | **MEASURED NEGATIVE, and it closes a shortcut that looked free.** 89% of the 4,087 missing far-court training frames sit in bridges of ≤10 frames with a confident detection on *both* sides, so recovering them from the anchors would have cost no human time. Scored against human gold clicks (n=73 bridged positions, 3 calibrated clips): median error 5–9 px but **p90 46–95 px, max 396 px, and only 63% land within 10 px**. A label that wrong is a Gaussian on empty court — worse than no label. And accuracy is **flat across bridge length** (62 / 60 / 64% for 1-2 / 3-5 / 6-9 frames), so there is no short-gap subset to rescue. Human far-court labels are now *measured* to be required, not assumed. Evidence: data/output/farcourt_label_yield.md |
| Improving CourtNet for auto-calibration | Wrong target. CourtNet is **Tier 2**; `courtfit` consensus is Tier 1 and beats it on this footage — CourtNet returns nothing on three clips courtfit nails at 8/8, 7/8 and 6/8. |

---

## Open, and what each is waiting on

| Item | Waiting on |
|---|---|
| **Far-court recall** (detector fires on nothing in 24–27% of frames) | **Human far-court labels — now measured, not assumed.** The hole is **4,087 frames** (not "a few hundred"), which would grow far-court training data 43% but costs 4–5 hours of clicking. Automating it is a **measured negative**: 89% of those frames are bridged by confident anchors, but interpolating between them lands within 10 px only **63%** of the time, flat across bridge length (data/output/farcourt_label_yield.md). So: **rank, don't complete** — a few hundred frames stratified across clips buys most of the diversity in 30–40 min. Any such training run must pre-register a **ghost-ball gate**: teaching the detector to fire where the ball can't be seen is one step from teaching it to hallucinate an arc. |
| **9 solid ghost balls — and we now know why nothing removes them** | **All 19 chain false locks have `run_len = 1`** (roam 208–829 px) — by the tool's own legend, *"a real ball scores high roam and short run; a fixture the reverse"*. Every survivor carries the kinematic signature of a real ball, so `suppress_false_locks` cannot touch them without also deleting single-frame real-ball sightings — the far-court balls we are already short of. That is why nine downstream attempts failed (all test for non-ball-like behaviour) and why detector work does not reach the product (this is the one-off *tail*, not the bulk error rate). Composition: **five frames defeat all three models** (yt_rally2 18/762/1494, yt_match40 4773, am_hard_utr 13276) and they are **not one object type** — 3 static scenery, 2 person-attached — so racket negation reaches 2 of 5. Two of the five may be *mislabels* (a ball-sized object beside a mid-swing player on a "no ball" frame); that is a Lab re-label question, not a model fix. **Read Trap 9 first**: at 74 no-ball frames the gate can only see a near-elimination. |
| **Confirming the localised-weighting detector win** | **~2h20m of GPU, and it is now well-motivated** — a −11.7 pt pooled false-fire effect on 6 of 6 clips is large enough to confirm or kill cleanly. Re-run the pair with the new `--seed 0` on both arms so the flag is the only difference, plus a third arm at `--seed 1 --hard-weight 1.0` (~1h10m) to measure how far two *identical* recipes drift — without that floor a paired difference still cannot be sized. Do NOT spend the ~12h on a 40-epoch pair until this comes back. |
| **Whether a better detector can reach the ghost ball at all** | Three interventions have now cut detector false fire substantially and delivered nothing to the rendered output. Before the next detector idea, establish *which* stage absorbs it — the tracker gates and `suppress_false_locks` are the suspects, and `fire_frames_solid` plus the per-gate miss counters can answer it without new training. |
| **Bounce detection** | No true ball height from one camera. Unevaluated candidates: audio impact (module exists, unwired), monocular 3D. |
| **Speed coverage** | Downstream of ball recall. The −15% bias is average-vs-launch physics and must **never** be corrected away. |
| **Court auto-detection** | **Closed as a model problem.** Tier 1 (`courtfit` consensus) auto-accepts **11 of 20** gold clips with a perfect precision record (3.4–13.9 px, zero wrong courts ever accepted); the 6/8 bar is verified correct. The remaining 9 clips refuse, and refusal costs ~30 s in the setup tool. CourtNet (Tier 2, 20.2% held-out detect) is the weaker path and is not worth improving. |
| **8 court gold frames are mislabelled** | `am_indoor_hard1` frames 9204/10093/10982/11871/12760/13649/14538/15427 are marked `court: false` but plainly show a full usable court (3 of 3 inspected). Needs re-labelling in the Lab — a minute of human time. Until then that clip's `false%` is not a valid metric. |
| **Rally segmentation over-splits** | Surfaced by the highlights cut: yt_match40 yields **63 rallies in 5.9 min** — one every 5.6 s, with a **median inter-rally gap of 0.0 s**. Contiguous "rallies" mean `events` is fragmenting continuous play, not finding points (real tennis is ~20-25 s between them). Pre-existing and independent of highlights, but it now has a number and a visible symptom. |
| **Phone app shell** | App development, not ML. The model export and call logic are done and verified bit-identical in JS; no phone fps has ever been measured, so do not quote one. |
| **Processing 60 fps clips at full rate** | **A product call, not more measurement.** The sweep is done: `max_gap_s = 0.4` is already correct at 60 fps on both native-60fps gold clips, so no re-tune is needed. What remains is a genuine trade nobody has decided — 60 fps clearly wins the MEASUREMENT (arc reproj 148 → 91 px, HUD speed MAE 38.9 → 33.1%) and is a wash-to-negative on DETECTION (yt_rally2 recall +2.7, far_geo −1.7, false-fire +7.7). It also doubles perception cost. |

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
