# Does the RTS BACKWARD pass separate real from ghost among the innovation gate's rejects?

> Measurement run 2026-09-03 by backend-dev against the pre-registration the lead wrote
> BEFORE anything ran (`.claude/journals/lead.md`, "PRE-REGISTRATION — smoother innovation
> gate: is a BACKWARD-pass re-admit separating?"). The bar was not restated, retuned or
> softened after seeing numbers.
>
> **This run authorised no fix.** `backend/swingvision/ball.py` was NOT modified, nothing was
> shipped, and no coverage / `seen_frac` number is claimed anywhere below.

**DELIVERABLE:** one PASS/FAIL verdict on whether the distance from a gate-rejected detection
to the FINAL RTS-smoothed trajectory separates real detections from ghosts — with per-clip
distributions, the best-threshold exchange rate, and a mandatory shuffled-label null control.

---

## Verdict

# FAIL — and it closes the branch.

The signal does not separate on **any** of the three clips, and pooled it is slightly
**anti**-separating. The pre-registered bar needed ≥ 3:1 real-to-ghost at the best single
distance threshold on ≥ 2 of 3 clips. Measured:

| clip | rejects scored | real | ghost | best cut at **≥ 3:1** | best ratio at ANY cut (≥5 real) |
|---|---|---|---|---|---|
| `am_hard_utr` | 18 | 9 | 9 | **none exists** (0 real admissible) | **1.14 : 1** (8 real / 7 ghost @ 257 px) |
| `yt_match40` | 13 | 6 | 7 | **1 real / 0 ghost @ 37.6 px** | **2.00 : 1** (6 real / 3 ghost @ 88.6 px) |
| `yt_rally2` | 18 | 6 | 12 | **none exists** (0 real admissible) | **0.56 : 1** (5 real / 9 ghost @ 187 px) |
| **pooled** | **49** | **21** | **28** | **none exists** | **0.93 : 1** (13 real / 14 ghost @ 89 px) |

0 of 3 clips clear the bar (2 were required). The single cut that reaches 3:1 anywhere is on
`yt_match40` and admits **one** real detection — a 1-frame recovery is not a mechanism.
The null control (below) confirms the observed separation is **at or below chance**.

**A failed bar stays failed. This is the third measured negative in the smoother-gate family
(after `bounce_reset` and `bounce_hypothesis` v1/v2), so rule 3 now bars a fourth attempt in
this family.** The specific idea that is now closed: *using information from the smoother's
backward pass to re-admit detections the forward innovation gate rejected.*

**What is NOT closed by this:** the `-11.0 / -8.1` pt `seen_frac` cost of `smooth_forecast`
itself. That row stands, unchanged. This run says only that the RTS trajectory is not the
discriminator that would fix it — see §5 for why, which is the more useful half of the result.

---

## 1. What the innovation gate is, and whether the backward pass already re-admits

Established by reading the code, before any measurement.

**The gate** (`backend/swingvision/ball.py:863`):

```python
y = np.array([z[0], z[1]]) - Hm @ x          # innovation, 2-vector, IMAGE PIXELS
S = Hm @ P @ Hm.T + R                        # innovation covariance
if float(y @ np.linalg.solve(S, y)) <= gate_chi2:      # <- the statistic
```

- **Statistic:** the squared Mahalanobis norm of the innovation, `yᵀ S⁻¹ y`, where `x` is the
  *propagated prior* (`x = F @ x` one line earlier, at `:857`) and `R = I·meas_var·res_scale²`.
- **Threshold:** `gate_chi2 = 13.8` (default, `:633`) — the χ²₂ 99.9% point.
- **Where a rejection happens:** the `else` at `:868`. The detection is simply not fed to the
  update; `rej += 1`; `accept` stays `False`; `used[i] = accept` at `:963`.

**Does the RTS / backward pass already re-admit or re-score rejections? NO.** The smoother
loop (`:972–981`) recurses only over `xf / xs / Pf / Pp` and `seg_id`. It never re-reads
`positions[i]`, never recomputes an innovation, and never writes `used[]`. Emission
(`:1010–1024`) keys entirely off `used[i]`. So a detection rejected by the forward gate is
gone before the backward pass begins, and the backward pass has no path to bring it back.

**The premise is alive**, and the measurement in §3 is the right question.

**One code fact the brief did not have, and it matters.** A rejection that trips
`rej >= reset_after` is **re-seeded on that same frame** (`:968–970`,
`if z is not None and accept is False and rej == 0: ... used[i] = True`). So the shipped code
*already* re-admits a subset of gate rejections, via the segment-reset path. Measured on the
adjudicated population: **1 of 19** (`am_hard_utr`), **3 of 16** (`yt_match40`), **8 of 26**
(`yt_rally2`). Those are excluded from the population below — a re-admit mechanism cannot
claim credit for detections the shipped code keeps. The population is the rejections that
stay **lost**.

## 2. Are the rejected detections observable?

Not as shipped — nothing records them. Instrumentation was added, and it is **observability
only**: `smooth_forecast` was left untouched on disk and instrumented by **source transform**
in a scratchpad script (`inspect.getsource` → two textual insertions → `exec`):

1. the gate line split so `_d2` is recorded per frame before the comparison;
2. `xs`, `used`, `seg_id` exported just before the final `return`.

**Proof it changed nothing** (discipline: a refactor must prove it changed nothing): every run
calls the instrumented copy and the shipped `B.smooth_forecast` on the identical input and
compares all three returned lists. `identical: true` on all three clips, asserted in-run.

## 3. The measurement

**Population.** Detections rejected by the forward innovation gate (`chi2 > 13.8`), minus
those the reset path re-seeds, restricted to frames a human adjudicated. Frames with no human
label are **excluded** — they are unadjudicated, not ghosts.

**Labels — human gold clicks only** (`data/gold/<clip>.labels.json` via `tools/_goldset.py`,
read-only, TEST-only). `real` = the rejected lock is within **10.0 px** of the human click on
that frame (the project's own recall criterion, `tools/eval_model_filters.py:200`);
`ghost` = anything else on an adjudicated frame, which includes both a lock on a
human-marked no-ball frame and a mislocalised lock on a ball frame. Nothing here is labelled
against the smoother's output or any model's output.

**Gold-leak guards.** The three guards (`assert_no_gold_leak`, `assert_no_swingvision_leak`,
`assert_no_court_gold_leak`) live in the *training* scripts (`backend/train_ballnet.py:125,163`,
`backend/train_courtnet.py:67`) and guard training data against gold. This path trains
nothing, fits nothing and writes no label file; gold is read one-way, as TEST. No guard is
bypassed.

**Signal.** Distance in image pixels from the rejected detection to the **final RTS-smoothed
trajectory** at that frame, `xs[i] → (x, y)`. This is the backward-pass quantity: `xf[i]` at a
rejected frame is the un-updated prior, and the RTS recursion corrects it using *future*
frames — information the forward gate did not have at rejection time.

### Distributions (px to the RTS-smoothed track), min / p25 / median / p75 / max

| clip | REAL rejects | GHOST rejects |
|---|---|---|
| `am_hard_utr` (n=9 / 9) | 73.6 / 89.3 / **160.3** / 237.3 / 337.8 | 37.9 / 80.2 / **97.9** / 139.0 / 641.5 |
| `yt_match40` (n=6 / 7) | 37.6 / 50.7 / **69.0** / 81.2 / 88.6 | 49.0 / 57.6 / **111.4** / 162.1 / 1626.2 |
| `yt_rally2` (n=6 / 12) | 17.6 / 37.0 / **42.2** / 55.5 / 231.9 | 11.9 / 18.0 / **44.2** / 120.7 / 412.9 |

The two distributions sit on top of each other on every clip. On `am_hard_utr` the signal
points the **wrong way**: real rejects are a median 160 px from the smoothed track while
ghosts are 98 px — a threshold there admits ghosts *preferentially*. `yt_match40` is the only
clip where the medians order favourably, and even there the ranges overlap almost completely
(real 37.6–88.6, ghost 49.0–1626).

### Exchange rate at the best single threshold

Defined as the pre-registration defines it — a single distance cut, count real and ghost
admitted below it. `best cut at ≥ 3:1` = the cut admitting the **most real** detections while
holding ratio ≥ 3:1. Results are in the verdict table above. Restated plainly: **on two of
three clips no cut of any value reaches 3:1 while admitting even one real detection**, because
the nearest reject to the smoothed track is a **ghost** on both.

## 4. Null control (shuffled labels, seeded, 1000 draws) — MANDATORY, run

Same distances, labels permuted, `random.Random(20260903)`, 1000 draws per clip. Statistic =
the number of real detections re-admittable at ≥ 3:1 (the quantity the bar is about).

| clip | observed statistic | draws ≥ observed | p |
|---|---|---|---|
| `am_hard_utr` | 0 | 1000 / 1000 | **1.000** |
| `yt_match40` | 1 | 526 / 1000 | **0.526** |
| `yt_rally2` | 0 | 1000 / 1000 | **1.000** |
| pooled (49) | 0 | 1000 / 1000 | **1.000** |

Every clip is far above the 5% bar. The one non-degenerate case, `yt_match40`, is reached or
beaten by **more than half of random label permutations** — its "1 real at 3:1" is exactly
what shuffled labels produce by chance. There is no evidence of separation to interpret.

## 5. Inspecting the rejects (rule 10) — where the two distributions overlap, and why

The signal does not separate, so per rule 10 the finding is *what the overlapping cases have
in common*. The twelve rejects closest to the smoothed track, pooled:

| clip | frame | d to RTS track | chi2 | label | lock error vs click |
|---|---|---|---|---|---|
| `yt_rally2` | 774 | **11.9** | 16.1 | ghost | (human: no ball) |
| `yt_rally2` | 1240 | **17.4** | 18.3 | ghost | 30.3 px |
| `yt_rally2` | 1112 | 17.6 | 19.9 | REAL | 3.9 px |
| `yt_rally2` | 762 | 18.0 | 25.5 | ghost | (human: no ball) |
| `yt_rally2` | 414 | 34.3 | 14.6 | ghost | 24.0 px |
| `yt_rally2` | 942 | 37.0 | 16.8 | REAL | 2.5 px |
| `yt_rally2` | 1598 | 37.3 | 17.3 | ghost | (human: no ball) |
| `yt_match40` | 8378 | 37.6 | 20.8 | REAL | 3.4 px |
| `am_hard_utr` | 23524 | 37.9 | 13.8 | ghost | 49.8 px |
| `yt_rally2` | 2052 | 42.2 | 26.9 | REAL | 4.0 px |
| `yt_rally2` | 522 | 44.2 | 24.2 | ghost | (human: no ball) |
| `yt_match40` | 7245 | 49.0 | 35.1 | ghost | 386.2 px |

**The closest reject to the smoothed trajectory, on the pooled set, is a ghost on a frame a
human marked as having no ball at all.** Three of the four nearest are ghosts.

What the overlapping cases have in common, and the mechanism this measurement establishes:

- **The ghosts that sit nearest the RTS track are locks that continue the model's own
  motion.** They are either fires on no-ball frames lying along the extrapolated path, or
  locks 24–50 px off a click — near-misses onto a nearby confuser that the constant-
  acceleration path happens to run through. Being close to the smoothed track is close to a
  *definition* of the ghosts this stage is worst at.
- **The real rejects are far from the RTS track for the same reason the gate rejected them.**
  A real detection fails a χ²₂ 99.9% gate essentially only when the model is stale — after a
  hit or a bounce, where the ball's direction has changed and the filter's prior has not. But
  `xs[i]` at that frame is smoothed **within the same segment**, off the same stale motion
  model (the RTS recursion is blocked at segment boundaries, `:977`). So the backward pass
  does not relocate the trajectory toward the real ball; it refines the wrong path more
  smoothly. The real detections are 17.6–337.8 px away precisely because they mark where the
  model went wrong.
- **This is a confound, not a tuning problem.** The signal is measuring "does this detection
  agree with the model?" — which is the *same question the forward gate already asked* and
  the same question it got wrong. It is a second look at the same evidence, so it cannot
  separate the cases the first look failed on. That is why no threshold works and why
  tightening or loosening one would not help.
- **The real detections a re-admit would still miss = all of them** on `am_hard_utr` and
  `yt_rally2`, and 5 of 6 on `yt_match40`, at any cut satisfying 3:1.

## 6. Provenance — which cache and which gold file every number came from

Every number above comes from exactly these files. **No perception was re-run from video**;
frame size and fps were read from the video container only (`cv2.VideoCapture` properties, no
decode).

| clip | ball detections (the ARM) | human labels | frames × step | resolution | `res_scale` | pre-smoother locks |
|---|---|---|---|---|---|---|
| `am_hard_utr` | `data/output/detector_ab/am_hard_utr.tracknet.perception.json` | `data/gold/am_hard_utr.labels.json` (175 ball, 53 no-ball) | 14,499 × 2 | 1920×1080 | 1.5 | 8,330 |
| `yt_match40` | `data/output/detector_ab/yt_match40.tracknet.perception.json` | `data/gold/yt_match40.labels.json` (184 ball, 24 no-ball) | 10,268 × 1 | 1280×720 | 1.0 | 5,974 |
| `yt_rally2` | `data/output/detector_ab/yt_rally2.tracknet.perception.json` | `data/gold/yt_rally2.labels.json` (258 ball, 26 no-ball) | 1,108 × 2 | 1280×720 | 1.0 | 788 |

All three arms are **TrackNet** — v1's shipped detector — from the `detector_ab/` family, the
only cache family that is a one-variable detector pair. Model, parameters and commit are the
ones stamped in those caches; `gate_chi2 = 13.8`, `meas_var = 25`, `sigma_jerk = 1.0`,
`reset_after = 3`, `max_gap_s = 0.4` (shipped defaults, resolved at the call, not read from a
preset table).

**No homography is touched anywhere in this measurement.** The pre-smoother chain was run as
`remove_outliers → rectify_track → suppress_false_locks`, deliberately **omitting**
`gate_ball_to_court`, so that `yt_match40`'s known-broken calibration (T23) cannot reach any
number here. The signal itself is a pixel distance in image space. Effect of the omission,
checked rather than assumed: STATE records the court gate removing locks on 4 of 7 calibrated
gold clips — `gold_sAjkpeRq4P4`, `gold_uR5q2cSM6AY`, `gold_L73ep7JHiJ4` and `yt_match40 (−5)`.
**`am_hard_utr` and `yt_rally2` are not among them, so on 2 of 3 clips the omission is an
exact no-op**, and on `yt_match40` it can touch at most 5 locks clip-wide. The bias direction
is conservative: the gate retains 100% of human-labelled ball frames on all 7 clips, so it can
only ever have removed **ghosts** from this population — including them makes separation
*harder*, never easier.

## 7. Power — stated, not buried

The adjudicated populations are small: **18 / 13 / 18** lost rejections per clip, 49 pooled.
That is a ceiling, not a sampling choice — a rejection is only scoreable on a frame a human
clicked, and the gold sets carry 175–258 ball frames per clip against 1,108–14,499 frames.
Trap T09 applies to any *positive* read on numbers this thin.

It does not rescue this result, for two reasons. First, the pooled set (49) fails too, at
0.93:1. Second, the failure is not "too few to tell" — the nearest rejects to the smoothed
track are ghosts on two of three clips, so the ordering is wrong at the top of the ranking
where a threshold has to work, and §5 gives the mechanism for why it is wrong. A larger
sample of the same confound measures the same confound.

## NOT ESTABLISHED THIS RUN

- **Whether any *other* signal separates these rejects.** Only the pre-registered one
  (distance to the RTS-smoothed trajectory) was measured. §5 argues that any statistic derived
  from the same motion model shares the confound, but a signal from *outside* the model
  (appearance, a detector confidence, agreement across the two detectors) is untested and is
  not covered by this negative.
- **A fix for the `-11.0 / -8.1` pt coverage cost.** None was proposed, built or authorised.
  The row stays open and stays the best-measured target.
- **The behaviour of the reset-path re-seed** (§1) beyond counting it. It already re-admits
  1 / 3 / 8 of the adjudicated rejections per clip; whether those re-admissions are real or
  ghost was not scored, because the population of interest was the rejections that stay lost.
- **Anything under BallNet.** All three arms are TrackNet.
