# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-09: CANDIDATE PROPOSAL RECALL (court only)

Question: on what fraction of gold clips does a court candidate within the accept
tolerance (WRONG_PX_640 = 20.0 px @640) EVER appear — regardless of whether the vote
accepts it? Separates "the search never found it" from "it found it and lost the vote".
GATES backend-dev's CNN-global/classical-local reorder. Message backend-dev with the
headline as soon as I have it.

DELIVERABLE: docs/evidence/candidate-proposal-recall.md
STOP-WHEN: audit run + verdict written, or ~40 tool calls.
Instrument: eval/candidate_audit.py (exists, marked UNRUN as of 2026-08-24).

## PRE-REGISTERED BAR — written BEFORE any result was seen (this is the whole point)

Let R = (# gold clips where >=1 per-frame lock lands <= 20.0 px @640 from the human
court) / (# gold clips audited).

- **VOTING BINDS** if R >= 0.80. The search reaches the right answer on nearly every
  clip; the loss is downstream (scoring/agreement/accept-conjunction). A CNN global
  localiser would then be replacing a stage that is already working -> external
  document's premise COLLAPSES.
- **SEARCH BINDS** if R <= 0.60. On >=40% of clips no correct candidate is ever
  produced, so no downstream gate/score/vote change can recover them -> external
  document's premise HOLDS, rebuild justified.
- **MIXED / INDETERMINATE** for 0.60 < R < 0.80. Say so; do not round either way.

Secondary, also pre-registered:
- HEADROOM H = (# clips with >=1 good candidate) - 12 (clips the shipped gate already
  accepts). H >= 4 clips => materially recoverable recall exists downstream.
- SHELL (indoor, historically 0/5 accepted): search binds on shell if shell recall
  <= 1/5; voting binds on shell if >= 4/5; between = mixed.
- MOUNT HEIGHT mechanism (net tape overlapping far baseline below ~2.0-2.2 m) is
  CONFIRMED as a distinct mechanism only if recall drops by >= 40 percentage points
  across the 2.0-2.2 m boundary AND the low group has >= 3 clips. Otherwise: not
  established, report the numbers only.

A failed bar stays failed. I will not read the threshold off the results.

## KNOWN CAVEAT TO STATE UP FRONT (identified from source before running)
`audit()` calls `cf.auto_fit_frame` per frame, which returns ONE winner per frame,
already past the per-frame accept conjunction. So what this instrument measures is
**per-frame ACCEPTED-LOCK recall across k frames**, which is a LOWER BOUND on true
proposal-stage recall (raw quad candidates before scoring are strictly a superset).
=> a HIGH R is strong evidence for "voting binds". A LOW R is weaker evidence for
"search binds" — it could still be the per-frame accept rule killing a proposed
candidate. The script's `truth_would_pass` / `truth_fails` columns address exactly
that second half (would the accept rule take the human court if handed it), so I
must report BOTH.

## LOG
- 2026-09-09: read journal + memory; read eval/candidate_audit.py in full (339 lines,
  docstring says UNRUN, no number in repo produced by it yet). Bar pre-registered above.
- 2026-09-09: POOL = run_refs.references() -> 20 clips, all with `_exact:true` human
  clicks + a `_audit` stamp carrying camera_height_m. Surfaces by data/incoming folder:
  Hardcourt 8, Clay 2, Shell 10 (= 5 shell RECORDINGS x2 points each: flexi_franz,
  flexi_joy, hillsborough, mpc_mixed, mpc_tuesday -> this is the "0 of 5" shell set).
  Heights <2.0m: 12 clips; >=2.0m: 8 clips. HoHxFSX_gLk_s1/s2 share a source.
- 2026-09-09: audit running (~10min+ for 12/20; 4K shell clips are slow). INTERIM
  best_err@640: A7vXlWIlyrI 5.3(reached x1), am_hard_utr 7.5(x8), CYqapSq5llo 5.2(x5),
  e8T34KoJzOw_s2 6.7(x3), flexi_franz_p01 8.8(x3), flexi_franz_p07 6.6(x2),
  flexi_joy_p01 40.8(x0), flexi_joy_p07 40.8(x0), hillsborough_p02 37.2(x0),
  hillsborough_p08 27.6(x0), HoHxFSX_gLk_s1 60.5(x0), HoHxFSX_gLk_s2 23.1(x0).
  => 6/12 so far reached. NOTE the near-misses: HoHxFSX_gLk_s2 23.1 and
  hillsborough_p08 27.6 sit just outside 20px; flexi_franz DOES reach truth on shell,
  which already contradicts a blanket "shell search never finds the court".
- 2026-09-09: AUDIT COMPLETE, 20/20 clips. HEADLINE: proposal recall 8/20 = 40%.
  Pre-registered bar said <=0.60 => **SEARCH BINDS**. Shell 2/10 clips = 1/5
  recordings (exactly ON my pre-registered <=1/5 shell line => borderline search-binds,
  said so). Mount height <2.0m 4/12=33.3% vs >=2.0m 4/8=50.0%, gap 16.7pp vs a
  pre-registered 40pp bar => mechanism NOT ESTABLISHED (and confounded: 8 of 12
  sub-2m clips are shell). Second half: truth_would_pass 9/20; blockers g>=.33 x11,
  struct x4, verify x4, suffic x3; selects_against_truth on 9 clips. Verdict: BOTH
  stages fail; search binds on 12 clips, accept rule refuses truth on 11.
- 2026-09-09: CAVEAT found in the instrument: truth_would_pass is a UNION over 8
  frames of any failing term, scored on the EXACT human clicks -> harsh; proven
  distorted because 5 of the 8 clips where a good lock WAS produced are marked
  "truth would not pass". Reported 9/20 as a FLOOR. Did not edit the script (not mine).
- 2026-09-09: DELIVERABLE WRITTEN: docs/evidence/candidate-proposal-recall.md with the
  headline for backend-dev at the very top. NO SendMessage tool exists in my toolset
  (2nd consecutive run a brief claimed it); used the file as the channel.
- 2026-09-09: CONFLICT: docs/STATE.md:196 (researcher) says it waits on "qa's SHELL
  proposal recall, which decides it" yet already declares DIAGNOSIS CONTRADICTED with
  "generated 7/10, reachable 31/38, recognised 9/10, lost at the vote". My shell
  number is 2/10 / 1/5 and points the OTHER way. Next: reconcile units by reading
  researcher's evidence file (read-only, not editing it).
- 2026-09-09: MAJOR RECONCILIATION, corrects my own draft.
  (a) candidate_audit.py docstring "UNRUN" is STALE: Session O ran it on SHELL on
      2026-08-24 -> data/output/court_scoring_diagnosis.md §10 + docs/evidence/
      indoor-shell-courts.md. Prior shell: 3/10 reached, 4 locks-no-truth, 3 no-lock.
      MINE: 2/10 reached, 5 locks-no-truth, 3 no-lock. Same direction, ONE CLIP LOWER
      -> report as drift/possible small regression; cannot name the clip from the
      archived summary (no per-clip table), and 2 within-frame margins flipped sign.
      Candidate cause worth someone's eye: 4a33635 scaled refiner reach 55 -> 55*w/640,
      validated as "no-op on the gate" -- but shell is 3840x2160 (6x) and is NOT in
      the gate pool, so a shell-only effect would be invisible to that validation.
  (b) MY 9/20 truth_would_pass IS THE WITHDRAWN-FIGURE ARTIFACT. §10 records the
      already-existing correct instrument: the neighbourhood sweep at a median 4.9 px
      from the clicks clears the 0.33 accept gate on **19 of 20** references (only
      UHf0LeMU2pg fails). So the criteria do NOT bind. RETRACT my "both stages are
      broken" framing -> SEARCH BINDS, cleanly, and this AGREES with Session O's
      "the search is decisively the bottleneck".
  (c) researcher's row is NOT in conflict: its own §3.4 pre-states the narrowing
      condition ("if shell proposal recall is near zero while pooled is 70%, the doc
      is right about shell") and says it could not obtain the number. My shell number
      TRIGGERS that condition. Also its pooled 7/10 is the 10 ORIGINAL calibrated
      clips (docs/evidence/court-detection-frames-that-each-find-the.md), a DIFFERENT
      population from my 20 -> 7/10 and my 8/20 are not the same quantity.
  (d) mpc_tuesday's two human labels disagree by 25.4 px (above the wrong-court line)
      -> not usable as truth; shell recall on the 4 trustworthy recordings = 1/4.
- 2026-09-09: DELIVERABLE FINALISED docs/evidence/candidate-proposal-recall.md (7 sections,
  headline for backend-dev at top, §4 retraction of my own "both stages broken" draft in
  place, §6 researcher reconciliation, decisions-for-lead list). Memory written:
  .claude/agent-memory/qa/court-proposal-recall-search-binds.md + MEMORY.md index line.
  Did NOT write docs/DECISIONS_PENDING.md (not on my allowlist) — decisions are in §5 of
  the evidence file and in my report instead.
## TASK STATE: COMPLETE. Nothing outstanding.

---

## TASK — 2026-09-09 (run 2): SEARCH RANKING DEFECT (court only)

Question: on the 9 clips where `selects_against_truth` fired, is the true court PRESENT
in the candidate set but OUT-RANKED, or ABSENT? If mostly absent -> not a ranking defect,
retire cheaply and redirect to proposal generation.
DELIVERABLE: docs/evidence/search-ranking-defect.md
STOP-WHEN: 9 clips characterised + verdict written, or ~40 tool calls.
BARRED INPUT: the retracted `9/20 truth_would_pass` and anything derived from it.
NOTE ALREADY: the brief's "`g>=.33` dominant x11" is the blocker tally of the 11
truth-FAILS clips from that same barred instrument (11 = 20-9). So the x11 attribution
is itself downstream of the barred number and must be re-derived independently before
it can be cited. Flag, do not inherit.

## PRE-REGISTERED PATTERN — written BEFORE looking at any per-clip score

Let S = the 9 clips where `selects_against_truth` fired.
PRESENT-BUT-OUTRANKED on a clip := on at least one audited frame, the candidate set the
ranker actually scored contains a quad within 20.0 px @640 of the human clicks, AND the
ranker selected a different quad that is >20.0 px from the clicks.

- **RETIRE (proposal defect, not ranking):** fewer than 5 of the 9 are
  PRESENT-BUT-OUTRANKED. Then the fire is mostly "truth was never proposed" and the
  thread dies; effort belongs upstream in proposal generation.
- **SYSTEMATIC RANKING DEFECT** requires ALL THREE:
  (R1) >= 5 of 9 PRESENT-BUT-OUTRANKED;
  (R2) ONE named score term is decisive (removing/neutralising that single term alone
       reverses the ordering truth-vs-selected) on >= 2/3 of the R1 clips, the SAME
       term across them;
  (R3) not a tie: median |score(selected) - score(truth)| >= 0.02 on the composite's
       own 0..1 scale (or >= 5% of the observed candidate score range on that frame if
       the composite is not 0..1). Below that = INCIDENTAL TIES / numerical noise.
- **SEVERAL DEFECTS (not one):** R1 holds, R3 holds, but no single term is decisive on
  >= 2/3 -> report as multiple unrelated ranking losses, explicitly NOT one fixable bias.
- **MIXED:** R1 holds but R3 fails -> ties, report as such.

I will not read the criterion off the clusters. A failed bar stays failed.

## LOG (run 2)
- 2026-09-09: journal read (prior task COMPLETE), bar pre-registered above. Next: read
  eval/candidate_audit.py for the definition of `selects_against_truth` and of `g`.
- 2026-09-09: FINDING A (source, decisive). `selects_against_truth` is NOT frame-for-frame.
  candidate_audit.py:187-189: fails = union over ALL frames of terms truth fails;
  lock_ok = union over LOCKED frames of terms a lock passes; against = intersection.
  Truth failing term X on frame 3 and a lock passing X on frame 6 puts X in `against`.
  It is a SUBSET of `truth_fails`, i.e. it INHERITS the barred union artifact rather
  than cancelling it. My own §4 last run said "within-frame ... applies to both sides
  equally" — that was WRONG and the brief inherited it from me. Self-correct.
  The genuinely frame-for-frame quantity in that file is `within_margin` (line 177:
  rt - rl computed on the SAME frame), median over locked frames.
- 2026-09-09: FINDING B (source). explain() models the WHITE path only. autodetect's
  clay/shell fallback (mask_fn is not None) uses rankv = st and a DIFFERENT conjunction
  with no `g >= accept` term at all. So on any clip that locks via the fallback,
  "truth fails g>=.33" names a term that was never applied. Must split clips by path.
- 2026-09-09: FINDING C (source). Ranking has TWO layers: (a) seed plausibility rank
  decides which topk=12 seeds get REFINED at all (hard truncation), (b) rankv =
  g*(0.5+0.5*st) picks among candidates that pass the accept conjunction. A hard filter
  sits between them. "Out-ranked" must be resolved against the right layer.
- 2026-09-09: explain() checked line-by-line against courtfit.py white path: NOT drifted.

---

## TASK — 2026-09-09 (run 3): DOES CAMERA MOTION INVALIDATE THE HUMAN CORNER AUDIT?

Question: for each of the 28 clips the founder reviewed from data/output/corner_audit/,
does the camera move enough ACROSS THE CLIP that the choice of RENDERED frame (frame 0,
render_corner_audit.py's default) vs the frame the corners were PLACED on (gallery mode
= arbitrary mid-clip via eval/collect_frames.py) could flip the founder's verdict?
Measurement about the VIDEO only. I do NOT judge any corner placement.
DELIVERABLE: docs/evidence/camera-motion-verdict-risk.md
HEADLINE NEEDED: how many of the 10 "marked WRONG" verdicts are AT RISK.
STOP-WHEN: measured + verdict written, or ~40 tool calls.
Prior run of this exact brief: killed at ZERO work by a usage limit. Starting clean.

## PRE-REGISTERED BAR — written BEFORE any frame was decoded

QUANTITY: for each clip, estimate the BACKGROUND (static-scene) transform between the
rendered frame (frame 0) and each evaluation-sampled frame (eval/run_refs.frame_positions,
k=8). Apply that transform to the FOUR HUMAN-CLICKED CORNERS of that clip and take the
max over corners; then D_clip = max over sampled frames. Units: px at width 640
(same units as WRONG_PX_640). Rationale: this is exactly the apparent corner displacement
a CORRECT placement would show if rendered on the wrong frame — the quantity that could
make a correct placement look wrong to an eye.

BANDS (justified from WRONG_PX_640 = 20.0, the project's own wrong-court distance):
- **AT RISK: D_clip >= 20.0 px@640.** Frame choice alone can produce a displacement at
  or beyond the distance at which this project calls a court wrongly placed. A correct
  placement can therefore render as wrong-court-sized error. Verdict not trustworthy
  from the sheet alone.
- **WATCH: 10.0 <= D_clip < 20.0 px@640.** Half the wrong-court line. Below the formal
  bar but inside the range where accepted-correct courts already live (3.4-13.9 px), so
  a strict eye on a marginal call could be swayed. Reported, but NOT counted in the
  headline "at risk" number.
- **SAFE: D_clip < 10.0 px@640.** Frame choice cannot plausibly account for a verdict.

HEADLINE = count of the 10 WRONG-marked clips with D_clip >= 20.0 (AT RISK band only).

GROUP COMPARISON (control), also pre-registered: motion is a PLAUSIBLE DRIVER of the
wrong/correct split only if the WRONG group's median D_clip is >= 10.0 px@640 higher
than the CORRECT group's median. Otherwise motion did not produce the split and I say so.

UNMEASURABLE clips get named with the reason; they are NOT counted as SAFE.

A failed bar stays failed. I will not read the threshold off the results.

## LOG (run 3)
- 2026-09-09: journal read (runs 1-2 complete), T26 read, bar pre-registered above.
  Next: locate the 28 clips' videos + _pts.json, read frame_positions(), then measure.
- 2026-09-09: MEASURED all 28/28 clips (ORB+RANSAC similarity, frame0 -> each of the 8
  eval-sampled frames, corner displacement in px@640). Script:
  scratchpad/measure_motion.py, raw scratchpad/motion.json.
  INSTRUMENT CONTROLS PASS ON EVERY CLIP: null (frame vs itself) = 0.000 px@640 on all
  28; positive control (inject known 8.000 px@640 translation) recovered 7.95-8.10 on
  all 28. So the instrument is validated per-clip, not just once.
  HEADLINE: 7 of the 10 WRONG-marked clips are AT RISK (D>=20 px@640); 1 more is WATCH.
  AT RISK(wrong): A7vXlWIlyrI 162.6, HoHxFSX_gLk_s3 212.9, HoHxFSX_gLk_s1 119.4,
  sAjkpeRq4P4 80.4, bump_ntrp30 60.5, CYqapSq5llo 38.8, UHf0LeMU2pg 29.2.
  WATCH: uR5q2cSM6AY 13.2 (frame-corner 20.5). SAFE: L73ep7JHiJ4 5.95, demo30 0.04.
  CORRECT group: 2 AT RISK (HoHxFSX_gLk_s2 110.5, bump_ntrp30b 40.2), 1 WATCH
  (am_hard_utr 11.9), 15 SAFE (13 of them <0.5 px -- all 10 shell + tc8 + yt_match40 +
  yt_rally2 are locked-off tripods).
  GROUP MEDIANS: WRONG 49.6 vs CORRECT 0.30 -> gap 49.3 px, my pre-registered >=10 px
  gap for "motion is a plausible driver of the split" is MET.
  MECHANISM: mostly NOT drift. Step changes (bump_ntrp30 0.03->60.4 at pos 508;
  UHf0LeMU2pg 0.1->27.4 at 4198; CYqapSq5llo 1.1->37 at 18129) = SCENE CUTS/zoom
  changes. sAjkpeRq4P4 is the striking one: ALL 8 eval frames sit at scale 0.734 vs
  frame 0, i.e. frame 0 is a DIFFERENT (zoomed-in) shot from the entire scored body of
  the clip -- the lead's one-clip check compared frame 0 with frame 500, both inside
  that opening shot, so it could not have seen this. MUST RENDER TO CONFIRM.
  INSTRUMENT QUALIFIER (stated, not a moved bar): rows with <30 RANSAC inliers and
  wild scale/rot (e.g. scale 0.0014, rot 177deg) are NOT displacement estimates, they
  are "no common background" = a cut. Excluded from the max; counted separately.
  HoHxFSX_gLk_s1 (3 rows), _s3 (3), _s2 (2) have such rows. Excluding them LOWERS
  those clips' D, so it cannot inflate the headline.
  NEXT: render frame0-vs-eval-frame pairs for sAjkpeRq4P4, bump_ntrp30, A7vXlWIlyrI,
  HoHxFSX_gLk_s3, bump_ntrp30b and LOOK before writing the claim.
- 2026-09-09: RENDERED AND LOOKED (scratchpad/pair_*.png). Mechanism CONFIRMED visually:
  A7vXlWIlyrI frame 0 is a MONOCHROME intro frame at a different zoom (and the shipped
  sheet data/output/corner_audit/A7vXlWIlyrI_corners.png is that same greyscale image,
  captioned "frame 0" in its own header -> sheets ARE frame 0, confirmed not assumed).
  sAjkpeRq4P4 frame 0 = zoomed-in opener with a title banner; f5262/f18795 are wider.
  Lead's f0-vs-f500 check could not see it (f500 is inside the opening shot; eval starts
  at f5262). sAjkpeRq4P4 verdict is AT RISK, contradicting the spot-check.
  HoHxFSX_gLk_s3 f1808 is a DIFFERENT VENUE (different trees/shadows/fence).
  bump_ntrp30 + _30b: clean step at f508 (60.4 / 40.1 px), one framing change mid-clip.
- 2026-09-09: DELIVERABLE WRITTEN docs/evidence/camera-motion-verdict-risk.md.
  Headline 7/10 AT RISK + 1 WATCH (uR5q2cSM6AY, borderline, 13.2 corners / 20.5 frame),
  2 SAFE (L73ep7JHiJ4 5.95, demo30 0.04). Group gap met (49.6 vs 0.30) BUT reported as
  confounded with clip type (13 of 18 correct-marked are locked-off tripods) and neither
  necessary nor sufficient. Also flagged the direction the brief did not anticipate:
  2 of the 18 CORRECT verdicts (HoHxFSX_gLk_s2 110.5, bump_ntrp30b 40.2) are equally
  unsupported -> false EXONERATION risk. Named unmeasurables: HoHxFSX_gLk_s3 f3044
  decode fail; eala_segment has no clicked pts file (only the excluded eala_pts_auto.json).
## TASK STATE: COMPLETE. Deliverable written. Nothing outstanding.

---

## TASK — 2026-09-09 (run 4): DOES CAMERA MOTION DEGRADE COURT *ACCURACY*/AGREEMENT?

Question (two parts, one study):
1. INTER-FRAME DISAGREEMENT: fit the court independently on each of the 8
   run_refs.frame_positions frames of each of the 20 run_refs clips; measure how far
   those 8 fits disagree with EACH OTHER in px@640. Does it track the per-clip camera
   displacement I measured yesterday (scratchpad/motion.json)?
2. IS THE DISAGREEMENT REAL OR APPARENT: warp each frame's fit into a common frame's
   pixel space using yesterday's background transform, re-measure. If disagreement
   largely vanishes, the vote is partly rejecting CAMERA MOTION, not bad detections.
   WIDTH reported as a named dimension of the same measurement (STATE's open row).

DELIVERABLE: docs/evidence/camera-motion-vs-court-agreement.md
STOP-WHEN: measured + written, or ~40 tool calls.
REUSE: scratchpad/motion.json (per-clip per-frame background similarity transform,
frame0 -> each eval frame, ORB+RANSAC, null 0.000 and +8px positive control passed on
all 28 clips). Same 8 frame positions as this run => directly composable.

## PRE-REGISTERED BAR — written BEFORE any court fit was run

DEFINITIONS.
- Per clip c, per frame i in the 8 eval positions: run the same per-frame court fit the
  vote consumes (cf.auto_fit_frame). Frames with no fit are NOT counted as agreement.
- RAW DISAGREEMENT D_raw(c) = median over all pairs (i,j) of locked frames of the mean
  distance between the two quads' 4 corners, in px@640, compared IN RAW PIXELS
  (i.e. exactly what the vote compares).
- COMPENSATED DISAGREEMENT D_comp(c) = same, but each frame i's quad is first mapped
  into frame 0's pixel space by yesterday's background similarity transform (inverse of
  frame0->i). Frames flagged as CUTS (no common background) are excluded from D_comp
  and NAMED, not silently dropped.
- M(c) = that clip's measured background displacement (Dc from motion.json).
- A clip needs >= 2 locked frames to have a D at all; clips with <2 are UNMEASURABLE and
  named, never counted as agreeing.

BAR 1 — DOES MOTION DRIVE RAW DISAGREEMENT?
- MOTION DRIVES IT if BOTH: (a) Spearman rho(M, D_raw) >= +0.60 over the measurable
  clips, AND (b) median D_raw among clips with M >= 20.0 px@640 exceeds median D_raw
  among clips with M < 20.0 by >= 20.0 px@640 (one full wrong-court distance).
- MOTION DOES NOT DRIVE IT if rho <= +0.20 OR the group median gap is < 10.0 px@640.
- INDETERMINATE otherwise. I will say INDETERMINATE rather than round.

BAR 2 — IS THE DISAGREEMENT APPARENT (motion) OR REAL (detection)?
Restricted to the HIGH-MOTION clips (M >= 20.0) that are measurable.
- APPARENT / THE VOTE PENALISES MOTION if median (D_raw - D_comp) >= 20.0 px@640 AND
  median D_comp < 20.0 px@640 — i.e. compensation moves the disagreement from above the
  wrong-court line to below it. That is the "the vote is rejecting camera motion" finding.
- REAL if median D_comp >= 20.0 px@640, i.e. the fits still describe different physical
  courts after motion is removed. Then the disagreement is a detection problem.
- PARTIAL if D_raw - D_comp >= 20.0 but D_comp is still >= 20.0. Report as partial.

BAR 3 — WIDTH DIMENSION.
W(c) = median over locked-frame pairs of |width_i - width_j| / mean(width) as a fraction,
where width = the fitted quad's baseline width in COURT-NORMALISED terms (compare the
two homographies' image-space width of the doubles baseline).
- WIDTH DISAGREEMENT IS LINKED TO ZOOM if median W among clips whose motion.json rows
  show a scale change |log s| >= log(1.05) (i.e. >=5% zoom) is >= 2x the median W among
  clips with |log s| < log(1.02). Otherwise NOT LINKED, report the numbers.

POWER, STATED IN ADVANCE — n = 20 clips, and from yesterday only ~6-8 of the 28 audited
clips carry M >= 20; inside the 20-clip run_refs pool the high-motion group is likely
4-6 clips. A Spearman rho on n=20 with a 4-6 clip high group is WEAK evidence: at n=20,
rho=0.60 is around p=0.005 two-sided but the high group carries almost all the leverage,
so one clip can move it. I will report the group sizes with every correlation and will
not present rho alone as a finding.
CONFOUND, stated in advance: source type (short locked-off 4K tripod shell clip vs long
edited YouTube/broadcast clip) predicts BOTH motion and surface. Any motion effect here
is inseparable from a surface effect on this pool. I will say so in the verdict.

BARRED (from the brief, and I hold to them):
- May NOT conclude camera motion explains the 40% proposal recall (the three 0/8 clips
  are static tripods).
- Lock rate is NOT correctness. "Locked 8/8" never means "correct 8/8".
- No number scored against the human-clicked pool is quoted as ACCURACY without the
  caveat that those calibrations are under review (T26, docs/evidence/
  calibration-provenance.md, 7 of 10 flagged verdicts unresolved).

A failed bar stays failed. I will not read a threshold off the results.

## LOG (run 4)
- 2026-09-09: journal + camera-motion-verdict-risk.md read; scratchpad/motion.json from
  run 3 confirmed present in THIS session's scratchpad (same session id) => reusable.
  Bar pre-registered above BEFORE any fit. Next: read run_refs.py frame_positions + the
  per-frame fit call, then build the fit harness.
- 2026-09-09: SOURCE FINDING (relevant, not a fix): courtfit.AGREE_PX = 30.0 is compared
  in the clip's RAW pixels (courtfit.py:774, _corner_dist at 778, used at 789) and is NOT
  resolution-scaled, unlike CLAUDE.md's "every pixel threshold scales by frame_height/720".
  So the vote's agreement window is 30 px@640 on a 640-wide clip but only 5.0 px@640 on the
  3840-wide shell clips - 6x stricter on shell. The pixel-space agreement test therefore
  penalises RESOLUTION, which is a real answer to "does it penalise anyone specifically".
- 2026-09-09: harness scratchpad/interframe_agreement.py running (20 clips, 8 eval frames
  each, auto_fit_frame + ORB/RANSAC frame_i->frame_0eval similarity + courtfit.consensus
  re-invoked on compensated quads). Per-clip controls PASS on every clip so far: null
  0.000 px@640, positive 7.98-8.03 vs an injected 8.000.
  INTERIM (13/20): A7vXlWIlyrI D_raw 44.2 -> D_comp 20.1; HoHxFSX_gLk_s2 41.6 -> 15.7
  (CROSSES the 20 line, votes 2->3); HoHxFSX_gLk_s1 116.5 -> 69.5; CYqapSq5llo 32.5 ->
  26.4 (votes 2->4). BUT the SHELL clips are the decisive control: static (max|log s|
  <= 8e-05), compensation changes D by <0.02 px, and D_raw is still 20.8-37.5 px@640
  (flexi_joy_p07 37.5, hillsborough_p08 36.3, flexi_joy_p01 29.9, hillsborough_p02 31.9).
  => a large part of the disagreement is REAL and has nothing to do with camera motion.
  mpc_mixed_p02 locked 0/8 -> UNMEASURABLE by my own bar, named not counted.
- 2026-09-09: ALL 20 MEASURED + within-eval-window motion measured separately
  (scratchpad/window_motion.py -> window_motion.json). CRITICAL: yesterday's M (vs VIDEO
  frame 0) is NOT the covariate this question needs - sAjkpeRq4P4 is 80.4 px vs frame 0
  but only 3.6 px WITHIN the eval window. Added M_win and used it as primary; disclosed
  that the pre-registered bar named M = Dc.
  INSTRUMENT VALIDATED THREE WAYS: (1) per-clip null 0.000 / positive 7.98-8.03 px@640
  on all 20; (2) my lock counts match the shipped ai_court_audit index EXACTLY on all 9
  clips the brief named (mpc_mixed_p02 0, mpc_mixed_p08 0, mpc_tuesday_p07 0,
  mpc_tuesday_p01 1, flexi_joy_p01 2, sAjkpeRq4P4 8, HoHxFSX_gLk_s2 8, CYqapSq5llo 8,
  uR5q2cSM6AY 8); (3) accepted 2/20 on references, matching STATE:196's classical arm
  "References: 2/20" exactly. resolved_proposer() == "classical" (shipped arm confirmed).
  VERDICTS vs the pre-registered bar:
  BAR1 INDETERMINATE. rho(M_win,D_raw)=0.474 (bar needed >=0.60 for "drives", <=0.20 for
  "does not"); hi(M_win>=20,n=5) med D_raw 44.2 vs lo(n=11) 25.6, gap 18.6 (bar 20.0 for
  "drives", <10.0 for "does not"). BOTH halves land in the dead band. Not rounded.
  BAR2 PARTIAL. hi clips med D_raw 44.2 -> D_comp 26.4, med drop 24.0 px@640 (>= the 20
  px bar) BUT D_comp still 26.4 >= 20 => PARTIAL by my own definition, not APPARENT.
  DECISIVE CONTROL: lo clips med D_comp 24.8 vs hi 26.4 - after motion is removed the two
  groups are the SAME. Compensation is a 0.01 px no-op on the low group (as it must be).
  Pool: D_raw >=20 on 13/16 measurable, D_comp >=20 on 12/16. EXACTLY ONE clip crosses
  (HoHxFSX_gLk_s2 41.6 -> 15.7). votes changed on 2 clips (CYqapSq5llo 2->4,
  HoHxFSX_gLk_s2 2->3); ZERO clips changed ACCEPTANCE (nothing reached ACCEPT_VOTES=6).
  BAR3 LINKED, but underpowered - say so. zoom(|log s|>=5%, n=3) med W_near 16.4% vs
  static(n=12) 7.1%, ratio 2.30 vs a pre-registered 2.0. Compensation drops the zoom
  group to 6.5%, i.e. onto the static baseline. BUT 8 of 12 fully static clips still
  disagree about width by >=5% => zoom explains the EXCESS on 3 clips, NOT STATE's row.
- 2026-09-09: NOT-NEW: my AGREE_PX resolution finding is ALREADY recorded -
  docs/evidence/agree-px-is-6-tighter-on-4k.md (30 / 10.0 / 5.0 px@640 at 640/1920/3840;
  scaling it is a no-op on gold, 0->2 on shell, but ADMITS TWO WRONG COURTS on the 1920
  references, tc8CGFxyRE8 58.7 and e8T34KoJzOw_s2 28.7). Cite, do not re-claim. This is
  the real answer to "does the pixel agreement test penalise anyone specifically": it
  penalises RESOLUTION, not motion.
- 2026-09-09: DELIVERABLE WRITTEN docs/evidence/camera-motion-vs-court-agreement.md.
## TASK STATE: COMPLETE.

---

## TASK — 2026-09-09 (run 5): CAN THESE CLIPS SUPPORT A SINGLE CALIBRATION AT ALL?

Question: for each affected clip, is there ONE camera setup covering enough of the 8
`run_refs.frame_positions` frames to support a calibration — and if so, WHICH frames?
Measurement of CLIP STRUCTURE only. I do NOT judge any corner placement, and a
single-setup clip can still be badly calibrated (explicitly BARRED from concluding
anything about WHY a placement is wrong).

POPULATION (9 affected + 1 positive control):
HoHxFSX_gLk_s1, HoHxFSX_gLk_s2, HoHxFSX_gLk_s3, bump_ntrp30, A7vXlWIlyrI, CYqapSq5llo,
UHf0LeMU2pg, uR5q2cSM6AY, bump_ntrp30b + CONTROL sAjkpeRq4P4.
Adding negative controls (my call): 2 static shell tripods, flexi_joy_p01 + hillsborough_p02
(measured at 0.0-0.1 px@640 of motion in run 3/4) — they MUST come back 8/8 one setup.

DELIVERABLE: docs/evidence/clip-shot-map.md
STOP-WHEN: measured + written, or ~35 tool calls.

## PRE-REGISTERED BAR — written BEFORE any pair was estimated

SAME-SETUP EDGE (i,j), between two of the 8 sampled frames, requires ALL of:
  (E1) >= 30 RANSAC inliers on the ORB background match (the same "no common
       background" cut-off used in run 3 / run 4, carried over unchanged);
  (E2) sane similarity parameters: 0.5 <= scale <= 2.0 AND |rotation| <= 30 deg.
Anything failing E1 or E2 = NO EDGE = "different camera setup / no common background".
Rationale for E1/E2: these are the exact criteria already used and validated in this
session's two prior runs (null 0.000, +8px positive control recovered on all 28 clips);
re-using them unchanged means this run cannot be accused of picking a cut-off to fit.

NON-TRANSITIVITY, handled not assumed away. "Same setup" is a noisy relation and need
not be transitive. I therefore compute BOTH and report both:
  - CC = connected components (transitive closure; the OPTIMISTIC grouping — a chain
    of weak links merges two genuinely different setups).
  - CLIQUE = largest set of frames that are ALL pairwise linked (the STRICT grouping;
    a setup by every pairwise test at once). n=8 so exhaustive enumeration is exact.
  - G(c) = size of the largest CLIQUE. The clique is PRIMARY because a calibration
    placed on one frame must be valid on every other frame in the group SIMULTANEOUSLY
    — that is the pairwise-simultaneous condition the vote imposes. CC is reported as
    the optimistic bound; where CC > CLIQUE I say so explicitly.

BAR, justified from the project's own acceptance rule, NOT from the data:
`courtfit.ACCEPT_VOTES = 6` of `ACCEPT_K = 8`. A calibration can only be accepted if
>= 6 of the 8 sampled frames agree with it. A single camera setup covering < 6 frames
therefore cannot pass the vote no matter who places the corners.
  - PASS (RE-PLACEABLE): G(c) >= 6. Name the frames.
  - FAIL-RESTRICT: 2 <= G(c) <= 5 — a usable window exists but is narrower than the
    current sampling; cannot pass the 8-frame vote as sampled today.
  - FAIL-DROP: G(c) <= 1 — no window supports a calibration across sampled frames.
Note in advance: 6/8 is NECESSARY, not sufficient — a clip can be single-setup and still
uncalibratable for reasons this measurement does not see. I will state that.

CONTROL GATE, pre-registered as a stop condition: sAjkpeRq4P4 must return G = 8 (one
setup, all 8 frames). If it does not, my grouping is miscalibrated, NOTHING else in the
run is trusted, and I say so and STOP. Same for the 2 shell negative controls.

A failed bar stays failed. I will not read the threshold off the results.

## LOG (run 5)
- 2026-09-09: journal read (runs 1-4 COMPLETE). Bar pre-registered above BEFORE any
  pair estimated. Scratchpad CONFIRMED same session id aad66fbf => motion.json,
  measure_motion.py, window_motion.py all present and reusable.
- 2026-09-09: NOTE the covariate trap I hit in run 4 applies here too: motion.json is
  frame0->eval-frame. This run needs PAIRWISE among the 8 eval frames only. Frame 0 is
  NOT one of the 8 and must not enter the grouping.
- 2026-09-09 (RESUMED after usage-limit kill; bar above recovered VERBATIM, not
  re-derived). Wrote scratchpad/shot_map.py: all 28 pairs among the 8 eval frames per
  clip, ORB+RANSAC partial-affine; edge = inl>=30 & 0.5<=s<=2.0 & |rot|<=30 (the E1/E2
  in the bar above). Reports G = largest CLIQUE (exhaustive, n=8) AND CC (connected
  components) so non-transitivity is measured, not assumed away. Per-clip controls:
  null (frame vs itself, must be an edge ~0px), positive (+8px@640, must be an edge and
  recover ~8), NEGATIVE (frame vs a frame from a DIFFERENT clip, must be NO edge) —
  the negative control is new this run and is what actually validates the grouping.
  DISCREPANCY I must disclose, not hide: the bar's E2 (0.5-2.0 scale, 30 deg) says it
  re-uses run 3/4 unchanged, but run 3/4 code actually used 0.33-3.0 and 25 deg. I honour
  the JOURNAL's E2 as primary (it is the pre-registered text) and will report a
  sensitivity check under run3/4's numbers rather than swap the bar.
  Output: scratchpad/shot_map.json.
- 2026-09-09: MEASURED all 12. CONTROL GATE PASSES: sAjkpeRq4P4 G=8, 28/28 pairs, one
  component. Shell negcontrols 8/8 (0.1-0.4 px). Null 0.000 and +8px recovered 7.91-8.05
  on all 12. NEW negative control (frame vs a DIFFERENT clip's frame) = NO EDGE on 11/11
  (3-12 inliers) => the criterion can say "different setup". Sensitivity check under
  run3/4's 0.33-3.0 / 25deg: G IDENTICAL on all 12 => the E2 discrepancy is a no-op.
  VERDICTS: PASS(G>=6) sAjkpeRq4P4 8, HoHxFSX_gLk_s2 6 (borderline, exactly on the line),
  bump_ntrp30 8, A7vXlWIlyrI 8, CYqapSq5llo 8, UHf0LeMU2pg 8, uR5q2cSM6AY 8,
  bump_ntrp30b 8. FAIL-RESTRICT: HoHxFSX_gLk_s1 G=5, HoHxFSX_gLk_s3 G=4. FAIL-DROP: NONE.
  NON-TRANSITIVITY MEASURED, DID NOT BITE: CC_max == G on all 12 clips.
  THE BIG CAVEAT, and it is load-bearing not boilerplate: my E1/E2 edge only asks
  "common background under a SIMILARITY", which a 188 px@640 / 40% zoom camera move
  still satisfies. A7vXlWIlyrI is G=8 with 188.3 px max intra-clique displacement =>
  one homography CANNOT hold there, yet it PASSES the bar. Did NOT move the bar.
  Reported a labelled SECONDARY S20 = largest all-pairwise-linked set also within
  WRONG_PX_640=20.0 (an EXISTING project constant, not a new threshold of mine):
  sAjkpeRq4P4 8, CYqapSq5llo 7, uR5q2cSM6AY 5, UHf0LeMU2pg 4, bump30 4, bump30b 4,
  HoHxFSX_gLk_s2 3, A7vXlWIlyrI 3, s3 2, s1 1. S20 independently reproduces run 3's step
  positions (bump 508, UHf0LeMU2pg 4198, CYqapSq5llo drops only 5076) from a different
  direction => two instruments agree on the cut positions.
  POOL: run_refs = 20; only 7 of the 10 population clips are IN it. NOT in pool:
  HoHxFSX_gLk_s3, bump_ntrp30, bump_ntrp30b. POOL-SIZE ANSWER FOR THE FOUNDER:
  by the bar N=1 (HoHxFSX_gLk_s1 only) => 20->19, 5%. Under the tight S20 reading N=4
  (s1, s2, A7vXlWIlyrI, UHf0LeMU2pg) => 20->16, 20% (uR5q2cSM6AY at 5 a marginal 5th).
- 2026-09-09: DELIVERABLE WRITTEN docs/evidence/clip-shot-map.md (8 sections, control
  first, per-clip grouping + G + verdict + recommendation, S5 the instrument limitation,
  S7 the pool-size number, S4 non-transitivity).
## TASK STATE: COMPLETE.

---

## TASK — 2026-09-09 (run 6): MIXTURE vs PRECISION FLOOR falsifier (court only)

Question: are the per-frame court quads on a clip ONE noisy blob (precision floor of the
line-fit solver at 4K) or SEVERAL distinct tight hypotheses alternating (mixture)?
Kill condition: PRECISION FLOOR => researcher's part (a) is WRONG and the classical court
path has a real ceiling => closes a direction. Report a negative as willingly as a positive.

DELIVERABLE: docs/evidence/mixture-vs-precision-floor.md
STOP-WHEN: verdict written, or ~25 tool calls.

## PRE-REGISTERED BAR — from docs/evidence/court-recall-what-would-actually-move-it.md
   §4.1, written by someone else BEFORE I was asked. Honoured verbatim, not re-derived.

Single-linkage cluster each clip's per-frame court quads at 12 px@640.
- MIXTURE if >= 6 of ~12 clips give >= 2 clusters, with within-cluster <= 8 px@640 AND
  between-cluster >= 25 px@640.
- PRECISION FLOOR if >= 6 clips give a SINGLE cluster, OR within-cluster spread
  >= 15 px@640.
- Anything else: INDETERMINATE. Do not round toward either reading.

NOT-THIS-RUN: judging corner placement, editing pts/backup, changing any threshold,
STATE.md, git commit, ball/speed/score/mobile, proposing a fix.

## LOG (run 6)
- 2026-09-09: journal read (runs 1-5 COMPLETE). Bar copied verbatim above. Scratchpad
  confirmed same session: interframe.json (run 4, 20 clips x 8 eval frames, auto_fit_frame
  quads + ORB compensation), motion.json, window_motion.json, shot_map.json all present.
  Next: check whether interframe.json stores the raw per-frame QUADS (needed for
  clustering) or only pairwise distances.
- 2026-09-09: interframe.json stores ONLY per-clip medians/max (D_raw, D_comp, W_*),
  NOT the pairwise matrix and NOT the quads. So the bar's "no new measurement required /
  no footage decode" is WRONG: quads must be RECOMPUTED. Wrote scratchpad/modality.py —
  same auto_fit_frame on the same 8 run_refs.frame_positions frames, single-linkage at
  12 px@640 in RAW pixels (primary) and MOTION-COMPENSATED (ORB, so camera motion cannot
  manufacture a mode). Pool: 20 (run_refs.EXCLUDED_CLIPS cleared IN MEMORY ONLY, repo
  file untouched) with strict16 flag per row so the two populations never mix.
- 2026-09-09: 14/20 done. REPRODUCIBILITY CONTROL PASSES — my all-pairs medians match
  run 4's D_raw to 2dp on every clip (A7 44.16/44.16, s2 41.64/41.6, CYq 32.5/32.5,
  flexi_joy_p07 37.53/37.5, hills_p02 31.86/31.9, hills_p08 36.26/36.3) => the fit is
  deterministic and this is the same quantity, recomputed not re-derived.
  SHAPE SO FAR, and the bar has a SPECIFICATION GAP I must report not patch: many clips
  come back ALL-SINGLETON (flexi_joy_p07 sizes [1,1,1,1,1], hills_p08 [1,1,1]) — no two
  frames within 12 px. Then within-cluster median is UNDEFINED, so the clip satisfies
  NEITHER "within<=8 => MIXTURE" NOR "1 cluster or within>=15 => PRECISION FLOOR".
  By the letter those are INDETERMINATE. Note all-singleton is what a sigma~30 px SCATTER
  predicts under a 12 px linkage, and is the OPPOSITE of repeated modes — I will report
  that as a clearly-labelled SECONDARY reading, and will NOT move the bar to collect it.
  flexi_joy_p01 (one of the 4 motivating clips) locks only 2/8 => its 29.9 px figure rests
  on a SINGLE pair and it is UNMEASURABLE under the bar's own >=3-locked-frames rule.
- 2026-09-09: ALL 20 MEASURED. VERDICT = INDETERMINATE on both populations; the KILL
  CONDITION DID NOT FIRE (this neither closes nor confirms researcher's part (a)).
  strict-16 measurable n=11: MIX 4 / PF 1 / IND 6 (bar needed >=6 either way).
  excluded-4: MIX 1 / IND 3. pooled-20 measurable n=15: MIX 5 / PF 1 / IND 9.
  MIXTURE: e8T34KoJzOw_s2, sAjkpeRq4P4, tc8CGFxyRE8, uR5q2cSM6AY (+UHf0LeMU2pg excluded).
  PRECISION FLOOR: flexi_franz_p01 only (k=1, and on just 3 pairs - thin).
  TWO THINGS THAT MATTER MORE THAN THE HEADLINE:
   (1) ALL 5 MIXTURE verdicts are 1920-wide; 0 of 5 measurable 3840 shell clips is MIXTURE
       => the mixture reading cannot be carried onto shell, which is where the product
       problem is. Shell is also underpowered: 5 of 10 shell refs lock <3 of 8 frames.
   (2) The 4 MOTIVATING static 4K tripods: flexi_joy_p01 UNMEASURABLE (its 29.9 px is ONE
       pair), hills_p02 3 pairs (within 8.75 vs bar <=8 -> misses MIXTURE by 0.75 px),
       hills_p08 3 pairs all-singleton, joy_p07 10 pairs all-singleton.
  SENSITIVITY (check, bar not moved): thr 8/10/12/16 never reaches 6 either way on
  strict-16; PF only reaches 6 at thr 20-25, i.e. by calling the wrong-court distance
  "the same court". Compensated clustering changes NO verdict (only s2 k 5->2).
  CONTROL: my all-pairs medians reproduce run 4's D_raw to 2dp on all 8 checked clips.
- 2026-09-09: DELIVERABLE WRITTEN docs/evidence/mixture-vs-precision-floor.md (9 sections;
  §1 reused-vs-recomputed - the bar's "no new measurement required" was WRONG, interframe.json
  keeps only medians so every quad was RECOMPUTED; §5 the bar's SPECIFICATION GAP: 4 clips are
  ALL-SINGLETON so within-cluster median is undefined and they satisfy NEITHER branch - flagged
  for §4.1's owner to resolve BEFORE seeing which clips it moves, not patched by me).
## TASK STATE: COMPLETE.
