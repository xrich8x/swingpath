# backend-dev memory

Seeded 2026-08-28 from the mobile viability audit. Updated 2026-08-28 (overnight P0-3
run) — that session's own findings are marked **[measured 08-28]**.

## Where the authoritative detail lives

- `docs/evidence/mobile-viability-audit.md` — what ports, what is a rebuild, what is
  blocked. Read it before scoping anything.
- `docs/STATE.md` — the only live record of state. "What has not worked" is ~50 measured
  negatives; check it before proposing.
- `docs/evidence/p0-0-coreml-export.md` — why Core ML export needs macOS.
- `docs/evidence/p0-3-crop-around-contact.md` — the P0-3 result and how it was measured.
- `docs/evidence/yt-match40-calibration-is-wrong.md` — the calibration defect that
  invalidated P0-2 on that clip.

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
- **[measured 08-28] The far player needs ~100–140 px in the model INPUT TENSOR, and the
  lever is the UPSCALE FACTOR, not the crop size.** On `yt_match40` the far player is
  ~30–34 px native. Full frame @1280 (1.0×) finds them at **0 of 25** far-end contacts.
  A 192 px crop fed at 640 (3.33× → ~110 px) finds them at **15 of 25**; a 320 px crop at
  1280 (4.0× → ~135 px) at 13 of 25. Below ~90 px nothing; at 6.67× (~203 px) it falls
  back to 6. **Crop size 192 and 320 both work** if the ratio is right — do not
  re-derive this as a crop-size question. PROVISIONAL until a human reads the contact
  sheets (`data/output/p0_3_sheet_yt_match40_crop192at640_x.png`).
- **[measured 08-28] The cheapest good arm is also the best.** `crop192@640` beats
  `crop192@1280` at a quarter the cost. Nothing argues for a bigger input tensor.
- **P0-2 (full-frame pose downscaling) is NOT ESTABLISHED, not a closed negative.** Its
  `yt_match40` column is withdrawn — see the calibration trap below. Surviving evidence
  is `am_hard_utr` 1.0 → 0.0 → 0.0, which never had headroom to measure a 2-pt gate.

## The calibration trap that cost P0-2 — check this FIRST on any clip

**[measured 08-28] `data/yt_match40_pts.json` is miscalibrated and the audit says PASS.**
All four clicked corners lie on run-off asphalt, hedge and fence — no court line.
`tools/validate_new_clip.py --audit` reports 0.9 px residual because a residual only asks
whether four points form a plausible projective image of a court, and four arbitrary
points in a sane trapezoid do. Consequence: the net line lands 35–75 px low, so
`select_players_on_court` calls the NEAR player FAR, and P0-2 published that as an
11.0% far-player rate. Recorded as `T23`; the file is human ground truth and was NOT
edited (rule 9).

**Do this before trusting any calibration:** render the clicked corners on frame 0 at 2×
and look. `data/output/p0_3_calib_corners_yt_match40.png` is the pattern. Also treat an
implausible camera height as a failure — the audit said 11.3 m for a tripod clip.

**Both calibrated gold clips are LOW cameras.** `am_hard_utr` is 1.74 m (known);
`yt_match40` is ~5.4 m behind the baseline and under ~2.2 m high (from the pixels — the
far baseline is occluded by the net tape, which only happens below ~2.2 m). Neither has
a measurable far court. There is no broadcast-mount clip in the calibrated set.

## Things this project's data cannot currently support

- **Far-end contact populations are THIN.** The homography-free criterion (far-end hit =
  local MINIMUM of the ball's raw image y-track) yields 25 usable contacts on
  `yt_match40` and 12 on `am_hard_utr` out of 196 and 120 shots. n=12 is underpowered;
  say so and stop rather than quoting a rate.
- **On a LOW camera the trajectory APEX is also a local image-y minimum**, so the
  criterion admits mid-flight points. It refuses rather than guesses (most shots come
  back `undecided`), but contamination survives and dilutes every arm equally.
- **`am_hard_utr`'s contacts are partly anchored on balls lying on the court** — the
  static-fixture false lock, visible on the contact sheet.
- **`yt_match40`'s shot list is downstream of the bad calibration** (`striker = "A" if
  track[h][2] < NET_Y`, and hit detection runs through `ball_player_gap`), so its hit
  times and player attribution are partly corrupted until it is re-calibrated.

## Architecture rules that are not preferences

- Pin `computeUnits = .cpuAndNeuralEngine`, never `.all` — a layer that silently lands on
  GPU is a background crash on iOS 26.2, not a slowdown.
- Fixed or enumerated input shapes only; flexible shapes push work off the ANE. For the
  crop path this means **one fixed-size crop per contact, batched** — a variable-shape
  graph loses the ANE and the saving with it.
- Sequential `AVAssetReader` decode only. No random seeking. (Desktop probes should use
  sequential `grab()`/`retrieve()` too — `cap.set(POS_FRAMES)` is a seek.)
- Compact binary, resumable storage. Not JSON-per-frame.
- Checkpoint and resume — iOS has no multi-hour background compute at any tier.

## Traps this project has already paid for

- **Unscaled pixel constants.** Anything tuned at 720p silently deletes real balls at
  1080p. Scale by `frame_height/720` — except the fixture radius, where measurement says
  otherwise.
- **Stale caches.** Perception caches are calibration- and settings-dependent. **The
  provenance stamp must read the RESOLVED configuration, not a static preset table.**
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
- **Never quietly edit human ground truth.** Mislabels get recorded, not fixed.
- **Render the frames before believing a count.** The first P0-3 number survived for days
  because nobody did. Render at the arm's own crop scale — a 25 px player inside a 448 px
  tile shrunk to fit is unreadable, which is the same failure in a new costume.
