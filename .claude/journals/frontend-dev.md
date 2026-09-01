# frontend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/frontend-dev/`, and
findings go in `docs/STATE.md` + `docs/evidence/`. Do not duplicate those here.

---

## TASK — what I was asked to do

Establish a video-free parity check between mobile/live_calls.js (JS port) and
backend/swingvision/live.py (Python reference) for the on-device live line-call
logic. Lead's brief: verify_live.js is unverifiable today (needs missing
data/tennis_sample.mp4). Find whether LiveAnalyzer's calling logic is separable
from the frame loop/renderer in live.py; if so drive both sides on the SAME
cached ball_px track + calibration and diff call-for-call. Do NOT edit the JS
port to match an unverified number. Python is the reference by decision.
Pre-register parity bar BEFORE running. Commit increments, no push. Update
docs/STATE.md in the same commit as any backend/tools/mobile code change.

## STATE — investigating; separability confirmed, building the no-video harness

- Read live.py: `LiveAnalyzer.push_position(ball_px, t_s)` is PURE — no frame,
  no cv2, no renderer. `push_frame` just wraps it with a detector call.
  `stream()` (the only thing coupled to cv2.VideoCapture) exists ONLY to (a)
  get frame index i / fps for t_s, (b) call push_position, (c) render overlay
  frames to an mp4 — (c) is irrelevant to a numeric parity check, and (a)/(b)
  don't need the video AT ALL if we already know len(ball_px) and fps from
  elsewhere. CONCLUSION: separable. Video-free parity IS possible by calling
  push_position directly. Not proposing any refactor to live.py.
- Confirmed real_match.perception.json (ball_px, 123 entries, frame_step=1) IS
  the tennis_sample.mp4 cache: data/output/real_match.json video block =
  {filename: tennis_sample.mp4, fps: 30.0, width:1920, height:1080,
  duration_s:4.1} and 4.1*30=123.0 == len(ball_px) exactly. So iterating
  i in range(123) with t=i/30 reproduces stream()'s loop exactly (no video
  decode needed since frame count is already pinned by this cross-check).
- CALIBRATION AMBIGUITY RESOLVED, no video needed: git log -p on
  data/court_pts.json (commit 20a672e, "Make a degenerate calibration
  announce itself...") states explicitly: "live_demo.py's docstring pointed
  at court_pts.json; now court_pts_refined.json, the good version of the SAME
  CLIP." court_pts.json is stamped `_audit.verdict: DEGENERATE` (38.1px
  residual — validate_new_clip.py's own gate says this corner set is not a
  physical camera view). court_pts_refined.json is stamped PASS (2.3px
  residual). Both are for tennis_sample.mp4. So the 6in/1out number (JS
  pointed at court_pts.json) was built on a calibration the project's own
  audit tool already rejected — not a live ambiguity, a harness bug reading
  the wrong file. court_pts_refined.json is unambiguously correct, matching
  what live_demo.py's docstring names.
- PRE-REGISTERED PARITY BAR (before running the Python side):
  exact match required on: number of calls, in/out per call (order-matched),
  t_s per call (exact, both round to 2dp the same way). Tolerance: margin_m
  within 0.001 m (both round to 3dp; only allowing for float order-of-ops
  drift between numpy H^-1 (Python) vs a hand-rolled Gaussian-elim inverse
  (JS) — homography itself is solved by DIFFERENT algorithms (numpy SVD+
  Hartley-normalized DLT vs plain 4-point Gaussian elim in JS), so bit-
  identical is not the bar; sub-mm agreement is. A failed bar stays failed —
  will not loosen it post-hoc.
- NEXT: write a no-video Python driver (mirrors live_demo.py's replay lambda
  + stream()'s loop body, skipping cv2 entirely) using court_pts_refined.json,
  run it, run JS pointed at the same file, diff.

## TASK 2 — fix the doubles-branch bug at live_calls.js:145, exercise it for real

Coordinator follow-up 2026-09-02: fix `isInSingles` being called unconditionally in
`_detectBounce` (ignores `this.singles`). MUST extend verification to actually run the
doubles branch — the singles-only cached track from task 1 cannot see this bug (0 OUT
calls, singles-only). Cannot invent a doubles ball track with fake "ground truth".
Legitimate construction: synthetic COURT POSITIONS (not a real trajectory) straddling
every X/Y boundary in both singles and doubles, run through BOTH analyzers, asserted
call-for-call. Must label as a PARITY test, not accuracy. Python is reference; if
Python itself mishandles doubles, report as a finding, do not silently reconcile.

### Root-cause read (both languages)

Python `live.py` `_detect_bounce` (correct):
  in_bounds = court.is_in_singles(x,y,margin) if self.singles else court.is_in_doubles(x,y,margin)
  _distance_inside also branches correctly on self.singles (xl/xr chosen per mode).
JS `live_calls.js` `_detectBounce` (BUGGY, line 145):
  const inBounds = isInSingles(x, y, this.lineMargin);   // <- no branch on this.singles at all
  `_distanceInside` (2 lines below) DOES branch correctly on this.singles.
So in doubles mode: the IN/OUT verdict is always tested against the NARROWER singles
box, while the reported margin_m is computed against the WIDER doubles box. Net effect
in call terms: a ball that lands in the doubles alley (inside doubles, outside singles)
is called OUT on screen while the displayed margin reads POSITIVE (inside) — a visibly
self-contradictory call, and worse, the wrong call in doubles scoring (alley is IN for
doubles). Only fires when `singles:false`; today's shipped default and everything
task-1 tested is `singles:true`, so it has never been exercised.
`isInDoubles` does not exist in live_calls.js yet (only `isInSingles` is exported) —
need to add it, mirroring `court.is_in_doubles`.

### Pre-registered test design (BEFORE writing the fix)

Cannot unit-test `isInSingles`/`isInDoubles` alone — they're each individually correct;
the bug is in the WIRING inside `_detectBounce`. Must drive the full push()/bounce-
detection state machine so the actual buggy code path runs. Plan:
- Identity homography (3x3 identity, both langs) so pushed "pixel" coords equal court
  METRES directly — a pure geometry probe, explicitly not tied to any real camera/
  calibration, labelled as such.
- Per test case (x0,y0): 4-point synthetic trajectory p0..p3 with p2=(x0,y0), speeds
  [9,1,9] (dt=1 each) so the middle segment is a clean local-min dip (passes both
  is_min and is_dip at default min_speed_drop=0.6) and the bounce is reported at
  exactly (x0,y0). Fresh LiveAnalyzer per case per mode (singles/doubles) avoids
  min_call_gap_s and ordering entirely.
- ~21 cases in a SHARED JSON (one source of truth, no duplicate hand-transcription
  into two languages): court centre; both alleys (the key IN-doubles/OUT-singles
  asymmetric case) at exact line, ~3mm inside margin, ~3mm outside margin, on both
  left/right sidelines; fully outside doubles both sides; near/far baseline ~3mm
  inside/outside (Y bound is SHARED by singles/doubles — not alley-asymmetric, still
  worth covering for margin precision). Expected in/out per case HAND-COMPUTED from
  the raw constants (X_LEFT_SINGLES=1.37, X_RIGHT_SINGLES=9.60, X_LEFT_DOUBLES=0,
  X_RIGHT_DOUBLES=10.97, Y 0..23.77, margin=0.05m pinned explicitly in the cases file
  rather than relying on each side's own default) — NOT deferred to either
  implementation, so this is an independent check, not two implementations grading
  each other.
- Three-way assertion per case per mode: Python actual == hand-computed expected
  (Python correctness, reported as a finding if it ever fails — not fixed quietly);
  JS actual == Python actual (the parity bar, call + sub-mm margin tolerance 0.001m,
  matching task-1's bar); JS actual == hand-computed expected (should follow from the
  above, checked directly anyway).

### STATE (task 2) — DONE. Fixed, exercised, verified non-vacuous, committed.

- Added `isInDoubles` to live_calls.js (mirror of court.is_in_doubles — did not
  exist before). Fixed `_detectBounce`'s `inBounds` to branch on `this.singles`,
  mirroring live.py's ternary exactly.
- Built mobile/doubles_alley_parity_cases.json (21 cases, hand-computed expected,
  margin pinned 0.05), backend/live_doubles_alley_probe.py (Python driver, full
  bounce state machine via identity homography + [9,1,9]-speed synthetic
  trajectory per case), mobile/verify_live_doubles.js (JS driver + 3-way compare:
  vs hand-computed expected, vs Python actual, both within 0.001m).
- Ran Python probe FIRST, standalone: 42/42 match hand-computed expected, ZERO
  findings against live.py itself (it was already correct — only the port had
  drifted). This is the "check Python independently" step, not skipped.
- Ran JS: 42/42 match both hand-computed expected AND Python. PASS.
- SANITY-CHECKED THE TEST ISN'T VACUOUS: `git stash push -- mobile/live_calls.js`
  to temporarily restore the buggy version, re-ran verify_live_doubles.js ->
  correctly FAILED 7/42, every failure a doubles-mode alley case (left_alley,
  right_alley, on_doubles_sideline_exact, both margin-left/right 3mm-inside
  alley variants), every one flagged DIVERGES FROM PYTHON. `git stash pop` to
  restore the fix, re-ran -> 42/42 PASS again. Confirms the new test actually
  exercises the fixed line.
- Re-ran task-1's verify_live.js too (singles-only real track) — still 7/7in/0out
  PASS, confirming the fix + new isInDoubles addition didn't disturb it.
- Updated MOBILE.md (file listing + accurate "verified against Python" framing,
  dropped the old bare "bit-identical" claim), docs/STATE.md (new row, FIXED +
  linked evidence, placed in the Open section following the row-235 convention
  of keeping resolved items in place with strikethrough rather than moving
  tables), docs/evidence/doubles-alley-live-call-bug-fixed-and-exercised.md
  (full writeup incl. the "is Python itself correct" check and the non-vacuous
  regression proof).
- Committing next: mobile/live_calls.js, mobile/doubles_alley_parity_cases.json,
  mobile/verify_live_doubles.js, backend/live_doubles_alley_probe.py,
  data/output/live_doubles_alley_python.json, mobile/MOBILE.md, docs/STATE.md,
  docs/evidence/doubles-alley-live-call-bug-fixed-and-exercised.md. No push.

## STATE (task 1) — DONE. Parity established, verified, committed.

- Built `backend/live_replay_novideo.py`: drives `LiveAnalyzer.push_position`
  directly over cached `ball_px`, cross-checks frame-count assumption against
  `real_match.json` (refuses to run if it doesn't hold). Ran it against
  `court_pts_refined.json` (the correct calibration, see above) -> 7 calls,
  7 in / 0 out.
- Ran the JS port the same way (ad-hoc copy of verify_live.js pointed at
  court_pts_refined.json, deleted after) -> IDENTICAL 7 calls, 7 in / 0 out,
  every t_s/xy/margin_m equal to 0.000 diff (well inside pre-registered
  0.001 m bar). Wrote both raw outputs to data/output/live_calls_python_
  reference.json and live_calls_js_port.json, diffed programmatically —
  zero divergence on any field.
- Fixed verify_live.js for real: points at court_pts_refined.json (not the
  DEGENERATE court_pts.json), documents the verified 7/7in/0out result and
  how to reproduce it, and now EXITS NON-ZERO on drift (was print-only
  before — a real regression gate now, not just an eyeball check).
- Wrote docs/evidence/live-call-parity-verified-without-video.md (full
  derivation) and updated docs/STATE.md row (the existing "stamped
  calibration" row, in place, since it's the same item — now marked fixed +
  linked to the new evidence file).
- NOT verified (documented as such in the evidence file): the doubles branch
  (known bug, live_calls.js:145, not exercised — this track is singles-only
  and all-IN), any OUT call (none in this track), the video decode/capture
  path itself, and whether tennis_sample.mp4 really is 123 frames @30fps
  (taken from real_match.json's recorded metadata, not re-measured against
  the absent video file — the one unverified premise underneath everything).
- Did NOT touch live.py or live_calls.js's calling logic — no divergence was
  found once given correct input, so nothing needed moving.
- Noticed but did NOT touch: .claude/hooks/agent_cap.py, .gitignore, and
  .claude/slots.py show as modified/untracked in git status — pre-existing,
  not mine, left alone.

## LOG — newest first

- Committed backend/live_replay_novideo.py, mobile/verify_live.js,
  docs/STATE.md, docs/evidence/live-call-parity-verified-without-video.md,
  data/output/live_calls_{python_reference,js_port}.json. No push (bar in
  force).
- Full derivation done: separability confirmed -> frame-count cross-check
  confirmed (123 == 4.1*30) -> calibration ambiguity resolved via git log
  on court_pts.json (commit 20a672e) -> ran both sides -> exact match.
