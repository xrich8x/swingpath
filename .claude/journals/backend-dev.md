# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-05)

Build a NET-ANCHOR calibration check: project court features NOT in the 4-corner fit
(net line at court-y 11.885 m, both NET POSTS at 0.914 m outside doubles sideline) and
render over a real frame so a human can see if they land on the real thing.
Motivation: yt_match40 re-click 2026-09-05 IMPROVED on every screen (0.2 px residual,
1.61 m height, 0.944 coverage) and was STILL WRONG — far corners on the NET. Coverage
rewards that: court squashed into near half still lands on real paint, wrong paint.
WIRE INTO: tools/validate_new_clip.py --audit and/or tools/render_corner_audit.py
(extend, do not fork). run.py parser must not change (hook).
Add post constants to backend/swingvision/court.py if missing. Add a test.
RUN over ~25 existing data/*_pts*.json with videos; report which get flagged.
DELIVERABLE: docs/evidence/net-anchor-calibration-check.md
STOP-WHEN: check runs over existing calibrations + written up, or ~40 tool calls.
NOT-THIS-RUN: editing any calibration file; verify_court thresholds; docs/STATE.md; commit.

## STATE - 2026-09-05 - STARTING

## LOG

- CARRIED FORWARD: `python` is a broken Store shim. Use backend/.venv/Scripts/python.exe
- CARRIED FORWARD: `grep -rn` across repo ROOT times out (walks .venv) — grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS return false "no matches"; use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- CARRIED FORWARD: bash /tmp NOT visible to Windows python.exe — use scratchpad abs path.
- court.py + court.js: added NET_POST_OFFSET .914, NET_HEIGHT_POST 1.07, NET_HEIGHT_CENTER
  .914, X_LEFT/RIGHT_POST (-0.914 / 11.884), X_LEFT/RIGHT_STICK (0.456 / 10.514),
  NET_LINE_SEGMENT, NET_POST_BASES, net_post_segments_3d(). LINES UNCHANGED (still 10) on
  purpose: overlay.py draws LINES and validate_new_clip counts horizon crossings over it.
- calibration.project_court_3d(H,img_wh,xyz,hfov_deg) exists -> post TOPS projectable.
  Feed it hfov from courtfit.cam_fit_quad focal, not the 70deg default.
- SHIPPED tools/net_anchor_check.py (shared module: geometry + measure + draw, with the
  PRE-REG bars band_ratio<1.5 and |dy|>0.5*net_px_height) and
  tools/render_corner_audit.py --net-anchors (separate <tag>_netanchor.png, net_index.json).
  NOTE: `import net_anchor_check` works because tools/ is the script dir.
- FIRST RESULTS: yt_match40 (the RE-CLICKED wrong one, stamped 0.0px LOW-CAMERA)
  ratio 0.78 -> 16.67 at dy +49, netpx 36 => FLAG, 21x separation.
  yt_rally2 (known good) ratio 1.79, dy -17 => ok. Bars survive first contact.
- *** LEAD CORRECTION 2026-09-05 (mid-run). The brief's premise was WRONG. yt_match40's
  re-click is CORRECT (residual 0.0 px, camera 1.64 m, coverage 0.948). The lead had
  compared the projected net GROUND line (z=0) against the net TOP TAPE (z=0.914) in the
  image - apples to oranges; the tape necessarily images higher. Correct arithmetic:
  (row-horizon) ~ H/depth, so a point h above ground scales by (H-h)/H. H=1.64,
  horizon 264.6, net ground row 325 -> tape must be at 291.3; observed ~295 => 3.7 px.
  Do NOT cite "wrong court scoring 0.944". .bak-2026-09-05 IS the wrong one - negative
  example only, never restore.
- CONSEQUENCE: my PRE-REGISTERED BARS FAIL. 14/27 flagged INCLUDING yt_match40 (ratio
  0.78, dy +49) which is now known CORRECT. A failed bar stays failed - report, do not move.
- My band ALREADY projects to tape height (project_court_3d + fitted hfov), so the
  machinery is right; the LABELS were not. Fix: draw+name z=0 ground line vs z=0.914/1.07
  TAPE line vs post segments distinctly, and print horizon/ground/tape ROWS so a human can
  redo the lead's arithmetic from the PNG without repeating the mistake.
- FULL SWEEP RESULT (27 rendered of 29; court/yt_court have no video) saved at
  data/output/corner_audit/net_index.json
- SHIPPED + VERIFIED. 513/513 backend tests pass (incl. 7 new in
  backend/tests/test_net_anchor_geometry.py and the JS parity 6).
  Wired: render_corner_audit.py --net-anchors (+ --tag/--video-tag) and
  validate_new_clip.py --audit --net-anchors. Doc:
  docs/evidence/net-anchor-calibration-check.md. DECISIONS_PENDING appended
  (am_hard_utr + sAjkpeRq4P4 need a human eye on their _netanchor.png).
  Memory: net-ground-vs-net-tape.md. TASK COMPLETE 2026-09-05.
- Run2. net_index.json ALREADY has per-clip horizon_row/net_ground_row/net_tape_row/
  camera_h_m/hfov. Verified lead's formula reproduces camera_h_m exactly on A7vXlWIlyrI
  (t=0.4582 -> H=1.687 vs stamped 1.69). So the MODEL side is free; only the OBSERVED
  tape row needs measuring.
- KEY REPARAMETRISATION: for a pinhole, a point h above ground at the net images at
  row(x) = horizon(x) + (ground(x)-horizon(x))*(1-h/H). So "constant height above the
  net line" is a ONE-PARAMETER family t = 1 - h/H, the SAME t at every column. Search t,
  not rows -> perspective/roll handled exactly, H = h/(1-t).
- PRE-REGISTERED DETECTOR THRESHOLDS (written before running the sweep):
  clean plate = per-pixel median of 7 frames; 3 disjoint column ranges inside the CENTRAL
  50% of the net span (h=0.914 there to <1%); score(t) = min(on-above, on-below) on a
  bright-band matched filter, windows scaled by frame_height/720;
  REFUSE unless: >=3 ranges valid & >=20 columns each; peak score >= 4.0 gray levels;
  robust z >= 4.0; 2nd local peak (>=5px away) <= 0.75*best; spread of the 3 ranges'
  peak rows <= 3px*scale. Refusals get reported, not dropped (rule 10).
- TOOL WORKS: tools/net_tape_height.py. Smoke: yt_match40 tape 1.752 vs fit 1.641 (+6.7%);
  am_hard_utr tape 1.678 vs fit 1.743 (-3.7%). BOTH within 10%.
- *** THE HEADLINE. My automated tape row for am_hard_utr centre = 528.0. qa's eyeball
  profile said 522, and 522 is EXACTLY the row that yields the lead's briefed 1.52 m
  (-12.8%). Six pixels. Sensitivity: dH/drow = H^2/(h*(ground-horizon)) = 1.8%/px at
  1080p on am_hard_utr, 3.2%/px at 720p on yt_match40. The pre-registered 10% bar is
  ~3 px of tape row at 720p. This is a PRECISION-LIMITED instrument and that is the
  finding, whichever way the sweep lands.
- yt_match40: mine 293.8, model 291.9, qa/lead's ~295 -> 1.84 (+12.2%). Same 2-3 px story.
- SWEEP DONE (27 clips, 2 no-video). 15 confident, 12 refused. 13/15 within 10%
  => AGREE on the pre-registered bar. Directions 8+/7-, median +0.3% => NO systematic
  sign. Outliers: demo30 +75.4% (720p, 47.9px net span, 5.5%/px - BELOW the
  instrument's resolution) and L73ep7JHiJ4 -22.3% (real, strong, 20.9px above model).
- CONFLICT TO REPORT, not smooth: on sAjkpeRq4P4 qa's hand profile says tape row
  406-409, my matched filter says 437.8 (=model 437.5 to 0.3px). ~30px apart. At 407
  it is -33%; at 438 it is +5.4%. Verdict holds either way (12/15 still clears 2/3).
- 4 courts appear twice: each pair agrees in sign and to <=2.6pp => the estimator is
  REPEATABLE; the spread is court-specific (net sag), not per-frame noise.
- SHIPPED: tools/net_tape_height.py, backend/tests/test_net_tape_height.py (12 tests),
  docs/evidence/net-tape-camera-height-consistency.md, DECISIONS_PENDING appended.
  525/525 backend tests pass. TASK COMPLETE 2026-09-05. docs/STATE.md row NOT written
  (NOT-THIS-RUN, lead's) - lead must add one.
- PRE-REGISTERED, 2026-09-05, BEFORE ANY POST-DETECTOR CODE WAS WRITTEN OR RUN.
  MEASURAND: the image row of the POST TOP (z=NET_HEIGHT_POST=1.07) at the predicted post
  column (X_LEFT_POST -0.914 / X_RIGHT_POST 11.884, y=NET_Y). Same h' reparametrisation as
  the tape: sweep a fake height h', project (X_POST,NET_Y,h') under the FITTED pose, the
  response peak converts to H = 1.07*H_fitted/h'. Post BASE is on z=0 and carries NO
  off-plane information - reported for framing only, never used in the height.
  SIGNAL: "postness" p(h') = max( min(on-left,on-right), min(left-on,right-on) ) - a
  vertical bar brighter than BOTH neighbours OR darker than both (posts are dark against
  sky and light against a dark fence; sign is not knowable a priori). Column windows are
  the tape's, rotated 90 deg and scaled by frame_height/720.
  TOP = step edge in p: R(h') = mean(p just BELOW h') - mean(p just ABOVE h'), window
  +-4 px scaled. Peak of R over the sweep = post top.
  REFUSAL RULES (report every refusal, rule 10):
   P0 no camera pose / degenerate horizon-vs-net-ground rows.
   P1 >=60% of the swept grid samples on-frame AND the +-4px window at the peak fully
      on-frame, for that post.
   P2 peak edge response >= 4.0 grey levels (same bar as the tape's MIN_SCORE).
   P3 robust z of the peak over the sweep >= 4.0 (same as tape MIN_Z).
   P4 best rival peak >= 5.0 px away scores <= 0.75 of the best (same as tape R4).
   P5 if BOTH posts pass P1-P4 their implied top rows must agree to <= 3.0 px * scale
      (same as tape R5). If they disagree the CLIP is refused - two rigid posts that
      disagree is exactly the case where I cannot say which is the post.
   P6 RESOLVABILITY: predicted post pixel length (base row -> top row under the fit)
      >= 10 px, ABSOLUTE not scaled. Deliberately absolute: an edge measured on a 6 px
      bar is not measurable at any sensor resolution. This is the rule demo30 (47.9 px
      net span, 5.5%/px) should have hit in the tape run and did not.
   Clip estimate = mean of the passing posts. 0 passing = clip refused.
  BAR (the tape's own, reused verbatim from independent-calibration-references.md
  "second falsifier"): AGREE if |post-implied - fitted| <= 10% of fitted on >= 2/3 of
  confident clips, with n >= 6 confident clips. Fewer than 6 confident = NO VERDICT,
  which is a legitimate outcome and will be reported as such, not softened.
  SECONDARY, pre-registered as a DESCRIPTION not a gate: post-vs-tape on clips confident
  in both. Where they agree with each other, that corroborates the fitted height. Where
  they disagree, sag can only make the CENTRE tape read LOW (tape sags DOWN -> larger
  (row-horizon) -> smaller (H-h)/H is wrong... sign to be derived in the doc from the
  formula, not asserted here) - so the sign of the disagreement is the discriminator.
  NO FIFTH GATE. This is a diagnostic number for a human, and the doc will say so.
- SHIPPED tools/net_post_height.py. SMOKE ON 3 CLIPS: ALL THREE REFUSE.
  yt_match40 P3 (z 1.5 / 2.8); am_hard_utr P5 posts disagree 46.9 px; yt_rally2 P5
  posts disagree 55.8 px. post_px 39-65 so P6 is not the binding rule.
  DIAGNOSIS (not a tuning excuse): the step-edge peak lands at h' well ABOVE the post -
  yt_rally2 right h'=2.03 m and left h'=3.59 m above the net ground point, with peak_edge
  119 grey levels and z 18. There is far more vertical structure (fence tops, wall edges)
  in a 4 m column than the 1.07 m post. The pre-reg sweep range (copied from the tape's
  H 0.9-12.0) lets the detector lock onto it. I will NOT shrink the range after seeing
  this - that is choosing a threshold after the result. Report the refusal.
- Adding DIAGNOSTIC fields only (never used by any rule): response at the calibration's
  own predicted h'=1.07, its robust z, its percentile rank, and px distance to the
  nearest local max. Labelled post-hoc; it characterises whether the post produces a
  detectable step AT ALL, which is the instrument question.
