---
name: video-free-parity-checks
description: How to verify a mobile JS port against the Python reference when the source video isn't in the repo — LiveAnalyzer.push_position is pure, drive it directly.
metadata:
  type: project
---

Established 2026-09-02 (`.claude/journals/frontend-dev.md`, that date;
`docs/evidence/live-call-parity-verified-without-video.md`).

**The technique, reusable for other on-device logic:** `LiveAnalyzer.push_position`
(`backend/swingvision/live.py`) is a pure function of `(ball_px, t_s)` — no frame, no
`cv2`, no renderer. The only thing coupling it to a real video is `live.stream()`'s
`cv2.VideoCapture` loop, and that loop exists only to learn `fps` and iterate a frame
index. If you already know both from elsewhere (a `match.json`'s recorded
`video.fps`/`video.duration_s`, cross-multiplied against `len(ball_px)` in the matching
`*.perception.json`), you can drive the pure function directly and never touch the
missing video. `backend/live_replay_novideo.py` is the reusable driver — CHECK, don't
assume, that `len(ball_px) == round(duration_s * fps)` before trusting it; it refuses
loudly if that cross-check fails.

**Before assuming a piece of Python logic needs a video to test: check whether the
frame-loop and the pure logic are actually separate.** They usually are in this codebase
— `push_frame` is a one-line wrapper around `push_position`, and the pattern (thin
frame-consuming wrapper around a pure core) recurs. Read the function signatures before
concluding a missing asset blocks verification.

**Result on record:** JS (`mobile/live_calls.js`) vs Python (`live.py`) on the cached
`real_match.perception.json` ball track, `court_pts_refined.json` calibration: 7 calls,
7 in / 0 out, both sides, every `t_s`/`xy`/`margin_m` equal to 0.000 m diff. This is
agreement, not independent proof — Python is the reference by project rule (CLAUDE.md
hard rule 1, "never let a model grade its own homework" extends here to "never treat
either port as ground truth for the other").

**What this did NOT touch:** the doubles branch of the JS port
([[known-js-port-defects]] — still open, still unexercised, this track is singles-only
and produced no OUT calls at all) and the actual video decode / `cv2.VideoCapture` path,
which remains genuinely untestable without `data/tennis_sample.mp4`.
