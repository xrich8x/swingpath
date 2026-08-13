# The +57%-data detector does NOT reach the product — and recall now fails the same way precision did

**Date:** 2026-08-13 · **Tool:** `tools/eval_model_filters.py` + `tools/gate_verdict.py`
**Evidence:** `data/output/chain_ab_{yt_rally2,yt_match40,am_hard_utr}.json`
**Measured against:** human gold clicks on the three calibrated clips — 532 ball frames, 74
no-ball frames — scored through the SHIPPED chain (tracker gates → rectify →
`suppress_false_locks` → court gate → Kalman), i.e. what the renderer actually draws.

## Verdict

| | solid ghosts | chain recall |
|---|---|---|
| `ballnet_v21` (shipped) | **9** | 66.9% |
| `pool_new_s0` (arm B, +57% data) | **13** | 66.9% |

Pre-registered gate: solid ghosts must fall, recall must not drop >2 pts, far_geo must not
drop >2 pts.

- solid ghosts **FAIL** (+4)
- recall PASS (+0.0)
- far_geo PASS (+0.0)

**VERDICT: FAIL. `ballnet_v21.pt` stays the default. Arm B is not shipped.**

`v21` scoring exactly **9** solid ghosts independently reproduces the standing figure and
checks the whole measurement chain.

## The result that matters more than the verdict

**A detector recall gain of +5.6 pts arrives at the product as +0.0 pts.**

| clip | tracker-gates-only recall | FULL chain recall |
|---|---|---|
| yt_match40 | 65.8 → **75.5** (+9.7) | 65.2 → 67.4 (+2.2) |
| am_hard_utr | 60.0 → 57.8 (−2.2) | 54.4 → **54.4** (+0.0) |
| yt_rally2 | — | 72.5 → 70.9 (−1.6) |

Nearly ten points of extra recall survive the tracker gates on yt_match40 and are then
absorbed by `suppress_false_locks` and the Kalman. Pooled, the chain returns **exactly the
same number it returned before**.

Session I established that detector *precision* gains do not reach the product, three times
over, and that finding explicitly did **not** predict what a *recall* gain would do. Now
measured: it does not arrive either. **The chain, not the detector, is the binding
constraint on what the user sees.**

## Where the extra ghosts come from — the target footage

The per-clip rows disagree in sign, and the disagreement is the point:

| clip | camera | solid ghosts v21 → arm B |
|---|---|---|
| yt_rally2 | 3.31 m | 5 → **2** |
| yt_match40 | 11.33 m | 3 → 4 |
| **am_hard_utr** | **1.74 m, 1080p** | **1 → 7** |

The clip that collapses is the low-mount amateur 1080p clip — the footage this project
targets. Same pattern as Session I, where the 15-epoch arms were also worst precisely
there, and as Session H part 6, where a smoother setting that looked clean on yt_rally2 fell
apart on am_hard_utr. **Never decide this on the easy clip.**

## Honest limits

`gate_verdict` flags both:

1. **The clips disagree in sign** (+6, +1, −3), so the pooled +4 is an average of opposite
   effects — the signature of noise rather than a mechanism. Only **4 of 18** solid-ghost
   frames fire on both arms (22% overlap).
2. **Resolution.** 74 no-ball frames at a 12.2% solid-ghost rate: sampling alone moves the
   count ±2.8. This test set can detect near-elimination; halving needs 351 no-ball frames,
   a 30% cut needs 1092.

So the defensible statement is **"arm B did not clear the bar, and it is materially worse on
the low-mount clip"** — not "more data makes ghosting worse in general". The detector result
from `pool_ab.md` stands unchanged: +5.6 pts pooled recall, 4.1σ, generalising to the legacy
six. It is a real detector improvement that the chain declines to pass through.

## Consequences

1. **Do not ship arm B.** `ballnet_v21.pt` remains the default detector.
2. **Stop scoring detector work at the detector — on either axis.** Precision (×3) and now
   recall (×1) have both failed to arrive. The next ball-side idea should be justified by a
   chain-level mechanism or not run.
3. **The bottleneck is named:** `suppress_false_locks` plus the Kalman gate. On yt_match40
   they absorb 7.5 of 9.7 points of recall. That is where a product gain would have to come
   from.
4. The SwingVision retrain question resolves itself — arm B's recipe is not shipping, so
   there is nothing to re-train to remove the overlay from. The scrub and its guard remain
   in place for every future run.
