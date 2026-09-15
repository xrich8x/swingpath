# P1 — the monocular 3D ceiling, measured for the first time

**Run 2026-09-12/15. `backend-dev` built the instrument and ran the sweep; the lead recomputed
every headline in this file directly from the raw per-flight JSON rather than from the agent's own
summary.**

**WHAT EVERY NUMBER HERE WAS MEASURED AGAINST:** EXACT simulated truth — the interpolated `z=0`
crossing of a drag+gravity+Magnus flight (`synth_truth.truth_of`). No human labels, no HUD, no
model output, and nothing scored against another estimator.

**WHAT PINNED THE DEPTH** (hard rule 7 — a single camera does not observe depth, it imposes it):
- **the 3D arm** — known `g = 9.81`; drag+Magnus with CD/CL fixed at the fitter's defaults; EXACT
  hfov; 6-DOF camera pose from four known doubles corners (regulation court dimensions);
  `fit_arc`'s `physical_bounds` box; and the ground plane `z = 0` for the intersection.
- **the 2D control arm** — `z = 0` assumed for EVERY observation, plus the four-corner homography
  onto the regulation doubles rectangle.

**Rig:** 1920x1080, 60 fps, `truth_fps` 240 (so the truth grid is an exact decimation and no frame
rate is flattered), hfov 100° exact, setback 6.0 m, n = 500 simulated flights per configuration
(~441 presented), seed 0, `p0` free, spin free, `physical_bounds` on. Arms are **paired**: the 3D
fit and the 2D control score the identical flights and the identical noisy pixels, which is pinned
by a test rather than trusted.

---

## THE VERDICTS

| Bar | What it required | Result | Verdict |
|---|---|---|---|
| **A** | >=90% of flights within 10 cm @ 2 px, dropout .30, 60 fps, 3.0 m | **6.1%** | **FAIL** |
| **B** | >=90% within +/-1 frame, >=99% within +/-2 | B1 29.5 / 46.0, B2 11.3 / 19.5 | **FAIL** — not even PARTIAL |
| **C** | KILL if <50% at 10 cm at EVERY height with PERFECT detections | 59.6-72.1% | **NOT FIRED** |
| **D** | premise holds if 1.5 m is within 10 points of 8.0 m | gap 5.9 pts (9.2 pts perfect) | **HOLDS** — but see below |
| **E** | descriptive: the detector precision 10 cm demands | see the noise axis | reported |
| **F** | simulator aero offset +/-20% from the fitter's | +2.0 pts (1.1σ), +0.3 pts (0.2σ) | **no detectable effect** |
| **G** | SPEC §5 depth-from-ball-size (6.7 cm) | rig emits (u,v) only, no radius | **UNTESTED** |

**Bar A is FAILED and stays failed (rule 2).** Nothing below re-opens it.

### Bar A — FAIL, by a factor of fifteen

**6.1%** of flights land within 10 cm, against a **>=90%** bar. Median error **1.32 m**, p90
**6.48 m**, worst **15.2 m** on a 23.77 m court.

- **The integrator shortcut is not the cause.** The sweep ran at `dt = 6e-3` for speed; re-run at
  the shipped `dt = 2e-3` the answer is **5.9%**. The 3x speedup did not buy the verdict.
- **It is not a convergence artefact.** `n_no_ground_crossing = 0` — **every** fitted arc reaches
  the ground. 19 of 441 fits did not converge, and counting them as failures (as pre-registered)
  moves the headline by **0.05 points** (6.12% presented vs 6.07% on all-truth). **The failure is
  POSITION, not convergence.**

### Bar B — FAIL, and the bracket did its job

Pre-registered as a bracket because the rig truncates the track at the true bounce, which leaks the
segmentation:

| Arm | Within +/-1 frame | Within +/-2 frames | Bar |
|---|---|---|---|
| **B1** — segmentation GIVEN (upper bound) | 29.5% | 46.0% | 90% / 99% |
| **B2** — last 3 observations withheld | 11.3% | 19.5% | 90% / 99% |

**Both fail, so the verdict is FAIL rather than PARTIAL.** Timing is also **biased, not merely
noisy**: mean error **+3.66 frames LATE**, |error| median 2.35 frames, p90 **12.7 frames**. The
fitted arc systematically crosses the ground later than the truth.

### Bar C — NOT FIRED, and this is the most important line in the file

With **perfect detections** (noise 0, dropout 0) the 10 cm rate is **59.6-72.1% at every height**,
far above the 50% kill threshold, with a **median error of 2.2-3.1 cm**:

| Mount | 10 cm rate | Median err | p90 |
|---|---|---|---|
| 1.0 m | 64.9% ± 2.3 | 3.1 cm | 2.69 m |
| 1.5 m | 68.8% ± 2.2 | 2.9 cm | 1.40 m |
| 2.5 m | 72.1% ± 2.1 | 2.8 cm | 0.86 m |
| 3.0 m | 71.7% ± 2.1 | 2.7 cm | 1.15 m |
| 4.0 m | 70.3% ± 2.2 | 2.4 cm | 1.79 m |
| 8.0 m | 59.6% ± 2.3 | 2.2 cm | 3.92 m |

**So the geometry and physics are CORRECT and monocular 3D is not intrinsically incapable of
SPEC §3. The spec is NOT automatically renegotiated.** This is also the internal control that makes
the whole run credible: a frame-conversion error, an inverted `g` or a broken ground intersection
would fail *here too*, and this project has shipped both of those bugs before. A 2.2 cm median on
noiseless pixels says the estimator is right and the conditioning is wrong.

### Bar E — the noise axis, and the answer is not the one the bar expected

| Pixel noise | 3D: 10 cm rate | 3D: median | 2D control: 10 cm | 2D control: median |
|---|---|---|---|---|
| **0 px** | **71.4%** | **2.2 cm** | 24.9% | 37 cm |
| 1 px | 10.0% | 95.9 cm | 15.4% | 37 cm |
| 2 px | 6.1% | 132.3 cm | 8.6% | 55 cm |
| 4 px | 3.2% | 166.3 cm | 4.1% | 80 cm |

**ONE PIXEL OF NOISE COSTS A FACTOR OF 44 IN MEDIAN ERROR (2.2 cm -> 95.9 cm).** That is the
finding.

**What detector precision does the 10 cm bar demand? The question has no answer, and that is the
useful result.** Even at **exactly zero** pixel noise the rate is 71.4%, short of 90%. **Sub-pixel
precision is necessary but not sufficient — no detector improvement whatsoever reaches bar A with
this estimator.** This independently re-confirms rules 5 and 6 from a completely new direction:
detector work cannot deliver this bar.

**AND THE 3D FIT LOSES TO THE INCUMBENT.** At every noise level from 1 px up, the 3D arm is worse
than the 2D ground-projection estimator that ships today — on both the 10 cm rate and the median.
It wins decisively only on noiseless pixels. Whatever replaces the 2D path has to beat it at the
noise the detector actually has, and this configuration does not.

### Bar D — the premise HOLDS, but it passes the letter and fails the spirit

| Mount | 3D 10 cm rate | 3D median | 2D control |
|---|---|---|---|
| 1.0 m | 1.1% | 3.09 m | 3.2% |
| 1.5 m | 4.1% | 2.48 m | 4.5% |
| 2.5 m | 6.6% | 1.62 m | 6.1% |
| 4.0 m | 6.8% | 1.07 m | 12.0% |
| 8.0 m | 10.0% | 0.64 m | 15.4% |

1.5 m vs 8.0 m is **4.1% vs 10.0% — a 5.9 point gap**, inside the pre-registered 10 points, so
**CLAUDE.md's founding premise ("works regardless of mount height") HOLDS** by the criterion fixed
before the run. At perfect detection the gap is 9.2 points and it also holds.

**READ IT HONESTLY: at bar A's noise the premise holds because EVERY height fails**, 1.1% to 10.0%
against a 90% bar. Height-independence among uniformly failing configurations is not the
reassurance the premise was reaching for. The median error still moves **4.8x** across the range
(3.09 m -> 0.64 m), so height matters a great deal to how wrong you are — just not to whether you
clear 10 cm, because nothing does.

**A second-order result worth keeping:** at perfect detection the highest mount has the **best
median (2.2 cm) and the WORST 10 cm rate (59.6%) and p90 (3.92 m)**. A high mount sharpens the
typical case and fattens the tail.

### Bar F — the self-grading control, and the worry does not bind

The simulator and the fitter share a physics model — **verified exactly** (`MASS .057`,
`RADIUS .0335`, `AIR_DENSITY 1.21`, `GRAVITY 9.81`, `CD 0.55`, `CL_MAX 1.0`, `CL_SAT 2.0`, same
CL law, same acceleration form; the only differences are the integrator step and that the numpy
`simulate()` stops at the first `z=0` crossing). So bar A on its own is a ceiling under a
**perfectly specified model**, not an accuracy — which is exactly why bar F was required.

| Simulator aero | 10 cm rate | Median | vs matched |
|---|---|---|---|
| matched (0%) | 6.1% ± 1.1 | 1.32 m | — |
| **+20%** | 8.1% ± 1.3 | 1.42 m | +2.0 pts, **1.1σ** |
| **-20%** | 6.4% ± 1.2 | 1.67 m | +0.3 pts, **0.2σ** |

**Mis-specifying the physics by ±20% has no detectable effect.** Neither offset is significant, and
both are nominally *better* than matched. **So bar A's 6.1% is not flattered by the shared model** —
the error is dominated by monocular depth ambiguity, not by how well the aerodynamics are known.
That makes the ±20% arms a stronger result than a ceiling caveat: at this noise level the physics
model is not the binding constraint, so refining it is not a route.

*Caveat: the arms are not perfectly paired — changing the simulator's aero changes which flights
bounce inside the 2 s horizon, so n is 445 / 438 / 441 rather than identical.*

### Bar G — UNTESTED, and it must not be read as covered

SPEC §5's **depth-from-known-ball-size** (6.7 cm diameter) is **not exercised by this run**. The rig
emits `(u, v)` only, with no apparent radius — verified. **No number in this file covers §5**, which
is the channel the spec itself calls the weakest part of the whole system. Carried from the shelved
int8 work, and directly relevant: **quantisation moved blob AREA, not peak** — apparent size is the
fragile quantity, so §5 deserves its own measurement rather than an inherited assumption.

---

## WHY IT FAILS — the diagnosis

**Reprojection residual is very nearly useless as a quality signal, and it is now quantified.**
Across 441 bar-A fits, `corr(rmse_px, err_m) = 0.159`. Fits landing **within 10 cm** have a median
reprojection of **1.77 px**; fits landing **beyond 10 cm** have **1.87 px**. The first eight fits
ever run returned **1.3-2.0 px rmse against 2.0 px of injected noise — a perfect image fit — with
bounce errors of 0.32 / 1.24 / 1.49 / 2.31 / 3.39 / 7.88 / 10.30 m.**

This is hard rule 7 measured rather than asserted. The rule previously rested on a single anecdote
(a 23.8x span error that passed its residual); it now has n=441 and a correlation coefficient.

**What separates a good fit from a bad one** — and it is the depth direction, exactly as the
monocular argument predicts:

| | GOOD (<=10 cm) | BAD (>10 cm) |
|---|---|---|
| launch speed | 26.8 m/s | 37.9 m/s |
| launch elevation | 0.06° | 7.72° |
| **bounce distance down-court** | **9.85 m** | **23.62 m** |

Slow, flat, near bounces are fittable. Fast, lofted, far bounces are not — and the far baseline is
precisely where a line call matters.

**The rejects are unremarkable, which is itself the finding** (rule 11). Only 19 of 441 fits failed
to converge, and their median error (**0.93 m**) is slightly *better* than the converged population
(**1.35 m**). Non-convergence is not the failure mode; there is no reject population to mine.

**The optimiser is absorbing pixel noise into unphysical spin.** Fitted spin has a p90 of **7,244
rpm** against a TRUE p90 of **3,116**, a maximum of **12,375 rpm**, and **4.1% of fits exceed
10,000 rpm** — against a real-world ceiling near 5,000. `fit_arc`'s own docstring predicted this
before the run: the optimiser "buys a cheap residual reduction by pinning all three components at
their bound (|omega| = 750*sqrt(3) rad/s = 12,405 rpm)". The observed maximum is that bound.

## The spin-zero diagnostic — PRE-REGISTERED, and it came back NEGATIVE

The unphysical-spin finding above suggests an obvious route: drop the three spin parameters and
stop the optimiser absorbing noise into them. **That was pre-registered before it ran**
(`.claude/journals/lead.md`, 2026-09-15), including the explicit condition that **whatever it
returned it could not un-fail bar A**, and the confound that `omega = 0` mis-specifies the physics
because the simulator really does apply Magnus at up to 3,633 rpm.

One variable changed — `spin_free: True -> False` — on the identical seeded flights and identical
noisy pixels:

| | 10 cm rate | Median | p90 | +/-1 frame | non-converged | wall |
|---|---|---|---|---|---|---|
| spin FREE (bar A) | 6.1% ± 1.1 | **1.32 m** | 6.48 m | 29.5% | 19 | 1050 s |
| **spin ZERO** | 3.9% ± 0.9 | **3.31 m** | 10.11 m | 11.1% | 0 | 138 s |

**It is WORSE, and the paired test is unambiguous.** The 10 cm rate difference alone is only 1.5σ,
but these are the same 441 flights, so the paired comparison is the right one: the median paired
error **rises 0.99 m**, and spin-zero is better on just **29.7%** of flights.

**So the bias half dominates the variance half. The Magnus term is carrying real signal**, and
removing it costs more than the noise absorption it prevents — even though that noise absorption is
demonstrably happening (4.1% of free fits pinned at the spin bound). The tempting fix is a dead end
in its flat form.

**What this does and does not license.** It kills *zero spin*. It does **not** kill a **bounded** or
**parsimonious** spin fit — `bridge.py:211 _spin_parsimonious` already implements the two-stage
policy `fit_arc`'s docstring recommends (fit spin-free, then accept spin only when it clearly earns
its residual), and that is a different mechanism from clamping spin to zero. **Untested here. It is
a hypothesis, not a plan**, and under rule 2 nothing in this paragraph softens bar A's FAIL.

*Two secondary observations kept because they are cheap: spin-zero converged on every flight (0 vs
19) and ran **7.6x faster**, both consistent with a better-conditioned but biased optimisation.*

## The secondary arm: an ORACLE launch anchor

Reported as a descriptive secondary because it needs information v1 does not have — and it is an
**oracle**, not an estimate: the anchor is the **exact true launch point**, `fix_p0` on the
simulator's own `p0`.

| | 10 cm rate | Median | p90 | +/-1 frame | +/-2 frames | non-converged |
|---|---|---|---|---|---|---|
| `p0` free (bar A) | 6.1% | 1.32 m | 6.48 m | 29.5% | 46.0% | 19 |
| **oracle `p0` anchor** | **16.8%** | **0.29 m** | **0.74 m** | **72.3%** | **88.4%** | **3** |

Anchoring the launch point improves the median **4.6x** and p90 **8.8x**, and is the single largest
lever found. **It still fails bar A by a factor of five.**

**The scope consequence, stated plainly: restoring pose would NOT rescue bar A.** SPEC §9 tossed all
pose, which is what removes any launch anchor from v1. This arm prices that decision — and shows
that even a *perfect* anchor, better than any pose model could deliver, leaves the 10 cm bar
unreachable. §9's removal is not what is costing this bar.

---

## WHAT THIS MEANS

1. **Bar A and bar B are FAILED. They stay failed.** No configuration found in this run reaches
   them, including one using information v1 has deliberately given up.
2. **Bar C did NOT fire, and that is the constructive half.** The estimator is a **2.2 cm**
   instrument on clean pixels at every mount height tested. The physics, the frames, the camera
   solve and the ground intersection are all correct. What fails is **conditioning**: an
   unconstrained nine-parameter monocular arc fit is exquisitely sensitive to pixel noise.
3. **The binding constraint is the ESTIMATOR, not the DETECTOR.** Zero pixel noise still yields only
   71.4%. No detector will deliver bar A. But **"just constrain the fit" is not a free answer** —
   the one constraint tested, zero spin, made it **worse** (median 1.32 m -> 3.31 m, paired). The
   surviving candidates are a *bounded* rather than removed spin, a multi-arc or multi-bounce
   constraint, or an independent depth channel such as SPEC §5's ball size (untested, bar G). All
   are hypotheses; none is measured.
4. **SPEC §3's 10 cm bar is not currently reachable by the method SPEC §5 mandates**, at the pixel
   noise a real detector has. That is a founder decision, not an engineering one, and it is the
   decision this measurement existed to inform.

## Reproducing it

**Committed:** `data/output/mono3d_ceiling_summary.json` — every per-configuration headline in this
file, 20 KB, so each number above is auditable in-repo without re-running anything.

**NOT committed:** the full per-flight results, `data/output/mono3d_ceiling/*.json` (~13 MB across
20 configurations, each carrying its own provenance block: tool, commit, python, platform, what it
was measured against, what pinned the depth, the full config, the camera solve, and both aero
models). `data/output/` is gitignored and git does not descend into an ignored directory, so the
`!data/output/*.json` exception does not reach a subdirectory. They are **exactly reproducible** —
every arm is seeded at `seed 0`:

```
cd backend && .venv/Scripts/python.exe ../tools/mono3d_ceiling.py --suite all --n 500 --workers 11
```

Budget ~3-5 h on 12 cores. `--suite report` re-prints the tables from whatever is already on disk.
