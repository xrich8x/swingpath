# CLAUDE.md

Project context for Claude Code. Read this before editing.

## Project docs — read the right one for the task

- **CLAUDE.md** (this file) — architecture, hard rules, current status. Read before editing.
- **[SCOREBOARD.md](SCOREBOARD.md)** — the LIVING record: the stack, the working method,
  and flat lists of what has and has not moved a number. This file's Status section is
  chronological; SCOREBOARD is the consolidated state of play. **Update it in the same
  commit as the work it describes** — a shipped win, a measured negative, a stack change,
  or a process trap hit twice. This is ENFORCED, not remembered:
  `.claude/hooks/scoreboard-guard.sh` refuses any commit that touches code without also
  modifying SCOREBOARD.md. Doc-, data- and config-only commits pass; put
  `[no-scoreboard]` in the message for a change that genuinely moves no number.
- **[README.md](README.md)** — what the project is + how to run it (quickstart, layout).
- **[ML_PRACTICES.md](ML_PRACTICES.md)** — how to *conduct* ML work: honesty, evidence
  tags, ground-truth-before-metrics, reproducibility, the session-end checklist.
- **[ML_PLAYBOOK.md](ML_PLAYBOOK.md)** — how to *think about* the ML: diagnosis buckets,
  per-area technique (ball/court/pose/physics), and the 2024-26 SOTA survey.
- **[HANDOFF.md](HANDOFF.md)** — historical evidence log (from 2026-07-05); the ML docs
  cite its `§` numbers. For *current* state use this file's Status + [docs/sessions/](docs/sessions/).
- **[docs/sessions/](docs/sessions/README.md)** — the forward plan: one researched brief per
  planned session (A-E), each with its Results filled in as it ships.

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
- Session 2026-07-05: git repo initialized (one commit per step; weights/datasets
  gitignored with documented reasons, but in-house trained weights and the
  data/output JSON evidence caches ARE committed). Perception caches now carry a
  provenance stamp (model names, weight-file hashes, device, hfov, court-gate
  threshold, homography hash, git commit); loading a cache under different
  settings prints a plain-English warning (pipeline.py, tests/test_provenance.py).
  The demo30 968-lock archive regression (HANDOFF.md par.6) is RESOLVED as far as
  it can be: hfov/gate/device/rescue all ruled out by experiment (current code is
  bit-deterministic at 781 tracknet locks), 183 of the archive's 968 locks are
  static junk (SwingVision HUD/logo/net posts), the real ball-only gap is
  785-vs-678 (107, or just 38 vs fusion), and the archive was built by pre-git
  code that no longer exists. Full verdict + numbers: HANDOFF.md par.10. The
  canonical demo30 dashboard build still uses the archived cache, unchanged.
  Known issue made explicit by the investigation: BOTH old and new trackers
  sometimes lock onto SwingVision's burned-in HUD graphics (sourced test clips
  only — the user's real recordings have no HUD, but net posts/fixtures fool
  detectors the same way). FIXED same day: BallTracker static-lock gate
  (a lock moving <3px/frame for 5 frames is a fixture: track dropped, spot
  blacklisted, ball re-acquired). Measured on yt_rally2: tracknet 686 locks
  with ZERO static junk (vs 781 incl. 103 junk; ball-only coverage UP
  678->686), fusion 746 with zero junk (747 before). Gate params are in the
  cache provenance stamp; 57 tests. The gold-label set remains the only way
  to score far-court coverage properly.
- Session 2 (2026-07-05 evening): the gold-label benchmark EXISTS (HANDOFF
  §11). tools/{select_gold_frames,gold_label_server,eval_gold,
  extend_noball_frames}.py; the user hand-labeled 300 stratified yt_rally2
  frames blind (258 ball / 26 no-ball / 16 unsure) ->
  data/gold/yt_rally2.labels.json. These labels are a TEST set — NEVER train
  on them. First honest numbers (hit@10px vs human clicks, stratified-hard
  sample): ballnet 65.9% / archive 65.5% / fusion 43.0% / tracknet 41.5%;
  far court is the whole gap (ballnet 76.2%, fresh runs 31.0%); on true
  dead-time frames the gated fresh tracks false-fire 5.9% vs 58.8% for
  archive/ballnet. The §10 verdict is settled: the archive's extra far-court
  locks were mostly real ball. BallNet v1 is the best ball-finder but worst
  false-firer; NOTE v1 trained on this very clip (indoor_elev = yt_rally2,
  archive labels) — home-field advantage. BallNet v2 (negatives, static-gated
  labels, yt_rally2 EXCLUDED from training; backend/relabel_train_clips.py +
  train_ballnet.py --exclude) is the top item, scored via eval_gold.py only.
  To label more clips: select_gold_frames.py then gold_label_server.py.
- Session 3 (2026-07-06): 2nd gold clip yt_match40 (300 uniform frames, cold —
  in NO training set) + BallNet v2 (negatives, yt_rally2 excluded) + the
  offline live-ball trajectory filter (ball.filter_live_ball; tools/
  {ball_perception,filter_cache}.py). HANDOFF §12. HONEST verdicts vs human
  clicks: (1) the LIVE-BALL FILTER is the biggest false-fire win — yt_rally2
  archive FP 61.5%->7.7%, v1 65.4%->34.6%, far-court recall unchanged (needs
  calibration for the off-court test). (2) v2 beats v1 only MODESTLY, measured
  fairly: on cold yt_match40 recall is tied (v1 65.2 / v2 63.6) and v2
  false-fires less (75%->62.5%); v1's big yt_rally2 lead was a data leak
  (trained on that clip). (3) HUMBLING: on unseen footage custom BallNet does
  NOT beat off-the-shelf TrackNet — all four cluster 61-65% recall and TrackNet
  false-fires LEAST (50%); prior BallNet leads were overfitting. (4) dead-time
  negatives were the wrong negatives; v2.1 needs HARD negatives (HUD/adjacent/
  edges) + a far-court recipe (sharper input, real far labels). Not "more
  epochs". weights/ballnet_v2.pt shipped as baseline; v1 kept for reference.
- Session E5+ (2026-07-25): FALSE-ALARM reduction, measured on the 2 calibrated
  gold clips (tools/eval_model_filters.py, fresh runs). THREE things. (1) The
  court+vertical gate is a proven DEAD END for false alarms: a real airborne far
  ball and a fixture project to overlapping court coords (real far balls span
  court-y -229..+1667 m), so no court envelope separates them without wiping far
  recall. (2) NEW ball.suppress_false_locks — two recall-safe image-space tests
  (persistence run-in-radius; min-segment length; a real ball never holds still
  and always forms a multi-frame track). Wired into pipeline after rectify_track;
  calibration-free so it helps every clip incl. amateur. (3) The live-ball filter
  is RETIRED from the pipeline (function+tests kept): net-negative once suppress
  runs (its image-px flicker + z=0 off-court tests punish far balls). Net pooled:
  no-ball false-fire 14% -> 6.0% at flat recall (51.8 -> 50.2). ballnet_v21.pt
  (hard negatives) is now the DEFAULT detector (was ballnet.pt) — only affects
  calibrated clips. Stale-cache lesson: the old 50-67% figures were from a cache
  built at an old commit; always re-perceive. Committed and pushed (on master).
- Session E5+ smoothing+forecast (2026-07-25): the detector loses the ball
  mid-flight and its per-frame locks jitter ("janky"). ball.smooth_forecast is now
  the pipeline smoother/forecaster — a constant-acceleration KALMAN FILTER + RTS
  (forward-backward) smoother in image pixels: denoises real detections, forecasts
  through gaps with one ballistic model (no kink at fill/detection boundaries),
  gates outlier locks by innovation, and RESETS at hits (sustained gated frames ->
  new segment; RTS never bridges a reset, so corners stay sharp). Returns
  (smoothed, coasted mask, confidence). Tuned meas_var=25 (~5px), sigma_jerk=1.0:
  demo30 jerkiness 9.9 -> 4.1 px/frame^2 (2.4x smoother) at -1.6pt gold hit@10.
  Wired into pipeline replacing the earlier ball.coast_fill (kept in module +
  tested). CRITICAL FIX after first cut: the CA model EXTRAPOLATED past the last
  detection -> ran off-screen ("insane") and painted a phantom ball through dead
  time (gold no-ball false-fire +9). smooth_forecast now emits ONLY interpolation:
  denoised detections + gaps <= max_gap_s(0.4s) bounded by a detection on BOTH
  sides; no forward/backward extrapolation. Off-frame 6->0, phantoms +9->+1.
  Also: annotate.py now draws the ball straight from the smoothed image-space
  ball_px + the coasted flag (ghost=interpolated), NOT reprojected/re-smoothed
  from the court track (reprojection through an imperfect H threw the trail across
  the frame). And overlay.draw_court now CLIPS court lines at the horizon (w<=0 /
  off-frame) — a low camera put the far baseline past infinity and drew stray
  lines to the corners (seen on demo30 AND yt_rally2). Verified end-to-end:
  run.py analyze yt_rally2 --annotate -> clean ball trail + court overlay, avg
  70 / top 95 km/h. demo30's manual corners were DEGENERATE (floored speeds) —
  RE-CALIBRATED in Session G part 2 to a 1.38 m camera at 0.5 px. amber/coasted still to be excluded
  from speed/bounce (finishing step; CLOSED in E6 — coasted frames no longer count
  as real detections). 148 tests. Committed and pushed (on master).
- Session E6 (2026-07-28): MERGED the court-detection work (setup guide, roll-aware
  snap, `calibration.RELIABLE_SCALE_M_PER_PX`, `reliable_court_span`) and made the
  ball stack GEOMETRY-AWARE. Thesis: the ball stack was half physical, half
  720p-pixel-tuned, and the court work published the conversion factor. THREE
  results. (1) `gate_ball_to_court` took `img_wh` and never used it — its 220/120 px
  airborne margins were frozen at the 1280x720 they were tuned on. Measured against
  human gold clicks (tools/eval_court_gate.py): on the 720p clips every variant
  keeps 100%, but on am_hard_utr (1080p) the shipped gate kept **15.4% of far-court
  balls** — the GATE, not the detector, was deleting the far ball. Replaced with a
  derivation: the court+runoff box extruded to ball height, projected; a box is
  convex so its image is the hull of its 8 corners. 100% retention pooled (617 balls
  / 255 far). Needs the camera, not just H, hence `calibration.camera_pose_m` +
  `project_court_3d`. (2) `smooth_and_fill` re-created the phantom ball in COURT
  space (it fills every gap incl. the edges), so events/speed saw a ball through
  dead time even though the renderer did not. Contacts now require a frame the ball
  was actually on (`events.drop_events_without_ball`): yt_rally2 bounces 6 -> 3,
  half were phantoms. Coasted frames no longer count as real detections in
  `real_fraction` (closes the old open item). (3) The `avg 0.0 km/h` symptom is
  DIAGNOSED, not a bug: the pipeline now prints why each speed was rejected — on
  yt_rally2 it is `2x seen 28%<50%, 1x seen 45%, 1x seen 49%, 1x seen 23%, 1x serve`.
  Four shots have under half their hit->landing span backed by a real detection.
  Verified the same 0.0 with the pre-change rule, so this is detection COVERAGE
  within a rally, not the confidence gate. Also: eval ladder now matches the shipped
  chain (it had been scoring the retired live-ball filter), far-court is reported as
  both `far_px` and `far_geo`, and train_ballnet's gold guard is derived from
  data/gold manifests (the old `--exclude indoor_elev` default matched no directory
  and had been protecting nothing). Detector baseline on merged code (ballnet_v21,
  vs human clicks, 1201 ball frames): pooled recall 69.4%, far_px 68.8%, far_geo
  72.5%, false-fire 34.8%. MEASURED NEGATIVE: depth-aware smoothing (scale the
  Kalman's process noise by the local m/px) is NOT a lever — median-referenced is
  worse (false-fire 19->27%), tighten-only is +1.2pt far / -0.8pt overall / 5% less
  jerk, inside noise. Kept off by default with the numbers in the docstring.
  CAVEAT on far_geo: it is "the part of the clip we cannot measure in", and on a low
  camera that is most of the frame (am_hard_utr: 141 of 175 clicks), so it reads
  ABOVE overall recall there. Only compare it between clips of similar measurable
  depth.
- Session E6, part 2: the gate bug had SIBLINGS. Every pixel threshold in the ball
  path was tuned at 1280x720 and applied unchanged at 1080p, where the same physical
  motion covers 1.5x the pixels. All now scale by `res_scale = frame_height/720`,
  which is an EXACT no-op at 720p (pinned by tests AND by a byte-identical
  end-to-end yt_rally2 match.json). Fixed: `BallTracker.gate` (association radius,
  70 -> 105 px at 1080p), `rectify_track` max_speed_px/resid_px, and
  `suppress_false_locks`' seg_step_px. `smooth_forecast` is now SCALE-EQUIVARIANT —
  its meas_var (px^2), sigma_jerk (px) and seed variances all scale, which matters
  because the innovation gate `y'S^-1y <= chi2` otherwise inflates by 2.25x at 1080p
  and rejects real detections as outliers. **The before/after numbers first recorded
  here (recall 36.6 -> 41.1%, false-fire 20.8 -> 17.0%) are WITHDRAWN** — they came
  from a scorer that mis-aligned decimated frames (see E6 part 3). The scaling
  changes themselves stand: they are exact no-ops at 720p, pinned by tests and by a
  byte-identical end-to-end yt_rally2 match.json.
  ONE THRESHOLD DELIBERATELY DOES NOT SCALE: `static_radius_px` (the fixture test).
  Theory says it should; measurement says scaling it 12 -> 18 px halves false-fire
  (13.2 -> 5.7%) but costs 4.3 pts of far-court recall, because on a 1.74 m camera a
  far ball's 0.2 s excursion clears 12 px but not 18 and gets reclassified as a
  fixture.
- Session E6, part 3 — SPEEDS ON THE DASHBOARD, and a measurement debt repaid.
  (1) MEASUREMENT BUG, now fixed: `eval_model_filters`/`eval_smoother` scored gold
  frame f against track index `f//step` without checking f was processed, so at
  step=2 every ODD gold frame was compared against the position one frame earlier.
  Blast radius is exactly known from gold-frame parity: **yt_rally2 is 100% even, so
  every number on it stands**; am_hard_utr is 48.6% odd, so this session's ladder
  runs understated the tracker. Corrected re-baseline (step=1, all 175 gold frames,
  shipped chain): tracker-gates-only 39.4 -> **52.6%**, FULL 41.1 -> **43.4%** recall
  at **7.5%** false-fire. The earlier E6 part-2 before/after pair is WITHDRAWN.
  (2) NEW per-gate MISS counters (the four old counters only counted successes).
  On am_hard_utr, 28998 frames: no-detection **7934** dominates; court-gate 694
  (acquiring) + 1834 (continuing); off-path 1324; fixture **0**. Also visible:
  `suppress_false_locks` is the largest recall cost in the chain. (The "15 pts"
  first written here was measured at `--frame-step 1`, i.e. fps_eff 60, which is NOT
  the shipped config; at the shipped ~30 fps it costs **5.4 pts on yt_rally2 and
  10.0 pts on am_hard_utr**. Corrected, and swept in E6 part 4.)
  (3) `avg 0.0 km/h` FIXED -> **62.8 km/h avg / 91.9 top**, 7 of 14 shots confident.
  Two causes. AIRBORNE != MISSING: the runoff box left 42% of tracked frames with no
  court position, and `real_at` treated that as "ball not seen", collapsing coverage
  to 37%. And `scale_ok` is MEASURED ANTI-CORRELATED with speed accuracy (PASS
  median |err| 41.6% vs FAIL 19.2% — passing it means a SHORT ball, where a path
  integral is proportionally worst), so it is off the speed test and stays on the
  line call. Validated vs the SwingVision HUD (tools/speed_band.py): published
  n=7 median 29.7% bias -13.9%, suppressed n=6 median 33.3% bias -32.8%. The
  negative bias is EXPECTED PHYSICS (average flight speed vs launch speed) and must
  not be "corrected" — see the Gotchas entry.
  (4) MEASURED NEGATIVE: raising `acquire_bound_m` 4 -> 10 m. Static analysis said it
  was free (seeding 62.9 -> 88.6% of gold positions, far-court 0/13 -> 13/13); end to
  end it bought +0.6 pt recall for +1.9 pt false-fire. Not shipped. 171 tests.
- Session F (2026-08-01): FALSE FIRE, measured on what the user actually sees.
  Steps 1-3 of docs/sessions/SESSION_F_false_fire.md; steps 4-5 gated and not run.
  (1) THE PRODUCT METRIC. Per-frame false-fire is not the product (E6 pt 4 raised
  it 19.2 -> 23.1% for ZERO extra phantom events), so it is now reported next to a
  product number and picked on that. "Visible ghost ball" ALREADY EXISTED as the
  eval ladder's FULL-row `fires` — annotate.py draws a ball iff ball_px[i] is not
  None on the same post-smooth_forecast track — and only needed splitting into
  `(N solid, M faded)`, because the renderer draws a real detection as a solid disc
  and an interpolated one as a faded ring. NEW tools/event_audit.py adjudicates
  each hit/landing against human clicks, on **yt_rally2 only**: gold is a uniform
  grid and the share of frames with a decided label within +/-3 is 64.7% there vs
  **5.5% on am_hard_utr**, the clip with the WORST false-fire. So event metrics are
  the narrow half of any decision and ghost ball (3 clips) is the wide half.
  DROPPED as unmeasurable: "phantom speed". The 17 HUD readings tile source frames
  62-2214 with a constant 2-frame gap — the HUD is a persistent PANEL, not an event
  list — so "a shot the HUD has no reading for" is identically empty. Replaced by
  `surplus_shots`, tie-break evidence only. RETRACTED: every hud_compare.py coverage
  figure quoted before this session. Its greedy matcher had a hard `lag >= 0` floor,
  but our t_hit_s carries its own +/-2-frame error; on rally2_seg10 the shot at
  t=14.73 could not claim the 14.60 panel (lag -0.13), took the 16.20 one (+1.47 vs
  a typical +0.5..0.9) and orphaned the real shot at 15.73 that gold clicks
  exonerate. One 0.13 s error cascaded into two wrong verdicts. Now an
  order-preserving assignment; coverage on that file 11/17 -> 12/17.
  (2) THE CONFUSERS MOVE — this is the load-bearing finding. All 71 raw false locks
  on human no-ball frames, all six gold clips, classified by eye from contact sheets
  (data/gold/false_lock_classes.json): racquet 31.0%, player 28.2%, background
  11.3%, fence 9.9%, court_line 7.0%, court_surface 5.6%, held_ball 2.8%, signage
  2.8%, net 1.4%. **MOVING WITH A PERSON 59.2% / static scenery 38.0% / real ball
  not in play 2.8%**; through the chain 54/46/0. So (a) STEP 5 MOTION ATTENTION IS
  SKIPPED — it suppresses static confusers and the largest class is a ball-sized,
  ball-coloured racquet head on an arc; (b) mine_hard_negatives' static-lock
  criterion reaches only that 38%, and the kinematic alternative is no better since
  a swung racquet forms a smooth track — the signal is PERSON-ATTACHMENT and the
  pipeline already runs pose; (c) this is not the live-ball question.
  TRAP: a tight image-space cluster on a FIXED camera is not necessarily a fixture.
  am_hard_utr's (5 locks in an 11x14 px box across 19k frames) was first read as
  balls on the court; the video shows it sweeping up with the feeder's arm.
  (3) SCORE_THRESH is now a dial (CLI on 5 tools + BALLNET_SCORE_THRESH env),
  STAMPED in the perception provenance and mismatch-checked, and swept for the
  first time — 0.5 was inherited and hardcoded in four places. The sweep costs ONE
  GPU pass, not one per threshold: detect() argmaxes BEFORE thresholding, so the
  peak position is threshold-independent. Exact, pinned by tests and by the swept
  0.50 row reproducing data/output/gold_v21_e6.txt digit for digit.
  MEASURED NEGATIVE — 0.5 STAYS. Pooled chain recall over 617 labelled ball frames
  66.5% -> 64.8% at 0.6 -> 60.3% at 0.7; both FAIL the pre-registered recall gate.
  Raising the threshold does NOT remove ghost balls: on yt_rally2 at 0.7 the chain
  reaches ZERO fires after suppress_false_locks and the smoother puts 7 back —
  total 8 -> 7 (noise) for 6.2 pts of recall and 9.5 of far_geo — while the
  per-frame number (30.8 -> 26.9%) makes it look like a win. Gate ordering earned
  its keep: at 0.6 the ghost-ball gate would have PASSED (solid fires down on all
  3 clips, up on none) and only the recall gate, deliberately ordered first,
  killed it. 209 tests; the shipped 0.5 path is verified byte-identical end to end.
  (4) SMOOTHER GAP POLICY — a SECOND measured negative, and it corrects (3).
  `smooth_forecast`'s max_gap_s=0.4 had never been swept either; it sits at the END
  of the chain so one perception pass scores every value (tools/tune_smoother.py).
  Swept at each clip's SHIPPED frame step, pooled over 532 scoreable ball / 74
  no-ball frames on the 3 calibrated clips:
      max_gap_s   pooled recall  d recall  worst d far_geo  ghost  solid  faded
        0.00          61.1%        -5.8         -8.6          11     11      0
        0.10          61.1%        -5.8         -8.6          10      9      1
        0.20          62.0%        -4.9         -6.1          13      9      4
        0.30          66.2%        -0.8         -2.8          16      9      7
        0.40 shipped  66.9%          -            -           19      9     10
  Every value FAILS Gate 1. 0.4 stays. THE INVARIANT IS THE FINDING: solid fires
  are 9 at EVERY setting 0.10-0.40. The gap policy cannot touch them — they are the
  detector genuinely firing on a racquet/player/fence in dead time, i.e. the Step 2
  tally. It only moves the faded count (10 -> 0) and charges 5.8 pts of recall to
  do it. So the ghost ball at the shipped config is 19 fires / 74 no-ball frames,
  9 SOLID + 10 faded, and BOTH post-hoc knobs now swept trade recall ~1:1 against
  the faded half while leaving the solid half untouched. NOTHING DOWNSTREAM OF THE
  DETECTOR REMOVES A SOLID GHOST — the next real work is Step 4 with a
  POSE-PROXIMITY criterion, not a filter, threshold, or motion attention.
  RETRACTED from (3) as first written: "the ghost ball is, at the margin, the
  SMOOTHER interpolating through dead time". That came from a --frame-step 1 run
  (fps_eff 60, a 24-frame bridge) reading 0 solid / 7 faded; at the SHIPPED step
  (fps_eff 30, 12-frame bridge) the same clip reads 5 solid / 1 faded, the opposite
  composition. This is the identical trap recorded in E6 part 3 and it was walked
  into anyway. STANDING RULE: never quote a --frame-step 1 number as shipped
  behaviour; use step 1 only for A/B deltas and for clips whose gold parity demands
  it, and re-measure at the shipped step before concluding a MECHANISM.
- Session G (2026-08-02): POSE PROXIMITY IS A MEASURED NEGATIVE. Session F named it
  "the only remaining lever the evidence supports" — mine "lock near a person" as a
  hard negative, since 59.2% of confusers move with a person and the static-lock
  miner reaches only the other 38%. Step 1 (tools/eval_pose_proximity.py) scored the
  criterion against human labels BEFORE any GPU time: 44 person-attached locks
  (racquet 22 / player 20 / held_ball 2, from data/gold/false_lock_classes.json) for
  CATCH, and 1201 frames where a human clicked a real ball for COLLATERAL. NOTE the
  collateral population is 1201, NOT the 617 chain-level count — a mining criterion
  is applied at detector level. Gate was catch >= 60% at collateral <= 5%. RESULT: at
  the 5% ceiling the best catch is 11.4%; max catch anywhere is 43.2% at 23.5%
  collateral. Off by 5x with NO KNEE — catch and collateral rise together ~2:1 across
  every radius, keypoint set, and both sizing modes (absolute px normalised to 720p,
  and body-relative). NOT a pose-quality artefact: the pre-registered `accurate`
  (yolo11x@1920) check moved max catch 38.6 -> 43.2% while RAISING collateral.
  WHY IT FAILS, and this is the transferable part: the racquet is not on the
  skeleton. Median lock-to-nearest-upper-body-keypoint distance is 2.12 BODY HEIGHTS
  for racquet (n=22), 0.76 for player, 0.24 for held_ball. A pose skeleton has no
  racquet, and at contact the head of a 68 cm racquet at arm's length is often
  further from the wrist than the ball is. CONFOUND RULED OUT: pose finds only ONE
  person on 1006 of 1272 frames (structural — 5 of 6 gold clips are low/close cameras
  where the far player is unresolvable), but on gold_shell, where 2+ people are found
  on 192/201 frames, catch is FLAT at 20.0% across R = 0.20/0.30/0.50 body heights
  while collateral goes 6.0 -> 19.6%. With complete pose, 8 of 10 person-attached
  locks are still beyond half a body height from every keypoint. Also: am_hard_utr
  collateral is 14.9% at R=0.20 — a person-proximity rule is MOST dangerous on the
  low-camera amateur footage this project targets. Steps 2-3 NOT run;
  mine_hard_negatives.py is unchanged (no --criterion flag, because there is no
  criterion worth adding). Next levers, best-supported first: (1) detect the RACQUET
  and negate locks on it (needs labels we don't have); (2) extended elbow->wrist ray
  — cheap to test against the same 44 locks with the cached pose, but the 2.12 bh
  median sets a low prior; (3) accept the 9 solid ghosts as the detector's floor at
  this data scale and spend the effort on far-court recall, where E6 showed the GATE
  was deleting real balls, not the detector. 209 tests.
- Session G part 2 (2026-08-03): calibration stops failing SILENTLY, and demo30 is
  fixed. (1) `validate_new_clip.py --stamp` writes the verdict it already computes
  back into each calibration as an `_audit` key (verdict, fit residual, camera
  height, the frame size used and whether it came from the clip or was assumed,
  reasons). All 11 committed files stamped. `pipeline.calibrate_video` reads it back
  and WARNS on DEGENERATE — it warns rather than refuses because coast_fill_probe.py
  and demo_false_alarm.py point at bad files deliberately. Inert by construction
  (calibrate_video already strips `_` keys); verified by test AND by confirming every
  corner VALUE round-tripped identically through the rewrite. (2) demo30
  RE-CALIBRATED: 564.6 px -> **0.5 px**, hfov 104 deg, camera **1.38 m**, verdict
  LOW-CAMERA. Auto-calibration cannot do this clip (2 of 8 frames, needs 6), so it
  was placed in tools/court_setup_server.py — auto-seed then Snap, 90% line coverage,
  shape-lock ON. (3) HONEST LIMIT, and it matters for the dashboard: fixing the
  calibration does NOT make demo30 a speed demo. At 1.38 m it is measurable to
  **court-y 5.2 m of 23.77 (22% of depth)**, and a fresh analyze reports `speed not
  trusted for 5/5 shots` (coverage 22-48% < 50%; arc reproj 80-157 px vs a 6 px
  gate). Old outputs quoting demo30 at avg 59.5 / top 166.8 km/h came off the
  DEGENERATE corners and are junk; the honest read is avg 31.8 / top 50.7 with
  nothing trusted. The clip is fine for the overlay and the dashboard shell — do not
  cite its speeds. (4) Two live references to the degenerate `court_pts.json` fixed:
  the auto-calibration failure message told users to CREATE a file with that exact
  name, and live_demo.py's docstring pointed at it. 213 tests.

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

- Session G part 3 (2026-08-03): FAR-COURT RECALL IS NO LONGER GATE-SHAPED. The
  standing recommendation after E6 was "attack far court from the GEOMETRY side,
  because E6 showed the GATE was deleting real balls, not the detector". Re-measured
  on all three calibrated gold clips at their SHIPPED frame step
  (tools/eval_model_filters.py, fresh perception, ballnet_v21). far_geo through the
  ladder:
      clip          tracker-gates  +rectify  +suppress  +court-gate  FULL
      yt_rally2         74.3         74.3      66.5       **66.5**    74.3
      yt_match40        62.6         62.6      57.6       **57.6**    66.9
      am_hard_utr       64.4         64.4      58.9       **58.9**    60.3
  THE COURT GATE COSTS EXACTLY ZERO far-court recall on every clip — E6's fix was
  complete and there is no second gate bug. The miss counters agree: court-gate
  misses are 0 on yt_match40, 6 of 1108 frames on yt_rally2, and 2528 of 28998 on
  am_hard_utr against 7934 no-detection — 3.1x smaller than the detector simply not
  firing. Pooled, the post-detector chain is far-court NEUTRAL (yt_rally2 74.3 ->
  74.3, yt_match40 62.6 -> 66.9): suppress_false_locks costs 5.0-7.8 pts of far_geo
  and the Kalman gives them back.
  So the remaining far-court gap is DETECTOR-shaped, and the geometry lever is
  spent. That matches SESSION_E §E3j's prediction that the last ~20% of the ball
  cannot be taught by pseudo-labels — the teacher cannot see it either — and needs
  a few hundred HUMAN far-court labels, which is precisely what the Lab exists to
  collect.
  ALSO: suppress_false_locks' parameters were ALREADY swept (data/output/
  tune_suppress_*.txt, committed earlier this session) and never acted on. At the
  SHIPPED step the shipped setting (seg_dur 0.10, seg_gap 0.00) DOMINATES every
  alternative on am_hard_utr — best recall (54.4%), best far_geo (60.3%) AND lowest
  false-fire (25.0%) of all nine rows. The step=1 sweep in the same directory
  suggests otherwise and is the frame-step trap again: seg_gap is a TIME threshold,
  so at fps_eff 60 it spans twice the frames. Do not re-sweep it without a new
  reason.

- Session G part 4 (2026-08-03): THE RACQUET BOX IS THE RIGHT LOCALISER — and it
  still misses the pre-registered gate. Session G part 1 killed pose proximity
  because the racquet is not on the skeleton (2.12 body heights from the nearest
  keypoint). The follow-up needs racquet labels we do not have — except COCO
  already ships one: **class 38 "tennis racket"**, in every stock ultralytics
  checkpoint, so the criterion is testable with ZERO new annotation.
  `tools/eval_racquet_negation.py`, scored on the SAME populations and the SAME
  gate as the pose eval (22 racquet-class / 44 person-attached human-classified
  locks for CATCH; 1201 human ball clicks for COLLATERAL):
      margin@720p   catch(racquet)   catch(person)   collateral
          0px           54.5%            36.4%          4.5%
         20px           54.5%            36.4%          9.2%
         50px           63.6%            50.0%         18.4%
  GATE (catch >= 60% at <= 5% collateral) **FAILS** — 54.5% at the 4.5% ceiling.
  The gate is NOT moved: it was pre-registered and 54.5 < 60.
  BUT THE MARGIN IS THE FINDING. Pose proximity managed **11.4%** catch at that
  same 5% ceiling; the racquet box manages **54.5%** — 4.8x better, and 5.5 points
  short of a gate rather than 5x short. The part-1 diagnosis was right: the
  skeleton was the wrong proxy and the racquet is the right object. Whether
  54.5%@4.5% is worth shipping as a MINING criterion (where the economics differ
  from a runtime filter — a mined negative is a training example, not a deleted
  detection) is a judgement call that has NOT been made.
  Stock racket detection genuinely works on this footage: a racket is found on
  64.5-100% of sampled frames per clip (yt_rally2 64.5%, gold_shell 100%), so the
  ceiling here is the CRITERION, not the detector.
  FREE EXTERNAL BASELINE, first this project has had: the same pass scored COCO
  class 32 "sports ball" against the same human clicks — **32.1% recall @10px
  (386/1201) vs BallNet v21's 69.4%**. Not like-for-like (COCO's sports ball is
  trained on large sharp balls, not a 2-4 px blurred far-court one) so read it as a
  FLOOR, not a rival — but it is an independent confirmation that the in-house
  detector is worth roughly 2.2x a general-purpose one on this footage.

- Session H (2026-08-06): THE COURT TEST SET WAS THE TRAINING SET, and fixing that
  changed what the problem is. The feature list said the next court step was "CourtNet
  retrain with MAE loss + per-keypoint local Hough refine (both in the playbook,
  untried)". Reading the code, all three premises were wrong.
  (1) The local Hough refine is NOT untried — `calibration._refine_keypoint` is
  implemented and `detect_court_learned` already calls it on 11 of 14 keypoints.
  (2) THE REAL BLOCKER: `data/court_dataset/` had 20 training dirs and `data/gold/`
  has 20 hand-labelled court clips — **17 were the same clips** — and unlike the ball
  trainer, `train_courtnet.py` had NO leak guard. Only 3 clips / 54 frames had never
  been trained on. FIXED: `data/gold/court_split.json` declares 8 TEST / 15 TRAIN
  one-way; `train_courtnet.assert_no_court_gold_leak()` REFUSES to start if a TEST clip
  is in the training root (proved by pointing it at the unsplit dir); the 5 pulled clips
  moved to `data/court_testset/`; 6 tests in tests/test_court_split.py pin it.
  NOTE `tools/eval_court.py` ALREADY split held-out vs trained-on and refused to print a
  pooled number — the awareness existed, the GUARD did not.
  Also added `COURTNET_WEIGHTS` env override (mirrors `BALLNET_WEIGHTS`): without it,
  `detect_court_learned` prefers `courtnet_ft.pt` BY FILENAME, so benchmarking any other
  checkpoint silently scored the contaminated one instead.
  (3) HONEST BASELINE, retrained on the clean split (same MSE recipe, only the training
  set changed; `weights/courtnet_split.pt`, 15 epochs, 22m49s): **held-out 20.2% detect
  (25 of 124 frames, 8 clips)** vs trained-on 23.6%. The leak was flattering almost
  nothing — the model generalises about as badly as it memorises.
  THE FINDING IS THE SHAPE, NOT THE NUMBER: the bottleneck is REFUSAL, not accuracy.
  Where it fires it is good — am_ntrp30 100% detect / 3.9 px / 86.6% within-8px,
  am_usta60 60% / 4.7 px / 74.1%, IoU 0.893 — and it returns NOTHING on 5 of 8 clips
  (am_beginner, am_grass1, am_ntrp45_courtlevel, am_rec30, am_wingfield_clay). So MAE
  loss and the Hough refine both aim at localisation, which is already single-digit px.
  The next question is which gate in `detect_court_learned` refuses: `min_points=6`, the
  0.40 heatmap floor, the reproj gate (`0.015*max_dim`), or `verify_court`.
  DO NOT compare any of this to the old `data/gold/court_scores.md` (kp_err 212-281 px):
  that table has no `split` column, predates the leak-aware eval, and may have been the
  classical detector. It is not a valid before. Also open: am_indoor_hard1 returns a
  court on **62.5%** of frames a human marked UNUSABLE — a confidently-wrong overlay.
  228 tests.

- Session H part 2 (2026-08-06): COURT AUTO-DETECTION IS CLOSED AS A MODEL PROBLEM, and
  the 6/8 bar is now verified rather than believed. Three results.
  (1) CourtNet IS THE WRONG TARGET. `pipeline.calibrate_video` TIER 1 is
  `courtfit.fit_video_frames` (line-fit consensus, "the measured best on amateur
  footage"); `detect_court_learned` is only TIER 2, reached when Tier 1 already refused.
  demo30's "2 of 8 frames, needs 6" was COURTFIT, not CourtNet — the feature row
  conflated them. Measured head-to-head on the 8 held-out clips, courtfit auto-accepts
  am_ntrp45_courtlevel 8/8, am_ntrp30 8/8, am_rec30 7/8 and am_grass1 6/8, while CourtNet
  returns NOTHING on three of those four. CourtNet adds value on exactly one clip
  (am_usta60) and is confidently wrong on another. Do not spend on MAE loss, the Hough
  refine, or gate instrumentation for it.
  (2) THE CONSENSUS BAR IS EMPIRICALLY CORRECT — measured, not asserted
  (`tools/eval_court_consensus.py --all --k 8`, evidence in
  data/output/court_consensus_bar.md). Pre-registered gate: lower 6 -> 5 only if ZERO
  5-vote consensuses are wrong. There is exactly one 5-vote clip, am_ntrp50, and it is
  wrong by **68.7 px**. GATE FAILS, bar stays at 6. THE SEPARATION IS THE FINDING: every
  clip at >=6 votes lands 3.4-13.9 px; every clip at <=5 votes lands 25.5-111.0 px;
  nothing is in the gap. Auto-calibration already succeeds on **11 of 20** gold clips
  with a perfect precision record — no wrong court has ever been auto-accepted. The
  failure mode is refusal, and refusal costs ~30 s in the setup tool.
  (3) 8 COURT GOLD FRAMES ARE MISLABELLED, and this INVALIDATES a number I recommended
  acting on. `am_indoor_hard1`'s 62.5% "confidently-wrong overlay" was the detector being
  RIGHT and the labels being WRONG: frames 9204/10093/10982/11871/12760/13649/14538/15427
  are marked `court: false, unusable: true` but plainly show a full usable court (3 of 3
  inspected by eye; timestamps 3 s apart, consistent with a mis-click run). Contrast
  am_usta60, whose 8 unusable frames are genuine talking-head/selfie shots — so the
  labelling convention is right and this clip is an anomaly. NOT FIXED HERE ON PURPOSE:
  never quietly edit human ground truth to suit a model. Re-label in the Lab; until then
  that clip's false% is not a valid metric.

- Session H part 3 (2026-08-06): SYNTHETIC GROUND TRUTH — the first ABSOLUTE accuracy
  in this project. Every other number here is an AGREEMENT number (human clicks, or 7
  HUD readings); the geometry and physics layers are closed-form, so truth can be
  manufactured. `tools/synth_truth.py` simulates flights with a known launch velocity
  through the real drag+gravity+Magnus model, projects them through a REAL clip's
  calibration, adds our actual detector noise (2 px) and dropout (30%), and runs the
  shipped measurement code on the result. 341 flights through yt_rally2_pts.
  (1) LINE CALLS AND BOUNCE ARE VALIDATED ABSOLUTELY for the first time: the call
  agrees with truth on **327/341 (95.9%)** and the bounce lands **0.75 m** (median,
  p90 4.91 m) from where the ball really hit.
  (2) THE -15..-20% SPEED RULE IS CONFIRMED, AND ITS REASONING REFINED. The error
  budget: drag (launch -> true average 3D) **-21.7%**; ground projection (3D ->
  ground, dropping the vertical) **only -0.9%**. So the under-read is almost entirely
  DECELERATION, not the loss of the z component as the docs implied. The rule stands:
  do not bias-correct it.
  (3) NEW MEASURED LIMIT: the flat z=0 back-projection is UNUSABLE for an airborne
  ball — integrating path length over the whole arc reads **+72% median, p90
  +25,000%**, because a near-grazing ray meets the plane at infinity. Restricted to a
  ball under 1 m it is +15% bias / 27.9% median |error|. This quantifies why
  `gate_ball_to_court` and the physics arc fit exist and why `speed_source="approx"`
  is a floor, not a measurement.
  CAVEAT, stated in the tool: this exercises `analytics.shot_speed_kmh` on a raw
  back-projection. It does NOT exercise `speedspin`'s physics fit, which is the
  shipped preferred path — so (3) bounds the fallback, not the product.
  TRAP HIT AND FIXED DURING THE BUILD: the physics package and swingvision use
  DIFFERENT court frames (tennis_tracker X=length/Y=width-centred-mirrored vs
  swingvision x=width/y=length). The first run compared a physics-frame bounce
  against a court-frame estimate and reported a 30 m median error on a 23.77 m
  court. `to_court_xy` is now asserted at startup to be the exact inverse of
  `speedspin._to_framework_xy`.

- Session H part 4 (2026-08-07): WHAT CAMERA HEIGHT COSTS, in errors rather than in
  bounds. `courtfit.setup_verdict`'s docstring claimed `reliable_court_span` was "the
  number that turns 'mount it higher' from an opinion into a measurement" — but that
  span is a GEOMETRIC BOUND (where one pixel exceeds `RELIABLE_SCALE_M_PER_PX`), not an
  error, and no error had ever been measured. `tools/height_curve.py` drives
  `synth_truth` over a ladder of camera heights: synthetic cameras on the centre line,
  6 m back, 100 deg lens, 720p, with ONLY the height changing and the pitch re-solved at
  each step to keep the court framed (the freedom a user actually has). Every generated
  camera is round-tripped through the same PnP the measurement uses and the run ABORTS
  if the recovered height disagrees by >2%. Evidence: data/output/height_curve.{md,json}.
  (1) THE HEADLINE, and it is a floor result. On bounces within 0.5 m of a line — the
  only population where a call is a call — accuracy runs **54.0% at 1.0 m, 60.1% at 1.5,
  69.1% at 3.0, 79.9% at 6.0, ~81% at 8+**, and bounce error **3.81 m -> 0.37 m**. The
  majority-class floor on that population is **56.2%**, so a 1.0 m mount is not "slightly
  better than chance", it is WORSE THAN ANSWERING 'IN' EVERY TIME. `calibration.
  expected_call_accuracy` + `CALL_MAJORITY_FLOOR_PCT` now carry the table, and every
  `setup_verdict` says "Close calls: ~N% right at this height", adding "no better than
  guessing" at or below the floor. Pinned by 6 tests in tests/test_setup_guide.py.
  (2) POOLED AGREEMENT IS THE WRONG METRIC and would have hidden all of it: over ALL
  bounces it reads 86.8% at 1 m and 98.7% at 12 m, because most simulated bounces land
  nowhere near a line and metres of error still call them correctly. Same shape as
  Session F's "per-frame false-fire is not the product". THE RULE: score on the
  population where the answer is in doubt, and state the majority-class floor next to it.
  (3) CONTROL RUN, because the obvious rival explanation is sampling: our bounce
  estimate is the last TRACKED point, so at 30 fps with 30% dropout it can land a frame
  or two early. Removing the handicap (240 fps, no dropout) moves 1.0 m from 54.0 ->
  65.4% and 12 m from 79.4 -> 87.6%. So sampling is worth **~8-11 pts everywhere and
  halves bounce error**, but the 1 m-vs-12 m SPREAD SURVIVES — the curve is the camera.
  (`--control` reruns it.)
  (4) THE REAL CALIBRATIONS TRACK THE SWEEP, which is what makes it usable as guidance:
  demo30 (1.38 m) 58.7%, am_hard_utr (1.75 m) 59.8%, yt_rally2 (3.30 m) 72.2%,
  yt_match40 (11.33 m) 83.8% — each within ~3 pts of the synthetic curve at its height,
  despite differing lens, setback and resolution. Their lenses are solved by
  `courtfit.cam_fit_quad`, NOT `focal_from_homography`, which refuses outside 25-110 deg
  and silently drops exactly the three high-mount/broadcast files.
  CAVEAT: the speed column exercises `analytics.shot_speed_kmh` on a raw
  back-projection, so it bounds the `approx` FALLBACK, not `speedspin`'s physics fit.
  `synth_truth.measure/summarize` were extracted for this and are byte-identical on the
  committed yt_rally2 run. 243 tests.

- Session H part 5 (2026-08-07): FRAME RATE IS A REAL LEVER, and `frame_step="auto"`
  is spending it. Evidence: data/output/fps_decision.md.
  (1) CORRECTION to part 4's control: it varied frame rate AND detector dropout
  together and the gap was quoted as the value of frame rate. Those are different
  things — fps is a free recording/processing choice, dropout is a detector property.
  Re-run as a full grid, one variable at a time. METHOD FIX REQUIRED FIRST: the
  harness sampled truth at the fps under test, so a low-fps run got a less accurate
  truth bounce and the comparison would have flattered high rates for free.
  `synth_truth.simulate(truth_fps=...)` now computes truth once on a 240 Hz grid and
  DECIMATES to each rate, so runs are strictly nested and perfectly paired (default
  path unchanged, byte-identical on the committed yt_rally2 run).
  (2) ISOLATED RESULT: 30 -> 60 fps is worth **+5.8 pts of close-call accuracy at
  1.5 m, +3.2 at 3.0 m, +1.8 at 12.0 m**, and cuts bounce error 24-35%. It holds at
  BOTH dropout levels, so it is not dropout in disguise. For scale, at 30 fps
  eliminating detector dropout ENTIRELY buys +4.7 / +2.5 / +2.2 at the same heights —
  so doubling the frame rate we already have is worth about as much as a perfect
  detector. Returns flatten above 60-120; 15 fps sits near the majority-class floor.
  (3) END TO END on yt_rally2 (native 60 fps, calibrated, gold-labelled, HUD): every
  measurement number improves — physics-arc reproj median **148.2 -> 91.2 px** (best
  arc 103 -> 24.5), HUD speed MAE **38.9% (n=6) -> 33.1% (n=7)**, HUD strokes we
  produced nothing for 8 -> 6, trusted-speed shots 7 -> 8. Gold per-frame recall
  72.5 -> 75.2%, far_geo 74.3 -> 72.6% (flat-ish, consistent with the standing
  "fps buys precision, not recall" finding).
  (4) THE COST IS ENTIRELY THE SMOOTHER, and that is the actionable part. Through the
  detector and its gates 60 fps is BETTER on false-fire (15.4% vs 19.2%); the Kalman
  stage then takes it to 30.8% vs 23.1%. `max_gap_s=0.4s` bridges twice as many frames
  at 60 fps and has only ever been swept at 30 (Session F step 4). So full-rate
  processing is NOT a safe one-line change until that sweep is done.
  (5) TWO APPARENT REGRESSIONS THAT ARE NOT. `fixture` rejections 83 -> 0 is the
  static-lock gate working as designed — it is ALREADY fps-scaled (Session E3c) and
  at 60 fps correctly declines to call a slow-looking far ball a fixture. And ghost
  `fires` 6 -> 8 with composition 5 solid/1 faded -> 4 solid/4 faded is the Session F
  trap reproducing exactly: a 0.4 s bridge holds twice as many frames at 60 fps, so a
  per-frame fire count is not comparable across rates for the faded half — SOLID
  fires actually went DOWN (5 -> 4).
  UNEXPLAINED, do not cite: `no-detection` misses went 10.1% -> 20.0% of processed
  frames while the overall lock rate ROSE (83.8 -> 87.2%) and gold recall did not
  drop. Most likely counter bookkeeping shifting as the fixture gate stops firing.
  Not verified.

- Session H part 6 (2026-08-07): `max_gap_s` AT 60 FPS IS A MEASURED NEGATIVE, and the
  replication is the whole story. Part 5 named the smoother as the one blocker to
  full-rate 60 fps processing (all the false-fire cost is there; `max_gap_s=0.4` had
  only ever been swept at 30 fps). Swept on BOTH native-60fps calibrated gold clips.
  Evidence: data/output/tune_smoother_60fps.md. Pre-registered gate: match/beat the
  shipped 30 fps baseline on recall AND far_geo, and do not increase SOLID ghosts.
  (1) ON yt_rally2 IT LOOKS LIKE A CLEAN WIN. Ghost is FLAT at 8 fires from
  max_gap_s 0.20 through 0.60 while recall climbs 70.5 -> 77.1%, then breaks (0.80 ->
  10 fires, 2.00 -> 22). 0.60 passes the gate outright: recall 77.1% (vs 72.5%),
  far_geo 75.4% (vs 74.3%), solid ghosts 4 (vs 5).
  (2) ON am_hard_utr IT COLLAPSES. No flat region at all — false-fire rises
  monotonically, and 0.4 -> 0.6 costs **+5.6 pts false-fire and +3 ghost frames for
  +0.5 pts recall**. GATE FAILS. **0.4 STAYS.**
  (3) WHY THEY DISAGREE — the transferable part. yt_rally2 is a 3.31 m camera with
  dense detections (recall 75%), so its gaps are short and widening the bridge past
  0.4 s rarely finds a gap to fill. am_hard_utr is a **1.74 m** camera at 1080p with
  recall 54.9%: sparse detections, long gaps, and every extra 0.1 s of bridge invents
  more ball. THE OPTIMAL GAP POLICY SCALES WITH DETECTION DENSITY, and the low-camera
  amateur clip — the footage this project targets — is the one that punishes a wide
  bridge. Tuning on the easy clip would have shipped a setting actively worse where it
  matters most. Never tune this on one clip.
  (4) THE USEFUL CONSEQUENCE: the part-5 blocker is REMOVED, not resolved in its
  favour. 0.4 is already right at 60 fps on both clips, so full-rate processing needs
  no re-tune and NO rate-dependent gap policy. What remains is a product call: 60 fps
  wins the MEASUREMENT decisively and is a wash-to-negative on DETECTION, at 2x
  perception cost.
  CORRECTION, withdrawn from part 5: the ghost increase 6 -> 8 at 60 fps was
  explained there as the Session F frame-step trap ("a 0.4 s bridge holds twice the
  frames"). WRONG — the scorer uses a FIXED set of human-labelled source frames (258
  ball / 26 no-ball, all scoreable at both steps on yt_rally2), so fire counts ARE
  comparable across rates. The increase is real: two more of 26 no-ball frames get a
  drawn ball. Solid fires did fall 5 -> 4, so the extra two are interpolated.
  ALSO MEASURED, and it explains the mechanism: pre-smoother recall is a WASH (68.2%
  at 30 fps vs 67.8% at 60). Backing out interpolated hits, real detections kept are
  168 vs 173 — the Kalman innovation gate rejects FEWER genuine locks at 60 fps
  because smaller inter-frame motion is better predicted by the constant-acceleration
  model. 60 fps does not find more ball; it keeps and reconstructs more of what it
  found. Consistent with the standing "fps buys precision, not recall" result.

- Session I (2026-08-09): LOCALISED CONFUSER WEIGHTING — the product gate FAILS, the
  DETECTOR improves on 6 of 6 clips, and neither claim is what it first looks like.
  Whole-frame negative mining was closed in Phase 0 (the format asks about the FRAME
  when the useful question is the LOCATION), so this weights the per-pixel loss 8x in
  a 12 px disc at every mined confuser: on a frame whose ball position is known, a
  detector argmax >20 px away is a confirmed false fire at a known spot. Yield 3,336
  of 26,293 labelled frames (12.7%). It is RE-WEIGHTING, not new labels — the BCE
  target is already zero there; the racquet head is one pixel among 147,400 scored
  like empty sky. Two 15-epoch arms, `--hard-weight` 1.0 vs 8.0 (1h13m + 1h09m).
  Evidence: data/output/session_i_ab/results.md.
  (1) PRODUCT GATE FAILS. Pooled over the 3 calibrated clips (74 no-ball frames),
  solid ghosts **14 -> 15**, recall 69.2 -> 69.0%. Ninth failure at the ghost ball.
  (2) THE DETECTOR IMPROVED, and consistently: pooled over all 6 gold clips (204
  no-ball, 1201 clicks) false fire **53.9 -> 42.2%** — down on **6 of 6 clips** by
  7.3 to 23.0 pts — at HIGHER recall (79.9 -> 80.4%) and far_px (80.9 -> 82.5%).
  110 -> 86 false fires, a 3.4 sigma shift; the operating point moved outward on both
  axes rather than trading one for the other.
  (3) BUT IT IS NOT ATTRIBUTABLE YET, and this is the load-bearing caveat.
  `train_ballnet.py` had **NO SEED** — no manual_seed, no random.seed — so the two
  arms differ by initialisation, batch order and augmentation draws as well as by the
  flag. Six clips are six measurements of the SAME two models, so the 6/6 sign test
  measures EVALUATION noise; the unit of randomisation for the treatment question is
  the TRAINING RUN, and n=1. Do not record "localised weighting cuts detector false
  fire by 11.7 pts" until a paired re-run says so. FIXED: `--seed` (default 0) seeds
  python/numpy/torch and the train DataLoader's shuffle generator, and
  `train_ballnet.recipe_stamp` writes args/seed/git/dataset counts/`confuser_samples`
  into every checkpoint — closing the same gap that made `ballnet_v21.pt` unusable as
  a control and forced this session to spend an hour training its own baseline.
  (4) A DETECTOR PRECISION GAIN HAS NOW FAILED TO REACH THE PRODUCT THREE TIMES —
  input resolution (Phase 0 gate B), `score_thresh` (Session F step 3), and this. The
  mechanism is consistent: on yt_rally2 the detector's false fire nearly halved
  (61.5 -> 38.5%) while the same clip's tracker-gates-only row went the WRONG way
  (30.8 -> 38.5%). The chain's gates already remove the false fires a better detector
  removes — the easy ones — so what survives to be drawn is a different, harder
  population. Detector precision and chain precision are close to DECOUPLED. Stop
  scoring ghost-ball work at the detector.
  (5) THE GATE HAS NEVER BEEN REPORTED WITH ITS OWN RESOLUTION, across nine runs. It
  is a count of ~14 out of **74** no-ball frames, where sampling alone moves the count
  **+/-3.4**. Near-elimination is detectable (needs 62 frames); HALVING the ghost rate
  needs **212**; a 30% cut needs **656**. So nine nulls license "nothing has come
  close to eliminating the ghost ball", NOT "none of these did anything". The method
  is fine — 204 no-ball frames over six clips resolved an 11.7-pt effect comfortably —
  the CHAIN metric is just restricted to three calibrated clips. NEW
  `tools/gate_verdict.py` pools the clips by summing numerators and denominators (a
  mean of percentages over clips of 26/24/53 frames is not a rate), prints the
  required-n beside the verdict, and warns when the clips disagree in sign.
  (6) TWO MEASUREMENT FIXES. `eval_model_filters` now records WHICH frames fire
  (`fire_frames_solid`), not just how many — a count of 9 that never moves reads
  identically whether every variant fires on the same nine frames or nine different
  ones, and those call for opposite next moves. And the session's own resume list had
  omitted `yt_match40`, one of the three clips in a gate defined as pooled.
  (7) THERE IS A UNIVERSAL HARD CORE, AND IT IS **FIVE FRAMES**, not nine.
  9 of the 20 distinct solid-ghost frames fire on BOTH arms (45%). Scoring
  `ballnet_v21` the same way — a fair question even though it cannot be a training
  control, because this asks which FRAMES defeat it, not how it was made — its pooled
  solid-ghost count comes back at **9**, reproducing the standing figure exactly and
  independently checking the whole measurement chain. But it shares only **5 of the
  arms' 9**: yt_rally2 18/762/1494, yt_match40 4773, am_hard_utr 13276. Those five
  beat a 40-epoch detector and two 15-epoch ones with different initialisations.
  SO THE COUNT IS STABLE AND THE COMPOSITION IS NOT — about half shared — which is
  exactly why a count that never moves was never good evidence of an immovable set.
  Do not describe the ghost floor as "nine specific frames"; it is five universal
  ones plus a model-specific tail. Also visible: v21 has **1** solid ghost on
  am_hard_utr against the arms' 5 and 6, so the 15-epoch arms are worst precisely on
  the low-camera amateur footage this project targets.
  (8) WHY NINE SESSIONS OF FILTERING COULD NOT TOUCH THEM — one number, and it is the
  most useful thing in this session. `inspect_false_locks --stage chain` on v21 over
  the 3 calibrated clips returns 19 false locks on 74 no-ball frames (9 solid + 10
  faded, reproducing Session F). **ALL 19 HAVE `run_len = 1`**, roam 208-829 px. The
  tool's own legend reads "a real ball scores high roam and short run; a fixture the
  reverse" — so every confuser that survives to be DRAWN carries the kinematic
  signature of a real ball. That is not a weakness in `suppress_false_locks`, it is
  the definition it was built on: the persistence test removes things that hold
  still, and these do not hold still. The chain cannot remove them without also
  removing single-frame real-ball sightings, which are exactly the far-court balls
  the project is short of. It also explains why detector-side work does not reach the
  product: this is the TAIL of the error distribution (one-off fires on ball-sized,
  ball-coloured things), and cutting the bulk error rate by 11.7 pts barely moves a
  tail of one-offs. And it explains the stable-count/unstable-composition pattern —
  it is a RATE of single-frame errors, not a fixed set of defeated frames.
  The five universal frames, seen at zoom (data/output/session_i_ab/universal5_zoom.png):
  yt_rally2:18 a fold on the green curtain (class fence), yt_rally2:762 a wall fixture
  above the curtain (NEVER CLASSIFIED - Session F classified raw locks, so some chain
  survivors were never reviewed), yt_rally2:1494 a light blob at a mid-swing player's
  racquet head, yt_match40:4773 ball-coloured foliage in a hedge, am_hard_utr:13276 a
  light object against the dark windscreen beside a player. **NO SINGLE OBJECT TYPE**
  — 3 static scenery, 2 person-attached — which kills "detect the racquet and negate
  it" for this population outright: it reaches 2 of 5.
  NOT ADJUDICATED, ON PURPOSE: two of the five (yt_rally2:1494, am_hard_utr:13276)
  show a light, ball-sized object beside a player mid-swing on a frame a human marked
  "no ball". That may be a racquet head, or a ball at contact the labeller judged not
  in play. Never quietly change human ground truth to suit a model — this is a Lab
  re-label question, alongside the 8 known-bad `am_indoor_hard1` court frames. If some
  of the five are mislabels, part of this "floor" is not a model problem at all.
  NOTE the two arms are 15-epoch and NOT SHIPPABLE (v21 scores 9 solid ghosts; these
  score 14-15). They are committed anyway because they predate `--seed` and can never
  be reproduced, and every number above is measured on those exact files.

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
