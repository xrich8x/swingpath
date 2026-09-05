---
name: mount-crossover-splits-v1-outputs
description: Below the ~2.0-2.2 m net-occlusion crossover v1 withholds metric outputs but still ships shot list and rally clips; pixel-domain ball numbers are provably unaffected
metadata:
  type: project
---

**The ~2.0–2.2 m crossover splits v1's outputs into two classes, and the split is by
COORDINATE SYSTEM, not by clip.** Derived 2026-09-05
(`docs/evidence/setup-envelope-net-occludes-far-baseline.md`); product consequences in
`docs/evidence/low-mount-implications.md`.

- **Time-domain and pixel-domain outputs ship at any mount height**: shot list, shot types,
  rally clips, dead-time trim, highlights, ball trail overlay.
- **Homography-domain outputs are withheld below the crossover**: ball speed (km/h),
  bounce map in court coordinates, distance run. Line calls were already parked.
- **Posture: WARN at capture, never block** (a recording refused courtside is a match lost
  forever); **BLOCK the metric outputs rather than caveating them** (a speed leaves the app
  in a screenshot with no caveat attached). One bit — *framing verified* — on the **match
  record**, not in view state.

**The fact that settles the gold-set question, and it was measured not inferred:** STATE's
BallNet-vs-TrackNet chain row records that the court gate removes **0 locks on 7 calibrated
clips × 2 arms** and `--no-gate` is **byte-identical**. The ball chain does not consume the
calibration, so **no pixel-domain ball number is at risk** from an unconfirmable court.

**The close-call curve is NOT this cost re-expressed.** 54.0%/69%/81% is *precision given a
correct homography*; the crossover is *whether a correct homography is identifiable at all*.
Independent costs that compound — but the remedy is the same one, so the user is asked for
one thing, not two. See [[line-call-numbers-assume-perfect-bounce]].

**Ship the QUESTION, not the number.** "Is the far baseline clear of the net tape?" is
self-verifying and needs no homography; "mount at 2.5 m" is a number a user cannot measure.
The comfortable-clearance threshold is 2.19–2.98 m depending on configuration anyway.

**Why:** five autonomous gates failed trying to verify an arbitrary calibration after the
fact; this is the same question asked *before* a homography exists, which is the only place
it is answerable.

**How to apply:** any brief touching the results screen must design an **absent-speed
state** from the start — retrofitting it later costs several sessions. Any proposal for a
corroboration ladder or a sixth calibration gate is rejected: net posts, fitted hfov,
gravity/arc and every ground-plane statistic are already in STATE's *What has not worked*.
Related: [[v1-cut-line-after-court-closure]], [[live-path-has-no-refusal-surface]].
