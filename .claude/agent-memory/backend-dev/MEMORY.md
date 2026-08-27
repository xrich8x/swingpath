# backend-dev memory

Seeded 2026-08-28 from the mobile viability audit and the measurements taken up to that
date. Nothing here was produced by this agent — it is inherited context so you do not
re-derive it.

## Where the authoritative detail lives

- `docs/evidence/mobile-viability-audit.md` — what ports, what is a rebuild, what is
  blocked. Read it before scoping anything.
- `docs/STATE.md` — the only live record of state. "What has not worked" is ~50 measured
  negatives; check it before proposing.
- `docs/evidence/p0-0-coreml-export.md` — why Core ML export needs macOS.

## The split, settled

**Ports as-is:** `live.py` (streaming, causal, no cv2/torch — already mirrored to JS and
verified bit-identical), `court.py`, `schema.py`, `analytics.py`, `scoring.py`,
`corrections.py`, and every closed-form geometry routine.

**Rebuild, not port:** the offline analyzer. The smoother is non-causal by construction
(constant-acceleration Kalman + RTS forward-backward, plus Savitzky-Golay) and the
pipeline runs whole-video multi-pass with full per-frame arrays materialised before
events/speed/score run.

**Blocked on-device:** numpy, scipy, torch, ultralytics; and `annotate.py`, `audio.py`,
`highlights.py`, which shell out to a bundled desktop ffmpeg binary.

**Better than feared:** no Windows-specific code in the shipped core, no `highgui` in the
pipeline, and every cv2 symbol used exists in OpenCV's iOS build. cv2 is imported lazily
at ~50 call sites, so the pure-logic modules import with no OpenCV present at all.

## Measured, and binding on design

- **The ANE inverts the desktop cost ordering.** On desktop CPU pose (~0.4 s/frame) was
  cheaper than ball (~0.7 s/frame). On an A13 Neural Engine, `yolo11m-pose@1280` is
  roughly 25× the ball model, because ANE cost tracks FLOPs. Estimated, not measured on a
  phone — no phone benchmark exists in this repo.
- **int8 buys no compute speedup on an A13.** int8×int8 ANE compute begins at A17 Pro;
  earlier silicon stores int8 weights and dequantises to fp16. It buys download size and
  memory bandwidth. Plan on fp16.
- **Pose downscaling FAILED its pre-registered gate, measured 2026-08-27.** Far-player
  detection on `yt_match40`: **11.0% @1280 → 0.1% @640 → 0.0% @384**, while the near
  player barely moves (80.3% → 78.1% → 72.5%). On `am_hard_utr`: 1.0% → 0.0% → 0.0%. The
  gate allowed a 2-point absolute drop. Do not revisit full-frame downscaling as the way
  to afford pose; run pose on fewer FRAMES instead.
- **The crop-around-contact probe is UNMEASURED, not negative.** A first attempt reported
  78.8% but was invalidated on inspection: a 448 px box on a 1280×720 frame is wide enough
  to catch the near player regardless, and the contact population was wrong (the camera
  sits behind the near baseline, so near-player hits project past the net into far-court
  coordinates). Any retry needs a correct population and a detection test tied to the
  specific person. `tools/probe_crop_pose.py` and `tools/render_crop_probe.py` exist.

## Architecture rules that are not preferences

- Pin `computeUnits = .cpuAndNeuralEngine`, never `.all` — a layer that silently lands on
  GPU is a background crash on iOS 26.2, not a slowdown.
- Fixed or enumerated input shapes only; flexible shapes push work off the ANE.
- Sequential `AVAssetReader` decode only. No random seeking.
- Compact binary, resumable storage. Not JSON-per-frame.
- Checkpoint and resume — iOS has no multi-hour background compute at any tier.

## Traps this project has already paid for

- **Unscaled pixel constants.** Anything tuned at 720p silently deletes real balls at
  1080p. Scale by `frame_height/720` — except the fixture radius, where measurement says
  otherwise.
- **Stale caches.** Perception caches are calibration- and settings-dependent; a whole set
  of published figures was withdrawn over this. **And the provenance stamp must read the
  RESOLVED configuration, not a static preset table** — a bug of exactly that shape was
  found and fixed on 2026-08-27, where a 640-resolution run would have stamped itself
  `@1280`.
- **A refactor must prove it changed nothing** — re-run and diff, or pin with a test.
- **Never quietly edit human ground truth.** Mislabels get recorded, not fixed.
