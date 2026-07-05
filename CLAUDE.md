# CLAUDE.md

Project context for Claude Code. Read this before editing.

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
