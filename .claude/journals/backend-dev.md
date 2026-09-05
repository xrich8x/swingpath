# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-05) COMPOSITE CALIBRATION SCORE

Founder: "don't just use the net - a mix of all we've worked on".
Build a SIMPLE INSPECTABLE composite (weighted vote / thresholded indicators, NOT a
fitted classifier) over already-built signals; emits SCORE + REASON STRING.
Signals (REUSE, do not rebuild): net_tape_clearance, net_tape_height.py,
net_post_height.py, cam_fit_quad hfov + camera height, court_line_coverage,
court_centrality, verify_court, fit residual, player-feet depth anchor.
POSITIVE CLASS = SYNTHETIC (qa harness in docs/evidence/ground-plane-blindness-test.md).
n=1 real wrong calibration (data/yt_match40_pts.json.bak-2026-09-05).
BAR (pre-reg, lead journal last section): TRAIN/HELD-OUT split of CLIPS. PASS = on
held-out, flags >=80% of synthetic corruptions at <=1 false flag among believed-correct
(eala_pts_auto INCLUDED as a negative). Report BY CORRUPTION TYPE, never pooled.
MANDATORY ABLATION: each signal's SOLO score beside composite; if one solo matches the
composite SAY SO - that kills the ensemble.
DELIVERABLE: scorer + tests, and docs/evidence/composite-calibration-score.md.
NOT-THIS-RUN: editing data/*_pts*.json; a shipped gate; run.py parser; docs/STATE.md;
git commit. DO NOT TOUCH docs/evidence/composite-score-qa.md (qa is live).
STOP-WHEN: held-out eval + ablation written up, or ~45 tool calls.

## STATE - 2026-09-05 - starting: reading qa corruption harness + signal APIs

## LOG

- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
  ALSO: `\n` inside an f-string via bash heredoc becomes a REAL newline. Use print("").
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- CARRIED FORWARD: focal_from_homography(H,img_wh) self-calibrates f from 4 corners, no
  free parameter. project_court_3d(H,img_wh,xyz,hfov_deg). courtfit.cam_fit_quad -> fit
  tuple; hfov_from_focal(fit[3][5]); camera height = cam[2].
- PRIOR RESULT: fitted hfov FAILS as a solo gate (eala 23.4 sits INSIDE the compression
  distribution). data/output/hfov_sweep.json has fitted hfov+height for 32 files.
- PRIOR RESULT: net clearance sweep in data/output/net_clearance_sweep.json (32 scored).
- PRIOR RESULT: net-post height FAILS (3/11); net-tape height 13/15.
- SWEEP DONE: data/output/composite_signal_sweep.json, 513 rows = 27 clips x
  (baseline + 18 corruptions). Script: scratchpad/sig_sweep.py. eala needed an explicit
  video map (eala_auto -> data/incoming/Grass/eala_segment.mp4); the .bak needed explicit
  file listing (glob *_pts*.json misses a .bak- suffix). 4 pts files have no video
  (court_pts*, yt_court_pts*) -> skipped.
  Signals per row: coverage, centrality, verify_ok, residual_px, cam_h_m, cam_x/y_m,
  hfov_deg (cam_fit_quad), clear_px720 + self_hfov (net_tape_clearance, self-calibrated).
- NEXT: seeded 50/50 clip split declared BEFORE inspecting, then rule on TRAIN only.
- TRAP: court_line_coverage returns a TUPLE (coverage, visible_frac). First sweep silently
  lost coverage/centrality/verify_ok (cov_err). Fixed + re-run.
- SPLIT DECLARED BEFORE INSPECTING RESULTS, seeded:
  TRAIN if sha256("calibsplit-seed-2026-09-05|"+tag) % 2 == 0. 17 TRAIN / 9 HELD-OUT
  believed-correct clips + the 1 known-WRONG .bak (reported separately, in neither split).
  HELD = am_hard_utr demo30 eala_auto flexi_franz_p01 flexi_franz_p07 flexi_joy_p07
         hillsborough_p08 mpc_tuesday_p01 uR5q2cSM6AY  (eala IS held-out - good)
- NOTE: my cam_fit_quad residual for yt_match40 is 1.09 px, stamp says 0.0 - validate_new_clip
  likely fits with allow_roll=True. Same function, different DOF; report, do not chase.
- TRAIN DISTRIBUTIONS READ. Two mechanism findings that shape the rule:
  * hfov<60 catches ALL 85 TRAIN depth rows (max at a=0.15 is 56.08) with 0 TRAIN false
    flags (TRAIN baseline min 61.35). But HELD has eala 24.5 and flexi_franz_p07 59.5
    => hfov SOLO will fail held-out. That is the ablation story, expected.
  * clear_px720 EXPLODES under depth a>=0.50 (+117..+2296) vs believed-correct range
    -19.6..+24.6. New: net clearance is a depth-compression detector, not just setup.
  * KEY IDEA (coherence, not thresholds): broadcast = narrow lens + HIGH mount (coherent);
    depth compression = narrow lens + LOW mount (INCOHERENT). Same for clearance: a
    tower-sized clearance with a 1.6 m fitted height is a contradiction. This is how the
    mix beats hfov-solo without false-rejecting eala.
  * residual bound taken from the REPO's existing >40 px _cam_refine REFUSE gate, NOT
    picked off TRAIN (TRAIN baseline max 19.15, HELD max 23.98).
- tape_sweep.py running in BACKGROUND (log scratchpad/tape_sweep.log), writes
  data/output/composite_signal_sweep.json incrementally per clip. 4K clips are slow.
- *** RULE CHOSEN ON TRAIN, selection criterion declared before touching HELD:
  "maximise pooled TRAIN detection subject to ZERO TRAIN false flags; tie-break simpler".
  WINNER: weights lines=0.5, all other indicators 1.0, FLAG_AT=1.0, RESIDUAL_REFUSE_PX=25.
  TRAIN: FF 0/17, pooled 172/306 = 56%. depth 84/85(99%) iso 0/68 shift 33/51 rot 48/51
  asym 7/51. Sensitivity variant (res=40, the repo's own _cam_refine bound): 148/306=48%.
  PRIMARY = the TRAIN winner. res=40 reported as a sensitivity check ONLY; verdict is
  taken from the primary, not whichever wins on held-out.
- FINDING (important, contradicts a qa reading): coverage catches isotropic scale only
  RELATIVE TO THE CLIP'S OWN BASELINE. As an ABSOLUTE threshold it cannot: iso0.7 coverage
  median 0.399 min 0.056 OVERLAPS believed-correct baselines (HoHxFSX_s3 0.188,
  CYqapSq5llo 0.326). At deploy there is no baseline => isotropic scale is INVISIBLE.
- lines is the ONLY iso detector, and the source of all 3 TRAIN false flags. Down-weighting
  it to 0.5 is mechanism-justified (known low-contrast-paint false rejects), and it costs
  iso entirely -> 0%.
- TAPE SWEEP FINISHED, 27/27 clips, 513 rows. RULE RE-SELECTED on TRAIN with tape present,
  same declared criterion. FROZEN RULE: WEIGHTS {lines 0.5, tape_height 0.5}, all others
  1.0, FLAG_AT 1.0, RESIDUAL_REFUSE_PX 25.
  TRAIN: FF 0/17, pooled 187/306 = 61%. depth 85/85 100%, iso 12/68 18%, shift 34/51 67%,
  rot 48/51 94%, asym 8/51 16%.
- *** HEADLINE NEGATIVE, pinned in backend/tests/test_calib_score.py: the composite
  SCORES 0 on the ONE confirmed-wrong calibration (.bak). 10.82 m + 20.9 deg IS the
  broadcast signature the coherence rule exists to exonerate (eala: 8.73 m + 24.5 deg).
  coverage 0.436 is ABOVE verify_court's 0.40 bar and BELOW 4 believed-correct clips.
  DO NOT RETUNE: n=1 and every constant that catches it re-breaks eala.
- backend/tests/test_calib_score.py: 15 tests, all pass.
- NEXT: HELD-OUT eval + solo ablation on HELD, then write the deliverable.
- *** HELD-OUT RESULT (rule frozen before looking): FF 1/9 (flexi_franz_p07, lens_coherence
  at 59.5 deg vs the 60 floor - fragile, sibling p01 is 60.5). eala_auto 0.0 NOT FLAGGED.
  Detection pooled 92/162 = 57% -> FAILS the 80% bar. BY TYPE: depth 91%, rot 93%,
  shift 67%, asym 30%, ISO 0/36 = 0%.
  ABLATION (held-out): best solo pooled = residual 37%; best solo on DEPTH = lens_coherence
  76% AND it is the one that false-flags. COMPOSITE 91% on depth, 57% pooled.
  => NO SOLO MATCHES THE COMPOSITE. The ensemble is NOT redundant. That is the positive.
  Sensitivity res=40 (repo's own bound): same FF, pooled 49%. Verdict unchanged.
- ISO BLIND SPOT EXPLAINED: coverage catches isotropic scale only RELATIVE to the clip's own
  baseline; absolutely it OVERLAPS believed-correct clips (0.188/0.326/0.433). At setup time
  there is no baseline. Argued, not proved, that no single-frame 4-corner rule can catch it.
- FULL SUITE 586/586 PASS (was 571; +15 new). No pre-existing test moved.
- DELIVERABLE docs/evidence/composite-calibration-score.md WRITTEN IN FULL (all sections).
- DECISIONS_PENDING appended: eye-check flexi_franz_p07 / demo30 tape +80% / surface-or-not /
  COMMISSION HUMAN MIS-CLICKS as real positives (the real ask).
- TASK COMPLETE 2026-09-06. docs/STATE.md row NOT written (NOT-THIS-RUN); lead must add:
  "Composite calibration score FAILS the pre-registered bar: held-out 57% detection (bar 80%)
  at 1/9 false flags; depth compression 91%, isotropic scale 0/36; no solo signal matches the
  composite; scores 0.0 on the one real wrong calibration --
  docs/evidence/composite-calibration-score.md". No git commit (NOT-THIS-RUN).
