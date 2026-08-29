# The far end of the court — player and ball, one question tested, two different answers

> Written in response to a founder question posed deliberately as one problem ("far-person
> tracking and ball tracking"). No code was run for this document; it synthesises existing
> measurements (all cited) plus outside literature (all flagged for footage mismatch) and
> pre-registers one new gate. Nothing here has been executed.

## Finding, stated first

**Not the same problem.** Both share one optical root cause — a fixed amateur mount at
1.3–3.4 m height puts the far end of the court (15–24 m away) below the pixel budget of
any appearance model — but they diverge at the point of failure, and the divergence is
already measured, not assumed:

- **The far player is SEARCH-limited.** The full-frame pose model finds it at **0 of 25**
  far-end contacts on `yt_match40`, at any tolerance. A targeted 192 px crop upscaled to
  640 (upscale factor ~3.3×, ~107–112 px of player in the tensor) finds it at **2/25
  strict / 15/25 post-hoc**. Spatial supersampling of a known region **works** — it is a
  measured, if weak, positive. [p0-3-crop-around-contact.md](p0-3-crop-around-contact.md)
- **The far ball is DISCRIMINATION-limited.** The detector already fires in the far court
  on the large majority of frames — it fires on *nothing* in only 24–27% of them
  ([far-court-recall.md](far-court-recall.md)). The ball's own direct analog of the
  player's fix — **raising the whole-frame detector resolution 512×288 → 640×360** — was
  already tried. It bought **+8.2 pts far_px recall at the detector**, and at the chain the
  entire gain **arrived as extra solid ghosts** (5→7 on `yt_rally2`, 1→5 on `am_hard_utr`)
  while the shipped setting dominated every variant end to end.
  [raising-the-detector-s-input-resolution.md](raising-the-detector-s-input-resolution.md)
  This is one of **four for four** detector-side gains (resolution, `score_thresh`,
  localised confuser weighting, +57% data) that cut detector error and delivered nothing
  or worse to the rendered output.
  [expecting-a-detector-gain-of-any-kind.md](expecting-a-detector-gain-of-any-kind.md)

**Why this is not just semantics.** If the ball were also purely search-limited, "more
resolution" would have looked like the player's result — a jump from near-zero to
something. It did not: it looked like a wash, because the confusers that create solid
ghosts (59.2% of false locks travel with a person; [motion-attention.md](motion-attention.md))
are *already* ball-sized and ball-textured at native resolution, so giving the model a
sharper look at the whole frame sharpens the confuser as much as the ball. **Every solid
ghost that survives the chain carries `run_len = 1`** — a real ball's own kinematic
signature — which is why nine downstream chain attempts, all of which test for
*non-ball-like behaviour*, have failed against them.
[9-solid-ghost-balls.md](9-solid-ghost-balls.md) That is a discrimination failure, not a
sampling failure, and it is a different disease from "the model never fired."

**What would disprove this framing.** If a *targeted, localised* ball re-query (not the
whole-frame bump already tested) produced the same shape of result the player crop did —
a large jump on a population where the baseline is near-zero — the two problems would
look more alike than this document claims. That is exactly the experiment pre-registered
below, and it is the cheapest available falsifier of this finding.

**Confidence: 80** that the two are genuinely different failure modes (search vs.
discrimination), based on the resolution-bump result being a real, already-executed test
of the closest available analog to the player's fix, not an assumption. **Confidence: 30**
that a localised version of the same idea will do any better for the ball — see the
literature note below.

---

## What is left — ranked, with mechanism, why it isn't already dead, and (for ball) the chain reason

### 1. PLAYER — re-center the crop on something better than the ball position (top item, gate below)

**Mechanism.** P0-3 already measured the crop's own weak link: a ball-centred 192 px crop
holds the far player at a **median of 26.3 px from the crop edge** — the player is often
found, barely, right at the boundary of usefulness. [p0-3-crop-around-contact.md](p0-3-crop-around-contact.md)
If the true far-player position sometimes drifts outside the crop, the crop-based detector
returns to the 0/25 full-frame failure by construction — not because the upscale trick
stopped working, but because the crop was pointed at the wrong 192 px square. A crop center
informed by something with lower variance than "wherever the ball currently is" (e.g. the
far-side baseline/service-box band, which moves far less frame to frame than a struck ball)
could recover some of the 8 of 15 post-hoc misses without touching the model at all.

**Why it is not already dead.** This is not a repeat of the three dead player-foot-gate
items (survivor vote, wrong-court negation, nearest-motion-blob identity) — those all asked
"which candidate blob IS the player." This asks "where should the crop be centred," a
different variable, never swept. It is also not a repeat of the resolution/downscale
negatives (`--pose-quality accurate`, P0-2 downscaling) — those changed the model's input
resolution globally; this changes only the crop's coordinate, at fixed 192@640.

**Chain relevance.** Not applicable in the ball sense — the player pipeline has no
`suppress_false_locks`-style absorbing stage between detection and the rendered pose; a
found detection is used directly. The open question is purely "does it fire," which is
exactly what P0-3 already measures.

**Feasibility on A13.** No new compute. Same fixed 192×192→640×640 enumerated-shape crop
already scoped for Core ML in P0-3 — this changes only which pixel is the crop's center,
a logic change, not a model or shape change.

### 2. BALL — Kalman/track-gated LOCAL re-query, only in a physically-constrained window, only on low-confidence frames (second item, unproven, gate sketched)

**Mechanism.** Distinct from the closed whole-frame resolution bump: instead of sharpening
every pixel in the frame (which sharpens confusers as much as the ball), run a second,
small, upscaled detector pass **only** inside the small window the existing Kalman track
predicts, and **only** on frames where the current lock is already flagged
low-confidence/ambiguous (the population the smoother and `suppress_false_locks` are
already fighting over). The claimed selectivity gain: a confuser sitting in the far court
(a fence post, a ball machine, a spectator's white shirt) is unlikely to sit exactly on the
track's own physically-predicted point at the physically-predicted time; a real ball is.
This is a different axis of selectivity than "more signal everywhere," which is the axis
all four closed items share.

**Why it is not already dead.** Not the same as **detector fusion** (TrackNet+WASB —
rescued 4 frames, doubled cost): that combined two *different models* over the *same*
full-frame region. Not the same as **screening far-court gaps at selection/by kinematics**
(both measured negatives): those post-hoc scored *existing* interpolated points for
trustworthiness; this *re-runs the detector* at a new location and resolution rather than
grading what is already there. Not the same as the **bounce_hypothesis** family: that
added a second physical model inside the smoother; this adds a second detector call, and
its failure mode (if any) would show up as a *precision* problem (locks on a plausible-but-
wrong point), not a *sign-reversal* problem like the reflected-hypothesis's own
false-acceptance region.

**Chain-level reason it could reach the output, stated plainly.** All four closed items
increased the *volume* of detections without changing what is being asked of any single
detection; the chain absorbs volume by design (that is what `suppress_false_locks` and the
smoother exist to do). This proposal does not increase volume — it asks a **new, narrower
question** ("is there a ball specifically at this predicted point, at this predicted time,
at higher resolution") only in the frames the chain is already unable to adjudicate. If it
works at all, the win shows up as fewer solid ghosts and/or more real hits in exactly the
ambiguous population, which is the metric the chain evidence already tracks
([9-solid-ghost-balls.md](9-solid-ghost-balls.md)).

**Why confidence is low (~25–30%), and the honest caveat.** The one wholesale detector
change that DID move solid ghosts (TrackNet swap, −29.5%,
[ballnet-v21-vs-tracknet-at-the-chain.md](ballnet-v21-vs-tracknet-at-the-chain.md)) worked
by being a genuinely different model on genuinely different failure frames (18% overlap),
not by looking harder in a smaller place. There is no existing evidence that "same model,
smaller/sharper input, physically-gated" changes *which* frames fail rather than just
re-confirming the same failures at higher resolution. The outside literature is a further
caution, not a support: a 2025 survey of five widely-used Kalman-based multi-object
trackers (ByteTrack, OC-SORT, DeepOCSORT, BoTSORT, StrongSORT) on a 10,000-frame
racquetball dataset (720p–1280p, tiny fast erratic object — the closest published analog
to a tennis ball found) reports **3–11 cm / 31–114 px average displacement error, 3–4×
worse than standard MOT benchmarks**, and attributes it to the combination of small size
and unpredictable motion defeating linear-motion prediction generically — i.e. the exact
mechanism this proposal leans on (a good Kalman-predicted window) is reported elsewhere as
itself unreliable for this class of object. (arXiv 2509.18451, robotics/vision domain,
camera setup and amateur-vs-fixed status not stated in the abstract — flagged as an
unverified footage match, cited for the failure-mode argument only, not for a number to
import.)

**Feasibility on A13.** Additive, not free. BallNet's full-frame 512×288 pass is already
estimated at ~30–50 ms/frame on ANE ([[coreml-ane-budget]] — **arithmetic, not measured, no
phone has run any part of this pipeline**). A second small fixed-shape crop pass (e.g.
128×128→256×256, enumerated shape for Core ML) triggered only on the ~24–27% of frames
already flagged low-confidence would add a bounded, modest per-frame cost on a minority of
frames — plausibly single-digit ms given the smaller tensor, but this is arithmetic and
must be labelled as such until measured.

---

## What is now CLOSED — do not re-propose

- **Motion+contrast as a far-player finder** (the founder's original framing of this same
  general question, tested 2026-08-29): the nearest motion blob does not identify the far
  player (median 5.751 box-heights vs a ≤1.5 bar; null control also fails, so the negative
  is clean). Third negative in the player-foot-gate family; rule 3 closes the family.
  [far-player-motion-gate-result.md](far-player-motion-gate-result.md)
- **Any GLOBAL/whole-frame change to the ball detector** (resolution, threshold,
  weighting, more data of the general kind already tried) — closed by rule 6 and the
  four-for-four precedent. This document's #2 proposal is explicitly **not** this: it is
  local and gated, not global. Do not conflate the two when this is read back later.
- **Filling far-court ball gaps by interpolating between existing anchors** — already a
  measured negative (63% accuracy, correlated with false anchors on both sides of the
  gap). [far-court-recall.md](far-court-recall.md) This document's #2 proposal is also
  not this: it re-runs the detector at new pixels, it does not trust or interpolate
  existing locks.
- **Contrast (luminance/chroma) as a far-player discriminator** — characterised, not
  gated (no bar existed to fail), but the descriptive numbers already show it does not
  separate frames motion found from frames it missed. Not re-open-able as a discriminator
  claim without a fresh, pre-registered population.

---

## Pre-registered gate — PLAYER item #1 (the one worth running first)

**Metric.** Re-run `tools/p0_3_crop_probe.py`'s `crop192@640` arm with the crop center
computed from a court-geometry prior (the far service-box/baseline band's projected image
position, held fixed for the whole clip or updated at a coarse rate) instead of the ball's
image position at the contact frame, on the **same 25 far-end contacts** used in P0-3 —
zero new labelling.

**Threshold.** Pass requires the post-hoc "far-sized non-near person found anywhere in the
crop" rate to **exceed 15/25** (P0-3's existing ball-centred number) **and** the median
distance-to-crop-edge to fall **below** the existing 26.3 px weak-link figure. Both must
move in the right direction — a center that finds more players but centres them no better
is not the mechanism this claims.

**Held-out set.** `yt_match40`'s 25-contact population only, exactly as P0-3 defined it
(homography-free, no court lines rendered, calibration void per T23). Do not extend to
`am_hard_utr` — its n=12 population is already flagged underpowered and contaminated by
static-fixture false locks.

**Kill condition.** If the pass rate does not exceed 15/25, or if it does but the median
edge-distance does not improve, stop — the crop's centring signal is not the bottleneck
and this joins the dead list rather than being re-swept with a different prior.

**Seed / provenance.** No stochastic component in this test (deterministic geometric crop
placement); still stamp the calibration file hash and git commit per existing P0-3
provenance convention so the run is reproducible.

---

## Literature checked, and how our footage differs from every one of it

- **SAHI / tiled slicing inference** (arXiv 2202.06934, VisDrone/xView aerial imagery):
  +5.1–6.8% AP untuned, +12.7–14.5% with fine-tuning. Smaller than our own crop-and-upscale
  result (0/25→15/25 relaxed) because SAHI tiles blindly across a huge image with no
  location prior; our crop already has a strong prior (the contact frame's ball position).
  **Footage mismatch:** aerial drone imagery of cars/pedestrians from directly overhead —
  no perspective foreshortening, no motion blur, fixed nadir view. Not sports, not
  ground-level oblique, not amateur single-camera. Do not import the percentage; the
  mechanism (crop at native res, upscale) is the only transferable idea, and we already
  tested it directly on our own footage rather than relying on this number.
- **TOTNet** (arXiv 2508.09650, occlusion-aware ball tracking, table tennis/badminton/tennis):
  mechanism is 3D convolutions + visibility-weighted loss + occlusion augmentation. The
  visibility-weighted-loss + occlusion-augmentation half of this is **already shipped here**
  and already validated on our own gold set (82.9→84.9, occluded 84.2→89.7 — see STATE
  "What has worked"). The 3D-conv half is untested here. **Footage mismatch:** trained and
  evaluated on **professional Paralympic broadcast** table tennis — fixed elevated camera,
  not a handheld/tripod amateur phone, no reported ball pixel size. Also: occlusion (ball
  hidden behind a body) is a different failure mode from smallness-at-distance (ball
  visible but sub-pixel-informative); the two get conflated in ball-tracking literature
  generally, and this document does not import TOTNet's numbers for the far-end problem.
- **Kalman-filter survey on tiny fast objects** (arXiv 2509.18451, racquetball,
  720p–1280p, ByteTrack/OC-SORT/DeepOCSORT/BoTSORT/StrongSORT): 31–114 px / 3–11 cm ADE,
  3–4× worse than standard MOT benchmarks. Used above as a caution against proposal #2, not
  as a positive result to import. **Footage mismatch:** camera count, mount, and
  amateur-vs-fixed status not stated in the abstract — this is cited for the qualitative
  failure-mode argument (linear-motion Kalman prediction is generically unreliable for
  small erratic objects) only, never for a number.

---

## For the PM — the product tradeoff, left open

Both remaining items are cheap to test (no new labelling, existing infrastructure) and
neither is guaranteed to move the number by much. The player item is the safer bet: it
tests a narrow, already-measured weak link with a clean kill condition and no new compute.
The ball item is the more speculative bet: it is the only genuinely new mechanism left in
scope for the ball's far end that is not already closed by the four-for-four rule, but the
outside literature and the shape of the one detector change that *did* work (a model swap,
not a sharper look) both argue against it working as hoped. **If neither clears its bar,
the honest position is that the ball's far end has no cheap remaining lever inside a single
amateur camera** — the nine solid ghosts carry a real ball's own kinematic signature and
nothing short of a different sensing modality (a second camera, depth, or a materially
different detector architecture, none of which are in scope under the on-device/one-camera
constraint) has a stated mechanism left to try against them. That is a product-relevant
ceiling, not a research dead end to paper over.

## Open questions

- Does the far-player crop-recentring gain, if it passes, survive on a *second* clip with a
  correctly-calibrated far end? `yt_match40`'s homography is void (T23); this whole test is
  homography-free by construction, but a positive result should be replicated on a clip
  whose calibration is trusted before it is treated as more than a single-clip finding.
- The ball's Kalman-gated proposal needs its own low-confidence-frame population defined
  and pre-registered before anyone runs it — this document sketches the mechanism and the
  chain-level argument but does not yet specify the exact frame-selection rule, threshold,
  or kill condition the way the player gate above does. That is deliberate: given the
  literature caution, it is not worth fully specifying test parameters before the cheaper
  player test either confirms or disconfirms whether "localised, prior-informed re-query"
  is a mechanism that works on this footage at all.
- No A13 measurement exists for either proposal's added cost. Both feasibility notes above
  are arithmetic, not measurement, and must be labelled as such wherever they are quoted
  next.
