# frontend-dev memory

Seeded 2026-08-28 from the mobile viability audit and the iOS research done up to that
date. Nothing here was produced by this agent — it is inherited context so you do not
re-derive it.

## What already exists, and is verified

`mobile/` holds a working starting point: the ball model exported to ONNX fp32 and int8
(11 MB) with argmax baked into the graph, so the per-frame output is 0.9 MB rather than
236 MB; `live_calls.js` (the line-call logic and homography, pure JS); `ball_detector.js`;
`verify_live.js`; and `MOBILE.md` as an integration guide. `court.py` is mirrored to
`frontend/src/lib/court.js` and the mirror is enforced by `tests/test_js_mirror_parity.py`.

`live_calls.js` is genuinely verified against the Python reference now (2026-09-02,
[[video-free-parity-checks]]) — singles-path, real cached track, 7/7 calls exact to
0.001 m — AND, separately (2026-09-02, [[doubles-alley-bug-fixed]]), both singles AND
doubles branches on 21 synthetic boundary cases, 42/42 exact. Earlier claims of
"verified bit-identical" in this repo (including a prior version of this memory file)
were **unverifiable, not verified** — the harness was silently dead, then silently
reading a degenerate calibration, then (separately) silently not exercising doubles at
all. Don't repeat an inherited verification claim without re-checking what it actually
covers — "verified" always needs a "verified WHAT, on WHAT input" attached.

## iOS execution model — the finding that shapes the whole app

**There is no multi-hour background compute on iOS at any tier.** `BGProcessingTask` is
minutes not hours, is scheduled at the system's discretion (typically overnight, on
charger), dies the moment the user picks up the phone, and is **blocked entirely after a
force-quit** with no documented override. A CPU-monitor kill (80% over 60 s) has been
observed firing even on charger.

**Therefore the foreground is the primary execution surface**, not a fallback. The phone
is mounted on a fence, dedicated to the task, screen on, for the whole match — that is
exactly the situation where foreground compute is fully available. SwingVision ships this
way on iPhone 11+, which is third-party evidence the thermal envelope exists.

**Consequences that are architecture, not polish:**
- Resumable checkpointing is required. The job *will* be interrupted.
- `isIdleTimerDisabled` while analysing.
- Background is an opportunistic top-up, never a completion promise.
- **GPU submission from the background is refused** — on iOS 26.2 it aborts the process.
  This is why Core ML must be pinned `.cpuAndNeuralEngine`, never `.all`.
- **Do not declare the `audio` background mode** without testing: Apple DTS suspects it
  re-enables the CPU kill-switch that charging is supposed to disable. Capture audio in
  the `AVCaptureSession` without the background entitlement — different things.

## Capture rules

- **Video stabilisation OFF.** It warps the frame, destroys homography consistency, and
  conflicts with any IMU prior. Correctness, not quality.
- **1080p60 with per-frame presentation timestamps preserved** — everything downstream
  needs frame-accurate time.
- Record at 60, analyse at 30 by default; keeping the frames preserves the option to
  re-analyse a disputed game at full rate. `--full-rate` costs 2× perception time for
  +5.8 pts close-call accuracy at 1.5 m.
- **Preprocessing can exceed inference.** Ultralytics' own iOS profiling found ~8 ms
  preprocessing against ~7 ms inference. It does not shrink when the model does.

## Refusal is a designed surface

- **Manual 4-corner tap is the shipped calibration path**, not a failure state. On a
  touchscreen with pinch-zoom and a loupe it is genuinely better than the desktop mouse
  version — of everything that gets harder on mobile, this is the one thing that gets
  easier. A v1 can ship with manual calibration only and skip court auto-detection
  entirely.
- **Stats already refuse rather than invent.** Player distance returns nothing below a
  ≥50% coverage bar and refuses outright in doubles — it used to show a confident 0.0 m
  for a player the system never saw. Show coverage, not a fake number.
- **A scoreline is not a measurement.** `stats.score_validation_note` exists specifically
  to stop the UI presenting one as measured. Do not render it as if it were.
- **Never show an invented confidence percentage.** Too close to call is an honest answer.

## Numbers you may not quote

- **No phone fps has ever been measured in this repo.** Every mobile speed statement is an
  expectation from model size and structure. Do not put one in the UI or in copy.
- **The headline accuracy figures are geometry ceilings, not end-to-end.** The 95.9%
  line-call figure and the 54/69/81% camera-height curve both come from a harness that
  hands the bounce position over for free (`tools/synth_truth.py:251-253` — "the same
  information a perfect bounce detector would have"). Do not put 95.9% in user-facing copy.
- **A low mount is a measured ceiling:** 54.0% at 1.0 m against a **56.2% majority-class
  floor** — worse than answering "in" every time. This is why camera-height guidance is a
  product feature.

## Live path — remaining known gap

`live.py` never reaches `analytics.is_in`, so the live path has no serve boxes — a
serve landing deep is called IN. Still open, not touched by the doubles-alley fix.

(The doubles-alley `isInSingles`-called-unconditionally bug is FIXED — see
[[doubles-alley-bug-fixed]]. Do not re-diagnose it; if the live-call verdict looks
wrong in doubles again, it's a NEW bug, not a recurrence of the old one — check
`mobile/verify_live_doubles.js` still passes first.)

## More memory files

- [Video-free parity checks](video_free_parity_checks.md) — how live-call JS/Python
  parity was verified without the missing sample video; the reusable technique
- [Committed calibration files can be degenerate](committed_calibration_files_can_be_degenerate.md)
  — check the `_audit` stamp before trusting any `data/*_pts.json` as a reference
- [Doubles-alley bug: fixed and exercised](doubles_alley_bug_fixed.md) — the
  `isInSingles`-called-unconditionally fix, and the general lesson: a fix is not done
  until the SPECIFIC branch is driven through the real code path, not just patched
