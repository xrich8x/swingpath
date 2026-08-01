# CLAUDE.md

Project context for Claude Code. Read this before editing.

## Project docs — read the right one for the task

- **CLAUDE.md** (this file) — architecture, hard rules, current status. Read before editing.
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
  built at an old commit; always re-perceive. NOT yet committed (branch work).
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
  70 / top 95 km/h. demo30's manual corners are DEGENERATE (0.2 m camera, floored
  speeds) — that clip needs re-calibration. amber/coasted still to be excluded
  from speed/bounce (finishing step). 148 tests. NOT yet committed.
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
  THE MECHANISM GENERALISES PAST THIS KNOB: raising the threshold does NOT remove
  ghost balls, because `smooth_forecast` fills the gaps a stricter detector creates.
  On yt_rally2 at 0.7 the chain reaches ZERO fires after suppress_false_locks, then
  the smoother puts back 7, ALL FADED — total ghosts 8 -> 7 (noise) for 6.2 pts of
  recall and 9.5 of far_geo. Only the solid/faded split makes that visible; the
  per-frame number (30.8 -> 26.9%) makes 0.7 look like a win. The ghost ball is, at
  the margin, the SMOOTHER interpolating through dead time, not detector precision
  — that is where the next attempt goes. Gate ordering earned its keep: at 0.6 the
  ghost-ball gate would have PASSED (solid fires down on all 3 clips, up on none)
  and only the recall gate, deliberately ordered first, killed it. 209 tests; the
  shipped 0.5 path is verified byte-identical end to end.

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
  yt_court_pts_doubles 54, yt_court_pts_singles 91, demo30_pts 565.
  demo30 needs re-calibration.
  A LOW camera is not degenerate — it is the amateur case this project targets;
  what it costs is measurable DEPTH, so the audit reports that in metres via
  `calibration.reliable_court_span`. Note the primary 1080p gold clip
  `am_hard_utr` fits a **1.74 m** camera (hfov 86 deg, 0.7 px — good corners,
  low mount) and is measurable only to **court-y 7.5 m of 23.77 (32% of depth)**:
  it does not reach the net at 11.885 m. Treat any far-court number on that clip
  as detection recall, NOT as a measurement.
