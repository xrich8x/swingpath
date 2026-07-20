# Session E (multi-session arc) — The ball stack: tracking → trajectory → arc → speed + spin

**Kickoff prompt:** `Start Session E<n> (docs/sessions/SESSION_E_ball_push.md)`
**User brings:** real footage (more = better) AND ~15 min of blind labeling per new
gold clip (browser tool, same flow as the court labels). Gold labels are TEST
data — the NEVER-train-on-gold rule is absolute.

---

## The five workstreams, and why they are ONE arc

The user asked for tracking, spin, arc, trajectory, and speed. They are not five
independent features — they are a **dependency chain**, and every downstream
number is currently blocked by the same two upstream failures:

```
1. TRACKING  (where is the ball in the image?)        ← 22-33% on clay, 74% indoor
        ↓
4. TRAJECTORY (where is the ball in 3D, over time?)   ← we assume z=0. THE gap.
        ↓
3. ARC       (fit one hit→bounce flight, physics)     ← exists; rejected at the gate
        ↓
5. SPEED     +     2. SPIN                            ← both fall out of the arc fit
```

Chasing spin or speed before trajectory is fixed is chasing symptoms. The order
below is the honest one; each session ends with numbers, not vibes.

---

## Current honest state (measured, in-repo)

| # | Area | Where it lives | State |
|---|---|---|---|
| 1 | Tracking | `ball.py` (TrackNet/WASB/fusion + `BallTracker`), `_ballnet.py` | Detection **22-33%** of frames on worn outdoor clay 720p vs **~74%** indoor/broadcast. Static-fixture gate + live-ball filter working. |
| 4 | Trajectory | `ball.smooth_and_fill` → project to court **plane** | **The architectural gap: z is assumed 0.** An airborne ball is projected as if it were rolling. Documented in CLAUDE.md as a known single-camera reality. |
| 3 | Arc | `speedspin.py` + `ball_physics/tennis_tracker` (drag+Magnus simulator, `trajectory_fit`, bounce-anchored) | Framework is REAL and complete. Gate is `reproj_max_px = 6.0`. Measured arcs: tennis_sample **13.1 / 20.8 / 284 px**, e2e clay **58 / 61 px** → *everything rejected*. |
| 5 | Speed | `analytics.shot_speed_kmh` (headline) + physics speed | Headline = path length ÷ time on the **plane** → ~15-20% under radar by construction. Physics speed is ~4% on synthetic but gated off (above). Post-lens-fix tennis_sample read 118-141 km/h @ 4.2-4.6k rpm — *physically realistic*, still rejected on reproj. |
| 2 | Spin | `events.classify_spin` (pose heuristic) + physics `spin_rpm`/`topspin_rpm` | Heuristic v1 **unvalidated** (disagreed with SwingVision's burned-in label on yt_rally2). Physics spin blocked with the arc. `ball_physics/estimation/spin_net.py` + `train_spin_net.py` exist but are unexercised. |

**Assets we already own and under-use:** `ball_physics/tennis_tracker/data/synthesize.py`
(physics-simulated trajectory generator), `physics/simulator_torch.py`
(differentiable simulator), `estimation/spin_net.py`, `eval/metrics.py`. The
synthetic-to-real path the literature now favours is *already scaffolded here*.

---

## Research (2025/26) — the approaches worth adopting

### Tracking (workstream 1)
- **TrackNet lineage:** V2 = MIMO consecutive-frame heatmaps (our vendored arch).
  **V3** adds trajectory rectification + **inpainting of missed detections**;
  **V4** adds motion-attention from frame differences; **V5** (Dec 2025) adds
  residual spatio-temporal refinement + motion-direction decoupling. V3/V4's
  ideas target our exact failure (small far ball, blur, dropouts).
- **WASB** (HRNet backbone) is the strong cross-sport baseline — already in our
  stack and it *wins the per-clip probe* on amateur 720p.
- **BlurBall** (2025): joint ball + motion-blur estimation — blur as a *label*,
  not an augmentation. Matches our own finding (blur-aug alone was a dead end;
  visibility-weighted occlusion training won).
- **RacketVision** (Nov 2025): multi-racket-sport benchmark with ball
  annotations — candidate EXTERNAL training data; check the license before use.

### Trajectory + arc (workstreams 4, 3)
- Monocular 3D ball reconstruction = **physics-based model fitting to the 2D
  track**, i.e. depth is recovered by requiring the flight to obey ballistics
  (gravity + drag + Magnus) rather than by seeing it. This is exactly what
  `speedspin.py` does by anchoring each flight at its bounce (bounce = a known
  z=0 point, which pins the otherwise-ambiguous depth).
- Known failure modes named in the literature, all of which we exhibit:
  **model drift**, sensitivity to **inaccurate key-event identification**
  (our bounce/hit timing!), calibration error, and insufficient video quality.
- Standard remedy: a **Kalman/EKF with a ballistic motion model** to suppress
  measurement noise and enforce physically plausible trajectories, i.e. *filter
  in 3D physics space, not in 2D pixel space* — and mixing the physical model
  with the geometric model beats either alone.

### Spin (workstream 2)
- Spin is **not directly observable** in normal video (no seam resolution at our
  pixel scale) — it is *inferred from trajectory curvature* via the Magnus
  effect, and from bounce behaviour.
- The current best monocular result (table tennis, CVPR 2025 workshop):
  **physically grounded synthetic-to-real transfer** — train on physics-simulated
  trajectories, apply to real broadcast video: **92.0% spin classification
  accuracy**, 0.19% image-diagonal reprojection error. Follow-up work ("Uplifting
  Table Tennis", Nov 2025) hardens this for real-world 3D trajectory + spin.
- Tennis is friendlier than table tennis on some axes (bigger ball, slower rpm)
  and harder on others (much longer flights, outdoor light) — treat their numbers
  as method validation, not as our expected accuracy.

**Sources**
- [TrackNetV4: motion attention maps (arXiv 2409.14543)](https://arxiv.org/pdf/2409.14543)
- [TrackNetV5: residual spatio-temporal refinement (arXiv 2512.02789)](https://arxiv.org/pdf/2512.02789)
- [BlurBall: joint ball + motion-blur estimation (arXiv 2509.18387)](https://arxiv.org/html/2509.18387v1)
- [RacketVision benchmark (arXiv 2511.17045)](https://arxiv.org/html/2511.17045v3)
- [Ball spin + trajectory via physically grounded synthetic-to-real transfer (CVPRW 2025)](https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Kienzle_Towards_Ball_Spin_and_Trajectory_Analysis_in_Table_Tennis_Broadcast_CVPRW_2025_paper.pdf)
- [Uplifting Table Tennis: real-world 3D trajectory + spin (arXiv 2511.20250)](https://arxiv.org/pdf/2511.20250)
- [TT4D: monocular 4D reconstruction pipeline + dataset (arXiv 2605.01234)](https://arxiv.org/html/2605.01234)
- [3D ballistic shot reconstruction from monocular video (IEEE)](https://ieeexplore.ieee.org/document/10312079/)
- [3D ball trajectory from a single camera, cricket (TechRxiv)](https://www.techrxiv.org/doi/10.36227/techrxiv.176761698.86519755)

---

## Session plan

### E1 — Measure: gold labels + the failure taxonomy *(do this first; it decides everything after)*
1. Gold-label ball on the two analyzed clay clips + one indoor clip
   (`select_gold_frames` → user labels ~300 frames blind, stratified toward
   far-court and rally time).
2. Score EVERY current detector on the new gold via `eval_gold.py`
   (tracknet / wasb / fusion / ballnet_v2 / ballnet_visweighted) → the honest
   per-surface baseline table.
3. **Failure taxonomy with images** — every miss classified: motion smear /
   too small / low contrast vs surface / occlusion / left frame. This is the
   fork in the road:
   - smear-dominated → BlurBall-style blur labels (E2a)
   - size/contrast-dominated → **inference-side first**: native-res or tiled
     far-court crops, WASB threshold sweep, motion-difference input channel
     (zero training, could be a step change)
   - background-confusion → hard negatives (HUD/fixtures/adjacent court/edges)
4. **Arc-gate diagnosis in the same session** (cheap, high information): for the
   rejected arcs, is `reproj_px` dominated by (a) bad bounce/hit *timing*, (b)
   too few real detections in the arc, or (c) the z=0 projection? Re-fit a
   handful of hand-picked clean arcs with hand-corrected event frames and see
   what reproj does. This tells us whether E3 is a detection problem or a
   physics-plumbing problem *before* we spend a session on either.
   **Gate:** honest baseline table + taxonomy counts + arc diagnosis, written
   into this file's Results.

### E2 — Tracking: close the detection gap
Driven by E1's taxonomy, cheapest-first: inference-side experiments → hard
negatives / blur labels → architecture (V3-style trajectory rectification +
inpainting is the highest-value upgrade; V4/V5 motion priors next).
**Gate:** per-surface hit@10px on gold must beat the E1 baseline, with
false-fire on no-ball frames not worse. No training on gold, ever.

### E3 — Trajectory + arc: get the physics fit to PASS
1. **3D trajectory, not plane trajectory.** Introduce ball height: use the
   physics fit as the estimator of z (bounce-anchored, as now), then *keep* the
   3D track instead of collapsing to the plane. Store it in the perception cache.
2. **Ballistic filtering** — EKF/smoother with the ballistic model over the 3D
   state, replacing plane-space `smooth_and_fill` for in-flight segments
   (keep the existing filter for gap-filling detections).
3. **Event timing refinement** — sub-frame hit/bounce times by fitting the arc
   on both sides of the event (the literature names key-event error as a top
   cause of monocular failure; our bounce detector is an admitted heuristic).
4. Re-measure `reproj_px` distribution vs the 6.0 gate.
   **Gate:** a real (non-synthetic) clip produces ≥1 arc passing at 6 px, and
   the accepted arcs' speeds are physically sane; line calls and bounce
   positions must not regress (they ride the same track).

### E4 — Speed + spin: turn passing arcs into trustworthy numbers
1. **Speed:** promote physics speed to the headline when the arc passes; keep
   the plane-average as the labelled fallback (`speed_source` already exists).
   Validate against any ground truth we can get (SwingVision's burned-in MPH on
   sourced clips = free labels via OCR; radar if the user ever has one).
2. **Spin:** two independent estimators, cross-checked —
   (a) physics `spin_rpm`/`topspin_rpm` from the passing arc;
   (b) the pose heuristic (`classify_spin`), currently unvalidated.
   Where they disagree, report the physics value and flag it; where the arc
   fails, report the heuristic as *style only* (topspin/slice), never an rpm.
3. **Synthetic-to-real spin net (stretch, follows the CVPR-2025 recipe):**
   `ball_physics/data/synthesize.py` + `simulator_torch.py` already generate
   physics-true trajectories with KNOWN spin — train `spin_net.py` on simulated
   arcs, test on real gold arcs. This is the one place where *training on
   synthetic* is not a leak, because the labels come from the simulator.
   **Gate:** OCR-validated speed error stated per surface; spin reported only
   where an arc passed; every unvalidated number labelled as such in the UI.

---

## Guardrails (hard-won — do not relearn)
- Custom BallNet did **not** beat off-the-shelf on unseen footage; prior "wins"
  were data leaks. Measure on gold via `eval_gold.py` only.
- Dead-time negatives were the WRONG negatives; hard negatives are the fix.
- The live-ball trajectory filter was the single biggest false-fire win — keep
  it in every evaluation loop.
- Speed is honest-by-construction today (average, ~15-20% under radar). If a new
  method reports higher numbers, prove it against ground truth before shipping —
  do NOT "fix" speed to match TV.
- Never report an rpm from a failed arc. `speed_confident` / `call_confident`
  already exist — use them rather than inventing numbers.

## Results (fill in per session)
- _E1 pending_
- _E2 pending_
- _E3 pending_
- _E4 pending_
