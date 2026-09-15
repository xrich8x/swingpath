# pm — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

Write DURING the work. Rewrite TASK/STATE in place; append to LOG; compact past ~30 lines.
Durable learnings -> `.claude/agent-memory/pm/`. Findings -> `docs/evidence/`.

---

## TASK — what I was asked to do

2026-09-15 (NEW RUN). **P5 — THE CAPTURE PROTOCOL. Build an artefact the founder executes at a
court.** ONE deliverable: `docs/CAPTURE_PROTOCOL.md` + add a row to CLAUDE.md's doc-map table
(150 non-blank-line cap — if breached, propose what comes out, do not exceed silently).
Must contain: (1) printable TARGET SHEET, exact court coords + offsets from lines, from
`backend/swingvision/court.py` constants — do not invent dimensions; (2) step-by-step run sheet;
(3) two framings + two mount heights, concrete; (4) pre-registered success criterion FOR THE VISIT
ITSELF, checkable before packing up; (5) what each artefact feeds.
BAR: >=30 landing points known to <=3 cm INDEPENDENT of video, >=2 surfaces; my delta supersedes:
**>=30 per DIRECTION CLASS**. Marks must span BOTH range and lateral offset (R1b: 0.049 m on
centreline -> 0.348 m at doubles sideline; 72.9% -> 20.0%). Capture floor HARD 60fps AND 1080p.
Mount fixity is what binds (static tripod 0.1-0.4 px bg displacement; our best "compliant" clip
6.3 px). Calibrate-LAST. Audio bounce timing: price the 29 ms/10 m = 1.75 frames at 60 fps
propagation delay, recommend or reject WITH ARITHMETIC. One person, one session, priced in minutes.
ON-DEVICE CATCH must be stated in plain words: tape measure / chalk / 2nd camera used ONLY to build
truth is a LAB INSTRUMENT, not a product dependency — NOT a scope violation.
NOT THIS RUN: no STATE row, no SPEC edit, no code.

### PRIOR RUN (complete, for context only)
2026-09-15. **SCOPE OPTIONS FOR THE FOUNDER AFTER P1 + R1.** ONE deliverable: APPEND a
fifth entry to `docs/DECISIONS_PENDING.md` (a 2026-09-12 P4 entry with four contradictions
already sits there awaiting a ruling — CROSS-REFERENCE it, do not duplicate).

Five questions to answer:
1. What does v1 CLAIM given a blind axis? Is a per-direction / per-line accuracy floor the
   honest shape for SPEC §3? Say what I would put in §3.
2. Rank the three renegotiation shapes (a) refuse by geometry+covariance (b) move the
   CAPTURE spec (collides with "regardless of mount height") (c) depth-dependent bar or
   margin-based in/out call. Add any missing.
3. Does a blind axis change "what v1 outputs, end to end"? (bounce location / in-out /
   refusal). A margin call is a DIFFERENT PRODUCT from a landing coordinate — I own that.
4. Refusal rate: honest target, or does P2's occlusion census have to land first?
5. Does R1 change the REQUIREMENTS of P5 (the court-visit capture protocol)? P5 is top of
   queue because P3 fired: we own NO clip >=60fps AND >=1080p AND fixed-mount AND high.

NOT THIS RUN: implementation plan, picking an estimator route (R2-R7 not mine), ANY edit
to docs/SPEC.md (LOCKED, founder only moves a bar). No code.
BINDING: Bar A stays FAILED. Do not propose pose/§6 occlusion/stereo/2nd camera/court
auto-detect/ball-detector work. Label PRODUCT JUDGEMENT vs MEASUREMENT visibly. Carry the
synthetic caveat (i.i.d. Gaussian noise, uniform flight population -> 6.1% may be
pessimistic by an unknown amount).

## STATE — where I got to

**P5 RUN COMPLETE.** `docs/CAPTURE_PROTOCOL.md` WRITTEN (11 sections, target sheet + run sheet +
gates + artefact map + time budget + open questions). Two memory files written and indexed
(truth-is-built-at-capture-not-labelled, audio-bounce-timing-accepted-with-slate).
**CLAUDE.md NOT EDITED — it is on my forbidden list AND it is at exactly 150/150 non-blank lines
(measured), so any added row breaches the cap.** Handed the lead a ZERO-LINE-DELTA in-place
amendment instead. No STATE row, no SPEC edit, no code. Remaining: nothing.
All source docs read (P5-scope entry, P3 census, P1 ceiling, R1+R1b,
SPEC §1-§9, court.py). Design settled in head; writing `docs/CAPTURE_PROTOCOL.md` now.
**KEY DESIGN DECISIONS — do not re-derive if killed:**
1. Truth is made BALL-FIRST, not mark-first: the ball leaves a print (coloured chalk/talc on hard,
   natural ball mark on clay); you tape-measure the PRINT's offset from the line. Mark-first
   ("hit the mark") rejects ~90% of balls and is the wrong design. Marks are AIM POINTS + FIDUCIALS.
2. TRUTH DEFINITION pinned: first contact = the REAR (incoming-side) edge of the print, not centre.
   A skid print is 6-8 cm long; centre-vs-contact ambiguity alone blows the 3 cm budget.
3. ITF convention: all court measurements are to the OUTSIDE of the lines (centre service line to
   its CENTRE). court.py does NOT document this. 5 cm paint = 1.7x the 3 cm budget if got wrong.
4. THE LEVER IS CAMERAS, NOT BALLS. Measuring a print is the bottleneck; every extra camera on the
   same bounce is free. 2x2 (2 heights x 2 framings) must be SIMULTANEOUS -> paired tests, and 4
   devices turn one ball session into four answers. Extra cameras = LAB INSTRUMENT (on-device catch).
5. FRAMING B (far-half tele) CANNOT BE CALIBRATED BY THE SHIPPED FOUR-TAP — the near corners are out
   of frame. That is why the F-mark fiducials earn their place.
6. AUDIO TIMING: ACCEPT, with mandatory correction + a 10-CLAP SLATE. Uncorrected bias is
   +1.17 frames (near baseline) to +5.28 frames (far corner) at 60 fps — range-dependent, so it
   would be misread as estimator bias. Corrected residual ~±0.15 frames vs a ±1 bar.
7. BALL MACHINE at the far baseline is what makes it a ONE-PERSON job. Without one, a helper is
   REQUIRED (or ~4 h solo).
8. Station layout: 8 ALONG stations (obliquity 0 / 4.115 / 5.485 m) x 3 range bands, 5 balls each
   = 40; 5 ACROSS stations x 8 (C2 gets 10) = 42. >=30 clean per class with 20% reject headroom.
9. CANNOT edit CLAUDE.md (allowlist). Hand the lead the exact doc-map row + the line-count
   arithmetic instead.

### PRIOR RUN
**RUN COMPLETE.** Deliverable APPENDED to `docs/DECISIONS_PENDING.md` as
"2026-09-15 — P5-scope: THE CAMERA IS BLIND IN ONE AXIS" (after the 0d STILL LIVE section,
end of file). Cross-references P4 without duplicating it, incl. the P4(iv)/bar-B interaction.
All five questions answered; five founder sentences + a definition of done at the end.
Two memory files written (blind-axis-splits-the-accuracy-bar, capture-framing-is-a-scope-lever)
and indexed in MEMORY.md. NOTHING written outside my allowlist — no SPEC edit, no STATE row,
no code. Remaining: report Q1 + Q3 to the lead.

## LOG — newest first

- **MY THREE PIECES OF ARITHMETIC** (label them PM-ARITHMETIC, not measurement; all
  re-derivable in 3 lines; if wrong the conclusions go with them):
  (1) OBLIQUITY LEAK. Camera on centreline 6 m behind near baseline. Far doubles corner =
  lateral 5.485 m, 29.77 m down-ray -> ray sits 10.44 deg off the court long axis ->
  sin = 0.181 of the BLIND (radial) error lands ACROSS the sideline -> 0.181 x 1.28 m =
  ~23 cm median at the far corner, vs the pooled court-frame lateral median of 10.1 cm.
  => the sideline is NOT uniformly safe; it is worst exactly at the far corner where the
  contested calls are. => the right BAR frame is PER-LINE PERPENDICULAR, not researcher's
  radial/tangential (that is the right MECHANISM frame; they differ by this obliquity term
  and coincide only on the centreline).
  (2) TELEPHOTO / FAR-HALF FRAMING — the only capture variant with a feasible band.
  Framing only the far baseline width (10.97 m at 29.77 m) allows hfov <= 20.9 deg =>
  f <= 5209 px at 1920 wide. Need f.h >= 8862 (1 px) => f >= 2954 at h=3 m. BAND EXISTS
  (hfov 21-36 deg). At bar A's 2 px the requirement doubles to 17,724 => f >= 5908 > the
  5209 cap at h=3 => needs h >= 3.4 m. So MARGINAL, not impossible — unlike the wide
  full-court config which has NO solution at any setback. Costs the near half of the
  court and most of the arc (fewer observations = worse conditioning: must be measured).
  DEVICE CONSEQUENCE: SE 2nd/3rd gen have NO tele lens -> optical version narrows the A13
  device floor. The 4K-digital-crop alternative works on any device but re-raises R7's
  undecidable detector-noise question.
  (3) SIDE MOUNT is not a rescue. Camera 6 m outside the sideline level with the net ->
  worst point (opposite far corner) 20.7 m not 29.8 m, BUT framing 23.77 m of length from
  6 m setback needs hfov ~126 deg => f ~489 px => f.h = 1467 at 3 m => 29 cm/px vs the
  end-mount's 36 cm. ~20% better and it merely SWAPS which lines are blind.
- **THE CAVEAT, carried the cleanest way:** the ANISOTROPY is geometric and survives real
  correlated/heavy-tailed noise. The RATES (49.9% / 83.9% / 6.1%) are properties of the
  i.i.d. noise model and the uniform flight population and WILL move. => rule on the
  SHAPE now, on the NUMBERS after P5. That is the whole argument.
- (start 2026-09-15) P1+R1 absorbed. Load-bearing: tangential 5.4 cm vs radial 1.28 m
  (23.5x); lateral-only 10 cm RATE 49.9% vs 90% bar, p90 0.611 m; lateral PERFECT pixels
  still 83.9%; f.h >= 8862 px.m vs f <= 175.S framing cap => no 1080p/3m solution at any
  setback; 6 m mount needs 12.6 m setback; 4K needs ~5.5 m. Tangential error moves only
  36% across an 8x height change.

- (start 2026-09-15) P1+R1 absorbed. The load-bearing numbers I will build on:
  lateral median 5.4 cm tangential / 1.28 m radial (23.5x); lateral-only 10 cm RATE 49.9%
  vs 90% bar, p90 0.611 m; lateral PERFECT pixels still only 83.9%; f·h >= 8862 px·m needed
  vs f <= 175·S framing cap => no 1080p/3m solution at any setback; 6 m mount needs 12.6 m
  setback; 4K needs ~5.5 m. Tangential error moves only 36% across an 8x height change.

### Carried forward from prior runs (still binding on my recommendations)
- Manual 4-tap calibration IS v1's setup story; court auto-detect is NO for v1 and v1.x.
- Human asks are scarce — batch into ONE update, ranked by leverage.
- Project owns NO confirmed metric footage; all four named mounts 1.36-1.74 m.
