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

## The mechanism, named. Partial — agent killed mid-clip 2026-09-02

frontend-dev root-caused frame 0147 before a session limit ended the run. Recovered
from `.claude/journals/frontend-dev.md`, which is the whole reason it survived.

Inspected the three heatmaps directly with connected components — PyTorch reference,
fp32 ONNX (byte-identical to it), and int8 ONNX:

| | true-ball blob | competing blob | winner |
|---|---|---|---|
| fp32 | area 15 × peak 220 = **3300** | area 13 × peak 242 = 3146 | true ball, by **~5%** |
| int8 | fragmented to area 2 + area 1 → **440** | unchanged, **3146** | **the wrong blob** |

> **Quantisation flips a close two-blob score margin by eroding the true-ball
> component's AREA, not by moving either peak.**

This is not a repeat of the decode bug — both sides run the corrected `area × peak`
connected-component decode. The heatmap was already a near-tie in fp32; quantisation
fragments the winning component's pixel footprint below threshold density and the
runner-up takes it.

**Two consequences worth stating.** The failure is not random: it needs a close
two-blob heatmap, so its rate is the rate of *those*, not of frames in general. And
the fp32 margin being ~5% means fp32 itself was one bad frame from the same error —
the quantisation exposed a fragility that was already there.

**Partial, and where it stopped:** a second cluster was found on `yt_rally2` with the
mirror-image mechanism — int8 *growing the false blob's* area/peak rather than eroding
the true one — and it is a **3-frame cluster, not an isolated frame**. That clip's int8
stage completed (178/178); the decode and compare had not run. `yt_match40` was not
started. The rate across clips is therefore still unknown.

Tooling left behind: the probe now takes `BALL_PARITY_VIDEO` so other gold clips run
without forking it, and `onnx_run_int8()` skips tags whose heat file exists — int8
inference is ~11.7 s/frame on this desktop, so a single agent call cannot cover 178
frames and resumability is what makes the work survive a kill.

## Second clip: the same failure, but a 3-frame CLUSTER. 2026-09-02 (lead)

`yt_rally2`, full 178 frames, same probe, same bar:

| | `am_hard_utr` | `yt_rally2` |
|---|---|---|
| null/non-null agreement | 170/178 (95.5%) PASS | 176/178 (98.9%) PASS |
| median disagreement | 0.163 px PASS | 0.144 px PASS |
| **no frame >10 px** | **70.831 px FAIL** | **75.393 px FAIL** |
| frames where both fire | 53 | 149 |
| shape of the failure | 1 isolated frame | **3 CONSECUTIVE — 0108, 0109, 0110** |

    0109: fp32=[295.46,112.31]  int8=[351.62,162.62]  75.393 px
    0110: fp32=[296.50,112.50]  int8=[353.31,161.46]  74.996 px
    0108: fp32=[295.38,113.38]  int8=[350.50,163.50]  74.493 px

**The cluster is the finding.** A single 70 px frame is a blip a smoother may absorb.
Three consecutive frames, all ~75 px off in the same direction, is a ball that visibly
jumps, sits somewhere wrong, and jumps back — and it is long enough to survive
`smooth_forecast`'s innovation gate rather than be rejected as an outlier. The
mechanism named on `am_hard_utr` frame 0147 (quantisation erodes the winning blob's
area and flips a close two-blob margin) persists across consecutive frames because the
*heatmap* persists across consecutive frames: a near-tie between two blobs does not
resolve itself in 33 ms.

**Two clips, two failures, both on the outlier condition only.** Aggregates stay
excellent — medians 0.144–0.163 px, null agreement 95.5–98.9%. This is the third time
on this file that a passing aggregate has concealed a catastrophic individual lock.

Rate, stated honestly: **1 of 53 both-fire frames on one clip, 3 of 149 on the other**
— roughly 1–2%, on two clips, both of which failed. That is not yet a rate anyone
should quote as *the* rate; `yt_match40`'s int8 pass was 46/178 complete when the agent
was killed.

### A mislabelling I caused and corrected

The summary filename is suffixed from `BALL_PARITY_VIDEO`. I set `BALL_PARITY_DIR` for
the `yt_rally2` run and not the video var, so it wrote `yt_rally2`'s numbers into
`..._summary__am_hard_utr.json`, **overwriting the real one**. Both have been
regenerated with the env correctly set. Recorded because a mislabelled evidence file is
worse than a missing one — it is wrong and it looks right.

---

## Six clips, both named mitigations, and a rate at last. 2026-09-03 (lead + backend-dev + qa)

Picking up the three things the previous section left open: `yt_match40`'s unfinished int8
pass, the absence of a real cross-clip rate, and an untested mitigation against the named
mechanism. **The bar is the one pre-registered 2026-09-02 and is unchanged** — null/non-null
agreement >=90%, median disagreement <=2 px when both fire, no single frame >10 px. The
six-clip set, the rate's definition and both mitigation arms were written into
`.claude/journals/lead.md` **before any of them ran**.

### The six-clip result

Full 178 contiguous frames per clip, same probe, same span (source frames 0-179), int8 and
fp32 both decoded by the real `mobile/ball_detector.js` `_decode()`.

| clip | surface | cond 1 null-agree | cond 2 median | cond 3 max | **>10 px** | null mism. | verdict |
|---|---|---|---|---|---|---|---|
| `am_hard_utr` | Hardcourt | 170/178 (95.5%) | 0.163 px | **70.831 px** | 1/53 | 8 | **FAIL** |
| `yt_rally2` | Shell | 176/178 (98.9%) | 0.144 px | **75.393 px** | 3/149 | 2 | **FAIL** |
| `yt_match40` | Hardcourt | 170/178 (95.5%) | 0.000 px | 1.362 px | 0/93 | 8 | PASS |
| `gold_clay` | Clay | 175/178 (98.3%) | 0.000 px | 0.960 px | 0/77 | 3 | PASS |
| `gold_am` | Hardcourt | 173/178 (97.2%) | 0.137 px | 0.688 px | 0/67 | 5 | PASS |
| `gold_shell` | Shell | 177/178 (99.4%) | 0.000 px | **185.066 px** | 1/89 | 1 | **FAIL** |

**3 of 6 clips fail. Pooled: 5 failing frames / 528 both-fire frames = 0.95%.** Conditions 1
and 2 pass on every clip without exception — six clips on, the outlier condition is still
the only one that ever fires, and it is the only reason anyone knows there is a problem.

`gold_shell` produced the worst disagreement measured anywhere in this work, **185.066 px**,
and did it while posting the *best* null agreement (99.4%) and a **0.000 px median**. That
single clip is the clearest statement of why condition 3 exists.

### The reject, inspected (rule 10)

`gold_shell` tag 0097, blobs dumped from the real heatmaps, guarded (the top-scoring blob's
centroid must equal what the real `_decode()` returned — it does, on every arm):

```
fp32 : true  13 x 220 = 2860   <- wins by 6.9%      | false 11 x 242 = 2662
int8 : false 12 x 242 = 2904   <- wins by 24.2%     | true  10 x 220 = 2200
```

Margin throughout this section is `(winner - runner_up) / winner`. Stating it matters: an
earlier draft of this file, and backend-dev's Arm C write-up, divided by the *runner-up*
instead and so quoted 7.4% where the winner-relative figure is 6.9%. qa caught it. The
five failing frames' fp32 margins, computed the one way: **0147 4.67%, 0108 7.69%,
0109 6.92%, 0110 0.00% (exact tie), 0097 6.92%** — widest **7.69%**.

Same mechanism as `am_hard_utr` 0147, now doing **both halves at once**: quantisation erodes
the true blob (13 -> 10 px) *and* grows the false one (11 -> 12 px). Neither peak moves.
**Area is the lever, on every failure examined.**

Two corrections to the mechanism as previously written here, from the blob dumps:
`yt_rally2` **0108 is erosion, not the "mirror image" growth** — its true blob is deleted
outright while the false blob sits unchanged at fp32's own 12x242=2904; and **0110's fp32
answer is an exact 2640-vs-2640 tie** broken only by raster scan order, which makes 0110 the
weakest of the five failures, not a clean one.

### Both named mitigations: REJECTED

Pre-registered screen for each: the 4 known-failing frames (`am_hard_utr` 0147, `yt_rally2`
0108/0109/0110) must all land within 10 px of fp32. A screen pass buys only the right to a
full run; a screen failure rejects the arm and no full run is paid for. One variable per arm.

**Arm B — `per_channel=True`. REJECTED, and the reason is the finding.** The graph it
produces is **byte-identical to the shipped one** — same sha256, same 10,918,923 bytes.
`quantize_dynamic` forces `QuantizationMode.IntegerOps`, which maps Conv to **`ConvInteger`**,
and ORT's `ConvInteger` operator class **has no per-channel branch at all**; only
`QLinearConv` (static) and `QDQConv` consult `is_per_channel()`. TrackNet is 18 Convs and
nothing else quantisable, so the flag touched zero weights — all 18 `*_weight_scale`
initializers came out scalar with `per_channel=True` set. **Per-channel int8 for this graph
is unreachable through `quantize_dynamic`**; reaching it needs static QDQ plus a calibration
set, which is a second variable and therefore a different experiment.

**Arm C — `nodes_to_exclude=[final Conv]`, keeping the heatmap-writing convolution in fp32.
REJECTED, 3 of 4 screen frames still fail.** Unlike Arm B this is a real change (11.36 MB vs
10.92; 17 `ConvInteger` + exactly 1 fp32 `Conv`). The final Conv was identified by graph
topology, not by name — of 18 Convs exactly one has no Conv downstream
(`node_conv2d_17 -> Relu -> BatchNormalization -> Reshape -> ArgMax`) — and the exporter
aborts rather than guess if that count is ever != 1.

| clip | tag | dist, shipped int8 | dist, Arm C |
|---|---|---|---|
| `am_hard_utr` | 0147 | 70.831 px | **70.989 px** (0.16 px *worse*) |
| `yt_rally2` | 0108 | 74.493 px | **74.493 px** (bit-identical) |
| `yt_rally2` | 0109 | 75.393 px | **75.355 px** |
| `yt_rally2` | 0110 | 74.996 px | 0.000 px |

The one frame it fixes is 0110 — the tie-break frame flagged above as the weakest instance.
Blobs on 0147 show why: the true blob's area went **15 (fp32) -> 2 (shipped) -> 3 (Arm C)**
against a target of 15. **Arm C recovered one pixel of area.**

> **The negative localises the fault: the erosion is already present in the int8 features
> ARRIVING at the final convolution. Output-layer precision is the wrong lever.**

That is worth more than a passing arm would have been — it rules out a whole class of fix
and points at where the next one would have to act. Reported, not gating: Arm C costs
+0.44 MB (+4.1%) and changed the null/non-null answer on none of the four frames.

### What the rate is a rate OF

`0.95% of both-fire frames` is a true number with a misleading denominator. The failure
needs a close two-blob race in the **fp32** heatmap; it cannot occur without one. Counting
fp32 frames whose runner-up blob scores >=85% of the winner (same threshold, same
8-connected components, same `area x peak` scoring as the shipped decode; guarded against
the real `_decode()`'s own answer, **0 guard failures in 528 frames**):

| clip | both-fire | close races | % | failures |
|---|---|---|---|---|
| `am_hard_utr` | 53 | 4 | 7.5% | 1 |
| `yt_rally2` | 149 | 9 | 6.0% | 3 |
| `yt_match40` | 93 | **0** | 0.0% | 0 |
| `gold_clay` | 77 | **0** | 0.0% | 0 |
| `gold_am` | 67 | 1 | 1.5% | 0 |
| `gold_shell` | 89 | 2 | 2.2% | 1 |
| **pooled** | **528** | **16** | **3.0%** | **5** |

**All 5 failures fall inside those 16 frames, and both clips that pass cleanly contain zero
close races.** So the defensible rate is **5 of 16 close races (31%)**, and what varies by
clip is how often the footage produces a close race at all.

**The honest weakness, and qa's correction to it.** The 0.15 threshold was chosen *after*
seeing which frames failed (widest failing fp32 margin **7.69%**, plus headroom), so it is
not independent of the result it explains. qa swept it
([int8-parity-qa-verification.md](int8-parity-qa-verification.md)) and the two halves of
the claim came apart:

| CLOSE | pooled close/both | am_hard_utr | yt_rally2 | gold_am | gold_shell | yt_match40 | gold_clay |
|---|---|---|---|---|---|---|---|
| 0.05 | 7/528 (1.3%) | 2/53 | 3/149 | 1/67 | 1/89 | **0/93** | **0/77** |
| 0.10 | 16/528 (3.0%) | 4/53 | 9/149 | 1/67 | 2/89 | **0/93** | **0/77** |
| 0.15 | 16/528 (3.0%) | 4/53 | 9/149 | 1/67 | 2/89 | **0/93** | **0/77** |
| 0.20 | 17/528 (3.2%) | 4/53 | 10/149 | 1/67 | 2/89 | **0/93** | **0/77** |
| 0.30 | 20/528 (3.8%) | 4/53 | 13/149 | 1/67 | 2/89 | **0/93** | **0/77** |

- **SURVIVES:** *the two cleanly-passing clips contain zero close races* holds at **every**
  threshold from 0.05 to 0.30, not just the chosen one. That is a real signal about the
  footage, not an artefact of where the line was drawn.
- **DOES NOT SURVIVE:** *all five failures are close races* is threshold-dependent — at
  CLOSE=0.05 only **2 of 5** remain (`am_hard_utr` 0147 and the exact-tie `yt_rally2` 0110);
  0108, 0109 and 0097 fall outside. So "31% of close races flip" is **not** a rate to quote:
  it is the ratio at one post-hoc threshold, and the threshold was drawn around the
  numerator. The pooled and per-clip parity numbers in the table above are unaffected —
  they never depended on this — but the *explanation* is weaker than it first looked.

### The derived candidate — NOT measured, NOT shipped

The close race is visible in the fp32 heatmap **at decode time**, before any quantisation
question arises. A decode that refuses when the margin is below threshold would convert a
confident wrong lock into a null, which the smoother already absorbs. The cost is
computable from the table above and is not obviously worth paying: at CLOSE=0.15 it refuses
**16** frames to prevent **5** wrong locks, so **11 of the 16 refusals remove detections int8
currently gets right** — and per the sweep, a threshold tight enough to refuse only 7 frames
catches only 2 of the 5. Rule 5 applies — this is a chain-level claim and gets scored at the
chain or not at all. It is recorded here as the next candidate, not as a result, and any run
of it must pre-register the threshold **before** looking at which frames it catches.

### Reproduce (the 2026-09-03 additions)

```
# one clip, all stages. SET BOTH ENV VARS — setting only BALL_PARITY_DIR once wrote one
# clip's numbers into another clip's summary file and overwrote a real result.
export BALL_PARITY_DIR=<scratch>/ball_parity_<clip>
export BALL_PARITY_VIDEO=<repo>/data/incoming/<Surface>/<clip>.mp4
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py extract
node mobile/verify_ball_detector.js build-decode
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py onnx-run
node mobile/verify_ball_detector.js decode-onnx
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py onnx-run-int8   # ~10 s/frame, resumable
node mobile/verify_ball_detector.js decode-int8      # RE-RUN THIS after widening the int8 pass —
                                                    # compare-int8 silently skips frames whose JS decode is stale
backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py compare-int8

# close-race census across clips (no inference, reads the fp32 heatmaps already dumped)
backend/.venv/Scripts/python.exe backend/ball_parity_margin_census.py     am_hard_utr=<dir> yt_rally2=<dir> ... [--close 0.15]

# the two rejected mitigation graphs
backend/.venv/Scripts/python.exe mobile/export_int8_perchannel.py
backend/.venv/Scripts/python.exe mobile/export_int8_lastconv_fp32.py
```

**Control path re-verified after the harness gained its variant modes:** re-running
`decode-int8` + `compare-int8` on `am_hard_utr` reproduces 2026-09-02's numbers exactly —
170/178, 53 both-fire, median 0.163 px, max 70.831 px — so the `onnx-run-var` / `decode-var`
additions did not disturb the measurement they sit beside.


---

## The third mitigation, measured: THERE IS NO PRECISION BOUNDARY TO INSTALL. 2026-09-04

Founder ruling 2026-09-04 ("yes to all") authorised option 3 of `DECISIONS_PENDING` item 0 —
*a per-layer activation diff to find where the erosion first appears, then a precision
boundary above it.* Run. **The premise is false, and the arm is dead before it is built.**

**Method.** Both graphs expose the **same 36 Relu/BatchNormalization output tensor names** —
verified against the ONNX graphs, not assumed. Each was re-exported with those tensors added
as graph outputs and both were run on the **same real input tensor**. Nothing was trained,
tuned or scored; this is instrumentation of two fixed graphs.

**The control is what makes this a finding.** The diff was run on the failing frame `0147`
(70.8 px) **and on two frames that decode identically in both graphs** (`0012`, `0016`).
Without those, "error peaks at the bottleneck" would have been a fact about int8 in general
masquerading as an explanation of the failure.

| layer | 0147 (FAILS) | 0012 (agrees) | 0016 (agrees) | ratio 0147 / mean(control) |
|---|---|---|---|---|
| 0 `relu` | 0.0239 | 0.0238 | 0.0238 | **1.000** |
| 13 `getitem_18` | 0.2137 | 0.2142 | 0.2078 | **1.013** |
| **19 `getitem_27` (peak)** | **0.2821** | **0.2813** | **0.2612** | **1.040** |
| 27 `getitem_39` | 0.1688 | 0.1726 | 0.1924 | 0.925 |
| 35 `getitem_51` (output) | 0.0705 | 0.0811 | 0.1386 | **0.642** |

Relative L2 error rises monotonically through the encoder, peaks at the **512-channel
bottleneck (layer 19)** and then *falls* through the decoder — and it does so **identically on
all three frames**. Peak magnitudes: 0.282 / 0.281 / 0.261. The failing frame is within **4%**
of the controls across the entire encoder and is **35% QUIETER than a control** at the output.

> **Quantisation error is not elevated on the failing frame at any layer.** There is no point
> where its erosion "first appears", because it has no anomalous erosion. It carries the same,
> frame-typical quantisation noise as frames that decode perfectly.

### What actually breaks, restated

The frame fails because the **fp32 decision was already a near-tie** — the two-blob
`area x peak` margin was ~5% (3300 vs 3146). Ordinary, unremarkable quantisation noise is
enough to flip an already-marginal decision. This corroborates, from the activations, what the
blob analysis said from the output: *the quantisation exposed a fragility that was already
there.*

**Consequence — the whole framing of item 0 changes.** A precision boundary installed anywhere
would be raising precision against a noise level that is **identical on frames that decode
correctly**, so it cannot separate the failing case. That is why Arm C recovered 1 px of area
out of 13: not because the boundary was in the wrong place, but because there is no place.

**int8 is not the disease.** The exposure is the fp32 model's own top-2 decision margin. Two
things follow, and neither is a quantisation flag:

1. **A refusal signal on a close top-2 blob margin** — cheap, chain-side, and it would protect
   the **fp32** path too, which the ~5% margin shows is one bad frame from the same error. The
   current failure mode's defining property is that it is a confident wrong lock with *no
   refusal signal*; this attacks exactly that.
2. **A better-separated detector** — the standing answer, and rule 6 closes detector work.

**Option 3 is measured out. Do not fund a fourth precision-boundary arm**; three arms
(`per_channel`, final-conv-fp32, per-layer boundary) have now failed, the third by refuting
the premise the other two shared.
