---
name: smoother-noise-model-is-over-dispersed
description: MEASURED 2026-09-10 — smooth_forecast's innovations are ~12x tighter than its own S predicts, P (not R) supplies 70-81% of S, and the real accept radius is 33-64 px not the ~19 px two documents derived
metadata:
  type: project
---

Measured on the three TrackNet `detector_ab` arms (`am_hard_utr`, `yt_match40`,
`yt_rally2`), n = 291 gold-real accepted frames and 8,157 / 5,834 / 777 gate-tested
frames. Source: `docs/evidence/innovation-gate-noise-calibration.md` §5.2–5.3,
raw rows in `data/output/gate_noise_diag/` (gitignored).

**The gate statistic is NOT chi-squared-2.** Median `d2` on gold-confirmed real
ACCEPTED frames is **0.265 / 0.122 / 0.104**, pooled **0.113** — against chi²₂'s median
of **1.386**. That is ~12x LOW. Meanwhile pooled p90 is **4.776** against chi²₂'s
**4.605** — within 4%. A distribution whose median is 12x low and whose p90 is exactly
right is a **mixture**: a very tight core plus genuine outliers. Not a mis-set sigma.

**Why: S is over-stated, so every consequence runs the opposite way to intuition.**
`meas_var = 25` is not too small; the modelled uncertainty is too big. So "raise
`meas_var` to admit more real detections" is not merely a widen (which §1 of that file
already barred on a 0.75:1 census) — it pushes an already-over-dispersed statistic
further from calibration.

**P dominates S, not R. This refutes a DERIVED claim that two documents leaned on.**
Measured `R[0,0]/S[0,0]`: median **0.187 / 0.257 / 0.304**, and it never exceeds
**0.31** on any frame of any clip. The prior covariance supplies 69–81%. The published
derivation said R supplies 70–85% — exactly inverted. Consequence: scaling `meas_var`
by k scales S by `1 + (k-1)·(R/S)`, roughly a QUARTER of the assumed multiplier.

**The accept radius is ~1.8x wider than believed.** `sqrt(13.8 · S[0,0])` median is
**64.4 px** at 1080p (`am_hard_utr`) and **36.7 / 33.7 px** at 720p — not the 18.6–21 px
derived in two places. So the four ghost rejects at 24.0 / 30.3 / 49.8 / 386.2 px are,
three of them, INSIDE the median accept radius already. They were not rejected for being
far away; they were rejected at instants when P happened to be tight or the innovation
pointed the wrong way. **A radius change is not the lever on this stage.**

**How to apply.** If anyone proposes touching `meas_var`, `gate_chi2` or `sigma_jerk`,
these numbers are the starting point and nothing needs re-measuring. The implied next
lever is `Q` / `sigma_jerk` — but Q has a measured negative already (`ball.py:686–692`,
false-fire 19 -> 27% when loosened; tighten-only held flat and bought +1.2 pts far-court
hit@10), and a TIGHTEN cannot buy coverage, so it is not a candidate for the
-11.0 / -8.1 pt `seen_frac` cost. Recorded because no file previously held it.

Related: [[chain-gate-mechanism-findings]], [[traps-this-project-paid-for]],
[[speed-error-is-geometry-not-detection]].
