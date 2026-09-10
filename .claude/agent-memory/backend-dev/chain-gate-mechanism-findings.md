---
name: chain-gate-mechanism-findings
description: What seven attempts on the ball-chain smoother have established — the reflected bounce hypothesis has its own false-acceptance region, gate tightness is not the lever, the RTS backward pass is confounded with the forward gate, and rejection-run length does not separate
metadata:
  type: project
---

Seven attempts on `smooth_forecast` have now failed a pre-registered gate: `max_gap_s`,
`reset_after`, `bounce_reset`, `bounce_hypothesis` v1, v2 (`restitution_set`), the
**backward-pass re-admit** (2026-09-03) and **rejection-run coherence / M2** (2026-09-10). The durable results, so a seventh does not
re-derive them.

**The ~7:1 exchange rate is NOT a property of the signal.** Attempts 1–3 all measured
~7 real ball frames lost per ghost removed, which looked structural. `bounce_hypothesis`
lands at **9.00:1** at full power (10 clips, 1658 clicks, 272 no-ball frames) and a
single-`e` ablation at **10.50:1**. A second hypothesis genuinely beats it, so the
stopping rule built on that premise has not fired. Chain work is open.

**Gate tightness is not the lever, and the band was exonerated.** v2 removed
`restitution_band`'s y-variance inflation entirely and gated at the unmodified `S` —
strictly tighter than v1, since inflating a variance can only lower a χ². The `wrong`
rises survived on 4 of 5 clips. Do not propose another tightening or another way of
choosing `e`.

**The reflected hypothesis has its OWN false-acceptance region.** This falsifies the
design claim that "a ghost fits neither hypothesis". At every `miss → wrong` frame the
raw detection was already **20–502 px** from the human click and the reflected model
admitted it: negating `vy` moves the prediction far enough to cover a lock 502 px off
the track. A sixth attempt has to constrain **where** the reflected state may be
adopted, not how tightly it is tested.

**Second, separate failure mode: segment-restart degradation.** Accepting a bounce
inserts a segment boundary, and the RTS pass then smooths a different set of frames
together — a raw detection **0.7 px** from truth was emitted **11.3 px** off. Recovering
a frame can damage a neighbour.

**`wrong` and `fp` are the same object seen twice.** A far-off lock scores `fp` on a
no-ball frame and `wrong` on a ball frame. Any mechanism that admits more detections
raises hits and `wrong` together, so a bar of "`wrong` must not rise on any clip" may be
very hard for an admitting mechanism to clear. That is an observation for whoever writes
the next gate — **not** grounds to relax a pre-registered bar after seeing a result.

**THE RTS BACKWARD PASS CANNOT ADJUDICATE THE FORWARD GATE'S REJECTS — measured
2026-09-03, branch CLOSED** (`docs/evidence/smoother-gate-backward-readmit-separation.md`).
Distance from a rejected detection to the final RTS-smoothed track was scored against human
gold clicks on `am_hard_utr` / `yt_match40` / `yt_rally2` (TrackNet `detector_ab` caches).
Best real:ghost ratio **1.14 / 2.00 / 0.56**, pooled **0.93:1** against a >=3:1 bar; the
shuffled-label null is p = 1.000 / 0.526 / 1.000. **The nearest reject to the smoothed track
is a GHOST on 2 of 3 clips.** Mechanism, and it generalises: a ghost that continues the
model's stale motion sits ON the smoothed path, while a real detection fails a chi2 99.9%
gate essentially only when the model IS stale — and `xs[i]` at that frame is smoothed within
the SAME segment off that SAME stale model (the RTS recursion is blocked at segment
boundaries). So the backward pass is a second look at the evidence the forward gate already
got wrong. **Any future re-admit signal must come from OUTSIDE the motion model** —
appearance, detector confidence, cross-detector agreement — not from the filter's own track.

**Two code facts about `smooth_forecast` worth not re-deriving.** (1) A rejection that trips
`rej >= reset_after` is **re-seeded on that same frame** (`ball.py:968-970`, `used[i]=True`),
so the shipped code already re-admits a subset of gate rejections — 1/19, 3/16 and 8/26 of
the adjudicated rejections on those three clips. Any "re-admit" proposal must exclude them or
it is claiming credit for shipped behaviour. (2) The function has TWO
`return out, coasted, conf` statements (the `n == 0` early return); match on the newline plus
4-space indent when source-transforming it.

**REJECTION-RUN LENGTH DOES NOT SEPARATE — measured 2026-09-10, M2 DEAD BEFORE ANY CODE**
(`docs/evidence/innovation-gate-noise-calibration.md` §5.4). Contingency run-length
(1 vs >=2) x (real/ghost) on the same 49 pooled adjudicated lost rejects: enrichment
**+60.0 / +10.0 / +10.7 pp** against a >=25 pp on >=2-of-3 bar (**1 of 3**), and a seeded
shuffled-label null (1000 draws, `random.Random(20260910)`) at p = **0.105 / 0.589 / 0.585**,
pooled +23.6 pp at p = **0.135**. Not one clip reaches p <= 0.05. The one clip that clears
the separation bar rests on a runs-of-1 cell of **three**.

**THE POPULATION-SWAP TRAP HAS NOW BITTEN THE SAME FILE TWICE.** M2's whole mechanism came
from `9-solid-ghost-balls.md`: all 19 chain false locks have `run_len = 1`, so "a ghost
cannot form a coherent run". Measured at the GATE, **19 of the 28 pooled ghost rejects (68%)
sit in runs of >= 2**. Those 19 chain false locks are the ghosts that SURVIVED the whole
chain — the identical swap that made the "208-829 px" argument wrong. **A property measured
on survivors does not transfer to the gate's rejects, on any variable. Check it before
building on it.**

**M1 IS DEAD TOO, AND ITS KILL IS LOAD-BEARING** (§5.6). `seen_frac`'s rule that a coasted
frame is a guess, not a measurement (`ball.py:667-669`), was an untested empirical claim.
Tested: pooled coast error in the `"1-2"` gap bin is **19.90 px** (n=16) against a <=10.0 px
bar; only 31% land inside the 10 px recall radius. **The exclusion rule is RIGHT, so the
-11.0 / -8.1 pts are real lost balls and not an accounting artefact.** Do not re-propose
counting short bridges. Note the existing `coasted_err_px_by_gap` outputs in
`data/output/{session_i_ab/coast_,chain_ab_,coherent_}<clip>.json` are ALL BallNet
(1-2 medians 6.7 / 11.8 / 5.3) and would have PASSED — the detector matters here.

**THE RESETS HAVE NOW BEEN COUNTED, and the discarded ceiling is large** (§5.5). Per clip
**630 / 384 / 34** resets (`457 / 246 / 24` triggered by `rej >= reset_after`), discarding
**902 / 479 / 47** earlier rejections. Flipping exactly those to `seen` and re-running
`_build_match_from_events` over the same fixed spans moves mean `seen_frac`
**51.06 -> 57.55 (+6.49) / 54.79 -> 59.71 (+4.93) / 67.96 -> 71.41 (+3.45)** — i.e. roughly
40-60% of this stage's entire cost sits in frames the reset path throws away. It is a
CEILING (K2 shows run length cannot say which of them are real: 18 of 37 are ghosts), but
it is the size of the target for any future mechanism. `yt_rally2`'s smoother-stage mean
had never been published: **67.96%, on 10 shots**.

**`D_smooth` IS the rejection rate, confirmed by measurement** (§5.7). Lost gate rejections
as a fraction of ALL hit->landing span frames: **10.19% / 7.88% / 7.52%**, against the
published -11.0 / -8.1 pts. Not a downstream reset cascade.

**Two more harness facts.** (1) `tools/eval_model_filters.py` has **no cache option** — it
re-perceives from video on CUDA, so anything needing its `measure()` must replay the ladder
from a cache and call `measure()` for the binning rather than reimplement it. (2) A
source-transform run must re-read its own sha AFTER the last edit: the first draft of this
run's report quoted the sha of a superseded script version.

**Harness facts.** `tools/eval_chain_gate.py` runs off cached perception — CPU only, no
GPU, ~2 min for all ten clips. It now prints P6-input and P7. P3 (`seen_frac` shots
≥50%) needs hit→landing spans from a committed `match.json` and is not in that tool;
`real_fraction` is a closure in `pipeline.analyze_video` and must be re-derived, so
validate any re-derivation by reproducing `post_bounce_chain.md` part 3's committed
am_hard_utr **69**/120 and yt_match40 **124**/196.

**H-routing for chain A/Bs.** Scoring is a pixel distance to a human click, so it is
H-free — but `gate_ball_to_court` sits in the chain and is NOT a no-op on the gold
caches. It runs *before* the smoother and the flag under test only touches the smoother,
so both arms get identical input and **the deltas are H-clean while the levels are not**.
P3 is weaker: its hit→landing windows come from H-dependent bounce detection.

Related: [[traps-this-project-paid-for]], [[ball-detector-choice-is-split]],
[[where-authoritative-detail-lives]], [[calibration-trap-check-corners-first]].
