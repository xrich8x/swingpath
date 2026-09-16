# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (2026-09-16) H1 HIDDEN-BOUNCE BRIDGE (RESUMED after kill at start)

Spec = docs/evidence/swingvision-teardown.md s4 + lead addendum. MEASUREMENT, no tuning.
Deliverables: tools/hidden_bounce_bridge.py + tests; docs/evidence/hidden-bounce-bridge.md;
STATE row; commit master, DO NOT PUSH. Suite baseline 713 passed 4 skipped.
Arms G0/G9/G24 (+ audio sensitivity t*=t_true+N(0,.15fr)). Bar-A config, seed 0, n=500.
Bands near<=12 (PRIMARY) mid 12-20 far>20 by bounce range from camera.
Precursor FIRST: share >=5 in-frame post-bounce obs per band (<60% overall -> R6 dies).
PRIMARY near G9 med <= 1.5x G0; SECONDARY G24 <= 3x G0; KILL G9 > 3x G0.
Report SPEC6: near G9 within 10cm, G24 within 25cm vs 90%.
LEAD ARM (descriptive, no bar): near-line population (rejection-sample to within .30 m of
singles line, seed 0), >=150 within 10cm; IN/OUT correctness in 10cm & 30cm bands, Wilson 95%,
H1 AND 2D control; unfittable = wrong.
Do NOT add perturbed-calib / corrupted-edge arms - name as next.

## STATE
- [ ] read rig sources (synth_truth, mono3d_ceiling, numpy simulator, R1 decomposition)

## P1 (DONE, committed) key results kept for reference
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
