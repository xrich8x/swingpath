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

> **CORRECTED BY E1 (2026-07-20).** Two of the three claims below did not
> survive measurement. (a) The evidence base is *not* all 24-30 fps: 13 clips
> are 60 fps, **including the gold-labelled `yt_rally2`** — past runs merely
> *sampled* it at `frame_step=2`. (b) Event-timing error is **not** what fails
> the arc fits: ±2 frames of anchor error costs only 1.5-3.4 px, well inside the
> 6 px gate. The absurd rpm is real, but its cause is that the fit is
> **under-determined**, not mistimed. Read the E1 Results section before
> planning from this box.

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
> **E1 re-ordered this list.** Item 2 (a second constraint on the launch point)
> is now the whole ballgame — it moved ground-truth speed error from +107% to
> −2%. Item 1 (event timing) measured as second-order: ±2 anchor frames costs
> 1.5-3.4 px. Do the constraint first; revisit audio only if speed error stays
> above target once the arc is determined. And note the stated gate below is
> **void** — an arc passing at 6 px proves nothing (E1 §2).

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

### E1 (2026-07-20) — MEASURED. The bottleneck is not frame rate; it is observability.

E1 set out to price frame rate. Frame rate turned out to be a second-order
variable, and the experiment designed to test it uncovered the first-order one:
**the arc fit's `reproj_px` gate does not constrain speed at all.** Everything
below is measured, with the fps of every measurement stated.

#### 0. The premise needed correcting first
`tools/clip_inventory.py` (new) probed all 32 clips. The doc's claim that "our
entire recent ball evidence base is 24-30 fps" was **wrong**: 13 clips are 60 fps,
including **`yt_rally2` — one of our two human-gold-labelled clips — at
1280x720/60 fps.** Its 300 gold frames were merely *sampled* at `frame_step=2`,
so past measurements were taken at an effective 30 fps on 60 fps footage. That
means the fps experiment could run against real human labels, at no annotation
cost. (The 24 fps clay e2e set and 30 fps `tennis_sample` are as the doc said.)

#### 1. fps-controlled detection [MEASURED, yt_rally2, 60fps source, human gold]
Same footage, same detector, same 284 scored gold frames; only the ingest frame
rate changes (`ball_perception.py --target-fps`, `eval_gold.py --common-frames`).

| track | hit@10 | hit@5 | wrong>10 | miss | FP (no-ball) | far court |
|---|---|---|---|---|---|---|
| tracknet @60 | **43.4%** | 30.2% | 10.5% | 46.1% | **15.4%** | 23.8% |
| tracknet @30 | 42.6% | 32.9% | 14.7% | 42.6% | 30.8% | 23.8% |
| wasb @60 | 29.5% | 20.9% | 8.9% | 61.6% | 19.2% | 4.8% |
| wasb @30 | 34.9% | 26.7% | 15.5% | 49.6% | 26.9% | 9.5% |

Extending the ladder (common subset, n=142): tracknet hit@10 is 42.4 / 40.9 /
38.6% at 60 / 30 / 15 fps, while mislocks (`wrong>10`) climb 10.6 / 12.9 / 21.2%
and no-ball false fires 10 / 10 / 20%.

**Finding: frame rate buys PRECISION, not recall.** Per-frame recall is flat
within noise from 15 to 60 fps; what degrades as fps falls is the tracker's
ability to reject junk (its temporal continuity and static-fixture gate have
less to work with). Recording at 60 fps roughly halves the false-fire rate and
changes hit rate by ~1 point.

What 60 fps *does* buy is **sample density**: locks per second of video are
29.7 @60 vs 16.8 @30 (tracknet) — nearly 2x as many looks at the ball per second
of flight. That is the currency arcs and bounce localisation spend, and it shows
up downstream: full `analyze` on yt_rally2 built **2 candidate arcs at 60 fps and
0 at 30 fps** (a 30 fps arc rarely reaches `min_arc=6` samples). So the "record
at 60 fps" advice is right, but for the trajectory stage, not the detector.

Also settled: **far court is fps-independent** (23.8% at both 60 and 30). It is a
resolution/apparent-size problem, so E2's far-court work should be
inference-side (native-res or tiled crops), not frame rate and not more epochs.

Sanity check on the harness: tracknet@30 reproduces Session 2's independently
measured 41.5% (we got 42.6%), so this rig is comparable to the old numbers.

#### 2. The arc gate is not a gate [MEASURED, ground truth, `tools/arc_observability.py`]
Simulate a real flight (86.9 km/h, 2400 rpm topspin) through the real yt_rally2
calibration, project it to **noise-free** pixels, hand it to the same
`fit_anchored` the pipeline ships, and walk the launch point along its own
viewing ray:

| launch height | recovered speed | error | reproj | passes 6 px gate |
|---|---|---|---|---|
| 0.3 m | 54.6 km/h | −37% | 0.14 px | YES |
| 1.0 m | 83.4 km/h | −4% | 0.01 px | YES |
| 2.0 m | 114.1 km/h | +31% | 0.01 px | YES |
| 3.0 m | 151.5 km/h | +74% | 0.02 px | YES |

**A 2.8x span of shot speeds all reproject under 0.15 px.** Identical result at
60, 30 and 24 fps — this is geometry, not sampling. A hit→bounce arc pinned only
at its bounce leaves the launch point free to slide along its viewing ray, and
the fit trades depth against speed (and against the Magnus term) for essentially
nothing in pixels. `reproj_px` measures self-consistency, not truth.

That fully explains the two facts that opened this session:
- the **11,692 / 12,221 rpm** readings — the optimiser absorbing free depth into
  spin, exactly as suspected, but *not* because of timing error;
- and the corollary nobody had checked: with today's bounce-anchor-only fit, the
  ground-truth arc comes back at **+107% (60 fps) to +143% (24 fps)** speed.

**Corrected: `arc_error_budget.py` shows event-timing is NOT the dominant term.**
Anchoring ±2 frames off costs only 1.5→3.4 px of reprojection at 120→24 fps,
and all of it passes the gate. Timing error is real but second-order; E3 should
lead with the constraint, not with audio hit detection.

**What breaks the tie [MEASURED]:** an exact contact-height prior recovers the
speed to **−2% (60 fps) / −3% (30) / −4% (24)**. Sensitivity: a height prior
0.25 m wrong costs ~13% of speed, 0.5 m wrong costs ~25%. So the E4 target of
<5% speed MAE needs the launch height to ~0.2 m — which is roughly what pose
(wrist/racket height + the striker's court position via the homography) can
supply. **That is E3's job, and it now outranks everything else in the chain.**

#### 3. Confirmed on real footage, and the gate is fixed [SHIPPED]
`analyze` on yt_rally2 @60 fps produced an arc at **reproj 3.5 px** — inside the
gate — reporting **110 km/h with 10,361 rpm**. It was being promoted to
`speed_source="physics"` with `speed_confident=True` and shown in the dashboard.

Fixed in `speedspin.py`: `ok` now requires a physical plausibility band
(20-250 km/h, |spin| ≤ 3500 rpm) *as well as* the reprojection gate, and every
rejected arc carries a `reject_reason`. That clip's headline speed drops from a
fabricated 110 km/h to the honest plane-average 81.7 km/h. 6 new tests;
114 backend tests pass.

**Consequence for the plan: E3's stated gate — "≥1 arc passes at 6 px with a
physically sane speed" — is satisfiable by noise and must be replaced.** The
right gate is agreement with an independent measurement (OCR'd SwingVision MPH,
or a radar gun), or a demonstrated collapse of the ray-walk speed spread once
the second constraint is in.

#### Not done in E1 (needs the user or a download)
- New gold labels on a clay clip and a 60 fps clip (~15 min blind labelling each).
  The existing yt_rally2 labels carried the fps experiment, so this is no longer
  blocking, but clay is still unmeasured against human clicks.
- The image-level failure taxonomy (smear / too small / occlusion). The
  near-vs-far split above is the part that came free, and it already points at
  apparent size.
- The TrackNet-dataset hit/bounce external check (needs the ~19,835-frame download).

#### Artifacts
`tools/clip_inventory.py`, `tools/arc_error_budget.py`,
`tools/arc_observability.py`, `tools/run_fps_sweep.sh`;
`ball_perception.py --target-fps`, `eval_gold.py --common-frames`;
`data/output/fps/*` (8 fps-swept perception caches + 2 analyze runs + 4 JSON
result files), `data/gold/yt_rally2.fps.md`, `data/output/clip_inventory.json`;
`backend/tests/test_speedspin_gate.py`.
- _E2 pending_
- _E3 pending_
- _E4 pending_
