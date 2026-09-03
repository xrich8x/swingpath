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
  runoff-box test (`pipeline.py:1471-1472`) then `ball.cap_court_jumps(max_step_m =
  84/fps)` then `ball.smooth_and_fill(window=7, polyorder=2)` then
  `analytics.shot_speed_kmh`.
- Error: `abs(100 * (est - avg_ground_kmh) / avg_ground_kmh)`.

**CORRECTION 2026-09-03 (§8):** the harness ran that runoff box at **+/-4.0 m**. The
**shipped** value is **2.5 m** (`RUNOFF_M`, `pipeline.py:1352`). That is a fidelity defect in
this harness, not a design choice, and it is the one place where the faithful configuration
differs materially from what §4/§5 report. `tools/seen_frac_speed_error.py --runoff-m 2.5`
is the faithful setting; §8.2 ablates it (it moves each clip's ratio by <= 0.06 on its own)
and §8.4 states the one conclusion that does turn on it.

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
| harness | **`tools/seen_frac_speed_error.py`** (promoted 2026-09-03; was `scratchpad/seen_frac_vs_error.py` + `analyse.py`). Defaults reproduce every number in §4/§5 exactly, including band counts — see §8.1. |
| runoff box | **4.0 m** in this file's numbers; **shipped is 2.5 m** (`pipeline.py:1352`) — see the correction in §2 and the ablation in §8.2 |
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
never have emitted as a shot at all. **Corrected citation (was `pipeline.py:1762` for both
cuts, which conflated two lines and omitted a condition — qa, 2026-09-03):**

```python
1759:  if speed < MIN_SPEED_KMH:                              # 5.0, unconditional
1760:      continue
1761:  if not is_serve and (disp < 0.8 or speed > 250.0):     # NOT applied to serves
1762:      continue
```

So the `> 250` cut is **conditional on `not is_serve`**, and the same conjunction also
carries `disp < 0.8`, which the arms below do not apply either. The gate's own conjunction
separately requires `speed <= PLAUSIBLE_KMH` (160) and `not is_serve`. This harness has no
serve/rally distinction, so Arms A/B apply the non-serve branch to every flight — a
population slightly **stricter** than the pipeline's, stated rather than hidden. It does not
change what the arms show. Omitting these filters from the primary population was an
oversight in fidelity, not a design choice, so the restricted arms are reported alongside —
**the bar is unchanged in all of them.**

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

   **And the correlation is PARTLY MECHANICAL, not purely diagnostic** (qa, 2026-09-03 —
   stated here because §6 did not say it plainly). `analytics.shot_speed_kmh` integrates the
   path over **exactly the points that survived court projection**: the runoff-box gate and
   `cap_court_jumps` delete points, `smooth_and_fill` bridges the hole flat, and the path
   integral therefore collapses toward zero *by construction* as court-coverage falls. A
   large negative rho between court-coverage and error is thus partly a restatement of how
   the estimate is computed, not an independent discovery that court-coverage predicts
   error. That is a second, independent reason not to swap it in as a gate: a gate must be
   evaluated against an error measured over a span the gate did not itself define. The
   -0.749-vs-0.098 gap is still a real and large asymmetry — `seen_frac` is *also* a
   coverage statistic and does not enjoy the same mechanical advantage — but the magnitude
   of -0.749 must not be read as a clean effect size.

## NOT ESTABLISHED THIS RUN

- **Whether `seen_frac` predicts speed error on REAL footage.** Only the causal
  (random-dropout) form of the question is answered. In real clips dropout is caused by the
  shot, so `seen_frac` could still carry predictive information this design cannot see.
  This is the single largest gap and item 4 of §7 exists for it.
- ~~**Why the two populations disagree.**~~ **ANSWERED 2026-09-03 — see §8. The
  population-to-population moves quoted here (1.35 -> 1.11, 0.86 -> 1.21) are inside the
  ratio's own sampling noise and should not be given a mechanism.**
- **The other three conjuncts of `speed_confident`** (`real_landing`, `is_serve`,
  `PLAUSIBLE_KMH`) are untested. Only `seen_frac` was under test.
- ~~**The harness is uncommitted.**~~ **RESOLVED 2026-09-03: promoted to
  `tools/seen_frac_speed_error.py`, which reproduces this file's numbers AND qa's rebuild
  exactly, from flags. See §8.**
- **The band ratio's sensitivity ceiling on 2 of 3 cameras** (qa's positive control, §8.4).
  A real but weak `seen_frac` effect could go undetected on `am_hard_utr` / `yt_court` by
  this exact band window, because error saturates before the window can resolve it. The
  harness is demonstrably not blind in general; it is blind to *small* effects on those two
  geometries.
- **No `docs/STATE.md` row was written** (barred by the brief). STATE still has no row for
  this question.

---

## 8. Reconciliation with qa's rebuild — why the two implementations disagreed

Added 2026-09-03, after `docs/evidence/seen-frac-gate-qa-verification.md` reported that an
independent rebuild produced materially different band ratios, flipping `yt_court` to the
other side of 1.0. **The verdict is unchanged. What changes is how many digits of the band
ratio anyone — qa or me — is entitled to quote: the answer is roughly none.**

### 8.1 The harness is now in the repo, and it reproduces BOTH implementations exactly

`tools/seen_frac_speed_error.py`. Clips and seed are arguments; defaults are the exact
configuration that produced §4's numbers; qa's correlated-dropout positive control is
`--arm correlated`, an option rather than a fork, because the control is part of the
experiment now. Provenance is stamped from the resolved argparse namespace, never a preset
table.

The refactor proof is two-sided — one file, two flag sets, both prior results land on the
digit *and on the band counts*, which is the stronger check:

| what | command | result | previously published |
| --- | --- | --- | --- |
| §4 primary | `--n 1200` | 1.346 (155/201) / 0.855 (132/171) / 0.756 (143/197), n=2557 | 1.35 / 0.86 / 0.76, same counts, n=2557 |
| §5 Arm A | `--n 1200` (shipped_shot block) | 1.110 (126/163) / 1.223 (84/100) / 1.017 (98/120) | 1.11 / 1.22 / 1.02, same counts |
| §5 Arm B | `--n 1200 --max-speed-kmh 160` | 1.114 (125/163) / 1.207 (78/97) / 0.969 (97/118) | 1.11 / 1.21 / 0.97, same counts |
| **qa's rebuild** | `--n 800 --runoff-m 2.5 --min-alive 6 --rng-scheme split --track-mode compressed` | **1.180 (81/95) / 1.465 (38/54) / 1.893 (55/66)** | qa: **1.18 (81/95) / 1.46 (38/54) / 1.89 (55/66)** |

**qa's positive control reproduces exactly too**, `--n 500 --runoff-m 2.5 --min-alive 6
--rng-scheme split --track-mode compressed --arm {random,correlated}`, unrestricted
population — every band count and every median lands on qa's:

| clip | `--arm random` | `--arm correlated` (dropout ranked onto `max_z`) |
| --- | --- | --- |
| yt_rally2 | 1.583 (62/65) | 1.763 (85/84) |
| am_hard_utr | 0.905 (53/59) | 1.000 (56/80) |
| yt_court | 1.046 (59/62) | 1.142 (72/83) |

qa's published values: 1.58 / 0.91 / 1.05 and 1.76 / 1.00 / 1.14, same counts.

**And running the control through the tool surfaces something qa's write-up did not: the
band ratio is the WEAK instrument, and the classifier framing is the sensitive one.** On the
same two arms, pooled:

| arm | accept-precision | base rate | margin | refused-but-accurate |
| --- | --- | --- | --- | --- |
| random | 0.500 | 0.462 | **+3.8 pts** | 36.4% of refused |
| correlated | 0.501 | 0.353 | **+14.8 pts** | 4.5% of refused |

Under the injected correlation the gate becomes genuinely informative and would **clear §7's
pre-registered >= 10-point replacement bar**, while the band ratio on two of three clips
barely moves off 1.0 (0.905 -> 1.000, 1.046 -> 1.142). Same injected effect, same rows: one
metric sees it plainly, the other does not. This is direct evidence that the ratio-of-medians
estimator — not the harness, and not the data — is what is failing to resolve an effect, and
it reinforces §8.3's conclusion and §7's choice of accept-precision as the acceptance metric
for any future bar.

One detail that was load-bearing for exact reproduction and is called out in the tool: the
original harness `continue`d on `alive.sum() < MIN_ALIVE` **before** drawing pixel noise, so
a rejected flight consumed no `normal()` draws and shifted every later flight's stream
position. An implementation that draws noise unconditionally is not wrong; it is a different
sample.

### 8.2 One framing error, then five real differences — and none of them is the cause

**Framing error first, so it is not mistaken for a mechanism.** The comparison as circulated
put my **Arm B** (`5 < est < 160`, 1.11 / 1.21 / 0.97) against qa's **Arm A** (`5 < est <
250`, 1.18 / 1.46 / 1.89). Like for like, my Arm A is 1.110 / 1.223 / **1.017**. So a little
of the `yt_court` gap is a population mismatch — but only 0.05 of it.

The five genuine implementation differences, each ablated as **one variable** from the
default, Arm A, `--seed 0 --n 1200`:

| change | yt_rally2 | am_hard_utr | yt_court | move on yt_court |
| --- | --- | --- | --- | --- |
| *(baseline = §5 Arm A)* | 1.110 | 1.223 | 1.017 | — |
| `--runoff-m 2.5` (qa's, and **the shipped value**) | 1.144 | 1.231 | 1.038 | +0.02 |
| `--min-alive 6` (qa's) | 1.015 | 1.559 | 0.961 | -0.06 |
| `--rng-scheme split` (qa's separate streams) | 1.232 | 1.018 | 1.013 | -0.00 |
| `--track-mode compressed` (qa drops None frames before Sav-Gol) | 1.246 | 1.306 | 0.965 | -0.05 |
| all four, `--n 1200` | 1.742 | 1.020 | 1.369 | +0.35 |
| all four, `--n 800` (**= qa exactly**) | 1.180 | 1.465 | **1.893** | +0.88 |

**No single implementation choice moves `yt_court` by more than 0.06.** The largest
single-flag move anywhere in the table is `--min-alive 6` on `am_hard_utr` (1.223 -> 1.559).
The four flags together do shift the central tendency up (§8.3 puts that at roughly +0.3 in
the mean), but the flags cannot account for a 1.02 -> 1.89 flip, and neither can the change
in `n`: the *same* qa configuration at `--n 1200` gives 1.369, not 1.893, on the same seed.

So it is **not** seeding scheme, **not** band membership at the boundary — though that one
deserves a warning rather than a dismissal. `seen_frac` is a ratio of small integers, and
**74 of 2557 rows (2.9%) sit exactly on 0.50**, which is also the gate's own threshold. Both
implementations happen to use the same half-open convention (`[0.35,0.50)` / `[0.50,0.65)`,
so an exact 0.50 is ACCEPTED, matching `seen_frac >= 0.5` in `pipeline.py`), and the band
counts in §8.1 match exactly, which they could not if the convention differed. But a future
implementation that flips one `<` to `<=` would move ~3% of the sample across the boundary
in the direction that flatters the gate. It is not the cause here; it is a live trap.
Next, **not** the serve condition in the shot filter (§5's
corrected citation: it changes which flights are in the population, and both Arm A and Arm B
were re-run above), and **not** float accumulation in the path integral (identical code,
`analytics.shot_speed_kmh`, invoked not re-derived).

### 8.3 The cause: the adjacent-band ratio is not a stable quantity

Seeds 0-9, Arm A ratio, both configurations:

| config | clip | mean | sd | min | max |
| --- | --- | --- | --- | --- | --- |
| this file's default, `--n 1200` | yt_rally2 | 1.312 | 0.338 | 0.826 | 1.944 |
| | am_hard_utr | 1.070 | 0.256 | 0.554 | 1.377 |
| | yt_court | 1.088 | 0.166 | 0.924 | 1.395 |
| qa's, `--n 800` | yt_rally2 | 1.715 | 0.445 | 0.962 | 2.274 |
| | am_hard_utr | 1.394 | 0.352 | 0.800 | 1.972 |
| | yt_court | 1.304 | 0.404 | 0.623 | 1.893 |

`yt_court`'s 1.893 is that configuration's **maximum over ten seeds**, and 0.623 is its
minimum. A single clip's ratio moves by more than 1.2 across innocuous reseeds. Non-parametric
bootstrap (4000 resamples within each band, `--seed 0`) says the same thing about a single
run's own uncertainty:

| config | clip | point | bootstrap 95% CI | width |
| --- | --- | --- | --- | --- |
| default, n=1200 | yt_rally2 | 1.110 | [0.85, 1.68] | 0.83 |
| | am_hard_utr | 1.223 | [0.80, 1.67] | 0.87 |
| | yt_court | 1.017 | [0.80, 1.49] | 0.69 |
| qa's, n=1200 | yt_rally2 | 1.742 | [0.89, 3.37] | 2.47 |
| | am_hard_utr | 1.020 | [0.76, 1.55] | 0.79 |
| | yt_court | 1.369 | [0.85, 2.02] | 1.18 |

**Every interval contains 1.0.** No clip's band ratio, in either implementation, is
distinguishable from "no effect" at its own sample size. The estimator is a ratio of two
medians of a heavy-tailed, ceiling-saturating error distribution over n ~ 40-160 per band;
it has no business being read to two decimals, let alone three.

**This is the finding, and it is more useful than a reconciled digit: the adjacent-band
ratio was never a quantity worth quoting to three digits by anyone, including this file.**
§4 and §5 should be read as "no clip separated the bands", not as the specific numbers they
report. Both harnesses were correct. They drew different samples.

### 8.4 The one thing this does change, stated rather than buried

Under **qa's configuration — which is the more faithful one, because `--runoff-m 2.5` is the
shipped value at `pipeline.py:1352` and this file's harness used 4.0, a fidelity defect on my
side** — the pre-registered G would have **passed on 4 of 10 seeds** (seeds 2, 3, 6 and 9
each put >= 2 clips at >= 1.5x). Under this file's default configuration G passes on 0 of 10.

This does **not** establish G, and the bar is not being moved: a pre-registered bar that
passes on 4 of 10 reseeds of the same experiment has not been met, it has been shown to be
undecidable by this experiment at this sample size. The correct reading is that the
**INDETERMINATE verdict is reinforced**, and that the specific claim "G fails on every clip
in every arm" is true of *the seeds that were run* but is not robust to reseeding under the
faithful configuration. Anyone re-running this must sweep seeds; a single-seed G-refusal
from this harness is not evidence.

What is *not* affected: **G was never passed by anybody**, in any run, at any seed, in the
sense the pre-registration required of a single pre-registered execution; and the two
independent implementations agree on every claim that does not go through the band ratio.

### 8.5 What is safe to quote to three digits, and what is not

**Safe.** These reproduced across two independently written implementations with different
sample sizes, different RNG streams and different chain-assembly details:

- **The gate is at chance as a classifier of accuracy.** Accept-precision **0.500-0.501**
  against a base rate of **0.467-0.473**, on both implementations, on both populations, at
  every configuration in §8.2's table. A ~3-point margin, where §7's pre-registered
  replacement bar demands >= 10.
- **Refused-but-accurate is ~38-39% of the refused set** in every run either of us made.
- **The court-coverage / `seen_frac` asymmetry as a *shape*** (a large negative rho versus a
  near-zero one) — with §7's mechanical-correlation caveat attached to its magnitude.
- **Every whole-range Spearman for `seen_frac` is small and negative.** The sign and the
  order of magnitude reproduce; the third digit does not.

**Not safe.** Any individual adjacent-band ratio, to any precision beyond "near 1"; any
statement that one clip's ratio is above or below another's; and any mechanism offered for a
population-to-population move in §4/§5 of less than about 0.5 (which is all of them). The
"why do the two populations disagree" question in NOT ESTABLISHED is withdrawn rather than
answered: those moves are noise and do not have a mechanism.

**If this question is ever reopened**, the estimator has to change before the bar can be
tested: seed-average the ratio over >= 20 seeds and report its spread, or replace the ratio
of medians with a paired design (the same flight simulated at two dropout levels), which
removes the between-flight variance that is drowning the effect. §7's pre-registration for a
replacement bar stands as written and is unaffected by any of this.


---

## Definitive numbers on the faithful config. 2026-09-04 (lead, run directly)

The agent briefed for this was killed by a session limit before doing any work. The harness
had been promoted to `tools/seen_frac_speed_error.py` an hour earlier, so the lead ran it
directly — which is the payoff for promoting it out of a scratchpad.

**Configuration:** shipped runoff **2.5 m** (`pipeline.py:1352`) — *not* the 4.0 m that
produced §§4-5. **10 seeds x 2 arms**, because this file's own instability finding is that a
single seed is not evidence. `--arm correlated` is qa's positive control.

**The instrument is the classifier margin, not the band ratio.** That choice is forced by the
evidence already in this file: the band ratio's bootstrap CIs all contain 1.0, while under an
injected effect the margin moves and the ratio does not. **The bar — accept-precision minus
base rate >= +10.0 points — is the one pre-registered in §7**, written before this number
existed and not adjusted after seeing it.

| population | arm | margin (pts) | sd | seeds >= +10 | verdict |
|---|---|---|---|---|---|
| unrestricted | **shipped gate** | **+4.96** | 1.00 | **0/10** | **FAIL** |
| unrestricted | positive control | +12.49 | 0.78 | 10/10 | PASS |
| shipped_shot | **shipped gate** | **+3.11** | 0.71 | **0/10** | **FAIL** |
| shipped_shot | positive control | +4.58 | 0.57 | 0/10 | FAIL |

### What this establishes

**The shipped gate fails the usefulness bar, stably.** +4.96 and +3.11 points against +10,
on 0 of 10 seeds in both populations, with sd ~1.0 and ~0.7. This is not a knife-edge result
and it does not depend on a seed.

**On the `unrestricted` population that FAIL is meaningful**, because the control reaches
+12.49 (10/10 seeds) — the instrument can see a real effect there, and separates control from
shipped by **+7.53 points**.

### What this does NOT establish, and it is the important half

**On the `shipped_shot` population — the one that matches what the pipeline actually emits —
the positive control itself FAILS, reaching only +4.58 against the same +10 bar, and clearing
it on 0 of 10 seeds.** Control minus shipped is **+1.47 points**. So on the population that
matters most, this experiment can barely distinguish a strong injected effect from none.

> **The `shipped_shot` FAIL is UNDERPOWERED, not a clean negative.** A verdict is only worth
> what its control says, and here the control says the instrument is nearly blind on that
> population. Reporting the FAIL without this would be quoting a result the experiment was
> not powerful enough to produce.

### TWO EARLIER CLAIMS IN THIS FILE ARE WITHDRAWN

Both came from the 4.0 m defect and both were repeated into `docs/STATE.md` by the lead.

1. **WITHDRAWN — "the gate refuses shots whose median error is less than half that of what it
   accepts".** Under the faithful config **the opposite is true**: refused shots are *worse*,
   by **+39.9 points** median absolute error (85.4% refused vs 45.4% accepted) on
   `unrestricted` and **+13.0 points** (39.8% vs 26.8%) on `shipped_shot`. **The gate is
   directionally correct.** It does refuse the worse shots; it is simply not strong enough to
   be worth what it costs.
2. **WITHDRAWN — "the gate is at chance".** It is not. Accept-precision sits **~3-5 points
   above base rate**, consistently and on every seed. That is weak, far under the +10 bar, and
   not worth the coverage it spends — but "weakly predictive and below the usefulness bar" is
   a different and more accurate claim than "at chance", and only the first is supported.

**What survives unchanged:** a substantial share of what the gate throws away is accurate —
**33.0%** of refused shots on `unrestricted`, **37.8%** on `shipped_shot`, are in the accurate
half. That is the real cost and it was not an artefact of the defect.

**Superseded by this section:** every accept-precision, base-rate, refused-but-accurate and
median-error figure in §§4-5, and the two withdrawn claims above. The INDETERMINATE verdict on
the band ratio stands and is reinforced. No threshold was changed and none is named.

Raw per-seed JSON: 20 runs under the lead's scratchpad `sf/`, each stamping its resolved
config and the calibration hashes. Reproduce with
`tools/seen_frac_speed_error.py --seed <n> --arm <random|correlated>`.
