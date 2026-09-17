---
name: audio-bounce-timing-accepted-with-slate
description: Audio gives bounce-timing truth to ~±0.15 frames vs a ±1 frame bar, but ONLY with range correction and a 10-clap slate; uncorrected it is a range-dependent +1.2 to +5.3 frame late bias
metadata:
  type: project
---

# Audio bounce timing: ACCEPTED, conditionally. The arithmetic, so it is never re-derived.

Ruled 2026-09-15 by pm in `docs/CAPTURE_PROTOCOL.md` §6. Rule 12 permits it — the sound of
the ball hitting the court is the GAME, not an overlay — and it is independent of the visual
track, which is what makes it useful for SPEC §4's ±1 frame bar.

**Why the naive version is worse than useless.** Sound covers 343 m/s. From a camera 6 m
behind the near baseline at 3 m height, slant distance to a bounce runs 6.7 m (near baseline)
to 30.2 m (far baseline): delay **+1.17 to +5.28 frames at 60 fps**, spread 4.1 frames across
the court. It is **RANGE-DEPENDENT**, which is exactly the signature an estimator bias would
have — and P1's bar B already measured the fitted arc crossing the ground **+3.66 frames
late**, squarely inside that band. Anyone timing truth by an uncorrected audio transient will
manufacture that bias and then explain it as physics.

**How to apply — two mandatory corrections:**
1. **Range correction.** `t_contact = t_audio − d/c`, `c = 331.3 + 0.606·T`. Needs the bounce's
   true position, which a tape-measured truth set supplies to ≤3 cm → ±0.005 frames. ±2 °C
   on temperature → ±0.02 frames. Transient onset → ±0.12 frames.
2. **A 10-CLAP SLATE, 1.0 m in front of the lens, at the start of every take.** A/V sync
   inside the phone container is the only real unknown. One clap locates to ±0.5 frame
   (a constant per-take bias at half the bar); ten claps average to ±0.5/√12/√10 ≈ **±0.05
   frames** because the clap's phase against the frame clock is random. Clap at 1.0 m so its
   own 2.9 ms propagation is known and subtracted.

**Total residual ≈ ±0.15 frames against a ±1 frame bar — 6x margin.**

**Three things that must be declared, not absorbed:**
- Audio marks FIRST CONTACT; the vertical-velocity sign reversal is mid-compression, ~3-5 ms
  (+0.2 to +0.3 frames) later. Declare it in the label.
- Audibility at 30 m is not guaranteed (wind, traffic, indoor echo). Field-test in the first
  five minutes; if the far baseline is inaudible, the audio arm is near-half only.
- A ball machine's firing thump is also a transient (~1 s before its bounce, so separable).

**Related:** [[truth-is-built-at-capture-not-labelled]].
