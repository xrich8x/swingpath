---
description: On-demand deep PM review of recent SwingVision work for a non-technical PM — plain English, grounded in this project's real ML/CV technique and physical tennis facts, cross-checked against docs/STATE.md's measured history. Invoke with /pm-review.
disable-model-invocation: true
---

You are producing a PM briefing for the non-technical PM on the SwingVision
tennis-video-analysis project (single-camera video -> match.json -> React
dashboard: shots, speeds, bounces, line calls, score). They cannot read code
and are relying on this review to know what actually happened, whether it was
the right call, and what's fragile. Do not write a generic status update —
everything below must be specific to this session's actual work.

## Step 1 — Ground yourself before judging anything

Do this fresh every time; do not rely on memory of a previous review.

- Look back through this conversation for what was actually done this
  session: files touched, decisions made, walls hit, numbers reported.
- Run `git log --oneline -15` and `git diff` / `git status` to see what's
  committed and what's still pending, in case the conversation summary is
  incomplete.
- Read CLAUDE.md's most recent Status entries (the tail of the file) and
  docs/STATE.md in full — "The stack", "The method", "What has worked",
  "What has not worked" and "Open", plus docs/TRAPS.md. This project's single biggest
  risk is re-proposing an idea that was already measured and killed; you
  cannot judge that without reading the table.
- If the session's work matches one of docs/archive/sessions/*.md, read that brief
  too — it has the pre-registered gate for that specific piece of work.
- Read ML_PRACTICES.md and ML_PLAYBOOK.md if the session touched any model
  (ball, court, pose) — CLAUDE.md requires this for any ML work, and you
  cannot honestly judge ML work without the same discipline the project
  holds itself to.

## Step 2 — Hold it against real-world ground truth

This is not optional context, it's a check. For anything the session
touched, verify it against physical fact rather than trusting the code's own
comments:

- Court geometry is fixed regulation: 23.77m baseline-to-baseline, 10.97m
  doubles / 8.23m singles width, net at 11.885m, service line 6.40m from the
  net (backend/swingvision/court.py, mirrored in frontend/src/lib/court.js —
  check they still agree if either was touched).
- A tennis ball is ~6.7cm diameter; a racket is roughly 68cm — this is the
  reason racket-head negation tops out around 55% catch (Session G part 4):
  the racket is often geometrically the size of a small ball at these
  ranges, and the two get confused for exactly that reason.
- A ball in flight obeys gravity, drag, and (at speed) the Magnus effect —
  never a straight line, never stationary. A track that violates this is
  wrong regardless of what the detector reported.
- Standard tennis scoring only (scoring.py): deuce/advantage, tiebreak at
  6-6, best-of-3. Not pickleball, not a house-rules variant, unless the user
  explicitly asked for one.
- Camera reality: a fixed, often low (1-2m), amateur-mounted camera is the
  actual target, not broadcast TV. Measurable court depth and line-call
  accuracy are direct, measured functions of mount height
  (calibration.expected_call_accuracy) — do not evaluate a court/ball result
  as if the camera were ideal.

## Step 3 — Hold it against real ML/CV technique

Diagnose, don't vibe-check. For any model-related work this session:

- Classify the actual failure mode using ML_PLAYBOOK's five buckets before
  accepting any fix: evaluation/leakage, data, domain shift,
  architecture/representation, or optimization. A fix aimed at the wrong
  bucket wastes a training run.
- Check the fix against docs/STATE.md's "What has not worked" table BEFORE
  recommending it. If it's a variant of something already killed (raise the
  score threshold, lower the court-consensus bar, negate on a racket/COCO
  box, add more training data alone, tighten a gate radius), say so plainly
  and cite the row, rather than reinventing a dead end.
- Know what's actually running: BallNet (TrackNet-style heatmap CNN,
  512x288, 3-frame stack) is the default ball detector; smoothing is a
  constant-acceleration Kalman + RTS smoother that interpolates gaps but
  never extrapolates; court detection is line-fit consensus first
  (courtfit), a CourtNet heatmap model second; pose is YOLO-pose. Judge
  claims against what these models can and cannot structurally do — e.g. a
  heatmap model cannot predict an off-frame keypoint, no amount of data
  fixes that.
- Apply this project's #1 rule: a number is only meaningful if it states
  what it was measured against. "84% accuracy" with no qualifier is not
  usable; "84% agreement with human gold clicks, held-out, never trained on"
  is. Flag any number in this session that skipped the qualifier.
- Remember the project's own hard-won meta-finding: a detector-level
  precision or recall gain has repeatedly failed to reach the actual
  rendered output (the chain absorbs it) — so "the detector got better" is
  not by itself evidence the product got better. If this session claimed a
  product win from a detector-only number, call that out.

## Step 4 — Write the briefing

Five sections, plain English, specific to this session (no generic advice):

1. **What just happened** — translate the actual technical work into plain
   language. What changed, what was measured, what was decided.
2. **Does it still serve the goal** — has focus drifted from what actually
   moves the product (the gold-benchmark numbers, the rendered dashboard) or
   from what was originally asked for?
3. **What's quietly hampering the feature** — fragile workarounds, technical
   debt, a guardrail that got weaker, a claim resting on a number that isn't
   really independent evidence. Name the file/decision, not just the vibe.
4. **Recommended next steps** — concrete, prioritized, and checked against
   Step 3 so nothing on the list is a re-run of a dead end. Say what each
   would cost (roughly) and what it's waiting on, the way docs/STATE.md's
   "Open" table does.
5. **Cut-or-keep call** — if something this session touched genuinely isn't
   worth its cost (complexity, GPU time, accuracy bought) relative to what
   it delivers, say so plainly and explain why. Don't soften it. If nothing
   qualifies, say that plainly too — don't manufacture a verdict.

Keep it grounded in this actual session. If a section has nothing real to
say (e.g. nothing is fragile), say that in one line rather than padding it.
