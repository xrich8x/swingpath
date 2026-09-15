# Routes out of the monocular 3D ceiling — a ranked read on P1

**researcher, 2026-09-15.** Written against `docs/evidence/monocular-3d-ceiling.md` (P1, landed
2026-09-15), `docs/SPEC.md` §3/§4/§5, `docs/measure/CLOSED.md`, `docs/ball/CLOSED.md`,
`docs/STATE.md`, and a read of `tools/mono3d_ceiling.py`, `tools/synth_truth.py`,
`tools/gen_synth_camera.py:draw_launch`, `ball_physics/tennis_tracker/estimation/trajectory_fit.py`
and `ball_physics/tennis_tracker/bridge.py:180-260`.

**No number in this file is new. Nothing was run.** Every claim is tagged with which of three
kinds it is, and the three kinds are never blended:

| Tag | Means |
|---|---|
| **[M]** | **MEASURED in this repo.** Named source file. |
| **[P]** | **PUBLISHED elsewhere.** Cited, with the footage it was measured on. |
| **[A]** | **MY ARITHMETIC.** Closed-form, from the pinhole model and the court constants. Re-derivable in three lines. No data behind it — if the arithmetic is wrong the conclusion goes with it. |

**This file does not move a number and writes no STATE row. It proposes; it decides nothing.**

---

## 0. The answer to the question that matters — is 90% at 10 cm reachable at all?

**No, not as SPEC §3 is written, and the obstruction is not the estimator.** It is the angle at
which the camera meets the ground plane at the far end of the court, and it binds every possible
method equally.

But the failure is **one-dimensional, and the spec never noticed**. Stated in one line:

> **[A] From a mount of height `h` at range `D`, one pixel of image error is `D²/(f·h)` metres of
> DOWN-COURT error and `D/f` metres of LATERAL error. The ratio is `D/h`.**

At P1's configuration (1080p, hfov 100° → `f = 805.5 px`, `h = 3.0 m`, far baseline at `D = 29.8 m`
from the camera) that ratio is **≈ 10x**. One pixel is **36 cm down-court** and **3.7 cm across**.

So:

- **Baseline and service-line calls** — which need DOWN-COURT accuracy — require **0.28 px** of
  vertical localisation at the far baseline for 10 cm. That is not available from any detector, and
  it is not an estimator problem: **[M]** P1's bar C shows the estimator is a 2.2 cm instrument
  when the pixels are clean, and **[M]** bar E shows that even exactly-zero pixel noise reaches only
  71.4%.
- **Sideline calls** — which need LATERAL accuracy — require **2.7 px** at the same point. That is
  an ordinary ask. **It has never been measured separately, because P1 reports only the scalar
  distance.** This is the single most valuable thing in this document and it costs nothing to
  settle (route **R1**).

**The renegotiation pm should open with the founder is therefore NOT about the 10 cm number.** 10 cm
is defensible. It is about **which lines v1 calls, and what refusal rate is acceptable** — and, if
the founder insists on the far baseline, about the **capture spec**, which is a computable
requirement (§7 below) rather than a research bet.

Confidence that down-court 10 cm at the far baseline is unreachable at 1080p / 3 m by any admissible
method: **0.88.** What would move it: a demonstration that a real detector localises a motion-blurred
far ball to better than 0.3 px, or an independent depth channel I have not thought of. Confidence
that the lateral direction is ~`D/h` times better conditioned: **0.93** (it is pinhole geometry; the
only softness is a `sec²` term worth at most ~2x, and it is corroborated below).

---

## 1. The arithmetic, in full, because everything below is ranked by it

**[A]** P1's camera: width 1920, `hfov 100°` (`tools/height_curve.py:61`), so

```
f = (1920/2) / tan(50°) = 960 / 1.19175 = 805.5 px        vfov = 2·atan(540/805.5) = 67.7°
```

Setback 6.0 m (`height_curve.py:60`), so the near baseline is at `D = 6.0 m` from the camera and the
far baseline at `D = 29.77 m`. A ground point at range `D` sits below the horizon by `f·h/D` pixels.
Differentiating, with the camera pitched down by `φ` and the point at depression `θ`:

```
|dD/dv| = (D² + h²) / (f·h·sec²(θ−φ))      ≈  D² / (f·h)     when the point is near the image centre
|dLateral/du| = D / f
```

The `sec²` term is ≤ ~1.9 at the frame edge for a 67.7° vfov, so the simple form is **conservative by
at most a factor of 2**. With `f·h = 2416.5 px·m`:

| Range from camera | Down-court, m per px | Lateral, m per px | px needed for 10 cm down-court |
|---|---|---|---|
| 10 m (≈ 4 m past the near baseline) | 4.1 cm | 1.2 cm | 2.4 px |
| 15 m | 9.3 cm | 1.9 cm | 1.1 px |
| 20 m | 16.6 cm | 2.5 cm | 0.60 px |
| **29.8 m (far baseline)** | **36 cm** | **3.7 cm** | **0.28 px** |

**The break-even range where 10 cm equals exactly one pixel:**

```
D_1px = sqrt(0.1 · f · h) = sqrt(0.1 · 805.5 · 3.0) = 15.5 m from the camera
                                                    = 9.5 m past the near baseline
```

**[M] P1's measured split between fits inside and outside the 10 cm bar is 9.85 m down-court (good)
versus 23.62 m (bad).** My independently-derived break-even is **9.5 m down-court**. The arithmetic
reproduces the measured failure boundary to within 4%. I did not tune anything to make that happen,
and it is the reason I rank the geometric routes above the estimator routes.

**Why this caps every method, not just this one (hard rule 7).** At the bounce the ball is ON the
ground plane. That is the strongest depth pin the rule's inventory permits — a point known to lie on
`z = 0` has its full 3D position determined by a single pixel, with no physics, no spin and no
launch anchor needed. The table above is the resolution of **that** pin. Known `g`, drag, Magnus,
`physical_bounds` and a launch anchor are all ways of getting *to* the plane; none of them beats
being *on* it. **[M]** P1's oracle-`p0` arm is the empirical confirmation: perfect launch knowledge
— strictly more than pose could ever supply — still leaves a 0.29 m median, 5x outside the bar.

**Mount and resolution scaling, for §7:** capability goes as `sqrt(f·h)`. Covering the far baseline
at 10 cm needs `f·h ≥ D²/0.1 = 8,862 px·m`. Framing the 10.97 m doubles width from setback `S`
requires `tan(hfov/2) ≥ 5.485/S`, i.e. `f ≤ 175·S`. **[A]** At 1080p and `h = 3.0 m` those two
demands have **no solution at any setback**. At `h = 6 m` they intersect for `S ∈ [12.6, 45] m`. At
4K (`f = 1611 px` at hfov 100°) they intersect at `h ≈ 5.5 m`.

---

## 2. The ranked routes

Ranked by **(value if true) × (confidence) ÷ (cost to falsify)**. R1-R3 cost almost nothing and two
of them run on data already on disk; R4-R6 are estimator changes; R7 is a capture-spec change.

| # | Route | Pins depth with | Cost to falsify | Open? |
|---|---|---|---|---|
| **R1** | Decompose the existing bar-A error into lateral vs down-court | (nothing new — a re-read of P1) | **zero compute** | OPEN |
| **R2** | Fit-covariance abstention (`res.jac` → bounce 1σ) | (nothing new — supplies a *quality* statement) | ~20 min | OPEN |
| **R3** | Geometric capability map from the four-tap calibration | ground plane + known court dims, used to state their own limit | **zero compute** | OPEN |
| **R4** | MAP fit: 2D control as a bounce prior + population priors | ground plane via the homography; published launch statistics | ~1 h | OPEN |
| **R5** | Penalised (not bounded) spin | frees pixel information back into (p0, v0) | ~20 min | OPEN |
| **R6** | Joint pre- and post-bounce arcs sharing a z=0 bounce point | a point ON the plane, constrained from both sides — the only route that ADDS observations | ~1 h precursor, then days | OPEN, precursor-gated |
| **R7** | 4K capture as a geometric (not detector) lever | doubles the angular sampling of the ground plane | ~35 min, but partly undecidable here | OPEN with a caveat |

---

### R1 — Decompose the error. Free, and it may redefine the product.

**What it is.** P1 scores `math.dist(true_bounce_xy, bounce_xy)` — a scalar
(`tools/mono3d_ceiling.py:293`). Both endpoints are stored per flight. Recompute the error as its two
court-frame components instead: `Δx` = lateral (across the court, the sideline direction) and `Δy` =
down-court (the baseline / service-line direction). `synth_truth.to_court_xy` already puts both arms
in the same frame, where `x` is width 0-10.97 m and `y` is length 0-23.77 m.

**What pins the depth.** Nothing new. R1 does not estimate anything — it asks which *component* of
the existing estimate is already good enough. That is the point: **[A]** the lateral component is
pinned directly by the image `u` coordinate at `D/f` metres per pixel with no grazing penalty, and
the down-court component is pinned by the `v` coordinate at `D²/(f·h)`. They are not the same
measurement and should never have been pooled.

**Pre-registered bar** — config: the existing `barA_noise2px_3.0m` per-flight JSON, arm `b1`, seed 0,
n≈441. No refitting.
- **Primary:** median `|Δx|` (lateral) **≤ 0.20 m**. Pass ⇒ a sideline-only v1 at 10 cm is on the
  table today and pm has a product shape that does not need any of R4-R7.
- **Secondary (tests my arithmetic, not the estimator):** `median|Δy| / median|Δx|` within a factor
  of **2** of `D/h` evaluated at the median bounce range. **[A]** My prediction at the observed
  failing depth of 23.6 m down-court is `29.6/3.0 = 9.9`, so the pass band is **5-20**.
- **Kill:** median `|Δx|` > 0.50 m, **or** the ratio outside 3-30. Either outcome falsifies §1's
  geometric diagnosis, and if it does, **R3 and R7 go with it** — they are downstream of the same
  arithmetic.

**What would disprove it / cost if wrong.** A ratio near 1 would mean the error is isotropic, which
would mean the failure is optimiser pathology rather than grazing geometry, and would promote R4/R5
above everything. Cost: one afternoon of re-analysis, no compute, nothing built.

**Caveat, load-bearing.** The per-flight JSONs (`data/output/mono3d_ceiling/*.json`, ~13 MB) are
**[M]** not committed — `data/output/` is gitignored. If they are gone from disk, regenerating the
single bar-A configuration is a seeded ~1,050 s re-run, not a re-run of the 3-5 h sweep.

**Confidence the primary bar passes: 0.55.** Genuinely uncertain, which is exactly why it is ranked
first — it is the cheapest finding in the document to falsify and it has the largest product
consequence. What would move it: the number itself.

> **R1 HAS SINCE BEEN RUN — see "R1 — RUN AND SETTLED" at the end of this file.** Both bars PASS
> (median `|Δx|` 0.101 m; ratio 12.6). **The bar text above is left EXACTLY as pre-registered and
> must not be edited** (rule 2). But note that the consequence written into the Pass line —
> "a sideline-only v1 at 10 cm is on the table today" — **does NOT follow**, because this is a
> MEDIAN bar and SPEC §3's is a RATE bar: the lateral-only 10 cm rate is **49.9%** against a 90%
> requirement. The diagnosis is confirmed; that product conclusion is not.

**Feasibility on an A13:** not applicable — R1 changes nothing that runs on a phone.

---

### R2 — Fit-covariance abstention. SPEC §3 mandates it and it has never been measured.

**What it is.** `scipy.optimize.least_squares` returns `res.jac` at the solution. The parameter
covariance is `σ²(JᵀJ)⁻¹` with `σ²` from the residual; propagate it through the forward integration
and the ground intersection to a 2×2 covariance on the bounce point, and use its 1σ as **SPEC §3's
abstention signal** ("refuse the call if the tracking filter's position-uncertainty exceeds 10 cm at
1σ"). This does not improve accuracy. It decides which calls to make.

**Why it is not the thing P1 already killed.** **[M]** P1 measured `corr(rmse_px, err_m) = 0.159` and
concluded the reprojection residual is near-useless. The residual is the *fit quality*. The
covariance is the *parameter uncertainty*, and the two are different quantities precisely because
the problem is ill-conditioned: a tiny residual with a near-singular `JᵀJ` is exactly the signature
P1 observed (good fits 1.77 px, bad fits 1.87 px, bounce errors 0.32-10.30 m). **The covariance is
the object that knows the difference.** It has not been looked at.

**What pins the depth.** Nothing new — it inherits P1's pin list verbatim. What it supplies is a
calibrated statement about *how weakly* depth was pinned on this particular flight.

**Pre-registered bar** — config: exactly bar A (2.0 px noise, 0.30 dropout, 60 fps, 3.0 m, 1080p,
hfov 100°, seed 0, n=500, arm `b1`, `physical_bounds` on). **This is not a re-run of bar A. Bar A is
FAILED and stays failed. The estimand here is the abstention signal, not the landing accuracy.**
- **Primary (calibration):** among flights whose predicted 1σ ≤ 10 cm, **≥90% must have true error
  ≤ 10 cm**. The retained fraction is *reported, not gated* — a 3% retention that is honest is a
  result, not a failure (SPEC §3 explicitly allows this and §7's ≤5% refusal cap is already flagged
  provisional).
- **Secondary (discrimination):** Spearman ρ(predicted 1σ, true error) **≥ 0.50**, against the
  reprojection proxy's **[M]** 0.159.
- **Boundary handling, pre-registered:** a Jacobian covariance is invalid at an active bound, and
  **[M]** 4.1% of bar-A fits pin at the spin bound. Boundary-active fits count as **refuse**, never
  as dropped.
- **Kill:** ρ < 0.30, **or** the predicted-good subset is under 80% accurate. If it kills, **SPEC §3's
  abstention clause has no implementation and the product cannot honestly refuse** — which is a more
  serious finding than bar A failing, and pm needs it either way.

**What would disprove it / cost if wrong.** A low ρ. ~20 min of compute on 11 workers if `res.jac` is
persisted; the single bar-A config took **[M]** 1,050 s wall. If it fails, R3 is the fallback
abstention signal and does not depend on the fit at all.

**Feasibility on an A13.** A 9×9 (or 6×6) normal-equation inverse per arc is arithmetic in the noise
of a 16.7 ms budget — microseconds. It runs on the CPU alongside the fit and never touches the ANE.
Confidence this is affordable: **0.95**.

**Confidence the primary bar passes: 0.50.** Honestly a coin flip: the linearised covariance of a
bounded, badly-conditioned nonlinear fit is often optimistic by a large factor. What would move it:
the run. It is cheap enough that the coin flip is worth paying for.

---

### R3 — The geometric capability map. Deterministic, free at runtime, and it is the abstention signal that cannot fail.

**What it is.** From the four-tap calibration alone — which v1 already has, and which
`tools/court_setup_server.py` already produces — evaluate `|dD/dv| = (D²+h²)/(f·h·sec²(θ−φ))` across
the court and mark the region where 10 cm corresponds to at least some threshold of image
displacement. Refuse calls outside it. Show the user the callable region at setup time, before they
record. This is CLAUDE.md's "compute what you can": it is closed-form geometry, no ML, no model, no
per-frame cost. `run.py check` already exists to grade the mount and is the natural home.

**What pins the depth.** The ground plane and the regulation court dimensions — the same two pins,
used here to state *their own resolution limit* rather than to produce an estimate.

**Pre-registered bar** — config: the existing bar-A per-flight JSON (zero compute), plus the
existing `height*` and `kill*` configs for the cross-check.
- Partition the presented flights by true bounce range into three bins by *predicted* one-pixel
  down-court error: **< 10 cm**, **10-30 cm**, **> 30 cm**.
- **Pass:** measured median error is **monotone increasing** across the three bins, **and** the ratio
  of measured medians between the outer bins is within a factor of **2** of the ratio the formula
  predicts.
- **Cross-check, also free:** across the existing 1.0 / 1.5 / 2.5 / 4.0 / 8.0 m height configs, the
  measured median error should scale roughly as `1/h` at fixed range. **[M]** P1 reports 3.09 m at
  1.0 m and 0.64 m at 8.0 m — a 4.8x span against a predicted 8x, same direction, right order. That
  is already weak corroboration before the run.
- **Kill:** non-monotone, or the outer-bin ratio off by more than 3x. That kills §1's diagnosis and
  R1's secondary bar simultaneously.

**What would disprove it / cost if wrong.** Non-monotonicity. Cost: an afternoon of re-analysis.

**Feasibility on an A13.** A lookup table computed once at calibration. Zero per-frame cost.
Confidence: **0.98**.

**Confidence: 0.85** that the map is predictive enough to gate on. What would move it: the bin test.

**Product note, stated and left open.** R2 and R3 are complementary, not alternatives: R3 refuses by
*where the ball landed* (known before the ball is hit) and R2 refuses by *how well this particular
arc was determined*. R3 alone gives a static callable region; R2 alone gives a per-call confidence;
both together give a refusal the user can understand ("your camera cannot resolve that end of the
court from here — move it back or higher").

---

### R4 — MAP fit: give the 3D arc the 2D control as a prior, and give the launch state a population prior.

**What it is.** Replace the maximum-likelihood fit (pure reprojection least-squares inside a hard box)
with a penalised one. Append residual blocks: `√λ_k (x_k − μ_k)` for each launch parameter with an
independently-sourced population prior, and a block pulling the fitted arc's `z = 0` crossing toward
the 2D control's homography estimate, weighted by the control's own measured error distribution.
Hard bounds become soft priors and the boundary optima that break R2 disappear.

**What pins the depth.** Three things, all admissible:
1. **The ground plane, read directly.** The 2D control *is* the `D²/(f·h)` channel of §1, applied at
   the one instant when its `z = 0` assumption is exactly true. **[M]** At 2 px it has a 55 cm median
   against the 3D fit's 132 cm, and it wins at every noise level from 1 px up. **The 3D arm currently
   discards the better estimator.** A correctly weighted combination of two estimators cannot, in the
   Gaussian limit, be worse than the better of them.
2. **Published launch statistics**, which exclude the fast-and-far branch of the monocular ambiguity.
3. Everything P1 already pinned (known `g`, drag+Magnus, exact hfov, 6-DOF pose from four corners).

**The self-grading hazard, named before it bites (hard rule 1).** **[M]**
`tools/gen_synth_camera.py:36-50` draws speed `U(18, 55) m/s`, elevation `U(−5°, 22°)`, topspin
`U(−1500, 3500) rpm`, launch height `U(0.3, 1.2) m`. **Setting the priors to those numbers is using
the answer key.** The priors must be pre-registered from the tennis literature and reported side by
side with the rig's draw so the overlap is visible and auditable. If the externally-sourced prior
happens to be tighter than the rig's draw anywhere, that arm is void.

**Pre-registered bar** — config: bar A's exact settings, paired on the same seeded flights and the
same noisy pixels, one variable changed.
- **Primary:** paired median bounce error falls from **[M]** 1.32 m to **≤ 0.55 m** — that is, the
  fused estimator must at minimum MATCH the 2D control it is being handed, or the fusion is
  destroying information. Pass also requires it to be better on **≥60%** of flights (paired sign
  test; **[M]** the spin-zero arm scored 29.7% on this and was correctly called worse).
- **Guard, must also hold:** at the noiseless configuration (0 px, 0 dropout, 3.0 m) the median must
  not rise above **5 cm**. The prior must not damage the case where **[M]** the fit is already a
  2.2 cm instrument. A prior that helps at 2 px by ruining 0 px is a knob.
- **Kill:** paired median > 0.90 m, or the noiseless median > 5 cm.
- **This is a new hypothesis with a new bar. It does not re-open bar A.**

**What would disprove it / cost if wrong.** The primary bar. ~1 h of compute (two configs) plus the
prior-sourcing work. If it fails, the correct product conclusion is to **retire the 3D arm for the
landing point** and keep it only for bounce timing and the height flag — which is a clean, cheap
decision, not a dead end.

**Feasibility on an A13.** Extra residual blocks are ~free; the cost of a fit is dominated by
**[M]** `(t_max/dt)` RK4 steps per residual evaluation (`fit_arc` docstring). Adding priors does not
change that and typically *reduces* iteration count by improving conditioning — **[M]** the spin-zero
arm converged 7.6x faster for exactly this reason. It stays a CPU-side arithmetic job, off the ANE.
Confidence it fits the 16.7 ms budget: **0.35, and this is unmeasured** — 400 `max_nfev` × ~500 RK4
steps is not obviously a 16.7 ms job on an A13 and no number in this repo covers it. That is a
separate open question (§8).

**Confidence the primary bar passes: 0.60.** What would move it: whether the 2D and 3D errors are
correlated. If they share the same grazing-geometry cause — and §1 says they do — the fusion gain is
much smaller than independence would suggest. That is the main reason I am not more confident.

---

### R5 — Penalised spin, not bounded spin. (The brief's second question.)

**Verdict first: a BOUND is a knob. A PENALTY is principled. `_spin_parsimonious` is the crude
special case of the penalty.**

**Why a bound is a knob.** A hard bound only acts on the fits whose unconstrained optimum lies
outside it — **[M]** 4.1% of bar-A fits sit at the current 12,405 rpm bound and the fitted p90 is
7,244 rpm. Lowering the bound moves those and nothing else, it has no principled value except the one
you pick, and it *creates* a boundary optimum, which is precisely where R2's Jacobian covariance
becomes invalid. It makes the abstention signal worse in order to make the point estimate slightly
better. **[M]** `bridge.py:211 _spin_parsimonious` already ships `max_rpm = 3500.0` — and
**[M]** `draw_launch` draws `|ω| ≤ ~3,700 rpm`, so testing that exact value on this rig would be
grading against the answer key. Do not.

**Why a penalty is principled.** Spin is a parameter with a *known population distribution*. The
correct treatment of such a parameter is a prior, not a wall: append `√λ·ω` to the residual with `λ`
set so the implied prior width matches the published distribution. It is smooth, it degrades
gracefully to free spin when the data genuinely demand curvature, it never creates a boundary, and it
sits on the continuum whose two endpoints P1 already measured: **[M]** free spin 1.32 m, zero spin
3.31 m. Since zero is *worse*, the optimum is interior — which is the definition of a case a ridge
handles and a switch does not. `_spin_parsimonious`'s two-stage accept/reject is the same idea
collapsed to a 0/1 decision with a hand-set `min_gain = 0.30`.

**Sourcing `λ` externally (mandatory).** **[P]** Press-reported Hawk-Eye figures: Nadal's forehand
averages ~3,200 rpm with a measured peak of ~4,900 rpm, and the highest measured groundstroke is
Federer's backhand slice at ~5,300 rpm — ATP-tour broadcast footage, not amateur, and not
peer-reviewed. **[P]** Cross & Lindsey's serve-spin work is the peer-reviewed reference for serve
spin rate and axis. **Every one of these is a professional number and our footage is amateur, so
they are an upper bound, which is the safe direction for a prior.** A prior width around
`σ ≈ 2,000 rpm` with no hard ceiling is looser than the rig's own draw and therefore not the answer
key.

**What pins the depth.** Nothing new. The mechanism is subtractive: **[M]** the optimiser is
demonstrably absorbing pixel noise into fictitious Magnus force (fitted p90 7,244 vs true 3,116), and
every unit of noise absorbed there is a unit not being resisted by `(p0, v0)` — the parameters depth
rides on. Removing the sink forces the pixel information back into the parameters that matter.

**Pre-registered bar** — config: bar A exactly, paired, one variable (`λ` added). Both comparison
arms are **[M]** already on disk at seed 0.
- **Pass:** paired median error **≤ 1.00 m** (a 25% cut on 1.32) **AND** fitted-spin p90 **≤ 5,000
  rpm** **AND** **< 1%** of fits above 8,000 rpm.
- **Kill:** paired median **≥ 1.32 m** — no better than free spin. If it kills, **spin regularisation
  is dead in every form**, because zero (3.31 m) and free (1.32 m) then bracket it with no interior
  gain, and that closes the whole family in one run.
- `λ` is pre-registered from the literature as a **single value**. A 3-point sensitivity sweep is
  reported alongside but **must not be used to select** — selecting on the rig is fitting to truth.

**What would disprove it / cost if wrong.** The paired median. **This is the cheapest estimator change
in the list: one configuration, ~1,000 s.** It is also a strict subset of R4, so if R4 is run it
should be run as R4's first arm to keep one-variable discipline (hard rule 8).

**Feasibility on an A13:** identical to R4 — one extra residual block, no ANE involvement.

**Confidence the pass bar is met: 0.45.** What would move it: whether the 4.1% bound-pinned tail is
representative of a broader, softer noise-absorption across the whole population, or is genuinely
just 4% of flights. **[M]** The fitted p90 of 7,244 vs a true 3,116 says the inflation is broad, not
tail-only, which is the reason I am not lower.

---

### R6 — Joint pre- and post-bounce arcs sharing one `z = 0` bounce point. The only route that adds observations.

**What it is.** Stop fitting a single arc that ends at an unobserved extrapolated crossing. Fit the
pre-bounce and post-bounce arcs *simultaneously*, sharing one bounce point constrained to lie on
`z = 0`, linked by a restitution and spin-reversal model. The bounce point stops being the far end of
a nine-parameter extrapolation and becomes a directly parameterised two-DOF quantity on a known
plane, constrained by observations from **both** sides.

**What pins the depth.** **A point known to lie on `z = 0` is fully determined in 3D by one pixel** —
the strongest pin available from a single camera, and P1 currently spends it exactly once, at the end
of an extrapolation, after all the conditioning damage has already been done. R6 makes it a shared
parameter and lets the post-bounce observations constrain the same point from the other direction.
**Everything in R2-R5 is conditioning. R6 is the only entry that brings new data.**

**RULE 3 CHECK — this is NOT the closed bounce work, and I am flagging it because it sounds like it.**
`docs/ball/CLOSED.md` carries four adjacent rows: `bounce_hypothesis` (gate fails P2/P6 over 10 gold
clips), `bounce_hypothesis v2 / restitution_set` (fails 4 of 7 bars), `bounce_reset` (fails on all 3
clips), and `docs/STATE.md:170` ("more restitution hypotheses is the WORSE half of v2"). **All four
are modifications to the 2D Kalman smoother in `backend/swingvision/ball.py`, operating on pixel
tracks with no 3D model at all.** R6 is a change to the parameterisation of the 3D physics fit in
`ball_physics/`. Different subsystem, different mechanism, different failure mode. It is not a
re-proposal — but pm and qa should both satisfy themselves of that before anyone spends on it.

**The honest risk.** R6 imports a restitution model — surface-dependent, spin-coupled, and
**unmeasured here** — at exactly the point of interest. **[M]** Bar F showed ±20% aero
mis-specification has no detectable effect, but that was aerodynamics *in flight*. **Do not transfer
bar F's reassurance to restitution *at* the bounce.** They are different quantities and the second
one sits directly on the estimand.

**Pre-registered bar, in two stages.** The rig currently simulates with `bounces=0` and truncates the
observed track at the true bounce, so R6 has no data to fit until the rig is extended.
- **PRECURSOR (cheap, gates everything else):** re-run the rig with `bounces=1` and a longer horizon,
  and report how many presented flights have **≥5 in-frame, in-horizon post-bounce observations**.
  **Pass if ≥60% do.** If under 60%, R6 has nothing to add and dies here, for ~1 h, before any
  fitter work. *(My expectation is that far-court bounces often exit frame or horizon immediately
  after the bounce, so I rate this genuinely uncertain.)*
- **ROUTE BAR, only on a precursor pass:** paired median bounce error **≤ 0.55 m** at bar-A noise,
  **AND** a bar-F-style self-grading control in which the simulator's restitution coefficient is
  offset by **±20%** from the fitter's and neither arm differs from matched by more than **2σ**. If
  the ±20% arms *do* differ, R6's gain is a shared-model artefact and the route is void regardless of
  the primary number.

**What would disprove it / cost if wrong.** Precursor: ~1 h, rig change only. Full route: days of
`backend-dev` time plus a restitution model nobody has measured. **That asymmetry is why the
precursor is mandatory and why R6 ranks below R4/R5 despite having the better mechanism.**

**Feasibility on an A13.** Roughly doubles the fit cost (two arcs, more observations). Given R4's
already-unmeasured latency position, this makes the INSTANT budget harder, not easier. Confidence it
fits 16.7 ms: **0.20, unmeasured.**

**Confidence the route bar would pass if the precursor passes: 0.55.** What would move it: the
precursor's post-bounce observation count, and any real measurement of court restitution variance.

---

### R7 — 4K capture as a geometric lever. Admissible, but partly undecidable inside these constraints.

**What it is.** Capture at 3840×2160 instead of 1920×1080. **[A]** `f` doubles to 1,611 px at hfov
100°, so every entry in §1's table halves and `D_1px` rises by √2 from 15.5 m to 21.9 m from the
camera — i.e. the 10 cm-capable band extends from 9.5 m to **15.9 m past the near baseline**, which
reaches the far service line but still not the far baseline.

**What pins the depth.** The same ground plane, sampled at twice the angular rate.

**This is not the closed row, and it is not detector work.** `docs/ball/CLOSED.md` closes *raising
the detector's input resolution* (the model's input tensor; Gate B fails on both clips). R7 changes
the **optical sampling of the scene**, which changes the metres-per-pixel of the measurement itself
— a different quantity with a different mechanism. Hard rule 6 closes detector work; R7 proposes no
change to any detector.

**The reason it may self-cancel, stated up front.** A heat-map detector's centroid noise is not a
fixed number of pixels. If localisation noise scales with the ball's blob size in pixels, doubling
resolution doubles the pixel noise and cancels the geometric gain **exactly**. Whether it cancels is
a **detector measurement**, and rule 6 closes that. **So this route cannot be fully adjudicated by
anyone operating under these constraints, and saying so is the correct answer rather than guessing.**

**Pre-registered bar that changes no detector** — config: bar A at 3840×2160, two arms.
- **Optimistic arm:** pixel noise held at **2.0 px** (noise does not scale with resolution).
- **Pessimistic arm:** pixel noise at **4.0 px** (noise scales exactly with resolution).
- **Pass only if the PESSIMISTIC arm's median improves by ≥30%.** If only the optimistic arm
  improves, R7 is **undecidable without a barred measurement** and must be reported as undecidable,
  not adopted. Cost: two configs, ~35 min.

**Feasibility on an A13.** **[P]** iPhone 11 (A13) and later capture 4K60. **[M, memory]** Nothing in
this repo has ever been measured on the ANE, and sustained 4K60 capture *plus* per-frame inference
after a full match is a thermal question with no number behind it
(`.claude/agent-memory/researcher/coreml-ane-budget.md`, `ios-background-compute.md`). **A 4x pixel
budget against a 16.7 ms frame on the weakest supported device is the part I would expect to bind,
and I will not assert it either way.** Confidence 4K60 + per-frame ANE inference sustains on an A13:
**0.30, unmeasured.**

**Confidence the geometric half is real: 0.90** (it is arithmetic). **Confidence the end-to-end gain
survives: 0.35.**

---

## 3. Bar G — depth-from-known-ball-size. Answered on paper. It does not need a run.

**[M]** P1 left SPEC §5's depth-from-known-ball-size untested because the rig emits `(u, v)` with no
radius. **The arithmetic settles it without building the missing channel, which saves the run and,
more importantly, avoids a rule-1 trap.**

**[A] The apparent diameter of a 6.7 cm ball is `s = f·d/Z`**, so at `f = 805.5 px`:

| Range `Z` | Apparent diameter | Metres of depth per PIXEL of diameter error |
|---|---|---|
| 5 m | 10.8 px | 0.46 m |
| 12 m | 4.5 px | 2.67 m |
| 23 m | 2.35 px | 9.80 m |
| 29.8 m (far baseline) | 1.81 px | 16.2 m |

**[A] And the decisive form, which is scale-free — the focal length cancels:**

```
dZ/Z = − ds/s
```

**To place a bounce to 10 cm at range `Z`, the apparent diameter must be measured to a FRACTIONAL
precision of `0.1/Z`, no matter what the focal length, sensor or resolution is:**

| Range | Required fractional size precision | In pixels of diameter |
|---|---|---|
| 5 m | 2.0% | 0.22 px |
| 12 m | **0.83%** | **0.037 px** |
| 23 m | **0.43%** | **0.010 px** |

**Three independent reasons this is not attainable, none of which a better sensor fixes:**

1. **[A] Motion blur dominates the apparent extent.** A ball at 30 m/s at 12 m range moves 0.5 m per
   frame at 60 fps, which is **34 px of smear** against a **4.5 px** ball. Even a 1/250 s shutter
   gives 8 px of smear — still 1.8x the ball's own diameter. The measured "size" is an exposure
   parameter, not a physical one.
2. **Apparent size is a radiometric quantity, not a geometric one.** A blob's extent depends on
   contrast, background and threshold. **[M, memory]** The shelved int8 work found that
   **quantisation moved blob AREA, not peak** — the project has already measured that size is the
   fragile quantity while position is the robust one
   (`.claude/agent-memory/researcher/coreml-ane-budget.md`).
3. **[A] Even a perfect sensor has a quantisation floor.** At a physically unavoidable ±0.5 px on the
   diameter, depth at 12 m is ±1.33 m and at 23 m is ±4.9 m. **That is a floor, not an estimate**, and
   it is 13x and 49x outside the bar respectively.

**Verdict: SPEC §5's depth-from-known-ball-size is NOT an independent depth channel at tennis ranges.
Confidence 0.90.** What would move it: a real measurement showing sub-1% apparent-diameter precision
on a motion-blurred 2-5 px blob. I judge that implausible and it is barred here anyway as detector
work.

**What it might still be, stated fairly:** a **weak soft prior**, worth order ±1-3 m of depth per
frame, which over 20 observations could contribute at the ±0.3-0.7 m level — comparable to R4's 2D
control prior but far worse, and pointing in the same direction. **It is not worth building
separately, and it should be folded into R4 or dropped.**

**And a warning about testing it on the rig.** The rig would have to *synthesise* an apparent radius
with an assumed noise model. **We have no measurement of real apparent-size noise on real footage, so
the experiment would grade our own assumption — that is exactly the failure hard rule 1 exists to
prevent.** If anyone insists on running bar G, the honest precursor is measuring apparent-radius
precision on real clips first, and that is detector work, which rule 6 closes. **The arithmetic above
is the cheaper and more honest answer.**

**[P] A counterpoint I want on the record, because it is the benchmark-transfer trap in its purest
form.** Vorobev, Prosvetov & Elhadji Daou, *Real-time Localization of a Soccer Ball from a Single
Camera* (arXiv:2506.07981, 9 June 2025) report **centimetre-level** monocular 3D ball localisation,
comparable to multi-camera systems, on CPU in real time. **It is measured on 6K-resolution Russian
Premier League broadcast footage with a 22 cm ball.** **[A]** Against our 1080p and 6.7 cm that is
roughly **10x** in `f·d` before accounting for broadcast long-lens framing. **The result is real and
it does not transfer.** Cite it only with that sentence attached.

---

## 4. What is already dead, so nobody re-proposes it (hard rule 3)

| Idea | Why it is dead | Source |
|---|---|---|
| Any ball-DETECTOR improvement | **[M]** Zero pixel noise still yields 71.4%; four detector gains delivered nothing to the product | rule 6; P1 bar E; `ball/CLOSED.md` |
| Pose, a launch anchor, occlusion prediction | **[M]** An ORACLE `p0` — better than any pose model — still fails by 5x (0.29 m median) | P1 secondary arm; SPEC §6/§9 tossed |
| Zero / flat spin | **[M]** Paired median 1.32 → 3.31 m; better on only 29.7% of flights | P1 spin-zero diagnostic |
| Refining the aerodynamic model | **[M]** ±20% mis-specification has no detectable effect (1.1σ / 0.2σ) | P1 bar F |
| Reprojection residual as a quality or abstention gate | **[M]** `corr(rmse_px, err_m) = 0.159`; good 1.77 px vs bad 1.87 px, n=441 | P1 diagnosis |
| Depth-from-known-ball-size as a measurement channel | **[A]** Needs 0.83% fractional size precision at 12 m; blur alone is 8x the ball | §3 above |
| A hard spin BOUND as the fix | Knob; acts on 4% of fits and breaks R2's covariance | §R5 |
| Mining the non-converged fits | **[M]** Only 19 of 441, and their median error (0.93 m) is *better* than the converged population | P1, rule 11 |
| Second camera / stereo / any network call | v2 / scope violation | CLAUDE.md |
| Court auto-detection | Closed for v1; the court is a manual four-tap | CLAUDE.md |

---

## 5. Where there is no ground truth at all — say it plainly

1. **Nothing in P1 or in anything proposed here has touched real footage.** Every number is against a
   simulator sharing a physics model with the fitter. **[M]** Bar F shows that does not flatter the
   result at 2 px, but it is still synthetic pixel noise with an assumed Gaussian, i.i.d. structure.
   **Real detector error is not i.i.d.** — it is correlated across frames, biased by motion blur
   direction, and heavier-tailed. **Every route above would be ranked on a proxy.** I have no way to
   fix this from here, and CLAUDE.md already records it: the 10 cm gold set **cannot be labelled from
   video** and must be built at capture with tape-measured marks.
2. **The flight population is not a tennis population.** **[M]** `draw_launch` samples speed and
   elevation *uniformly* over wide ranges. Real amateur rallies are not uniform, and the failure
   cases P1 identifies (fast, lofted, far) are over-represented relative to a real rally. **The 6.1%
   may be pessimistic for real footage and nobody knows by how much.** Any route bar above inherits
   this and none of them can fix it.
3. **No number in this project has ever come from a phone.** Every "feasibility on an A13" line above
   is judgement, not measurement.

---

## 6. For the PM — the tradeoff, stated plainly, decision left open

**The 10 cm number is fine. The coverage promise is what breaks.** SPEC §3 asks for 10 cm on ≥90% of
near-line contested calls. §1's arithmetic says the sidelines are roughly **`D/h` ≈ 10x** better
conditioned than the baseline, and P1 never separated them. There are three shapes for v1 and they
are not mutually exclusive:

- **(a) Keep 10 cm, accept a large refusal rate, refuse by geometry (R3) and by fit covariance
  (R2).** SPEC §3 already permits this — "10 cm applies to calls the system actually makes" — and
  §7's ≤5% refusal cap is already flagged provisional in the spec's own text. **This is the honest
  shape and it is nearly free to build.** The open question is whether a product that refuses the far
  baseline is a product the founder wants.
- **(b) Keep 10 cm and keep coverage, and move the CAPTURE requirement.** **[A]** The requirement is
  computable, not a research bet: `f·h ≥ 8,862 px·m` with `f ≤ 175·S`. At 1080p and a 3 m mount **no
  setback satisfies it**. A 6 m mount needs 12.6 m of setback. 4K plus a ~5.5 m mount satisfies it.
  This is a **hardware and court-access decision**, not an engineering one, and it collides head-on
  with CLAUDE.md's founding premise that this works "regardless of mount height" — a premise **[M]**
  P1's bar D passed only because every height failed equally.
- **(c) Make the bar depth-dependent, or make it a call rather than a coordinate.** 10 cm near, a
  wider bar far; or in/out with a margin test instead of a landing coordinate. **R1 decides how much
  room this has, for free.**

**My recommendation on sequencing, and it is a recommendation, not a decision: run R1 first.** It
costs nothing, it uses data already produced, and its outcome changes which of (a), (b) and (c) is
even on the table. Running R4/R5 before R1 risks spending a day on an estimator improvement in a
direction the geometry will not repay.

---

## 7. Open questions

1. **Is the error anisotropic as §1 predicts?** R1 settles it for free. Everything else in this
   document is downstream of the answer.
2. **Can the fit state its own uncertainty?** R2. If not, SPEC §3's abstention clause has no
   implementation and that must go to the founder regardless of bar A.
3. **How many post-bounce observations survive in frame?** R6's precursor. Cheap, and it decides
   whether the only information-adding route exists at all.
4. **Does a real detector's pixel noise scale with capture resolution?** Decides R7, and it is
   **undecidable under rule 6**. Someone with authority to re-open detector measurement would have to
   rule.
5. **What is the actual per-arc latency of `fit_arc` on an A13?** Unmeasured. **[M]** `fit_arc`'s cost
   is `(t_max/dt)` RK4 steps per residual evaluation with `max_nfev = 400`, and R4/R6 both make it
   heavier. Against a 16.7 ms INSTANT budget this is not obviously affordable and no number in this
   repo covers it. It is a CPU-side cost, so the ANE budget work does not answer it.
6. **What does real restitution variance look like on amateur courts?** Unmeasured, and R6 imports it
   at the estimand.

---

**Cheapest finding to falsify:** R1 — zero compute, a re-read of JSON already produced, and it has the
largest product consequence of anything here.

**What would disprove the whole document:** if R1's ratio comes back near 1 (isotropic error), then
§1's grazing-geometry diagnosis is wrong, R3 and R7 collapse with it, and the failure is optimiser
pathology after all — which would promote R4 and R5 to the top and make me substantially more
optimistic about SPEC §3.

---

# R1 — RUN AND SETTLED, 2026-09-15 (lead). BOTH BARS PASS. The diagnosis holds; the product claim does not.

**Measured against:** the existing `data/output/mono3d_ceiling/*.json` per-flight records, arm `b1`,
seed 0, n=441. **No refitting, no new compute** — exactly the re-read R1 specified. The lead
independently re-derived researcher's arithmetic before running it: `f = 960/tan(50°) = 805.5 px`,
`D²/(f·h) = 36.8 cm` down-court vs `D/f = 3.7 cm` lateral at the far baseline, break-even at
`sqrt(0.1·f·h) = 15.5 m` from camera = **9.54 m past the near baseline** against P1's measured
good-fit median of **9.85 m**.

## The bars, exactly as pre-registered above

| Bar | Required | Measured | Verdict |
|---|---|---|---|
| **Primary** | median `\|Δx\|` (lateral) <= 0.20 m | **0.101 m** | **PASS** |
| **Secondary** | `median\|Δy\|/median\|Δx\|` in 5-20 | **12.6** | **PASS** |
| **Kill** | med `\|Δx\|` > 0.50 m, or ratio outside 3-30 | 0.101 m, 12.6 | **NOT FIRED** |

## The error is one-dimensional, and it is worse than the court-frame ratio shows

Decomposing about the **camera ray** rather than the court axes — more physically exact, since the
camera sits 6 m behind the near baseline on the centreline — the anisotropy is larger:

| Config | med lateral `\|Δx\|` | med down-court `\|Δy\|` | ratio | med **tangential** | med **radial** | radial/tang |
|---|---|---|---|---|---|---|
| noise 0 px | 0.002 | 0.020 | 9.5 | **0.001** | 0.020 | 20.4 |
| noise 1 px | 0.087 | 0.922 | 10.6 | **0.038** | 0.943 | 24.5 |
| **bar A (2 px)** | **0.101** | **1.270** | **12.6** | **0.054** | **1.280** | **23.5** |
| noise 4 px | 0.145 | 1.655 | 11.4 | 0.080 | 1.658 | 20.6 |

**The median error perpendicular to the camera ray is 5.4 cm. The median error along it is 1.28 m.**
The estimator is not broadly inaccurate — it is accurate in two of three dimensions and blind in the
third, which is the one a single camera cannot observe (hard rule 7, now with a number attached).

## The height sweep confirms the MECHANISM, not just the symptom

If the cause is grazing geometry then the ratio must track `D/h` while the tangential error stays
put. It does, across five independent configurations:

| Mount | D/h | radial/tangential | med tangential | med radial |
|---|---|---|---|---|
| 1.0 m | 28.9 | **69.6** | 0.044 | 3.090 |
| 1.5 m | 19.2 | 53.4 | 0.046 | 2.467 |
| 2.5 m | 11.5 | 29.3 | 0.052 | 1.526 |
| 4.0 m | 7.2 | 18.9 | 0.056 | 1.055 |
| 8.0 m | 3.6 | **9.9** | 0.060 | 0.593 |

**Tangential error moves 36% across an 8x change in mount height. Radial error moves 5.2x.** Raising
the camera buys down-court accuracy and nothing else — which is exactly what the `D²/(f·h)` vs `D/f`
pair predicts, and it re-reads bar D: the founding premise passed only because the pooled scalar
hid a component that is strongly height-dependent and one that is barely height-dependent at all.

And by depth, within bar A — the `D²` vs `D` scaling, visible directly:

| Bounce depth | n | med `\|Δx\|` | lateral <=10 cm | med `\|Δy\|` | down-court <=10 cm |
|---|---|---|---|---|---|
| 0-6 m | 11 | 0.039 | 63.6% | 0.19 | 36.4% |
| 6-12 m | 86 | 0.067 | 62.8% | 0.26 | 23.3% |
| 12-18 m | 63 | 0.092 | 52.4% | 0.50 | 7.9% |
| 18-24 m | 73 | 0.085 | 53.4% | **0.86** | **4.1%** |

## THE CORRECTION — passing R1's bar does NOT put a sideline-only v1 on the table

R1's stated consequence was that a PASS means "a sideline-only v1 at 10 cm is on the table today".
**That does not follow, and the reason is a bar-shape mismatch that is worth naming.** R1's primary
bar is a **MEDIAN** bar (<= 0.20 m). **SPEC §3's bar is a RATE bar — >=90% of calls within 10 cm.**
A median passing at 0.101 m says nothing about the 90th percentile, and here the two diverge hard:

| | 10 cm rate | needed | p90 |
|---|---|---|---|
| pooled 2-D (bar A) | 6.1% | 90% | 6.48 m |
| **lateral only** | **49.9%** | 90% | **0.611 m** |
| tangential only | 69.8% | 90% | — |
| lateral, PERFECT pixels | 83.9% | 90% | — |
| tangential, PERFECT pixels | 87.1% | 90% | — |
| tangential, ORACLE `p0` anchor | 90.0% | 90% | — |

**Restricting to the lateral component raises the 10 cm rate 8x, from 6.1% to 49.9% — and still
fails SPEC's 90% bar by 40 points.** Even with *zero* pixel noise the lateral rate is 83.9%. The
only configuration that reaches 90.0% is the tangential component under an **oracle** launch anchor,
i.e. information v1 does not have and no pose model could supply perfectly.

**So R1 confirms the diagnosis and refutes the product conclusion drawn from it.** A sideline-first
v1 is a real and much stronger direction — 8x on the bar that matters — but it is **not** an
available product today, and the routes document should not be read as saying it is.

## What this changes

1. **The failure is one-dimensional and geometric, not an optimiser pathology.** R4/R5-style
   estimator work is aimed at the wrong target: it would have to improve a component that is
   *already* 5.4 cm.
2. **R3 and R7 survive** — they are downstream of arithmetic that just reproduced the measured
   failure boundary to 4% and the height scaling across five configs.
3. **SPEC §3's 10 cm bar is not one bar.** It is comfortably met in the cross-range direction at the
   median and unreachable along the range direction. Any renegotiation should be **per-direction or
   per-line**, not a single relaxed number: sidelines and the centre service line depend on the
   well-measured coordinate; baselines and service lines depend on the blind one.
4. **Bar A remains FAILED** (rule 2). Nothing here re-opens it.
