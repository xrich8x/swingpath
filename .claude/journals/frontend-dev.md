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

## TASK 4 (current) — coordinator follow-up: verify mobile/models/tracknet_ball.int8.onnx
(listed as unverified in task 3's evidence file). Two parts: (1) is it reachable at
all, (2) if so, run the same real-frame parity probe through it. Python fp32 stays
the reference. Pre-register a QUANTISATION-aware tolerance before measuring (not
the 0.00px/5px bars from task 3 — those were for algorithm-parity between two
implementations of the SAME fp32 numbers; here the two SIDES are numerically
different by design). Watch for outliers specifically, not just pass-rate (coordinator's
explicit warning — task 3's aggregate bars both passed while hiding a real bug).

### STATE (task 4)

- REACHABILITY — read-only, no code exists to inspect beyond mobile/ + docs (no
  app shell in this repo yet). ball_detector.js does NOT hardcode a model path —
  the caller passes an already-created `session` into `new BallDetector(session)`,
  and the path choice happens wherever `InferenceSession.create(modelPath)` is
  called (outside this file). BUT: ball_detector.js's own file-header comment
  (line 3) says "Wraps the mobile TrackNet ONNX (tracknet_ball.int8.onnx)" --
  names int8 explicitly, not fp32. MOBILE.md's file listing calls fp32 "(reference)"
  and int8 "BUNDLE THIS" (line 31), and its integration instructions say
  "bundle mobile/models/tracknet_ball.int8.onnx as an app asset" (line 79).
  So: int8 is not just reachable, it is THE documented/intended shipped model;
  fp32 is the desktop verification reference. grep across the repo for
  "tracknet_ball"/"onnxruntime-react-native" outside mobile/ + docs found
  nothing else that could override this (no app code exists to check). VERDICT
  on part 1: reachable, and in fact the default/intended path per this repo's
  own docs -- not dead weight.
- PRE-REGISTERED BAR (writing before measuring int8 vs fp32):
  Reference point already in the repo: export_tracknet.py's own historical
  check reported int8 within 0.32px mean of fp32 (12 frames, using Python's
  correct _postprocess on BOTH sides, one clip only -- weak population, but
  the only existing number for this exact quantisation).
  Reasoning for MY bar: task 3 already proved the fp32 leg (JS build -> real
  ONNX fp32 -> JS decode) is IDENTICAL (0.00px, 61/61) to Python's PyTorch
  reference. So for this task, comparing "JS decode of the int8 heatmap" vs
  "JS decode of the fp32 heatmap" isolates PURELY the quantisation effect --
  both sides now run the SAME (already-fixed, already-correct) decode
  algorithm, no algorithm confound. A ball's own footprint in this heatmap
  space is small -- observed connected-component areas around 9-15px
  (~3.4-4.4px diameter) for a real ball in task 3's own inspected frames, and
  the repo elsewhere cites "far ball ~3.9px in a 720p frame". So:
    1. Null/non-null agreement >=90% -- same severe-failure bar as task 3;
       quantisation causing the model to lose the ball entirely (or gain a
       phantom one) changes the IN/OUT call outright, worse than a wobble.
    2. Central tendency: MEDIAN position disagreement (both fire) <= 2px --
       ~6x the historical 0.32px baseline, giving real-clip-diversity margin
       while staying inside "quantisation noise", not "different object".
    3. OUTLIER bar, checked per-frame not aggregated (this is the one task 3's
       own pattern says to not skip): NO individual frame may disagree by
       more than 10px (~2-3x a real ball's own footprint) -- beyond that the
       two graphs are not agreeing on sub-pixel placement of the same blob,
       they are picking different features, and get inspected individually
       (not averaged away) exactly as task 3's 4 outliers were.
  A failed bar (especially #3, even a single frame) stays failed -- reported
  as a genuine finding, not smoothed by the aggregate passing.
- Extended backend/ball_detector_parity_probe.py: added ONNX_INT8 const,
  onnx_run_int8() (int8 sibling of onnx_run, same Python-onnxruntime
  substitution, named explicitly in its own docstring), compare_int8()
  (reports null-agreement, median/mean/max, prints WORST 5 individual
  disagreements explicitly not just pass/fail, writes
  data/output/ball_detector_int8_parity_summary.json). Extended
  mobile/verify_ball_detector.js with decodeInt8Phase() (mode "decode-int8"),
  same real _decode(), only the heatmap source graph differs.
  int8 model confirmed on disk: mobile/models/tracknet_ball.int8.onnx =
  10.9MB vs fp32 43.0MB, matches MOBILE.md's stated 43->11MB claim.
- MISTAKE, corrected: backgrounded onnx-run-int8 and ended the turn twice
  expecting a wake-up notification — nothing wakes this agent, only the
  coordinator gets notified and has to manually restart it. Cost real
  restart overhead. Wrote [[background-wait-does-not-survive-ending-turn]]
  memory so this doesn't repeat. Fix applied: polled the scratch dir's
  int8_heat_*.bin file count in a FOREGROUND bounded loop instead, and once
  it was clear full-178 completion would take ~25+ more minutes (int8 rate
  ~11.7s/frame vs fp32's ~0.8s/frame — matches MOBILE.md's known x86
  int8-kernel pathology, not a bug), STOPPED at 51/178 frames (clip-start
  only) and used that as an explicitly-labelled PARTIAL result per the
  coordinator's own framing ("partial labelled honestly beats complete after
  another restart").
- TASK 4 DONE on partial data. Int8 reachability: YES, and it's the
  documented/intended shipped model (ball_detector.js's own header names
  int8, not fp32; MOBILE.md says "BUNDLE THIS" for int8, fp32 is "(reference)").
  Pre-registered bar: null-agreement >=90%, median (both-fire) <=2px, no
  single frame >10px — justified against a real ball's own ~3.4-4.4px
  footprint in this heatmap space, not a round number. Measured on 51/178
  real frames (tags 0002-0052): null-agreement 48/50 (96%), median 0.192px
  max 1.202px on 10 both-fire frames, zero frames >10px — ALL THREE BARS
  PASS. Named explicitly (not hidden in the aggregate): 2/50 frames (4%) are
  real coverage loss (fp32 fired, int8 returned null) — a genuine but
  non-bar-breaking cost. Verdict: safe to ship on the position-accuracy axis
  measured so far; NOT a fully powered verdict (small n=10 for position,
  partial/non-representative span) — full 178-frame re-run flagged as the
  natural next step if this becomes higher priority, harness already
  supports it (onnx-run-int8/decode-int8/compare-int8 in
  backend/ball_detector_parity_probe.py + mobile/verify_ball_detector.js).
  Full writeup appended to docs/evidence/ball-detector-parity-tracknet.md
  ("The int8 graph" section). docs/STATE.md new row. Committing next:
  backend/ball_detector_parity_probe.py, mobile/verify_ball_detector.js,
  docs/STATE.md, docs/evidence/ball-detector-parity-tracknet.md,
  data/output/ball_detector_int8_parity_summary.json,
  .claude/agent-memory/frontend-dev/{MEMORY.md,background_wait_does_not_survive_ending_turn.md}.
  No push. Leaving .claude/ hooks/doorman/session_watchdog/slots/.gitignore
  and other agents' journals/memory alone (concurrent session).

## Nothing else in flight. Tasks 1-3 all DONE and committed; no push (repo convention).

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
