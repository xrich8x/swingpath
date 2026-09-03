# Does `seen_frac >= 0.5` predict speed error?

> DELIVERABLE for the pre-registration *"does `seen_frac >= 0.5` actually predict speed
> error?"* written at the end of `.claude/journals/lead.md` on 2026-09-03, BEFORE this run.
> Measured by backend-dev, 2026-09-03, at commit `79c381d`.
>
> **Nothing here changes the constant, and no replacement value is named.** The
> pre-registration and the brief both forbid choosing a new bar from this data; §7 gives
> the pre-registration for choosing one instead.

## VERDICT: **INDETERMINATE** — and **G is refuted in every population tested**

- **G (the gate predicts error, >= 1.5x on >= 2 of 3 clips) FAILS.** No clip reaches 1.5x
  in any population. The largest single-clip ratio anywhere is **1.48**, and it occurs on
  one clip in one secondary arm.
- **N (<= 1.1x on >= 2 of 3 clips) is met on the population exactly as my harness drew it**
  (ratios 1.35 / 0.86 / 0.76 — two clips at or under 1.1), **but is NOT met once the
  population is restricted to what the shipped pipeline actually calls a shot**
  (1.11 / 1.21 / 0.97 — one clip at or under 1.1).
- The two readings disagree, so by the pre-registration's own wording — *"anything between,
  including a split across clips"* — the honest verdict is **I**, and **"no threshold is
  moved on an indeterminate result."**

I am reporting the **weaker** of the two available readings on purpose. N was the more
interesting outcome and the one my harness produced first; the restricted population is
the more faithful one, and it does not support N. Picking the reading I liked would be the
same error the pre-registration was written to prevent.

**What is established regardless of which reading you take:** at its own threshold the gate
has, at most, weak discriminative power. Adjacent-band Mann-Whitney is non-significant on
every clip in every arm (11 of 12 tests p > 0.14; the twelfth p = 0.033 uncorrected, 1 of
12), and as a classifier of "accurate" the gate's accept-precision is **0.500 against a
0.472 base rate** — 2.8 points above answering "confident" for every shot. That is the same
shape of finding as the close-call majority-class floor already in `CLAUDE.md`.

## 1. The bar, restated (not re-derived, not retuned)

`backend/swingvision/pipeline.py:1873`:

```python
speed_confident = (seen_frac >= 0.5 and real_landing
                   and not p["is_serve"] and speed <= PLAUSIBLE_KMH)
```

- **G:** median |speed error| for `seen_frac` in **[0.35, 0.50)** is **>= 1.5x** that in
  **[0.50, 0.65)**, on **>= 2 of 3** clips.
- **N:** ratio **<= 1.1x** on **>= 2 of 3** clips.
- **I:** anything between, including a split across clips.
- **Sample floor (mandatory):** **n >= 15 in EACH band** per clip; fewer than 2 clips
  clearing it => UNDERPOWERED.

**The floor is comfortably cleared: all three clips have n >= 78 in each band in every
arm.** This is not an underpowered result.

## 2. Where the two paired numbers come from

**A per-shot absolute speed error IS obtainable compliantly — but only on synthetic
flights.** Real clips have no absolute speed reference at all: the HUD is barred as an
accuracy reference (rule 11, and it is agreement with another estimator), and human clicks
label ball *position*, not speed. So the paired dataset has to be manufactured, and
`tools/synth_truth.py` is the tool that manufactures it.

**`seen_frac`** — computed exactly as the pipeline computes it, not re-derived:

- `pipeline.py:1460` `ball_seen[i] = ball_px[i] is not None and not ball_coasted[i]`
  — the smoother emitted a position there AND it was a measurement, not a forecast.
- `pipeline.py:1716` `real_fraction(a, b)` = mean of `ball_seen` over `[a, b]`.
- `pipeline.py:1862` `seen_frac = real_fraction(h, land)` — hit frame to landing frame.

In the harness a flight spans launch (frame 0) to the bounce (`truth_of`'s `i_bounce`), so
`[h, land]` is the whole flight and `seen_frac = mean(ball_seen)` over it.

**Absolute speed error** — the shipped estimator against exact simulated truth:

- Truth: `synth_truth.simulate()` (drag + gravity + Magnus, `simulator_torch`) projected
  through the clip's real calibrated camera; `synth_truth.truth_of()` returns
  `avg_ground_kmh`.
- Estimate: the shipped chain, mirrored stage-for-stage from `pipeline.analyze`:
  `ball.smooth_forecast` (`res_scale = h/720`) then `calibration.image_to_court` + the
  +/-4 m runoff-box test (`pipeline.py:1464-1477`) then `ball.cap_court_jumps(max_step_m =
  84/fps)` then `ball.smooth_and_fill(window=7, polyorder=2)` then
  `analytics.shot_speed_kmh`.
- Error: `abs(100 * (est - avg_ground_kmh) / avg_ground_kmh)`.

**Comparator fixed before any numbers existed** (journal, 2026-09-03): `avg_ground_kmh`,
which is synth_truth's error-budget component 3 — *"the only part that is our error"*.
Referencing `launch_kmh` instead would add the shared -21.7% drag bias to both bands and
compress the ratio toward 1, i.e. bias the test toward N. Launch-referenced and km/h errors
are reported as secondary in §4.

**ONE VARIABLE.** Per-flight `dropout ~ U(0.05, 0.80)`, drawn independently of the flight.
Everything else is fixed: `fps 30`, `horizon 2.0 s`, `pixel_noise = 2.0 * h/720` (the 720p
constant, scaled per the project rule), `seed 0` on all three clips so the three cameras
see the *same* launches. Realised `seen_frac` correlates with `dropout` at rho = -0.885 and
spans 0.10 to 1.00.

**The limitation this design has, stated up front.** Dropout here is random and independent
of the flight; in a real clip, dropout is *caused* (far court, motion blur, occlusion). So
this measures the causal question the gate assumes — *holding the shot fixed, does losing
frames make the speed worse?* — and it does **not** measure whether `seen_frac` is a proxy
for some other hard-shot property in real footage. A gate can be useless causally and still
correlate in the wild. That is a real gap and it is what §7's pre-registration is for.

## 3. Provenance

| item | value |
| --- | --- |
| commit | `79c381d` |
| perception cache used | **none** — this is synthetic; no detector was run, no `data/output/` cache read |
| truth generator | `tools/synth_truth.py` (`simulate`, `truth_of`), unmodified, imported not copied |
| shipped code exercised | `swingvision.ball.smooth_forecast` / `cap_court_jumps` / `smooth_and_fill`, `swingvision.calibration.image_to_court` + `homography_from_landmarks`, `swingvision.analytics.shot_speed_kmh` |
| harness | `scratchpad/seen_frac_vs_error.py` + `analyse.py`, output `paired.json`. **Uncommitted** — writing it to `tools/` would be a code change, which this brief bars. See NOT ESTABLISHED. |
| seed | 0, every clip |
| flights requested / usable | 1200 per clip; 892 / 803 / 862 usable = **2557** |
| runtime env | `backend/.venv-train/Scripts/python.exe` |

**Clips = calibrations.** Each "clip" is that clip's audited camera geometry, and the
constraint I applied is the one the brief names:

| clip | pts file | fit residual | camera | resolution | hfov used |
| --- | --- | --- | --- | --- | --- |
| `yt_rally2` | `data/yt_rally2_pts.json` | 1.4 px | 3.31 m | 1280x720 | 93.7 deg |
| `am_hard_utr` | `data/am_hard_utr_pts.json` | 0.7 px | 1.74 m (LOW) | 1920x1080 | 86.1 deg |
| `yt_court` | `data/yt_court_pts.json` | 2.1 px | 2.42 m | 1280x720 (assumed) | 60.0 deg |

hfov per clip from `tools/height_curve.py::hfov_of` (`courtfit.cam_fit_quad`), never the
93.46 default — speed scales with it.

**EXCLUDED, and why:** `yt_match40` — T23, its four clicks sit off every court line, and
speed is a homography-dependent quantity here, so it is barred; **no `yt_match40` number
appears in this file.** `demo30` — `docs/STATE.md` records its speeds as never citable.

## 4. Per-clip, per-band n and median absolute error

**PRIMARY — the pre-registered test, population as my harness drew it (n = 2557).**

| clip | n [0.35,0.50) | med abs% | n [0.50,0.65) | med abs% | **ratio** | floor n>=15 | Mann-Whitney p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `yt_rally2` | 155 | 46.1 | 201 | 34.2 | **1.35** | yes | 0.495 |
| `am_hard_utr` | 132 | 64.0 | 171 | 74.8 | **0.86** | yes | 0.92 |
| `yt_court` | 143 | 57.8 | 197 | 76.5 | **0.76** | yes | 0.676 |
| pooled | 430 | 55.4 | 569 | 57.5 | 0.96 | — | 0.857 |

G: 0 of 3 clips >= 1.5x. N: 2 of 3 clips <= 1.1x. **Reads N.**

**Secondary metrics, same bands, same primary population** (ratio [0.35,0.50)/[0.50,0.65)):

| metric | yt_rally2 | am_hard_utr | yt_court |
| --- | --- | --- | --- |
| abs km/h error | 40.1 / 32.5 = **1.23** | 60.7 / 59.0 = **1.03** | 55.4 / 62.1 = **0.89** |
| abs % error vs `launch_kmh` | 45.8 / 38.1 = **1.20** | 60.4 / 72.5 = **0.83** | 59.9 / 71.4 = **0.84** |

Neither secondary metric reaches G on any clip.

**RESTRICTED ARMS.** The primary population contains flights the shipped pipeline would
never have emitted as a shot at all: `pipeline.py:1762` drops `speed < MIN_SPEED_KMH` (5)
and `speed > 250`, and the gate's own conjunction requires `speed <= PLAUSIBLE_KMH` (160).
Omitting those filters was an oversight in fidelity, not a design choice, so the restricted
arms are reported alongside — **the bar is unchanged in all of them.**

| arm | population | n | yt_rally2 | am_hard_utr | yt_court | reads |
| --- | --- | --- | --- | --- | --- | --- |
| A | `5 < est < 250` (shipped shot filter) | 1782 | 1.11 (126/163) | 1.22 (84/100) | 1.02 (98/120) | **I** |
| **B** | A plus `est <= 160` (the gate's own conjunct) | 1722 | 1.11 (125/163) | 1.21 (78/97) | 0.97 (97/118) | **I** |
| C | true apex `max_z <= 1.5 m` (ground shots) | 1230 | 1.17 (68/98) | 1.48 (66/94) | 1.09 (66/96) | **I** |

Arm B medians: 29.6/26.5, 30.7/25.4, 34.1/35.1. Arm B Mann-Whitney p = 0.274 / 0.256 /
0.521. Arm C Mann-Whitney p = 0.191 / **0.033** / 0.41 — that 0.033 is uncorrected and is
1 of 12 adjacent-band tests run across all arms; at 12 tests it is what chance produces.

**All arms clear the sample floor on all three clips. G fails in all four populations.**

## 5. Full distribution across all bands (descriptive context only)

**Does not decide the verdict.** Primary population, median abs % error:

| band | yt_rally2 n/med% | am_hard_utr n/med% | yt_court n/med% | pooled n/med% |
| --- | --- | --- | --- | --- |
| [0.05,0.20) | 10/83.6 | 7/100.0 | 9/100.0 | 26/100.0 |
| [0.20,0.35) | 97/75.8 | 65/100.0 | 85/93.5 | 247/88.9 |
| **[0.35,0.50)** | 155/46.1 | 132/64.0 | 143/57.8 | 430/55.4 |
| **[0.50,0.65)** | 201/34.2 | 171/74.8 | 197/76.5 | 569/57.5 |
| [0.65,0.80) | 212/31.9 | 203/77.2 | 205/56.9 | 620/53.9 |
| [0.80,0.95) | 175/25.7 | 181/56.9 | 182/47.2 | 538/44.8 |
| [0.95,1.01) | 42/15.5 | 44/35.8 | 41/28.3 | 127/24.6 |

Arm B (shipped shot definition), pooled: 72.5 (n=12) / 43.4 (131) / **31.3 (300)** /
**28.1 (378)** / 23.2 (401) / 25.4 (393) / 22.9 (109).

Whole-range Spearman rho(`seen_frac`, abs%): primary **-0.169** (p=3.9e-7) / **-0.030**
(p=0.39) / **-0.097** (p=0.0044), pooled -0.098; arm B pooled -0.093 (p=1.1e-4).

**Read this carefully, because it is the trap the brief warned about.** There *is* a real
monotone trend across the full range — a shot seen on 15% of its span is genuinely worse
than one seen on 100%. But the trend is carried by the **extremes**, and it is flat exactly
where the constant sits: pooled arm B goes 72.5 -> 43.4 -> 31.3 -> 28.1 -> 23.2, i.e. the
whole cliff is below 0.35 and the [0.35,0.50)/[0.50,0.65) step is 3.2 points out of a
~50-point range. On `am_hard_utr` and `yt_court` in the primary arm the curve is
**non-monotone across the threshold** — error *rises* from [0.35,0.50) to [0.50,0.65). A
whole-range correlation does not license the bar being at 0.5, and the pre-registration
deliberately measured locally so this could not be mistaken for support.

## 6. The rejects (rule 10)

"Accurate" is defined without reference to the outcome: **abs% <= the median of the
ACCEPTED population**, i.e. a shot the gate refused that is better than the typical shot it
accepted. Both populations shown.

**Primary population** (accept threshold `seen_frac >= 0.5`; accurate := abs% <= 46.9):

| set | n | % of its side | med `seen_frac` | med max_z | med span | med court-coverage | med abs% | med signed% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| refused-but-**accurate** | 268 | **38.1% of refused** | 0.39 | 1.18 m | 21 f | 0.71 | **18.8** | -8.3 |
| refused-and-inaccurate | 435 | 61.9% of refused | 0.36 | 2.27 m | 37 f | **0.04** | 100.0 | -100.0 |
| accepted-but-**inaccurate** | 927 | **50.0% of accepted** | 0.73 | 2.52 m | 37 f | **0.04** | 100.0 | -100.0 |
| accepted-and-accurate | 927 | 50.0% of accepted | 0.75 | 0.94 m | 16 f | 0.93 | 16.2 | -10.0 |

**Arm B, the shipped shot definition** (accurate := abs% <= 24.7):

| set | n | % of its side | med `seen_frac` | med max_z | med span | med court-coverage | med abs% | med signed% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| refused-but-**accurate** | 173 | **39.1% of refused** | 0.39 | 1.20 m | 23 f | 0.74 | **11.8** | -4.3 |
| refused-and-inaccurate | 270 | 60.9% of refused | 0.37 | 1.53 m | 26 f | 0.25 | 62.8 | -48.3 |
| accepted-but-**inaccurate** | 639 | **50.0% of accepted** | 0.74 | 1.22 m | 23 f | 0.70 | 55.9 | -40.7 |
| accepted-and-accurate | 640 | 50.0% of accepted | 0.75 | 0.93 m | 16 f | 0.95 | 11.5 | -7.6 |

**Neither reject set is small, and neither is explained by `seen_frac`.**

- **The gate refuses ~10% of all shots that are more accurate than the median shot it
  accepts** (268/2557 primary, 173/1722 arm B), and those refused-but-accurate shots have a
  median error of **11.8%** in arm B — less than half the accepted population's 24.7%.
- **It accepts an equal-sized set that is worse:** 639 shots (37% of all) at a median 55.9%
  error, and it accepts them at *higher* `seen_frac` (0.74) than the refused-but-accurate
  ones it threw away (0.39).
- **As a classifier of accuracy the gate is at chance.** Arm B confusion: accept&accurate
  640, accept&inaccurate 639, refuse&accurate 173, refuse&inaccurate 270.
  **Accept-precision 0.500 against a 0.472 base rate.** Same numbers on the primary
  population (0.500 vs 0.467).

**What DOES separate accurate from inaccurate.** Across both reject tables the one column
that moves is **court-coverage fraction** — the share of the span that survives the
+/-4 m runoff-box test and `cap_court_jumps` and therefore contributes a real court
position to the path integral (0.93-0.95 for accurate, 0.04-0.70 for inaccurate).
Spearman rho(court-coverage, abs%) = **-0.749** (p < 1e-300) versus **-0.098** for
`seen_frac`. Mechanically this is `max_z`: an airborne ball's z=0 projection lands outside
the runoff box, the court track empties, `smooth_and_fill` bridges it flat, and the path
integral collapses (median signed error -100%, i.e. `est` near 0). **The gate is measuring
whether the DETECTOR saw the ball; the error is driven by whether the GEOMETRY could place
it.** Those are different quantities, and `seen_frac` is not a proxy for the second — by
construction here, and by rho -0.166 between `seen_frac` and `max_z` in the data.

**Confound audit** (primary population, Spearman vs `seen_frac`): `dropout` -0.885,
`span_frames` -0.196, `max_z_m` -0.166, `launch_kmh` +0.014 (p=0.49). The two nuisance
correlations are weak, same-signed on both bands, and identical across clips by
construction (seed 0, same launches), so they cannot manufacture the band ratios above.

## 7. What this does NOT authorise, and the pre-registration for a replacement bar

**Not authorised:** changing `0.5`, proposing any specific replacement value, shipping,
quoting a coverage gain, or re-reading the "37 shots lose their speed to the chain" figure
as now-invalid. That figure is still exactly what it always was — *a count of shots under
this bar*; what this file establishes is that the bar has not been shown to sort accurate
speeds from inaccurate ones at the point where it cuts.

**PRE-REGISTRATION for choosing a replacement bar — written here, before any candidate
value has been looked at, and to be executed on clips NOT used above.**

1. **Held-out clips only.** `yt_rally2`, `am_hard_utr` and `yt_court` are now burned for
   this question. A replacement bar is chosen on calibrations not used here and not
   excluded by T23 / the demo30 rule — candidates from the audited PASS list, e.g.
   `court_pts_refined`, `eala_pts_auto`, plus any newly audited file. Minimum 3 clips.
2. **The candidate is a curve, not a point.** Sweep the threshold over [0.2, 0.9] in 0.05
   steps and report the FULL sweep. A value that is only good at one step is noise; this
   project has already had one threshold collapse under exactly that check.
3. **Pre-registered acceptance:** a replacement `t` is admissible only if, on **>= 3 of the
   held-out clips**, (a) accept-precision at `t` beats the base rate of "accurate" by
   **>= 10 points** (the 0.500-vs-0.472 result above is 2.8, and a bar that costs coverage
   must clear a margin no eye could mistake for noise), and (b) the neighbouring sweep
   steps `t +/- 0.05` are both within 3 points of `t`'s precision (the plateau test).
4. **Confirm on real footage before shipping.** The synthetic arm answers the causal
   question with random dropout. Before any value ships, the *ordering* it implies must be
   reproduced on real clips against a compliant reference — human-clicked ball tracks give
   `seen_frac` directly, and the accuracy side needs either `synth_truth` re-projected
   through the same calibration or a new compliant absolute reference. **Not the HUD.**
5. **The obvious alternative gate must be measured in the same sweep, not adopted:** §6
   says court-coverage fraction carries rho -0.749 where `seen_frac` carries -0.098. That
   makes it the leading candidate and therefore exactly the thing that must face the same
   held-out, swept, pre-registered bar rather than be swapped in on the strength of a
   correlation found here. Naming it is not proposing it.

## NOT ESTABLISHED THIS RUN

- **Whether `seen_frac` predicts speed error on REAL footage.** Only the causal
  (random-dropout) form of the question is answered. In real clips dropout is caused by the
  shot, so `seen_frac` could still carry predictive information this design cannot see.
  This is the single largest gap and item 4 of §7 exists for it.
- **Why the two populations disagree.** Restricting to shipped-shot speeds moves
  `yt_rally2` 1.35 -> 1.11 and `am_hard_utr` 0.86 -> 1.21. The mechanism is presumably the
  near-zero-speed collapse landing differently in the two bands, but it was not isolated.
- **The other three conjuncts of `speed_confident`** (`real_landing`, `is_serve`,
  `PLAUSIBLE_KMH`) are untested. Only `seen_frac` was under test.
- **The harness is uncommitted** (`scratchpad/seen_frac_vs_error.py`, `analyse.py`,
  `paired.json`). Promoting it to `tools/` is a code change and this brief bars code
  changes and STATE edits; §2 and §3 describe it precisely enough to rebuild.
- **No `docs/STATE.md` row was written** (barred by the brief). STATE still has no row for
  this question.
