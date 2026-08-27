---
name: line-call-numbers-assume-perfect-bounce
description: Every line-call accuracy number in this repo (95.9%, the 54/69/81% height curve) was measured with a PERFECT bounce detector; real bounce-detector error is unmeasured
metadata:
  type: project
---

**Every line-call accuracy figure in this project assumes the bounce position is
already known exactly.** `tools/synth_truth.py` (~line 251-254) takes the estimated
bounce as *the last projected point of the pre-bounce arc* — its own comment says this
is "the same information a perfect bounce detector would have."

That harness is what produced both headline numbers:
- **line calls 95.9%** (`docs/evidence/synthetic-ground-truth.md`)
- **close calls 54% at 1.0 m / 69% at 3 m / 81% at 8 m** vs a 56.2% majority floor
  (`tools/height_curve.py` imports `synth_truth.measure` and `summarize` directly)

**Why:** the harness was built to isolate the *projection* error (flat-plane assumption,
camera height, detector noise/dropout) — so it deliberately holds the bounce constant.
That was the right design for the question it was asked. It means the numbers are a
**ceiling**, not an end-to-end accuracy.

**How to apply:** never quote 95.9% or the height curve as what a user would experience.
They are upper bounds on the geometry, with the bounce-detection contribution set to
zero. Any feature whose output depends on *finding* the bounce — above all
`backend/swingvision/live.py`, whose bounce detector is a causal 3-segment local speed
minimum with no smoother — has **no measured accuracy at all**. There is no evidence
file for live calls; check `docs/evidence/` and you will find none.

Related: [[mobile-v1-scope-live-calls]], [[live-path-has-no-refusal-surface]]
