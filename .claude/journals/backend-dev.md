# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (2026-09-10) DIAGNOSTIC ONLY: gate noise calibration K1/K2/K3 + M1

DIAGNOSTIC ONLY. NOT authorised to build/ship/default-on any fix.
One instrumented pass over 3 TrackNet arms (am_hard_utr, yt_match40, yt_rally2),
one row per detection-bearing frame. Adjudicate 3 pre-registered kill conditions:
- K1: median d2 on gold-real ACCEPTED frames. In [0.9, 2.2] -> R premise DEAD.
  Report median + p90 per clip and pooled. NO 99.9th percentile.
- K2: contingency rej-run-len (1 vs >=2) x (real/ghost) on adjudicated rejects.
  real-frac in >=2 must beat runs-of-1 by >=25pp on >=2 of 3 clips + seeded
  shuffled-label null (1000 draws) reached by <=5%.
- K3: clip reset count x 2 frames as points of seen_frac. <1.0 pt -> M2 inert.
- M1 falsifier: coast_by_gap "1-2" bin median pooled over 3 TrackNet arms.
  >10.0 px median KILLS M1.
DELIVERABLE: new SECTION appended to docs/evidence/innovation-gate-noise-calibration.md
(no new md file). Raw per-frame data under data/output/.
METHOD MANDATED: ball.py NOT modified on disk; inspect.getsource -> textual
insert -> exec; in-run assertion instrumented == shipped output; PRINT it.
STOP-WHEN: report section has numbers+verdicts for K1/K2/K3/M1 and the identity
assertion. Do NOT edit docs/STATE.md, do NOT commit, do NOT spawn subagents.

## STATE - **TASK COMPLETE.** Report section 5 appended; memory + journal written.
DELIVERED: docs/evidence/innovation-gate-noise-calibration.md SS5 (5.0 verdict table ..
5.10 not-established); data/output/gate_noise_diag/ (summary.json + 6 per-frame
rows.json + a verbatim copy of the harness, gitignored dir). ball.py UNMODIFIED
(sha 171932521dc3e796, absent from git status). docs/STATE.md NOT touched (it was
already dirty before this run - not mine). Nothing committed, no subagent spawned.
Memory: NEW smoother-noise-model-is-over-dispersed.md + chain-gate-mechanism-findings.md
extended (six -> seven failed attempts) + MEMORY.md index updated.

RESULTS (all from data/output/gate_noise_diag/, script sha e494f55e96168792):
IDENTITY: instrumented == shipped TRUE on all 3 clips x BOTH chains.
VALIDATION: my lost-reject census reproduces SS5 EXACTLY - 18/13/18 rejects,
  9real/9ghost, 6/7, 6/12. Instrumentation is trustworthy.
K1  median d2 gold-real ACCEPTED: 0.265 / 0.122 / 0.104; POOLED 0.113 (n=291),
    p90 6.764 / 6.341 / 2.328, pooled p90 4.776. Band [0.9,2.2] NOT MET - miss is
    12x LOW, i.e. S is OVERSTATED not understated. R premise dead by opposite sign.
    Uncensored (acc+rej) gold-real medians 1.033 / 0.138 / 0.113.
K2  enrichment_pp +60.0 (p=.105) / +10.0 (p=.589) / +10.7 (p=.585); pooled +23.6
    (p=.135). 1 of 3 clears 25pp (2 required); NO clip reaches null p<=.05. KILL.
K3  resets 630(457rej/173miss) / 384(246/138) / 34(24/10); recoverable frames
    902/479/47; mean seen_frac 51.06->57.55 (+6.49) / 54.79->59.71 (+4.93) /
    67.96->71.41 (+3.45). All >1.0 pt -> K3 PASSES (not inert). Moot: K2 killed M2.
M1  pooled "1-2" bin median 19.90 px (n=16) vs <=10.0 bar -> KILL. Per clip
    2.9(n=3) / 29.6(n=6) / 19.9(n=7). seen_frac's coast-exclusion rule is RIGHT.
LEG2 REFUTED BY MEASUREMENT: R00/S00 median .187/.257/.304 (max .31), NOT the
    derived .70-.85. P dominates S. Accept radius sqrt(13.8*S00) median 64.4 px
    (1080p) / 36.7 / 33.7 - not the derived 18.6-21 px.
SS2 CODE-READ CONFIRMED: rejections / ALL span frames = 10.19% / 7.88% / 7.52%
    vs published D_smooth -11.0 / -8.1.

FINDINGS SO FAR (do not re-derive):
F1. PATH CONFLICT RESOLVED: `data/output/speed_coverage/` EXISTS as a DIRECTORY
    (11 files, e.g. am_hard_utr.tracknet.json, yt_match40.tracknet.json).
    No flat `data/output/speed_coverage_amhard_tracknet.json`. The evidence file
    is right; eval_speed_coverage_chain.py's DOCSTRING example is stale.
    NOTE: no yt_rally2 file there -> yt_rally2 has no published smoother mean.
F2. The 3 TrackNet caches EXIST at
    data/output/detector_ab/{am_hard_utr,yt_match40,yt_rally2}.tracknet.perception.json
    Provenance all consistent (ball_perception.py, tracknet, weights/tracknet.pt,
    cuda, score_thresh 0.5, court_gate false, bgsub true, 2026-08-28).
    am_hard_utr: step2, src_fps 59.94, eff 29.97, 14499 frames, 1920x1080 (rs 1.5)
    yt_match40:  step1, src_fps 29.0,  eff 29.0,  10268 frames, 1280x720 (rs 1.0)
    yt_rally2:   step2, src_fps 60.0,  eff 30.0,  1108 frames,  1280x720 (rs 1.0)
F3. M1 "cheap extra": existing coast-by-gap outputs DO exist but are ALL BallNet
    (ballnet_v21 / pool_new_s0), NOT TrackNet:
    data/output/session_i_ab/coast_{clip}.json, data/output/chain_ab_{clip}.json,
    data/output/coherent_{clip}.json. Key name is `coasted_err_px_by_gap`.
    BallNet "1-2" medians: amhard 6.7 (n=4), match40 11.8 (n=4), rally2 5.3 (n=5).
    -> the TrackNet number must be computed. Bash `grep -rl` in data/ TIMES OUT;
    use a python os.walk byte scan instead (worked in ~20s).
F4. eval_model_filters.py has NO cache option - it re-perceives from video on
    CUDA. So M1 must be computed by replaying the ladder from the cache and
    reusing that tool's `measure()` binning code (import it, do not reimplement).
F5. smooth_forecast defaults: gate_chi2 13.8, meas_var 25, sigma_jerk 1.0,
    reset_after 3, max_gap_s 0.4, bounce_reset FALSE, bounce_hypothesis FALSE,
    res_scale 1.0. Reset block is `if rej >= reset_after or miss >= max_gap:` and
    `rej = 0` is set BEFORE the `if ... rej == 0` re-seed test, so the re-seed
    fires whenever z is not None and accept is False.
F6. CHAIN CHOICE: primary = SS5's chain (remove_outliers -> rectify_track ->
    suppress_false_locks, court gate OMITTED) so the reject census can be
    validated against the published 9/9, 6/7, 6/12. Full shipped ladder (with
    gate_ball_to_court) reported as a sensitivity.
F7. eval_speed_coverage_chain.py CLIPS = {am_hard_utr, yt_match40} only.
    yt_rally2 is NOT in it. Needs a pose cache data/output/<clip>.perception.json.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.

## DONE-PREV (2026-09-10 task: Core ML export on Linux, COMPLETE - do not redo)
Verdict YES for both models, high confidence, no CI run. Delivered
docs/evidence/coreml-export-on-linux.md + .github/workflows/coreml-export-linux.yml
(workflow_dispatch only, NOT triggered) + memory coreml-export-runs-on-linux.md.
