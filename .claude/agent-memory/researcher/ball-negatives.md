---
name: ball-negatives
description: Ball detector/chain approaches already measured here — detector work is CLOSED, chain work is open, and four detector gains delivered nothing downstream
metadata:
  type: project
---

Backfilled 2026-08-27 from `docs/STATE.md` and the archived sessions.

**Rule 5 of the project: score ball work at the CHAIN, not the detector.** Four detector
gains — input resolution, `score_thresh`, localised confuser weighting, +57% data — each
cut detector error substantially and delivered **nothing** to the rendered output. Four
for four. Justify the next ball idea by a chain-level mechanism or do not run it.
**Ball-DETECTOR work is closed** by the Session L stopping rule; **chain work is open**
and as of 2026-08-27 explicitly not closed — the stopping rule did not fire.

**Measured negatives worth not re-deriving:** motion attention (**59.2%** of false locks
travel with a person, only 38.0% are static scenery — motion attention addresses the wrong
population); racquet-box negation (failed twice — COCO finds the *near* player's racquet
while the detector fires on the *far* player's); pose-proximity mining (11.4% catch at the
5% collateral ceiling — a skeleton has no racquet, 2.12 body heights away); detector fusion
(rescued **4 frames**, doubled the cost); whole-frame hard negatives; mining
`suppress_false_locks`' rejections; depth-aware Kalman process noise (made false-fire
*worse*, 19 -> 27%); raising `acquire_bound_m`; blur augmentation alone.

**What worked:** hard-negative mining + retrain (false-fire 14% -> 6.0% at flat recall);
occlusion augmentation + visibility-weighted loss (gold 82.9 -> 84.9, occluded 84.2 ->
89.7); `suppress_false_locks`; the static-lock gate; scaling every pixel threshold by
`frame_height/720`.

**Live and unresolved as of 2026-08-27:** `bounce_hypothesis` v2. v1's separation ratio
was published as 4.50:1, **withdrawn** on 2026-08-27 as a two-event denominator; at full
power over all 10 gold clips it is **9.00:1** against a >7 bar, which passes. So the
premise that the exchange rate is a property of the signal is disproved. v1 still fails on
position accuracy on one clip. **Do not cite 4.50:1.**

**Mobile note (2026-08-27):** BallNet is 1.3M params, a 9-channel U-Net at 512x288, so
~8-12 GFLOPs — genuinely cheap on the ANE. But `mobile/models/*.onnx` are exported from
the vendored **TrackNet** (360x640, 256-channel output), which is much heavier. The
already-logged model divergence now has a compute consequence: the exported model is the
expensive one. See [[coreml-ane-budget]].

**Far-end framing test (2026-08-29):** the ball's far-end problem is NOT the same as the
far player's. The player is search-limited (full-frame model literally never fires); the
ball already fires on 73-76% of far-court frames — its problem is that the chain cannot
DISCRIMINATE the survivors from confusers carrying the same kinematic signature (all 19
chain false locks have `run_len = 1`, a real ball's own signature — see
[[9-solid-ghost-balls]] via `docs/evidence/9-solid-ghost-balls.md`). The one thing that
did move solid ghosts was a MODEL SWAP (TrackNet vs BallNet, -29.5%), not a sharper look —
which is why "more resolution, applied locally instead of globally" (sketched, NOT run,
NOT gated, confidence ~25-30%) is the only ball-side idea left that isn't already closed.
Full ranking, literature check (SAHI/TOTNet/Kalman-tiny-object survey, all footage-flagged)
and the caveats in
[docs/evidence/far-end-player-and-ball-what-is-left.md](../../../docs/evidence/far-end-player-and-ball-what-is-left.md).

Related: [[open-questions]], [[project-method-rules]]
