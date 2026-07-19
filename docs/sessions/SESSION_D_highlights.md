# Session D — Auto-highlights / per-rally clips

**Kickoff prompt:** `Do Session D (docs/sessions/SESSION_D_highlights.md)`
**User brings:** ideally one longer clip (5-15 min) so highlight selection is
meaningful; otherwise the existing e2e clips demo the mechanics.

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
1. `run.py highlights <video> --match <match.json> [--out-dir]` → per-rally mp4s
   (stream copy, 2 s pre-pad / 1.5 s post-pad) + `highlights.json` manifest
   (rally id, file, rank, why). Unit-test the boundary math; smoke-test that a
   cut clip opens and has ~expected duration.
2. Optional `--reel`: concat the top-3 into one highlights.mp4 (concat demuxer).
3. Dashboard: Rallies tab gains a play button per rally (serves the clip file
   from the output dir via the dev server / file URL) + a "Top rallies" strip.
4. Verify on a long clip end-to-end: durations, no rally cut short at the START
   (keyframe snap must only extend), reel plays.
5. Commit + push.

## Definition of done
- One command turns video+match.json into per-rally clips + manifest
- Clips never start inside the rally (pad + snap verified on a real file)
- Dashboard plays individual rallies; tests pass; pushed

## Guardrails
- Generated mp4s are artifacts: gitignore the output dir (same rule as
  analyzed.mp4); the manifest JSON may be committed as evidence.

## Results (fill in during the session)
- _pending_
