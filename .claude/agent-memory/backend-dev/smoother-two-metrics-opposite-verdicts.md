---
name: smoother-two-metrics-opposite-verdicts
description: smooth_forecast's per-frame ghost/recall behaviour is detector-PAIRING dependent but its speed-coverage cost is NOT — settled 2026-09-02, and the reason is how each metric treats coasted frames
metadata:
  type: project
---

**`smooth_forecast` is judged by two metrics that give OPPOSITE verdicts about
detector-dependence, and both are correct.**

- **Per-frame recall / ghost fires — a PAIRING property.** 7 calibrated gold clips,
  human gold clicks. BallNet v21: mean recall **−1.0 pt**, **+12** ghosts. TrackNet:
  **+3.9 pts**, **+3** ghosts, up on 6 of 7.
  (`docs/evidence/smooth-forecast-adds-ghosts.md`)
- **Speed coverage (`seen_frac` over hit→landing spans) — a STAGE property.** Measured
  2026-09-02 on the matched `detector_ab/` caches, one variable:
  `am_hard_utr` **−10.1** (BallNet) vs **−11.0** (TrackNet); `yt_match40` **−10.2** vs
  **−8.1**. Pre-registered pairing bar (`≤ 0.5×`) FAILED; stage bar (`≥ 0.75×`) PASSED
  on both. Cross-checked on identical shot populations: −10.2 and −8.1.
  (`docs/evidence/speed-coverage-is-chain-shaped-and-the.md`, part 4 of
  `data/output/post_bounce_chain.md`)

**Why:** recall counts an **interpolated** position within 10 px of a human click as a
hit; `seen_frac` excludes coasted frames by construction, because a forecast is a physics
guess and not a measurement. The smoother therefore draws more balls near where the ball
is while *measuring* fewer of them — on `am_hard_utr` its TrackNet recall gain (+3.4 pts
≈ 3 hits) is smaller than the **5** interpolated hits it created. The underlying
deletion rate is detector-independent: the innovation gate removes **14–17%** of
surviving real detections in every arm.

**How to apply:**
- Never generalise a verdict from one of these metrics to the other, in either
  direction. "The pairing finding closes the coverage question" is wrong and was
  explicitly checked.
- A fix that raises recall is not automatically a coverage fix; it may be *purely*
  extra coasting. Score any sixth smoother attempt on **both**.
- The tools: `tools/eval_model_filters.py` (recall/ghosts vs human gold) and
  `tools/eval_speed_coverage_chain.py` (coverage; reads `seen_frac` out of the shipped
  `_build_match_from_events` through its inert `span_sink` kwarg, rather than
  re-deriving span logic — pinned by `backend/tests/test_speed_coverage_span_sink.py`).
- Speed coverage is still the live target STATE records; the −12 pt row did **not** need
  rewriting.

Related: [[chain-gate-mechanism-findings]], [[ball-detector-choice-is-split]],
[[perception-cache-families]].
