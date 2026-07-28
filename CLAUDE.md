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
  swapped / near-baseline at top of frame / camera height <2 m) and silently break
  the court overlay + ball gating. KNOWN BAD: yt_court_pts_doubles.json,
  yt_court_pts_refined.json, demo30_pts.json. KNOWN GOOD: yt_rally2_pts.json,
  yt_match40_pts.json, yt_court_pts.json. ALWAYS validate a corners file before use:
  `tools/validate_new_clip.py --audit data/<clip>_pts.json` (checks camera height
  2-15 m, orientation, no horizon-crossing). demo30 needs re-calibration.
