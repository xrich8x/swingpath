---
name: seen-frac-gate-positive-control
description: Verification of backend-dev's seen_frac-vs-speed-error gate evidence (2026-09-03); positive control, rebuild reproducibility, and the court-coverage confound
metadata:
  type: project
---

Verified `docs/evidence/does-seen-frac-predict-speed-error.md` (backend-dev, commit
`79c381d`). Full writeup filed at `docs/evidence/seen-frac-gate-qa-verification.md`.

**Headline confirmed with a caveat.** `speed_confident = seen_frac >= 0.5` genuinely does
not predict speed error at its own threshold (G refused in every population/arm tested,
by both backend-dev and my independent rebuild). Accept-precision-equals-base-rate
(≈0.50 vs ≈0.47) reproduced almost exactly on a from-scratch reimplementation of the
harness — that is the load-bearing, trustworthy part.

**Why: a positive control matters here, and it partially passed.** Injecting a real
correlation between per-flight dropout and a genuine error-driver (apex height/`max_z`,
via rank-reassignment of the same dropout draws) DOES move the band ratio in the expected
direction on all 3 clips — so the harness is not blind by construction. But on 2 of 3
camera geometries the movement is weak/saturates near a -100%-signed-error ceiling once
court-coverage collapses (the estimator's path integral runs out of real points and
`smooth_and_fill` bridges flat) — meaning a WEAK true `seen_frac` effect could go
undetected by this exact band-window test on some camera mounts, in addition to the
causal-vs-correlational gap backend-dev already disclosed. **Any future gate-validation
harness of this shape should be positive-controlled BEFORE trusting a negative result on
it** — this is now a general lesson, not just a one-off finding: see
[[synth-truth-harness-reproducibility]].

**Court-coverage as a "rival predictor" is partly definitional, not purely diagnostic.**
`analytics.shot_speed_kmh` sums pairwise distances over exactly the points that survive
`cap_court_jumps`, so a fraction-of-span-that-survived metric will correlate with the
estimator's own error under almost any detector, by construction — the huge rho (-0.75 to
-0.82 across two independent harnesses) partly reflects that entanglement, not a fully
independent geometric insight. Worth checking for this shape of confound (a candidate
"better gate" measured on the same quantity its target error is computed from) whenever a
rival predictor is proposed from the same synthetic rig that produced the negative result.

**Standing note for next time a builder's harness needs re-verifying:** a scratchpad
script in another agent's OWN session temp directory is not accessible to QA — different
agent sessions get different `Temp/claude/<session-id>/scratchpad` paths, and this is
outside the project folder besides. QA cannot diff against it; the only option is an
independent rebuild from the evidence file's prose description, which is what happened
here. That rebuild reproduced classifier-shape numbers (accept-precision, refused-but-
accurate fraction) almost exactly but diverged materially on finer band-ratio digits
(one clip's ratio even flipped which side of 1.0 it landed on) — treat any two-decimal
ratio in this kind of synthetic-harness evidence file as indicative, not exact, unless the
literal script is available to re-run.
