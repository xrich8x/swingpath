# Is the far player better found by MOTION+CONTRAST than by person detection?

> Answers the founder's question, verbatim: *"the far person is always moving and is in
> relative contrast to the court."* Researcher task, 2026-08-29. No code run — this is a
> synthesis of evidence already in the repo (`eval/movers.py` and its two downstream
> exercises), plus outside literature, against the P0-3 far-player population.

**Verdict up front: NOT WORTH BUILDING as tested to date; genuinely UNTESTED in the one
form that matters. The founder's mechanism (motion) has already been run on this exact
footage for a related purpose and failed with a backwards sign; the specific claim — that
a motion blob's *position* identifies *which* one is the far player — has never been
measured. A cheap, pre-registered, zero-new-labelling experiment can settle it.**

---

## Correction to the brief before anything else

The brief states `eval/movers.py` is "UNRUN... no number in this repo comes from it." **That
premise is wrong, and it matters for what follows.** The module's docstring says that
because it was written 2026-08-24 as a library, but its primitives (`clean_plate`,
`foot_points`, `crop_row`, `feet_in_court`) were exercised the same day via
`eval/candidate_audit.py --movers` and `eval/foot_gate_power.py`, over **30 clips (20 gold
+ 10 calibrated references)**. The results are in `data/output/court_scoring_diagnosis.md`
§§7–9 and are already in `docs/STATE.md` "What has not worked" as **"The horizon crop
(`movers.crop_row`) at `k = 1.0`"** (safe but inert) and the player-foot-gate rows. Those
tool files' own docstrings are stale — written before the same-day run, never updated
after — which is why the brief inherited the wrong premise. This is a documentation-lag
bug, not a fabrication, but the founder's question needs the corrected timeline: **the
underlying motion-detection primitive has already been measured on this project's own
footage, just not for player *identity*.**

---

## What the existing runs actually measured, and what they did NOT

Two prior exercises used the identical classical mechanism (temporal-median clean-plate →
`cv2.absdiff` → connected components, size/aspect-filtered to player-sized blobs) the
founder is proposing. Neither asked "which blob is the far player." Both are the closest
available evidence, and both are named explicitly to avoid conflating them with a
same-question replication.

1. **`feet_in_court`, aggregate court-hypothesis discriminator.** 216 per-frame locks
   across 30 clips, labelled GOOD/BAD against human court truth. Statistic: fraction of a
   frame's foot points landing inside a *candidate* court. Result: **DEAD, and the sign is
   backwards** — wrong courts contain the feet *better* than right ones at every margin
   tested (±5/10/20 m: gap −0.033, −0.054, −0.071). Best catch at the project's 5%
   collateral ceiling: 2.0%, five times worse than the worst other negation idea already
   rejected on the same bar (racquet-box, 54.5%/4.5%). *(`data/output/court_scoring_diagnosis.md`
   §9, `eval/foot_gate_power.py`.)*
2. **`crop_row`, horizon-bound proposal.** Same foot points, used to bound where court
   lines can be. Result: **safe but inert** — a crop is proposed on 1 of 20 gold clips, and
   that one removes 20 rows of 360 for +172 px of clearance. *(§7, same file.)*

**Neither is the founder's question.** Both collapse many foot points into ONE aggregate
number per clip or per frame; neither asks "does the position of a single motion blob
match the far player's position." That per-frame, per-blob identity question is untested.

## The confuser census — measured, and it is the single most load-bearing number here

`eval/movers.py`'s own comment (lines 56–62), backed by the 30-clip run above: **the
size/aspect filters alone let through a median of ~9 candidate blobs per frame (up to 18)**
before any count cap. Named explicitly, from this footage: *"crowd, scoreboard flicker,
trees, and high-contrast edges shivering under camera shake."* `MAX_PLAYERS = 4` then keeps
only the largest-by-**area** blobs — a rule (a court holds at most 4 players), not a
discriminator; it does not know which of the survivors is a player at all, let alone which
one is the *far* player.

This is a direct, footage-matched answer to one of the brief's required questions — **name
the confusers from the actual footage, not in the abstract** — and it is negative for the
founder's mechanism in its raw form: motion+size alone does not separate "far player" from
8 other things that also moved between frames.

## Does contrast hold? No number exists; the qualitative record is mixed

No experiment in this repo measures contrast between the far player and the local
background. The closest evidence is P0-3's own human review of `yt_match40`'s far-end
contact sheets (`docs/evidence/p0-3-crop-around-contact.md`): the far player is
**"sometimes a red shirt against dark hedge (high contrast) and sometimes near-
silhouette."** That is a documented within-clip failure mode, not a rate. **The founder's
premise holds sometimes and fails sometimes, on the same clip, and nothing here quantifies
the split.**

## Does the footage stay static enough for a clean-plate at all?

Target footage is "amateur phone video on a **fence or tripod**" (`docs/STATE.md` line 72)
— semi-static mounts, the assumption `clean_plate`'s docstring is built on ("the camera is
static, so this is the court with the people taken out"). The 9-of-20-clips run that used
120 frames spanning **whole recordings** (not just 8 sample frames) did not blow up, which
is weak positive evidence the mounts hold still enough on those 9. But camera motion is a
**named, already-encountered failure mode** elsewhere in this codebase:
`backend/swingvision/ball.py:1649`, the ball's own background-subtraction candidate
generator, bails out explicitly — `if th.mean()/255.0 > self.max_fg_ratio: # camera moved
/ lighting jump; return []`. **No number here measures how often target footage trips
that condition**, and "high-contrast edges shivering under camera shake" is already named
as one of the ~9 median confusers per frame — so camera motion is not hypothetical, it is
already inside the measured confuser population, just not broken out separately.

## What would a motion-based far-player signal actually feed? Three options, ranked

- **(a) Replace pose entirely — off the table regardless of outcome.** A motion blob is a
  bounding region with no keypoints. Shot classification and stroke type
  (`events.classify_shot`, `classify_spin`) need a skeleton, which motion cannot supply at
  any accuracy. This option does not survive inspection and should not be tested.
- **(b) Propose a crop location, feeding the existing pose pass — the only option worth
  testing.** P0-3 already found the mechanism that works (`crop192@640`, upscale ~3.33×,
  2/25 strict / 15/25 post-hoc) and its own weak link: **a ball-centred crop holds the far
  player only by a median 26.3 px from the crop edge.** If a motion blob can re-centre that
  crop on the *player* rather than the *ball's last known position*, it attacks exactly
  that measured gap. This is cheap to test and the test is specified below.
- **(c) A refuse/veto signal only — already tested in its aggregate form and dead.**
  `feet_in_court` is the veto-shaped version of this idea and it failed with a backwards
  sign. A per-frame veto is a different mechanism sharing the same primitive; the prior
  from (1) above is against it, and per rule 3 a second failed test of the same family
  should retire it, not invite a third attempt.

## Outside literature — cited, and labelled by footage

Temporal-median background subtraction for small/fast objects in racket sports is
published and the general technique is not in question (WebSearch, 2026-08-29): a
median-frame background model is a standard prior for isolating small moving objects, and
background-modelling approaches report **54–61% Mean-Distance-Error reduction across
racket sports** in at least one paper found. **This number is almost certainly measured on
broadcast or controlled-camera footage** — no source found specifies amateur, off-centre,
handheld phone video with fence mesh, roof trusses or crowd motion, and none was verified
against those conditions. Per the benchmark-transfer rule, **do not import that number**;
it says the *mechanism* is real, not that it clears our bar on our footage. Separately,
SAHI-style tiled/sliced inference for small objects (reported AP gains 6.8–14.5%) is the
literature's name for the technique P0-3 already validated in-repo (crop + upscale beats
full-frame) — but that is a **detector**-based technique, not motion-based, and it is
already the thing this repo is pursuing via P0-3, not a new lever this question adds.

Sources: [Object Detection and Tracking Based on Trajectory in Broadcast Tennis Video](https://www.researchgate.net/publication/283184656_Object_Detection_and_Tracking_Based_on_Trajectory_in_Broadcast_Tennis_Video), [Players tracking and ball detection for an automatic tennis video annotation](https://www.researchgate.net/publication/221144146_Players_tracking_and_ball_detection_for_an_automatic_tennis_video_annotation), [Player Detection and Tracking in Broadcast Tennis Video](https://www.researchgate.net/publication/221411677_Player_Detection_and_Tracking_in_Broadcast_Tennis_Video), [Small Object Detection in Video (SAHI and Slicing Inference)](https://intechhouse.com/blog/small-object-detection-in-video-sahi-and-slicing-inference), [A Comprehensive Review of Computer Vision in Sports](https://arxiv.org/pdf/2203.02281). None of these were verified against amateur off-centre phone footage; treat every number in them as broadcast-conditioned until shown otherwise.

## iOS / A13 cost — order of magnitude only, not measured on-device

`eval/movers.py` runs at `WORK_W = 960`, pure OpenCV (`absdiff`, `GaussianBlur`,
`morphologyEx`, `connectedComponentsWithStats`) — CPU work with no matmul-heavy op, plausibly
low single-digit milliseconds per frame at that resolution. This is **cheap relative to the
ANE pose budget**: `yolo11m-pose @ 1280` is estimated at **~1,000 ms/frame on an A13 ANE**
([[coreml-ane-budget]] memory, arithmetic not measurement), so a motion pass competing for
CPU time while pose runs on the ANE is very unlikely to be the bottleneck. **Two caveats,
both real:**

1. `eval/movers.py` lives in `eval/`, not `backend/swingvision/`. The mobile-viability audit
   (`docs/evidence/mobile-viability-audit.md`) covers only the shipped package and found
   "every cv2 symbol used exists in the mobile builds" — that finding has **not** been
   re-checked against `movers.py`'s specific calls. They are standard core-OpenCV symbols,
   so the risk is judged low, but it is a judgement, not a re-run of that audit.
2. `clean_plate` needs a rolling buffer of up to `PLATE_MAX = 31` frames. For the shipped
   **offline, record-then-process** design this is not binding (the whole clip is already in
   hand — [[mobile-port-split]]); it would matter for any future live/real-time use, which
   is out of scope today.

No phone has ever run any part of this pipeline (`docs/STATE.md`, "Phone app shell" row) —
this section is arithmetic, not measurement, and must be quoted as such.

---

## Pre-registered gate, before anything is built

**Population.** Reuse P0-3's `yt_match40` far-end contact set — no new human labelling.
Restrict to the **15 of 25** contacts where the post-hoc `crop192@640 (yolo11x)` arm found
a far-sized non-near person within 1.5 box-heights of the ball anchor
(`data/output/p0_3_tolerance_sweep.json`). This is the closest thing to a ground-truth far-
player position that exists without new labelling; it is explicitly labelled post-hoc in
P0-3 and stays labelled post-hoc here.

**Metric.** For each of the 15 frames (± a small window matching `movers`' intended
temporal footprint), run `eval.movers.foot_points` unmodified. Measure the distance from
the **nearest** returned foot point to the known far-player box centroid, in box-heights
(same unit P0-3 already uses).

**Null control — mandatory, not optional.** With a median of ~9 candidate blobs per frame
already measured, *some* blob being close to the true position is close to guaranteed by
chance alone. Compare against: distance from a **randomly selected** blob (of the same
frame's candidate set) to the same target, over the same 15 frames. The real (nearest-blob)
statistic must beat the random-blob control by a wide margin, or the "signal" is just
"there are usually 9 things and one of them happens to be nearby."

**Bar to be worth building.** Median nearest-blob distance ≤ 1.5 box-heights on ≥10 of 15
frames, **and** the random-blob control fails that same bar (i.e., the improvement is
attributable to position, not candidate density).

**Kill condition, pre-committed.** If the nearest-blob median exceeds 1.5 box-heights, or if
the random control clears the bar about as often as the nearest-blob statistic, this joins
`docs/STATE.md` "What has not worked" as a third measured negative in the player-foot-gate
family, and per rule 3 the family should not be re-proposed a fourth time.

**Cost.** No new labelling, no training, no GPU. Reuses cached P0-3 probe JSON and
`eval/movers.py` unmodified. Compute is a scoring pass over ~15 already-identified frames
at 960 px working width — minutes.

**Compliance check.** This experiment never calls `calibration.image_to_court` and touches
no homography, so `yt_match40`'s known-broken calibration (T23) cannot contaminate it —
unlike the earlier `feet_in_court` court-validation use, which is homography-dependent and
is not affected by this note either, since it was measured on 30 clips, not on `yt_match40`
alone. `am_hard_utr` is excluded from this population per P0-3's own finding that its n=12
contacts are contaminated by anchors sitting on a stationary ball.

---

## For the PM: the tradeoff, left open

If the pre-registered experiment above passes, the only defensible next build is a
**crop-centring proposal feeding the already-partially-validated `crop192@640` pose pass**
— not a pose replacement (motion carries no skeleton) and not a veto (the aggregate version
of that idea is already dead). That is a small, cheap addendum to work already in flight
(P0-3), not a new subsystem. If it fails, the honest statement is that this project has now
measured the same underlying primitive negative **twice** for player-identity purposes
(`feet_in_court` aggregate, and this per-frame test) on top of the already-measured
confuser census — closing the motion-for-players line, not just this specific proposal.
Either way, the decision to run the 15-frame check is cheap enough that it should not need
much sequencing weight.

## Open questions

- No number anywhere quantifies how often target footage (fence/tripod amateur clips)
  actually triggers camera-motion contamination of a clean-plate. `ball.py`'s bail-out
  proves the failure mode is real and already coded around; nothing measures its rate.
- No number quantifies the founder's contrast claim as a rate (P0-3's "sometimes... sometimes"
  is qualitative). A contrast statistic (e.g. mean |Δluminance| or Δchroma between the
  known far-player box and its local surround, at the same 15 P0-3 frames) is a second,
  even cheaper, homography-free, no-new-labelling check that was not run here for time
  reasons and would sharpen "does contrast hold" beyond the single documented anecdote.
