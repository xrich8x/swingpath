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

## Results (2026-07-19)

**Step 1 — k1 estimator: DONE, with a method correction.** The textbook
circle-fit route (F = 1/k1 from an algebraic fit) collapses on shallow arcs
(Kasa small-arc bias: a true −0.18 read as −0.53). Shipped instead: per-chain
k1 by minimizing the STRAIGHTNESS residual of the undistorted chain
(model-consistent chain growth; a straight chain actively votes 0). Accuracy on
synthetic known-k1 renders: within ~0.012 absolute over k1 ∈ [−0.25, +0.08],
~0.05 s/frame. `calibration.estimate_k1 / undistort_points / distort_points`,
14 tests in `tests/test_lens.py`.

**Step 2 — threaded through calibrate_video, and the premise was WRONG on the
target clip.** Three independent measurements agree that e2e_l6o8FOoy3MY has
**no radial distortion** (in-camera rectified): the real paint is straight to
±1 px over a 967 px span; no k1 in [−0.10, +0.13] reduces the lock residual
(minimum at 0); per-frame plumb-line reads scatter +0.04..+0.18 (a real lens is
frame-constant). The pipeline's cross-frame HONESTY GATE
(`estimate_k1_frames`) therefore refuses k1 on this clip — correctly.

The ACTUAL cause of the near-left sideline offset: the physical camera fit's
**roll = 0 assumption**. The mount is tilted −1.1°, which roll-free could only
express as an 8–16 px displaced court. Fix: bounded roll DOF (±3°) on the
TRUSTED path only (`shape_lock` / calibrate); the auto-detect candidate path
keeps roll frozen — measured on gold, roll there let a 68 px wrong court gain
2 consensus votes past the auto-accept bar (am_indoor_hard2 4→6), so it was
restricted and the law re-verified.

GATES: gold consensus scorecard **17/20 locked, median 12.0 px** (baseline
17/20 ~12 px; every ≥6-vote court correct, wrong courts ≤5 votes). e2e frame-60
near-left crop `[330:640,120:640]`: sideline residual **7.99 → 3.41 px**,
near-baseline **8.41 → 1.08 px** (local: data/output/e2e_l6o8FOoy3MY
.sideline_{before,after}.png); reprojection 8.20 → 2.60 px; lock displacement
15.8 → 10.0 px. `lens_k1` stored in match.calibration.

**Step 3 — lens-corrected projection path: DONE.** With a measured lens, ball
pixels are undistorted after camera-motion unwarp and projected with the
pinhole H_und; player positions re-derived from cached ankle keypoints; the
physics camera gets undistorted corners+pixels; the shot-type contact point is
bent back before comparing against real striker keypoints. Points only, no
frame resampling. GATES: tennis_sample (telephoto, k1≈0) analyze output is
byte-identical before/after the change (same cache+flags, empty diff);
`test_metric_projection_through_the_lens` shows the pinhole path exact
(<1e-6 m) where the distorted-corner path errs >0.05 m; e2e re-checked under
the corrected court (positions on-court, no artifacts; one borderline
6.7 km/h shot fell below the stroke gates).

**Step 4 — watchdog on a moving camera: PROVED (clip rebuilt after review).**
Synthetic bump via `tools/make_bump_clip.py`. The full analyze printed
`camera change detected ~frame 480 -> court RE-ACQUIRED (motion track rebased)`
and recorded `{"frame": 480, "kind": "reacquired"}` in match.calibration.events.

FIRST ATTEMPT WAS FLAWED (caught by the user): the original `--shift 40`
cropped BOTH axes, which pushed the near-right corner (x≈612 of 640) out of
the pre-bump frame. With a corner missing, multi-frame consensus couldn't lock
(2/8 votes), so the seed fell back to a single-frame `auto_fit_frame` — a
wrong-rung distorted quad, **62 px** off the human gold labels. That is the
"insanely abnormal shape" that showed in the first evidence render. The
line-detection code was never the problem; it was fed a mutilated framing.

FIX: the tool now PADS (black-fills the vacated edge) instead of cropping, so
the framing is never altered — nothing leaves the frame. Rebuilt clip
`bump_ntrp30b.mp4` (640×338, +40 px vertical shift at frame 450). Measured on
the corrected clip:
- pre-bump consensus calibration **8/8 votes**; seed vs human gold labels
  (source frame 817) **6.1 px** (was 62.1 px);
- watchdog signal: coverage 0.87 baseline → 0.21 the frame the bump lands
  (0.21 < the 0.45× trigger), fires cleanly;
- tracked court coverage 0.87 pre-bump → **0.91** post-bump (re-acquired);
  both overlays land on the paint (data/output/bump30b_{pre,post}_tracked_*.png).
- BONUS: this footage has a genuine mild lens distortion — the honesty gate
  ACCEPTED k1 = +0.061 (consistent across frames; the untouched source reads
  +0.060 independently), so it's also the first REAL clip exercising the
  Step-3 lens-correction path.
Evidence: data/output/bump_ntrp30b.match{.json,.perception.json}. Only one gold
frame exists in this segment, so the post-bump court is validated by coverage
(0.91), not a second gold score.

**Definition of done: all four boxes ticked.** 93 backend tests pass. The one
scope adjustment vs the brief: the e2e residual reduction came from the
measured cause (camera roll) rather than the hypothesized one (lens k1) — the
k1 machinery shipped anyway, honest-gated, awaiting genuinely uncorrected
wide-lens footage.

