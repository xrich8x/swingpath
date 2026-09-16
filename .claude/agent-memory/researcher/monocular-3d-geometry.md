---
name: monocular-3d-geometry
description: The pinhole arithmetic that caps monocular bounce placement — down-court vs lateral error is D/h, depth-from-ball-size is dead on paper, and which P1 routes are already closed
metadata:
  type: project
---

# Monocular 3D — the arithmetic that caps it, and what P1 closed

**Established 2026-09-15** reading `docs/evidence/monocular-3d-ceiling.md` (P1). Full writeup:
`docs/evidence/monocular-3d-routes.md`. **Do not re-derive any of this.**

## THE ONE EQUATION

For a camera of focal length `f` px at mount height `h`, viewing a point on the ground plane at
range `D` from the camera, ONE PIXEL of image error is worth:

```
down-court  D² / (f·h)   metres        lateral  D / f   metres        ratio = D / h
```

Exact form `|dD/dv| = (D²+h²)/(f·h·sec²(θ−φ))`; the `sec²` is ≤ ~1.9 at the frame edge, so the
simple form is conservative by at most 2x.

**Break-even range where 10 cm == 1 px:  `D_1px = sqrt(0.1·f·h)`.**

At P1's config (1920 wide, hfov 100° → f = 805.5 px; h = 3.0 m; setback 6.0 m):
- far baseline sits at **D = 29.77 m from the camera**, where 1 px = **36 cm down-court / 3.7 cm
  lateral**. 10 cm down-court needs **0.28 px**.
- `D_1px` = 15.5 m from camera = **9.5 m past the near baseline**. P1's MEASURED good/bad fit split
  is 9.85 m vs 23.62 m down-court. **The arithmetic reproduces the measured failure boundary to 4%.**

**Consequences to reuse without re-deriving:**
- Whole court at 10 cm needs `f·h ≥ D²/0.1 = 8,862 px·m`. Framing the doubles width from setback S
  caps `f ≤ 175·S`. **At 1080p + 3 m mount NO setback works.** h=6 m works for S ∈ [12.6, 45] m.
  4K (f = 1611 @ hfov 100°) works at h ≈ 5.5 m.
- Capability scales as `sqrt(f·h)` — a WEAK lever. Doubling resolution buys only √2 of range.
- **Sideline calls are ~D/h ≈ 10x better conditioned than baseline calls.** P1 reports only the
  scalar `math.dist`, so this has never been separated. Decomposing it is free.

## DEPTH-FROM-KNOWN-BALL-SIZE (SPEC §5 / P1 bar G) — DEAD ON PAPER, no run needed

`s = f·d/Z` with d = 0.067 m. **`dZ/Z = −ds/s` — SCALE FREE, focal length cancels.**
10 cm at range Z needs fractional size precision `0.1/Z`: **2.0% @5 m, 0.83% @12 m, 0.43% @23 m**
= 0.22 / 0.037 / 0.010 px of diameter. Apparent diameters: 10.8 / 4.5 / 2.35 px.
Killed three ways: (1) a 30 m/s ball at 12 m smears **34 px at 60 fps** (8 px even at 1/250 s) vs a
4.5 px ball; (2) blob extent is radiometric not geometric — **int8 quantisation moved blob AREA, not
peak** (`coreml-ane-budget`); (3) an unavoidable ±0.5 px diameter floor is ±1.33 m of depth at 12 m.
**At best a weak soft prior (±1-3 m). Never a measurement channel.**
**Do NOT test it on the rig** — the rig emits (u,v) only, so a synthetic radius means inventing a
noise model and grading our own assumption (rule 1).

## PUBLISHED, and the transfer trap
- Vorobev, Prosvetov & Elhadji Daou, *Real-time Localization of a Soccer Ball from a Single Camera*,
  arXiv:2506.07981 (2025-06-09): **centimetre-level monocular 3D, CPU, real time — on 6K broadcast
  football footage with a 22 cm ball.** That is ~10x our `f·d` before long-lens framing. **Real, and
  it does not transfer.** Always quote it with that sentence.
- Ribnick, Atev & Papanikolopoulos, "Estimating 3D Positions and Velocities of Projectiles from
  Monocular Views", IEEE TPAMI 31(5):938-944, 2009 — the canonical proof that the monocular ballistic
  problem has a unique solution and an analysis of its local convexity. Identifiability was never the
  issue here; conditioning is.
- Spin ceilings (press/Hawk-Eye, ATP broadcast, NOT peer-reviewed): Nadal forehand avg ~3,200 rpm,
  peak ~4,900; Federer backhand slice ~5,300 = highest measured groundstroke. Cross & Lindsey is the
  peer-reviewed serve-spin reference. **All professional — an upper bound for amateur, the safe
  direction for a prior.**

## THE ANSWER-KEY TRAP IN THIS RIG (rule 1)
`tools/gen_synth_camera.py:36-50 draw_launch` draws speed U(18,55) m/s, elevation U(−5°,22°),
topspin U(−1500,3500) rpm, sidespin U(−1200,1200), p0_z U(0.3,1.2) m → |ω| ≤ ~3,700 rpm.
**`bridge.py:211 _spin_parsimonious` ships `max_rpm = 3500.0`.** Testing that value on this rig is
grading against the answer key. Any prior or bound must be sourced from the literature and reported
alongside the rig's draw.
Also: the flight population is UNIFORM, not a tennis distribution — it over-represents the fast,
lofted, far flights that fail, so 6.1% may be pessimistic for real rallies by an unknown amount.

## CLOSED BY P1 — do not re-propose
- **Any ball-detector gain** (bar E: zero noise still only 71.4%).
- **Pose / any launch anchor** (an ORACLE p0 still fails by 5x, median 0.29 m).
- **Zero/flat spin** (paired median 1.32 → 3.31 m; better on only 29.7% of flights).
- **Refining the aero model** (bar F: ±20% mis-specification, 1.1σ / 0.2σ — no effect).
- **Reprojection residual as a quality or abstention gate** (`corr = 0.159`, n=441; good 1.77 px vs
  bad 1.87 px). Note: the *covariance* `σ²(JᵀJ)⁻¹` is a DIFFERENT object and is still open.
- **Mining the non-converged fits** — only 19/441 and their median error (0.93 m) is BETTER than the
  converged population. There is no reject population to mine.
- **A hard spin bound as the fix** — acts on only 4% of fits and creates a boundary optimum that
  invalidates any Jacobian covariance. A smooth ridge penalty is the principled form.

## RULE-3 LOOKALIKE, flagged so it is not mis-killed
A joint pre+post-bounce 3D arc fit is **NOT** `bounce_hypothesis`, `bounce_hypothesis v2 /
restitution_set`, or `bounce_reset` in `docs/ball/CLOSED.md`, nor STATE.md:170. **All four of those
are 2D Kalman SMOOTHER changes in `backend/swingvision/ball.py` with no 3D model.** Different
subsystem. It is also the only candidate route that ADDS observations rather than re-conditioning.

## HIDDEN BOUNCES (2026-09-16, `docs/evidence/swingvision-teardown.md`)
- A bridged bounce is at best as good as a seen one: allowed inferred-pixel error for 10 cm is
  `0.1·f·h/D²` = 6.7 px @6 m, 2.4 @10, 1.7 @12, 0.6 @20. Near player hides `Dp..Dp·h/(h−H)` (2.5·Dp
  at h=3) = near court, the forgiving zone. Net tape puts far service boxes BEHIND THE MESH at h=3
  (7.8 m past net); clearing far service line needs h ≥ 3.47 m (centre) / 4.06 m (posts).
- Phone mic array = bearing only (~3°/sample), no range. Audio is a CLOCK, not a locator.
- Cheapest test = 2D two-sided quadratic intersection with G0/G9/G24 hidden frames, near band primary
  (bar: G9 ≤ 1.5×G0; kill > 3×). Needs rig to emit post-bounce frames.

## RIG FACTS worth not re-reading the code for
- **`synth_truth.simulate` uses `simulator_torch` = FLIGHT ONLY.** Post-bounce truth needs numpy
  `ball_physics/tennis_tracker/physics/simulator.py simulate(bounces=N)` (`_bounce` e_n/e_t/mu, :59).
- `tools/mono3d_ceiling.py` scores `math.dist` only (line ~293) — no error decomposition exists yet.
- Per-flight JSONs `data/output/mono3d_ceiling/*.json` (~13 MB) are **gitignored, not committed**;
  only `mono3d_ceiling_summary.json` is. Regenerating one config is a seeded ~1,050 s run.
- The rig runs `bounces=0` and truncates the track at the true bounce, so there is NO post-bounce
  data today.
- `HFOV_DEG = 100.0`, `SETBACK_M = 6.0` in `tools/height_curve.py:60-61`.
