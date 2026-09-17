---
name: synth-truth-harness-reproducibility
description: Rebuilding a synthetic (tools/synth_truth.py-based) harness from a prose description reproduces classifier-shape numbers closely but not fine band-ratio digits
metadata:
  type: project
---

When a builder measures something with a bespoke synthetic harness built on
`tools/synth_truth.py` + shipped `swingvision.ball`/`calibration`/`analytics` code, and
QA cannot access their literal script (it lives in scratchpad, often in a different
agent session's own temp directory, outside the project folder), QA's only option is an
independent rebuild from the evidence file's own methodology description.

**What reproduces well:** aggregate classifier-style numbers computed over large pooled
n (accept-precision vs base rate, refused-but-accurate fraction of refused, Spearman
correlation sign and rough magnitude) — these held up to within a few points across two
independently-written implementations with different RNG sequencing and different N.

**What does NOT reproduce well:** per-clip band-ratio numbers quoted to two decimal
places on n~50-150-per-band subsets. In [[seen-frac-gate-positive-control]] one clip's
ratio flipped which side of 1.0 it fell on between two legitimate rebuilds of the same
described method. Treat fine per-clip ratios in this class of evidence file as
indicative of direction/shape, not as precise digits, unless the literal script is
available to re-run — and say so explicitly in the QA report rather than silently
re-deriving different numbers and picking a side.

**Practical implication for future QA verification tasks:** budget for building a
positive control (inject a known effect and confirm the harness detects it) BEFORE
spending effort trying to match a builder's exact numbers digit-for-digit — the
positive control tells you whether the measurement approach works at all, which matters
more than matching two decimal places you cannot fully audit anyway.
