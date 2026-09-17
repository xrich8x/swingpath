---
name: player-detection-negatives
description: Far-player detection approaches already measured here — what failed, what is a documentation trap, and what is genuinely still open
metadata:
  type: project
---

The far player is the binding accuracy AND compute problem (see [[coreml-ane-budget]]:
`yolo11m-pose @ 1280` is ~1,000 ms/frame on an A13 ANE estimate — "the whole budget").

## Measured negatives

- **`--pose-quality accurate` for the far player** — MEASURED NEGATIVE, gate pre-registered.
- **Depth-invariant static-player guard (`body_relative`)** — GATE FAILS on 1 of 3
  calibrated clips; the two misses are DETECTION failures (14.5%, 26.7% far-player
  coverage, both under what a path integral needs), not filtering failures. Also: the
  fixture population this guard exists to catch appears in **no gold clip** — unmeasurable.
- **Player-foot gate, twice** (survivor-based vote rule; wrong-court negation criterion) —
  DEAD, converts zero reference clips, then re-measured at n=216 locks/30 clips with the
  sign **backwards** (wrong courts contain feet BETTER than right ones, gap −0.033 to
  −0.071 at every margin ±5/10/20 m). This is a COURT-hypothesis discriminator, not a
  player-identity test, but it is the closest prior exercise of the same primitive.
- **Motion+contrast as a far-player finder** (founder hypothesis, tested 2026-08-29) — the
  underlying motion primitive (`eval/movers.py`, temporal-median clean-plate) was ALREADY
  run at scale (30 clips) for a different purpose (court validation, above) and is DEAD
  there. Its own instrumentation reports a **median of ~9 candidate mover blobs per frame
  (up to 18)** even after size/aspect filtering — named confusers on THIS footage: crowd,
  scoreboard flicker, trees, camera-shake edges. Motion alone does not separate "far
  player" from 8 other things that also moved. **But the specific claim — does a motion
  blob's POSITION identify WHICH blob is the far player, per-frame — was never tested**
  (both prior exercises used aggregate statistics over all foot points, not per-frame
  single-blob identity). A cheap, zero-new-labelling, pre-registered test is specified in
  [docs/evidence/far-player-motion-contrast-hypothesis.md](../../../docs/evidence/far-player-motion-contrast-hypothesis.md).
  **DOCUMENTATION TRAP FOUND HERE:** `eval/movers.py` and `eval/candidate_audit.py`'s
  docstrings both say "UNRUN" — that is STALE, written before the same-day 2026-08-24
  Session O run that DID measure them (`data/output/court_scoring_diagnosis.md`). Do not
  trust a tool docstring's "unrun" claim without checking `docs/STATE.md` and its evidence
  files first — this cost a wrong premise in the brief that spawned this file.

## The far player is a SEARCH problem; the far ball is a DISCRIMINATION problem (2026-08-29)

Tested the founder's "are these the same problem" framing directly. They are not. The
player's fix (crop+upscale) does not transfer to the ball because the ball's own analog
(a whole-frame resolution bump, already tried) already failed at the chain — the entire
recall gain arrived as extra solid ghosts, one of ball-negatives.md's four-for-four closed
items. See [[open-questions]] and
[docs/evidence/far-end-player-and-ball-what-is-left.md](../../../docs/evidence/far-end-player-and-ball-what-is-left.md)
for the ranked list, the closed items, and a pre-registered gate for the next player test:
**re-centre the P0-3 crop on a court-geometry prior instead of the ball position**, to
attack the measured weak link (median 26.3 px from crop edge). Cheap, zero new labels,
existing infrastructure, not a repeat of anything dead.

## What IS established about the far player (not a negative — the state of the problem)

- Full-frame pose @1280 finds the far player at **0 of 25** far-end contacts on
  `yt_match40` (strict, pre-registered test). A 192px crop around the ball, fed at 640,
  finds them at **2/25 strict / 15/25 post-hoc** (label both, always). Causal variable is
  **upscale factor** (~100-140px of player in the tensor is the peak; crop SIZE is not the
  lever). A ball-centred crop holds the far player only barely: **median 26.3 px from the
  crop edge** — the identified weak link any future crop-centring signal should target.
  Far player is ~25-35 px tall in a 1280x720 frame. `docs/evidence/p0-3-crop-around-contact.md`.
- COCO's racket class finds the far player's own racket only at **conf 0.12** (37x56 px) —
  corroborates the far end is a genuine small-object noise-floor regime for ANY
  appearance-based detector, learned or classical. `docs/evidence/racquet-box-negation.md`.
- `yt_match40`'s calibration is confirmed WRONG (T23) — void its homography for anything;
  a homography-FREE test (image-space boxes only) is required to say anything about this
  clip. The P0-3 population and the motion-contrast experiment above are both compliant.

Related: [[court-detection-negatives]], [[coreml-ane-budget]], [[open-questions]]
