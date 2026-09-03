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

## 4. Null control (MANDATORY) — (pending)

## 5. Null mismatches — reported, not gating — (pending)

## 6. Inspecting the rejects (rule 10) — (pending)

## 7. What is NOT established — (pending)
