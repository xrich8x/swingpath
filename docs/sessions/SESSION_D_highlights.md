> **STATUS: SHIPPED 2026-08-08** — stamped 2026-08-15 during doc cleanup.
> Per-rally clips + top-3 reel, ffmpeg stream copy.
> This file is the PRE-REGISTERED BRIEF, kept for its gate and reasoning.
> For what actually happened and the current state of play, read
> [SCOREBOARD.md](../../SCOREBOARD.md) — not this file.

# Session D — Auto-highlights / per-rally clips

**Kickoff prompt:** `Do Session D (docs/sessions/SESSION_D_highlights.md)`
**User brings:** nothing required. `data/yt_match40.mp4` (6 min, calibrated at
0.9 px — the best residual in the repo) is long enough for highlight selection to
be meaningful; a longer personal clip would be better still.

**Status (2026-08-08):** this is now the LAST unbuilt product feature. Every other
open item is either closed on evidence or blocked on the user's labelling time.
Needs no ML and carries no measurement risk.

## Premises re-verified 2026-08-08 — do not re-derive these

Session H's lesson was that a brief's premises rot (all three of the court brief's
were wrong by the time it ran). These were re-checked against the code:

| Claim | Status |
|---|---|
| `imageio-ffmpeg` is a dependency and bundles the binary | OK — `backend/requirements.txt:7`; exe resolves and exists |
| An ffmpeg shell-out pattern already exists | OK — `annotate._to_h264` (annotate.py:146): `imageio_ffmpeg.get_ffmpeg_exe()` + `subprocess.run`. Lift a shared `_ffmpeg_exe()` rather than copying it |
| match.json times are SOURCE-video seconds, not decimated | OK — `fps_eff = fps / frame_step` and track times use it (pipeline.py:1213), so `i / fps_eff = i * frame_step / fps`. Cutting the source at `start_s` is valid at ANY frame step. Do not "correct" for frame_step |
| The dashboard can already play video | OK — `Broadcast.jsx` takes a `videoUrl` prop; `frontend/public/analyzed.mp4` is the existing serving pattern, with a HEAD-check empty state in `App.jsx:26`. No new server needed |
| gitignore already covers the artifacts | OK — `data/output/*` ignores mp4 while `!data/output/*.json` keeps the manifest. Only new rule needed: `frontend/public/rallies/` |
| `Rallies.jsx` already computes top-confident-speed per rally | OK — Rallies.jsx:24-26. Reuse that exact rule for ranking so the CLI and the UI cannot disagree |

**THE ONE DESIGN CONSEQUENCE.** `rally.start_s = raw_shots[0]["t_hit_s"]`
(pipeline.py:241) — the first CONTACT, not the point start. So the 2 s pre-pad below
is SEMANTIC, not just keyframe insurance: without it every clip opens mid-swing.

## Goal
SwingVision's signature convenience: every rally becomes its own playable clip,
dead time disappears, and the dashboard offers "best rallies".

## Researched approach — cutting strategy (this is the part people get wrong)
ffmpeg has two cutting modes with a real trade-off:
- **Stream copy** (`-c copy`) is I/O-bound (near-free) but can only cut on
  KEYFRAMES — the start snaps to the nearest keyframe at/before the requested
  time. Keyframe spacing is typically 2-10 s, so cuts can start seconds early.
- **Re-encode** is frame-accurate but ~5-10× slower than real time.

Decision for us: rally boundaries already carry PADDING (we want a second of
lead-in anyway), so **stream copy is the default** — request `start_s - 2.0`
and accept keyframe snap (never cuts INTO the rally, only adds lead-in).
Re-encode only for the "share this rally" export path where exact trims matter
(flagged option, not default). Batch pattern: one ffmpeg invocation per rally
from Python; for a combined highlight reel, cut parts with stream copy then
join with the **concat demuxer** (also stream copy — near-instant).
`imageio-ffmpeg` is already a dependency and bundles the ffmpeg binary — use
`imageio_ffmpeg.get_ffmpeg_exe()`; do NOT assume a system ffmpeg on Windows.

Sources:
- [Clip sections of a video with ffmpeg (Mux)](https://www.mux.com/articles/clip-sections-of-a-video-with-ffmpeg)
- [Trim/cut: fast, lossless, or frame-accurate (TechEarl)](https://techearl.com/ffmpeg-trim-cut-video)
- [Precise timestamps without re-encoding (mpegflow)](https://www.mpegflow.com/recipes/trim-cut-video)
- [Cutting videos with FFmpeg — keyframe behaviour (Mark Buckler)](https://www.markbuckler.com/post/cutting-ffmpeg/)

## Highlight selection (v1 heuristics — deterministic Logic-layer, no ML)
Rank rallies by: shot_count (longest rally), top confident shot speed, and
rally duration. "Top 3" list + full rally index. (Winner/unforced-error
reasoning is explicitly OUT of scope — that's a separate, harder feature.)

## Plan

**1. `backend/swingvision/highlights.py`** — Logic layer, pure and testable. Keep
ffmpeg in exactly ONE function so the rest needs no binary to test.

```
rank_rallies(match, top_n=3) -> list[dict]     # deterministic; a plain-English `why` each
clip_bounds(rally, duration_s, pre_s=2.0, post_s=1.5) -> (start_s, end_s)  # clamped to [0, duration]
cut_clips(video_path, match, out_dir, *, top_n=3, reel=False, exact=False) -> manifest
```

Cutting: `-ss <start> -i <video> -t <dur> -c copy`. `-ss` BEFORE `-i` seeks to the
nearest keyframe at or before the timestamp, so a clip can only start EARLIER, never
later — that is what makes stream copy safe here. `exact=True` re-encodes (libx264,
mirroring `_to_h264`'s flags) for the share path; not the default.

**2. `run.py highlights`** — follow the existing `_cmd_*` + `sub.add_parser` pattern.
Writes `rally_<NN>.mp4`, plus `highlights.json` recording rally id, file, rank, why,
and **requested vs actual start** (the evidence that the snap only extended).

**3. `--reel`** — concat the top-3 with the concat demuxer (stream copy; the parts
share codec params because they come from one source, so it is near-instant).

**4. Dashboard** — `Rallies.jsx` gains a play button per row plus a "Top rallies"
strip. Reuse `Broadcast.jsx`'s `<video>` handling and its missing-file empty state
rather than writing a second player. Write clips to `frontend/public/rallies/` and
reference `/rallies/rally_03.mp4`, exactly how `analyzed.mp4` is already served.

**5. Tests** (`backend/tests/test_highlights.py`) — no ffmpeg needed for the ones
that matter: `clip_bounds` clamps at both ends; **a clip never starts after
`rally.start_s`** (the load-bearing property); ranking is deterministic with a pinned
tie-break; ranking ignores `speed_confident is False` shots, matching the UI. One
`importorskip`-guarded ffmpeg smoke test for duration.

**6. Verify end to end** on a clip long enough to mean something — `yt_rally2` is
only 37 s. Use `data/yt_match40.mp4`:

```
cd backend
.venv-train/Scripts/python.exe run.py analyze ../data/yt_match40.mp4 --keypoints ../data/yt_match40_pts.json --out ../data/output/yt_match40.json --device cuda
.venv-train/Scripts/python.exe run.py highlights ../data/yt_match40.mp4 --match ../data/output/yt_match40.json --out-dir ../../frontend/public/rallies --reel
```

**7. Record it** — fill in Results below; move "Highlights / clip export" out of
SCOREBOARD's **Open** into **What has worked**; add `highlights` to the README
command list. (The scoreboard-guard hook refuses a code commit that skips this.)

## Definition of done
- One command turns video+match.json into per-rally clips + manifest
- Clips never start inside the rally (pad + snap verified on a real file, via the
  manifest's requested-vs-actual start)
- Dashboard plays individual rallies; tests pass; pushed

## Guardrails
- Generated mp4s are artifacts: gitignore `frontend/public/rallies/` (the
  `data/output` rules already cover the rest); the manifest JSON is committed as
  evidence.
- This is a **Logic-layer** feature. No model goes anywhere near rally ranking.
- Guard the 0-shot rally — `raw_shots[0]`-style indexing would break on one.
- Never re-encode by default: stream copy is near-free, re-encode is 5-10x slower
  than real time.

## Out of scope
Winner / unforced-error classification, ML excitement scoring, social formats
(vertical crop, burned-in captions), audio-based highlight detection.

## Results (2026-08-08) — SHIPPED

`backend/swingvision/highlights.py` + `run.py highlights` + per-rally playback in the
Rallies tab. 258 tests (was 243); 15 new in `backend/tests/test_highlights.py`.

**The premise check paid for itself twice.**

1. `rally.start_s` is the first CONTACT, so the 2 s pre-pad is what makes a clip
   watchable — not just keyframe insurance. Pinned by
   `test_clip_starts_before_the_first_contact`.
2. Times are source-video seconds at any frame step, so no `frame_step` correction
   was needed anywhere. Had that been assumed the other way, every clip on a 60 fps
   clip would have been cut at half the right timestamp.

**THE BUG THAT MATTERED, and it was hiding behind a check that could not fail.**
The first cut used the obvious approach — ask ffmpeg for the padded start, let it
snap to a keyframe — and "verified" it by reading the clip's own container start
offset. That offset is ~0 for every cut clip, so the check was comparing
`0 <= rally_start_s`: **vacuously true for every rally in the file.** It was caught
because the manifest also reported a nonsense median lead-in of 176 s.

Underneath it was a real defect. With `-ss` before `-i`, `-t` counts from the
KEYFRAME, so a snap of dt slides the whole window back and takes dt off the END.
yt_match40's keyframes are **5.52 s** apart against a median rally of 4.2 s, so
short points were losing their finish. Measured directly: requesting [3.60, 8.90]
around a rally ending at 7.4 s produced a window of [0.00, **5.30**] — 2.1 s of the
point gone.

Fixed by not guessing: `keyframe_times()` enumerates every keyframe in one pass
(**0.7 s** for a 6-minute clip) and each clip starts ON the last keyframe at or
before the padded start. Nothing snaps, `-t` is exact, and containment holds by
construction. `run.py highlights` now prints `verified: all 63 clips contain their
whole rally (lead-in 1.7-7.3s, median 5.1s)` — real numbers on both edges.

The regression test needed the same care: at the fixture's original 1 s keyframe
spacing the BROKEN code still covered the rally, so the test would have passed
either way. It now builds a coarse-GOP fixture (5 s) that reproduces the real
condition.

**A real bug the happy path would not have caught.** The manifest is served from one
fixed path but rally ids are per-match, so loading a DIFFERENT match still matched
clips by id — the Demo match showed Play buttons wired to yt_rally2's clips, and
clicking rally 3 would have played an unrelated point with nothing on screen saying
so. Fixed by gating on `clips.video === match.video.filename`. Verified both ways in
the browser: Demo 42 rows / 0 play buttons / hint shown; Analyzed 9 rows / 9 play
buttons / no hint.

**Verified in the browser**, not asserted: `/rallies/rally_06.mp4` loads at
`readyState 4`, `duration 8.68 s` — exactly the 5.2 s rally + 2.0 pre + 1.5 post —
1280x720, `error null`, served 206 Partial Content, zero console errors.

Ranking is deterministic (shot count → top *confident* speed → duration → rally id)
and deliberately mirrors `Rallies.jsx`'s existing speed rule, so the reel and the
table can never disagree about which rally was best. `test_ranking_ignores_unconfident_speeds_like_the_dashboard`
pins that: a 200 km/h shot flagged unconfident must not win.

**Verified on the real match**: yt_match40, 196 shots / 63 rallies. 64 keyframes
enumerated, 63/63 clips cut in **4.3 s** (stream copy — a re-encode would be
minutes), all landing on a keyframe, **0** failing containment, on-disk durations
within 0.19 s of requested across a 12-clip sample.

**IT ALSO EXPOSED A PRE-EXISTING DEFECT, which is not ours to fix here.** 63
rallies in 5.9 minutes is one point every 5.6 s, with a **median inter-rally gap of
0.0 s** — the rallies are contiguous, so `events` is fragmenting continuous play
rather than finding 63 points (real tennis is ~20-25 s between points). Highlights
did not cause it; it made it visible, because the fragments become 63 clips whose
padded spans sum to 148% of the source. Logged as an open item.

Also corrected while here: README still listed the manual-correction UI as pending
build-order work and as a known limitation. It shipped 2026-08-06.
