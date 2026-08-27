# Mobile viability — the port is SPLIT, not uniform (audited 2026-08-27)

> Evidence for the `mobile-viability` row in [docs/STATE.md](../STATE.md) (Open).
> Read-only audit of the shipped stack against the iOS + Android on-device target.
> Nothing was changed to produce it. **No code was run and no phone was involved** —
> this is a static read of dependencies, call sites and control flow.

**The headline: live line calls are a straightforward port that is largely done; the
offline match analyzer is a significant rebuild.** The concern that prompted this audit
— that the codebase was built assuming a PC — is directionally right but narrower than
feared. There are no Windows paths, no GUI calls and no exotic OpenCV usage in the
shipped core. What is desktop-class is the *architecture of the offline analyzer*,
specifically its non-causal smoothing and its whole-video passes.

---

## 1. What the shipped core actually depends on

`backend/swingvision/` is ~10,700 lines of Python across 23 modules.

| Dependency | Verdict on-device |
|---|---|
| `numpy`, `scipy` | **Blocked.** No Python runtime on iOS; impractical on Android for a store app. Reimplementation, not port. |
| `opencv-python` | **Portable algorithms, unusable bindings.** Every cv2 symbol used is core OpenCV — `resize`, `cvtColor`, `distanceTransform`, `HoughLinesP`, `morphologyEx`, `connectedComponentsWithStats`, `Sobel`, `threshold`, `getStructuringElement`, `convexHull`, `pointPolygonTest`, `solvePnP`, `SOLVEPNP_IPPE`, `Rodrigues`, `findHomography`, `projectPoints`, `createCLAHE`, `findTransformECC`, `absdiff`, `VideoCapture`, `VideoWriter`. All present in OpenCV's Android/iOS builds. |
| `torch`, `torchvision` | **Blocked as-is.** Export path only (ONNX/CoreML/TFLite); partly done for the ball model, not at all for pose. |
| `ultralytics` (YOLO-pose) | **Blocked as-is.** `yolo11m@1280` default, `yolo11x@1920` for the far player. Not phone-viable at those input sizes without export and heavy downscale. Not started. |
| `imageio-ffmpeg` + `subprocess.run` | **Blocked where used.** A bundled desktop ffmpeg binary. Used by `annotate.py` (H.264 transcode), `audio.py` (audio extract), `highlights.py` (stream-copy cutting). All three are export/post-processing, not the measurement core. |
| `gdown` | Dev-time weight fetch. Irrelevant to shipping. |

**Cleaner than expected, and worth recording as negatives:**

- **No Windows-specific code in the shipped core.** Grepped for drive letters, `.exe`,
  `os.name`, `sys.platform` and backslash paths across `backend/swingvision/*.py` —
  zero hits. The `backend/.venv/Scripts/python.exe` form appears only in dev docs and
  tooling.
- **No `highgui` in the pipeline.** `imshow` / `namedWindow` / `waitKey` appear in
  exactly one file, `backend/calibrate.py`, which is a dev tool outside the analyzer.
- **cv2 is imported lazily**, inside functions, at ~50 call sites rather than at module
  top level. So the modules that do not touch video (`analytics`, `scoring`,
  `corrections`, `court`, `schema`) import with no OpenCV present at all.

## 2. Can the pipeline run on-device today?

**The offline analyzer: no.** It is a desktop-class batch program — not a client/server
split, since there is no server, but it assumes desktop resources throughout.

- **Non-causal smoothing, by construction.** `ball.smooth_forecast` is a
  constant-acceleration Kalman filter plus an **RTS forward-backward** pass
  (`ball.py:647`), and `smooth_and_fill` applies Savitzky-Golay. Both need the whole
  segment in hand. This is not an implementation detail that can be streamed around —
  making it causal changes what it computes.
- **Whole-video multi-pass.** `pipeline._perceive` (`pipeline.py:864`) runs detector and
  pose over every `frame_step`-th frame of the entire clip and materialises full
  per-frame arrays; events, speed and score then run over the complete track.
- **Desktop frame budget.** ~0.7–1.1 s/frame on CPU. A 10-minute 30 fps clip is 18,000
  frames.
- **Desktop I/O assumptions.** Random seeking via `CAP_PROP_POS_FRAMES`, and perception
  cached to JSON on disk.

**This is a stated design decision, not desktop-era sloppiness.** `docs/STATE.md`
records the shipped stack as "Offline-first by design; there is no real-time
requirement." The audit's finding is that the decision has a mobile cost, not that it
was made carelessly.

**The live path: yes, and it already exists.** `backend/swingvision/live.py` (187 lines)
is genuinely streaming and causal — `push_frame(frame, t)` / `push_position(px, t)`, one
frame in, a call out. No cv2, no torch. It deliberately drops player pose, because line
calls need only the ball, and that is what makes it feasible.

## 2a. CORRECTION 2026-08-27 — non-causality only binds the REAL-TIME path

Added the same day, after the user chose a parity-first direction. §2 above is factually
correct but its emphasis misleads on the path now being scoped, so it is corrected here
rather than rewritten.

**The claim to be careful with:** "the smoother is non-causal, therefore the offline
analyzer is a rebuild." The first half is true. The inference is only valid **if the
product demands real-time output.**

It does not. This product is offline-first by design — `docs/STATE.md`: *"Offline-first
by design; there is no real-time requirement."* On a phone that maps to **record, then
process on-device**, as a background job. Over a finished recording the Kalman + RTS
forward-backward smoother has the whole track in hand and works exactly as it does
today. **Non-causality is not an obstacle on the parity path**, and any plan that
proposes a buffered-replay architecture to work around it there is solving a constraint
that is not active.

Non-causality binds only the live line-call path, where output is demanded during the
point. That is a real constraint on *that* feature and nothing else.

**What actually blocks parity on-device, restated:**

1. **Runtime** — no on-device Python. All three perception stages need an
   ONNX/CoreML/TFLite path. Only the ball has one, and it is a TrackNet export while the
   shipped default is BallNet v21. Court and pose have no export at all.
2. **Compute budget** — ~0.7–1.1 s/frame on desktop CPU (pose ~0.4 at the fast preset,
   ball ~0.7). 18,000 frames in a 10-minute 30 fps clip. A background job of tens of
   minutes, and whether that is acceptable is a product question, not a technical one.
3. **Thermal throttling** — a sustained multi-minute inference job is precisely where it
   bites. Budget on frame 1 is not budget on frame 5000.
4. **The classical CV** — ~2,900 lines with no conversion toolchain, becoming a shared
   C++ core. The algorithms port; the Python bindings do not.
5. **ffmpeg** — three features shell out to a bundled desktop binary.

None of these is about causality. They are about runtime, silicon and heat.

## 3. Scope of the change

**Small — the remaining live-calls work.** The vision-camera frame processor (native
frame → 640×360 RGB), app UI, store build. Per `mobile/MOBILE.md` the frame processor is
~30 lines, plugin-assisted.

**Large — rebuild, not port.**

- **Court auto-detection.** `courtfit.py` (1,118) + `calibration.py` (1,793) ≈ 2,900
  lines of hand-written classical CV: Hough, a 5-parameter seed search, refinement,
  consensus voting, the CLAHE clay mask, `solvePnP` camera fit. There is no conversion
  toolchain for this — it becomes a shared C++ core over OpenCV's mobile builds behind
  thin platform wrappers. **A v1 can skip this entirely**: manual 4-corner tap is the
  designed fallback and is already pure JS (`computeHomography` in `live_calls.js`).
  Note also that this is currently the weakest subsystem in the project (12/20 gate
  acceptance), so porting it ports a known-fragile component.
- **Offline analysis on-device.** `pipeline.py` (2,131) + `events.py` (645) +
  `speedspin.py` (256). A rewrite, because of the non-causal smoothing and whole-video
  arrays above.
- **Pose / player stats.** Ultralytics export not started.
- **ffmpeg-dependent features.** Need native AVFoundation / MediaCodec equivalents.

## 4. Already mobile-ready — what is salvageable as-is

- **`mobile/`** — ONNX fp32 + int8 (11 MB), argmax baked into the graph so per-frame
  output is 0.9 MB rather than 236 MB, int8 within **0.32 px** of PyTorch.
  `ball_detector.js`, `live_calls.js`, `verify_live.js`, plus `MOBILE.md`.
- **`live.py`** — the right shape already, and ported to JS and verified bit-identical.
- **`court.py`** (109 lines) — constants and geometry, mirrored to `frontend/src/lib/court.js`
  and parity-enforced by `tests/test_js_mirror_parity.py`.
- **`schema.py`, `analytics.py`, `scoring.py`, `corrections.py`** — pure logic, no heavy
  deps.
- **Every closed-form geometry routine.** The architectural rule that geometry stays
  closed-form and is never learned is exactly what makes it portable to any language.
  That decision has already paid a mobile dividend nobody framed it as buying.

## 5. Two defects found en route

- **Mobile and desktop run DIFFERENT ball models.** `mobile/models/*.onnx` are exported
  from `_tracknet.py` (`mobile/export_tracknet.py` line 24), but `docs/STATE.md` lists
  **BallNet v21** as the shipped default detector. *Nuance, from the same table:* at the
  field's F1@4 threshold TrackNet wins 9 of 10 gold clips, so which model is "better"
  depends on the metric — this is logged as a silent divergence to resolve deliberately,
  not as an automatic regression.
- **`docs/modules.md` overclaimed.** It read "the app shell is the remaining mobile-dev
  work; the ML + call logic are done here." True for live calls, false for the offline
  analyzer. Corrected in the same commit as this file.

## 6. The honest caveat on every performance statement here

**No phone benchmark exists anywhere in this repo.** Not one. Every mobile speed
statement — including `MOBILE.md`'s "real-time on a modern device is the design target"
— is an expectation from model size and structure, never a measurement. `docs/STATE.md`
already carries the standing rule: *no phone fps has ever been measured, so do not quote
one.* This audit does not change that, and adds no number of its own.
