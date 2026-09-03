---
name: speed-error-is-geometry-not-detection
description: Measured 2026-09-03 — seen_frac (did the detector see it) barely predicts speed error; court-coverage fraction (could the geometry place it) predicts it strongly
metadata:
  type: project
---

On synthetic flights through three audited calibrations (n=2557), **absolute speed error
is driven by whether the GEOMETRY could place the ball, not by whether the DETECTOR saw
it.** Spearman vs absolute % speed error: court-coverage fraction **-0.749**, `seen_frac`
**-0.098**. The mechanism: an airborne ball's z=0 projection lands outside the +/-4 m
runoff box, `ball_court_raw` empties, `smooth_and_fill` bridges the gap flat, and
`shot_speed_kmh`'s path integral collapses toward zero (median signed error -100%).

The `speed_confident` gate (`pipeline.py`, `seen_frac >= 0.5`) therefore gates on the
weaker of the two signals. Tested against its own pre-registered bar it came out
**INDETERMINATE** — "the gate predicts error" was refuted in every population, and as a
classifier of accuracy its accept-precision is **0.500 against a 0.472 base rate**. It
refuses ~10% of all shots that are *more* accurate than the median shot it accepts.

**Why:** this is the second gate on speed found not to predict speed error — `scale_ok`
was the first ([[traps-this-project-paid-for]]). The pattern is that plausible-sounding
perception-side proxies get gated onto a geometry-side quantity.

**How to apply:** before quoting any speed-coverage number, remember it is a count of shots
under an unvalidated bar. If speed accuracy is ever the target, look at court-coverage /
apex height first. **No replacement threshold may be proposed from that correlation** — the
pre-registration for choosing one (held-out clips, swept not point-picked, >=10-point
precision margin over base rate, plus a real-footage confirmation arm) is §7 of
`docs/evidence/does-seen-frac-predict-speed-error.md`.

**TWO CAVEATS ADDED 2026-09-03 after qa verification — both bound the numbers above.**

1. **The -0.749 is PARTLY MECHANICAL.** `shot_speed_kmh` integrates over exactly the points
   that survived court projection, so the path integral collapses toward zero *by
   construction* as court-coverage falls. The asymmetry against `seen_frac`'s -0.098 is
   real, but -0.749 is not a clean effect size and court-coverage must not be adopted as a
   gate on the strength of it: a gate has to be scored against an error measured over a
   span the gate did not itself define.
2. **The adjacent-band RATIOS in that evidence file are not quotable to 2-3 digits.** Over
   seeds 0-9 a single clip's ratio has sd 0.17-0.45 and ranges as wide as 0.62-1.89;
   bootstrap 95% CIs are 0.69-2.47 wide and **every one contains 1.0**. The
   accept-precision-vs-base-rate numbers (0.500 vs 0.467-0.473) DO reproduce across two
   independently written harnesses and are the quotable result. See
   [[band-ratio-of-medians-is-a-weak-instrument]].

**SETTLED 2026-09-04 — the threshold cannot be re-tuned; the gate needs REPLACING.**
Executed the repaired held-out bar (>=10-pt margin on >=3 of 4 clips + plateau + accepts
>=60% of what `t=0.5` accepts) on four fresh calibrations, 10 seeds:
**NO threshold is admissible, at any coverage floor above 26.5%.** Margin rises
monotonically with `t` and coverage falls monotonically with `t`, and they never overlap:
the only thresholds clearing +10 are 0.85 (26.5% coverage) and 0.90 (15.4%); the last one
meeting a 60% floor is 0.65 at 0/4 clips. `seen_frac`'s measured ceiling is ~6 points of
accept-precision at usable coverage, bought by refusing 77% of all accurate shots at 0.85
(vs 22% at 0.5). **Court-coverage was swept under the same bar and REJECTED**: it clears
+10 on 4/4 clips at *every* threshold (+38.6..+43.3, spread 4.7 pts), precision already
0.887 at `t=0.20`, and on the `shipped_shot` population — which drops the 34% of rows whose
speed estimate left 5..250 km/h — the margin collapses to 1/4 clips. Its headline margin is
largely a measurement of which shots it broke. Full tables: "The repaired bar, EXECUTED" in
`docs/evidence/does-seen-frac-predict-speed-error.md`.

**How to apply:** do not propose another `seen_frac` threshold, and do not propose
court-coverage as the replacement gate — both are now measured and closed. A new
speed-confidence signal has to be a *different quantity* (apex height, projection residual,
something not defined over the span it is scoring), and it must be scored on an error
measured over a span the gate did not itself define.

Caveat that bounds the finding: dropout in that experiment was random and independent of
the flight, so it answers the CAUSAL question (holding the shot fixed, does losing frames
hurt?) and cannot see whether `seen_frac` proxies some hard-shot property in real footage.
