---
name: synth-truth-as-a-paired-error-rig
description: How to get a per-shot ABSOLUTE speed error paired with any pipeline quantity — synth_truth is the only compliant route, and the recipe that makes it faithful
metadata:
  type: project
---

**Real clips cannot give a per-shot absolute speed error.** Human clicks label ball
*position*, not speed, and the HUD is agreement with another estimator, barred as an
accuracy reference. `tools/synth_truth.py` is the only compliant absolute speed truth.

**Why:** any question of the form "does gate X predict speed error?" needs truth paired
per shot, and this is the only rig that produces it.

**How to apply — the recipe that makes it faithful** (built and run 2026-09-03; the
harness itself lives only in scratchpad, so this is the reproduction note):

- Import `synth_truth.simulate` / `truth_of`; do NOT use `synth_truth.measure()` for a
  pipeline-fidelity question. `measure()` simply DELETES dropped samples, whereas the
  shipped pipeline REPLACES them with smoother forecasts and integrates over the filled
  track. Mirror the shipped chain instead: `ball.smooth_forecast(res_scale=h/720)` then
  `calibration.image_to_court` + the +/-4 m runoff-box test then `ball.cap_court_jumps`
  then `ball.smooth_and_fill(window=7, polyorder=2)` then `analytics.shot_speed_kmh`.
- **Compare against `avg_ground_kmh`**, not `launch_kmh`. Launch carries the shared -21.7%
  drag bias into every shot and compresses any between-group ratio toward 1.
- **Apply the pipeline's own shot filters** (`5 < speed < 250`, and `speed <= 160` when the
  question involves `speed_confident`). Omitting them admits flights the pipeline would
  never emit as shots and can flip a verdict — it did, 2026-09-03.
- Per-clip `hfov` from `tools/height_curve.py::hfov_of`, never the 93.46 default: speed
  scales with it. `smooth_and_fill` is in `swingvision.ball`, not `pipeline`.
- "Clip" here means a CALIBRATION. Same seed across clips gives the same launches through
  different cameras, i.e. paired arms. Excluded by standing rules: `yt_match40` (T23) and
  `demo30` (speeds never citable) — see [[calibration-trap-check-corners-first]].
- ~1200 flights per clip runs in well under a minute and fills 0.15-wide bands with
  n > 100. Cheap. There is no excuse for an underpowered version of this experiment.

Result of the first use: [[speed-error-is-geometry-not-detection]].
