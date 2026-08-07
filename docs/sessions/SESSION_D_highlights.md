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

## Results (fill in during the session)
- _pending_
