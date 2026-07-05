# Build Prompts

Paste these into Claude Code one phase at a time, after setup is green. Each
phase is one verifiable milestone with acceptance criteria.

---

## Phase 1 — court calibration + a verifiable court overlay

You're picking up this SwingVision-clone repo. Read CLAUDE.md and README.md
first, then implement Phase 1: court calibration plus a verifiable court overlay.

Scope — do these, nothing else yet:

1. Manual calibration tool. Add backend/calibrate.py: open the first frame of a
   video (cv2), let me click the court landmarks named in court.LANDMARKS, and
   save the clicked pixel points to a JSON file ({landmark: [x_px, y_px]}). Use
   the existing calibration.compute_homography — do NOT reimplement the solve.

2. Auto-calibration stub -> real. Implement calibration.detect_court_keypoints
   so it returns detected landmark pixels for a frame. Start with a classical
   baseline (white-line mask -> Hough lines -> intersections matched to the
   court template) and leave a clearly-marked seam to swap in a learned
   keypoint model later. Fall back to the manual JSON if detection is low-confidence.

3. Overlay renderer. Add backend/overlay.py that, given a video + homography,
   uses calibration.court_to_image to draw the full court line set (from
   court.LANDMARKS / the line geometry) back onto frames and writes an
   annotated preview video or image. This is the visual proof the homography
   is correct.

4. Wire calibration into pipeline.analyze_video (just the calibration step;
   leave pose/ball stubs alone for now).

Constraints:
- Keep the geometry layer (compute_homography, image_to_court, court_to_image)
  exactly as-is. It's tested; don't touch it.
- Don't modify scoring.py, analytics.py, or the match.json schema.
- All new measurements in metres.

Acceptance criteria:
- I can run: python run.py analyze sample.mp4 --keypoints court_pts.json
  and get a calibrated overlay where the drawn court lines sit on the real
  court lines within a few pixels.
- Reprojection error of the named landmarks is printed and under ~5 px.
- Existing tests still pass; add tests/test_calibration.py covering a
  synthetic-camera round trip and reprojection error.

Work in small commits, run pytest after each meaningful change, and tell me
what you changed and why. Ask before adding any new dependency.

---

## Later phases — swap the scope block

- Phase 2 — TrackNet ball tracking into ball.BallDetector.detect + trail on overlay.
- Phase 3 — pose via ultralytics, feed events.detect_hits, replace classify_shot
  heuristic with a learned classifier.
- Phase 4 — connect real ball positions into the already-built analytics.
- Phase 5 — scoring/line-call correction UI in the frontend.
