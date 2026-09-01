# Mobile live-call parity: verified without the missing video (2026-09-02)

## The blocker

`mobile/verify_live.js` is the only verification the JS live-call port
(`mobile/live_calls.js`) has. Its header claimed "matches backend
`live_demo.py` replay: 7 calls, 5 in / 2 out" — a number that could not be
checked: `live_demo.py replay --video ../data/tennis_sample.mp4` needs a file
that is not in the repo. Worse, the harness itself was reading the wrong
calibration file (see below), so even a from-scratch run of the JS side gave
a *third* number depending on which calibration was pointed at.

## Is the calling logic separable from the frame loop? Yes.

`backend/swingvision/live.py`'s `LiveAnalyzer.push_position(ball_px, t_s)` is
a pure function: no frame, no `cv2`, no renderer. `LiveAnalyzer.push_frame`
is a thin wrapper that calls a detector and forwards to `push_position`. The
only thing coupled to `cv2.VideoCapture` is `live.stream()`, and only for
three things: reading `fps`, iterating a frame index `i`, and drawing an
annotated output video. None of that needs pixels once `fps` and the frame
count are already known some other way — and here they are: the cached
`ball_px` track already has one entry per source frame.

`backend/live_replay_novideo.py` (new) drives `push_position` directly over
a cached `ball_px` array, replicating `stream()`'s loop body only (see its
docstring for the line-by-line correspondence to `live_demo.py`'s replay
lambda). It is not a refactor of `live.py` — nothing in `live.py` changed.

**Frame-count assumption checked, not assumed:** `data/output/real_match.json`
records `video: {filename: tennis_sample.mp4, fps: 30.0, duration_s: 4.1,
width: 1920, height: 1080}`. `4.1 * 30.0 = 123.0`, which equals
`len(ball_px)` in `data/output/real_match.perception.json` exactly. The
script cross-checks this itself via `--match-json` and refuses to run if the
counts disagree, rather than silently assuming len(ball_px) == frame count.

## The calibration ambiguity was a harness bug, not a genuine unknown

`verify_live.js` read `data/court_pts.json`. That file's own `_audit` stamp
(written by `validate_new_clip.py --stamp`) says `"verdict": "DEGENERATE"`,
`"fit_residual_px": 38.1` — the project's own calibration gate already
rejects it as "not a physical camera view." `git log -p` on that file
surfaces commit `20a672e` ("Make a degenerate calibration announce itself
instead of breaking things quietly"), whose message states directly:
"live_demo.py's docstring pointed at court_pts.json; now
court_pts_refined.json, the good version of the same clip." Both files are
calibrations of `tennis_sample.mp4` / `real_match`; `court_pts_refined.json`
is the one stamped PASS (2.3 px residual) and is what `live_demo.py`'s own
docstring names. No video was needed to resolve this — the audit stamp and
the commit history settle it.

`verify_live.js` now reads `court_pts_refined.json`.

## The comparison, and the pre-registered bar

**Pre-registered before running:** exact match on call count, in/out per
call (order-matched), and `t_s` (both sides round to 2dp identically);
`margin_m` and `xy` within 0.001 m (allowing for the two sides solving the
homography by different algorithms — Python: SVD + Hartley-normalized DLT in
`calibration.compute_homography`; JS: a hand-rolled 4-point Gaussian
elimination in `live_calls.js`'s `computeHomography`. Bit-identical was
never the bar; sub-millimetre agreement was.)

**Python reference** (`backend/live_replay_novideo.py --keypoints
../data/court_pts_refined.json --cache ../data/output/real_match.perception.json
--match-json ../data/output/real_match.json --fps 30.0`):

```
7 calls (7 in / 0 out)
t=0.13s IN (+1.806 m) at (6.500, 1.806)
t=0.67s IN (+3.046 m) at (6.554, 16.441)
t=1.60s IN (+3.031 m) at (6.569, 17.969)
t=2.27s IN (+3.445 m) at (4.815, 15.732)
t=2.87s IN (-0.002 m) at (1.368, 0.220)
t=3.43s IN (+1.114 m) at (2.484, 13.399)
t=3.93s IN (+3.059 m) at (4.429, 17.860)
```

**JS port** (`node mobile/verify_live.js`, same calibration + same cached
track): identical 7 calls, 7 in / 0 out, and every `t_s`, `call`, `xy` and
`margin_m` matches to 3 decimal places — **zero divergence**, well inside the
pre-registered 0.001 m tolerance (measured diff was exactly 0.0 on every
field; see `data/output/live_calls_python_reference.json` and
`data/output/live_calls_js_port.json`, the two raw outputs this claim is
checked against).

**Python is the reference by decision.** This result is agreement of the JS
port WITH Python on this input, not independent proof either side is
correct — it establishes that the port has not drifted from the logic it was
translated from, on the singles / IN-only path this cached track exercises.

## What this does NOT verify

- **The doubles branch.** This track only exercises `singles: true` and
  produced 7 IN / 0 OUT — the known defect at `mobile/live_calls.js:145`
  (`isInSingles` called unconditionally, ignoring `this.singles`, while
  `_distanceInside` two lines below does honour it) is in the doubles path
  and is **not exercised by this comparison**. Still open, still a one-line
  fix + a test extension when someone touches that code (see
  `.claude/agent-memory/frontend-dev/MEMORY.md`).
- **Any OUT call.** This cached track produced 7 IN / 0 OUT under the
  correct calibration, so the IN/OUT boundary itself (the part most likely
  to expose a sign error) was not exercised either. The earlier, wrong-
  calibration run (`court_pts.json`) DID produce an OUT call, but that
  calibration is invalid, so nothing about that OUT call is trustworthy
  either way.
- **The video decode / capture path itself** — untouched, unexercised here.
  `live.stream()`'s `cv2.VideoCapture` loop, frame indexing against a real
  file, and the overlay renderer are not covered; this only proves the pure
  calling logic.
- **Whether `tennis_sample.mp4` really has 123 frames at 30.0 fps** — taken
  from `real_match.json`'s recorded metadata, not re-measured against the
  video file itself (which is not in the repo). If that metadata is wrong,
  this whole comparison is void; it is the one unverified premise underneath
  everything above.

## Files

- `backend/live_replay_novideo.py` — no-video Python driver (new)
- `mobile/verify_live.js` — now reads the correct calibration, asserts the
  verified expectation, exits non-zero on drift (was print-only)
- `data/output/live_calls_python_reference.json`,
  `data/output/live_calls_js_port.json` — raw outputs the 0.001 m claim
  above was checked against
