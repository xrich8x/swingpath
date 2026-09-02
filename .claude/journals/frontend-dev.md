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

## Nothing in flight. Last three tasks all DONE and committed; no push (repo convention).

## TASK 3 — DONE. `mobile/ball_detector.js` (ONNX TrackNet port) vs
`backend/swingvision/ball.py` `BallDetector`. Full writeup:
`docs/evidence/ball-detector-parity-tracknet.md`.

Input tensor (`_buildInput`) was already bit-exact. Decode (`_decode`) was NOT
a real mirror of `ball.py`'s `_postprocess` despite the docstring claiming it
was — Python does full-image connected-component + area*peak scoring, old JS
did global-argmax + fixed 7x7 window. Measured on 178 real frames
(`data/incoming/Hardcourt/am_hard_utr.mp4`, 61 real TrackNet detections),
decode-only isolation AND the real bundled fp32 ONNX graph: passed the
pre-registered loose bar (100% null-agree, 93.4% pos-agree <=5px) but had
4/61 gross mismatches up to 238px, all on two-blob heatmaps — JS locked the
wrong blob, a confident wrong answer with no refusal signal. Ported Python's
exact connected-component algorithm into JS (plain BFS flood-fill, no new
dep). Re-verified 61/61 exact 0.00px, same real frames/graph. Confirmed
non-vacuous via `git stash` (reverting reproduces the exact same 4
mismatches). Separately confirmed via pm's memory
(`founder-rulings-2026-08-29.md`) that "v1 ships TrackNet" is a real, dated
ruling — closed the 2026-08-27 "mobile bundles wrong detector" defect note in
`docs/STATE.md` as stale (BallNet v21 stays the DESKTOP default, a different
product; mobile correctly bundles what v1 ships).

Committed: `backend/ball_detector_parity_probe.py`, `mobile/verify_ball_detector.js`,
`mobile/ball_detector.js` (the fix), `mobile/MOBILE.md`, `docs/STATE.md` (two
rows), `docs/evidence/ball-detector-parity-tracknet.md`,
`data/output/ball_detector_parity_summary.json`. Left ALL concurrent-session
files alone (`.claude/hooks/agent_cap.py`, `doorman_server.py`,
`session_watchdog.py`, `slots.py`, `.gitignore`, qa's journal/memory) — staged
only my own files explicitly, never `git add -A`.

## TASK 2 — DONE. `live_calls.js` doubles-alley bug: `_detectBounce` called
`isInSingles` unconditionally regardless of `this.singles`. Fixed (added
`isInDoubles`, branched like Python), verified non-vacuous via 21 synthetic
boundary cases in both modes (42/42), git-stash regression check confirmed
the new test actually catches it. Full writeup:
`docs/evidence/doubles-alley-live-call-bug-fixed-and-exercised.md`. Memory:
[[doubles-alley-bug-fixed]].

## TASK 1 — DONE. Video-free parity check for `live_calls.js` vs `live.py`
(`push_position` is pure, no video needed — cross-checked frame count against
`real_match.json` instead of assuming it). Found the harness was pointed at a
DEGENERATE calibration (`court_pts.json`, stamped by the project's own audit
tool) instead of the correct `court_pts_refined.json` — not a code bug, a
harness bug. Fixed, 7/7 calls exact to 0.000 (well inside the 0.001m bar).
Full writeup: `docs/evidence/live-call-parity-verified-without-video.md`.
Memory: [[video-free-parity-checks]], [[committed-calibration-files-can-be-degenerate]].

## LOG — newest first

- Task 3 committed and journal compacted (tasks 1-2 detail moved to their
  evidence files + agent-memory; this journal keeps only pointers now).
- Task 3: fix verified non-vacuous via git stash (before-fix reproduces the
  exact 4/61 mismatches; after-fix restores 61/61 exact).
- Task 3: root-caused the 4 real-frame mismatches to two-blob heatmaps —
  Python's area*peak picks the larger/coherent blob, old JS argmax+window
  locked the wrong one. Fixed by porting the connected-component algorithm.
- Task 3: measured before-fix — input tensor bit-exact, decode 100%
  null-agree / 93.4% pos-agree (passes pre-registered bar but real gross
  divergence in 4/61 frames).
- Task 3: built the harness (backend/ball_detector_parity_probe.py +
  mobile/verify_ball_detector.js), no onnxruntime-react-native available
  offline so ran _buildInput/_decode directly (no runtime dep) + the real
  bundled ONNX graph via Python onnxruntime standing in for the RN binding
  (named as the one unverified link).
