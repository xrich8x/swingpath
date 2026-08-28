---
name: line-call-margin-curve
description: Measured line-call accuracy vs margin-from-line by camera height (2026-08-28) — where the "too close to call" crossover actually sits
metadata:
  type: project
---

2026-08-28, pm queue item 5: measured (not built) call accuracy as a function of
margin-from-line at each camera height, via `tools/synth_truth.measure()` driven
directly (bypassing `height_curve.py`'s cumulative-only `near_m` report so bins are
EXCLUSIVE). n=40,000 synthetic flights/setup, seed=0, fps=30, dropout=0.30, pixel
noise 2px@720p (shipped defaults), CPU-only venv (`backend/.venv`, torch cu-available
False) with `CUDA_VISIBLE_DEVICES=""` — backend-dev held the GPU per that night's
instruction.

**Measured against:** exact simulated truth (drag+gravity+Magnus) projected through
each camera, `analytics.line_call` run on the noised/dropped-out result — the
compliant reference per rule 11, no HUD, no human labels.

**Headline finding — both real amateur mounts (demo30 1.38 m, am_hard_utr 1.74 m):**
in the [0, 0.10) m band from a line, call accuracy is AT OR BELOW the majority-class
floor (demo30: 50.6% vs 51.7% floor in [0,0.05), 51.8% vs 55.3% in [0.05,0.10);
am_hard_utr: 51.1%/51.7%, 52.8%/55.3%). Accuracy clears the floor starting in
[0.10,0.20) m (demo30 56.5% vs 53.4%, +3.1pp — marginal; am_hard_utr 61.9% vs 53.4%,
+8.5pp) and clears it comfortably from [0.20,0.30) onward (+8.2pp / +15.7pp), staying
comfortably clear at every wider band tested up to 2.0 m.

**Recommended band width: 0.20 m (20 cm).** Reasoning: below it, real-mount accuracy
is provably no better than guessing; the [0.10,0.20) transition zone is a marginal
gray area (barely above floor for the worse mount) that the conservative read folds
into the refused band, given the asymmetric cost of a confidently wrong close call.
0.15 m is a defensible less-conservative alternative — the founder's call, not mine.

**Refusal rate at 0.20 m:** 2.2% of ALL simulated bounces, but 39.0% of "close" bounces
(within 0.5 m of a line — the same near_m=0.5 population CLAUDE.md's existing 54.0%/
56.2% figures use). At 0.15 m: 29.5% of close calls refused; at 0.25 m: 48.7%. This is
the number the founder needs alongside the crossover — a 20 cm band is not free, it
silences roughly two in five of the calls that were close enough to matter.

**Height ladder (controlled sweep, everything but height fixed):** a true 1.0 m mount
never clears the floor by a solid margin ANYWHERE in 0–2 m from a line — consistent
with CLAUDE.md's existing "1.0 m is worse than answering in every time" verdict, now
shown to hold at every margin, not just the pooled 0.5 m figure. By 3.0 m the
unreliable zone shrinks to under ~0.10 m; by 5.0 m+ mounts clear the floor from 0 m.
The controlled-sweep 1.75 m row reproduces the real am_hard_utr numbers almost exactly
(51.1/51.7, 51.8/55.3, 60.2/53.4 vs the real clip's 51.1/51.7, 52.8/55.3, 61.9/53.4) —
cross-validates that the real-mount numbers are representative of mount height, not an
artifact of that one clip's lens/setback.

**Cross-check:** the near_m=0.5 cumulative floor this run measured (56.7%, n=1867) is
close to CLAUDE.md's pre-registered 56.2% — the measurement pipeline reproduces the
existing landmark number before being trusted for the new one.

**Scope note:** this is read-only measurement, not a build. `live.py` already has a
baked-in `line_margin_m = 0.05` (5 cm) that this data shows sits INSIDE the unreliable
zone — worth flagging to whoever builds the refusal band, not a discrepancy to fix
tonight. No code was touched; no evidence file or STATE row was written to the repo
(this agent does not write to the codebase — see [[qa-does-not-write-to-codebase]]).
The full per-band table (9 exclusive bins x 10 setups) and per-width refusal-rate table
are in this session's report; regenerate with the scratchpad script pattern (drives
`synth_truth.measure()` directly, bins by `line_dist_m` exclusively) if needed again.
