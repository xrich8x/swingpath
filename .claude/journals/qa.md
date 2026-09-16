# qa - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK - 2026-09-16: P8 STAGE C2 (court model vs human clicks on REAL footage)
Four human doubles-corner clicks per gold frame -> flat homography (primary) -> project
every OTHER labelled landmark -> px@640 distance to human click. BAR (lead.md, fixed):
PASS iff median <= 5.8 px@640. Secondary: per-landmark median/p90, near vs far.
Pool: data/gold/*.court.labels.json (20 files, uncompromised). NOT data/<clip>_pts.json.
8 mislabelled gold frames: report with/without, never edit. Side check: demo30 vs
yt_match40 camera_height_of under hfov assumptions (compromised pool - not scored).
C2 cannot overturn C1; it catches real-footage-worse-than-sim problems.
Deliverables: docs/evidence/court-map-gold.md, STATE row TEXT (qa may not edit STATE ->
hand to lead), commit no push. Script: tools/ not on allowlist -> scratchpad, inlined
in evidence file.

## STATE
- Starting. Previous task (P2 sheet) DONE and committed 2cd476f; awaiting founder CSV.

## LOG
- 2026-09-16: C2 task recorded.
- PRE-RUN FINDING (BLOCKER): gold keypoints are NOT human clicks. tools/gold_label_server.py
  cornersToLabel() solves H from the 4 clicked corners and WRITES the 10 other keypoints
  as applyH(H, KP) rounded to 0.1 px. Human clicks only 4 corners. So C2 as registered is
  self-grading (rule 1) -> expected median ~0.03 px = rounding. Signature seen in git:
  2e49f38 (2026-09-06, agent commit "composite calibration score") re-saved am_beginner +
  am_usta45final: frames with UNCHANGED corners had keypoints move +-0.1 px (re-rounding),
  and changed corners moved all keypoints. ALSO: that commit EDITED human gold (am_beginner
  f1021 near_bl moved 16 px, f3904 all 4 corners moved up to 27 px) and ADDED 15 frames to
  am_usta45final -> rule-10/provenance finding. 8 mislabelled = am_indoor_hard1 court:false
  frames -> contribute nothing to C2 (with/without identical by construction).
- CONFIRMED by invoking (scratchpad/c2_control.py, backend venv): 360 frames, 30 court:false
  (am_indoor_hard1 8, am_usta60 8, am_usta45 5, am_grass1 4, 5 others 1 each), 330 court
  frames x 10 landmarks = 3300 pairs, 20 clips. median 0.0477 px, p90 0.0899, max 0.589
  (am_ntrp45w near singles, off-frame -> rounding amplified). near med .050/p90 .104,
  far med .046/p90 .083. = 0.1-px ROUNDING. Tool code identical at 82fb523/537ed12/6843ee7.
  Registered "PASS" is a self-grading artefact -> report C2 NOT RUNNABLE on this pool.
- SIDE CHECK DONE (scratchpad/c2_side.py, c2_render.py): shipped camera_height_of reproduces
  stamps: demo30 1.376 @ fitted hfov 104.16; yt 1.641 @ 91.04. Common hfov does NOT close gap:
  @104.16 1.376 vs 1.581 (.205); @91.04 1.421 vs 1.642 (.221); @70 1.507/1.784 (.277);
  @60 .322; @40 .501. 5 deg moves height 1.6-2.3% (C1 agrees). 13 deg on one quad = .045-.061 m.
  The QUADS disagree: 217/145 px@640 at near doubles corners, 8/10 at far. Rendered both on
  yt f0/f3002 + demo30 f450 (same image): GREEN (yt current, 2026-09-05 re-click) sits on the
  painted near baseline (y~452) + service line (y~362); RED (demo30, 2026-08-03) puts near
  baseline ~60px below any paint. T23 is about the .bak (11.3 m, 20.7 deg) - NOT the current
  file. So the wrong one on this frame is demo30. Both residuals 0.5/0.0 px (T23 blindness).
  Also explains my 09-10 "yt_match40 resolves to a different court" defect: file replaced 09-05.
- 30 court:false frames all carry unusable:true. am_indoor_hard1's 8 = the named mislabels.
- DONE: docs/evidence/court-map-gold.md written, memory written. Committing [no-state]
  (qa may not edit STATE; row text handed to lead in report). NOT pushed.
- (old) NEXT: confirm empirically by invoking calibration.homography_from_landmarks on all 20
  files (the "control" number), check tool version at label dates (82fb523/537ed12/6843ee7),
  then side check, then write up as C2 NOT RUNNABLE on this pool.
