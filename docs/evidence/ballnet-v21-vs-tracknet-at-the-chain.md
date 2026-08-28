# BallNet v21 vs TrackNet, scored at the CHAIN

> Evidence for the `ballnet-v21-vs-tracknet-at-the-chain` row in [docs/STATE.md](../STATE.md).
> Measured 2026-08-28. Artifacts: `data/output/detector_ab_chain.json`,
> `data/output/detector_ab_chain_nogate.json`, `data/output/detector_ab/`.

## Why this was run

Two detector-level verdicts in STATE point opposite ways — pooled hit@10 favours
BallNet (60.8 vs 57.9), F1@4 favours TrackNet, which wins 9 of 10 clips. Rule 5
says ball work is scored at the chain, because four detector gains in a row each
cut detector error and delivered nothing to the rendered output. Neither model
had ever been scored there. `mobile/models/*.onnx` are TrackNet exports while the
shipped desktop default is BallNet v21, so the divergence is live and the answer
decides which model the first scarce Mac session spends itself exporting.

## What was measured against what

**Human gold clicks on the 10-clip gold set.** A hit is a post-chain track point
within 10 px of a click. A **ghost** is a frame a human marked *no ball* on which
the post-chain track still carries one — **solid** if the detector put it there,
**faded** if `smooth_forecast` interpolated it. `annotate.py` draws a ball iff
`ball_px[i] is not None` on this same track, so a solid ghost is a frame where
the rendered video paints a solid disc over a human's "no ball". Converting a
solid ghost to a faded one removes nothing, so **solid is the number**.

One variable: `--ball-model`. Identical clips, frame steps, device, score
threshold, bgsub, and tracker court gate (off) on both arms.

## Homography routing, stated because two calibrations are compromised

`yt_match40` is confirmed wrong (trap T23 — all four clicked corners are off any
court line) and `am_hard_utr` is visibly skewed on the right.

| Metric | Routes through H? |
|---|---|
| solid ghosts, all ghosts, recall | **No** — see below |
| `far_px` (top 36% of frame) | No |
| `far_geo` (court-scale band) | **Yes** |
| speeds, line calls, `ball_track` | **Yes** |
| shots, rallies | No |

The ghost and recall numbers are H-free **as measured, not by assumption**. The
only H-dependent stage in the ladder is `gate_ball_to_court`, and it removes
**zero locks on all seven calibrated clips in both arms — 14 of 14**, at fitted
hfov from 20.7° to 93.7°. Re-running the whole comparison with `--no-gate`
produced a payload **byte-identical except the flag**. So the primary verdict
cannot rest on either broken calibration.

That the court gate costs exactly zero is **not new** — it is already recorded for
speed coverage on `am_hard_utr` and `yt_match40`
([speed-coverage-is-chain-shaped-and-the.md](speed-coverage-is-chain-shaped-and-the.md),
reproducing Session G part 3). What is new is the breadth: **seven clips, two
detectors, every fitted hfov in the gold set, zero locks removed anywhere.** The
gate is not merely cheap on the clips it was measured on; on this evidence it is
inert. That is what makes it usable here as a guarantee of H-independence rather
than as a hope.

## The ladder

Mirrors `pipeline.analyze_video` exactly, `remove_outliers` included:

    remove_outliers -> rectify_track -> suppress_false_locks
                    -> gate_ball_to_court (calibrated clips only)
                    -> smooth_forecast

`tools/chain_cache.py`'s `run_chain` omits `remove_outliers` and would score the
same caches differently. `backend/tests/test_detector_chain_ab_ladder.py` pins the
tool's ladder to the pipeline's by AST comparison — stage order, tuning literals,
`res_scale`, and the `H is not None` guard — so the eval cannot drift from the
thing it claims to measure (trap T15). Verified it fails on both the dropped-stage
and the changed-constant mutation.

## Chain result — full power, 10 clips, 1658 clicks, 272 no-ball frames

| clip | cal | no-ball | solid B | solid T | d | recall B | recall T | d |
|---|---|---|---|---|---|---|---|---|
| am_hard_utr | Y | 24 | 10 | 7 | **-3** | 42.2% | 36.7% | -5.5 |
| gold_shell | n | 55 | 20 | 10 | **-10** | 57.6% | 68.5% | +10.9 |
| gold_clay | n | 7 | 2 | 1 | -1 | 46.8% | 58.6% | +11.8 |
| gold_am | n | 32 | 10 | 4 | **-6** | 57.5% | 44.2% | **-13.3** |
| yt_rally2 | Y | 26 | 5 | 11 | **+6** | 59.7% | 60.1% | +0.4 |
| yt_match40 | Y | 24 | 5 | 9 | **+4** | 53.3% | 59.2% | +5.9 |
| gold_UHf0LeMU2pg | Y | 9 | 4 | 3 | -1 | 52.4% | 56.0% | +3.6 |
| gold_sAjkpeRq4P4 | Y | 33 | 6 | 5 | -1 | 36.4% | 31.1% | -5.3 |
| gold_uR5q2cSM6AY | Y | 32 | 21 | 6 | **-15** | 54.6% | 39.3% | **-15.3** |
| gold_L73ep7JHiJ4 | Y | 30 | 5 | 6 | +1 | 50.6% | 52.4% | +1.8 |
| **pooled** | | **272** | **88** | **62** | **-26 (-29.5%)** | **52.4%** | **51.9%** | **-0.5** |

All ghosts (solid + faded) 125 -> 83. Hits 869 -> 861, so **8 hits bought 26 solid
ghosts — 0.31 hits per ghost removed.**

For scale, the two prices this repo has already paid: the bounce hypothesis
gained ~7 real hits per ghost admitted (the "structural exchange rate"), and
shrinking the smoother gap traded ~1:1 — **and only ever moved FADED ghosts, with
solid stuck at 9 regardless.**

**Only 18% of solid-ghost frames (23 of 127) fire on both arms.** The two models
fail on largely disjoint frames. That is the signature of a different model, not
of a shifted operating point — which matters, because TrackNet also fires 13-21%
fewer raw locks than BallNet on 9 of 10 clips.

## What this settles, and what it does not

**It answers an open STATE question.** *"Whether a better detector can reach the
ghost ball at all"* — yes. Four **parameter-level** detector gains (input
resolution, `score_thresh`, localised confuser weighting, +57% data) reached
nothing. A wholesale **model swap** moves solid ghosts by 26 at flat recall. The
absorbing stages are not a wall against every detector change; they are a wall
against retuning the same detector.

**It does not settle the operating-point question by new measurement.** The
caches store no per-detection score, so BallNet cannot be re-thresholded offline
to match TrackNet's lock rate. The confound is bounded by existing evidence
rather than eliminated: `score_thresh` is already recorded as one of the four
detector moves that changed the detector and nothing downstream, so a threshold
move alone is not a plausible route to -26 solid ghosts.

**The pooled recall is a cancellation, not a stability.** It hides +20 hits on
`gold_shell` against -24 on `gold_am` and -25 on `gold_uR5q2cSM6AY`. Read the
rows.

**Clips disagree in sign on the product metric.** Weighting one ghost as seven
hits, TrackNet wins 6 of 10; at 1:1 it wins 5 of 10 with pooled utility +18. The
verdict is weight-dependent and there is no measured weight.

**Secondary, detector-level, reported only because they were asked for:**
`far_px` recall (H-free) 53.3% -> 53.8%; `far_geo` (H-dependent) 50.5% -> 48.9%.

## Product half — full pipeline, both arms, calibrated clips

Every row below except shots and rallies routes through the homography. Both arms
share the same H, so this is a valid A/B and **not** an accuracy statement.

| metric | clip | BallNet v21 | TrackNet | d |
|---|---|---|---|---|
| shots | yt_rally2 | 12 | 10 | -2 |
| **speed_confident (count)** | yt_rally2 | **7** | **5** | **-2** |
| call_confident | yt_rally2 | 3 | 2 | -1 |
| ball_track points | yt_rally2 | 252 | 231 | -21 |
| shots | gold_UHf0LeMU2pg | 43 | 39 | -4 |
| **speed_confident (count)** | gold_UHf0LeMU2pg | **22** | **22** | **0** |
| call_confident | gold_UHf0LeMU2pg | 16 | 14 | -2 |
| ball_track points | gold_UHf0LeMU2pg | 932 | 879 | -53 |

**Report the absolute `speed_confident` count, never the percentage.** On
`gold_UHf0LeMU2pg` the pct *rises* 51.2% -> 56.4% while the count is identical at
22, purely because the denominator shrank by four shots. A detector is not better
for emitting fewer shots.

**There is no shot-count ground truth**, so 43 -> 39 cannot be scored as better or
worse. The only instrument that adjudicates an emitted event is `event_audit.py`,
which runs on `yt_rally2` alone (label density; `am_hard_utr` is 5.5% adjudicable
and unmeasurable):

    phantom hits      BallNet 1/8   TrackNet 0/6
    phantom landings  BallNet 1/4   TrackNet 1/5

The raw count moves by **1**. The tool's own stated power bar is that a count must
move by **>= 3** before a change may be claimed. **event_audit is INDETERMINATE
here and must not be spent as a win for either model.**

## Verdict

**Split, and it does not justify a switch.**

- TrackNet wins the ghost half decisively and cheaply: **-26 solid ghosts (-29.5%)
  for 8 hits**, on disjoint failure frames, H-free, at full power.
- BallNet wins or ties the product half on **both** clips measured end to end:
  more speed-confident shots (7 vs 5; 22 vs 22), more confident line calls, a
  longer drawn trail.
- `event_audit`, the one instrument that adjudicates emitted events, is
  underpowered and separates nothing.

No gate was pre-registered for this comparison. It is a measurement to inform an
export decision, not a pass/fail experiment, and it is reported as one. **The
shipped desktop default is unchanged.**

## Consequence for the first Mac session

The divergence — mobile bundling TrackNet while desktop defaults to BallNet — is
**not** resolved in BallNet's favour by this evidence.

- TrackNet already has an ONNX export in `mobile/models/`; a Core ML conversion
  starts from something that exists.
- **BallNet v21 has no Core ML export path at all today.** Building one is a real
  line item — a 512x288 3-frame-stack heatmap CNN needs a fixed-shape Core ML
  conversion and ANE validation, and it must be scoped before a borrowed Mac is
  on the clock, not discovered on it.

Recommendation: export **TrackNet first**, since it is already the mobile
artifact and the chain evidence gives no product-level reason to prefer BallNet.
Treat a BallNet Core ML export as a scoped follow-up, and settle the divergence
by measuring both on device rather than by inheriting the desktop default.
