---
name: audio-lane-screened-not-measured
description: The 2026-08-28 audio feasibility screen — no bail-outs anywhere including indoor shell, level-dependent threshold, and the three on-device port items with measured costs
metadata:
  type: project
---

**The audio lane has data and the detector does not collapse indoors.**

**Why it matters:** indoor Shell is the hardest venue for vision (0 of 5 on court
detection) and carries 62 of 64 clips with audio, because the founder's own venue
recordings (`flexi_*`, `mpc_*`, `hillsborough_*`) are re-encoded by
`tools/split_by_serve.py` with `-c:a aac`. Corpus census: 88 of 116 clips have audio
(Shell 62/64, Hardcourt 21/39, Clay 5/9, Grass 0/4). Two live repo files claimed every
clip was video-only; that claim predates the Manila recordings and is stale.

**Measured 2026-08-28, label-free, 309.3 min of audio:**

- `detect_impacts` hits its `max_events_per_s` bail-out on **0 of 88** clips, including
  **0 of 62** indoor Shell. The feared correlated audio/vision failure on echo-heavy
  indoor courts is **refuted**, not confirmed.
- Shell yield is lower and splits by RECORDING, not surface: quiet venues (flexi,
  mpc_tuesday: crest 21–25 dB) run ~0.33 events/s; hot, clipping venues (hillsborough,
  mpc_mixed: crest 14–18 dB, peak 0.0 dBFS) run ~1.0–1.13. Outdoor runs ~1.45–1.58.
- The **absolute** test (`min_contrast × global median envelope`) is binding everywhere,
  and discards 2.4–2.9× more events on the quiet indoor venues than the 1.2–1.3× it
  discards outdoors. First thing to test once labels exist. Do not tune it blind.

**No recall or precision figure exists or may be derived.** The only per-stroke reference
in the repo is `tools/audio_hits.py` against SwingVision's burned-in HUD, barred by rule
11 for anything but a speed AGREEMENT figure. Two rally-segmentation figures were already
withdrawn for that premise. Say "this is a feasibility screen, not an accuracy
measurement" and stop.

**Three on-device items, all measured (`data/output/audio_ondevice_probe.json`):**

1. `extract_audio` shells out to bundled desktop ffmpeg → `AVAssetReader` / `AVAudioFile`
   + `AVAudioConverter`.
2. `sosfiltfilt` → vDSP biquad cascade. 4 sections; zero-phase double pass; scipy default
   `padtype='odd'` with `padlen=27`. Getting the padding wrong moves the output **4.83%
   of peak in the first and last 27 samples** and 0.11% in the interior. Needs a parity
   harness like the JS line-call mirror.
3. **CONFIRMED O(n·win), not O(n).** On a 28.2 min clip the rolling median/MAD floor
   costs **26.16 s against 0.82 s** for the entire band-pass stage — 32× — and 3.38
   billion element visits. Flat in n, doubling with win. The shipped expression also
   peaks at a **13.5 GB** allocation, which has never bitten only because nobody has run
   it on a full match. Accelerate has no rolling-median primitive.
   **The rewrite is prototyped and pinned:** `tools/audio_ondevice_probe.streaming_med_mad`
   maintains a sorted window and computes the MAD as an order statistic of the merge of
   two already-sorted deviation sequences (O(log win), no second sort), bit-identical to
   `np.median` — `backend/tests/test_audio_streaming_floor.py`, 10 tests.

**How to apply:** treat the audio lane as viable and unblocked on the engineering side,
and blocked on the measurement side until a rule-11-compliant per-stroke reference
exists. Detail: `docs/evidence/audio-impact-feasibility-screen.md`.

Related: [[mobile-port-split]], [[ios-architecture-rules]], [[traps-this-project-paid-for]].
