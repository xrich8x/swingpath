# Ball-chain intervention — the pre-registered gate

> Evidence for the `ball-chain-gate` row in [docs/STATE.md](../STATE.md) (Open).
> **Written 2026-08-26, BEFORE any code was touched.** Nothing here may be
> loosened after a result is seen (hard rule 2). A failed gate stays failed.

## What is being attacked, and what is not

**Not the detector.** Ball-detector work is closed by the Session L stopping rule,
and *"Expecting a detector gain of ANY kind to reach the product"* is four for four
in the dead-end table. This gate does not admit a detector change.

The target is the **chain**, which is the best-measured open thing in the repo:

| stage | am_hard_utr | yt_match40 |
|---|---|---|
| raw detector | 75.5% | 79.3% |
| `rectify` | 72.1 | — |
| `suppress_false_locks` | 64.9 (**−7.2**) | (**−8.1**) |
| court gate | 64.9 (**exactly zero**) | (**zero**) |
| `smooth_forecast` | **52.9 (−12.0)** | **59.7 (−9.7)** |
| shots clearing the ≥50% `seen_frac` bar | **106 of 120 → 69** | **182 → 124** |

The detector already covers **88%** of shots on the target clip and **58%** survive.
`smooth_forecast` and `suppress_false_locks` own ~85% of the loss. The court gate is
not a lever and must not be touched to make a number move.

## Why a coverage gate is not enough — the thing the three failures had in common

| attempt | result |
|---|---|
| `max_gap_s` at 60 fps | clean on yt_rally2, collapsed on am_hard_utr |
| `reset_after` 3 → 2 | PASSED all three bars on yt_match40, FAILED on yt_rally2 |
| `bounce_reset` | failed on all 3 clips; best case 1.4 pts short of `real_landing` +5 |

All three moved a threshold that admits **both** real ball and ghost. Two
independent routes — the `blocked` mask and `max_gap_s` — measured the same
exchange rate of **~7 real ball frames lost per ghost frame removed**, which means
the trade looks *structural*, a property of the signal rather than of any one
filter. Riding that line in the favourable direction buys coverage and pays in
ghosts; it is not a fix, and the previous gates could not tell the two apart
because they only asked whether coverage went up.

So this gate adds a bar that a threshold move cannot pass by construction.

## The gate — all bars, all three calibrated clips

Clips: **`am_hard_utr`** (1.74 m amateur mount, the target footage), **`yt_match40`**,
**`yt_rally2`**. All three have perception caches; all three must be run.

**P1 — chain recall must not fall.** ≥ **−0.0 pts pooled**, and ≥ **−2.0 pts** on
every clip individually.

**P2 — solid ghosts must not rise on any clip.** Pooled baseline is **9**. A rise on
one clip is a fail even if the pooled number holds.

**P3 — trusted-speed shots must rise.** On `am_hard_utr`, shots clearing the ≥50%
`seen_frac` bar must go **69 → ≥77** (+8, about a third of the 37 the chain loses).
On `yt_match40`, **124 → ≥132**.

**P4 — SEPARATION, the new bar.** If the intervention adds any ghost frames, it must
recover **more than 7 real ball frames per ghost frame added**. At or below 7:1 it is
riding the known structural trade and **FAILS regardless of what P1–P3 say**. An
intervention that adds zero ghosts and recovers real frames passes P4 trivially —
which is the shape a genuine separation mechanism should have.

**P5 — power (trap T09).** The ghost guard must rest on **≥74 no-ball frames**, not
the 24/26 the failed runs used. Below that, "ghosts did not rise" is underpowered
and must be reported as *failed to detect a change*, never as *no effect*.

**P6 — replication across density.** A pass on one clip and a collapse on another is
a **FAIL**, not a partial win. The optimal gap policy scales with detection density
(measured twice, by independent routes), and these three clips span the range.

## Stopping rule

**If a mechanism explicitly designed to SEPARATE real from false — not to loosen a
threshold — still lands at or below the ~7:1 exchange rate, then the exchange rate
is a property of the signal and not of the filter, and smoother/suppression chain
work closes the way ball-detector work closed.** Record it in *What has not worked*
and stop. This is the fourth attempt on this stage; it is not open-ended.

## What "one variable" means here

`--seed` on both arms, `recipe_stamp` on any checkpoint, and the three caches rebuilt
under the **same device and threshold** — the existing caches were deliberately built
on cuda at thresh 0.5 so the three are comparable rather than a device confound. A
run that mixes `.venv` and `.venv-train` numbers is invalid before it is read: those
two stacks are an opencv MAJOR version apart, and no experiment here has ever
separated device from libraries.

## Measured with

`tools/eval_gold.py`, `tools/ball_perception.py`, and the chain counters already used
for `data/output/post_bounce_chain.md` (part 3) and `data/output/smoother_coherence.md`.
No new scorer — a scorer written for one experiment is how this project understated a
tracker for a whole session (T04).
