# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (2026-09-09, SIXTH task of the day) POOL 20 -> 16 (founder ruling)

Task 5 (three audit-tool defects) COMPLETE - see DONE-T5 below, do not redo.
`eval/reach_ab.py` untracked leftover from an even earlier task - ignore.

FOUNDER RULING: references pool drops A7vXlWIlyrI, HoHxFSX_gLk_s1, HoHxFSX_gLk_s2,
UHf0LeMU2pg. 20 -> 16. Reason: strict "one camera setup" - qa's clip-shot-map.md
ORB/RANSAC similarity edge only proves REGISTRABLE background, a pan-and-zoom passes.
Within-winning-group motion: A7vXlWIlyrI 188.3 px@640 w/ 40% zoom at 8/8;
HoHxFSX_gLk_s1 189.5; HoHxFSX_gLk_s3 138.5; HoHxFSX_gLk_s2 105.9. Strict rule adds
EXISTING WRONG_PX_640=20.0 (no new constant): pairwise-linked AND pairwise <=20 px.
uR5q2cSM6AY is a marginal 5th - RETAINED, flagged not dropped. Do NOT widen rule.

DELIVERABLES: (1) explicit+discoverable exclusion in eval/run_refs.py (NOT by moving
files - that is how bump_ntrp30 vanished; glob is non-recursive at data/*_pts*.json).
(2) test in backend/tests/: pool==16, four absent, uR5q2cSM6AY present.
(3) docs/evidence/pool-strict-16.md = invalidation list of every published /20 number.

NOT-THIS-RUN: re-measuring ANYTHING (numbers stay as published, marked stale),
docs/STATE.md, git commit, editing any *_pts.json, data/pre_reaudit_backup/.

## STATE - **TASK COMPLETE.** All three deliverables in; full suite **706 passed**
(693 before + 13 new). Outstanding for the LEAD only: docs/STATE.md + commit.
Deliverable 3 = docs/evidence/pool-strict-16.md (before/after lists, composition
table, invalidation list in 3 parts: 3a stale, 3b affected-going-forward, 3c
NOT-affected). Nothing re-measured; no eval run.
KEY FINDINGS in that doc worth not re-deriving:
- All 4 dropped clips are 1920 HARDCOURT -> pool loses 20% of clips but 40% of its
  NON-SHELL half (10->6); shell share 50% -> 62.5%. Surface splits move most.
- proposal recall 8/20: drop removes 1 REACHED (A7vXlWIlyrI 5.3px) + 3 never-reached
  -> moves UP, does NOT cross the 60% search-binds line. Verdict survives, figure not.
- cnn-global References 2/20: BOTH accepts (am_hard_utr, sAjkpeRq4P4) are RETAINED ->
  numerator unchanged, denominator only.
- "19 of 20 clears the accept gate, only UHf0LeMU2pg fails" -> the SOLE counterexample
  is dropped. Same for camera-motion's "1 of 16 crosses the line" = HoHxFSX_gLk_s2.
- HAZARD: after the drop the pool holds 0 confirmed-MISPLACED clips. It looks cleaner
  because the contested clips LEFT, not because anything was re-placed. T26 unresolved.
- THREE different 20s in the repo: gold data/gold/*.court.labels.json (am_*, 640w,
  the 12/20 gate - NOT affected), the references pool (moved), and ball gold
  gold_UHf0LeMU2pg/gold_uR5q2cSM6AY (NOT affected, shared basename trap).
- 28-calibration populations (net tape 13/15, post 3/11, setup 28) do NOT use
  references() -> unaffected; the ruling deletes no file.
DONE so far:
- eval/run_refs.py: WRONG_PX_640=20.0 (copied, not new), EXCLUDED_CLIPS dict with a
  per-clip reason quoting S20/px/zoom, FLAGGED_MARGINAL=("uR5q2cSM6AY",),
  exclusion_note() printed to stderr ahead of provenance_warning(), module docstring
  + references() docstring say 16 and cite pool-strict-16.md. Skip is `if stem in
  EXCLUDED_CLIPS: continue` inside the glob loop - files NOT moved.
- backend/tests/test_refs_pool_strict16.py: 13 tests, all pass. Includes a test that
  the four *_pts.json are STILL ON DISK and still _exact (guards the bump_ntrp30
  move-it-out-of-the-glob failure mode) and a 20-4=16 arithmetic test that
  reconstructs the pre-ruling pool.
- tools/render_ai_court_audit.py: default_clip_list() docstring + --clips help said
  "20-clip gold pool"; corrected (it calls references(), so its default silently
  shrank to 16). Dropped clips can still be named explicitly.
SIDE EFFECT FOUND: provenance_warning() denominators are computed at runtime, so
they moved 6/20 -> 3/16 (named commits) and 9/20 -> 5/16 (agent session). All four
dropped clips were in FLAGGED_SESSION. -> invalidation list item.

## LOG-CTX WRONG_PX_640=20.0 lives in 9 eval
scripts (agree_sweep, behind_camera, candidate_audit, evid_band_sweep, foot_gate_power,
proposer_ab, score_truth, tol_sweep, truth_neighbourhood) - each defines its own copy.
run_refs importers (grep eval/*.py): behind_camera, candidate_audit, crop_safety,
evid_band_sweep, movers, proposer_ab, proposer_rejects, reach_ab, score_truth,
tol_sweep, truth_neighbourhood = 11 files (brief said 8).

DELIVERABLE - three fixes + tests green + a note (appended to
docs/evidence/calibration-provenance.md) saying for each defect WHAT IT COULD HAVE
HIDDEN. The note matters more than the fixes: audit-instrument failure modes are
findings.

1. tools/render_corner_audit.py: `--tag` accepted and SILENTLY IGNORED on the corner
   path (main() passes it only to render_net_anchors). Lead rendered one clip at 5
   frame indices -> 1 file, 4 silently destroyed.
2. Same file: defaults to `--frame 0`, but eval/run_refs.frames_from samples k=8
   over 5%-95%. Sheet can show a frame the scoring never sees. Caption must state
   WHICH frame and HOW it was chosen. Do not paper over ONE-frame-vs-EIGHT.
3. eval/candidate_audit.py docstring still claims UNRUN. It ran 2026-08-24 (Session
   O, shell) and 2026-09-09 (full 20-clip pool). Trap T24. Correct from git log +
   importers, not from prose in the file.

## NOT-THIS-RUN
docs/STATE.md (lead owns). git commit (lead commits). Re-placing/editing ANY corner
value (rule 9). Changing which clips references() returns. Ball/speed/score/mobile.

## STATE - 2026-09-09 - **TASK COMPLETE.** All three fixes in, full suite 693
passed (605 before + 88 new), addendum section 8 written into
docs/evidence/calibration-provenance.md. Smoke-tested: default frame, --tag +
--frame, --eval-frames (8 sheets), --net-anchors, and the --post-height refusal.
Outstanding for the LEAD only: docs/STATE.md (NOT-THIS-RUN) + commit.

## DECISIONS (made, do not re-derive)
- D1: make `--tag` WORK on the corner path (not error) - the tool already has
  --video-tag to find the clip, so the override is meaningful there too. PLUS the
  corner output filename gets the frame index appended, so N frames -> N files with
  no flag needed. That is the actual fix for the silent destruction.
- D2: `--frame` default becomes None = "the eval's own sampling". Resolve via a NEW
  pure function `run_refs.frame_positions(total, k)` that `frames_from` now calls
  (refactor pinned by a test, repo rule 8), imported by the tool so parity is
  STRUCTURAL not asserted. Default renders the lower-middle eval sample; new
  `--eval-frames` renders all 8. Caption states index, sample n/k, and the rule.
- D3: candidate_audit run history: git log --follow on the file shows only 424ecdc
  (creation) + 733565a (archive move) - the file's own history proves nothing about
  RUNS. Runs are established from what CONSUMED it:
    * 2026-08-24 Session O, shell: docs/archive/sessions/SESSION_O_shell_courts.md
      :443 "10 references x 8 frames. Reproduces the shipped 2/10 accept rate";
      --movers primitives same day (TRAPS T24, far-player-motion-gate-result.md).
    * 2026-09-09 full 20-clip pool: docs/evidence/candidate-proposal-recall.md,
      commit 5e322e2 "proposal recall is 40%: the SEARCH binds, not the vote".
    * qa memory + STATE:198 warn `truth_would_pass = 9/20` from this tool is NOT
      quotable (scores the wrong subject). Put that in the docstring too.

## DONE (this task)
- tools/render_corner_audit.py: --tag honoured on corner path; output names carry
  the frame (`_corners_f<N>.png`, `_netanchor_f<N>.png`); --frame default None ->
  default_frame(); --eval-frames renders all 8; grab_frame(seek=) mirrors
  run_refs' CAP_PROP_POS_FRAMES; caption states index + "eval sample n/k" + the
  ONE-vs-EIGHT line; refuses --post-height w/o --net-anchors, --eval-frames with
  --frame, --tag with >1 --pts.
- eval/run_refs.py: frame_positions(total,k) extracted; frames_from calls it.
- backend/tests/test_eval_frame_positions.py: 88 cases; legacy expression copied
  verbatim from 5e322e2 and asserted equal; also pins tool<->eval agreement.
- eval/candidate_audit.py: docstring run history corrected (2026-08-26 424ecdc
  committed its OWN output candidate_audit.json; 2026-09-09 5e322e2) + the
  truth_would_pass 9/20 "do not quote" caveat + T26 standing warning.
- docs/evidence/calibration-provenance.md section 8 (addendum) = the deliverable
  note: per defect, WHAT IT COULD HAVE HIDDEN.
- KEY FINDING for the note: court_setup_server --video mode places against frame 0
  (line 121 cap.read()), but GALLERY mode images come from collect_frames.py which
  SEEKS arbitrary positions. So frame-0 sheets were rendered at a frame that is
  not the placement frame for every gallery-placed calibration -> a correct
  calibration on a moving-camera clip renders as WRONG. False accusation risk in
  the founder's 10-of-28.
- CAVEAT recorded: all published --net-anchors numbers were frame-0; re-running at
  the new default is not like-for-like. Use --frame 0 to reproduce.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.

## DONE-PREV (2026-09-09 task 4, complete)
tools/court_setup_server.py _provenance on both /api/save paths;
backend/tests/test_court_setup_save_provenance.py (12 tests, corner values proven
byte-identical); eval/run_refs.py docstring corrected + provenance_warning();
docs/evidence/calibration-provenance.md. references() before==after, 20 clips.
