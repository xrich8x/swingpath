---
name: mobile-port-split
description: Settled split of the Python backend for iOS — what ports as-is, what is a rebuild, what is blocked on-device
metadata:
  type: project
---

The audit settled this; do not re-derive it.

**Ports as-is:** `live.py` (streaming, causal, no cv2/torch — already mirrored to JS and
verified bit-identical), `court.py`, `schema.py`, `analytics.py`, `scoring.py`,
`corrections.py`, and every closed-form geometry routine.

**Rebuild, not port:** the offline analyzer. The smoother is non-causal by construction
(constant-acceleration Kalman + RTS forward-backward, plus Savitzky-Golay) and the
pipeline runs whole-video multi-pass with full per-frame arrays materialised before
events/speed/score run.

**Blocked on-device:** numpy, scipy, torch, ultralytics; and `annotate.py`, `audio.py`,
`highlights.py`, which shell out to a bundled desktop ffmpeg binary. `audio.py`'s three
concrete port items are now scoped and measured — see
[[audio-lane-screened-not-measured]].

**Better than feared:** no Windows-specific code in the shipped core, no `highgui` in the
pipeline, and every cv2 symbol used exists in OpenCV's iOS build. cv2 is imported lazily
at ~50 call sites, so the pure-logic modules import with no OpenCV present at all.

**Why:** the iOS-only pivot (2026-08-27) means nothing may leave the phone, so every
module had to be classified before work could be scoped.

**How to apply:** when asked to "port" something, check this list first. A rebuild
costs a redesign of the algorithm's causality, not a translation.

Related: [[ios-architecture-rules]], [[where-authoritative-detail-lives]].
