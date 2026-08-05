# ML_PLAYBOOK.md — tennis computer-vision ML, for whoever works this repo

> **Two ML docs, two jobs.** This file (PLAYBOOK) is the *technique*: how to
> diagnose a weak model and what to steal from the field. **[ML_PRACTICES.md](ML_PRACTICES.md)**
> is the *discipline*: how to conduct the work honestly (never grade a model on its
> own outputs, tag every number, the session-end checklist). Read **both** before any
> model work — CLAUDE.md requires it. Current state lives in CLAUDE.md's Status +
> [docs/sessions/](docs/sessions/); [HANDOFF.md](HANDOFF.md) is the historical evidence log this file cites.

Operate as a machine-learning engineer who specializes in tennis computer
vision: small-object tracking, keypoint/geometry estimation, motion-blur and
occlusion, physics-based prediction, and pose-driven shot understanding. This
file is the standing reference for *how to think* when a model here is weak —
diagnose the real cause before touching a knob, and measure honestly.

The project's own architecture rule still governs (CLAUDE.md): **learn what you
can't compute, compute what you can.** ML is only for perception (court
keypoints, ball, pose, shot type). Geometry (homography, speed, line calls) and
logic (scoring, rallies) are exact — never ML-ify them. Most "model" problems
here are actually data, domain, or evaluation problems.

---

## 1. Diagnose before you adjust — the five buckets

When a model is weak, attribute the weakness to ONE of these before changing
anything. Guessing wastes training runs.

1. **Evaluation / leakage** — is the number even real? A train/test leak, a
   metric that rewards the wrong thing, or scoring against pseudo-labels all
   produce fake confidence. *Always fix this first.* (We caught `indoor_elev =
   yt_rally2` in both ball and court training; the gold sets are held out.)
2. **Data** — too little, imbalanced, noisy labels, or the labels came from a
   weaker model (pseudo-label ceiling: a student can't beat its teacher). Most
   gains in this repo are here.
3. **Domain shift** — train and deploy distributions differ (broadcast → phone;
   hard court → clay; bright → dim indoor). The model is fine; it's just never
   seen the target. Fix with target data + augmentation, not more epochs.
4. **Architecture / representation** — the model *cannot express* the answer.
   Example: CourtNet is a heatmap model, so it can only place a keypoint peak
   *inside* the image; it structurally cannot predict an off-frame corner that
   an amateur wide angle needs. No amount of data fixes a representation limit.
5. **Optimization** — LR too high/low, loss collapsed to background, catastrophic
   forgetting, under/over-fitting. Read the train-vs-val curve before blaming it.

Quick triage: **train acc low → underfitting (capacity/optimization/labels).
Train high, val low → overfitting or domain shift. Val high, real-world low →
leak or eval-set unrepresentative.**

---

## 2. Ball tracking (small, fast, blurry, often hidden)

TrackNet-style heatmap detectors + a tracker on top. The hard parts and how to
reason about them:

- **Recall vs false-positive is the core trade.** A tiny bright object invites
  false locks onto the HUD, logos, net posts, line marks, the next court's ball.
  Grade recall and false-fire *separately* (eval_gold does: hit / wrong / miss,
  and FP on true no-ball frames). "Coverage %" alone is a vanity metric.
- **Static-lock = not the live ball.** A detection that moves <~3px for several
  frames is a fixture or a dead/spare ball, never the in-play ball. Gate it out
  (drop the track, blacklist the spot). The user's design rule: track only the
  live ball; when unseen, *predict* the arc — don't hunt.
- **Motion blur is signal, not noise.** A fast ball is a streak. The streak's
  length ∝ speed × exposure and its orientation is the velocity direction — a
  free measurement. Options: synthesize physics-correct blurred balls for
  training data (unlimited perfect labels for the fastest shots that real labels
  never cover), and/or read velocity off the streak directly.
- **Occlusion / brief absence → interpolate with physics, not ML.** Between a
  hit and the next sighting the ball follows a parabola (gravity is known).
  Fit the flight (Kalman filter for smoothing, parabola for the ballistic gap)
  and keep drawing along it. This doubles as the serve-speed fix.
- **Temporal consistency beats per-frame confidence.** A per-frame peak that
  doesn't lie on a smooth trajectory is probably wrong; a live-ball trajectory
  filter removes false fires the raw detector can't.
- **The pseudo-label trap:** BallNet trained on the fusion tracker's output
  inherits its misses (esp. fast/far balls). It can't exceed the teacher without
  human labels on the hard cases. Prior "BallNet beats TrackNet" results were
  data leaks (trained + tested on the same clip). Grade only on held-out human
  gold.

## 3. Court / keypoint detection + homography

- **Heatmap keypoint model** (CourtNet): 14 named landmarks → homography. Fast,
  but the off-frame limitation above is real — amateur frames with cut-off
  corners need either coordinate regression, a homography/parametric output, or
  a classical intersection step that recovers corners outside the frame.
- **The homography is the whole game downstream.** Speed, line calls, and shot
  placement are exact functions of it. A court that's slightly wrong silently
  corrupts every number — so a *confidently-wrong* court is worse than no court.
  Prefer refusing (→ manual corner-drag) over drawing a bad court.
- **Self-check with geometry priors** (calibration.verify_court): project the
  rigid court template and measure how much lands on real white-line pixels
  (coverage) + whether it sits centrally (rejects background/adjacent courts).
  The template is also the line-continuation prior: you always know where a line
  *should* be even where the paint is faded/occluded/cut.
- **Line detection must be lighting-invariant.** Global thresholds (tophat+Otsu)
  collapse on dim indoor / bright-ceiling amateur footage. A bright-*ridge* test
  (brighter than a few px to the sides) + low-saturation (white, not coloured)
  is robust (line_ridge_mask lifted amateur coverage ~9-31% → 55-62%).
- **Domain adaptation for the learned path:** fine-tune the broadcast model on
  target angles with **random-perspective augmentation** (re-warp each labeled
  frame as a new camera). Guard **catastrophic forgetting** by balancing/
  oversampling domains so the target's few frames don't drown, and the source
  isn't forgotten. Fixed camera → detect once and *lock/smooth* the homography;
  don't re-detect a jittery court every frame.

## 4. Predictive modelling — speed, spin, trajectory

- **Speed** = displacement-per-frame × real-world scale (from the homography) ×
  fps. Three failure sources, in order of impact: wrong fps metadata, wrong
  homography scale, and projecting an *airborne* ball onto the ground plane
  (reads hot — the flat-ground assumption is why serves read ~70% high). The fix
  is physics: fit the flight and solve height from gravity, single camera.
- **Averaging vs peak:** reported speed is average over the flight (~15-20% under
  radar's peak). That's honest, not a bug — don't "fix" it to match TV.
- **Spin / swing type** need temporal windows around the contact frame, not a
  single frame. Identify contact reliably first (ball-track direction change +
  pose), then read the wrist/racket path. Validate against physics (a topspin
  arc curves differently) rather than trusting a heuristic.
- **Kalman / trajectory fit** is the right tool for smoothing noisy tracks and
  filling gaps — a constant-acceleration (gravity) model in court metres.

## 5. Pose / player tracking

- Off-the-shelf pose (YOLO) is fine for detection; the tennis-specific work is
  **stable IDs across crossings** (don't swap players at the net), **far-player
  recall** (run pose on an enlarged crop of the far half), and rejecting
  ball-kids/spectators (select players by court-metre position via the
  homography, not image position).
- **Contact-frame detection** is the linchpin for shot type + speed: it's where
  pose, ball track, and geometry must agree.

## 6. Data auditing (the QA lens that catches most "model" problems)

Before training, audit: **leakage** (same clip/footage in train and test),
**label provenance** (human vs pseudo-label vs projected), **balance** (surfaces,
angles, near/far, ball present/absent), **noise** (static-lock junk, drifted
clicks), **coverage gaps** (which real cases have *no* labels — usually the fast
/ far / occluded ones). A held-out, human-labeled gold set is the only honest
scoreboard; never train on it, and re-score the same set before/after every
change so "better" is a number, not a vibe.

## 7. Failure-mode → fix cheat-sheet

| Symptom | Likely cause | Adjustment |
|---|---|---|
| Great on val, useless in the field | leak, or eval set unrepresentative | rebuild an honest held-out set; check footage identity |
| Wrong when confident (court/ball) | no geometry/physics self-check | project template, verify on real pixels; refuse if low |
| Misses fast / far / blurry balls | no labels for those cases | synthesize blur; hand-label hard frames; physics gap-fill |
| Locks onto HUD/posts/next court | no static/centrality gate | static-lock drop + centrality/trajectory prior |
| Fine-tune breaks the old domain | catastrophic forgetting | balance/oversample source; lower LR; freeze less-aggressively |
| Can't predict off-frame keypoints | heatmap representation limit | coord-regression / parametric output / classical intersection |
| Speeds read high | airborne ball on ground plane | gravity height fit; verify fps + homography scale |
| Court jitters frame to frame | per-frame re-detection | detect once, lock/smooth (fixed cameras) |
| Student never beats teacher | pseudo-label ceiling | inject human labels on the hard cases |

---

## 8. Researched state of the art (2024–2026) — what the field does, what to steal

Concrete, current techniques from the literature, mapped to this repo. Sources
at the bottom.

### Ball tracking
- **TrackNetV4** (ICASSP 2025) — fuses learnable **motion-attention maps** with
  visual features. The lesson: pure-appearance TrackNets (V1–V3) fail under
  occlusion/low visibility because they ignore motion. *Steal:* feed BallNet an
  explicit motion cue (multi-frame stack / frame differences), not one RGB frame.
- **TOTNet** (2025, occlusion-aware) — **3D temporal convolutions** +
  **visibility-weighted loss** (down-weight occluded frames) + **occlusion
  augmentation** (synthetically paste occluders over the ball in training). Cut
  RMSE 37.3→7.2 and lifted fully-occluded accuracy 0.63→0.80. *Steal:* all three
  are cheap and directly applicable to BallNet v2.1 — this is the highest-signal
  find for our "vanishing ball" complaint.
- **BlurBall / "Tracking the Blur"** (2024–25) — jointly estimate the ball *and*
  its motion blur; the streak encodes per-frame velocity. *Steal:* validates
  synthesizing motion-blurred balls for the fastest shots (which real labels
  never cover) and reading velocity off the streak.
- **Kalman reality check** (2025) — KF smooths jitter/occlusion but is **linear**,
  so it can't model spin/deflection; feeding a CNN-predicted **image-plane
  velocity** as an extra EKF measurement cut bounce-prediction error **36%**.
  *Steal:* use KF/EKF for short gaps but switch to a gravity parabola across the
  flight, and drive the filter with a velocity estimate, not position alone.

### Added 2026-08-06 — the two finds that bear on our MEASURED position

- **RacketVision** (arXiv 2511.17045, Nov 2025 / rev Jan 2026) — a benchmark over
  table tennis, tennis and badminton, and **the first large-scale fine-grained
  annotations for RACKET POSE alongside ball positions**. Racket pose is **5
  keypoints: top, bottom, handle, left, right**. VERIFIED USABLE: MIT licence,
  downloadable from Hugging Face (`linfeng302/RacketVision`), and pretrained
  weights ship for all three tasks (BallTrack, RacketPose, TrajPred) via
  `download_checkpoints.py`. NOT stated in the README: per-sport frame counts, and
  whether the footage is broadcast or amateur — check before trusting transfer.
  *Why it matters here:* Session G part 4 measured racquet-box negation using
  COCO's generic "tennis racket" box and got **54.5% catch at 4.5% collateral** —
  5.5 points under the pre-registered gate. A 5-keypoint racket pose gives the
  racket's GEOMETRY (head vs handle) instead of a loose box, and the head is
  precisely where the ball-sized, ball-coloured confuser lives. That is the direct
  route to closing a 5.5-point gap, and it re-runs against the same 22 racquet /
  44 person-attached locks and 1201 human clicks with the harness we already have.
  Its BallTrack weights are also an EXTERNAL BALL BASELINE to score on our gold
  set — the only one we have today is COCO sports-ball at 32.1% vs our 69.4%.
  *Steal, but note the warning:* the paper's own headline finding is that
  **naively concatenating racket-pose features DEGRADES performance**, and a
  CrossAttention fusion is what unlocks them. Our instinct — hard-negate anything
  inside the racket region — is the concatenation-shaped move. The signal probably
  needs to CONDITION the detector, not filter its output.

- **TinySet-9M / DEAL / P2SOD** (arXiv 2604.02773, Apr 2026) — a 9M-image
  multi-domain small-object-detection dataset plus a benchmark specifically for
  **label-efficient** methods on small objects. Headline: DEAL, a point-prompted
  detector, beats fully supervised baselines by **31.4% relative at AP75** with a
  single click AT INFERENCE time. Code and model are released (licence not stated
  on the project page; domains and object pixel sizes not stated either).
  *Why it matters here, and it is not the obvious reason:* the load-bearing result
  for us is the NEGATIVE one — "weak visual cues further exacerbate the performance
  degradation of label-efficient methods in small object detection". That is
  independent, external confirmation of the standing conclusion in CLAUDE.md:
  the 2-4 px far-court ball cannot be rescued by pseudo-labels or semi-supervised
  shortcuts, because those degrade MOST exactly where the visual evidence is
  weakest. It matches SESSION_E §E3j and our own Session G part 3 measurement. So
  the far-court plan stays "collect real human labels", and we should NOT expect an
  SSL/active-learning trick to substitute for them.
  Note DEAL's click is an INFERENCE-time prompt, not a training-label saver — do
  not read the 31.4% as an annotation-budget result.

### Court / keypoints
- The de-facto open standard is a **heatmap CNN over 14 court keypoints**
  (yastrebksv/TennisCourtDetector) → homography from 4 corners. That is exactly
  what CourtNet is — so our architecture is mainstream; our gap is data/domain.
- **ML6's court study** (directly our fine-tune problem) found: **MAE loss beat
  MSE** for coordinates; a **fully-convolutional head** beat an FC head; backbone
  **MobileNetV3-Small** beat EfficientNetV2-Small and ResNet50 on accuracy *and*
  speed; and a **hybrid post-step** — crop around each predicted keypoint and run
  a **local Hough refine** (colour-reduce, thicken far lines, Zhang–Suen thin) —
  snaps points onto the true intersection. Predicting just the **4 outer corners**
  was about as good as 16. *Steal:* try MAE loss on the CourtNet fine-tune; add
  per-keypoint local-Hough refinement (we already have `line_ridge_mask` + Hough);
  consider a lighter backbone for phone.
- A dedicated **"Accurate Tennis Court Line Detection on Amateur Recorded
  Matches"** paper targets exactly our footage (CNN keypoints + geometric
  refinement) — worth mining if the classical/hybrid path is revisited.

### Spin
- On a single phone the practical route is **trajectory-based via the Magnus
  effect** (spin curves the flight): fit a physics model with drag + gravity +
  Magnus (e.g. the Nakashima model) to the ball track. Reported **~220 RPM RMSE**
  with clean tracking, but accuracy **degrades above ~4500 RPM** and needs smooth
  multi-frame trajectories. Direct-observation (a mark on the ball) needs
  resolution phone footage lacks. **Synthetic-to-real** (physically-grounded
  simulated spin) is the current trick when real spin labels are scarce. *Steal:*
  this matches our physics-fitter plan — deliver spin *axis* + moderate RPM
  honestly, don't promise pro-topspin extremes.

### Shot / stroke type
- Standard recipe: **pose keypoints (COCO) over a temporal window around the
  contact frame → a sequence model** (3-layer LSTM or temporal-attention)
  classifying serve / forehand / backhand / volley / slice / smash / dropshot.
  Contact-frame detection (ball-track direction change + pose) is the linchpin.
  *Steal:* make shot-type a pose-*sequence* classifier, not single-frame; nail
  contact detection first.
- **Pose2Trajectory** (transformers on pose sequences) predicts player movement —
  relevant later for movement stats / anticipation.

**Meta-lesson from the survey:** our architectures are already mainstream
(TrackNet heatmaps, 14-keypoint court CNN, pose→sequence shots). The field's wins
in 2024–26 are **motion/temporal modelling, occlusion & blur augmentation, MAE
loss + geometric post-refinement, and physics for spin/bounce** — i.e. exactly
the *data / domain / geometry / physics* levers this playbook prioritises, not
bigger backbones.

### Sources
- TrackNetV4 — motion attention: https://arxiv.org/abs/2409.14543
- TOTNet — occlusion-aware temporal tracking: https://arxiv.org/abs/2508.09650
- BlurBall — joint ball + motion-blur: https://arxiv.org/pdf/2509.18387
- Kalman for fast tiny objects: https://arxiv.org/html/2509.18451v1
- yastrebksv/TennisCourtDetector (14-keypoint court CNN): https://github.com/yastrebksv/TennisCourtDetector
- ML6 — improving court line detection with ML: https://www.ml6.eu/en/blog/improving-tennis-court-line-detection-with-machine-learning
- Accurate Tennis Court Line Detection on Amateur Matches: https://arxiv.org/pdf/2404.06977
- Ball spin from multi-camera tracking (Magnus, RPM RMSE): https://pubmed.ncbi.nlm.nih.gov/31783720/
- Spin/trajectory synthetic-to-real (table tennis): https://arxiv.org/html/2504.19863v1
- Tennis player actions dataset (pose, stroke classes): https://pmc.ncbi.nlm.nih.gov/articles/PMC11282921/
- Pose2Trajectory (pose→player trajectory): https://arxiv.org/pdf/2411.04501
- RacketVision — racket pose + ball, 3 racket sports: https://arxiv.org/abs/2511.17045
  (code + MIT + weights: https://github.com/OrcustD/RacketVision)
- TinySet-9M / DEAL — small-object benchmark + label-efficient findings:
  https://arxiv.org/abs/2604.02773 (project: https://zhuhaoraneis.github.io/TinySet-9M/)

---

**Bottom line:** in this repo, reach for *data, domain, geometry, and physics*
before reaching for a bigger model or more epochs. The exact answers (homography,
ballistics) are cheaper and more reliable than teaching a network to approximate
them. Measure on human gold, hold it out, and move the number.
