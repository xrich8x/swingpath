> **STATUS: RUN 2026-08-13 - STOPPING RULE FIRED** — stamped 2026-08-15 during doc cleanup.
> Nothing predicts a findable gap (null control confirms the signal is real but far too weak). BALL-DETECTOR WORK IS CLOSED.
> This file is the PRE-REGISTERED BRIEF, kept for its gate and reasoning.
> For what actually happened and the current state of play, read
> [SCOREBOARD.md](../../../SCOREBOARD.md) — not this file.

# Session L — far-court labels: the last untried input, and a stopping rule

## Where this sits

Session K closed the ball-model era. Eleven attempts have now tried to improve what the
user sees by improving the detector or by filtering after it, and every one has failed at
the product:

| lever | result |
|---|---|
| detector precision — input resolution, `score_thresh`, localised weighting | ×3, none reached the product |
| detector **recall** — +57% data, +5.6 pts pooled, 4.1σ | **×1, Session K: +0.0 pts at the chain** |
| post-hoc filters — `max_gap_s`, suppress params, score threshold, smoother/suppression coherence | all measured negative |
| automatic confuser criteria — pose proximity, racket box (×2), lock kinematics | all failed a pre-registered gate |

**One input has never been exercised: human far-court labels.** 173 of them are already
collected and sitting unconverted.

## Why this one is different — the mechanism, stated before the work

Every previous ball idea was "make the detector better and hope". This one has a chain-level
mechanism, which is the bar Session K set for any further ball work.

`suppress_false_locks`' min-segment test requires a **run of consecutive locks** to keep a
detection. Session L's coherence experiment measured what that filter actually removes:
**~7 real ball frames per ghost frame** — its removals are majority real ball, and they are
far-court balls, which are exactly the ones the detector finds only intermittently.

So the causal chain is:

> more far-court training labels → denser far-court detections → **longer consecutive runs**
> → survive the min-segment test → less recall destroyed by suppression → more ball at the
> product.

That predicts something specific and falsifiable, which is the point:

**PRIMARY PREDICTION (pre-registered):** far-court **run length** rises, and
`suppress_false_locks`' far_geo cost falls below its current 5.0–7.8 pts. If run length does
not move, the mechanism is wrong and the rest of the session is void regardless of what
recall does.

## Steps

### L1 — convert the 173 labels already collected (no GPU, ~1 h)

`farcourt_cal1` (96 ball / 25 no-ball / 26 unsure) and `farcourt_pilot2` (77 / 5 / 8) are
labelled and audited and have never been turned into training data.
`tools/farcourt_labels_to_dataset.py` exists and enforces the anchor control.

**Gate:** the converter's own round-trip check must pass on every clip (argmin of mean-abs
diff over ±3 frames, with its margin reported). A clip that declares itself unresolvable is
dropped, not forced.

⚠️ `farcourt_pilot` (the first 36) is marked `contaminated` and must stay excluded.

### L2 — measure the yield before spending hours (no GPU, ~1 h)

Session J found the anchor control measures *agreement with the tracker*, not correctness,
and the "it has to move" rule was added to the labelling page but **never validated on a
round labelled under it**. Both the 42% (pass 1) and 78% (pass 2) yield figures are
therefore unusable for sizing.

Label **one round of 30 gaps** and score it against the pre-registered separation from
Session J: a real ball moves 17–116 px across a gap, a mistaken static object 1–8 px.

**Gate:** ≥60% of gaps yield a click whose inter-frame motion exceeds the static band. Below
that, the queue is not producing usable far-court labels and L3 must not be run — it would
be hours of clicking for labels that teach the detector to fire on wall marks.

### L3 — label to scale (human time, ~4–5 h)

Only if L2 passes. Target **300–500 far-court positives**, even round-robin across clips
(decided in Session J). The queue has 2,677 gaps available, so selection is not the
constraint.

### L4 — retrain and score, in that order (GPU ~2 h + ~15 min)

`--seed 0`, one variable, against the arm-A-style control. Score at the **detector** first,
then at the **chain**.

**Gates, in this order** (the ordering is load-bearing — Session F's threshold change would
have passed the ghost gate and only the recall gate, deliberately first, caught it):

1. **Mechanism:** far-court run length rises; suppression's far_geo cost falls below 5.0 pts.
2. **Detector:** far_geo recall rises on ≥2 of 3 calibrated clips.
3. **Product:** pooled chain recall rises ≥2 pts over v21's **66.9%** with solid ghosts not
   above **9** (baseline 19 fires = 9 solid + 10 faded, 532 ball / 74 no-ball frames).

## The stopping rule — write it down now, not after the result

This project has spent eleven attempts on the ball. If L4 fails **gate 1**, the mechanism is
disproved and far-court labels are not the lever either. At that point:

> **The ball detector is at its floor for this data scale, and further ball work is
> closed.** Effort moves to what the camera and the geometry can still buy — mount height
> guidance (measured: 54% → 81% close-call accuracy from 1 m to 8 m) and frame rate
> (measured: +5.8 pts at 1.5 m) — both of which are *already quantified* and neither of
> which needs a model.

Deciding this in advance is the only way it gets decided honestly.

## Explicitly NOT in this session

- **Scoring, rallies and highlights** — deprioritised by the user, 2026-08-13. The research
  stands (`gap_s = 2.0` is the named suspect, ~1.6× over-split, and three clips carry a
  burned-in point-by-point score that would make it measurable). Parked, not lost.
- **Any further detector-precision idea** — four for four. Needs a chain-level mechanism
  first, same bar as this session.
- **SwingVision data** — permanently out per user rule; enforced by
  `train_ballnet.assert_no_swingvision_leak`, which refuses to start on an unscrubbed
  overlay clip.

## Parallel track — no GPU, no dependency on L (~1 evening total)

These are unblocked and can be done in any gap:

1. **Off-machine copy of `data/train_clips/` (1.06 GB).** Gitignored, tracked by nothing,
   and only 10 of 12 clips are recoverable by YouTube id. The dataset regenerates from the
   videos; the videos do not regenerate. *Unbounded downside, one evening.*
2. **Re-label the 8 known-bad `am_indoor_hard1` court frames** (marked `court: false` but
   plainly showing a usable court) and **adjudicate the 2 ambiguous ghost frames**
   (`yt_rally2:1494`, `am_hard_utr:13276` — a light object beside a mid-swing player on a
   "no ball" frame). Until then two metrics are not valid. *Minutes of clicking.*
3. **The 60 fps product call.** Measurement is complete: 60 fps wins measurement decisively
   (arc reproj 148 → 91 px, HUD speed MAE 38.9 → 33.1%), is a wash on detection, costs 2×
   perception, and needs **no** re-tune (`max_gap_s = 0.4` already correct at both rates).
   A decision, not a task.

---

## Results — L1 and L2, run 2026-08-13

**L2: GATE FAILS at 47%** (bar was ≥60%). Measured on `farcourt_cal1`, 49 gaps — which
turns out to be the validation round the step called for: it was labelled at 21:50, thirty
minutes after the "a ball is somewhere different on every frame" rule shipped at 21:20.

**The rule did not work.** `cal1` (after) is *worse* than `pilot2` (before), 47% vs 60%
ball-like click motion. **Seventeen of 49 gaps have the human clicking the identical pixel
on both frames.** A written instruction on the page is not a control.

**So L3 does not run**, per the gate. And the diagnosis has moved: the far-court lever is
**not blocked on labelling effort, it is blocked on queue selection** — 41% of gaps present
no findable ball, and at a 35% both-filters yield, 300 positives would need ~860 gaps
(~2,580 frames) clicked.

**L1: COMPLETE.** **105 human far-court ball labels** across 21 dataset dirs, every sample
round-trip verified. Four defects found and all four fixed:

- the motion test is **now enforced** — its threshold finally reproduced on an independent
  round (bimodal, valley at 9–16 px), which was the only thing blocking its use;
- the round-trip gate counted an exact **tie** as a mismatch (`argmin` decided by dict
  order); now judged as unresolved on the same margin;
- the gate ran *after* the write, leaving unverified data in the pool on failure; it now
  removes the directory.

- what looked like a **+2/+3 frame offset** was the gate's own index mapping: `build()`
  numbers triplets by position in the usable-frame list and drops `unsure` frames, while the
  gate re-derived that list and kept them. Sequential decode (no seeking) proved the build
  exact to MAD 0.0000. The only two failing clips were the only two with an unsure label;
  19 with none passed. The rule now lives once, in `labels_to_dataset.usable_frames`.

Evidence: `data/output/farcourt_l2.md`.

### Revised next steps

1. Fix (or exclude) the frame-offset clips.
2. **Move the anchor control from label time to selection time.** It currently runs after
   the human has spent the effort. Session J already measured that local roam and
   `suppress_false_locks` both fail as selection screens, so this needs a new idea.
3. Only then L3, and re-run the L2 gate on the first 30 gaps of it before committing hours.
