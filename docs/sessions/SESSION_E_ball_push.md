# Session E (multi-session arc) — The ball stack: tracking → trajectory → arc → speed + spin

**Kickoff prompt:** `Start Session E<n> (docs/sessions/SESSION_E_ball_push.md)`
**User brings:** footage recorded at **60 fps minimum** (see the frame-rate
finding below — this is not a nice-to-have), plus ~15 min of blind labeling per
new gold clip. Gold labels are TEST data — the NEVER-train-on-gold rule is
absolute.

> Sources for everything below are listed in the Research section. Where a claim
> is first-party (a vendor's own marketing) or from a paywalled abstract, it is
> labelled as such — do not repeat it as independent fact.

---

## ⚠️ The frame-rate finding — read this before planning anything

SwingVision's founder, on their own architecture: *"if you don't record at
60 fps, you won't even see the ball bounce — it just moves too fast."* 30 fps is
generally too slow to catch the bounce frame; **60 fps is the practical
minimum**; 120/240 fps materially improve bounce localisation and are required
for any direct spin work.

**Verified against our own footage (2026-07-19):**

| Clip | Resolution | fps |
|---|---|---|
| `tennis_sample.mp4` (broadcast) | 1920×1080 | **30** |
| `e2e_l6o8FOoy3MY` / `SgZpQtiTG1A` / `EQSfL7bwJ_I` (the clay e2e set) | 1280×720 | **24** |
| `train_clips/6jp23ghDY9Q`, `RZ_wyJ9rI3Q` | 1280×720 | **60** |

**Our entire recent ball evidence base is 24–30 fps — below the stated minimum
to resolve a bounce at all.** That reframes what we have been calling failures:

- The arc fit's rejected reprojections (13–284 px vs the 6 px gate) are
  *expected* if the bounce frame is systematically wrong by ±1 frame, because a
  ball travels ~0.5–1 m per frame at 24 fps. The literature independently names
  **inaccurate key-event identification** as a leading cause of monocular
  trajectory failure.
- The spin numbers the fit produced (**11,692 and 12,221 rpm**) are physically
  absurd — pro topspin is roughly 2,000–3,200 rpm. That is not a spin
  measurement; it is the optimiser absorbing timing error into the Magnus term.
- Our low clay detection rate (22–33%) is partly a *surface/resolution* problem
  and partly a **frame-rate** problem we never controlled for.

**Consequence for the plan:** every E-session result must state the fps of the
footage it was measured on, and E1's first experiment is an fps-controlled
comparison (we already own 60 fps clips in `data/train_clips/`). If the honest
answer turns out to be "this needs 60 fps footage," that is a *finding to ship
to the user*, not a failure — it is exactly the constraint SwingVision imposes
on its own users.

---

## The five workstreams are ONE dependency chain

```
1. TRACKING   (where is the ball in the image?)      ← 22-33% clay / ~74% indoor, all at 24-30fps
        ↓
4. TRAJECTORY (where is the ball in 3D over time?)   ← we assume z=0. THE architectural gap.
        ↓
3. ARC        (fit one hit→bounce flight, physics)   ← exists, complete; every fit rejected at the gate
        ↓
5. SPEED   +   2. SPIN                               ← both fall out of the arc fit
```

Chasing spin or speed before trajectory and event-timing are fixed is chasing
symptoms.

---

## Current honest state (measured, in-repo)

| # | Area | Where it lives | State |
|---|---|---|---|
| 1 | Tracking | `ball.py` (TrackNet/WASB/fusion + `BallTracker`), `_ballnet.py` | **22-33%** of frames on worn clay 720p/24fps vs **~74%** indoor/broadcast. Static-fixture gate + live-ball filter working. Our eval tolerance is hit@**10 px**; TrackNet's own convention is **5 px** — we are the lenient one. |
| 4 | Trajectory | `ball.smooth_and_fill` → project to court **plane** | **z is assumed 0** — an airborne ball is projected as if rolling. No depth cue is used at all. |
| 3 | Arc | `speedspin.py` + `ball_physics/tennis_tracker` (drag+Magnus sim, `trajectory_fit`, bounce-anchored, `simulator_torch`) | Framework is real and complete. Gate `reproj_max_px = 6.0`. Measured: tennis_sample **13.1 / 20.8 / 284 px**, e2e clay **58 / 61 px** → all rejected. |
| 5 | Speed | `analytics.shot_speed_kmh` (headline) + physics speed | Plane path-length ÷ time → ~15-20% under radar **by construction, and that is correct**: SwingVision reports average speed too and documents it as ~20% below TV radar (which shows peak off the racket). Physics speed ~4% on synthetic, gated off. |
| 2 | Spin | `events.classify_spin` (pose heuristic) + physics rpm | Heuristic v1 unvalidated (disagreed with SwingVision's burned-in label). Physics rpm blocked *and* implausible when it does fire (see above). `spin_net.py` + `train_spin_net.py` + `data/synthesize.py` exist, unexercised. |

**Under-used assets we already own:** `ball_physics/tennis_tracker/data/synthesize.py`
(physics trajectory generator), `physics/simulator_torch.py` (differentiable
simulator), `estimation/spin_net.py`, `eval/metrics.py`. The synthetic-to-real
path the literature now favours is already scaffolded here.

---

## Research — what to adopt, and what is honestly out of reach

### Frame rate & the Nyquist limit on spin (decides the whole spin workstream)
Direct spin observation obeys **fps > |ω|/2** (ω in revolutions/sec). At 60 fps
that caps directly-observable spin at ~30 rps = **1,800 rpm** — *below* typical
tennis topspin. Table-tennis robotics work uses 380 fps for this reason; a patent
in the space notes cameras under 200 fps fail through aliasing once the ball
turns >360° between frames.

**Therefore, the honest deliverable for a 60 fps consumer app is spin
DIRECTION/TENDENCY (topspin / slice / flat), not absolute rpm.** Anyone
promising accurate rpm from 30–60 fps video is overselling. The three practical
routes:
1. **Magnus curvature fitting** — infer spin indirectly from trajectory bend.
   The only route that works at 30–60 fps; recovers coarse spin only.
2. **Periodic texture/logo tracking** — recovers spin *rate* at 100 fps
   (a paywalled *Measurement* paper reports 3.42% — but that figure is
   **repeatability, not accuracy against radar**; do not quote it as accuracy).
3. **Synthetic-trained networks** — train on physics-simulated trajectories with
   known spin, transfer zero-shot to real video (Kienzle et al.; "Uplifting
   Table Tennis"). Our simulator makes this cheap, and training on synthetic is
   **not** a data leak because the simulator owns the labels.

### Trajectory + arc (tennis-specific work — closest to our problem)
- **SynthNet** (Ertner et al., ACM MMSports 2024): end-to-end monocular 3D
  *tennis* trajectory reconstruction. A GRU **"HBNet" detects hits/bounces** to
  segment shots, then a feed-forward net predicts projectile initial conditions,
  **trained purely on synthetic data** (deliberately avoiding Euler-integration
  instability). This is nearly a blueprint for E3.
- **"Where Is The Ball"** (Ponglertnapakorn et al., CVPR 2025 CVSports workshop,
  arXiv:2506.05763): improves SynthNet by enforcing **projection consistency**.
- **Apparent ball size as a depth cue** — the *Measurement* single-camera paper's
  "Trajectory Segmentation Speed Estimation" segments the trajectory using the
  ball's changing image size to recover depth, reporting **4.81% MAE / 7.38% max
  speed error at 100 fps** (paywalled abstract). We currently use *no* depth cue;
  our detector already produces a blob size we discard.
- Standard remedies for the named failure modes (model drift, event-timing
  error): **Kalman/EKF with a ballistic model** filtering in 3D physics space
  rather than 2D pixel space; mixing physical and geometric models beats either.

### Event timing — the cheapest big win we are not taking
- **Audio hit detection.** Racket-ball impact has a distinctive acoustic
  signature; TTNet / TennisVL train lightweight audio nets on impact sounds, and
  audio+visual fusion improves robustness. **We use no audio at all**, yet hit
  timing is a named top cause of monocular failure and directly poisons our arc
  fits. Cheap, no GPU, no labels needed beyond the visual events we already have.
- **Bounce detection as a time-series problem**: CatBoost on trajectory windows,
  sktime classifiers, LSTMs over (x,y) windows, or SynthNet's GRU over
  pose+ball+court features — all stronger than our current speed-minimum
  heuristic.
- **Free external validation:** the TrackNet tennis dataset (~19,835 labeled
  frames, 1280×720/30 fps, 10 matches) carries **ball + hit/bounce labels** — we
  can score our bounce/hit detectors against real labels without any new
  annotation.

### Tracking
- **TrackNetV3**: background as auxiliary input, mixup augmentation, and
  **trajectory rectification + inpainting of occluded segments** — 97.51% vs
  94.98% (V2) on badminton. The inpainting directly targets our dropouts.
  **V4** adds motion attention / frame-differencing fusion.
- **WASB** (BMVC 2023, `nttcom/WASB-SBDT`): sport-agnostic strong baseline, beats
  6 SOTA trackers across 5 sports. Stated limits: validated at HD/FHD and
  **25–30 fps**, one ball per frame. Already in our stack, already winning our
  per-clip probe on amateur footage.
- **Generic YOLO is the wrong tool for the ball** (TrackNetV3 97.5% vs YOLOv7
  53.5% on the same data). Specialised variants exist (YOLO-Ball: P2 shallow
  features + NWD loss, 82.2% precision on tennis) but heatmaps remain the way.
- **Quality > quantity for ball data**: a small (428/100/50) consistent,
  clearly-visible, well-annotated set beat a larger noisy one (arXiv:2511.04126).
  ~500 clean frames from *our* camera angle beat thousands of scraped ones.
- Expect paper headlines to overstate: TrackNet's 99.7% precision was one
  evaluation match; cross-validation dropped recall to ~76%.

**Sources**
- Frame rate / on-device / accuracy claims (first-party, SwingVision site + founder interviews)
- [TrackNet (Huang et al., AVSS 2019, arXiv:1907.03698)](https://arxiv.org/abs/1907.03698)
- TrackNetV2 (Sun et al., ICPAI 2020); [TrackNetV3 (Chen & Wang, ACM MM Asia 2023)](https://github.com/qaz812345/TrackNetV3); [TrackNetV4 (arXiv 2409.14543)](https://arxiv.org/pdf/2409.14543)
- [WASB (Tarashima et al., BMVC 2023, arXiv:2311.05237)](https://github.com/nttcom/WASB-SBDT)
- SynthNet (Ertner et al., ACM MMSports 2024) — monocular 3D tennis trajectory, HBNet hit/bounce GRU
- ["Where Is The Ball" (CVPR 2025 CVSports, arXiv:2506.05763)](https://arxiv.org/abs/2506.05763)
- [Ball spin via physically grounded synthetic-to-real transfer (CVPRW 2025)](https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Kienzle_Towards_Ball_Spin_and_Trajectory_Analysis_in_Table_Tennis_Broadcast_CVPRW_2025_paper.pdf)
- [Uplifting Table Tennis: real-world 3D trajectory + spin (arXiv 2511.20250)](https://arxiv.org/pdf/2511.20250)
- Gossard et al., "Table Tennis Ball Spin Estimation with an Event Camera" (CVPR 2024 workshop) — the fps > |ω|/2 Nyquist constraint
- Zhu, Shan, Huang et al., *Measurement* (Elsevier, 2026) — single-camera speed+spin, TSSE/PSE (**paywalled; abstract figures only**)
- [BlurBall: joint ball + motion-blur estimation (arXiv 2509.18387)](https://arxiv.org/html/2509.18387v1)
- [RacketVision benchmark (arXiv 2511.17045)](https://arxiv.org/html/2511.17045v3) — check licence before use
- TrackNet tennis dataset (~19,835 frames w/ hit+bounce labels); THETIS (strokes); OpenTTGames (120 fps events)

---

## Session plan

### E1 — Measure: fps control, gold labels, failure taxonomy, arc diagnosis
*(everything after this is decided here — do not skip it)*

1. **fps-controlled experiment (new, and now the headline).** Take the 60 fps
   `train_clips` and the 24 fps e2e clips. Measure, on each: detection rate,
   bounce-frame localisation error, and arc `reproj_px`. Also **decimate a
   60 fps clip to 30 and 24 fps** and re-measure — that isolates frame rate from
   surface/resolution with the same footage. **Deliverable: a table that says
   what fps actually buys us**, which either unblocks E3 or tells the user to
   record at 60 fps.
2. Gold-label ball on one clay clip + one 60 fps clip (`select_gold_frames` →
   ~300 blind-labeled frames, stratified toward far court and rally time).
   Score every detector (`eval_gold.py`): tracknet / wasb / fusion / ballnet_v2 /
   visweighted. Report at **both 10 px (our convention) and 5 px (TrackNet's)**.
3. **Failure taxonomy with images** — every miss classified: motion smear / too
   small / low contrast / occlusion / left frame. The fork:
   smear → blur labels (BlurBall-style); size/contrast → **inference-side first**
   (native-res or tiled far-court crops, WASB threshold sweep, motion-difference
   channel — zero training); background confusion → hard negatives.
4. **Arc-gate diagnosis (cheap, high information).** For rejected arcs, decompose
   `reproj_px` into (a) hit/bounce **timing** error, (b) too few real detections,
   (c) the z=0 projection. Re-fit a handful of clean arcs with **hand-corrected
   event frames** — if reproj collapses, E3 is an event-timing project (audio +
   better bounce model), not a detection project.
5. **Free external check:** score our bounce/hit detectors against the TrackNet
   tennis dataset's hit/bounce labels — real ground truth, no annotation cost.

**Gate:** fps table + per-surface baseline (at 5 px and 10 px) + taxonomy counts
+ arc-error decomposition, written into Results. Trigger from the literature:
**ball recall < 85% → fix tracking/fps before anything else.**

### E2 — Tracking: close the detection gap
Cheapest-first per E1's taxonomy: inference-side experiments → hard negatives /
blur labels → architecture (**TrackNetV3-style trajectory rectification +
inpainting** is the highest-value upgrade; V4 motion attention next). If we
fine-tune, follow the quality-over-quantity finding: ~500 clean, well-annotated
frames from our own camera angle, not thousands of scraped ones.
**Gate:** per-surface hit@5px and @10px must beat the E1 baseline with
false-fire on no-ball frames no worse. Never train on gold.

### E3 — Trajectory + arc: make the physics fit PASS
1. **Event timing first** (if E1 says timing dominates): add **audio hit
   detection** (impact transient on the audio track — we currently ignore audio
   entirely) and upgrade bounce detection from the speed-minimum heuristic to a
   trajectory-window classifier (CatBoost/GRU over ball+pose+court features, per
   SynthNet's HBNet). Sub-frame event refinement by fitting both sides of the event.
2. **3D trajectory, not plane trajectory.** Keep the physics fit's z instead of
   collapsing to the plane; store the 3D track in the perception cache.
   Consider the **apparent-ball-size depth cue** (our detector already computes a
   blob size we throw away) as an independent depth signal to stabilise the fit.
3. **Ballistic filtering** — EKF/smoother over the 3D state with the ballistic
   model, replacing plane-space smoothing for in-flight segments; enforce
   **projection consistency** (the "Where Is The Ball" correction to SynthNet).
4. Re-measure the `reproj_px` distribution vs the 6.0 px gate.
**Gate:** ≥1 arc on REAL footage passes at 6 px with a physically sane speed;
bounce positions and line calls must not regress (they ride the same track).
Trigger: **speed MAE > 8% → suspect calibration/bounce-frame, not the model.**

### E4 — Speed + spin: turn passing arcs into trustworthy numbers
1. **Speed:** promote physics speed to headline when its arc passes; keep the
   plane average as the labelled fallback (`speed_source` exists). Be explicit in
   the UI that we report **average** speed (~20% under TV radar's peak) — that is
   the same choice SwingVision makes and documents. Validate against ground truth
   where obtainable: **OCR SwingVision's burned-in MPH** on sourced clips is a
   free labelled set; a borrowed radar gun is better. Target < 5% MAE.
2. **Spin — ship direction, not rpm.** Cross-check two estimators: physics
   `topspin_rpm` sign from a passing arc, and the pose heuristic
   (`classify_spin`). Report **topspin / slice / flat**; report an absolute rpm
   only if it survives a plausibility band (~500–3,500 rpm) *and* came from a
   passing arc — otherwise suppress it. **Add that sanity gate regardless**, as
   the 11,692 rpm reading proves it is needed today.
3. **Synthetic-to-real spin net (stretch).** Train `spin_net.py` on
   `synthesize.py` trajectories with known spin; test on real gold arcs. Follows
   SynthNet/Kienzle precedent; not a leak (simulator owns the labels).
**Gate:** speed error stated per surface *and per fps*, against real ground
truth; spin reported only where an arc passed; every unvalidated number labelled
as such in the UI.

---

## Guardrails (hard-won + newly added)
- **State the fps of every measurement.** A number without its frame rate is
  not a result.
- **Never report absolute rpm from ≤60 fps footage** without a plausibility gate
  and a passing arc. Nyquist says we cannot see it directly; be honest in the UI.
- Custom BallNet did **not** beat off-the-shelf on unseen footage; prior "wins"
  were data leaks. Measure on gold via `eval_gold.py` only.
- Dead-time negatives were the WRONG negatives; hard negatives are the fix.
- The live-ball trajectory filter was the single biggest false-fire win — keep it
  in every evaluation loop.
- Speed is honest-by-construction today (average, ~15-20% under radar). If a new
  method reports higher numbers, prove it against ground truth before shipping —
  do NOT "fix" speed to match TV.
- A single camera reconstructs a *physically plausible* trajectory, not a
  measured one. Hawk-Eye's ~2.2 mm uses ~10 synchronised high-speed cameras.
  Market accordingly; never imply officiating-grade accuracy.

## Results (fill in per session)
- _E1 pending_
- _E2 pending_
- _E3 pending_
- _E4 pending_
