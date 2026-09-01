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

## STATE — DONE. Parity established, verified, committed.

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
