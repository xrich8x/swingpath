---
name: audio-hit-detection-mobile-port
description: audio.py's detect_impacts — corpus audio-track provenance is unverified since Session E3b, the O(n·win) rolling-median floor is a real mobile-port cost Accelerate can't cover, and this session had no code-execution tool at all
metadata:
  type: project
---

Researched 2026-08-28, overnight PM-ranked-#2 task. Full writeup:
`docs/evidence/audio-impact-screen-blocked-by-tooling-plus-gt-cost.md`.

## The session had no Bash/exec tool — the feasibility screen was NOT run

This researcher session's tool set was Read/Grep/Glob/Write/Edit/WebSearch/WebFetch
only — no shell execution. The brief asked to run `audio.detect_impacts` across
`data/incoming/`; that could not happen. **Zero clips were screened tonight.**
Check tool availability before pre-registering an execution-dependent deliverable
as achievable in a given session — this cost most of the session's value on
deliverable 1.

## The one fact that matters most, and it predates this session

`backend/tests/test_audio.py` (docstring) and `docs/archive/sessions/SESSION_E_ball_push.md`
(Session E3b, before 2026-07-21) both record: **every YouTube-pulled clip in the
repo was downloaded video-only — zero audio streams — except `tennis_sample.mp4`.**
That covers exactly the `yt_*`/`gold_*`/`am_*` corpus the task brief's stale counts
(Clay 9/Hardcourt 38/Shell 6/Grass 4, from `data/incoming/README.md`) describe. If
still true, `extract_audio` returns `None` before `detect_impacts` even runs for
most of that population — a **stronger, cheaper-to-state negative** than a DSP
bail-out, and a different bug (no track vs. a track the DSP gives up on). **Not
re-verified since Session E3b — the repo has grown since.** First thing the next
session with exec access should check, before touching thresholds.

## The corpus has grown to 213 files (README says 57) via `split_by_serve.py`

Two new batches post-date `data/incoming/README.md`: `hc1_*/hc2_*/hc3_*` (84 files,
Hardcourt) and five shell venues' `_p01.._p12` trims (~60 files: `hillsborough`,
`flexi_franz`, `flexi_joy`, `mpc_mixed`, `mpc_tuesday`). Both were cut by
`tools/split_by_serve.py`, which re-encodes with `-c:a aac` — so if the (not
checked-in) source recordings had audio, these trims should carry it forward.
**Whether they do is unverified.** These files are also unsuitable for
point-boundary *labelling* regardless of audio status, because the cutting tool
already consumed the boundary information (2 s pre-roll, dead time trimmed) —
see `[[point-boundary-ground-truth]]`.

## A real mobile-port cost beyond the two the brief named

`impact_envelope`'s rolling floor (`np.median`/MAD over `sliding_window_view`,
window ≈ 1000 samples at the ~1 kHz envelope rate) is **O(n·win) per pass, not
O(n)** — masked on desktop by numpy's vectorised C median, but for a match-length
clip that's billions of element-visits, and **Accelerate/vDSP has no rolling-
median primitive** (it's convolution/FFT/vector-arithmetic only). Porting this
needs a genuine streaming order-statistic rewrite (two-heap or histogram-bucket,
O(n·log win)), not a translation. Found by reading the code, not by benchmarking
it — confidence in the complexity claim is high (directly readable), confidence in
the A13 wall-clock magnitude is unmeasured.

The `butter`/`sosfiltfilt` → `vDSP_biquad` port (the brief's own line item) needs
the same parity discipline as the JS line-call mirror
(`tests/test_js_mirror_parity.py`) — SOS cascades map onto biquads cleanly, but
`sosfiltfilt`'s zero-phase double-pass plus scipy's default edge-padding
(`padtype='odd'`) has to be reproduced exactly, not assumed, or the two
implementations disagree most at clip start/end — exactly where a rally begins.

## Conditional finding worth keeping load-bearing

**If** the corpus actually carries audio (open question above), the signal itself
(band-pass + envelope + threshold) is cheap, CPU-only, and never touches the ANE —
likely the cheapest stage in the whole plan, once the rolling-median rewrite above
is done. That "if" is the whole ballgame and this session could not close it.
