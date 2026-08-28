# Audio impact feasibility screen — could not execute; here is what desk research found instead, plus the priced point-boundary ground-truth line item

> Overnight task, 2026-08-28. Ranked #2 by the PM, CPU-only, unattended.
> Two deliverables were requested: (1) a feasibility screen of `audio.detect_impacts`
> across `data/incoming/`, explicitly not an accuracy measurement; (2) a priced line
> item for compliant point-boundary ground truth. **Deliverable 1 could not be run —
> this session's tool set had no code-execution capability (no Bash/shell tool was
> provided to this agent).** That is stated plainly per the task's own instruction
> ("if the screen produces nothing interpretable, say so rather than dressing an
> estimate as a finding") rather than fabricated. Deliverable 2 does not need
> execution and is priced below from file counts, committed documentation, and the
> task's own stated labelling rate.

## Deliverable 1 — what a desk audit found, and exactly what should run next

**No `detect_impacts` call was made tonight. Zero clips were screened.** Everything
in this section is read from the repository as it stands, not measured.

### The corpus is not what the task brief described

The brief's counts (Clay 9, Hardcourt 38, Shell 6, Grass 4 = 57 files) match
`data/incoming/README.md`, which is stale. The directory as it exists today holds
**213 `.mp4` files** (excluding `Raw - Do Not Process`), because two large batches
were added after the README was last updated:

- **Hardcourt**: `hc1_1..hc1_8`, `hc2_1..hc2_27`, `hc3_1..hc3_49` — 84 files, each in
  its own subdirectory as `hcN_k/hcN_k-1.mp4`.
- **Shell**: `hillsborough_p02..p12`, `flexi_franz_p01..p12`, `flexi_joy_p01..p12`,
  `mpc_mixed_p02..p12`, `mpc_tuesday_p01..p12` — roughly 60 files across 5 venues.

Both batches were produced by `tools/split_by_serve.py` (per
`docs/archive/sessions/SESSION_O_shell_courts.md`, which names five of them as the
court-calibration label targets). This tool cuts a long source recording into
6–30 s point clips using a motion-lull heuristic, and re-encodes with **`-c:a aac`**
— i.e. it explicitly preserves an audio track when the source has one. **Whether the
underlying "Raw" recordings for these five venues carry audio is unverified tonight**
(their un-cut originals are not in this repo; only the point-trims are).

**Recommendation:** before re-running this screen, decide whether to scope it to the
57 files the brief named (the older, README-listed corpus) or the full 213. They are
different populations with, per the finding below, probably different audio
provenance.

### A documented prior finding this screen would have re-tested first

`backend/tests/test_audio.py` (module docstring, line 6) and
`docs/archive/sessions/SESSION_E_ball_push.md` (lines 690-696, Session E3b) both
record, as committed fact rather than something re-derived tonight:

> "every YouTube clip in data/ was pulled video-only — zero audio streams (only
> `tennis_sample.mp4` has sound)."

That statement covers exactly the corpus the brief describes (`yt_*`, `gold_*`,
`am_*` — the README-listed 57, sourced by YouTube download). **If still true, the
feasibility screen for that population would fail before `detect_impacts` even
runs** — `extract_audio` would return `None` for every file except
`tennis_sample.mp4`, which is a *stronger* and cheaper-to-state negative than
"the DSP bails out at `max_events_per_s`." Two different bugs (per project rule
4/CLAUDE.md hard-rule): "no audio track" and "the detector saw a track and gave up"
are not the same failure, and conflating them would misdiagnose a footage-acquisition
problem as a DSP-tuning problem.

**This has not been re-verified since Session E3b** (session log entry sits before
2026-07-21; the repo has since added the `hc*`/venue batches, none of which existed
then). It could have changed. Nothing here confirms or refutes it for the current
213-file corpus — it is a documented prior state, cited with file and line, not a
finding produced tonight.

### The `detect_impacts` mechanism, read (not run), for the next session that has exec access

- Band-pass 1.5–7 kHz, 4th-order Butterworth SOS, `sosfiltfilt` (zero-phase).
- Envelope: rectify, 4 ms moving-average smooth, decimate to ~1 kHz.
- Threshold: **both** a rolling median + `k_mad(=6.0)`×MAD floor over a 1 s window
  (adapts to a drifting noise level) **and** an absolute floor of
  `min_contrast(=4.0)` × the clip's global median envelope.
- Peaks de-duplicated within `min_sep_s=0.22 s` (kills direct-sound + first-echo
  doubles — relevant on shell specifically, since echo is the shell failure mode
  the brief is trying to catch).
- **Self-declare-useless**: if `len(events) / duration > max_events_per_s(=2.5)` on
  a clip longer than 2 s, the whole call returns `[]` (`audio.py:157`).

A five-minute script for the next session with exec access:

```python
# NOT RUN. Sketch for the next session with a shell tool.
import sys, json
from pathlib import Path
sys.path.insert(0, "backend")
from swingvision import audio

rows = []
for surface in ["Clay", "Hardcourt", "Shell", "Grass"]:
    for f in sorted(Path(f"data/incoming/{surface}").glob("**/*.mp4")):
        got = audio.extract_audio(str(f))
        if got is None:
            rows.append({"file": str(f), "surface": surface, "status": "no_audio_or_no_ffmpeg"})
            continue
        samples, sr = got
        dur = samples.size / sr
        times = audio.detect_impacts(samples, sr)
        env, erate = audio.impact_envelope(samples, sr)
        import numpy as np
        floor = float(np.median(env)) + 1e-9
        contrast = float(np.percentile(env, 99)) / floor
        rows.append({"file": str(f), "surface": surface, "status": "ok" if times or dur <= 2 else "bailed_out_or_empty",
                     "dur_s": round(dur, 1), "n_events": len(times),
                     "rate_per_s": round(len(times) / max(dur, 1e-9), 3),
                     "p99_over_median_contrast": round(contrast, 1)})
Path("data/output/audio_screen.json").write_text(json.dumps(rows, indent=2))
print(f"{sum(r['status']=='no_audio_or_no_ffmpeg' for r in rows)} of {len(rows)} had no audio track")
```

Report shell (`Shell/`) as an isolated row, per the brief — do not pool it with the
other three surfaces even in this future run, because indoor echo is exactly the
failure mode `min_sep_s` and the two-part threshold are trying to survive, and
pooling would let three surfaces' good behaviour hide one surface's bad behaviour.

---

## Deliverable 2 — pricing the compliant point-boundary ground truth

**What every number below is measured against:** file counts and directory
listings in this repo, read tonight; durations are **stated as unmeasured
estimates** from video titles, not from `ffprobe` (no exec tool this session).
The labelling rate (30–45 min human time per 30 min of video, ~150 clicks per
clip) is the planning assumption **given in the task brief**, not something
measured here.

### Split the cost the way `[[point-boundary-ground-truth]]` already settled it

Point boundaries are **logic** under this project's own architecture rule (a rule
over ball-in-play state and bounces), not perception — so labels are needed for
**evaluation only**, never for training. That collapsed the prior estimate from "15
matches" to "3–5 matches (~500 points)." This session prices that reduced set
concretely against what footage the repo actually has.

### The only compliant source of *continuous* match footage is 9 files, and they are not evenly spread across surfaces

`data/incoming/Raw - Do Not Process/` holds 9 full-length YouTube downloads whose
trims are already scattered through the surface folders (per
`data/incoming/README.md`'s gold table and the file list below). These are the only
candidates in the repo for point-boundary labelling, because everything else has
already been cut to short clips (single points or single frames) by
`split_by_serve.py` or a court-labelling tool — and a clip pre-trimmed to one point
cannot supply a *boundary* label, only a *content* label; the trimming already
consumed the information a boundary label would need (2 s pre-roll baked in, dead
time between points already removed).

| Raw file | Title (verbatim, truncated) | Surface (from where its trims live) |
|---|---|---|
| `L73ep7JHiJ4` | UTR 10 vs UTR 10 Singles Practice Match [1st Set] | Hardcourt |
| `tc8CGFxyRE8` | USTA 5.5 vs USTA 5.0 or UTR 12 vs UTR 10 | Hardcourt |
| `uR5q2cSM6AY` | INSANE Point Play! 12 UTR vs 13yo Junior | Hardcourt |
| `HoHxFSX_gLk` | I Challenged a 12 UTR to Slice Only | Hardcourt |
| `e8T34KoJzOw` | USTA 4.5 vs UTR 12.5! | Hardcourt |
| `A7vXlWIlyrI` | Almost 50, Out Of Shape & SUPER GOOD! (UTR 9 vs 9) | Hardcourt |
| `UHf0LeMU2pg` | 7 UTR vs 8 UTR | Hardcourt |
| `CYqapSq5llo` | My Opponent Hits & Acts CRAZY!! UTR 9 vs 10 | Clay |
| `sAjkpeRq4P4` | Amateur Tennis - Full Match - LK 13.4 vs LK 15.8 (NTRP 4.0) | Clay |

**7 Hardcourt, 2 Clay, 0 Shell, 0 Grass.** There is currently no full-length,
continuous recording of a shell or grass match in this repository — the shell
material that exists (`hillsborough`, `flexi_franz`, `flexi_joy`, `mpc_mixed`,
`mpc_tuesday`) survives only as `split_by_serve.py`'s point-trims, whose originals
are not checked in. Grass has 4 broadcast/highlight clips
(`eala_swiatek`, `eala_segment`, two IDs), which is also disqualified on a second,
independent ground: this project's own rule against benchmark transfer — broadcast
footage is not the fixed-phone amateur target this measurement is supposed to
validate, whatever its edit status.

**This is the line item's headline constraint, not a footnote: point-boundary
ground truth can be built for Hardcourt and Clay tonight-cheap; it cannot be built
for Shell or Grass without new recordings.** That is a scoping decision, not a
labelling-hours problem.

### A prerequisite the brief did not ask for but the footage requires

Titles like "vs" match-up videos are a common YouTube tennis-content genre, and
some channels in that genre jump-cut dead time out of the recording for viewer
retention. If any of these 9 are edited that way, they cannot supply dead-time-trim
ground truth (the join itself removes the very interval being measured) even
though they could still supply a point *count*. **Before spending any labelling
budget, a human needs ~5 minutes per candidate to scrub for a continuous,
unedited take** — this was not verified tonight (no video playback in this
session's toolset either). Budget it as a 45-minute prerequisite across the 9
candidates, separate from the labelling hours below.

### The price

Using the brief's own rate (30–45 min human time per 30 min of video) and the
titles' implied length (30–70 min per file; **unmeasured**, flagged), for an
evaluation set of **4–5 matches restricted to what's available — 3–4 Hardcourt +
1 Clay**, spanning ~150–225 minutes (2.5–3.75 hours) of source video:

| | Low estimate | High estimate |
|---|---|---|
| Matches labelled | 4 | 5 |
| Total video length | ~150 min (2.5 h) | ~225 min (3.75 h) |
| Points captured (60–80 / 30 min) | ~300–400 | ~450–600 |
| Human labelling time (30–45 min / 30 min video) | ~2.5–3.75 h | ~3.75–5.6 h |
| Scrub-for-edits prerequisite | 20 min (4 clips) | 25 min (5 clips) |
| **Total human time** | **~2.8–4.1 h** | **~4.2–6.1 h** |

**Call it 3–6 human hours**, same order of magnitude as the already-approved
far-court queue (4,087 frames / 4–5 h) — a number the founder could accept or
refuse on the same footing.

**What it buys:** a tolerance-based evaluation set (± N seconds, plus a count/
alignment score — never a raw tIoU against one annotator's frame, per
`[[point-boundary-ground-truth]]`'s citation of Sigurdsson et al. 2017) for
whatever point-boundary/dead-time-trim logic gets built — audio-based,
vision-based (bounces + ball-in-play state), or fused. It does **not** create a
training set (point boundaries are logic, not perception, so none is needed), and
it does **not** cover Shell or Grass — those stay unmeasured until continuous
footage of those surfaces exists in the repo.

**What would disprove this estimate:** an actual `ffprobe` pass on the 9 raw files
(seconds of work once exec access exists) replacing the title-based length guess;
and the edit-scrub above, which could remove some candidates entirely if they turn
out to be pre-cut.

---

## On-device line items (added to the two named in the brief)

1. **`extract_audio` → `AVAudioFile`/`AVFoundation`.** Decode-to-PCM is a solved,
   cheap, first-party API path; no ANE involvement. Low risk, not costed further —
   this is an ordinary port, not a research question.

2. **`butter`/`sosfiltfilt` → `vDSP_biquad`/`vDSP_biquadm` cascade.** Directly
   supported by Accelerate — SOS sections map onto biquad cascades natively.
   **Cannot be assumed bit-identical.** `sosfiltfilt` is zero-phase (forward pass,
   then a second pass on the time-reversed signal) with scipy's default edge
   padding (`padtype='odd'`, `padlen` derived from the cascade's order) — both the
   reflection scheme and the pad length have to be reproduced exactly in Swift or
   the two implementations will disagree hardest exactly at clip start/end, which
   is also where a rally beginning is most likely to sit. This needs the same
   discipline the JS line-call mirror got (`tests/test_js_mirror_parity.py`): a
   parity harness against a fixed synthetic signal plus one real clip, with an
   explicit numeric tolerance gate, before this is trusted for anything.

3. **NEW, not named in the brief — found by reading `impact_envelope` and
   `detect_impacts`, not by running them.** The rolling floor
   (`np.median`/`np.median(np.abs(...))` over `sliding_window_view(padded, win)`,
   `win ≈ floor_win_s × erate ≈ 1000` at the ~1 kHz envelope rate) is a **per-window
   recompute — O(n·win), not O(n)**. On a desktop this is masked by numpy's
   vectorised C partition-select; for a match-length clip (60–90 min ⇒ n ≈
   3.6M–5.4M envelope samples) that is on the order of several **billion**
   element-visits for the median pass alone, doubled again for MAD. **Accelerate
   has no rolling-median primitive** (vDSP is convolution/FFT/vector-arithmetic,
   not order statistics) — porting this step is not a translation, it needs a
   genuine rewrite as a streaming order-statistic (e.g. a two-heap or histogram-
   bucket rolling median), which is an O(n·log win) algorithm, roughly a
   thousand-fold reduction in element-visits at this window size. This is a real,
   previously-unflagged cost of shipping this module on-device, distinct from and
   in addition to the SOS-filter port. Confidence in the complexity claim: high
   (readable directly from the code). Confidence in the wall-clock magnitude on an
   A13: not measured, no benchmark run.

**If the audio track exists at all** (still open, see Deliverable 1), the *signal*
itself — band-pass, envelope, thresholding — is cheap and CPU-only, never touches
the ANE, and is very likely the least expensive stage in the whole plan once item 3
is rewritten. That conditional is load-bearing: it is cheap contingent on the
corpus actually carrying audio, which is the one thing this session could not
verify.
