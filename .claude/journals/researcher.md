# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-15 — P1 MONOCULAR-3D ROUTES (surprising-result read, pre-pm)

Deliverable: ONE file `docs/evidence/monocular-3d-routes.md`. A RANKED list of candidate
routes from the 2.2 cm noiseless estimator to one that survives 2 px noise. Per candidate:
(1) what it is; (2) WHAT PINS THE DEPTH (rule 7 — mandatory, no answer = not a candidate);
(3) a pre-registerable bar measurable on `tools/mono3d_ceiling.py` + `tools/synth_truth.py`
with config + pass condition, cheap ranks higher; (4) falsifier + cost if wrong; (5) open
or closed w/ CLOSED.md row.
Three specific asks: (a) SPEC §5 depth-from-ball-size (6.7 cm) — real channel or arithmetic
that cannot survive its own measurement error? want back-of-envelope px subtended at
5/12/23 m + d(depth)/d(radius px). (b) bounded/parsimonious spin (`bridge.py:211
_spin_parsimonious`) — principled or a knob? (c) IS 90%/10 cm reachable AT ALL monocular?
A well-argued NO is more valuable than an optimistic list.
BARRED: detector work (rule 6 + bar E), pose/occlusion (§6/§9 tossed + oracle p0 fails 5x),
second camera/stereo/network, court auto-detection, re-running bar A.
NO code. NO STATE row. NO SPEC edit. Separate measurement / published / my-arithmetic.

## DONE — 2026-09-15, ~12 tool calls. If restarted: the work is FINISHED, just report it.

Written: `docs/evidence/monocular-3d-routes.md` (7 sections + ranked table).
Memory: `.claude/agent-memory/researcher/monocular-3d-geometry.md` + MEMORY.md index line.
Nothing outside the allowlist. No STATE row, no SPEC edit, no code, no subagent, no commit.

REPORT LINES: rank order R1 error-decomposition (free) > R2 fit-covariance abstention >
R3 geometric capability map > R4 MAP fit w/ 2D control as prior > R5 penalised spin >
R6 joint pre+post-bounce arcs (precursor-gated) > R7 4K (partly undecidable under rule 6).
Q3 = NO for down-court at 1080p/3 m; YES for lateral. Renegotiate COVERAGE, not 10 cm.

## STATE — ANALYSIS DONE, arithmetic below is the spine of the deliverable.

READ: P1 evidence, SPEC, measure/CLOSED, ball/CLOSED, mono3d_ceiling.py, synth_truth.py,
trajectory_fit.py (fit_arc full), bridge.py:180-260 (_spin_parsimonious CONFIRMED at :211,
min_gain 0.30 / max_rpm 3500), gen_synth_camera.draw_launch.

### THE ARITHMETIC THAT CARRIES THE WHOLE ANSWER (mine, re-derivable in 3 lines)
P1 config: 1920 wide, hfov 100 deg -> f = 960/tan(50) = **805.5 px**. mount h=3.0 m,
setback 6.0 m, so the far baseline is D = 6 + 23.77 = **29.77 m FROM THE CAMERA**.
Ground point at range D: row offset below horizon = f*h/D. Exact:
  |dD/dv| = (D^2 + h^2) / (f*h*sec^2(theta-phi)),  sec^2 <= ~1.9 at frame edge (vfov 67.7)
So ~D^2/(f*h) = D^2/2416.5 m per pixel:
  D=10 m -> 4.1 cm/px | D=15 -> 9.3 | D=20 -> 16.6 | **D=29.6 (far baseline) -> 36 cm/px**
**10 cm at the far baseline = 0.28 px of vertical image error (0.53 px with the sec^2 relief).**
Break-even range where 10 cm == 1 px: **D_1px = sqrt(0.1*f*h) = sqrt(241.6) = 15.5 m from
camera = 9.5 m past the near baseline.** P1's measured GOOD-fit median bounce depth is
**9.85 m** down-court. Independent arithmetic reproduces the measured split. This is the
finding: the failure is GRAZING GEOMETRY, and it caps ANY estimator, because z=0 at the
bounce is already the strongest depth pin rule 7 permits.
Scaling: capability ~ sqrt(f*h). Whole court to 10 cm needs f*h >= D^2/0.1 = 8862 px*m.
Framing doubles width at setback S needs f <= 175*S. h=3,1080p: NO setback works.
h=6 m needs S in [12.6, 45] m. 4K (f=1611 @100deg) + h=5.5 m works. 1080p+3 m does not.

### BALL SIZE (SPEC 5 / bar G) — KILLED ON PAPER, no run needed
Apparent diameter s = f*d/Z, d=0.067. f=805.5: Z=5 -> 10.8 px; 12 -> 4.5; 23 -> 2.35;
29.6 -> 1.82. Depth from size: **dZ/Z = -ds/s — SCALE FREE, focal length cancels.**
10 cm at Z needs fractional size precision 0.1/Z: 2.0% @5 m, **0.83% @12 m, 0.43% @23 m**.
In px that is 0.22 / 0.037 / 0.010 px of DIAMETER. Motion blur: 30 m/s at 60 fps = 0.5 m/frame
= 34 px smear at 12 m (8 px even at 1/250 s shutter) vs a 4.5 px ball. Plus memory:
int8 quantisation moved blob AREA not peak. VERDICT: not a depth channel; at best a weak
soft prior (order +/-1-3 m), and testing it on the rig would grade OUR OWN noise model.

### SPIN VERDICT
BOUNDED spin = a knob (and creates boundary optima that break Jacobian covariance).
PENALISED spin (ridge lambda|omega|^2, lambda from a PUBLISHED spin distribution) =
principled. _spin_parsimonious is the crude 0/1 special case. Lit: Nadal avg 3200 rpm,
peak 4900; Federer slice 5300 (press/Hawk-Eye, not peer-reviewed). draw_launch draws
|omega| <= ~3700 rpm -> a bound at 3500 WOULD BE THE ANSWER KEY. Must source externally.

### RANKED ROUTES (final order)
A1 fit-COVARIANCE abstention (res.jac -> bounce 1-sigma). SPEC 3 mandates it, NEVER measured,
   reproj r=0.159 is the broken proxy not the covariance. Cheapest, highest value.
A2 geometric capability map from the four-tap (D_1px above). Pure arithmetic, no ML, free.
B1 MAP fit: population priors on (p0,v0,omega) + 2D-control bounce prior. 2D BEATS 3D at
   >=1 px, so 3D is discarding the incumbent.
B2 penalised spin (subset of B1, testable alone).
B3 joint pre+post-bounce arcs sharing a z=0 bounce point. NOT the CLOSED bounce_hypothesis
   rows (those are the 2D Kalman smoother). Needs rig extension past the bounce.
C1 4K capture (f x2) — may SELF-CANCEL if px noise scales with blob size.
D  dead: ball-size, zero spin, pose/oracle p0, aero refinement, reproj gate, detector work.

### ANSWER TO Q3
NO — not across the whole court at 1080p from a 3 m mount. YES over a computable near band.
The renegotiation is over COVERAGE/REFUSAL RATE or CAPTURE SPEC, not over 10 cm.

## LOG

- 2026-09-10 prior task DONE: docs/evidence/innovation-gate-noise-calibration.md.
- 2026-09-15 new task started; journal rewritten. P1 evidence file read in full.
