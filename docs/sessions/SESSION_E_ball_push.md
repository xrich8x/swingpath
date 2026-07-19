# Session E (multi-session) — The ball frontier: hard-footage detection

**Kickoff prompt:** `Start Session E (docs/sessions/SESSION_E_ball_push.md)`
**User brings:** real footage (more = better) AND ~15 min of blind labeling per
new gold clip (browser tool, same flow as the court labels). Labels are TEST
data — the NEVER-train-on-gold rule is absolute.

## Goal
Close the measured gap: ball detected in only 22-33% of frames on worn outdoor
clay at 720p vs ~74% indoor/broadcast (measured on the random-YouTube e2e
clips, 2026-07-18). This is what unlocks trustworthy speeds (physics arcs
currently rejected on reprojection error) and spin.

## Research snapshot (2025/26 state of the art — re-verify at session start)
- **TrackNet lineage**: V2 = MIMO consecutive-frame heatmaps (our vendored arch
  is this family); **V3** adds trajectory rectification + INPAINTING of missed
  detections; **V4** adds motion-attention from frame differences; **V5**
  (Dec 2025, arXiv 2512.02789) adds residual spatio-temporal refinement +
  motion-direction decoupling. Motion priors (V4/V5) directly target our
  failure mode (small far ball vs textured clay).
- **WASB** (HRNet backbone) is the strong cross-sport baseline — already in our
  stack; on our own probe it beat TrackNet on amateur 720p (that's why the
  probe picks per-clip).
- **BlurBall** (2025, arXiv 2509.18387): jointly estimates ball + motion blur —
  matches our documented finding that blur-aug-alone was a dead end but
  visibility-weighted occlusion training helped; blur as a LABEL not an aug.
- **RacketVision** (Nov 2025, arXiv 2511.17045): new multi-racket-sport
  benchmark with ball annotations — candidate EXTERNAL training data (check
  license) that sidesteps our pseudo-label circularity.

Sources:
- [TrackNetV4: motion attention maps (arXiv)](https://arxiv.org/pdf/2409.14543)
- [TrackNetV5 (arXiv 2512.02789)](https://arxiv.org/pdf/2512.02789)
- [BlurBall: joint ball + blur estimation (arXiv)](https://arxiv.org/html/2509.18387v1)
- [RacketVision benchmark (arXiv)](https://arxiv.org/html/2511.17045v3)
- [Sports ball detection & tracking survey listing (CatalyzeX)](https://www.catalyzex.com/s/Sports%20Ball%20Detection%20And%20Tracking)

## Ground rules learned the hard way (HANDOFF §11-12 — do not relearn)
- Custom BallNet did NOT beat off-the-shelf on unseen footage; prior "wins"
  were data leaks. Measure everything on gold via tools/eval_gold.py only.
- Dead-time negatives were the wrong negatives; v2.1 needs HARD negatives
  (HUD/fixtures/adjacent-court/edges) + a far-court recipe (resolution, real
  far labels), not more epochs.
- The live-ball trajectory filter was the biggest false-fire win — keep it in
  every evaluation loop.

## Session E1 plan (first session of the arc)
1. Gold-label the two analyzed clay clips (select_gold_frames → user labels
   ~300 frames blind, stratified toward far-court/rally time).
2. Score ALL current detectors on the new gold (tracknet / wasb / fusion /
   ballnet_v2 / visweighted) — establishes the honest clay baseline.
3. Failure taxonomy with images: blur? size? contrast vs clay? occlusion? This
   decides E2 (data recipe vs architecture): if misses are motion-smear →
   BlurBall-style blur labels; if size/contrast → input resolution/tiling test
   (720p native vs 1080p source at inference); if background confusion → hard
   negatives. Cheap inference-side experiments FIRST (resolution, WASB
   thresholds, motion-channel input) before any training.
4. Write E2's plan from the taxonomy; update this file's Results.

## Definition of done (per session in the arc)
- New honest numbers on gold, stated with their domain; no training on gold;
  decisions traced to the failure taxonomy, not hunches.

## Results (fill in during the sessions)
- _pending_
