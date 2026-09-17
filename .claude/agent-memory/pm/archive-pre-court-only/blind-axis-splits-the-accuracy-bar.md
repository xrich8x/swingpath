---
name: blind-axis-splits-the-accuracy-bar
description: The monocular error is 23.5x anisotropic, so SPEC §3's single 10 cm bar measures a quantity that does not exist; v1 must output a margin, not a coordinate
metadata:
  type: project
---

**The camera is accurate in two dimensions and blind in the third.** Measured 2026-09-15
(P1 `docs/evidence/monocular-3d-ceiling.md`, R1 at the end of
`docs/evidence/monocular-3d-routes.md`): median error **5.4 cm perpendicular to the camera
ray, 1.28 m along it** — ratio **23.5**, confirmed across five mount heights and predicted
by closed-form geometry to within **4%** of the measured failure boundary.

**Why:** one pixel is `D²/(f·h)` metres down-court and `D/f` metres lateral; the ratio is
`D/h`. At 1080p / 3 m / far baseline that is ~10x. Raising the camera buys down-court
accuracy and **nothing else** (tangential error moves 36% across an 8x height change).

**How to apply — four things that outlive this task:**

1. **The bar's FRAME is a product decision and it was wrong.** Scalar `dist(true, est)` is
   not the product's error. The camera-ray frame (radial/tangential) is the right frame for
   the *mechanism*; the right frame for a *bar* is **perpendicular to the line being
   called**. They coincide only on the centreline. Never accept a pooled scalar accuracy
   number for a directional product again.
2. **Sidelines and the centre service line ride the good axis; baselines and service lines
   ride the blind one.** Any accuracy floor must be stated per line class.
3. **v1 outputs a CALL, never a COORDINATE** (pm recommendation, founder ruling pending):
   line, side, signed margin, uncertainty, or refusal. A rendered landing dot is over a
   metre wrong while the call beside it is right — **the dot destroys the trust the call
   earns.** The bounce map / placement heatmap is cut on measurement, not deferred.
4. **Narrowing what a bar applies to is a way of moving a bar.** The split survives that
   objection only because the mechanism was derived independently, pre-registered in a
   5-20 ratio band, and came back 12.6 — and because 10 cm and 90% themselves do not move.
   Demand all three of those before accepting any future "split the bar" proposal.

**The caveat that decides sequencing:** the **anisotropy is geometric and survives real
noise; the rates (6.1% pooled, 49.9% lateral, 83.9% lateral at zero noise) are properties
of an i.i.d. Gaussian noise model and a uniform flight population and WILL move.** So rule
on the SHAPE now, set the NUMBERS after real footage. Nothing here has touched real footage.

**Dead on measurement, do not re-propose:** any detector improvement (zero pixel noise still
gives 71.4%), pose or any launch anchor (an ORACLE `p0` still fails by 5x), zero spin,
refining the aero model, reprojection residual as a quality gate, depth-from-ball-size.

Related: [[v1-cut-line-after-court-closure]], [[line-call-numbers-assume-perfect-bounce]],
[[the-mount-crossover-splits-v1-outputs]], [[no-confirmed-metric-footage-exists]].
