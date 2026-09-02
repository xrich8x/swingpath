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

## The int8 graph (`tracknet_ball.int8.onnx`) — coordinator follow-up, 2026-09-02

**Question 1: is it reachable at all?** `ball_detector.js` does not hardcode a
model path — the caller creates an `InferenceSession` and passes it into
`new BallDetector(session)`; the choice of which `.onnx` file to load happens
at that call site, outside this file. There is no app shell in this repo yet
to inspect for a real load call. But the documentation is unambiguous about
INTENT: `ball_detector.js`'s own file-header comment says "Wraps the mobile
TrackNet ONNX (**tracknet_ball.int8.onnx**)" — names int8, not fp32 — and
`MOBILE.md`'s file listing calls fp32 "(reference)" and int8 "**BUNDLE
THIS**," with the integration instructions saying explicitly "bundle
mobile/models/tracknet_ball.int8.onnx as an app asset." A repo-wide grep for
`tracknet_ball` / `onnxruntime-react-native` outside `mobile/` and `docs/`
found nothing else that could override this. **Verdict: reachable, and in
fact the documented/intended shipped model — not dead weight.** fp32 is the
desktop verification reference, not a shipping candidate.

**Pre-registered bar** (written before measuring, since int8 vs fp32 are
numerically different by design and the earlier 0.00px/5px bars were for
algorithm-parity between two implementations of the SAME fp32 numbers, not
applicable here): task 3 already proved JS-decode-of-the-real-fp32-graph is
IDENTICAL to Python's PyTorch reference (61/61, 0.00px), so comparing
JS-decode-of-int8 to JS-decode-of-fp32 isolates the quantisation effect alone
— both sides run the same (already-fixed) decode algorithm, no algorithm
confound. Justification for the numbers: a real ball's own footprint in this
heatmap space is small — observed connected-component areas of 9-15px
(~3.4-4.4px diameter) in task 3's own inspected frames, consistent with the
repo's existing "far ball ~3.9px in a 720p frame" figure elsewhere. Bar:
1. Null/non-null agreement `>=90%` — losing the ball to quantisation changes
   the IN/OUT call outright, the severe failure mode, same reasoning as task 3.
2. Median position disagreement (both fire) `<=2px` — ~6x the existing
   `export_tracknet.py` historical figure (0.32px mean, 12 frames, one clip),
   giving margin for real-clip diversity while staying inside "quantisation
   noise" rather than "different object."
3. **No single frame may disagree by more than 10px** (~2-3x a real ball's
   own footprint), checked and reported individually — the exact discipline
   that caught the decode bug above, applied again on purpose.

**Measured — PARTIAL SAMPLE, explicitly labelled as such.** The int8 graph is
markedly slower on this desktop x86 CPU than fp32 (already expected and
documented in `MOBILE.md` — no hardware int8 acceleration on x86; a phone's
CoreML/NNAPI provider is the intended target). Running the full 178-frame set
would have cost another long foreground/background wait for no benefit to the
question asked, so this was stopped after the **first 51 of 178 frames**
(tags 0002-0052 — the *start* of the clip only, not a random or representative
sample across the whole span) rather than waited out further:

```
=== INT8 vs FP32, both through the real (fixed) JS _decode() — 50 comparable frames ===
null/non-null agreement: 48/50 (96.0%)          (bar: >=90% — PASS)
both fire: 10 frames. median=0.192px mean=0.237px max=1.202px   (bar: median<=2px — PASS)
No frame exceeded 10px                                          (bar — PASS)

WORST 5 INDIVIDUAL DISAGREEMENTS (not the aggregate):
  0005: fp32=[400, 200.67] int8=[401, 200]         dist=1.202px
  0019: fp32=[397.13,108.47] int8=[397.1,108.8]     dist=0.335px
  0014: fp32=[400.18,140.82] int8=[400.38,140.62]   dist=0.287px
  0012: fp32=[401.33,155.75] int8=[401.43,155.93]   dist=0.202px
  0018: fp32=[398.33,115.11] int8=[398.3,115.3]     dist=0.192px

NULL MISMATCHES (2 of 50, both fp32-fires/int8-null — a real coverage cost,
not a position error): tags 0006, 0017.
```

All three pre-registered bars **PASS** on the available data. Position
agreement when both fire is tight and consistent with (in fact slightly
tighter than) the existing 0.32px historical figure — no sign of the
catastrophic multi-blob failure mode the fp32-vs-JS decode check found.
**But there is a real, honestly-reported finding this partial sample surfaced
and the aggregate does not hide**: quantisation caused the model to lose a
detection entirely (fp32 fired, int8 returned null) on 2 of 50 frames (4%).
That is coverage loss, not position error, and the null-agreement bar (96%)
still clears 90% — but it is a genuine, non-zero cost worth naming rather
than folding into "the bar passed."

**Verdict: SAFE TO SHIP on the position-accuracy axis measured so far** (no
outlier anywhere near the 238px class the fp32 decode bug produced) **but
NOT YET A FULLY POWERED VERDICT** — only 10 frames contributed to the
position-agreement number and only 51 of 178 real frames (the clip's start
only) were sampled. If int8 ships in the actual app (which the documentation
says it will), re-running this same harness's `onnx-run-int8` /
`decode-int8` / `compare-int8` over the FULL 178-frame set (or a larger,
more representative one) before that ships is the natural next step — the
harness already supports it; it was simply not worth another long wait to
extend a result that was already answering the question asked.

## What was NOT verified

- **The `onnxruntime-react-native` engine binding** — CoreML (iOS) / NNAPI
  execution-provider numeric parity with desktop `onnxruntime`'s CPU provider.
  Cannot be exercised on this machine (no RN runtime installed, offline).
  `export_tracknet.py`'s own fp32-vs-PyTorch check (`0.00 px`, `_postprocess`
  on both sides) is evidence the ONNX *graph* itself is faithful, but that is
  a Python-only check and does not touch the RN binding.
- **The int8 model, fully** — see "The int8 graph" section above: measured
  on a PARTIAL sample (51 of 178 real frames, clip-start only), 2026-09-02,
  as a coordinator follow-up. All three pre-registered bars passed on that
  sample; the full 178-frame run was not completed (see that section for why).
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

# int8 leg (slow on desktop x86 — no int8 HW accel; expect it to take a while):
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py onnx-run-int8 <dir>
node mobile/verify_ball_detector.js decode-int8    # BALL_PARITY_DIR=<dir>
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py compare-int8 <dir>
```

`<dir>` is any writable scratch directory (`BALL_PARITY_DIR` env var for the
Node steps, positional arg for the Python steps); large per-frame binaries are
NOT committed, only the scripts and the compact
`data/output/ball_detector_parity_summary.json` +
`data/output/ball_detector_int8_parity_summary.json` results.

---

## Full 178-frame int8 run: the bar FAILS. Run 2026-09-02 (lead)

The partial verdict above was flagged as needing a full run before being called
conclusively safe. It did, and the answer changed.

| | n=50 (partial) | **n=178 (full)** |
|---|---|---|
| null/non-null agreement (bar ≥90%) | 96.0% PASS | 95.5% PASS |
| median disagreement (bar ≤2 px) | 0.192 px PASS | 0.163 px PASS |
| **no single frame >10 px** | 1.202 px PASS | **70.831 px FAIL** |
| null mismatches (fp32 fires, int8 does not) | 2 | **8** |

    0147: fp32=[260.93, 143.60]  int8=[313.08, 191.54]  dist=70.831 px

**The bar was pre-registered and it fails. It stays failed.** Two of three conditions
still pass and the median is excellent — which is exactly why the outlier condition
was written in the first place: an aggregate hides the case that reaches a screen.
This is the second time on this file that a passing aggregate concealed a
catastrophic individual lock, the first being the 238 px decode bug.

**Why this matters more than a parity nicety:** `tracknet_ball.int8.onnx` is not a
variant, it is **what ships**. `mobile/ball_detector.js`'s own header names it, and
`MOBILE.md` labels fp32 "(reference)" while telling integrators "BUNDLE THIS" for
int8. So the 70.8 px frame and the 8 null mismatches are the shipped path's
behaviour, not a lab curiosity.

### Why the partial run could not have found this

Not a mistake in the earlier work — a sampling limit that was declared at the time.
The partial covered 50 contiguous clip-start frames with only 10 position-comparable;
frame 0147 is outside that span entirely. The earlier verdict's own words were "not
yet a fully powered verdict given the small n ... flagged as needing a full 178-frame
re-run", and that hedge was correct.

### A pipeline trap worth recording

Widening this took three attempts because the probe has **four stages that must run
in order** — Python fp32 inference, Python int8 inference, the **JS decode of each**,
then compare. Running the int8 inference over 178 frames did not widen anything,
because `js_results.json` still held the JS decode of the old 50 and `compare_int8`
silently skips any frame missing `int8_xy`. The comparison kept reporting "50 frames"
while both Python sides had 178. **The count in the output header is the number of
frames that had BOTH decodes, not the number measured** — read it as a diagnostic,
not a label.

### What this does not say

It does not say int8 is unusable — the median is 0.163 px and 170 of 178 frames agree
on fire/no-fire. It says the quantised graph has a failure mode the fp32 reference
does not, that mode is currently unbounded, and nobody has characterised how often it
occurs on other clips. This is one clip (`am_hard_utr`), 178 contiguous frames.
