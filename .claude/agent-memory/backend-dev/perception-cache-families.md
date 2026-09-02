---
name: perception-cache-families
description: data/output/ holds three incompatible perception-cache families — pick the wrong one and an A/B silently has two variables
metadata:
  type: project
---

`data/output/*.perception.json` is **not one population**. Three families, and mixing
them across the arms of an A/B adds a second variable without any error.

1. **Main clip caches** (`am_hard_utr.perception.json`, `yt_match40.perception.json`) —
   full schema: `ball_px` + `near_kpts`/`far_kpts`/`near_court`/`far_court`/`cam_motion`,
   modern provenance including `camera_hfov_deg`. Built with the tracker's
   **`court_gate` ON**. BallNet only.
2. **`data/output/detector_ab/*.{ballnet21,tracknet}.perception.json`** — `ball_px`
   only, **`court_gate` OFF**, both detectors built the same day with matched
   `score_thresh` and static gate. **This is the only one-variable detector pair.**
3. **`gold_*.perception.json`** — old `build_gold_caches.py` schema whose provenance has
   **no `camera_hfov_deg` key**, which silently drops `ball.play_volume_polygon` onto its
   much tighter fallback rung. See [[traps-this-project-paid-for]].

**Why:** the published per-stage speed-coverage table was measured on family 1; the
detector A/B has to run on family 2, so the BallNet arm must be **re-measured** rather
than quoted from the doc. Family 1's numbers differ from family 2's BallNet numbers by
~2 pts purely because of `court_gate`.

**How to apply:**
- Pose, camera motion and player court tracks are **detector-independent**, so it is
  legitimate (and necessary) to take them from family 1 while taking `ball_px` from
  family 2. `tools/eval_speed_coverage_chain.py` does exactly this via `--pose-cache`.
- Always print/stamp the RESOLVED provenance of every cache an arm consumed, and check
  `frame_step` and frame count match before pairing two caches.
- Never quote a published number as one arm of a new A/B. Re-run both arms on matched
  inputs; use the published number only to validate the tool.

Related: [[traps-this-project-paid-for]], [[ball-detector-choice-is-split]],
[[smoother-two-metrics-opposite-verdicts]].
