---
name: gate-noise-diag-k1-k3-verified
description: K3 and K1 of the innovation-gate diagnostic independently CONFIRMED 2026-09-10; two defects found (a run-splitting undercount, and yt_match40's calibration silently changing between runs so its "reproduces the published baseline" claim is false)
metadata:
  type: project
---

Audited `docs/evidence/innovation-gate-noise-calibration.md` §5 (backend-dev built the
harness AND graded its own output with it). My section is §6 of that file. Raw:
`data/output/gate_noise_diag/` (gitignored); my harness was scratchpad-only.

**Both headline verdicts stand.**

- **K3 CONFIRMED, number corrected UPWARD.** Discarded frames 914 / 492 / 48 (mine) vs
  902 / 479 / 47 (theirs) = exactly `2 x resets_by_rej` (457/246/24). Points of mean
  `seen_frac` +6.557 / +5.142 / +3.534 vs +6.492 / +4.926 / +3.450. Bar was >=1.0 pt →
  cleared 3.5x–6.6x. Base means 51.060 / 54.785 / 67.963 reproduce theirs to 3 dp.
- **K1 CONFIRMED.** Pooled median `d2` 0.11272 (n=291) vs 0.113, 12.30x below chi2_2's
  1.3863. R/S 0.1871 / 0.2571 / 0.3036; accept radius 64.41 / 36.63 / 33.71 px @source.

**Lessons worth keeping, beyond this file:**

1. **A "reproduces the published baseline" claim must check the POPULATION, not just the
   number.** `yt_match40`'s 54.785 vs published 54.95 looked like a 0.16 pt match — but
   the published run had **186 shots** and this run has **86**, because
   `pipeline.calibrate_video` resolved a *different court from the same pts file*
   (`manual+snap` 9.112 px / hfov 26.43° on 2026-09-02 vs `manual+snap-clay` 0.011 px /
   hfov 91.28° on 2026-09-10). Two different means agreeing by coincidence. Always read
   `n_shots` + `calibration_source` + `hfov` out of `data/output/speed_coverage/<clip>.
   <arm>.json` before calling anything a reproduction. **This calibration instability is
   unresolved and is the most important thing I found.**
2. **Post-hoc reconstruction of a counter's runs from its recorded values is a bug
   generator.** `gate_diag.py` rebuilt rejection runs from `rej_ctr` after the fact;
   because `rej_ctr` is also recorded on no-detection frames (where `rej` merely holds),
   runs containing a detection gap got split and the first rejection was orphaned. Count
   frame-by-frame **in trace order** instead. (Error was one-directional, so the verdict
   survived — but it need not have been.)
3. **`quant()` in these harnesses is NEAREST-RANK, not linear-interpolation.** Only bites
   on even n: `am_hard_utr` K1 median is 0.264 nearest vs 0.176 linear; M1's `"1-2"` bin
   median is 19.90 nearest vs 17.16 linear. Always report both when n is even.
4. **A censoring worry is testable in one line.** "Accepted d2 is truncated at 13.8 so the
   median is biased" — a true chi2_2 has 0.10% of mass above 13.8, so censoring moves its
   median 1.3863 → 1.3870. Simulate before arguing.
5. **Use a sign test to establish a SIGN.** 238/291 below chi2_2's median, p = 1.9e-29,
   and it clears on each clip separately (24/32, 83/106, 131/153) with the required-n
   quoted (22/32, 62/106, 88/153). A median ratio can be moved by outliers; a sign test
   cannot.
6. **`ball_seen` cannot move a span** — `pipeline.py` consumes it only at `real_at`
   (:1712) → `seen_frac` (:1862) and `real_landing` (:1849/:1851), both AFTER `h`/`land`
   are set (:1744/:1753) and `span_sink.append` (:1885) is unconditional. Verified
   empirically too (shots 90→90, 86→86, 10→10, span lists identical).
7. **n=16 kills a bar but does not establish its converse.** M1's pooled `"1-2"` median
   19.90 px vs a <=10 px bar is a valid pre-registered KILL, but a sign test against
   "true median = 10" gives p = 0.45 and you would need n >= 44 at the observed rate. Say
   "not contradicted", not "and it is right".

See also [[synth-truth-harness-reproducibility]] (classifier-shape numbers reproduce, fine
per-clip digits do not) and [[int8_parity_verified_but_close_race_threshold_is_post_hoc]]
(headline confirmed, supporting mechanism corrected) — same shape of outcome as this run.
