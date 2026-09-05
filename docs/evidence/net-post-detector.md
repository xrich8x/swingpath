# The net POST as a rigid off-plane camera-height reference

> **DELIVERABLE**: a net-post detector wired into an existing entry point, plus a
> per-clip table of fitted / tape-implied / post-implied camera heights, the
> instrument's pixel-sensitivity, every refusal with its reason, and the verdict
> against a bar pre-registered before the sweep ran.

> **This is a diagnostic NUMBER for the human who confirms a calibration at setup.
> It is NOT a gate.** Four autonomous accept/reject gates have failed in this family
> (`verify_court` coverage/centrality, the camera-height screen, `net_anchor_check`'s
> `band_ratio` and `dy`). This is not a fifth. Nothing here rejects a calibration,
> edits a calibration, or changes a fitted height.

## Why a post and not more tape

The net tape works (`net-tape-camera-height-consistency.md`: AGREE, 13/15 within 10%)
and is the only shipped check that reads a point **off** the ground plane — which
`independent-calibration-references.md` establishes is the whole reason it caught what
every ground-plane statistic missed. But the tape has one confound it cannot resolve
from its own evidence: **a net sags.** Four courts appear twice in the tape corpus and
every pair agrees in sign to <= 2.6 pp, which reads as court-specific net slack rather
than per-frame noise — but the tape alone cannot say whether a given clip's disagreement
is a slack net or a wrong calibration.

**A post does not sag.** It is rigid, at a regulation 1.07 m, at a known court x. So a
post measurement is off-plane like the tape and free of the tape's one confound, and
post-vs-tape disagreement is exactly the discriminator the tape lacked.

**Sag has a known sign**, which makes the comparison directional rather than merely
different. From `row = horizon + (ground_row - horizon)(1 - h/H)`, the estimator inverts
to `H_est = h_nominal / (1 - t)` with `t = (row_obs - horizon)/(ground_row - horizon)`.
A sagging net has true `h < 0.914` at the centre, so it images at a LARGER row, so `t`
is larger, so `H_est = H_true * 0.914 / h_true` is **larger than the truth**.

> **Net sag can only make the tape read the camera HIGHER. It can never make the tape
> read LOW.** So `tape > post` is consistent with slack; `tape < post` is not, and needs
> a different explanation.

## Post visibility is not the limit (already measured, not re-derived)

Both posts project inside the frame on **27 of 28** calibrations; at least one on
**28 of 28** (`independent-calibration-references.md`, falsifier run 2026-09-05). The
qualitative "posts are frequently off-frame" claim in `net-anchor-calibration-check.md`
is wrong. Two limits carried forward: it projects under each clip's *own* calibration,
and "in frame" is not "unoccluded".

## The pre-registered bar and refusal rules

(pending)

## Pricing the instrument: pixels per percent

(pending)

## Per-clip table: fitted / tape-implied / post-implied

(pending)

## The refusals

(pending)

## Verdict against the pre-registered bar

(pending)

## Post vs tape: sag or calibration error

(pending)

## NOT ESTABLISHED THIS RUN

(pending)
