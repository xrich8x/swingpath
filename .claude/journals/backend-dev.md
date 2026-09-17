# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - DONE (2026-09-17) CP1 STAGE 1 - committed, not pushed; stage 2 NOT started - seeded whole-court line fit (R1)

H1 hidden-bounce bridge (previous TASK) is PARKED: founder ruling 2026-09-17, court only.

Spec = docs/evidence/court-precision-routes.md s7 (CP1) + s5 R1 + LEAD ADDENDUM (end of file).
Deliverables: tools/court_fit_cp1.py + backend/tests/test_court_fit_cp1.py;
docs/evidence/court-fit-cp1.md; ONE STATE row; commit master, DO NOT PUSH.
Suite baseline 713 passed 4 skipped. Reuse C1 (court_map_ceiling.lines, true_projector,
height_curve.frame_the_court) by IMPORT.
Stage 1 ONLY: renderer, x265 harness, R1 fit, 3 controls, arm P + arm A3 (codec off).
Bars: PASS arm P every line p90<=5cm on L (where visible) AND M (all). KILL line p90>10cm.
INDET 5-10. Route kill: A3 passes but P fails on far lines (codec erased profile) -> R3.
400 trials/arm; 200 only if 400 would exceed 60 min, decided HERE before its scored run.

## PRE-DECLARED (written before any code, 2026-09-17)
Control readings (spec ambiguous -> my reading, fixed now):
- C1ctl: zero noise, zero distortion, zero seed noise, codec OFF, clutter OFF; PSF/contrast
  still drawn. n=20. PASS = max over trials of every line, BOTH readouts, < 5 mm.
- C2ctl: noise ON, codec OFF, distortion OFF, clutter OFF, seed sigma 14.78 (as P). n=400.
  PASS = every line p90 <= 2 cm on BOTH readouts. Seed-0 variant = descriptive only.
- C3ctl: render principal point shifted +0.10 px vertically, scoring truth UNshifted.
  (a) C1ctl settings, n=20: every trial far-baseline L signed vertical offset in 0.10+-0.02.
  (b) C2ctl settings, n=100, paired (same seeds) minus unshifted run: mean diff in
      0.10+-0.02. BOTH must pass.
Dev seeds for building/debugging: >= 1000. Scored runs: seed 0. Internals FROZEN at a
commit before the scored runs; commit hash stamped in output.

## DESIGN (R1 internals)
Scene (truth AND fitter's regulation model): positions to OUTSIDE (ITF). Paint 5 cm:
 near BL y[0,.05]; far BL y[23.72,23.77]; dbl L x[0,.05] R x[10.92,10.97];
 sgl L x[1.37,1.42] R x[9.55,9.60]; svc lines paint on the NET side of 5.485/18.285;
 centre svc x[5.46,5.51] y 5.485..18.285; centre marks 10 cm inside baselines.
 Colours: surface 95, run-off 80 (outside doubles), paint 95+C, C~U(60,160).
 Net: plane y=11.885, x in posts [-0.914,11.884], tape top parabola 1.07->0.914, 5 cm
 white tape (220), mesh cords 4 mm @ 4.45 cm dark (30), posts dark 10 cm. Back fence
 plane y=30.17 h 0..4 m dark (45) w/ rail + posts; roof trusses z=7..7.3 at several y;
 above-fence wall 150.
Render: truth cam = C1 true_projector geometry (roll 0, yaw 0) + Brown k1=-0.030,
 k2=+0.0056 in f-normalised coords (~30 px at horizontal edge, ~40 px at corner).
 Material coverage per pixel: 16x16 in FLAGGED pixels (projected feature edges dilated,
 whole net region, corner-grid material changes), 1 sample elsewhere. Maps cached per geometry.
 image = blur_sigma(base) + (S+C)*blur_sigma(paintcov); Gaussian-approx Poisson-Gaussian
 var = (3/128)*I + 1 (sigma 2 DN at 128); uint8. 30 frames.
Codec: Y plane as yuv420p (U=V=128, no range conversion), libx265 main, 60 fps,
 16M ABR, keyint 60; decode -> Y; average 30 frames.
Fitter: cam params (Cx,Cy,Cz,yaw,pitch,roll,f,lambda) pp fixed centre; division model
 in r normalised by half-diagonal 1101.5 px. Seed f closed-form from corner homography.
 Passes: 1 near lines + near sideline halves (W 40), 2 + far sideline halves + far centre
 (W 12), 3 + far svc + far BL (W 6), 4-5 all (W 3) final GN on raw pixels.
 Window per station also capped at 0.45 x predicted distance to nearest OTHER predicted
 feature (incl. net tape) = assignment rule. Profile model: surface + a*blurred box
 (width = model-projected paint width) + rho*blurred step at outer edge (boundary lines),
 sigma global from near lines. Camera fit: least_squares, robust loss.
Readouts: M = C1-style back-project true pixel via fitted cam, perp ground err, worst of
 11. L = straight-line fit to measured centre stations of each half in fitted-undistorted
 space, shifted by model half-width; ground err = root of signed image dist along the
 true line normal. Capture = L image err > 2 px at any of 11 pts.
 lambda* = best division fit to truth Brown with f fixed (for k1 error).

## STATE
- [x] read spec, C1, height_curve; ffmpeg libx265 present; numpy 2.5 scipy 1.18 cv2 4.13, py3.14
- [x] renderer + coverage cache (tools/court_fit_cp1.py drafted; cam == C1 projector exactly; Brown edge 30.0 px; lam* -0.04231; cov P build 28 s, 153k flagged px; render viewed OK)
- [ ] codec harness
- [ ] fitter
- [ ] tests
- [ ] controls (C1ctl, C2ctl, C3ctl)
- [ ] freeze commit; timing -> 400/200 decision per arm
- [ ] arm P, arm A3
- [ ] evidence doc, STATE row, memory, commit

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- CARRIED FORWARD: tools/ and ball_physics/ are at the REPO ROOT, not under backend/.
- CARRIED FORWARD: smoke-test at small n before any long run (float32 JSON crash, 25 min).
- H1 (ball) state before park: nothing built beyond reading; P1 results live in STATE.
- 2026-09-17 draft tool written (renderer+codec+fitter+readouts+arms in one file). Next: ctl1 smoke.
- WORDING RULING (coordinator, founder 2026-09-17): court is found AUTOMATICALLY, never taps.
  Call the perturbed 4 corners "a rough first guess, as an automatic court detector would
  supply it". Keep sigmas (14.78 primary; 1/4 stage 2). Note repo auto-detector corner error
  ~6.4 px@640 ~19 px@1920 is the same order. NO finger/tap framing anywhere (tool, output, doc).
- DEV FINDING 1 (ctl1 dev seed 1000, first draft): far BL biased -0.13 px on a NOISELESS image
  (M 2.6 cm, L 4.6 cm); far svc line 0 stations; far centre svc 5 stations.
  Cause A: a 0.14 px paint band ON the run-off/surface step is first-order DEGENERATE with a
  step shift (apparent edge shift ~ a*w/rho ~ 1 px) -> with paint amplitude free, any shape
  error biases c by tenths of px (exact-profile fit also -0.20..-0.25). Cause B: the model
  lacked pixel-box integration. Cause C: fixed 16x16 grid quantises a horizontal 0.14 px band
  (3 samples = 0.1875 vs true 0.1397 coverage) and would quantise ctl3's 0.10 shift to 0.0625.
  Cause D: at h=3 the net tape is only ~3.4 px from the far service line (tape bottom 407.3,
  svc 410.7 at centre) -> exclusion rule removed every station.
  FIXES (design, before any scored run): (1) boundary lines use a = kappa*rho with
  kappa = paint/step ratio measured on the wide near baseline (veil-invariant); internal
  lines keep a free. (2) exact pixel-footprint x Gaussian profile (Phi2 closed form).
  (3) render with stratified JITTERED 16x16 samples (still 16x16 area supersampling).
  (4) tape measured first each fine pass, then modelled as a linear nuisance (box + veil
  step) in nearby line profiles; tape caps windows by assignment frac only. (5) min stations
  per half 4, fine spacing 4 px. (6) net base line added as a crossing feature.
- kappa sign bug fixed (step basis oriented surface-side=1) -> all sidelines ~0.1 mm in ctl1.
- DEV FINDING 2 (ROOT CAUSE, forces a DEVIATION from s7 wording): s7 says "area-sampled 16x16,
  THEN Gaussian PSF". Literal order (box-sample to pixels, then discrete blur) makes a line
  narrower than a pixel render IDENTICALLY wherever it sits inside its row (per-column paint
  centroid std = 0.0 for far svc / far BL) -> sub-pixel position is ERASED by the renderer,
  not by physics; measured bias +0.07 near svc, -0.10..-0.17 far svc, +0.09 far BL with the
  TRUE camera. Real optics blur BEFORE pixel integration. FIX: render = PSF (x) pixel box on
  a 4x grid built from 16x16 jittered point samples (box sums, stride 4), Gaussian on the 4x
  grid, sampled at pixel centres. Sigma drawn from an 11-point grid 0.70..1.20 (cached maps).
  Still 16x16 area supersampling; order = optics then sensor. MUST be stated in evidence.
- render v3 (1/4 grid) cut true-cam biases to 0.005-0.016 px, but the pixel BOX sampled on the
  1/4 grid then discrete-Gaussian leaves a phase-dependent kink dipole (+0.007 near svc, +0.016
  far svc; resid rms 0.04-0.07 DN). Asymmetric-edge station model fixed near BL (-0.005->0.000).
  -> render v4: smooth separable kernel K=box(x)G applied to the 1/16 jittered indicator at
  stride 16 (midpoint rule: only adds symmetric h^2/12 blur, no position bias).
- render v4 + asymmetric edges + normal/edge intersection: TRUE-cam biases all <=0.0012 px.
  exclusions: centre marks by distance; crossing test for angles >=10 deg, parallel cap <30
  (far doubles sideline meets far BL at 29.6 deg and escaped both). ctl1 trial now ~mm-level.
- far BL per-station scatter 0.023 px on a NOISELESS image = renderer MC noise (0.09 DN rms
  band, concentrated on edge rows), GN converged. KAPPA SENSITIVITY: kappa +5% -> far BL
  -0.034 px (~1.3 cm) -> evidence must list "paint contrast identical near/far" as flattering.
  -> adding 2x2 jitter per 1/16 cell (sub=2, 32x32 effective) to halve render noise.
- RESUMED after kill (2026-09-17). sub=2 render built (117 s ctl geometry); far BL noiseless
  per-station sd 0.023 -> 0.006 px. Next: ctl1 dev smoke (seed 1000, n=6), then P geometry build.
- ctl1 dev n=6: M passes (far BL p90 4.1 mm) but L far BL 15 mm / far svc 19 mm. Cause: uint8
  rounding of NOISE-FREE frames = undithered structured error. Fix: noise=False yields float
  frames (no quantisation) - my reading of "zero noise"; state in evidence.
- DEV (seed 1000): ctl1 n=12 worst 0.6 mm; ctl2 n=30 worst p90 6.2 mm (far svc L); ctl3a n=10
  recovered +0.1000 px. All would pass. Next: P dev smoke (codec) n=10.
- x265 plain ABR overshot (25.9 Mbps on 30 frames) -> added vbv-maxrate/bufsize 16000 ->
  18.1 Mbps achieved (dev). P dev n=10 (seed 1000): every line PASS, worst L far BL 3.9 cm p90.
- Tests: backend/tests/test_court_fit_cp1.py 8 tests; suite 721 passed 4 skipped (713+8).
- TRIAL-COUNT DECISION (before any scored run): P measured 18.4 s/trial p50, 5 workers ->
  ~26 min at 400 < 60 -> P = 400. A3 (no codec) faster -> 400. Controls: ctl1 n=20,
  ctl2 n=400, ctl3a n=20, ctl3b n=100 (paired with ctl2 trials 0-99, seed 0), ctl2s0 n=100
  descriptive. All scored runs seed 0. FREEZE commit next, then scored runs.
- SCORED controls launched (bg, seed 0, commit 4ac52fc): ctl1 20, ctl3a 20, ctl2 400, ctl3b 100, ctl2s0 100 -> data/output/court_fit_cp1/<arm>_seed0_n<n>.json + log_<arm>.txt
- SCORED ctl1 n=20: max M 0.12 mm, max L 0.57 mm -> PASS (<5 mm). ctl2 n=400: worst p90 5.6 mm (far svc L), 0 failures -> PASS (<=2 cm). 665 s.
- SCORED ctl3a n=20: L offset 0.0997..0.1001 all in 0.10+-0.02 PASS; ctl3b paired n=100: L mean 0.0993 sd 0.0023 (M 0.1003) PASS. ctl2s0 (descr) far svc L p90 5.3 mm. ALL CONTROLS PASS -> launching P (6 workers) then A3 (10 workers), seed 0, n=400.
- SCORED P n=400 (1363 s, 0 failures): ALL 14 lines PASS both readouts. worst L p90 far BL 3.58 cm, far svc 3.42 cm; M p90 far BL 0.97 cm. capture 0. kbps p50 19.9k. Waiting A3.
- SCORED A3 n=400 (676 s, 0 failures): ALL PASS; far BL L p90 0.93 cm, far svc 0.74. Route kill NOT fired (P passes). Codec costs far BL L +1.2 cm paired median; kappa est +1.4% under codec. NEXT: evidence doc, STATE row, memory, commit.
- DONE: evidence docs/evidence/court-fit-cp1.md, STATE row, memory file; committed (no push). VERDICT: P PASS all 14 lines; route kill not fired.
