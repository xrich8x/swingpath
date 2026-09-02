# `mobile/ball_detector.js` vs `backend/swingvision/ball.py` `BallDetector` — TrackNet port parity

Third sibling check after `mobile/live_calls.js`'s two bugs (a calibration-key crash
that killed the only parity harness, and a doubles-alley branch that called an
in-bounds ball OUT). Task: establish whether the ONNX TrackNet port agrees with
the Python reference. Assume nothing verified going in.

**Python is the reference throughout.** `backend/swingvision/ball.py` was not
edited except to be called, read-only, by the probe script below. Only
`mobile/ball_detector.js` moved.

## What should be identical — read first, then measured

| | Python `BallDetector` (`ball.py:1047+`) | JS `ball_detector.js` |
|---|---|---|
| Input size | `in_h, in_w = 360, 640` | `IN_W=640, IN_H=360` — match |
| Frame buffer | `deque(maxlen=3)`; fills on calls 1-2, emits from call 3; `cur,prev,preprev = buf[2],buf[1],buf[0]` | `buf.push` + `shift()` when `length>3`; same fill/emit timing; `order=[buf[2],buf[1],buf[0]]` — match |
| Channel order | `concat([cur,prev,preprev], axis=2)`, each native-BGR (cv2), `/255`, `rollaxis` to CHW `(9,H,W)` — channel layout `[cur_B,cur_G,cur_R,prev_B,prev_G,prev_R,preprev_B,preprev_G,preprev_R]` | Per-frame R/G/B read from an RGB camera frame, written as B,G,R into the same channel-major layout, same order, `/255` — match (verified bit-exact, see below) |
| Decode threshold | `cv2.threshold(fm, 127, 255, BINARY)` selects `fm > 127` i.e. `>= 128` | `this.threshold = 128`, `>=` checks | Different literal (127 vs 128), same effective set on integer inputs — not a bug |
| **Decode algorithm** | `_postprocess`: 8-connected-component analysis over the WHOLE thresholded heatmap (`cv2.connectedComponentsWithStats`), pick the component maximizing `area * peak`, return its **unweighted geometric centroid** | **Was**: global argmax pixel, then an intensity-weighted centroid over a fixed **+-3px window** around it only | **Real divergence, found by reading, before any run** — different algorithm, not a rounding difference. Fixed (see below). |

## Assets used

- `data/incoming/Hardcourt/am_hard_utr.mp4` — a real gold amateur match clip
  (28,998 frames, 59.94 fps, 1920x1080). Chosen because
  `data/output/detector_ab/am_hard_utr.tracknet.perception.json` already
  confirms TrackNet fires repeatedly on this exact clip, so a contiguous span
  was known in advance to contain real ball detections rather than being a
  blind guess. `data/tennis_sample.mp4` (named in `export_tracknet.py`) does
  not exist at that path; the working videos in this repo live under
  `data/incoming/<Surface>/*.mp4`.
- 180 contiguous source frames (0-179), no frame skipping, decoded fresh with
  `cv2.VideoCapture` — 178 usable 3-frame triples. Python's real
  `BallDetector.detect()` fired (non-null) on 61/178.
- `backend/weights/tracknet.pt` (the real production weights) and
  `mobile/models/tracknet_ball.onnx` (the real bundled fp32 export — the
  literal file mobile ships, not a re-export).

## What ran, and why it counts as real

`onnxruntime-react-native` is not installed anywhere in this environment (no
`node_modules` under `mobile/`, offline, nothing fabricated to stand in for
it). `ball_detector.js` only imports it dynamically **inside** `detect()`;
`_buildInput()` and `_decode()` — the two methods actually in question — have
no runtime dependency and run under plain Node unmodified. Plan, mirroring the
video-free technique used for `live_calls.js`: drive the REAL methods on REAL
data, substitute only the one runtime binding that cannot be exercised here.

1. **Python (`backend/ball_detector_parity_probe.py extract`)**: for each real
   triple, replicates `ball.py:1092-1105` verbatim (not reimplemented logic,
   the same resize/concat/rollaxis/forward-pass/argmax) to capture the
   intermediate input tensor and heatmap `detect()` computes but does not
   return, and calls the REAL, unmodified `bd._postprocess()` for the
   reference decode. Dumps: 3 raw RGB frames per triple (for JS), Python's own
   input tensor, the raw heatmap, and Python's decoded `(x,y)`.
2. **JS (`mobile/verify_ball_detector.js build-decode`)**: loads the raw RGB
   frames, replicates the real deque state (`buf=[preprev,prev,cur]`, valid
   per-triple since a maxlen-3 deque has no memory beyond its last 3 elements —
   same technique as the doubles-alley cases' isolated construction), calls
   the REAL `_buildInput()` and dumps it; calls the REAL `_decode()` on
   Python's real heatmap (decode-only isolation, no ONNX/runtime involved).
3. **Python (`... onnx-run`)**: runs the REAL bundled `tracknet_ball.onnx`
   (fp32) via `onnxruntime` (Python) on JS's OWN `_buildInput()` output — the
   same graph file `onnxruntime-react-native` would load, just a different
   engine binding. Dumps the resulting heatmap.
4. **JS (`... decode-onnx`)**: calls the REAL `_decode()` on that ONNX
   heatmap — full pipeline: JS input-build -> real ONNX graph -> JS decode.
5. **Python (`... compare`)**: diffs both legs against Python's real
   end-to-end `detect()` output.

**Not verified**: the `onnxruntime-react-native` engine binding itself (iOS
CoreML/NNAPI execution provider parity with `onnxruntime` desktop CPU) — the
one link in the chain this machine cannot exercise. Everything else in
`ball_detector.js` ran as its real, unmodified self.

## Pre-registered bar (written before any comparison ran)

1. **Input tensor parity**: JS-built vs Python-built tensor, same 3 real
   frames — near-bit-exact, `<1e-5` max abs diff (pure arithmetic, no
   algorithm choice).
2. **Decode agreement**, ~60+ real frames:
   - (a) null/non-null agreement `>=90%` — the severe failure mode (a missing
     ball changes the IN/OUT call outright).
   - (b) when both sides fire: position agreement within **5px** (640x360
     inference space) on `>=80%` of those frames — loose on purpose, because
     the two decode algorithms were known (from the spec read) to differ by
     design and could legitimately land a few px apart on the same real blob;
     this bar exists to catch a GROSS divergence (different blob), not
     sub-pixel disagreement.

A failed bar stays failed. Not loosened after seeing the numbers below.

## Measured — BEFORE the fix

```
1. INPUT TENSOR PARITY: max abs diff 0.00000000 (sample of 20 triples) — PASS
2. DECODE PARITY (identical real heatmap, both sides): 178 frames
   null/non-null agreement: 178/178 (100.0%)
   position agreement (<=5px) when both fire: 57/61 (93.4%)
   position diff distribution: min=0.00 median=0.06 max=238.64 px
   4 mismatches, ALL on frames with two separate heatmap blobs (see below)
3. FULL PIPELINE (JS build -> real ONNX fp32 -> JS decode): identical numbers
   to (2) — the ONNX graph itself introduces no additional divergence.
```

Both pre-registered bars technically **PASS** (100% >= 90%; 93.4% >= 80%). But
the 4 mismatches are not noise — they are the exact mechanism predicted from
the spec read, confirmed by inspecting the heatmaps directly:

```
tag   n_components  global_argmax(y,x)  winning component (Python)      argmax's own component (JS's pick)
0080  2             (107, 383)          area=12 peak=220 score=2640     area=1  peak=220 score=220
0119  2             (192, 317)          area=14 peak=242 score=3388     area=13 peak=242 score=3146
0147  2             (191, 313)          area=15 peak=220 score=3300     area=13 peak=242 score=3146
0150  2             (301, 560)          area=9  peak=220 score=1980     area=1  peak=242 score=242
```

In every mismatch, the heatmap has two separate 8-connected blobs. Python's
`area * peak` scoring correctly prefers the larger, more spatially coherent
blob (12-15 px, almost certainly the real ball). JS's old global-argmax
approach always locked onto whichever single pixel happened to be brightest —
in these frames, a smaller/isolated blob elsewhere in the frame (plausibly a
false response: court line, kit, or sensor noise) — and its fixed +-3px window
never even saw the real blob a few dozen pixels away. This is a **confident
wrong lock, not a refusal** — exactly the failure mode this product is
designed to avoid elsewhere (a scoreline that isn't a measurement, a
distance stat that refuses below coverage, a too-close call that says so
rather than inventing a number). The port's own docstring claims to "mirror"
`ball.py`; on this axis it did not.

## Fix

`_decode()` in `mobile/ball_detector.js` reimplemented as a plain BFS 8-
connected-component flood-fill over the thresholded heatmap, matching
`cv2.connectedComponentsWithStats(binm, connectivity=8)`: per component, track
pixel count, coordinate sums (unweighted), and peak value; select by
`area * peak`; return the unweighted mean `(x, y)`. No new dependency —
pure JS, O(HW) worst case, same order as the code it replaced.

## Measured — AFTER the fix

```
2. DECODE PARITY: 178 frames, null-agreement 178/178 (100%),
   position agreement 61/61 (100%), diff distribution min=median=max=0.00px
3. FULL PIPELINE (real ONNX graph): identical, 61/61, 0.00px
```

**Confirmed non-vacuous**: `git stash push -- mobile/ball_detector.js` to
restore the pre-fix version, re-ran both node phases + the Python compare —
reproduced the exact same 4 mismatches, identical distances (37.8 / 87.1 /
71.1 / 238.6 px) to before. `git stash pop` restored the fix; re-ran — back to
61/61, 0.00px.

## The 2026-08-27 "mobile bundles the wrong detector" note — now STALE

The 2026-08-27 mobile viability audit (`docs/STATE.md` row, evidence
`mobile-viability-audit.md`) recorded as a defect: "mobile bundles a TrackNet
export while the shipped default is BallNet v21." At the time that was an
accurate observation. It is now stale: the founder ruled on 2026-08-29 that
**v1 ships TrackNet** (recorded in `.claude/agent-memory/pm/
founder-rulings-2026-08-29.md`, ruling 1 — "TrackNet's failure mode was
preferred over BallNet v21's, and TrackNet is the only detector with a Core ML
path today. BallNet v21 remains the upgrade path"). `docs/STATE.md`'s ball-
detection row (line ~44-45) still lists BallNet v21 as the **desktop**
pipeline's default — that is a separate product (`run.py analyze`) and that
default is unchanged. Mobile correctly bundles the model v1 actually ships.
Closed as stale in the STATE.md row itself (struck through with the
correction, not deleted — rule 9 territory adjacent: the original finding was
correct when made, only the context under it moved).

## What was NOT verified

- **The `onnxruntime-react-native` engine binding** — CoreML (iOS) / NNAPI
  execution-provider numeric parity with desktop `onnxruntime`'s CPU provider.
  Cannot be exercised on this machine (no RN runtime installed, offline).
  `export_tracknet.py`'s own fp32-vs-PyTorch check (`0.00 px`, `_postprocess`
  on both sides) is evidence the ONNX *graph* itself is faithful, but that is
  a Python-only check and does not touch the RN binding.
- **The int8 model** (`tracknet_ball.int8.onnx`) — this check used fp32
  throughout, matching what `export_tracknet.py` calls "the reference." int8
  vs fp32 decode drift (`export_tracknet.py`'s own 0.32px figure) is a
  separate, already-measured question and wasn't re-run here.
- **The native camera resize path** (1080p/4K frame -> 640x360 RGB) — Python's
  `detect()` resizes internally with `cv2.resize`; the JS port assumes the
  caller (a vision-camera frame processor) already delivers 360x640 RGB. This
  probe fed both sides frames pre-resized by the same `cv2.resize` call, so it
  does not test whatever resize algorithm the native frame processor will
  actually use.
- **Real-time performance on a phone** — no fps has ever been measured on
  device anywhere in this repo; not attempted here either.

## Reproduce

```
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py extract <dir>
node mobile/verify_ball_detector.js build-decode   # BALL_PARITY_DIR=<dir>
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py onnx-run <dir>
node mobile/verify_ball_detector.js decode-onnx    # BALL_PARITY_DIR=<dir>
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py compare <dir>
```

`<dir>` is any writable scratch directory (`BALL_PARITY_DIR` env var for the
Node steps, positional arg for the Python steps); large per-frame binaries are
NOT committed, only the two scripts and the compact
`data/output/ball_detector_parity_summary.json` result.
