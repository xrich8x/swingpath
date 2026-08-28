# Audio impact detection — a feasibility SCREEN across the corpus, indoor shell
# reported separately (2026-08-28)

> Evidence for the `audio-impact-feasibility-screen` row in
> [docs/STATE.md](../STATE.md). Scoped from
> [mobile-viability-audit.md](mobile-viability-audit.md), which lists `audio.py`
> among the modules blocked on-device by a bundled desktop ffmpeg.

**THIS IS A FEASIBILITY SCREEN, NOT AN ACCURACY MEASUREMENT.**

**Measured against: nothing.** Every detection number below is a property of
`audio.detect_impacts`'s own output on the clip's own soundtrack — an event
count, a rate, a ratio of the envelope to its own local floor. **No recall and
no precision figure is produced here, and none may be derived from these files.**
P0-7's real bar (impact recall at a bounded false rate) cannot be measured today:
the only per-stroke reference in this repo is `tools/audio_hits.py` scoring
against SwingVision's burned-in HUD panel, and rule 11 bars that. Rule 11 permits
the HUD as an *agreement* figure for **speed only**. Two rally-segmentation
figures were already withdrawn for exactly this premise (see STATE's *Withdrawn
figures* table) — this screen does not re-open that door.

The screen answers one question that needs no labels: **does the signal survive
on indoor shell**, the venue where court detection is 0 of 5?

---

## What the corpus actually has (and a stale claim, corrected)

`backend/tests/test_audio.py:5` and `docs/archive/sessions/SESSION_E_ball_push.md`
both state that **every** clip in `data/` was pulled video-only with no audio
stream. That was true when written and is **now stale** — it predates the Manila
venue recordings, which are the founder's own footage re-encoded by
`tools/split_by_serve.py` with `-c:a aac`. Census (`data/output/audio_census.json`):

| Surface | Clips | With an audio stream |
|---|---|---|
| **Shell (indoor)** | 64 | **62** |
| Hardcourt | 39 | 21 |
| Clay | 9 | 5 |
| Grass | 4 | 0 |
| **Total** | 116 | **88** |

The coverage lands on the hardest venue for vision. 58 of the 62 Shell clips with
audio are founder-recorded (`flexi_*`, `mpc_*`, `hillsborough_*`).

**All 88 were decoded successfully and none is silence.** RMS ranges −40.2 to
−11.2 dBFS; no clip is below −60 dBFS; `frac_exact_zero` is negligible
throughout (`data/output/audio_loudness.json`). A stream that exists but carries
digital silence would have made every ratio below a ratio of noise to noise.

---

## Result 1 — the detector never declares itself useless. Not once, anywhere.

`detect_impacts` has a self-protection bail-out (`audio.py:157`): if a clip
yields more than `max_events_per_s = 2.5` events per second it returns `[]`
rather than spraying false hits downstream. The feared indoor failure mode was
that echo trips it.

**Bail-outs: 0 of 88 decoded clips. 0 of 62 Shell clips.** 309.3 minutes of audio.

That is the screen's headline. The correlated audio/vision failure on echo-heavy
indoor courts **is not confirmed** — the cheap catastrophic mode did not occur.

## Result 2 — but yield and contrast on indoor shell are lower, and split by venue

Per-clip medians. `ev/s` is raw events per second; `contrast` is the median over
that clip's events of envelope-peak ÷ rolling-median floor; `gap` is the median
inter-event interval. Shell is **never pooled** with the other surfaces.

| Group | Clips | Audio min | Bail-outs | ev/s median | ev/s range | contrast median | gap median |
|---|---|---|---|---|---|---|---|
| **Shell / flexi_franz** (founder) | 12 | 1.5 | 0 | 0.33 | 0.00–0.77 | 5.41 | 1.393 |
| **Shell / flexi_joy** (founder) | 12 | 1.3 | 0 | 0.33 | 0.00–0.76 | 4.55 | 0.860 |
| **Shell / hillsborough** (founder) | 11 | 1.6 | 0 | 1.13 | 0.32–1.66 | 8.75 | 0.659 |
| **Shell / mpc_mixed** (founder) | 11 | 1.8 | 0 | 1.00 | 0.67–1.50 | 7.31 | 0.623 |
| **Shell / mpc_tuesday** (founder) | 12 | 1.3 | 0 | 0.33 | 0.00–0.85 | 4.69 | 0.897 |
| **Shell / other** (YouTube) | 4 | 29.3 | 0 | 0.42 | 0.21–0.76 | 5.45 | 0.662 |
| **Shell — all** | 62 | 36.7 | 0 | 0.49 | 0.00–1.66 | 5.88 | — |
| Clay | 5 | 61.4 | 0 | 1.58 | 1.22–1.64 | 8.26 | 0.479 |
| Hardcourt | 21 | 211.2 | 0 | 1.45 | 0.30–1.89 | 10.15 | 0.512 |

Four Shell clips fire **zero** events over a 6 s window: `flexi_franz_p05`,
`flexi_joy_p07`, `mpc_tuesday_p02`, `mpc_tuesday_p04`.

**The split inside Shell is not surface, it is the recording.** Levels
(`data/output/audio_loudness.json`) separate the same five founder venues into
two regimes:

| Group | RMS median (dBFS) | peak median (dBFS) | crest median (dB) |
|---|---|---|---|
| Shell / hillsborough | −13.9 | **0.0 (clipping)** | 13.9 |
| Shell / mpc_mixed | −17.5 | −0.0 (clipping) | 17.5 |
| Shell / flexi_franz | −30.8 | −5.8 | 25.0 |
| Shell / flexi_joy | −28.1 | −5.8 | 21.2 |
| Shell / mpc_tuesday | −30.6 | −8.7 | 20.8 |
| Clay | −34.9 | −2.3 | 31.2 |
| Hardcourt | −29.3 | −0.9 | 28.5 |

Crest factor is the quantity that matters to a transient detector: peak over RMS.
Outdoor footage sits at 28–31 dB. The quiet indoor venues sit at 21–25 dB — the
room's reverb tail raises the RMS floor without raising the peaks. The loud
indoor venues sit at 14–18 dB **and clip at full scale**, which flattens the very
transient the detector is looking for. The higher event rate at hillsborough and
mpc_mixed is therefore not obviously "better impacts"; it is at least partly a
hotter recorder.

## Result 3 — the binding threshold is the ABSOLUTE one, and it bites 2–3× harder indoors

`detect_impacts` requires **both** a local test (rolling median + `k_mad`·MAD)
and an absolute test (`min_contrast` × the **whole clip's** median envelope).
Dropping one test at a time says which is doing the suppressing. Totals over each
group, same run, same envelope:

| Group | Clips | Shipped (both) | Local test only | Absolute test only | % the absolute test discards |
|---|---|---|---|---|---|
| Shell / mpc_tuesday | 12 | 25 | 72 | 26 | **65.3%** |
| Shell / flexi_joy | 12 | 26 | 66 | 28 | **60.6%** |
| Shell / flexi_franz | 12 | 32 | 77 | 40 | **58.4%** |
| Shell / other (YouTube) | 4 | 970 | 2309 | 1073 | 58.0% |
| Shell / mpc_mixed | 11 | 111 | 163 | 135 | 31.9% |
| Shell / hillsborough | 11 | 96 | 136 | 135 | 29.4% |
| Clay (gold_clay, yt_tnxkujogch4) | 2 | 333 | 443 | 370 | 24.8% |
| Hardcourt (gold_am, am_hard_utr) | 2 | 1124 | 1353 | 1201 | 16.9% |

The last column is `1 − shipped / local-test-only`: the share of the adaptive local
test's candidates that the absolute test then throws away.

`min_contrast = 4.0` is a **globally normalised constant applied to a
level-dependent quantity**. In a reverberant room the clip's median envelope is
raised by the tail of every previous impact, so `4 × median` is a higher absolute
bar than the same constant sets outdoors — and it discards **58–65%** of what the
adaptive local test accepts on the quiet indoor venues, against **17–25%**
outdoors. (The two hot, clipping indoor venues sit in between, at 29–32%, which
is consistent with a limiter having already compressed their dynamic range.)
This is the same defect
class as the unscaled 720p pixel constants: a threshold tuned in one regime,
silently deleting real events in another.

**What this does NOT establish.** Whether those discarded candidates are real
impacts. That needs a compliant per-stroke reference and this screen has none.
Nothing here justifies changing `min_contrast`; it identifies the constant as
the first thing to test once labels exist.

---

## On-device: three line items for the iOS port

### 1. `extract_audio` shells out to a bundled desktop ffmpeg → AVFoundation

`audio.py:51-61` calls `imageio_ffmpeg.get_ffmpeg_exe()` under
`subprocess.run`, writes a temp WAV and reads it back with the `wave` module. On
iOS there is no shellable binary. The replacement is `AVAssetReader` /
`AVAudioFile` with an `AVAudioConverter` to mono float32 at 16 kHz — a decode,
not a translation. Note the module already returns `None` rather than raising
when extraction fails, so the degrade-to-visual-only path is in place.

### 2. `sosfiltfilt` → a vDSP biquad cascade, and the padding is the hard part

Pinned facts a parity harness must assert (`data/output/audio_ondevice_probe.json`):

- `butter(4, [1500/8000, 7000/8000], btype="band", output="sos")` gives **4
  second-order sections**; the exact float64 coefficients are stamped in the
  artifact.
- `sosfiltfilt` is a **zero-phase double pass** (forward, then reverse).
- scipy's default `padtype` is **`'odd'`** (odd-symmetric edge extension) and its
  default `padlen` here resolves to **27** samples. Confirmed empirically:
  `sosfiltfilt(sos, x)` and `sosfiltfilt(sos, x, padlen=27, padtype="odd")` are
  **bit-identical**.
- Per-section initial state is `sosfilt_zi(sos) * x[0]`; those values are stamped
  too.

**Cost of getting the padding wrong**, measured on a seeded random signal, as a
fraction of the signal's own peak: switching to `padtype='constant'` (or to no
padding at all) moves the output by **4.83% in the first and last 27 samples**
and by **0.11% in the interior**. A naive vDSP cascade that just filters forward
and backward gets the interior nearly right and the edges wrong — and the edges
are where a rally starts. This needs the same parity-harness discipline as the JS
line-call mirror (`tests/test_js_mirror_parity.py`), not an assumption.

### 3. CONFIRMED — the rolling floor is O(n·win), and it is 32× the filter

The researcher's read of the code was right. `detect_impacts` builds its floor
with `sliding_window_view` + `np.median`, twice (median, then MAD). Measured on
`data/incoming/Clay/CYqapSq5llo.mp4` (28.2 min of audio, 1,692,013 envelope
samples at 1 kHz, `win = 1000`), AMD Zen 4 desktop, numpy 2.5.0:

| Stage | Time |
|---|---|
| `impact_envelope` (butter + sosfiltfilt + smooth + decimate) | **0.82 s** |
| rolling median + MAD floor | **26.16 s** |

**32× the entire filtering stage**, for 3.38 **billion** element visits.

Scaling, same machine, same data — this is what confirms the complexity rather
than asserting it:

| n (win = 1000) | µs per envelope sample | | win (n = 200k) | µs per envelope sample |
|---|---|---|---|---|
| 50,000 | 13.73 | | 125 | 2.31 |
| 100,000 | 14.07 | | 250 | 4.09 |
| 200,000 | 14.58 | | 500 | 7.77 |
| 400,000 | 15.27 | | 1000 | 15.06 |
| 800,000 | 15.28 | | 2000 | 27.74 |

Flat in `n`, **doubling with `win`**. O(n·win), confirmed.

**A second problem found while measuring it:** the shipped expression
materialises an `n × win` float64 sort buffer. For this clip that is a
**13.5 GB** peak allocation. It has not bitten on desktop only because nothing
has run `detect_impacts` on a full match. `tools/audio_impact_screen.py` chunks
it, which `test_audio_streaming_floor.py::test_chunked_floor_equals_unchunked`
pins as numerically a no-op.

**The rewrite is a known algorithm, and it is now prototyped and pinned.**
Accelerate/vDSP has no rolling-median primitive, so this is not a translation.
`tools/audio_ondevice_probe.streaming_med_mad` maintains a sorted window and
takes the median as an order statistic; the **MAD** — the part that looks like it
needs a second sort — is the order statistic of the *merge of two already-sorted
deviation sequences* (below-median descending, above-median ascending), which is
O(log win) by partition search with no materialisation.

Proven exact against `np.median`, including the even-window
mean-of-two-middles convention, ties, and long constant runs
(`backend/tests/test_audio_streaming_floor.py`, 10 tests). On the real envelope,
`median_exact_match: true`, `mad_max_abs_diff: 0.0`.

The scaling is the point (n_out = 2000, same clip):

| win | numpy sliding-window (µs/output) | streaming prototype, pure Python (µs/output) |
|---|---|---|
| 125 | 3.48 | 6.45 |
| 250 | 4.49 | 12.59 |
| 500 | 7.07 | 10.65 |
| 1000 | 13.41 | 14.67 |
| 2000 | 24.75 | **17.58** |

numpy doubles per doubling of `win`; the streaming form does not. At the shipped
`win = 1000` an **interpreted Python** prototype already matches vectorised C,
and beats it at 2000. A compiled Swift order-statistic structure is not close.

Caveat, stated because it would otherwise be an overclaim: the prototype's window
maintenance uses `bisect.insort` on a Python list, which is O(win) memmove — that
is the residual growth visible above. A real port uses an order-statistic tree or
a bucketed histogram and is O(log win) throughout.

---

## Artifacts

| File | What it is |
|---|---|
| `data/output/audio_census.json` | which clips carry an audio stream |
| `data/output/audio_impact_screen.json` | the 88-clip screen, with provenance |
| `data/output/audio_loudness.json` | RMS / peak / crest, decode-only pass |
| `data/output/audio_impact_screen_shell_binding.json` | Shell re-run with the binding-test diagnostic |
| `data/output/audio_impact_screen_ref_binding.json` | four outdoor reference clips, same diagnostic |
| `data/output/audio_ondevice_probe.json` | complexity, filter parity, streaming-MAD equivalence |
| `tools/audio_impact_screen.py` | the screen |
| `tools/audio_impact_screen_report.py` | the by-venue summary; Shell is never pooled |
| `tools/audio_ondevice_probe.py` | the three on-device line items |
| `backend/tests/test_audio_streaming_floor.py` | parity harness for the streaming floor |

**Provenance.** Every artifact stamps the **resolved** detector configuration
read back out of `detect_impacts`'s own signature (`inspect.signature`), never a
static preset table, plus `audio.py`'s sha256 prefix, the commit, numpy version
and platform. Shipped defaults were not touched. On 10 randomly sampled clips
(seed 0) the screen's re-implementation of the detector's thresholding reproduces
`detect_impacts` exactly; 4/4 on the Shell re-run.

## What this settles, and what it does not

**Settles:** audio is present on 88 clips including 62 of 64 indoor shell; none is
silent; the detector self-declares useless on none of them. Point segmentation on
shell does **not** have to fall back to vision-only on the grounds of a
correlated audio failure — that specific fear is refuted.

**Does not settle:** whether the events are hits. Yield on the quiet indoor
venues is a third of outdoor, four clips fire nothing, and the absolute contrast
test discards 2.4–2.9× more there than outdoors. Any of that could be a real
signal deficit or a mistuned constant. Distinguishing them needs a per-stroke
reference that rule 11 permits — human-clicked impact times, or boundaries
derived from bounces and physics. Not the HUD.
