# CLAUDE.md

Project context for Claude Code. Read this before editing.

## Project docs — read the right one for the task

- **CLAUDE.md** (this file) — architecture, hard rules, current status. Read before editing.
- **[docs/STATE.md](docs/STATE.md)** — the LIVING record: the stack, and flat lists of
  what has and has not moved a number, what is open. One row per result, each naming its
  evidence file. This file's Status section is chronological; STATE is the consolidated
  state of play. **Update it in the same commit as the work it describes.** ENFORCED, not
  remembered: `.claude/hooks/scoreboard-guard.sh` refuses any commit that touches code
  without also modifying `docs/STATE.md`. Doc-, data- and config-only commits pass; put
  `[no-scoreboard]` in the message for a change that genuinely moves no number.
- **[docs/evidence/](docs/evidence/)** — one file per result: the mechanism, the war
  story, the caveats, the retraction narrative. **Never create a new top-level markdown
  file to record a result** — a result is a row in STATE plus a file here.
- **[docs/TRAPS.md](docs/TRAPS.md)** — **22** process failures this project hit **twice**,
  split out of SCOREBOARD on 2026-08-17 and re-keyed to stable IDs `T01`-`T22` on
  2026-08-26. Append-only history, unlike STATE's mutable state. **IDs are never
  reused and never renumbered** — cited from 13 files including code.
- **[docs/archive/](docs/archive/)** — frozen records: `HANDOFF.md`, the session briefs
  (all run), and `resolved/` for Open rows that have been answered. Never a work queue.
- **[README.md](README.md)** — what the project is + how to run it (quickstart, layout).
- **[ML_PRACTICES.md](ML_PRACTICES.md)** — how to *conduct* ML work: honesty, evidence
  tags, ground-truth-before-metrics, reproducibility, the session-end checklist.
- **[ML_PLAYBOOK.md](ML_PLAYBOOK.md)** — how to *think about* the ML: diagnosis buckets,
  per-area technique (ball/court/pose/physics), and the 2024-26 SOTA survey.
- **[docs/archive/HANDOFF.md](docs/archive/HANDOFF.md)** — historical evidence log (from 2026-07-05); the ML docs
  cite its `§` numbers. For *current* state use this file's Status + [docs/STATE.md](docs/STATE.md).

## REQUIRED READING before any ML work

Before you create, train, tune, or evaluate ANY model (ball, court, pose, spin,
or a new one), you MUST read **both [ML_PRACTICES.md](ML_PRACTICES.md) and
[ML_PLAYBOOK.md](ML_PLAYBOOK.md)** first and follow them. They are not optional and
not generic advice — every rule is there because this project already got burned by
breaking it. PRACTICES is the *discipline* (how to conduct yourself); PLAYBOOK is the
*technique* (how to diagnose and what to steal from the field). The load-bearing rule,
from PRACTICES: **never let a model grade its own homework** — score only against
independent human/gold labels, and state in one sentence what every number was
measured against.

## What this is

A single-camera **tennis** match analyzer. Backend turns a video into
`match.json` (shots, speeds, bounces, line calls, score); a React frontend
renders it. **Offline-first**: record, then process — no real-time requirement.

## Commands

# Backend (Python 3.12)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py demo --out ../frontend/src/data/sample_match.json   # synthetic data, no weights
python -m pytest tests/                                           # geometry + scoring tests

# Frontend
cd frontend && npm install && npm run dev

## The one principle: learn what you can't compute, compute what you can

Every stage is one of three kinds. Respect the boundary — it's the architecture.

- Perception (ML): court keypoints, player pose, ball tracking, shot type — models go here only
- Geometry (math): homography, projection, shot speed, line calls — closed-form; never replace with a model
- Logic (rules): scoring, rally segmentation, highlights — deterministic state machines

Do NOT "ML-ify" the geometry or logic layers — it adds error to exact answers.

## The second principle: learn the GAME, not the VIDEO

**Truth comes from the court — the ball, the players, the bounces, the physics.
It never comes from something a human or an app burned into the frame.**

A tennis video often carries two different things: the *game* (what the players
and the ball actually did) and *annotations about* the game (a burned-in
scoreboard, a SwingVision HUD reporting shot speed and stroke type, a graphic
someone rendered on top). The second kind is tempting because it is free,
exact-looking and already aligned to the frames. **It is somebody's data entry,
not a measurement of the court**, and it is out of bounds as a training target,
as a ground-truth reference and as a tuning signal.

Why, concretely:
- **Independence is not truth.** A burned-in scoreline is genuinely independent
  of anything we compute — and still only proves it is *self-consistent*. A
  diligently-kept WRONG board passes every internal check perfectly.
- **It encodes another system's errors and latency.** Tuning a rally threshold
  against point-boundary timestamps calibrates against *when somebody pressed a
  button*, reaction lag included. Copying a HUD's shot speed teaches us to
  reproduce SwingVision's estimator, including where it is wrong — a ceiling,
  not a target.
- **It does not generalise.** The user's own phone clip has no scoreboard and no
  HUD. Anything that leans on one works only on footage that already carries the
  answer, which is the footage that least needs us.
- **It leaks into training.** Five training clips carried a SwingVision overlay
  whose watermark is *a literal yellow tennis ball*, and 83 pseudo-labels landed
  inside those graphics — we were teaching the detector that a logo is a ball.
  Now scrubbed and enforced (`assert_no_swingvision_leak`).

Legitimate references, by contrast, all describe the court: **human clicks** on
the ball/court, **`tools/synth_truth.py`** (simulated flights with known
physics), and geometry we can derive ourselves.

**Applies to evaluation as much as to training** — the burned-in-scoreboard tool
was a *grading* tool and was still rejected on this premise (`afffb5a`). If a
number's provenance is "read off the video", it is not ground truth.

**Known live exception, flagged not hidden:** `tools/hud_ocr.py` reads
SwingVision's burned-in MPH panel and several shipped speed figures are measured
against it (ML_PRACTICES.md working-summary rule 11). Those numbers are *agreement with
another estimator*, not accuracy, and must be labelled that way; `synth_truth`
is the compliant reference for speed.

## Out of scope: the rally / score layer

**Ruled out by the user on 2026-08-20: the score layer is not important and will
not be worked on in any session.** It is not an open problem, not a backlog item,
and not something to research, diagnose or improve. Do not propose work on point
boundaries, rally segmentation, the `gap_s` override, the second-bounce rule, or
any ground-truth source for points.

What already exists keeps working and needs no attention: `scoring.py` runs the
tennis state machine, `corrections.py` replays it after a human correction, and
`stats.score_validation_note` labels the output as unvalidated in the dashboard.
Leave that code alone rather than removing it — the corrections replay depends
on it, and the honesty label is what stops the UI presenting a scoreline as a
measurement.

One thing that stays on the record: deriving score truth from a burned-in
scoreboard was built, rejected on its premise and reverted (`afffb5a`). That
entry stays in STATE's dead-end table so the idea cannot return a third
time — see also the second principle above.

## Status: real vs stubbed

- Working + tested: court.py, calibration.compute_homography/image_to_court,
  calibration.detect_court_keypoints (classical: white-tophat -> Hough ->
  intersections -> template fit), overlay.py, calibrate.py (manual click tool),
  pipeline.calibrate_video, ball.smooth_and_fill, analytics.py (speed, line
  calls), scoring.py, pipeline.generate_demo_match, schema.py. Tests pass.
- Perception now REAL (need ML deps from requirements-ml.txt + weights):
  pose.PoseEstimator (YOLO-pose, weights auto-download) tracks players;
  ball.BallDetector (TrackNet, weights/tracknet.pt, arch vendored in
  _tracknet.py) tracks the ball. Verified on a real broadcast clip
  (data/tennis_sample.mp4): pose tracks both players, ball detected ~74% of
  frames with gaps interpolated by smooth_and_fill. Demo scripts: track_pose_demo.py,
  ball_track_demo.py, track_match_demo.py (outputs in data/output/).
- END TO END: pipeline.analyze_video runs the full real pipeline (calibrate ->
  ball+pose -> project to court metres -> events/speed/line-calls -> rallies ->
  scoring -> match.json) and the React dashboard renders it. Verified on
  data/tennis_sample.mp4 -> data/output/real_match.json (4 shots, avg ~58 km/h).
  Perception is cached (<out>.perception.json) so downstream tuning is instant.
  Player selection (pose.select_players_on_court) is homography-derived in court
  metres, so it adapts to amateur angles, not just TV. Frontend has a
  Demo/Analyzed toggle (data/analyzed_match.json).
- Still imperfect (single-camera realities): speeds are approximate (airborne
  ball projected to the plane; capped at 230); real-footage court auto-detect is
  fragile on broadcast clay (use manual calibrate.py / the learned-keypoint seam);
  vision scoring is best-effort. These are bounded by calibration + camera, as
  the README says — not bugs to "fix" with more ML.
- Phase 1 done: calibration + a verifiable court overlay. detect_court_keypoints
  has a clearly-marked seam to swap the classical baseline for a learned
  keypoint model; low-confidence detection falls back to a manual keypoints JSON.
### Session log — condensed

One entry per session: the finding and its number. **The detail lives elsewhere
on purpose** — [docs/STATE.md](docs/STATE.md) holds the consolidated wins, the
dead-end table and the traps; `data/output/*.md` holds the evidence with its
denominators; [docs/archive/sessions/](docs/archive/sessions/) holds the pre-registered briefs.
Read those before re-proposing anything here.

- **2026-07-05 setup.** Git initialised; perception caches carry a provenance stamp
  (models, weight hashes, device, hfov, gates, homography hash, commit) and warn on a
  mismatched load. The demo30 "968-lock archive" regression resolved: 183 of the 968
  were static junk (HUD, net posts). NEW static-lock gate — a lock moving <3 px/frame
  for 5 frames is a fixture. yt_rally2 686 locks with **zero** static junk. 57 tests.
- **Session 2 (2026-07-05).** THE GOLD BENCHMARK EXISTS — 300 hand-labelled yt_rally2
  frames (258 ball / 26 no-ball / 16 unsure), TEST-only, never trained on. First honest
  numbers vs human clicks: ballnet 65.9% / archive 65.5% / fusion 43.0% / tracknet 41.5%.
  Far court is the whole gap. HANDOFF §11.
- **Session 3 (2026-07-06).** 2nd gold clip yt_match40 (cold). HUMBLING: on unseen
  footage custom BallNet does NOT beat off-the-shelf TrackNet — all four cluster 61-65%,
  and v1's earlier lead was a data leak. HANDOFF §12.
- **E5+ (2026-07-25) false alarms.** Court+vertical gate is a DEAD END (real far balls
  span court-y −229..+1667 m). NEW `ball.suppress_false_locks`; live-ball filter RETIRED.
  Pooled no-ball false-fire **14% → 6.0%** at flat recall. `ballnet_v21` becomes default.
- **E5+ smoothing.** `ball.smooth_forecast` = constant-acceleration Kalman + RTS smoother
  in image pixels. Jerkiness **9.9 → 4.1 px/frame²** at −1.6 pt hit@10. CRITICAL: it emits
  only INTERPOLATION — extrapolation ran off-screen and painted a phantom ball through
  dead time. `overlay.draw_court` now clips at the horizon. 148 tests.
- **E6 (2026-07-28).** The ball stack becomes geometry-aware. `gate_ball_to_court`'s
  margins were frozen at 720p and kept only **15.4%** of far balls at 1080p; replaced by a
  projected 3D box → **100%** retention. `events.drop_events_without_ball` kills phantom
  bounces (yt_rally2 6 → 3). `avg 0.0 km/h` diagnosed as coverage, not a bug.
- **E6 part 2.** Every pixel threshold now scales by `frame_height/720` — an exact no-op at
  720p, pinned by tests AND a byte-identical match.json. The before/after pair first
  recorded here is **WITHDRAWN** (bad scorer, see part 3). One deliberate exception:
  `static_radius_px` does NOT scale — scaling halves false-fire but costs 4.3 pts far recall.
- **E6 part 3.** MEASUREMENT BUG fixed: the scorer compared gold frame `f` against index
  `f//step` without checking `f` was processed. yt_rally2 is 100% even so its numbers stand;
  am_hard_utr was understated. `avg 0.0` FIXED → **62.8 avg / 91.9 top km/h**. `scale_ok` is
  measured ANTI-correlated with speed accuracy and is off the speed test. 171 tests.
- **Session F (2026-08-01).** Per-frame false-fire is NOT the product. THE CONFUSERS MOVE:
  71 raw false locks classified (`data/output/false_fires.md`) — **59.2% travel with a
  person**, 38.0% static scenery. So
  motion attention is skipped on evidence. `score_thresh` swept for the first time: **0.5
  stays** (0.6/0.7 fail the recall gate). `max_gap_s` swept: **0.4 stays**, and solid ghost
  fires sit at **9 at every setting** — nothing downstream removes a solid ghost. 209 tests.
- **Session G (2026-08-02).** POSE PROXIMITY IS A MEASURED NEGATIVE: **11.4%** catch at the
  5% collateral ceiling against a 60% gate. Why: the racquet sits **2.12 body heights** from
  the nearest keypoint — a skeleton has no racquet.
- **G part 2 (2026-08-03).** Calibration stops failing SILENTLY — every committed file
  carries an `_audit` verdict and `calibrate_video` warns on DEGENERATE. demo30
  re-calibrated **564.6 px → 0.5 px** (camera 1.38 m). Honest limit: at 1.38 m it measures
  only 5.2 m of 23.77 — **do not cite demo30 speeds**. 213 tests.
- **G part 3.** FAR COURT IS NOT GATE-SHAPED. The court gate costs **exactly zero**
  far-court recall on all three calibrated clips; the gap is DETECTOR-shaped.
  `suppress_false_locks`' shipped parameters already dominate all nine sweep alternatives.
- **G part 4.** Racquet-box negation (COCO class 38) FAILS at **54.5%** catch / 4.5%
  collateral against a 60% gate — but 4.8× better than pose proximity. Free external
  baseline: COCO "sports ball" scored **32.1%** recall on the six-clip gold set then;
  re-measured on the current ten-clip set it's **35.4%** (656/1851) vs BallNet v21's
  69.4% — data/output/racquet_negation_k.md.
- **Session H (2026-08-06).** THE COURT TEST SET WAS THE TRAINING SET — **17 of 20** gold
  clips were in `data/court_dataset/` and the court trainer had NO guard. Fixed with
  `court_split.json` + `assert_no_court_gold_leak`. Honest baseline on the clean split:
  **20.2%** held-out detect. The bottleneck is REFUSAL, not accuracy. 228 tests.
- **H part 2.** COURT AUTO-DETECTION CLOSED AS A MODEL PROBLEM. `courtfit` consensus is
  Tier 1 and beats CourtNet; the 6/8 bar is empirically correct (the one 5-vote clip is
  wrong by **68.7 px**, every ≥6-vote clip lands 3.4-13.9 px; evidence
  `data/output/court_consensus_bar.md`). 11 of 20 clips auto-calibrate with a perfect
  precision record. Also: 8 `am_indoor_hard1` gold frames are MISLABELLED — deliberately
  not "fixed", because human ground truth is never quietly edited. The valid court score
  table is `data/gold/court_scores_split.md`; `court_scores.md` is the pre-split leaked one.
- **H part 3.** SYNTHETIC GROUND TRUTH — the first ABSOLUTE accuracy here. Line calls
  **95.9%** correct, bounce **0.75 m** median. The −15..−20% speed rule CONFIRMED as physics
  (drag −21.7%; losing the vertical only −0.9%). New limit: flat z=0 back-projection is
  unusable for an airborne ball (**+72%** median).
- **H part 4.** WHAT CAMERA HEIGHT COSTS, in errors not bounds. Close-call accuracy
  **54.0% at 1.0 m → 69% at 3 m → 81% at 8 m**, against a **56.2%** majority-class floor —
  so a 1 m mount is worse than a constant answer. Pooled agreement is the WRONG metric
  (87-99% at every height). Real calibrations track the curve within ~3 pts. 243 tests.
- **H part 5.** FRAME RATE IS A REAL LEVER: 30 → 60 fps is worth **+5.8 pts** of close-call
  accuracy at 1.5 m — about as much as a *perfect* detector — and cuts bounce error 24-35%.
  Arc reproj **148 → 91 px**, HUD speed MAE **38.9 → 33.1%**. The cost is entirely the smoother.
- **H part 6.** `max_gap_s` at 60 fps is a MEASURED NEGATIVE: 0.60 passes cleanly on
  yt_rally2 and COLLAPSES on am_hard_utr. **The optimal gap policy scales with detection
  density — never tune it on one clip.**
- **Session I (2026-08-09).** Localised confuser weighting: PRODUCT GATE FAILS (solid ghosts
  14 → 15) while the DETECTOR improved on **6 of 6** clips (false fire 53.9 → 42.2%). NOT
  ATTRIBUTABLE — the trainer had **no seed**; `--seed` and `recipe_stamp` added. The ghost
  floor is **five universal frames**, not nine, and **all 19 chain false locks have
  `run_len = 1`** — every survivor carries the kinematic signature of a real ball.
- **Session J (2026-08-10).** The far-court queue's blocker was NOT the HUD — **RETRACTED**,
  only 5 of 36 clicks were inside a graphic. The real blocker: the ANCHORS bracketing the
  gaps were themselves false locks (≥1 anchor confirmed → 5 of 5 midpoints on a real ball;
  neither → 0 of 7). Then the sharper finding: **the anchor control measures agreement with
  the tracker, not correctness.** 326 tests.
- **Session K (2026-08-13).** MORE DATA IS A LEVER: +57% frames buys **+5.6 pts** pooled
  detector recall (74.8 → 80.4%, 4.1σ), up on 9 of 10 clips, and it GENERALISES (legacy six
  77.0 → 82.2%). **False fire did not move.** Not shipped — the chain test later failed
  (solid ghosts 9 → 13).
- **Session L (2026-08-13).** Far-court labels, under a pre-registered STOPPING RULE.
  Nothing predicts a findable gap: the best single feature keeps 73.0% / drops **50.0%**
  against a 70/60 bar, and 569 passing feature pairs cross-validate to **0-3%**. The null
  control (shuffled labels → **0** passing pairs) proves the signal is real and far too weak
  to screen on. Fourth failure on that lever. **The stopping rule fired: ball-detector work
  is closed.**
- **Session M (2026-08-15).** DELIVERY, not accuracy — no model touched, no gold number
  moved. The height guidance finally reaches users (`run.py check` + the Court Setup tab);
  `check` now invokes `pipeline.calibrate_video` so it can no longer disagree with `analyze`
  (**trap T15 recurrence** — the audit tool got the same fix a session earlier and nobody
  grepped the other callers); both JS mirrors are enforced by tests proved to fail; 60 fps
  shipped opt-in as `--full-rate`. **Scoreboard-derived score truth was BUILT THEN REJECTED
  ON ITS PREMISE — do not rebuild it** (a burned-in scoreboard is manual data entry;
  independence is not truth). 387 tests.
- **Session M part 2 (2026-08-15).** CHAIN ATTRIBUTION. In-rally coverage is the binding
  constraint on the target footage: the raw detector clears the ≥50% seen-fraction bar on
  **106 of 120** shots on am_hard_utr and only **69** survive the chain. Per stage,
  identical order on both clips: **`smooth_forecast` largest (−12.0 pts), `suppress_false_locks`
  second (−7.2), `gate_ball_to_court` exactly zero.** Two smoother fixes (`reset_after`,
  `bounce_reset`) both FAIL their pre-registered gate — loosening the outlier gate buys
  coverage and pays in ghosts. `am_hard_utr` finally has a perception cache. 391 tests.
- **Session N (2026-08-17).** RESPONSE TO THE 2026-08-16 REVIEW. Carved out a permanent
  blind holdout (2 of 10 gold clips) that `tune_smoother.py`/`tune_suppress.py` can no
  longer select (P0-1) — pre-registering each sweep's gate never stopped the cumulative
  drift of a dozen sweeps against one fixed set. Seeded CourtNet training to match
  BallNet's discipline (P2-1). Fixed a COCO baseline number that had gone stale (32.1%
  from the six-clip set, quoted with no qualifier; current is 35.4% on ten clips).
  Re-ran BallNet v21 vs TrackNet vs WASB (P1-1) on the current 10-clip gold set: BallNet
  still wins pooled hit@10 but by **+2.9 pts, not the +10.5 an undated `pipeline.py`
  comment claimed** — corrected in place, and not a clean win (TrackNet beats it
  outright on 2 of 10 clips). 391 tests.
- **Session N part 2 (2026-08-17).** THE DASHBOARD WAS INVENTING A STAT. `distance_run_m`
  is a path integral and was reported unconditionally, so **player B read a confident
  `0.0 m` on every real clip** — on yt_rally2 integrated over **0.0%** coverage (far
  player located on ZERO frames; 1.0% am_hard_utr, 9.6% demo30, 11.0% yt_match40).
  Forward-filling makes a sparse track *flat*, so it fails small-and-precise rather than
  obviously broken. Gated on the project's existing **≥50% seen-fraction** bar: below it
  the value is **None (not measurable), never 0.0**, and `stats.player_track_coverage`
  ships the denominator. UI says "not tracked" with the percent. **The cause is NOT
  fixed** — the far player really is untracked, now a named Open row with two unmeasured
  levers (`--pose-quality accurate`, `--far-player-rescue`).
  **A SECOND gate covers the axis coverage cannot see:** player tracking is deliberately
  **two-slot** (one per court half), so in DOUBLES the slot swaps between partners while
  coverage stays HIGH — distance is now refused there too, with its own reason in
  `stats.distance_run_note`. Verified by forcing `--doubles`: player A at **90.8%**
  coverage would have reported a confident 61.4 m. This is review finding P2-5 in its
  real form — doubles, not the singles net-exchange the review described (feet cannot
  legally cross the net mid-point). Also corrected a **SCOREBOARD self-contradiction**:
  its Open row told the next session to build score truth from burned-in scoreboards
  while its own dead-end table recorded that as built-then-rejected-on-premise and
  reverted; the `~1.6x` over-split came from that same withdrawn source and is now
  WITHDRAWN too (trap T20 fired twice — the second time on its own correction).
  400 tests.

## Keeping the docs true — which file moves with which change

Two guards enforce this; the rest is judgement. **A rule that is only remembered is
a rule that gets forgotten** — that is why both are hooks, not paragraphs.

| You changed | Update | Enforced by |
|---|---|---|
| Any code (`backend/`, `tools/`, `frontend/src/`, `mobile/`, `ball_physics/`) | **docs/STATE.md** — the number it moved, or the negative and why, plus its `docs/evidence/` file | `.claude/hooks/scoreboard-guard.sh` (`[no-scoreboard]` opts out) |
| `run.py`'s argument parser — a new flag, a removed one, a changed default | **README.md / USER_GUIDE.md / SETUP_PROMPT.md / CLAUDE.md** — whichever now lies | `.claude/hooks/docs-guard.sh` (`[no-docs]` opts out) |
| `schema.py` (the match.json contract) | **README.md** layout note + the frontend that reads it | judgement |
| Court constants in `court.py` | `frontend/src/lib/court.js` | `tests/test_js_mirror_parity.py` |
| `calibration.py`'s call-accuracy table | `frontend/src/lib/calls.js` | `tests/test_js_mirror_parity.py` |
| A model, weight file, or runtime | **docs/STATE.md** "The stack" | judgement |
| A process mistake hit **twice** | **[docs/TRAPS.md](docs/TRAPS.md)** (split out of SCOREBOARD 2026-08-17; never renumber — cited by number from code) | judgement |

**Which doc is authoritative for what**, so they can go stale gracefully instead of
contradicting each other:

- **docs/STATE.md is the only live record of state.** What worked, what failed with
  its number, what is open. If another doc disagrees with it, that doc is wrong.
- **CLAUDE.md** (this file) is orientation: architecture, hard rules, conventions,
  a condensed session log. Not a status board.
- **README.md / USER_GUIDE.md** are how to run it. They must match the CLI exactly.
- **docs/archive/sessions/** are pre-registered briefs. **All have run**; they are kept for
  their gates, not as a queue. Never read them as the forward plan.
- **docs/archive/HANDOFF.md** is a point-in-time evidence log from 2026-07-05, cited by `§`
  number from the ML docs. Historical by design — do not update it, and do not
  renumber its sections.
- **ML_PRACTICES.md / ML_PLAYBOOK.md** are discipline and technique. When a
  measurement invalidates advice in the PLAYBOOK, correct it in place with the new
  number — it has already recommended a route that a later session measured into
  the ground.

## Conventions

- schema.py is the single source of truth for match.json. Change shapes there;
  the frontend reads the same shape. Don't fork the format.
- Court constants live in backend/swingvision/court.py and are mirrored in
  frontend/src/lib/court.js. Keep them in sync.
- One module per pipeline stage; keep them independently testable.
- All real-world measurements are in metres; speeds reported in km/h.
- Add a test in tests/ for any new geometry or logic.
- Don't add dependencies for things stdlib/numpy/scipy already do.

## Live line calls (swingvision/live.py)

- LiveAnalyzer streams frames and emits an IN/OUT LineCall the instant it detects
  a bounce (online local-speed-minimum on the court-plane track). `run.py live
  <video|0> --keypoints court_pts.json` (0 = webcam); live_demo.py replays a
  cached ball track instantly. Verified: live_calls.mp4 + live_{in,out}_frame.png.
- Line calls need ONLY the ball (no pose), and the call logic runs ~86fps — so
  the live bottleneck is purely ball detection. On CPU TrackNet is ~1.4fps
  ("near-live": calls stream as bounces are found, slower than playback). TRUE
  30fps real-time needs hardware accel — pass --device cuda for a GPU, or plug a
  CoreML/ONNX-optimised ball model into the same LiveAnalyzer. A classical
  motion detector hits 110fps but is unreliable on busy footage (tracks players,
  not the ball) — don't ship it as-is.
- This is the one place the offline-first principle bends; the architecture is
  ready for real-time, the CPU model isn't fast enough.

## The Lab (tools/lab_server.py) — label, train, score, in a browser

- `py tools/lab_server.py` (stdlib only, no venv needed; it discovers
  `backend/.venv` for OpenCV and `backend/.venv-train` for torch+CUDA and uses
  them for the subprocesses). Five tabs: Clips, Label, Train, Score, Jobs.
- **It is not part of the analyzer.** It never imports `swingvision`, never writes
  match.json, and cannot change what the dashboard renders — it shells out to the
  scripts that already exist. Deleting it leaves the product unaffected.
- Why it exists: labelling and training only ever happened when someone ran a
  script by hand, so the far-court data that would fix ball recall never
  accumulated. `tools/lab_jobs.py` is its job runner — ONE job at a time (a single
  GPU; two runs would OOM or halve each other and make every timing a lie), and
  every job writes `data/runs/<id>.{json,log}` as it goes, so a crash still leaves
  the evidence.
- **The rule it enforces structurally:** a clip is declared gold (TEST, hand-labelled,
  never trained on) or train at intake, and that choice is ONE-WAY. It refuses to
  build a training set from a gold clip and refuses to cut gold frames from a train
  clip. `train_ballnet.assert_no_gold_leak()` remains the second, independent line
  of defence.
- The Train tab shows **No-ball** (labels.json's top-up frames) and **Hard negs**
  (mined confusers, with their share of labels) as SEPARATE columns. They are
  different files and different numbers; conflating them once made the
  worst-mined dataset read as the best-covered. Under 8% is flagged — the legacy
  tier runs 9-26%.
- A dataset with no recorded source video is not automatically unverifiable:
  `tools/verify_dataset_not_gold.py` settles it from the pixels (dHash every frame
  against every gold-manifest clip; a real match is 0-4 of 64 bits, different
  scenes are 10+) and records `provenance.gold_check`. `amateur` (min 12) and
  `highangle` (min 15) are cleared this way and show as "checked (pixels)".

## Mobile / on-device (mobile/)

- For phone deployment (live calls on-device, SwingVision-style): mobile/ has the
  ball model exported to ONNX with argmax baked into the graph (output 0.9MB not
  236MB), int8-quantized to 11MB (0.32px vs PyTorch), plus live_calls.js (the
  LineCall logic + homography in pure JS, verified bit-identical to live.py via
  mobile/verify_live.js) and ball_detector.js (onnxruntime-react-native wrapper).
  MOBILE.md is the integration guide (React Native + vision-camera + ORT).
- Caveat: int8 is slower than fp32 on x86 desktop (quant-kernel pathology); it's
  for mobile CoreML/NNAPI int8 accel. Not benchmarked on a real phone — don't
  quote a phone fps. The app shell (camera frame processor, UI, store build) is
  the remaining mobile-dev work; the ML + call logic are done here.

## Performance (CPU)

- The cost is perception. Pose dominated it: yolo11x@1920 ~2.4s/frame resolves a
  small far player but is slow; pose now defaults to the "fast" preset
  (yolo11m@1280, ~0.4s/frame). pose_quality fast|balanced|accurate trades speed
  for the far player. Ball (TrackNet, 360x640) is ~0.7s/frame and is now the
  floor — batching doesn't help it on CPU (compute-bound), so don't add it.
- frame_step="auto" targets ~30fps (TrackNet's rate), halving work on 60fps phone
  clips. Perception is cached at <out>.perception.json. analyze prints fps.
- Court detection is one-time (calibration), not per-frame — already efficient.

## Gotchas

- Speed is average ball speed (~15-20% under radar) — don't "fix" it to match TV.
- A LOW MOUNT IS NOT A STYLE CHOICE, it is measured accuracy. On close calls a 1.0 m
  camera scores 54.0% against a 56.2% majority-class floor — worse than a constant
  answer — rising to ~81% by 8 m (Session H part 4; `calibration.expected_call_accuracy`,
  evidence data/output/height_curve.md). Quote THAT to a user, not just the
  `reliable_court_span` percentage, which is a geometric bound and reads far kinder.
- Bounce detection is a single-camera heuristic (no true height) — improving it
  is a known open task, not a bug.
- Calibration quality + a fixed camera dominate accuracy more than model choice.
- CALIBRATION FILES: some committed `data/*_pts.json` are DEGENERATE (corners
  swapped / near-baseline at top of frame / a shape no real camera produces) and
  silently break the court overlay + ball gating. ALWAYS audit before use:
  `tools/validate_new_clip.py --audit data/*_pts*.json` — it reads each clip's own
  resolution and fits the actual camera (`courtfit.cam_fit_quad`, roll allowed)
  rather than assuming a 70 deg lens.
  The decisive number is the FIT RESIDUAL — how far the corners sit from the
  nearest legal camera view. It separates the set cleanly:
  KNOWN GOOD (<2.5 px): yt_match40_pts 0.9, yt_rally2_pts 1.4, yt_court_pts 2.1,
  court_pts_refined 2.3, eala_pts_auto 3.7, am_hard_utr_pts 0.7.
  KNOWN BAD (>10 px): court_pts 38, yt_court_pts_refined 48,
  yt_court_pts_doubles 54, yt_court_pts_singles 91.
  demo30_pts was the worst at 565 px and is now RE-CALIBRATED to **0.5 px** — the
  lowest residual in the repo (Session G part 2). It is LOW-CAMERA, not degenerate.
  EVERY committed calibration now carries its verdict in an `_audit` key
  (`tools/validate_new_clip.py --audit <files> --stamp`), and
  `pipeline.calibrate_video` WARNS loudly when it loads one stamped DEGENERATE —
  the point being that these files used to fail silently. The stamp is inert:
  calibrate_video already strips `_`-prefixed keys, pinned by
  tests/test_calib_audit_stamp.py (which also fails if the degenerate set drifts).
  A LOW camera is not degenerate — it is the amateur case this project targets;
  what it costs is measurable DEPTH, so the audit reports that in metres via
  `calibration.reliable_court_span`. Note the primary 1080p gold clip
  `am_hard_utr` fits a **1.74 m** camera (hfov 86 deg, 0.7 px — good corners,
  low mount) and is measurable only to **court-y 7.5 m of 23.77 (32% of depth)**:
  it does not reach the net at 11.885 m. Treat any far-court number on that clip
  as detection recall, NOT as a measurement.
