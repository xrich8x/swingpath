# Running on a phone — on-device live line calls

This folder holds everything needed to run the analyzer **on a phone**, the way
SwingVision does: the optimized on-device model, the ported call logic, and the
integration plan. The split is deliberate and honest:

- **Done here (the hard ML + logic):** the ball model exported and optimized for
  mobile (ONNX, int8, in-graph decode), the ball *decoder* (`ball_detector.js`)
  verified against `ball.py`'s `BallDetector` on real frames from a gold clip
  (`verify_ball_detector.js` + `backend/ball_detector_parity_probe.py` — see
  below), and the line-call brain ported to pure JavaScript and verified
  against the Python backend two ways: `verify_live.js` (a real cached ball
  track, singles-only) and `verify_live_doubles.js` (synthetic boundary cases,
  singles AND doubles). Python is the reference throughout; "verified" means
  agreement with it, not independent proof of correctness.
- **To build (the app shell):** the native camera capture + UI + store build.
  That's standard React Native work — the assets and logic below are drop-in.

## Why phone-capable at all

Line calls need **only the ball** (no player pose), and the call logic itself is
trivial compute (the JS port runs ~90k calls/sec). So the only thing that must be
fast on-device is the ball model — and TrackNet is tiny. We export it so a phone's
Neural Engine (iOS) / NNAPI-GPU (Android) can run it in real time.

## What's in this folder

```
models/
  tracknet_ball.onnx        fp32 ONNX (reference)
  tracknet_ball.int8.onnx   int8, ~11 MB, self-contained — BUNDLE THIS
export_tracknet.py          how the models were produced (+ verification)
ball_detector.js            on-device ball tracking (onnxruntime-react-native)
verify_ball_detector.js     Node test: JS decode == Python decode, real frames, real ONNX graph
live_calls.js               calibration + bounce + IN/OUT calls (pure JS)
verify_live.js              Node test: JS calls == Python calls, real cached track, singles only
doubles_alley_parity_cases.json  synthetic boundary cases (both singles + doubles), hand-computed expected
verify_live_doubles.js      Node test: JS vs Python on the cases above, singles AND doubles branches
package.json                ESM marker so the .js modules import cleanly
```
(`../backend/ball_detector_parity_probe.py` is `verify_ball_detector.js`'s Python
counterpart — extracts real frames, runs the real PyTorch model, and runs the
real bundled ONNX graph on the JS-built input tensor.)

### The key mobile optimization
The raw model emits a `256 × 360 × 640` tensor (~236 MB/frame) — infeasible to
hand to JS on a phone. The export bakes `argmax` **into the ONNX graph**, so the
runtime returns a single `360 × 640` int heatmap (~0.9 MB), decoded in JS in
microseconds. int8 quantization then shrinks the model from 43 MB → **11 MB**,
and the ball position is **within 0.32 px of the PyTorch model** (12/12 test
frames) — effectively lossless.

## On-device data flow

```
camera frame (vision-camera frame processor)
   → resize to 640×360, RGB bytes
   → BallDetector.detect(frame)          # ball_detector.js + onnxruntime-react-native
        3-frame buffer → 9-ch input → ONNX → heatmap → [x,y] px
   → LiveAnalyzer.push([x,y], t)         # live_calls.js
        homography → court metres → online bounce → IN/OUT
   → overlay the call + play a sound
```

Calibration is one-time per setup (fixed camera): the user taps the 4 court
corners once; `computeHomography()` (in live_calls.js, pure JS) turns those taps
into the homography. No backend, no network — it all runs on the phone.

## Recommended app stack

**React Native** (reuses this project's React knowledge and the shared court
geometry) with:
- [`react-native-vision-camera`](https://react-native-vision-camera.com/) — camera + a **frame processor** to get pixel buffers. The frame processor is the one native bit: grab the YUV/RGB buffer, resize to 640×360. (vision-camera's `resize-plugin` does this.)
- [`onnxruntime-react-native`](https://onnxruntime.ai/docs/get-started/with-javascript/react-native.html) — runs the ONNX model on-device (CoreML execution provider on iOS, NNAPI on Android for hardware acceleration).
- `ball_detector.js` + `live_calls.js` from this folder — copied in as-is.

```
npm i react-native-vision-camera vision-camera-resize-plugin onnxruntime-react-native
# bundle mobile/models/tracknet_ball.int8.onnx as an app asset
```

Minimal wiring (inside a vision-camera frame processor result handler):
```js
import { InferenceSession } from "onnxruntime-react-native";
import { BallDetector } from "./ball_detector.js";
import { LiveAnalyzer, computeHomography, LANDMARKS } from "./live_calls.js";

const session = await InferenceSession.create(modelPath, {
  executionProviders: ["coreml", "nnapi", "cpu"], // hardware-accelerate where available
});
const ball = new BallDetector(session);

// after the one-time corner-tap calibration:
const H = computeHomography(cornerNames.map(n => LANDMARKS[n]), tappedPixels);
const live = new LiveAnalyzer(H, { singles: true });

// per frame (rgb = 640x360 RGB bytes from the resize plugin):
const px = await ball.detect(rgb, frameWidth, frameHeight);
const call = live.push(px, timestampSeconds);
if (call) showCall(call); // { call: "in"|"out", margin_m, xy, t_s }
```

## Performance — measured, and the honest caveat

Verified on desktop (from `export_tracknet.py`):
- **Accuracy:** fp32 ONNX = PyTorch exactly (0.00 px); int8 within **0.32 px**. This
  is the ONNX *graph's* fidelity to the PyTorch model, checked with Python's own
  (correct) decode on both sides — a different question from whether the JS
  *port's* decode agrees with Python, which is what `verify_ball_detector.js`
  checks (see below).
- **Output size:** 0.9 MB/frame (in-graph argmax) vs 236 MB raw — the change that makes on-device decode possible.
- **Model size:** 43 MB → **11 MB** (int8).

**`ball_detector.js`'s decode, separately verified against real frames**
(2026-09-02): input-tensor channel packing was already bit-exact; the decode
*algorithm* was not — the port used global-argmax + a small fixed window while
`ball.py`'s `_postprocess` uses full-image connected-component analysis scored
by area×peak. On 178 real contiguous frames from `data/incoming/Hardcourt/
am_hard_utr.mp4` (61 real TrackNet detections), that difference caused 4/61
gross mismatches (up to 238px) whenever the heatmap had two separate blobs —
JS locked onto the single brightest pixel's blob, Python picked the larger,
more coherent one. Fixed by porting the same connected-component + area×peak
algorithm into JS (`_decode`, ball_detector.js); re-verified 61/61 exact
(0.00px) on the same real frames, through the real bundled fp32 ONNX graph.
See [evidence/ball-detector-parity-tracknet.md](../docs/evidence/ball-detector-parity-tracknet.md).

**Important caveat on speed:** I could NOT benchmark a phone here. On this desktop
x86 CPU, int8 was actually *slower* than fp32 (a well-known quantization-kernel
pathology on x86 — int8 only pays off where there's hardware int8 support). So:
- **On a phone, use the CoreML (iOS) / NNAPI (Android) execution provider** — those have native int8 acceleration, which is where the 11 MB int8 model shines and is expected to hit real-time. That's how SwingVision does it.
- **On a desktop/CPU fallback, use `tracknet_ball.onnx` (fp32)** — it matched PyTorch speed (~1 s/frame on this CPU), not the int8 build.

I'm flagging this rather than quoting a phone fps I haven't measured. The model is
tiny (a few MFLOPs/frame) and structured for mobile NN accelerators; real-time on
a modern device is the design target, but it needs validation on a real handset.

## What still needs a real device / mobile dev

- The vision-camera **frame processor** (native frame → 640×360 RGB) — ~30 lines, plugin-assisted.
- App UI: calibration screen (tap 4 corners), live overlay, call history, sound.
- Build/sign for TestFlight / Play Store.

None of that touches the ML or the call logic — those are done and verified here.

## Limitations (same as the rest of the project)

- Single camera → no true ball height; bounce is a court-speed heuristic, so
  calls are best-effort (real SwingVision has the same constraint).
- A fixed camera + good corner calibration dominate accuracy.
- For player movement/stats too (not just line calls), also export a pose model
  (`yolo export format=onnx` / `coreml`), but that's heavier — line calls don't need it.
