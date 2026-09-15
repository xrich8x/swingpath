# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (2026-09-12) P1 MONOCULAR 3D CEILING ON SYNTHETIC TRUTH

MEASUREMENT ONLY. Do NOT tune anything to reach a bar. Deliverables:
1. `tools/mono3d_ceiling.py` + tests under `tests/`
2. `docs/evidence/monocular-3d-ceiling.md`
3. one row in `docs/STATE.md`
4. commit to master, DO NOT PUSH.

Pre-registered bars (FIXED, do not move):
A PASS: >=90% of flights bounce within 10 cm @ noise 2.0px, dropout 0.30, 60fps, 3.0 m, hfov exact
B TIMING: >=90% within +/-1 frame, >=99% within +/-2. BRACKET: B1 (seg GIVEN, fit to true
  last in-air frame) AND B2 (withhold last 3 obs, extrapolate to z=0). PASS only if BOTH.
  B1 alone = PARTIAL (explicitly NOT a pass).
C KILL: perfect detections (noise 0, dropout 0) -> if 10cm rate <50% at EVERY height, monocular
  3D cannot reach SPEC 3. Report FIRED / NOT FIRED.
D HEIGHT: 10cm rate at 1.0/1.5/2.5/4.0/8.0 m, noise2/drop0.30/60fps. Premise HOLDS only if
  1.5 m within 10 points of 8.0 m.
E NOISE: 0/1/2/4 px at 3.0 m, descriptive. Output = the detector precision the 10cm bar demands.
F SELF-GRADING CONTROL: simulator cd & cl_max offset +20% and -20% from the fitter's, reported
  separately. FIRST report whether the two physics models already agree.
G SPEC 5 depth-from-ball-size: UNTESTED, rig emits (u,v) only. Say so.

Design calls from the lead (do not re-litigate): p0 FREE + physical_bounds=True is PRIMARY;
PAIRED arms (same seeded flights + same noisy pixels) vs the 2D ground-projection control in
synth_truth.measure; truth_fps=240 everywhere; non-converged/dropped count as FAILURES and the
rejects must be characterised.

## STATE - SWEEP LAUNCHED (background), writing evidence file while it runs

- [x] read CLAUDE.md / SPEC / rig sources
- [x] bar F premise check (see F1) -> premise TRUE, models agree exactly
- [x] refactor synth_truth (noisy_pixels + control_bounce_xy + cd/cl passthrough)
      PROVEN INERT: --keypoints yt_rally2 --n 120 --seed 7 JSON + stdout byte-identical
      before/after. Also pinned by test_the_two_arms_score_the_identical_noisy_pixels.
- [x] fit_arc gained an optional `dt` (default 2e-3 UNCHANGED) - the only speed lever
- [x] tools/mono3d_ceiling.py written
- [x] backend/tests/test_mono3d_ceiling.py - 7 passed
- [x] dt A/B (n=40, seed 0, paired): 2e-3 34.0 s/fit; 6e-3 11.8 s (2.9x) paired
      |delta| median 0.0014 m max 0.092 m; 1e-2 6.9 s median 0.0029 max 0.123 m.
      Median ERROR is 1.41 m, so a 1.4 mm shift cannot decide anything ->
      SWEEP RUNS AT dt=6e-3, and bar A gets re-verified at the shipped 2e-3.
      data/output/mono3d_ceiling/dt_ab.json
- [x] TRAP HIT + FIXED: first sweep launch CRASHED after finishing config 1's fits
      (25 min of compute lost) on `TypeError: Object of type float32 is not JSON
      serializable` for `true_t_b` - the truth grid is a float32 torch tensor.
      Fixed by float()-casting at source AND `default=float` on both json.dumps.
      SMOKE-TESTED at --n 14 before relaunching. Do this first next time.
- [x] SMOKE (n=12 presented, 3.0 m, 2 px, .30, 60 fps): 3D b1 median err 1.168 m,
      b2 2.131 m, 2D control 0.996 m, 0.0% within 10 cm on ALL THREE.
      Bar A is heading for a clear FAIL and 3D is NOT beating the 2D control.
- [ ] RUNNING (relaunched 2 h mark, OMP_NUM_THREADS=1): --suite all --n 500
      --workers 11 -> 17 configs, est 3-5 h.
      log C:\Users\richm\AppData\Local\...\scratchpad\sweep.log ; each config writes
      data/output/mono3d_ceiling/<tag>.json AS IT COMPLETES, so a kill loses <=1 config.
- [ ] bar A re-verify at dt=2e-3
- [ ] evidence md + STATE row + commit

## RESULTS AS THEY LAND (data/output/mono3d_ceiling/<tag>.json)
All: 1920x1080, 60 fps, truth_fps 240, hfov 100 exact, setback 6.0, n=500 sim,
seed 0, dt 6e-3, p0 free, spin free, physical_bounds. n = PRESENTED flights.
                          3D <=10cm  3D med  3D+/-1fr 3D+/-2fr 2D <=10cm 2D med
noise0px_3.0m/b1  n=441      71.4%   0.022 m   74.8%   79.4%    24.9%   0.367 m
noise1px_3.0m/b1  n=441      10.0%   0.959 m   34.5%   52.2%    15.4%   0.374 m
barA_noise2px/b1  n=441       6.1%   1.323 m   29.5%   46.0%     8.6%   0.553 m
barA_noise2px/b2  n=441       2.0%   2.639 m   11.3%   19.5%       "       "
noise4px_3.0m/b1  n=441       3.2%   1.663 m   22.2%   41.7%     4.1%   0.799 m
height1m/b1       n=441       1.1%   3.092 m   38.3%   61.7%     3.2%   1.979 m
height1.5m/b1     n=441       4.1%   2.479 m   34.2%   53.7%     4.5%   1.258 m
-> BAR A **FAIL** 6.1% vs >=90%.  BAR B **FAIL** (not even PARTIAL): B1 29.5/46.0,
   B2 11.3/19.5 vs 90/99.  nocross = 0 everywhere so far (every fitted arc reaches
   the ground); the failure is POSITION, not convergence.
-> THE HEADLINE: 3D is a 2.2 cm estimator on NOISELESS pixels and a 96 cm one at
   1 px - a 44x degradation for ONE pixel. From 1 px upward it is no better than
   (and at bar A slightly WORSE than) the 2D ground-projection control it would
   replace. The 10 cm bar demands SUB-PIXEL detector precision.
   Pace ~10 min/config -> 17 configs ~3 h; chain adds p0anchor + barA-verify@2e-3.

FIRST 8 FITS EVER RUN (3.0 m, noise 2 px, dropout .30, 60 fps, 1080p): rmse 1.3-2.0 px
against 2.0 px injected noise - a PERFECT image fit - with bounce errors of
0.32 / 1.24 / 1.49 / 2.31 / 3.39 / 7.88 / 10.30 m. Reprojection certifies NOTHING.

## FINDINGS (do not re-derive)

F1. BAR F PREMISE IS **TRUE** - the two physics models AGREE EXACTLY on every default:
    simulator_torch.py: MASS .057 RADIUS .0335 AIR_DENSITY 1.21 GRAVITY 9.81 CD_DEFAULT .55
    CL_MAX 1.0 CL_SAT 2.0.  physics/constants.py: MASS .057 DIAMETER .067 -> RADIUS .0335,
    AIR_DENSITY 1.21 GRAVITY 9.81 CD_DEFAULT .55; aerodynamics.DragModel.cd=CD_DEFAULT,
    LiftModel(cl_max=1.0, sat=2.0). Same CL law CL = cl_max*S/(sat*S+1), same accel form.
    ONLY differences: integrator step (synth_truth simulate_batch dt=2.5e-3 vs fit_arc
    _forward dt=2e-3) and that numpy simulate() BREAKS at the first z=0 crossing with
    bounces=0 (torch one integrates the full horizon). So bar F's "shared model" premise
    holds -> bar A on its own really is a perfectly-specified-model ceiling.
F2. numpy `simulate(..., bounces=0)` terminates EXACTLY at the interpolated z=0 crossing and
    records it in `bounce_indices`. So the fitted arc's ground intersection is just
    tr.pos[-1] / tr.t[-1] when bounce_indices is non-empty. No extra root-find needed.
    Consequence for fitting: Trajectory.sample() is np.interp -> CLAMPS past the crossing.
F3. fit_arc times are measured from p0 at t=0. synth_truth's truth grid also starts at the
    launch (t[0]=0), so absolute tm can be passed straight in and t_b is directly comparable.
F4. frames: physics frame X=length/Y=width-to-image-LEFT/Z=up; swingvision x=width,y=length.
    synth_truth.to_court_xy converts; it asserts the inverse of speedspin._to_framework_xy
    at startup. KEEP THAT ASSERT.
F5. rig defaults are 1280x720 and synth_truth documents --pixel-noise as "px @720p".
    SPEC 2 floors capture at 1080p, so the run is at 1920x1080 and the noise rungs are
    NATIVE px there. 2.0 px @1080p == 1.33 px @720p angular. Must be stated in the evidence.
F6. draw_launch: speed U(18,55) m/s, launch elev U(-5,22) deg, azim U(-8,8) deg,
    topspin U(-1500,3500) rpm, sidespin U(-1200,1200), p0 x U(0,2) y U(-3,3) z U(0.3,1.2).
    All inside fit_arc's physical_bounds box (p_lo [-6,-12,0], p_hi [30,12,6]).
F7. 12 CPU cores. fit_arc is scipy least_squares over a python-loop RK4 -> the run must be
    multiprocessed over flights or it will not finish.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- CARRIED FORWARD: tools/ and ball_physics/ are at the REPO ROOT, not under backend/.
