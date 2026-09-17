---
name: ball-detector-decode-bug-fixed
description: mobile/ball_detector.js's heatmap decode did not mirror ball.py's connected-component algorithm; fixed and verified on real frames + the real ONNX graph
metadata:
  type: project
---

`mobile/ball_detector.js`'s `_decode()` claimed (in its own docstring) to mirror
`backend/swingvision/ball.py`'s `BallDetector._postprocess`, but implemented a
materially different algorithm: global-argmax + a fixed +-3px window, vs
Python's full-image 8-connected-component analysis scored by `area * peak`.

**Why this matters more than a typical off-by-one:** on frames with two
separate heatmap blobs (a real ball plus some other bright response — court
line, kit, sensor noise), Python correctly prefers the larger/more coherent
blob; the old JS always locked onto whichever single pixel was brightest,
occasionally the WRONG blob entirely (up to 238px off, measured). That is a
**confident wrong answer with no refusal signal** — exactly the failure mode
this product is designed to avoid everywhere else (refusal is a designed
surface, see [[project-conventions]] / CLAUDE.md rule 11 territory). Measured
frequency: 4/61 real TrackNet detections in a 178-frame span of a real gold
clip (`am_hard_utr.mp4`) — a genuinely real, if occasional, failure mode.

**Fixed** by porting the exact connected-component + area*peak algorithm into
JS as a plain BFS 8-connected flood-fill (no new dependency, same O(HW) order
as what it replaced). Verified 61/61 exact (0.00px) on real frames through
BOTH decode-only isolation (same heatmap fed to both) AND the real bundled
fp32 ONNX graph (`mobile/models/tracknet_ball.onnx`, run via Python's
`onnxruntime` since no RN runtime is installed offline). Confirmed non-vacuous
via `git stash` (reverting reproduces the exact original 4 mismatches).

**The general lesson, third time now** (after the calibration-key crash and
the doubles-alley bug): every port in `mobile/` checked so far has had a real
bug on first inspection. **Never trust a port's own "mirrors X" docstring
claim — read the actual algorithm on both sides, don't just read the comment.**
See [[doubles-alley-bug-fixed]] for the same lesson applied to `live_calls.js`.

Full writeup: `docs/evidence/ball-detector-parity-tracknet.md`. Harness:
`backend/ball_detector_parity_probe.py` + `mobile/verify_ball_detector.js`,
reusable for future `ball_detector.js` changes (int8 model, native resize
path, or a future onnxruntime-react-native install).

## Technique note: verifying a port when the runtime isn't installed

`ball_detector.js` dynamically imports `onnxruntime-react-native` only INSIDE
`detect()`. Its `_buildInput()`/`_decode()` methods have zero runtime
dependency, so they run under plain Node with nothing installed. To still
exercise the real bundled ONNX graph (not skip it), ran the actual `.onnx`
file through Python's `onnxruntime` (a different engine binding, same graph
file) on the JS-built input tensor — this covers "does the real graph agree,"
leaving only the RN engine-binding identity itself unverified (named
explicitly, not silently assumed). Reusable pattern for any mobile/ port that
dynamically imports a runtime only inside its top-level call.

## Founder ruling confirms mobile's TrackNet bundle is correct, not a defect

`.claude/agent-memory/pm/founder-rulings-2026-08-29.md` records "v1 ships
TrackNet" as a real, dated founder ruling (chain test was SPLIT; TrackNet
preferred for its failure mode + being the only detector with a Core ML path
today). This makes the 2026-08-27 mobile-viability-audit's "mobile bundles a
TrackNet export while the shipped default is BallNet v21" note STALE —
BallNet v21 stays the **desktop** pipeline's default (`run.py analyze`, a
separate product); mobile correctly bundles what v1 actually ships. Closed in
`docs/STATE.md` (struck through with the correction, not deleted). Worth
knowing: `docs/STATE.md`'s ball-detection row describes the DESKTOP default
only — do not read it as describing what mobile should bundle.
