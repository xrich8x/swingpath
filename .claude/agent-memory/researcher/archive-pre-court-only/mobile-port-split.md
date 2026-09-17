---
name: mobile-port-split
description: What of the shipped Python stack ports to iOS as-is, what needs a rebuild, and what is blocked entirely — from the 2026-08-27 static audit
metadata:
  type: project
---

Condensed from `docs/evidence/mobile-viability-audit.md` (static read, 2026-08-27 — no
code run, no phone involved). **The port is split, not uniform.**

**Portable as-is**
- `live.py` (187 lines) — genuinely streaming and causal, one frame in / a call out, no
  cv2 and no torch. Already ported to `mobile/live_calls.js`, verified bit-identical.
- `court.py` (109 lines) — constants and geometry, mirrored to `frontend/src/lib/court.js`,
  parity-enforced by `tests/test_js_mirror_parity.py`.
- `schema.py`, `analytics.py`, `scoring.py`, `corrections.py` — pure logic, no heavy deps.
- Every closed-form geometry routine.
- `mobile/` — ONNX fp32 + int8 (11 MB), argmax baked into the graph (0.9 MB/frame output
  vs 236 MB raw), int8 within 0.32 px of PyTorch. **But these are TrackNet exports while
  the shipped default is BallNet v21** — a logged divergence, and the exported one is also
  the FLOP-heavier one ([[coreml-ane-budget]]).

**Needs a rebuild, not a port**
- The offline analyzer: `pipeline.py` (2,131) + `events.py` (645) + `speedspin.py` (256).
- Whole-video multi-pass — `_perceive` materialises full per-frame arrays before events,
  speed and score run.
- Court auto-detection — `courtfit.py` + `calibration.py` ~2,900 lines of hand-written
  classical CV with **no conversion toolchain**; becomes a shared C++ core over OpenCV's
  mobile builds. A v1 can skip it: manual 4-corner tap is already pure JS.
- **The smoother is non-causal by construction** (constant-acceleration Kalman + RTS
  forward-backward at `ball.py:647`, plus Savitzky-Golay). *Corrected the same day: this
  binds only the real-time line-call path. On a record-then-process job the whole track is
  in hand and it works as-is. Do not propose a buffered-replay workaround for the offline
  path — that constraint is not active there.*

**Blocked entirely on-device**
- `numpy` / `scipy` — reimplementation, not port.
- `torch` / `torchvision` — export path only.
- `ultralytics` YOLO-pose — `yolo11m@1280` / `yolo11x@1920`.
- `imageio-ffmpeg` + `subprocess` — bundled desktop binary, used by `annotate.py`,
  `audio.py`, `highlights.py`. Replace with `AVAssetReader` / `AVAssetWriter`.

**Better than feared, recorded as negatives:** no Windows-specific code in the shipped
core; no `highgui` in the pipeline (only `backend/calibrate.py`, a dev tool); every cv2
symbol used is core OpenCV and exists in the mobile builds; cv2 is imported lazily at ~50
call sites, so the pure-logic modules import with no OpenCV present.

Related: [[coreml-ane-budget]], [[ios-background-compute]]
