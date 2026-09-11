# SPEC.md — Live Court + Ball Tracking, v1 target spec (LOCKED)

**Founder spec, 2026-09-11. LOCKED.** These are pre-registered bars under hard rule 2: a target
here is not moved to fit a result.

**Amended the same day, by the founder, on four points:**
1. **Latency is INSTANT, not 2 s** (§8 rewritten). The original 2 s bar is withdrawn.
2. **Use the Neural Engine — or anything else that makes it work.** The spec's original
   "CPU-only" framing is withdrawn; hardware acceleration is a v1 tool, not a v2 upgrade.
3. **iPhone only.** Every Android reference is struck.
4. **§6 (occlusion prediction) and §9 (skeletal analysis) are OUT of v1** — "toss 6 and 9, we can
   evaluate as we move on." Both are preserved below, struck through, because their bars were
   reasoned and should not be re-derived from scratch when they return.

**Nothing in this file has been measured yet.** It is the bar, not the state. State lives in
`docs/STATE.md`.

---

## 1. Live 3D court mapping

- **Drift check:** every frame, track 4–8 court line-intersection points by optical flow. Trigger a
  full recalibration if mean reprojection error on those tracked points exceeds **15 px sustained
  for 3 consecutive frames** — single-frame spikes are noise, not camera movement.
- **Forced fallback recalibration:** full court re-solve every **10 s** (600 frames @60 fps)
  regardless of the drift signal, as a backstop.
- **During recalibration:** freeze the last-known court model and hold all ball calls until the new
  model passes the existing **8-frame vote (≥6/8)** — the same bar as static court detection today.

## 2. Capture requirements

- **Frame rate: 60 fps minimum, HARD requirement.** Below 60 fps, do not attempt bounce detection at
  all — report unsupported.
- **Resolution: 1080p minimum.**
- **Mount:** fence-mount or tripod for v1. **Handheld is explicitly out of scope** — its jitter
  profile needs separate tuning of §1's drift detector and will produce unreliable calls if forced
  through fence-mount thresholds.

## 3. Ball calls + landing accuracy

- **Target: 10 cm.** Applies to landing-call accuracy generally, but the validation set weights
  toward near-line landings (§7) — that is where 10 cm actually gets tested.
- **Measurement basis:** 10 cm applies to calls the system **actually makes**. With §6 out of v1,
  that means **directly detected bounce frames only** — an occluded bounce is a refusal, not a
  silent miss and not a bridged guess.
  **CONSEQUENCE, stated plainly: the ≤5% refusal target below is now almost certainly unreachable.**
  It was written assuming occlusion bridging carried the hard cases. Every bounce hidden by a player
  is now a refusal. Treat ≤5% as provisional until measured; the honest number may be far higher,
  and that is a v1 finding, not a v1 failure.
- **Detection on unoccluded frames: recall ≥92%, precision ≥98%.** Precision is weighted higher
  deliberately — a false positive near a line can corrupt a call outright, where a missed frame only
  degrades confidence.
- **Reacquisition after occlusion:** ball re-locked within **3 frames (~50 ms @60 fps)** of becoming
  visible again.
- **Abstention:** refuse the call if the tracking filter's position-uncertainty exceeds **10 cm at
  1σ** at the bounce frame. Target refusal rate on contested (near-line) calls: **≤5%**. A nonzero
  refusal rate is expected behaviour, not failure — SwingVision's single-camera setup is documented
  as occasionally unable to call at all.

## 4. Bounce detection

- **Method: vertical-velocity sign reversal.** NOT nearest-frame-to-court-plane.
- **Timing: ±1 frame (16.7 ms @60 fps) 90% of the time; ±2 frames 99% of the time.**
- **Spatial:** inherits §3's 10 cm, validated as its own metric on the gold set (§7) rather than
  assumed from general in-flight accuracy.

## 5. Trajectory prediction — physics model

- **Model: drag + Magnus.** Not a pure parabola.
- **In-flight tracking error (ball visible): ≤15 cm RMS over any 0.5 s window** against the
  human-labelled trajectory.
- **3D height:** monocular depth-from-known-ball-size (**diameter ≈ 6.7 cm**) for v1. **This is the
  weakest-precision part of the whole system — flag it as such in any UI or output** rather than
  presenting height with the same confidence as the 2D landing point.
- **Stereo / second camera: DEFERRED to v2.** Not realistic on a single-phone pipeline.
- **This section stands.** Drag+Magnus and depth-from-known-ball-size are v1.

## 6. ~~Prediction through occlusion~~ — **OUT OF v1** (founder, 2026-09-11)

> Kept struck-through, not deleted: the bars below were reasoned and should not be re-derived when
> this returns. **Nothing here is in scope. Do not build it.** With it gone, an occluded bounce is
> a refusal (see §3). The 4-class proxy spin defined here goes with it — **v1 has no spin output.**

- **Contact-event detection:** separate detector — racket/arm pose plus a sudden ball
  velocity-vector change.
- **Spin: proxy classification only, 4 classes** — flat / slice / topspin / heavy topspin — inferred
  from racket swing-path angle and, when available, post-bounce curvature. **Literal RPM-level spin
  is DEFERRED to v2**: out of reach at 60–120 fps on-device; would need higher fps or a purpose-built
  high-speed rig.
- **Reconciliation filter: extended or unscented Kalman.** Not a plain linear KF — confirmed
  unreliable for spin-curved trajectories.
- **Occlusion error-vs-duration curve** (starting targets — validate and adjust empirically, do not
  treat as fixed doctrine):

  | Occluded for | Predicted position error | Call |
  | --- | --- | --- |
  | ≤150 ms (≤9 frames @60 fps) | ≤10 cm | allowed, same bar as a direct detection |
  | 150–400 ms | ≤25 cm | allowed **only if** the predicted margin from the line exceeds the error bound; otherwise refuse |
  | >400 ms | — | **refuse.** No call, report insufficient data |

- **Ground-plane constraint:** applied for all landing-call predictions, so the physics prediction
  intersects the court plane rather than letting height drift freely through the occlusion window.

## 7. Validation methodology

- **Ball-call gold set pass bar (v1): ≥90% of near-line contested calls within 10 cm** of the
  human-marked point. Not SwingVision's 97% from day one — that is the v2 target once the pipeline
  is proven; 90% is the strict-but-achievable v1 bar.
- **Bounce-timing pass bar: ≥90% within ±1 frame, ≥99% within ±2 frames** (matches §4).
- **Occlusion gold set — NEW, REQUIRED before §6 ships:** real points with known occlusion duration,
  labelled for reappearance position and true path where determinable. **No occlusion-duration curve
  target counts as validated until this set exists and has been run against.**
- **Surface/lighting split:** validated across the splits already tracked for court detection (hard,
  clay, indoor shell). A ball-calling target that only holds on hard courts is not a passing target.

## 8. Latency — **INSTANT** (amended 2026-09-11)

- **Live line-calling (v1): the call is INSTANT.** The original 2 s bar is **withdrawn by the
  founder**. Treat the budget as **one frame at 60 fps = 16.7 ms** end-to-end for the per-frame path
  (detect -> track -> physics update), with the call emitted on the bounce frame itself.
- **Use the Neural Engine, or whatever makes it work.** Hardware acceleration is a v1 tool. The
  previous "CPU-only" framing is withdrawn, and with it the idea that sub-second is a v2 upgrade.
- **THE HONEST POSITION, because rule 1 requires it:** nothing in this repo has ever been measured on
  the ANE. The current pipeline runs **0.7-1.1 s/frame on CPU** — roughly **60x** over budget.
  Dropping §6 and §9 helps a great deal (no pose model, no occlusion predictor, ball + court +
  physics only, which is exactly `live.py`'s design), and the ball net is ~2 MB. **This is now the
  single largest unknown in the project and it sits on the critical path.** It is measurable today
  with the harness that already builds — it needs a phone, not more code.
- **Post-hoc / highlight generation:** no hard latency requirement.

## 9. ~~Skeletal & body-physics analysis~~ — **OUT OF v1** (founder, 2026-09-11)

> Kept struck-through for the same reason. **v1 uses NO pose of any kind** — not a custom model,
> not Apple Vision. The ±15% fence below was the right design and should be restored verbatim if
> pose ever returns, because it is what stops body language becoming evidence.

**Purpose: a secondary, corroborating signal.** Used when the ball itself is unresolvable (occlusion
past §6's confident window, or fully out of frame) to *inform*, never replace, a call. It gets no
10 cm-level accuracy target; it is a confidence modifier with a hard boundary so it never quietly
becomes primary evidence.

- **Model: the platform's NATIVE on-device pose estimation** (Apple Vision body-pose — iPhone only;
  the original Android ML Kit reference is struck, rule: iOS/iPadOS only), not a custom
  trained model. A custom pose model is real ML scope this pipeline has not taken on. **Custom model:
  deferred to v2, only if the native API proves insufficient.**
- **Keypoints:** shoulders, hips, wrists (racket-side), ankles/feet. Enough for weight-transfer and
  body-rotation/reach signals — not full biomechanical detail.
- **Sampling: 15–20 fps, not 60.** Body mechanics change far slower than ball position; running pose
  at ball-tracking rate burns budget for no accuracy gain.
- **Output: qualitative, not coordinate.** "Deep shot likely" / "short shot likely" with a confidence
  score. **Pose cannot produce a landing coordinate and must never be asked to.**
- **HARD LIMIT (non-negotiable):** the pose signal may only adjust confidence within **±15%** on a
  call that **already has ball-based evidence** from §6. It **cannot** convert a refusal into a call,
  and it **cannot** extend §6's 150 ms / 400 ms occlusion budgets. This exists specifically to stop
  "the player's body language suggested a deep shot" from becoming the basis for a call with no ball
  evidence behind it.
- **Classification target: ≥75% on binary deep/not-deep** against human-labelled footage —
  deliberately far coarser than the 10 cm ball target, because this is context, not measurement.
- **Validation set — NEW:** rallies with shot depth established from *ball* evidence, paired with the
  body-pose sequence, so the classifier is checked against ground truth rather than a human's
  eyeballed guess of what the pose looked like.

## 10. Edge cases

- **Net cord / let:** detect as a distinct mid-flight velocity discontinuity, not a bounce. No
  accuracy target set — v2.
- **Ball leaving frame entirely:** treated as a >400 ms occlusion — refuse.
- **Multiple balls in frame** (ball machine, adjacent court): out of scope v1. Assume single-ball,
  single-court.
- **Doubles alley:** the court model must include doubles lines. **Required for v1**, not optional —
  it is the same court-detection output already in place.
- **Surface/lighting robustness:** blocked on the indoor-shell-court issue. Ball-calling targets
  above **do not apply until that blocker clears**, since ball-calling is downstream of a working
  court model. **Attribution corrected 2026-09-11:** the original spec named *CourtNet*. That is the
  wrong component — CourtNet is the Tier-2 proposer and the classical `courtfit` consensus already
  beats it. The shell failure is a **SEARCH/proposal** problem: on 12 of 20 clips the shipped search
  never once produces a correct court across 8 sampled frames (recall 8/20 = 40%). Fixing CourtNet
  would not touch it.

---

## Summary — v1 vs explicitly deferred

**v1, in scope now:** live 3D court mapping + drift recalibration (§1) · 60 fps / 1080p / fixed
mount (§2) · **10 cm** landing accuracy with abstention (§3) · **±1 frame** bounce timing by
vertical-velocity sign reversal (§4) · drag+Magnus physics and depth-from-ball-size (§5) · **90%**
gold-set pass bar (§7) · **INSTANT** latency on the Neural Engine (§8) · doubles alley (§10).

**v2 — do not let these creep in:** occlusion prediction and proxy spin (**§6, tossed**) · all
skeletal/pose analysis (**§9, tossed**) · handheld mount (§2) · stereo depth (§5) · literal spin RPM
· let/net-cord (§10) · multi-ball (§10) · shot type · shot speed as a shown number · match scoring,
highlights and corrections.

**What v1 outputs, end to end:** where the ball bounced, whether it was in or out, and a refusal when
it cannot tell. Nothing else.
