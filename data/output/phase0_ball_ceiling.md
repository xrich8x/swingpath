# Phase 0 — where is the ball ceiling, and does raising it reach the product?

Two questions, asked before spending any human labelling time:

1. How much far-court recall is recoverable by fixing what the detector *sees*?
2. Does far-court recall convert into product value, or does E3f's "per-frame
   recall has stopped being the bottleneck" still hold?

**Gates, pre-registered.** A — a resolution change must lift pooled `far_px`
(the tool's designated resolution-comparable metric) by ≥5 pts without costing
>2 pts overall recall or adding >5 pts false-fire. B — with recall lifted, at
least one product number must improve and none may regress.

---

## 1. The detector IS resolution-starved. Gate A passes, hugely.

BallNet is fully convolutional, so it runs at any input size with **no
retraining** (`BALLNET_INPUT` env hook, same pattern as `BALLNET_WEIGHTS`).
Scored on all 6 gold clips, 1201 human ball clicks:

| detector input | recall | far_px | far_geo | false-fire |
|---|---|---|---|---|
| **512x288 (shipped)** | 69.4% | 68.8% | 72.5% | 34.8% |
| 640x360 | 76.2% | **77.0%** | 80.6% | 39.7% |
| 768x432 | 77.9% | 77.4% | 81.5% | 42.6% |

**+8.2 points of far-court recall for free.** And threshold is a free sweep
(the peak position is threshold-independent), so at 640x360 there are operating
points that dominate the shipped one outright:

| | recall | false-fire |
|---|---|---|
| shipped 512x288 @0.50 | 69.4% | 34.8% |
| 640x360 @0.60 | **74.8%** | 34.8% |
| 640x360 @0.80 | 69.8% | **20.6%** |

Same precision for +5.4 recall, or same recall for −14.2 false-fire. Take your pick.

**WHY THE INPUT IS SMALL, since it looks like an oversight and is one:** 512x288
is a training-time convenience inherited from TrackNet's 640x360, never chosen
against the footage. A far ball is ~3.9 px in a 720p frame (farcourt_probe, E2);
at 512 wide it reaches the net at **1.6 px** — *smaller* than the 2.0 px the
640-wide TrackNet saw. It is also scale-invariant to the source, so **recording
at 1080p or 4K currently buys nothing**: the extra pixels are thrown away before
the network sees them.

## 2. It does not reach the product. Gate B FAILS on both clips.

FULL chain, against the same human labels:

**yt_rally2** (3.31 m camera, dense detections)

| config | false-fire | ghosts | recall | far_geo |
|---|---|---|---|---|
| **shipped 512x288 @0.50** | **23.1%** | **6** (5 solid) | **72.5%** | **74.3%** |
| 640x360 @0.50 | 30.8% | 8 (7 solid) | 72.5% | 73.7% |
| 640x360 @0.60 | 30.8% | 8 (7 solid) | 70.9% | 72.6% |
| 640x360 @0.80 | 23.1% | 6 (5 solid) | 70.2% | 72.1% |

**am_hard_utr** (1.74 m phone, 1080p — the target footage)

| config | false-fire | ghosts | recall | far_geo |
|---|---|---|---|---|
| **shipped 512x288** | **25.0%** | **6** (1 solid) | **54.4%** | **60.3%** |
| 640x360 | 33.3% | 8 (5 solid) | 46.7% | 52.1% |

**The shipped setting dominates every variant on both clips.** The detector's
precision gain is absorbed — the chain was already removing those false fires —
and its recall gain arrives as *extra solid ghosts* (5 → 7, and 1 → 5).

So: **raising detector input resolution is a MEASURED NEGATIVE end to end**, and
E3f's finding stands. Per-frame detector quality is not the product bottleneck.

(Caveat: on am_hard_utr both arms score the ~51% even-frame subset, since that
clip's gold is 48.6% odd and the shipped step skips them. Paired, so the
comparison holds; the absolute recall understates.)

## 3. What the run revealed instead: the ghost source differs by clip

Stage by stage on the low-camera clip:

```
tracker gates only      37.5% false-fire   9 fires
+ suppress_false_locks   4.2% false-fire   1 fire     <- suppression is doing the work
+ kalman smoother       25.0% false-fire   6 fires    <- 5 of them FADED
```

| clip | dominant ghost |
|---|---|
| yt_rally2 (dense detections) | 5 **solid** — the detector firing on real objects |
| am_hard_utr (sparse, low camera) | 5 **faded** — the smoother bridging a gap |

## 4. The gap policy is a binary choice, and 0.4 should stay

Pooled over both native-60fps calibrated clips (433 ball / 79 no-ball frames):

| gap | recall | ghost frames | solid | faded |
|---|---|---|---|---|
| 0.10 s | 60.3% | 11.4% | 9 | **0** |
| 0.20 s | 62.3% | 17.7% | 9 | 5 |
| 0.30 s | 65.8% | 20.3% | 9 | 7 |
| **0.40 s (shipped)** | **67.0%** | 21.5% | 9 | 8 |
| 0.60 s | 68.3% | 25.3% | 9 | 11 |

0.10 → 0.20 costs 6.3 pts of ghosting for 2.0 of recall; 0.20 → 0.40 buys 4.7
for 3.8. So the middle is dominated — **once you leave 0.10 you may as well go
to 0.40.**

**And 0.10 is the wrong end.** At 60 fps, 60.3% recall means the ball is drawn on
36 of every 60 frames *during a rally*. Cutting the bridge does not remove
"insane", it RELOCATES it — from an occasional phantom in dead time to a
strobing ball while the point is being played, which is on screen while the user
is actually watching. **0.4 stays.**

Also corrected: single-digit false-fire is NOT reachable by tuning. 9.4% was the
low-camera clip alone; **pooled the floor is 11.4%**, because the 9 solid ghosts
are the detector and no downstream knob touches them.

---

## Verdict, and the redirection it forces

**SOLID GHOSTS ARE 9 AT EVERY SETTING** — across detector threshold, smoother
gap, input resolution, pose proximity and racquet negation. Six independent
attempts. They are the detector firing on real objects: racquet 31%, player 28%,
fence/line/background 38%.

Which means the labelling plan and the product goal were mismatched:

| goal | needs | was planned |
|---|---|---|
| **false fire down** | **hard negatives** — frames it fires wrongly on | far-court positives |
| recall up | far-court positives | yes |

**Far-court labelling improves misses. It cannot reduce false fire.** It remains
the right lever for recall, but it is not the lever for the stated product goal.

## Next candidate, and why this one is different

`suppress_false_locks` is *already* a high-precision false-fire detector: it takes
am_hard_utr from 37.5% to 4.2%. Its REJECTIONS are a ready-made hard-negative
pool, and unlike pose proximity and racquet negation it is proven to work at
runtime.

**The danger is explicit and must be measured, not assumed:** suppression also
costs 5.4–10 pts of recall, so some of what it rejects is real ball. Training on
those would teach the detector to go blind — the exact opposite of the goal.

Scored on the SAME populations and the SAME pre-registered gate as the two prior
miner failures (catch >= 60% of human-classified false locks at <= 5% collateral
on human ball clicks), so the three are directly comparable:

### RESULT: gate fails, and the first estimate was wrong

**WITHDRAWN — the 77.3% first recorded here.** It was computed as a set difference
between `g_falselocks_raw.json` and `f_falselocks_chain.json`. But "chain" in that
file is the FULL chain — tracker gates, rectify, suppression AND the court gate —
so it credited `suppress_false_locks` with every rejection the whole ladder makes.
The tracker's own gates do most of that work. Attributing it to suppression was an
over-attribution, and the corrected figure is less than half of it.

Measured properly by `tools/eval_suppress_mining.py`: the two suppression tests run
in ISOLATION (`suppress_false_locks(tests=...)`) over contiguous windows around each
target frame, on all six clips at each clip's shipped frame step. Collateral counts
only frames where the raw detector had ALREADY found the human's ball within 10 px —
rejecting an already-wrong lock is not collateral, it is the point.

| criterion | catch (person-attached) | collateral |
|---|---|---|
| pose proximity | 11.4% | 5% ceiling |
| racquet box | **54.5%** | 4.5% |
| suppression — persistence only | 7.5% | 5.7% |
| suppression — **min-segment only** | 32.5% | **2.4%** |
| suppression — both (shipped) | 40.0% | 8.1% |

Populations: 40 person-attached false locks, 803 correctly-located ball frames.

**GATE FAILS on all three.** Catch tops out at 40.0% against a 60% bar.

Two things are still worth keeping:

- **Persistence is nearly useless against person-attached confusers** — 7.5% catch
  for 5.7% collateral, i.e. it costs more real balls than confusers it catches.
  Expected in hindsight: persistence detects things that hold still, and these move.
  It earns its place against fixtures and nowhere else.
- **Min-segment has the lowest collateral of anything tested — 2.4%**, less than half
  the ceiling, while catching 4x what persistence does. It is also the only criterion
  reasoning about HOW a lock moves rather than where it is.

### The gate may be the wrong gate — but it does not get moved retroactively

That 60%/5% gate was written for a runtime FILTER, where catch is what matters
because an uncaught false fire reaches the screen. **Mining has different
economics:** you do not need to catch every confuser, you need what you DO mine to
be genuinely not-ball. The deciding quantity is the PURITY of the mined pool, and
this experiment did not measure it — collateral is a rate over ball frames, not the
composition of the rejected set.

So min-segment may still be a viable miner while failing this gate. **That is a new
question and it needs a NEW pre-registered gate**, not a reinterpretation of this
one. Moving a gate after seeing the result is the specific failure the method
section exists to prevent, and Session G part 4 stayed failed at 54.5 against 60 for
exactly this reason.

### Where that leaves automatic mining

Three distinct criteria have now failed: position relative to a skeleton, position
inside a racket box, and trajectory plausibility. They fail differently, which is
itself informative — there is no cheap automatic signal that separates a swung
racquet from a ball, because at 2-4 px on an arc it genuinely resembles one.

The remaining route is **human confirmation of a pre-filtered pool**, and min-segment
is the best pre-filter available (2.4% collateral). That is a much smaller ask than
far-court labelling: the candidates are already identified, and the judgement is
"ball or not" at a glance rather than locating a 2 px object.

---

## Gate C — mined-pool purity. Also fails, and it names the root cause.

Hard negatives in `train_ballnet.py` are WHOLE-FRAME all-zero targets, so a mined
frame is contaminated if it contains a ball anywhere. Purity therefore depends on
the BASE RATE of ball-present frames — and the gold set's 1201:204 ratio is a
sampling artefact, not a clip's composition. The base-rate-independent enrichment
is the number that transfers.

**Measured base rate of the actual training clips: 88.5% ball-present**
(26,293 labelled ball frames vs 3,409 no-ball). These are extracted rally clips.

| test | P(kill \| ball) | P(kill \| no-ball) | enrichment | purity @88.5% |
|---|---|---|---|---|
| persistence | 5.2% | 7.4% | 1.4x | 15.7% |
| min-segment | 5.0% | 29.6% | **6.0x** | **43.7%** |
| both | 10.1% | 37.0% | 3.7x | 32.2% |

Gate C required enrichment >= 10x AND purity >= 95%. **Both fail.** At the real
base rate a mined pool would be over half real-ball frames — training the detector
to see nothing on frames that contain a ball.

### The root cause, which is the same for every failure in this document

Every route tried has died on the same structural fact:

- **dead-time frames** are pure negatives but contain no confusers (already a
  measured negative — "the wrong negatives")
- **confuser-rich frames** are frames with tennis being played, which are 88.5%
  the frames that also contain a ball

**The whole-frame negative format forces a question about the FRAME when the
useful question is about the LOCATION.** A frame holding both a ball and a
racquet-fire is unusable as a whole-frame negative and perfectly usable as a
localised one.

### What is actually missing — and it is NOT new labels

The loss is `BCEWithLogitsLoss(pos_weight=100)` on a Gaussian heatmap, so the
target is ALREADY zero at the racquet: the model is already penalised for firing
there. The reason that penalty does nothing is weighting:

| | pixels | weight each |
|---|---|---|
| ball (Gaussian) | ~50 | 100x |
| everything else | ~147,400 | 1x |

The racquet head is one pixel among 147,400, weighted the same as empty sky. The
signal exists and is drowned.

So the proposal is **re-weighting, not new labels** — standard hard-example
mining. Up-weight the loss at locations the detector actually false-fires on. It
needs no human time, works on all 26,293 labelled frames rather than only the
14,202 unlabelled ones, reaches person-attached confusers that the static-lock
miner structurally cannot, and sidesteps the base-rate problem entirely because
it never asks whether the frame contains a ball — only whether the ball is HERE.

Written up as docs/sessions/SESSION_I_localised_negatives.md.
