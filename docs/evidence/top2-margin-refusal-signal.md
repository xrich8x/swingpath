# Top-2 blob margin as a REFUSAL signal — verdict against the pre-registered bar

**DELIVERABLE:** one written verdict — PASS / FAIL / UNDERPOWERED against the bar
pre-registered in `.claude/journals/lead.md` §"PRE-REGISTRATION — top-2 blob margin as a
REFUSAL signal, 2026-09-04, before any run" — with the margin distribution for good vs bad
frames, the chosen threshold's catch and collateral rates, the null-control result, the
null-mismatch numbers, and the provenance of every number.

Author: backend-dev, 2026-09-04. **Nothing here ships.** `mobile/ball_detector.js` and
`backend/swingvision/ball.py` are untouched; no coverage number is quoted; no threshold is
adopted. A PASS on this bar is a **screen that earns a wider run**, explicitly not a verdict
and explicitly not a ship — the lead named that before any number existed.

---

## 0. Verdict

**PASS on the fp32 heatmap — as a SCREEN, not a verdict.** *(section 3 for the threshold,
section 4 for the null control, section 6 for what the pass does not cover.)*

**FAIL on the int8 heatmap.** The signal is not computable on the graph that broke; it is
only computable on the graph that ships. That asymmetry is a finding, not a footnote —
section 3.2.

---

## 1. What was measured, and on what

`margin = 1 - score_2 / score_1` over the connected components of the decode's own
heatmap, where `score = area x peak`. Refusal rule under test: **refuse iff
`margin <= t`**. A frame with exactly one blob has no runner-up and is assigned
`margin = 1.0` (never refused).

**No inference was run and no model was loaded.** Every number below reads artifacts
already on disk from the 2026-09-03 six-clip parity run.

Scoring rule lifted verbatim from `backend/ball_parity_margin_census.py` (committed at
`28ead70`): OpenCV `threshold(heat, 127, 255, BINARY)` so `>=128`, 8-connected
`connectedComponentsWithStats`, `score = area * peak`. This is the same rule
`ball.py::_postprocess` and `mobile/ball_detector.js::_decode` both apply.

### Provenance of every number

| clip | parity dir (heatmaps + `js_results.json`) | summary file (labels) |
|---|---|---|
| `am_hard_utr` | `…\90dad6dd-87a4-4ac2-a50e-c4dab20c69f4\scratchpad\ball_parity` | `data/output/ball_detector_int8_parity_summary__am_hard_utr.json` |
| `yt_match40` | `…\90dad6dd-…\scratchpad\ball_parity_yt_match40` | `…__yt_match40.json` |
| `yt_rally2` | `…\90dad6dd-…\scratchpad\ball_parity_yt_rally2` | `…__yt_rally2.json` |
| `gold_am` | `…\ccc041b7-c8c5-43e5-a593-d06a07ec5983\scratchpad\ball_parity_gold_am` | `…__gold_am.json` |
| `gold_clay` | `…\ccc041b7-…\scratchpad\ball_parity_gold_clay` | `…__gold_clay.json` |
| `gold_shell` | `…\ccc041b7-…\scratchpad\ball_parity_gold_shell` | `…__gold_shell.json` |

(Temp-dir roots are `C:\Users\richm\AppData\Local\Temp\claude\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\`.)

**fp32 margin** is computed from `onnx_heat_<tag>.bin` — the bundled fp32 ONNX graph, the
one that ships. **int8 margin** is computed from `int8_heat_<tag>.bin`. Labels
(`dist_px`, `null_mismatch_tags`) come from the committed summary JSONs, not recomputed.

**GUARD, and it is clean.** For every frame the top-scoring blob's centroid must equal
what the real `_decode()` recorded in `js_results.json` (fp32 → `onnx_xy`, int8 →
`int8_xy`) to within 0.01 px. **Guard failures: 0 on fp32, 0 on int8, across all 528
both-fire frames.** Had they been non-zero these numbers would be void, not merely noisy.

### The populations

- **both-fire: 528.** 53 `am_hard_utr` + 93 `yt_match40` + 149 `yt_rally2` + 67 `gold_am`
  + 77 `gold_clay` + 89 `gold_shell`. Matches the parity run exactly.
- **bad (>10 px disagreement): 5.** `am_hard_utr/0147` (70.8 px),
  `yt_rally2/0108` (74.5), `/0109` (75.4), `/0110` (75.0), `gold_shell/0097` (185.1).
  This is *every* >10 px frame in the set — a ceiling on n, not a sampling choice.
- **correctly-decoded both-fire (the collateral denominator): 523.**
- **null mismatches (fp32 fires, int8 does not): 27** = 8 + 8 + 2 + 5 + 3 + 1.

---

## 2. Margin distribution, good vs bad

### The five bad frames

| clip | tag | dist_px | fp32 margin | int8 margin |
|---|---|---|---|---|
| `am_hard_utr` | 0147 | 70.8 | **0.0467** | 0.8601 |
| `yt_rally2` | 0108 | 74.5 | **0.0769** | 1.0000 |
| `yt_rally2` | 0109 | 75.4 | **0.0692** | 0.1608 |
| `yt_rally2` | 0110 | 75.0 | **0.0000** | 0.1608 |
| `gold_shell` | 0097 | 185.1 | **0.0692** | 0.2424 |

All five fp32 margins are `<= 0.0769`. `yt_rally2/0110` is an exact tie (`margin = 0`) —
two blobs with identical `area x peak`.

### Both-fire population, fp32 margin, per clip

| clip | n | min | p05 | p25 | median | frac <= 0.05 | frac <= 0.15 |
|---|---|---|---|---|---|---|---|
| `am_hard_utr` | 53 | 0.0083 | 0.0747 | 1.0000 | 1.0000 | 3.8% | 7.5% |
| `yt_match40` | 93 | 0.8571 | 1.0000 | 1.0000 | 1.0000 | 0.0% | 0.0% |
| `yt_rally2` | 149 | 0.0000 | 0.0769 | 1.0000 | 1.0000 | 2.0% | 6.0% |
| `gold_am` | 67 | 0.0152 | 1.0000 | 1.0000 | 1.0000 | 1.5% | 1.5% |
| `gold_clay` | 77 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0% | 0.0% |
| `gold_shell` | 89 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.1% | 2.2% |

**The distribution is not unimodal, it is nearly binary.** The median margin is 1.0000 on
every clip — the modal frame has a single blob and no runner-up at all. The signal is not
"how confident is the winner"; it is "is there a second blob worth arguing about", and on
most frames there is not. That is why a threshold anywhere in a wide band behaves the same
(section 3.1) and it is the main reason the pass is cheap rather than finely tuned.

`yt_match40` and `gold_clay` contain **no** frame below margin 0.85 and 1.00 respectively —
independently reproducing the property qa found on 2026-09-03 (`ball_parity_margin_census.py`
docstring): those two clips contain zero close races. They also contain zero failures.

---

## 3. The pre-registered bar, applied

**BAR (verbatim, unchanged):** *some margin threshold flags **>= 4 of the 5** known bad
frames while refusing **<= 5%** of correctly-decoded both-fire frames. Both halves
required.*

### 3.1 fp32 heatmap — the graph that ships

Full sweep. `catch` = bad frames refused / 5. `collat` = correctly-decoded both-fire
frames refused / 523.

| t | catch | collat | collat % | bar |
|---|---|---|---|---|
| 0.010 | 1/5 | 4/523 | 0.8% | fail (catch) |
| 0.020 | 1/5 | 5/523 | 1.0% | fail (catch) |
| 0.030 | 1/5 | 5/523 | 1.0% | fail (catch) |
| 0.050 | 2/5 | 5/523 | 1.0% | fail (catch) |
| 0.077 | 5/5 | 11/523 | 2.1% | **PASS** |
| 0.080 | 5/5 | 11/523 | 2.1% | **PASS** |
| 0.100 | 5/5 | 11/523 | 2.1% | **PASS** |
| 0.120 | 5/5 | 11/523 | 2.1% | **PASS** |
| 0.150 | 5/5 | 11/523 | 2.1% | **PASS** |
| 0.200 | 5/5 | 12/523 | 2.3% | **PASS** |
| 0.250 | 5/5 | 15/523 | 2.9% | **PASS** |
| 0.300 | 5/5 | 15/523 | 2.9% | **PASS** |

**Representative threshold: `t = 0.10`** — catch **5/5 (100%)**, collateral **11/523
(2.1%)**, well inside the 5% ceiling.

**The choice of `t` is deliberately not load-bearing, and that matters given how this
project has been burned before.** Every `t` in `[0.077, 0.30]` passes both halves; the
whole band shares a catch of 5/5 and a collateral of 2.1–2.9%. `t = 0.10` is quoted
because it is a round number inside the band, not because it was searched for.
`t = 0.077` is *excluded from consideration* even though it passes: it is exactly the
widest bad-frame margin (0.0769) and is therefore a threshold drawn around the numerator —
the precise post-hoc move the census docstring warns about. The plateau is what earns the
result, not the peak.

### 3.2 int8 heatmap — FAIL, and the asymmetry is the finding

| t | catch | collat | collat % |
|---|---|---|---|
| 0.050 | 0/5 | 2/523 | 0.4% |
| 0.100 | 0/5 | 8/523 | 1.5% |
| 0.150 | 0/5 | 9/523 | 1.7% |
| 0.200 | 2/5 | 12/523 | 2.3% |
| 0.250 | 3/5 | 13/523 | 2.5% |
| 0.300 | 3/5 | 13/523 | 2.5% |

**No threshold reaches 4/5 anywhere on the sweep.** The bar fails on int8.

The mechanism is visible in the table in section 2: on a frame the int8 graph gets *wrong*,
the int8 graph's own margin is **wide** — 0.86 on `am_hard_utr/0147` and a full 1.0000
(single blob, no runner-up at all) on `yt_rally2/0108`. Quantisation did not leave a
close race behind; it **resolved** the race, by eroding the true winner's area until the
impostor was the only blob left. The int8 graph is not merely wrong on these frames, it is
*confidently* wrong — which is exactly the failure signature the activation diff (`2110964`)
named, now measured on the decode side rather than inferred.

**Consequence for any implementation:** the refusal has to be computed from the fp32
graph's heatmap. It cannot be computed on-device from the int8 graph's own output. That is
a real constraint on where this could ever live, and it is stated here so it is not
discovered later.

---

## 4. Null control (MANDATORY)

Seeded, 1000 draws, `numpy.random.default_rng`, base seed `20260904`. Script:
`scratchpad/top2_null.py`. Run on the fp32 margins at the fixed representative
`t = 0.10`, where 16 of 528 both-fire frames are refused (5 bad + 11 good).

Three nulls were run, least to most conservative. **The pre-registered one is A**; B and C
are additions, not replacements, and both are harder to beat.

| null | what is permuted | catch >= 5 | catch >= 4 |
|---|---|---|---|
| **A. Pre-registered** | free permutation of the 5 bad labels over all 528 both-fire frames, fixed `t` | **0.0000** | **0.0000** |
| **B. Selection-adjusted** | as A, but every draw may search the same `t`-grid and keep its best catch subject to collateral <= 5% | **0.0000** | **0.0000** |
| **C. Cluster-preserving** | within-clip circular shift of the label vector — keeps `yt_rally2`'s 3-frame run intact *and* keeps each clip's bad-frame count | **0.0000** | **0.0010** |

Null A summary: permuted catch mean **0.151**, max **2** in 1000 draws — no permutation
reached even 3. The exact hypergeometric for the same statistic is
**P(catch >= 5) = 1.30e-08**, **P(catch >= 4) = 2.79e-06**, confirming the Monte Carlo
zero is a real tail and not a resolution limit of 1000 draws.

Null B exists because **`t` was chosen after seeing the sweep**, and a null that fixes `t`
gives the observed result a freedom it denies the permutations. Granting each permutation
the identical search: mean best-catch **0.194**, max **2**. The selection did not
manufacture the result.

Null C exists because **the 5 bad frames are not 5 independent events.**
`yt_rally2/0108`, `/0109` and `/0110` are consecutive frames of one failure — the same
cluster structure the parity work already recorded at `e52a39f`. Treating them as
exchangeable singletons inflates significance. Preserving both the run and the per-clip
counts, `catch >= 4` still occurs in only **1 of 1000** draws and `catch >= 5` in **0**.
(`catch >= 3` occurs in 7 of 1000.)

**Conclusion on power: the null control DOES separate at n = 5, on all three nulls
including the cluster-preserving one.** The branch is therefore reported as PASS, not
UNDERPOWERED. The separation is driven not by the count of bad frames but by how *rare*
low margins are: only 37 of 528 both-fire frames have a second blob at all, and only 16
fall below `t = 0.10`. A random 5 landing inside 16-of-528 is genuinely improbable
regardless of how few bad frames there are.

**What the null control does NOT license.** It says the association between low fp32
margin and int8 failure is not chance. It does not say the *rate* is estimable: with 5
events the catch rate's own confidence interval spans most of the unit interval, and
section 6 shows the association is far weaker than 5/5 makes it look.

---

## 5. Null mismatches — reported, not gating

The 27 frames where **fp32 fires and int8 does not**. fp32 margin:

| clip | n | median | min | frac <= 0.05 | frac <= 0.15 |
|---|---|---|---|---|---|
| `am_hard_utr` | 8 | 1.0000 | 1.0000 | 0.0% | 0.0% |
| `yt_match40` | 8 | 1.0000 | 0.9203 | 0.0% | 0.0% |
| `yt_rally2` | 2 | 1.0000 | 1.0000 | 0.0% | 0.0% |
| `gold_am` | 5 | 1.0000 | 1.0000 | 0.0% | 0.0% |
| `gold_clay` | 3 | 1.0000 | 0.4421 | 0.0% | 0.0% |
| `gold_shell` | 1 | 1.0000 | 1.0000 | 0.0% | 0.0% |
| **POOLED** | **27** | **1.0000** | **0.4421** | **0.0%** | **0.0%** |

**The margin has no signal on dropout, in either direction.** Not one of the 27 null
mismatches falls below `0.44`; 25 of 27 sit at exactly `1.0000` (single blob). The
answer to the lead's "worth more if it also predicts dropout" is **it does not** — and the
mechanism is clean: a dropout frame is one where fp32 found *one* faint blob and int8's
erosion pushed it under the `>=128` threshold entirely. There was never a runner-up to
argue with, so there is nothing for a top-2 margin to see.

This is a genuinely useful negative: the margin covers exactly one failure mode (the
confident wrong lock) and is blind to the other (dropout). Any future refusal design needs
a second, different signal for dropout — plausibly the winner's absolute `area x peak`,
which is not tested here.

---

## 6. Inspecting the rejects (rule 10) — and this is the part that qualifies the PASS

### 6.1 The 11 correctly-decoded frames refused at `t = 0.10`

True fp32-vs-int8 pixel error recomputed directly from `js_results.json`
(`onnx_xy` vs `int8_xy`), not read from the top-10 `worst_frames` list:

| clip | tag | fp32 margin | blobs | true error |
|---|---|---|---|---|
| `am_hard_utr` | 0119 | 0.0714 | 2 | 0.258 px |
| `am_hard_utr` | 0146 | 0.0769 | 2 | 0.287 px |
| `am_hard_utr` | 0149 | 0.0083 | 2 | 0.000 px |
| `gold_am` | 0178 | 0.0152 | 2 | 0.166 px |
| `gold_shell` | 0176 | 0.0000 | 2 | 0.000 px |
| `yt_rally2` | 0024 | 0.0571 | 2 | 0.226 px |
| `yt_rally2` | 0025 | 0.0667 | 2 | 0.000 px |
| `yt_rally2` | 0034 | 0.0769 | 2 | 0.278 px |
| `yt_rally2` | 0118 | 0.0000 | 2 | 0.144 px |
| `yt_rally2` | 0140 | 0.0667 | 2 | 0.318 px |
| `yt_rally2` | 0141 | 0.0000 | 2 | 0.196 px |

**These are not near-misses. They are perfect decodes.** Max error 0.318 px, three of them
exactly 0.000. Refused-good median error 0.196 px vs kept-good 0.000 px — a difference
with no product meaning at all (the whole good population's max is 1.362 px).

### 6.2 The mechanism the margin cannot see, stated plainly

Read the two tables together:

- `yt_rally2/0034` has margin **0.0769** and decodes at **0.278 px**.
  `yt_rally2/0108` has margin **0.0769** and decodes at **74.5 px**.
- `yt_rally2/0141`, `/0118` and `gold_shell/0176` have margin **0.0000** — an exact
  `area x peak` tie — and decode at 0.196, 0.144 and 0.000 px.
  `yt_rally2/0110` has margin **0.0000** and decodes at **75.0 px**.

**At identical margin, including an exact tie, the decode is correct three times out of
four.** The margin identifies the *population at risk*; it does not predict *which member
of that population flips*. Whether quantisation noise tips a tie one way or the other is,
on this evidence, a coin toss that the margin has no view on — which is exactly what the
activation diff would predict, since the noise is the same on failing and passing frames.

Quantitatively: only **37 of 528** both-fire frames have a second blob at all. `t = 0.10`
refuses **16** of those 37, of which **5** are the failures. **Refusal precision is
5/16 = 31%**; 11 of every 16 refusals throw away a perfect answer. That 31% is the same
number the `ball_parity_margin_census.py` docstring warns must not be quoted as a rate,
and the warning still applies — it is quoted here only as the cost side of the refusal,
never as a property of close races in general.

### 6.3 Missed bad frames

None at `t >= 0.077`. At `t = 0.05` the signal catches 2 of 5 and misses
`yt_rally2/0108` (0.0769), `/0109` (0.0692) and `gold_shell/0097` (0.0692) — i.e. the
whole result depends on the band `[0.05, 0.077]`, which contains three of the five
failures and no plateau boundary. The plateau above `0.077` is wide and flat, but the
*catch* transition is a single 2.7-point-wide step. With n = 5 that step is one frame's
worth of luck away from a different verdict.

### 6.4 What this means for the verdict

The PASS is real against the bar as written, and the bar was written before the run. But
what has actually been shown is the weaker, honest statement: **every int8 failure in this
set is a close race, and close races are rare (7% of both-fire frames).** It has *not*
been shown that a low margin predicts failure — inside the close-race set it does not
(section 6.2). A refusal built on this would be a **conservative risk gate that discards
roughly two correct answers for every error it avoids**, not a failure detector.

Whether that trade is worth taking is a product decision about how a refused frame is
handled downstream (coasted? interpolated? dropped?), and it is not answered here.

---

## 7. What is NOT established this run

1. **Any coverage or chain-level number.** Not measured, not authorised. Refusing 2.1% of
   both-fire frames is not the same as losing 2.1% of anything the user sees; the smoother
   coasts, and the effect on ghosts, speed coverage or rendered output is unknown.
2. **That the margin predicts failure within the close-race set.** Section 6.2 shows it
   does not, on the evidence available.
3. **Generalisation past six clips and 528 frames.** The PASS is a screen and earns a
   wider run; it is explicitly not a ship. n = 5 is a ceiling on this set, and the three
   `yt_rally2` frames are one event, so the effective event count is nearer 3.
4. **Anything about a threshold value to adopt.** `t = 0.10` is a representative interior
   point of a plateau, quoted for reporting. No threshold is proposed, and `t = 0.077` is
   excluded as post-hoc by construction.
5. **A dropout signal.** Section 5 is a clean negative; a second signal would be needed.
6. **Behaviour on the fp32-only path in production.** Every number here compares fp32
   against int8. The claim that the fp32 path is "one bad frame from the same error" rests
   on the margin distribution, not on an observed fp32 failure — no fp32 ground-truth
   failure exists in this set to test against.
7. **Cost on device.** Asserted as "a comparison" in the pre-registration; not measured.
   The blob decomposition is already computed, but nothing here timed it on an A13.

---

## Reproduce

```
backend/.venv/Scripts/python.exe scratchpad/top2_margin.py   # extraction + sweep
backend/.venv/Scripts/python.exe scratchpad/top2_null.py     # 3 nulls + rejects
```

(`scratchpad` = `C:\Users\richm\AppData\Local\Temp\claude\e--Claude-Outputs-Cowork-Tasks-Swing-Vision\ccc041b7-c8c5-43e5-a593-d06a07ec5983\scratchpad`.
Both scripts load only `.bin` heatmaps and JSON already on disk; neither loads a model or
runs inference. Seeds: `20260904`, `+1`, `+2` for nulls A, B, C.)

