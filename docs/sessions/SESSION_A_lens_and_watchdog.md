# Session A — Finish the camera story: lens undistortion + watchdog validation

**Kickoff prompt:** `Do Session A (docs/sessions/SESSION_A_lens_and_watchdog.md)`
**User brings:** nothing required. A real phone clip (any) is a bonus; a clip where
the phone gets bumped mid-recording upgrades step 4 from synthetic to real.

## Goal
Remove the last systematic court error on wide lenses (lines bend near frame
edges — seen as the near-left sideline offset on e2e_l6o8FOoy3MY, 81° hfov), and
prove the camera-change watchdog on a moving-camera clip (it has only been
validated on synthetic unit tests + a no-false-alarm static run).

## Researched approach (do NOT improvise past this without re-researching)
Lens distortion from the court's own lines — the **plumb-line method** with
**Fitzgibbon's division model** (1 parameter, k1):
- Straight world lines image as straight lines ONLY in a pinhole camera; under
  radial distortion they become curves. Under the division model those curves
  are **circular arcs**, so k1 estimation reduces to **circle fitting** on
  detected long lines — single image, no calibration pattern needed.
- We already detect the court's long lines (courtfit `_detect_lines` / Hough).
  Baselines + sidelines are the plumb lines. Fit arcs to the longest detected
  line pixel-chains; the shared k1 that straightens them is the lens.
- Undistort points (division model is closed-form to invert for points) BEFORE
  homography fitting; optionally `cv2.undistort` frames for perception, but
  point-level undistortion of corners/ball/pose is cheaper and sufficient.
- Distortion centre: assume image centre (standard for this method's 1-param use).

Sources:
- [Automatic Radial Distortion Estimation from a Single Image (Bukhari & Dailey, JMIV 2012)](https://link.springer.com/article/10.1007/s10851-012-0342-2)
- [Robust Line-Based Radial Distortion Estimation From a Single Image (IEEE)](https://ieeexplore.ieee.org/document/8932365)
- [Single Image Automatic Radial Distortion Compensation (arXiv 2112.08198)](https://arxiv.org/pdf/2112.08198)
- [Robust Radial Distortion from a Single Image (Springer)](https://link.springer.com/chapter/10.1007/978-3-642-17274-8_2)

## Plan (measure after EVERY step — user's standing rule)
1. `calibration.estimate_k1(frame)` — arc-fit the longest ridge-line chains,
   robust (median k1 over lines; reject arcs shorter than ~25% frame width).
   Unit test on synthetic distorted court renders (known k1 in → k1 out).
2. Thread k1 through `calibrate_video`: undistort the named corners + detected
   lines before fit; store k1 in `match.calibration`.
   GATE: gold consensus scorecard must not regress (17/20 locked, ~12px median);
   e2e_l6o8FOoy3MY near-left sideline residual must measurably shrink
   (zoom-crop comparison, same frame 60 crop [330:640,120:640] as before).
3. Undistort ball/pose pixels in the projection path (points only, not frames).
   GATE: tennis_sample e2e unchanged (telephoto ≈ zero distortion, k1≈0 —
   a good null test); e2e clip speeds/positions re-checked.
4. Watchdog on a moving camera: synthesize a bump (crop-shift an existing clip's
   frames +40px after the midpoint via cv2, re-encode with VideoWriter) →
   run analyze → expect "camera change detected → RE-ACQUIRED" + a sane
   post-bump overlay. If the user recorded a real bump clip, use that instead.
5. Commit per step; push; update memory + this file's Results section.

## Definition of done
- k1 estimator unit-tested (synthetic known-k1 round trip)
- Wide-lens clip edge error visibly + numerically reduced; scorecard not regressed
- Watchdog detects + re-acquires on a (synthetic or real) camera change
- All tests pass; pushed to the PR/master

## Guardrails (standing)
- Never emit a non-court shape; measure after each step; cold tests only on
  never-used clips; 720p for new footage; don't train on gold labels.

## Results (fill in during the session)
- _pending_
