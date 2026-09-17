---
name: score-layer-reopened-no-ground-truth
description: The rally/score layer was reopened 2026-08-27, superseding the 2026-08-20 closure — but it still has no ground truth and the easy source is still barred
metadata:
  type: project
---

**The 2026-08-20 out-of-scope ruling on the rally / score layer was SUPERSEDED on
2026-08-27.** User: *"I think follow what I said now."* CLAUDE.md rule 12 rewritten to
record the supersession. In scope again: **match scoring (sets, games)**, **point-by-point
clip segmentation with automatic dead-time trimming**, and **shot-filtered playlists**.

**Reopening scope created a requirement, not a measurement.** Carry all of this forward:

- **That layer still has NO ground truth of any kind**, and **rule 11 still bars the easy
  source**. A burned-in scoreboard remains barred — built once, rejected on its premise,
  reverted (`afffb5a`), and two published over-split figures (**1.47x, 1.6x**) were
  withdrawn because they came from it.
- **A compliant ground-truth source is a prerequisite line item.** Compliant options:
  human-labelled point boundaries, or boundaries derived from what is already measured
  (bounces, ball-in-play state, physics). Cost it explicitly *including human labelling
  hours*, the way the far-court queue was costed at 4,087 frames / 4-5 hours.
- **`stats.score_validation_note` STAYS** until a measured number replaces it. Its removal
  is not part of shipping a scoreline.
- **Do not size the scoring problem before establishing what the correct answer is.** The
  last attempt to size this layer without ground truth produced **trap T20** — a defect
  sized from an assumption about the footage, which fired twice, the second time on its
  own correction.

**Phasing consequence:** dead-time trimming and point segmentation are now how the product
presents video, so the compute-triage activity gate and the point-boundary problem are
**one build, not two**. That is a genuine simplification — the gate was going to be built
for compute reasons anyway.

**Verified while scoping, and load-bearing for the playlists feature:**
- **Stroke type is a heuristic riding on pose, not a model.** `events.classify_shot`
  (`events.py:507`) decides forehand/backhand from contact side relative to body centre;
  `classify_spin` (`events.py:609`) reads the racket-hand keypoint path. Both consume pose
  keypoints, so **stroke classification costs nothing extra at runtime** — but it inherits
  all pose error.
- The module docstring (`events.py:9-10`) says the heuristic is *"replaced by a learned
  classifier in Phase 3"*. **That classifier was never built** — no stroke model exists
  anywhere in `backend/swingvision/`.
- **Neither stroke type nor spin has ever appeared in `docs/STATE.md`.** Zero rows. They
  have never been measured or gated by this project.
- The shot corpus is tiny: `events.py:234` notes *"a volley currently accounts for 1 of our
  26 shots"*.

So shot-filtered playlists ("only backhand errors", "only first serves") are gated on an
unmeasured heuristic. That is the weakest claim in the described product.

Related: [[mobile-parity-first]], [[line-call-numbers-assume-perfect-bounce]]
