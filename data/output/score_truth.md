# The rally/score layer has ground truth for the first time

**Date:** 2026-08-15 · **Tool:** `tools/score_truth.py` · **Evidence:**
`data/gold/{yt_match40,am_hard_utr}.score_truth.json`
**Measured against:** each clip's own burned-in broadcast scoreboard — read by per-field
state clustering, with every distinct state labelled **by eye**. The scoreboard is produced
by the recording system and is completely independent of anything this project computes,
so this cannot self-grade. **Evidence tag: MEASURED.**

## Why this matters

Ball detection has 1,851 human clicks. Court has 20 hand-labelled clips. Speed has the HUD
and `synth_truth`. **Rallies and score had nothing** — no point boundary had ever been
labelled, so *"63 rallies is wrong"* was an assertion. It is now a measurement.

## The result

| clip | truth points | pipeline rallies | over-split | truth games | validation |
|---|---|---|---|---|---|
| **yt_match40** | **43** | **63** | **1.47×** | 5–1 (6 changes) | 0 issues |
| **am_hard_utr** | **36** | *(no cache)* | — | 2–4 (6 changes) | 0 issues |

`yt_match40`'s pipeline figures are read from the committed
`data/output/yt_match40.json` (2026-08-08): 63 rallies, 196 shots, 63 points in the score
timeline. Not re-derived — the artifact itself.

**Every point transition in both clips is legal tennis.** That is the independent check: a
misread digit almost always produces an illegal jump (15→40, 0→30), and 79 transitions
across two clips produced none. Per-point winner is resolved for **43 of 43** points on
yt_match40 (27 D. Tan / 16 Opponent).

## Correction to the 2026-08-13 research

That work estimated **"≈35–40 points, over-split ≈1.6×"** by counting distinct pixel-states
of the **whole panel**. The measured truth is **43**, which sits *outside* that range, and
the real over-split is **1.47×**.

The reason is the method, and it is the point of this tool. A whole-panel state changes when
*anything* changes — including the server dot moving at a game change — so the count
conflates three different events and the research had to hedge ±5. Clustering **per field**
separates them exactly: points move the points field, games move games, serve moves the dot.

## Why not OCR

`hud_ocr.py` segments glyphs and NCC-matches them, which is right for the speed readout
where the value is an arbitrary number. A tennis score is not arbitrary — points take 5
values, games 0–7 — so each field is clustered into distinct visual states and each state is
labelled **once, by a human**. Two things this caught that automation would not:

- On `am_hard_utr`'s `dot_bot`, the clustering **false-split the empty box into two states**
  on a background gradient. Trusting cluster identity to be semantic would have invented a
  serve change.
- On `yt_match40`, state `#0` of every field is **the scoreboard not being displayed** (the
  clip opens before the graphic appears). Entering and leaving that state would have
  invented two points. Those samples are dropped, and the count is recorded.

## Two panels, two vocabularies

| clip | deuce | advantage | panel |
|---|---|---|---|
| `am_hard_utr` | `DU` | `AD` | opaque navy card, white box behind points |
| `yt_match40` | `40`–`40` | `AD` | **semi-transparent** dark card over a **moving hedge** |

The second needed a different signature: an adaptive threshold follows the moving background
and shatters one digit into many states, so that clip thresholds on absolute brightness
instead (the glyphs stay near-white throughout). Recorded per clip as `sig` in `PANELS`.

## Not concluded here, on purpose

**`gap_s` is untouched.** The project's own rule — and the reason this reference was built
first — is that tuning a threshold against no reference is how you get a number you cannot
defend. The reference now exists; the tuning is separate work with its own pre-registered
gate.

**The game-score comparison is NOT yet a result.** Truth reads `5–1` top-to-bottom
(D. Tan–Opponent); the pipeline reports `2–5`. Those may be the same scoreline under a
different player-order convention (near/far vs panel top/bottom), which would make it
`5–2` against a true `5–1`. **Resolve the ordering convention before quoting this
either way** — as a difference it looks alarming, and as an off-by-one-game it looks
almost right, and nothing here distinguishes them yet.

## Reproduce

```
py tools/score_truth.py probe --clip yt_match40 --at 120 --out boxes.png
py tools/score_truth.py scan  --clip yt_match40 --every 0.5 --out scan.json
py tools/score_truth.py sheet --clip yt_match40 --scan scan.json --field pts_top --out st.png
py tools/score_truth.py build --clip yt_match40 --scan scan.json --out truth.json
```

Panel geometry is **recorded in the tool**. The 2026-08-13 research located these boxes,
produced evidence images and kept no code, so the coordinates were lost and had to be found
again from the pixels.
