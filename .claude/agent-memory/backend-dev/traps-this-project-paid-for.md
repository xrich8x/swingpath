---
name: traps-this-project-paid-for
description: Mistakes this project has already paid for — unscaled constants, stale stamps, fps confusion, rates that measure the wrong subject, believing a count without rendering it
metadata:
  type: feedback
---

- **Unscaled pixel constants.** Anything tuned at 720p silently deletes real balls at
  1080p. Scale by `frame_height/720` — except the fixture radius, where measurement says
  otherwise. **The same defect class exists in non-pixel constants:** `audio.py`'s
  `min_contrast = 4.0` multiplies the clip's own global median envelope, so it is a
  level-dependent bar and bites 2–3× harder on quiet reverberant recordings
  ([[audio-lane-screened-not-measured]]).
- **Stale caches and stale stamps.** Perception caches are calibration- and
  settings-dependent. **The provenance stamp must read the RESOLVED configuration, not a
  static preset table** — read defaults back out of the function's own signature.
- **`match["video"]["fps"]` is the EFFECTIVE (processed) rate, not the source rate.**
  `processed_index = round(t_hit_s * fps_eff)` indexes the perception-cache arrays;
  `source_frame = processed_index * frame_step` is the frame to decode. Conflating them
  seeks to half the intended time on a 60 fps clip, and did.
- **A rate is not evidence about the right thing OR the right person** (T19, T23). A
  detection test must be tied to the specific subject, and the same test must run on
  control and treatment or it is not an A/B. A relative-height test alone leaks: a small
  crop TRUNCATES the near player's box so they pass it in the crop arm and fail it in the
  control. Add an explicit "is not the near player" (IoU) term.
- **A refactor must prove it changed nothing** — re-run and diff, or pin with a test.
  When a probe re-implements shipped logic to get extra diagnostics out of one pass,
  verify a random sample against the shipped function and record the match count.
- **Never quietly edit human ground truth.** Mislabels get recorded, not fixed. A stale
  *claim* in a docstring is not ground truth — correct it and say when and why.
- **Render the frames before believing a count.** The first P0-3 number survived for days
  because nobody did. Render at the arm's own crop scale — a 25 px player inside a 448 px
  tile shrunk to fit is unreadable, which is the same failure in a new costume.
- **A repo claim about the DATA can go stale.** Two live files said every clip was pulled
  video-only; 88 of 116 now carry audio. Census the corpus before believing a blocker.

Related: [[calibration-trap-check-corners-first]], [[ios-architecture-rules]].
