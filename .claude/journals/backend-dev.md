# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (2026-09-09, SECOND task of the day) CNN-GLOBAL -> CLASSICAL-LOCAL

Founder brief supersedes the earlier proposal-recall task in this journal; that one
is now owned by qa (docs/evidence/candidate-proposal-recall.md - DO NOT TOUCH).
COURT ONLY. Build, behind a FLAG, a court path that runs CourtNet for GLOBAL
localisation, then the EXISTING classical machinery for LOCAL refinement, then the
EXISTING 6-DOF gate and consensus vote UNCHANGED. One variable: the proposal source.
DELIVERABLE: docs/evidence/cnn-global-classical-local.md (A/B vs shipped ordering,
per clip, split by surface and mount height) + tests + flag.
NOT-THIS-RUN: ball/speed/score/mobile; retraining CourtNet; data/*_pts*.json edits;
changing the shipped default; docs/STATE.md; git commit.
STOP-WHEN: A/B run and written up, or ~45 tool calls.

## BLOCKER RECORDED: SendMessage is DISABLED

The brief says teams mode is on and SendMessage works. It does NOT:
`Error: No such tool available: SendMessage. SendMessage is disabled for this
session, in subagents as well as here.` So I could not ask qa for the proposal-recall
number that would have killed or confirmed the premise. I build the flag-gated path
(cheap, reversible, useful either way) and report the premise as UNRESOLVED-BY-QA.

## PRE-REGISTERED BAR (written BEFORE running either arm)

ARMS. A = shipped ordering (classical global `autodetect` -> snap -> lock).
B = flipped (CourtNet global proposal -> the SAME snap -> the SAME lock).
Everything downstream identical: `snap_to_lines(min_coverage=0.0, max_move_px=60)`,
`lock_quad`, `consensus`, ACCEPT_VOTES=6, K=8 frames, same frame indices, same clips.
Deterministic apart from cv2.findHomography RANSAC inside detect_court_learned
(unseeded upstream code - noted, not changed).
WEIGHTS for arm B: `backend/weights/court_detector.pt`, the UPSTREAM released
checkpoint. Chosen because it is leak-free by construction (never saw our gold);
`courtnet_ft.pt` is our fine-tune and 17 of 20 gold clips were in that training pool,
so using it would be self-grading. Recorded in the artifact's provenance stamp.

SHIPPED GATE (unchanged, from the founder): >=12 of 20 gold clips ACCEPTED
AND ZERO accepted court beyond 20 px@640 of the human clicks.

VERDICTS, fixed before looking:
- FLIP WINS if B_accepted > A_accepted AND B has zero accepted court >20 px@640.
- FLIP LOSES if B_accepted < A_accepted, OR B accepts any court >20 px@640 (a wrong
  court accepted is worse than a refusal - it is the failure mode the vote exists
  to stop).
- NO DIFFERENCE if B_accepted == A_accepted and the accepted SET is the same.
- The ORDERING/GLOBAL-SEARCH HYPOTHESIS is SUPPORTED only if B accepts >=3 clips
  that A refuses AND at least half of those gains are indoor-shell clips. Fewer
  than that and any win is clip-specific, not the mechanism the document claims.
- Split bars: n>=4 per arm or I report the split UNDERPOWERED and draw no mechanism
  conclusion (same rule I pre-registered this morning).

BARRED CLAIMS (stated before running, because conflating them was made here this
week): I may NOT claim the flip beats the ~6.4 px line-detector precision floor or
the ~5.8 px human-click noise. Median err on clips BOTH arms accept is an
OBSERVATION only. And no ordering can fix the net-tape/far-baseline overlap below
~2.0-2.2 m mount - information absent from the image.

## STATE - 2026-09-09 - DONE. Flag built (default unchanged), 9 tests pass, both A/Bs run, docs/evidence/cnn-global-classical-local.md written, DECISIONS_PENDING appended. Nothing left except the return.

## RESULT - THE FLIP FAILED ITS PRE-REGISTERED BAR
GOLD (the founder's named gate, >=12/20 + zero >20 px): A classical 12/20 median
8.1 px 0 wrong; B courtnet 2/20 median 4.1 px 0 wrong. B fails by 10 clips.
REFERENCES (20 human _exact clips at native res): A 2/20 accepted, 89/160 frames
locked; B 0/20, 3/160. Shell (10 clips, all 3840x2160): A 0/10 + 20/80 frames;
B 0/10 + 0/80. Zero wrong-accepted courts in either arm.
MECHANISM (the real finding): the CNN REFUSES BEFORE our gate ever runs. On 4 of 6
probed gold clips detect_court_learned returned None on all 8 frames; the keypoint
probe shows only 2-3 of 14 heatmap peaks clear 0.40, and 4 are needed for ANY
homography. The upstream broadcast checkpoint does not see amateur courts.
The LOCAL half DID reproduce where observable: am_usta40 proposal 7.2 px -> 5.9 px
through our snap+lock (same direction as upstream's 2.83 -> 2.23). n=1 clip.
qa (relayed by the coordinator, SendMessage still absent): proposal recall 8/20=40%
-> THE SEARCH BINDS; shell worst; mount-height mechanism NOT established (16.7 pp vs
a 40 pp bar, confounded by surface) -> I split by SURFACE and withdrew my own
mount-height split bar rather than report it.

## WHAT IS BUILT
- backend/swingvision/courtfit.py: `auto_fit_frame(..., proposer=None|"classical"|
  "courtnet", weights=None)`, `fit_video_frames(..., proposer=)`, plus
  `resolved_proposer()` / `resolved_courtnet_weights()` (RESOLVED, not requested).
  Stage one only is switched; snap_to_lines + lock_quad + consensus are shared.
  SHIPPED DEFAULT UNCHANGED (env COURT_PROPOSER exists for the eval).
- backend/tests/test_court_proposer.py - 7 tests, incl. default==explicit classical
  (the refactor-changed-nothing proof) and a stub-detector test that the courtnet
  proposal really goes THROUGH the shipped snap+lock. 9 pass with the old test.
- eval/proposer_ab.py - both arms on the SAME decoded frames, run_refs metric.
- eval/proposer_rejects.py - per-frame stage-of-death for the courtnet arm.

## FIRST RESULT (smoke, am_hard_utr, Hardcourt, mount 1.74 m)
A classical: locked 8/8, votes 7, ACCEPTED, err@640 13.23.
B courtnet: locked 0/8, votes 0, NOT accepted (its err 25.84 came from the shared
stacked_clay_fit rescue, not from CourtNet). `locked=0` is the thing to diagnose:
proposal never made, or made and refused by lock_quad.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- ARCHITECTURE READ: auto_fit_frame = autodetect (classical GLOBAL) -> snap_to_lines
  (classical LOCAL) -> lock_quad (6-DOF gate). So the flip only replaces step 1.
- detect_court_learned ALREADY does CNN-global + per-keypoint classical local refine
  (`_refine_keypoint`, a 40 px crop Hough intersection) + RANSAC homography. The
  document's "local refinement" stage therefore already exists on the CNN path; what
  does NOT exist is CourtNet feeding OUR snap+lock+vote.
- detect_court_learned's `weights=` default is a RELATIVE path ("weights/...") so it
  only resolves with cwd=backend. Pass an absolute path from eval (eval_court.py
  already does exactly this via its _WEIGHTS constant).
- detect_court_learned has its own internal accept gates: reproj > 0.015*max(w,h)
  -> None, and verify_court(). I pass verify=False for the PROPOSAL, because the
  brief says the SHIPPED gate decides; leaving it on would add a second accept test
  the classical arm does not have (two variables).
