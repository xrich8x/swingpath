# Making the smoother respect suppression — MEASURED NEGATIVE, and it reframes `suppress_false_locks`

**Date:** 2026-08-13 · **Evidence:** `data/output/coherent_*.json` vs `chain_ab_*.json`
**Measured against:** human gold clicks through the shipped chain on the three calibrated
gold clips — 532 scoreable ball frames, 103 no-ball frames. Shipped detector `ballnet_v21`.

## The hypothesis, and why it was worth testing

The Session K chain test made a mechanism visible. `suppress_false_locks` removes ghost
locks and then the Kalman smoother **puts them back**:

| clip | model | tracker gates | after suppress | after Kalman |
|---|---|---|---|---|
| am_hard_utr | v21 | 9 | **1** | **6** |
| am_hard_utr | arm B | 13 | 8 | 9 |
| yt_match40 | v21 | 8 | 6 | 7 |
| yt_match40 | arm B | 7 | 6 | 9 |
| yt_rally2 | v21 | 9 | 5 | 6 |
| yt_rally2 | arm B | 8 | 3 | 2 |

Five of six runs get worse at the smoother, and every added fire is **faded**, i.e.
interpolated. The two stages are blind to each other: `smooth_forecast` sees only `None`
and cannot distinguish *the detector never fired here* (interpolating is the right guess)
from *a lock was deleted here as false* (interpolating re-asserts what suppression denied).

Fix: pass the removed-frame mask, and refuse to bridge a gap whose interior contains one.
Deliberately **not** `max_gap_s` by another name — that shrinks every bridge and was already
measured to cost recall ~1:1 (Session F step 4). This refuses only the bridges an earlier
stage had positively argued against.

## Pre-registered gate

Written down before the change was scored, against the shipped v21 baseline
(19 fires = 9 solid + 10 faded, pooled recall 66.9% — reproducing Session F exactly):

- **primary:** pooled total ghost fires < 19
- guard: solid ghosts must not rise above 9
- guard: pooled chain recall ≥ 64.9% (≤2 pt drop)
- guard: worst-clip far_geo drop ≤ 2 pts

## Result

| clip | scoreable | recall | far_geo | ghost fires |
|---|---|---|---|---|
| am_hard_utr | 90 | 54.4 → 53.3 | −1.4 | 6 → **3** |
| yt_match40 | 184 | 65.2 → **58.2** | **−7.2** | 7 → 6 |
| yt_rally2 | 258 | 72.5 → **67.4** | **−5.6** | 6 → 6 |
| **POOLED** | **532** | **66.9 → 61.8** | | **19 → 15** |

| gate | | |
|---|---|---|
| primary: ghost fires fall | 19 → 15 | **PASS** |
| guard: solid ghosts do not rise | 9 → 9 | **PASS** |
| guard: recall drop ≤ 2 pts | **−5.1** | **FAIL** |
| guard: worst far_geo drop ≤ 2 pts | **−7.2** | **FAIL** |

**VERDICT: FAIL. Not shipped.** The parameter and its four unit tests stay in
`ball.smooth_forecast`; `pipeline.analyze_video` does not pass it.

## What it actually taught us — the useful part

The trade is **4 ghost frames removed for ~27 real ball frames lost** (5.1% of 532) —
roughly **7 real balls per ghost**.

That ratio only makes sense one way: **the gaps `suppress_false_locks` opens are mostly
gaps where it deleted a REAL ball, not a ghost.** Suppression is already known to cost
5–10 pts of recall by design; this measurement says that cost dominates its output. So
refusing to bridge its removals compounds its own error instead of correcting a ghost.

That is a sharper characterisation of `suppress_false_locks` than the project had. It is
not "a filter that removes false locks, at some recall cost" — on this evidence it is a
filter whose removals are **majority real ball**, kept because the ghosts it does catch are
worth more than the balls it loses. Any future work on it should start from that.

Note also that this reaches the same ~1:1 recall trade Session F measured for `max_gap_s`,
by a completely independent route. Two different mechanisms landing on the same exchange
rate makes it look **structural** — the smoother's interpolation is buying real recall, and
anything that removes interpolation pays for it in recall at about the same price.

## Caveat

103 no-ball frames, 19 → 15 fires. `gate_verdict`'s resolution note applies: sampling alone
moves a count of this size by ±2.8, so the 4-frame drop is roughly one sigma and is **not**
established as a real reduction. The recall loss, at −5.1 pts over 532 frames, is far
outside noise. The asymmetry is the whole verdict: the cost is measurable, the benefit is
not.
