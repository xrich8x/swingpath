---
name: ball-negatives
description: Ball detector/chain approaches already measured here — detector work is CLOSED, chain work is open, and four detector gains delivered nothing downstream
metadata:
  type: project
---

Backfilled 2026-08-27 from `docs/STATE.md` and the archived sessions.

**Rule 5 of the project: score ball work at the CHAIN, not the detector.** Four detector
gains — input resolution, `score_thresh`, localised confuser weighting, +57% data — each
cut detector error substantially and delivered **nothing** to the rendered output. Four
for four. Justify the next ball idea by a chain-level mechanism or do not run it.
**Ball-DETECTOR work is closed** by the Session L stopping rule; **chain work is open**
and as of 2026-08-27 explicitly not closed — the stopping rule did not fire.

**Measured negatives worth not re-deriving:** motion attention (**59.2%** of false locks
travel with a person, only 38.0% are static scenery — motion attention addresses the wrong
population); racquet-box negation (failed twice — COCO finds the *near* player's racquet
while the detector fires on the *far* player's); pose-proximity mining (11.4% catch at the
5% collateral ceiling — a skeleton has no racquet, 2.12 body heights away); detector fusion
(rescued **4 frames**, doubled the cost); whole-frame hard negatives; mining
`suppress_false_locks`' rejections; depth-aware Kalman process noise (made false-fire
*worse*, 19 -> 27%); raising `acquire_bound_m`; blur augmentation alone.

**What worked:** hard-negative mining + retrain (false-fire 14% -> 6.0% at flat recall);
occlusion augmentation + visibility-weighted loss (gold 82.9 -> 84.9, occluded 84.2 ->
89.7); `suppress_false_locks`; the static-lock gate; scaling every pixel threshold by
`frame_height/720`.

**Live and unresolved as of 2026-08-27:** `bounce_hypothesis` v2. v1's separation ratio
was published as 4.50:1, **withdrawn** on 2026-08-27 as a two-event denominator; at full
power over all 10 gold clips it is **9.00:1** against a >7 bar, which passes. So the
premise that the exchange rate is a property of the signal is disproved. v1 still fails on
position accuracy on one clip. **Do not cite 4.50:1.**

**Mobile note (2026-08-27):** BallNet is 1.3M params, a 9-channel U-Net at 512x288, so
~8-12 GFLOPs — genuinely cheap on the ANE. But `mobile/models/*.onnx` are exported from
the vendored **TrackNet** (360x640, 256-channel output), which is much heavier. The
already-logged model divergence now has a compute consequence: the exported model is the
expensive one. See [[coreml-ane-budget]].

**Far-end framing test (2026-08-29):** the ball's far-end problem is NOT the same as the
far player's. The player is search-limited (full-frame model literally never fires); the
ball already fires on 73-76% of far-court frames — its problem is that the chain cannot
DISCRIMINATE the survivors from confusers carrying the same kinematic signature (all 19
chain false locks have `run_len = 1`, a real ball's own signature — see
[[9-solid-ghost-balls]] via `docs/evidence/9-solid-ghost-balls.md`). The one thing that
did move solid ghosts was a MODEL SWAP (TrackNet vs BallNet, -29.5%), not a sharper look —
which is why "more resolution, applied locally instead of globally" (sketched, NOT run,
NOT gated, confidence ~25-30%) is the only ball-side idea left that isn't already closed.
Full ranking, literature check (SAHI/TOTNet/Kalman-tiny-object survey, all footage-flagged)
and the caveats in
[docs/evidence/far-end-player-and-ball-what-is-left.md](../../../docs/evidence/far-end-player-and-ball-what-is-left.md).

**The smoother innovation gate — R-calibration assessed and killed 2026-09-10.** The founder
asked whether `meas_var = 25` (σ≈5 px, a tuning guess) is miscalibrated, since the gate claims
a 0.1% false-rejection rate (`gate_chi2 = 13.8`, χ²₂ 99.9%) and measures 14-17%.
**Verdict: INSIDE the barred widen family, dead.** Four facts worth never re-deriving:
1. **The gate's REJECT population is 21 real / 28 ghost = 0.75:1 pooled** (backward-readmit
   §3). That is a HARD CEILING on any widen — admit everything and you still get 0.75:1,
   against the family's ~7:1 structural rate and its ≥3:1 pre-registered bar.
2. **Session I's "all 19 chain false locks sit 208-829 px off the track" is the WRONG
   POPULATION** for this argument — those are chain SURVIVORS. The gate's reject-ghosts sit at
   **24.0 / 30.3 / 49.8 / 386.2 px**, inside any widened radius. Do not reuse 208-829 to argue
   a widen is safe.
3. **S ≈ (1.2-1.4)·R**, because `sigma_jerk=1.0` gives Q[0,0]=0.05 px² against R=25, so P
   converges small. Scaling R by k IS a `gate_chi2` sweep by k; accept radius ≈ 18.6-21 px.
   Also: raising R lowers the Kalman gain, making the staleness that causes rejections WORSE.
4. **`D_smooth` (−11.0/−8.1 pts) IS the gate's rejection rate over span frames**, not a reset
   cascade — `pipeline.py:1460` sets `ball_seen = p is not None and not coasted`, and every
   accepted detection is emitted. Code read, no run needed.
**No `gate_chi2` or `meas_var` sweep exists in STATE** (all 78 rows read) — the question is
virgin, the intervention is not. **No raw-detection-to-click σ distribution exists anywhere in
this repo**; only a binary at 10 px (`eval_model_filters.py:199`) and ~17 anecdotal errors
(3-4 px core in backward-readmit §5, a 20-502 px tail in bounce-hypothesis-v2) — i.e. a
MIXTURE, which argues for a tight gate, not a wide one.
**What is left, outside the family:** (1) are 1-2 frame interpolated bridges actually
unmeasured? `eval_model_filters.py:201-208` already accumulates `coast_by_gap`; (2)
rejection-run COHERENCE — `rej` counts every rejection alike and the reset re-seeds at the
CURRENT frame, discarding 2; all 19 chain false locks are `run_len = 1`, so requiring a
coherent run separates by the ghosts' own measured signature. Full assessment, ranked
candidates, diagnostic and pre-registered bar:
`docs/evidence/innovation-gate-noise-calibration.md`.

Related: [[open-questions]], [[project-method-rules]]
