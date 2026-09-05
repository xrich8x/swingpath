# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-05, NEW TASK; net-post work is ANOTHER instance)

FITTED HFOV REPORTING GAP. cam_fit_quad fits an hfov per clip; camera_height_m()
hardcodes 70 deg default instead. qa: under depth-anisotropic compression (the ONE
corruption invisible to all shipped gates) fitted hfov collapses 91->55->34->18->9->2
on yt_match40, leaving the 60-90 amateur-lens prior by ~15% compression.
MY FILES ONLY: backend/swingvision/calibration.py (camera_height_m area),
tools/validate_new_clip.py, docs/evidence/fitted-hfov-reporting-gap.md.
DO NOT TOUCH: tools/net_post_height.py, tools/net_anchor_check.py,
docs/evidence/net-post-detector.md (other instance live).
1 confirm gap by reading code (deliberate fallback? then STOP and say so)
2 check whether --audit's "hfov ...deg" is FITTED or the 70 default (bigger finding)
3 pre-reg bar: window justified from 60-90 prior ALONE flags >=4/5 compressions and
  0 of believed-correct incl eala_pts_auto. Corrupt IN MEMORY only.
4 report fitted hfov for ALL calibrations.
NO FIFTH GATE. Outcome is a REPORTED NUMBER. No STATE.md, no commit, no data/*_pts*.json edits.
STOP-WHEN: code question answered + sweep written up, or ~35 tool calls.

## STATE - 2026-09-05 - starting, reading calibration.py/courtfit.py

## LOG

- CARRIED FORWARD: `python` is a broken Store shim. Use backend/.venv/Scripts/python.exe
- CARRIED FORWARD: `grep -rn` across repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS return false "no matches"; use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- CARRIED FORWARD: bash /tmp NOT visible to Windows python.exe - use scratchpad abs path.
- CARRIED FORWARD: calibration.project_court_3d(H,img_wh,xyz,hfov_deg) takes hfov;
  courtfit.cam_fit_quad returns a fitted focal. Prior runs already fed the FITTED hfov
  into net_anchor_check, so the plumbing exists.
- CARRIED FORWARD: data/output/corner_audit/net_index.json has per-clip horizon_row/
  net_ground_row/net_tape_row/camera_h_m/hfov for 27 clips - may already answer ask 4.
- PRIOR TASKS DONE (earlier runs): net-anchor check, net-tape height. Both shipped.
- *** SWEEP DONE, VERDICT WRITTEN into docs/evidence/net-post-detector.md.
  BAR FAILED: 11 confident, 3/11 = 27% within 10% (bar was >=2/3, n>=6). Tape scored
  13/15 = 87% on the same corpus with the same constants.
  CONFIDENTLY WRONG rows: +261.7 / +94.0 / -69.1 / -45.8 %.
  PRICING (the key number): post %/px median 1.26 vs tape 1.48 => post is 0.854x = 15%
  MORE precise PER PIXEL, exactly as 0.914/1.07 predicts. But row precision: post peak
  lands median 22.3 px from the calibration's predicted top (n=54 posts); tape's row
  error is 2-6 px. ~7x worse. PRECISION DOMINATES => post is the WORSE instrument.
  8 of 11 confident clips rest on ONE post. Two-post same-frame disagreement median
  20.8% of H (range 1.7-134.5). P6 and P0/P1 NEVER fired => framing/resolution are NOT
  the limit; detection is.
  MECHANISM: P5 is confounded - a horizontal FENCE RAIL spans both posts at the same
  height, so both posts lock the same wrong h' and AGREE (bump_ntrp30 h'~3.46 both,
  -69.1%; UHf0LeMU2pg h'~1.97 both, -45.8%). Inferred, NOT eyeballed - flagged.
  DIAGNOSTIC: at the predicted h'=1.07 the step response sits at median 56.6th pctile
  of its own sweep; only 8/54 in the top 5%. The post top is not a distinguished
  feature of this response on typical footage.
  Refused to narrow the search range post-hoc: it is choosing after the result AND
  circular (range centred on the fitted height = steering the independent check).
  Post vs tape on the 7 both-confident clips: post is further from fitted on 6/7. The
  SAG question CANNOT be answered - post error swamps it. Bias asymmetry stated but
  NOT claimed, because the variance hides it.
- REMAINING: wire --post-height into render_corner_audit, add
  backend/tests/test_net_post_height.py, run the suite, memory + DECISIONS_PENDING.
- WIRED: render_corner_audit.py --net-anchors --post-height (off by default, costs a
  second decode for the clean plate; caption carries the FAILED-bar warning and
  "do not show a user"). Regression: --net-anchors alone unchanged.
- TESTS: backend/tests/test_net_post_height.py, 14 tests. FULL SUITE 539/539 PASS
  (was 525). Warnings-suppression patch proved no-change: tc8CGFxyRE8 2.109 / +5.3%
  and yt_match40 P3 z 1.5/2.8 reproduce byte-for-byte after the edit.
- DECISIONS_PENDING appended: two eye-checks (bump_ntrp30, UHf0LeMU2pg - is there a
  fence rail behind BOTH posts?) plus a keep-or-cut call on the tool.
- MEMORY: post-loses-on-precision-not-sensitivity.md + MEMORY.md index line.
- TASK COMPLETE 2026-09-05. docs/STATE.md row NOT written (NOT-THIS-RUN) - lead must
  add: "Net-post off-plane reference FAILS pre-registered bar, 3/11 within 10% (bar
  2/3, n>=6); 15% better %/px than the tape but ~7x worse row precision --
  docs/evidence/net-post-detector.md". No git commit (NOT-THIS-RUN).
- ASK1+2 ANSWERED AND WRITTEN TO DELIVERABLE. The briefed gap is NOT REAL.
  * calibration.py:192 `camera_height_m(H, img_wh, hfov_deg=70.0)` - 70 is a DEFAULT
    ARG, declared in the docstring, and the function has ZERO production callers.
  * pipeline.py:1244-1260 has an explicit priority chain: --camera-hfov > shape_lock's
    FITTED focal (pipeline.py:535 <- courtfit.shape_lock hfov_from_focal(fit[3][5])) >
    focal_from_homography > 70.0 last resort (prints a warning).
  * validate_new_clip.py:141-171 camera_fit() prints hfov_from_focal(cam[5]) = FITTED.
    Height printed is cam[2] from the same fit, NOT camera_height_m().
  => NOT the "bigger finding"; audit was never printing 70.
  REAL remainder (narrower): fitted hfov is decoration in a free-text string; nothing
  compares it to the 60-90 prior, nothing stamps it into _audit, no verdict mentions it.
- *** MY WINDOW, PRE-REGISTERED 2026-09-05 BEFORE RUNNING ANY SWEEP. Two windows, both
  fully determined by the repo's 60-90 deg amateur-lens prior with NO free parameter:
    W1 = [60,90] deg two-sided. The prior verbatim. Flag = fitted hfov outside.
    W2 = hfov < 60 deg only (one-sided lower bound at the prior's FLOOR).
         Justification, mechanism-matched and stated before the sweep: qa measured that
         depth compression drives hfov DOWN monotonically (91->55->34->18->9->2). An
         upper bound therefore cannot catch this corruption and can only add false
         rejects, so the prior's ceiling is dropped. I ALREADY KNOW from qa's published
         table that baseline yt_match40 fits 91.0 deg, i.e. W1 flags a believed-correct
         clip on sight; that is a reason to register W2, and I say so rather than hide it.
  W2's flag set is a SUBSET of W1's, so if W2 flags eala so does W1.
  BAR (lead's, unchanged): SEPARATES iff flags >=4 of the 5 depth compressions
  (alpha .15/.30/.50/.70/.90) AND flags 0 of the believed-correct calibrations,
  eala_pts_auto INCLUDED. Anything else = DOES NOT SEPARATE -> report the number, no gate.
  No third window will be invented after seeing results.
- SWEEP DONE, 32 files, data/output/hfov_sweep.json. Reproduced qa's compression column
  EXACTLY (91.0/55.3/34.4/18.3/8.7/2.4 and 60.6/38.2/24.8/13.7/6.7/5.5).
  DETECTION 10/10: both W1 and W2 flag all 5 alphas on both clips.
  FALSE FLAGS kill it. Believed-correct = 28 (all but the 4 stamped DEGENERATE).
  W1 [60,90] flags 7: demo30 104.2, eala 23.4, flexi_franz_p07 59.6, HoHxFSX_s2 94.3,
    yt_match40 91.0, yt_rally2 93.7, court_pts_refined 12.3.
  W2 (<60) flags 3: eala 23.4, flexi_franz_p07 59.6, court_pts_refined 12.3.
  BOTH FAIL the pre-reg bar (eala INCLUDED, as the lead predicted). => DOES NOT SEPARATE
  -> report the number, NO GATE. Bar stays failed; no third window invented.
  IMPOSSIBILITY (stronger than "my window failed"): eala 23.4 sits INSIDE the
  compression distribution (34.4, 18.3 either side). No 1-D threshold can exclude
  eala and still catch alpha>=0.30. Broadcast telephoto and compressed amateur court
  are the same number.
  *** SECOND HEADLINE, repeatability. Same mount, re-clicked: HEIGHT repeats to <=0.12 m
  but HFOV scatters up to 29.2 deg. HoHxFSX s1/s2/s3 = 65.1/94.3/83.1 (h 1.71/1.59/1.60);
  hillsborough p02/p08 = 71.6/80.1 (h 1.64/1.63); flexi_franz p01/p07 = 60.6/59.6
  STRADDLING the 60 bound on one camera. Scatter is comparable to the WIDTH of the
  60-90 window -> that is the deeper reason no bound works.
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe.
  grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs. run.py is
  backend/run.py, not repo root.
- GEOMETRY REPRODUCED. Prototype (scratchpad/proto.py) rebuilds the lead's synthetic
  pinhole and gets margin = tape_row - far_row at 3 m/80deg/720p:
    1.40 -15.0 | 1.64 -9.5 | 2.00 -1.3 | 2.50 +10.0 | 3.00 +21.2 | 4.00 +43.1
  vs the doc's own differences -15.0/-9.5/-1.4/+10.1/+21.4/+44.1. Agrees <=1 px.
  So my +10 px pre-registered "good" band IS the doc's 2.50 m row, exactly.
- PRIMITIVE CHOICE: focal_from_homography(H, img_wh) self-calibrates f from the FOUR
  CORNERS - no hfov assumption, no free parameter. My earlier hfov-scatter finding is
  click noise on the same determined quantity, not an extra unknown. Then
  project_court_3d(H, img_wh, [(X_CENTER, NET_Y, NET_HEIGHT_CENTER)], hfov).
- *** SWEEP DONE (scratchpad/sweep.py -> data/output/net_clearance_sweep.json).
  ASK2 HEADLINE: derivation gives far/near ratio ~0.12 (range .088-.189) at the
  crossover, .126 (.091-.189) at +10px. SHIPPED 0.28 corresponds to a camera height of
  8.5-10.0 m - a BROADCAST TOWER, not a phone. 0.28 is ~2.3x too strict.
  BUT the bigger ASK2 finding: the ratio is NOT monotone in camera height. HoHxFSX_s1 at
  1.71 m has elev 0.262; L73ep7JHiJ4 at 2.89 m has 0.215. Standoff+lens dominate. poor
  clips span elev .106-.268, good clips .190-.233 -> COMPLETE OVERLAP. No threshold on
  the width ratio works, so "0.28 is wrong by X" understates it.
  ASK3: 34 unique files, 32 scored. good 9 / marginal 6 / poor 17 (pre-dedupe counts
  were 11/7/18 with dupes). 4 stamped DEGENERATE are in there and must be split out.
  yt_court_pts_doubles: NO PHYSICAL CAMERA FITS (project_court_3d None) - graceful.
  Cross-check vs brief: yt_match40 -8.9, am_hard_utr -7.8, demo30 -10.2, flexi_joy_p01
  -19.6 all POOR; L73ep7JHiJ4 +12.0, UHf0LeMU2pg +24.5, sAjkpeRq4P4 +16.1 all GOOD.
  Every one of the 7 named clips lands on the side the brief predicted.
- CODE SHIPPED. calibration.py: CLEARANCE_GOOD_PX, _net_height_at_x, NetClearance,
  net_tape_clearance(H, img_wh, hfov_deg=None) + framing_report gains clearance_px_720 /
  clearance_level and a message (can hold good->warn, NEVER produces poor).
  courtfit.setup_verdict angle[] gains net_clearance_px/_level/_msg (does NOT touch level).
  backend/run.py prints a "Setup [OK|TIGHT|OVERLAP]" block. PARSER UNTOUCHED.
- TRAP: writing `\n` inside an f-string through a bash heredoc python script turned into a
  REAL newline and broke run.py's f-string. Use print("") instead of embedding \n.
- TESTS: backend/tests/test_net_tape_clearance.py, 32 tests. FULL SUITE 571/571 PASS
  (was 539). No pre-existing test moved -> rule 8 satisfied.
- run.py check on demo_30s.mp4 prints "[OVERLAP] -13 px". NOTE it reads the SHAPE-LOCKED H
  (1.49 m) not the stamped corners (1.38 m), so it differs slightly from the sweep table.
- DELIVERABLE docs/evidence/live-setup-criterion.md WRITTEN IN FULL (all sections).
- DECISIONS_PENDING appended: delete min_elevation? / no-fence fallback? / one eye-check at
  +5 px (mpc_tuesday_p01).
- TASK COMPLETE 2026-09-05. STATE.md row NOT written (NOT-THIS-RUN); lead must add:
  "Live setup criterion: net-tape clearance in px replaces the guessed min_elevation proxy;
  16/28 calibrations OVERLAP, derivation gives ratio 0.12 vs shipped 0.28 --
  docs/evidence/live-setup-criterion.md". No git commit (NOT-THIS-RUN).
