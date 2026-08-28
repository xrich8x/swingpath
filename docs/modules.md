# Modules — what is real, what each subsystem does, what it costs

> Moved out of CLAUDE.md on 2026-08-26. None of this is needed on a typical
> turn; it is here for when you are actually working on that subsystem.
> Mobile integration detail is in [../mobile/MOBILE.md](../mobile/MOBILE.md).

Text preserved verbatim from CLAUDE.md.

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
  quote a phone fps.
- **The port is SPLIT — do not read the line above as covering the product.** For
  **live line calls**, the ML + call logic really are done here and the app shell
  (frame processor, UI, store build) is the remaining work. For the **offline
  analyzer** that is false: it is a rebuild, not a port. Its smoother is non-causal
  by construction (Kalman + RTS forward-backward, plus Savitzky-Golay), it runs
  whole-video multi-pass with full per-frame arrays, court auto-detection is ~2,900
  lines of classical CV with no conversion toolchain, pose is not exported at all,
  and three features shell out to a bundled desktop ffmpeg. Audit:
  [evidence/mobile-viability-audit.md](evidence/mobile-viability-audit.md).
- Known divergence: `mobile/models/*.onnx` are exported from `_tracknet.py`, while
  the shipped default detector is **BallNet v21**. Mobile and desktop run different
  ball models.
- **`audio.py` on-device, scoped 2026-08-28:** three items, not one. (1)
  `extract_audio` shells out to the bundled desktop ffmpeg → `AVAssetReader` /
  `AVAudioFile` + `AVAudioConverter`. (2) `sosfiltfilt` → a vDSP biquad cascade,
  and the padding is the hard part: 4 sections, zero-phase double pass, scipy
  `padtype='odd'` with `padlen=27`; getting it wrong moves the output 4.83% of
  peak in the first and last 27 samples. Needs a parity harness, not an
  assumption. (3) The rolling median/MAD floor is **O(n·win)** and has no
  Accelerate primitive; the exact O(log win) streaming replacement is prototyped
  in `tools/audio_ondevice_probe.py` and pinned by
  `backend/tests/test_audio_streaming_floor.py`. Detail:
  [evidence/audio-impact-feasibility-screen.md](evidence/audio-impact-feasibility-screen.md).

## Performance (CPU)

- The cost is perception. Pose dominated it: yolo11x@1920 ~2.4s/frame resolves a
  small far player but is slow; pose now defaults to the "fast" preset
  (yolo11m@1280, ~0.4s/frame). pose_quality fast|balanced|accurate trades speed
  for the far player. Ball (TrackNet, 360x640) is ~0.7s/frame and is now the
  floor — batching doesn't help it on CPU (compute-bound), so don't add it.
- frame_step="auto" targets ~30fps (TrackNet's rate), halving work on 60fps phone
  clips. Perception is cached at <out>.perception.json. analyze prints fps.
- Court detection is one-time (calibration), not per-frame — already efficient.
