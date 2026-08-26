# PM Review Prompt

A standalone version of the `/pm-review` skill. Paste the block below into any
Claude Code chat box in this repo — a fresh session, one without the skill
installed, or one you're handing to someone else — to get the same review
without depending on any config being in place. If `.claude/skills/pm-review/`
already exists in this repo, typing `/pm-review` does the same thing.

**Corrected 2026-08-15:** the racket clause used to say confuser filtering tops
out at 55% because ball and racket "are genuinely close in apparent size". Both
halves were wrong — a racket is 10x a ball, and the measured reason negation
failed was that COCO found the *near* player's racket while the detector fired
on the *far* player's. A prompt that encodes a wrong cause hands it to every
future review, which is Trap T19 in [docs/TRAPS.md](docs/TRAPS.md) — the same incident, named
there as reading a detection RATE as evidence the detector found the right thing.
(Traps moved out of SCOREBOARD.md into docs/TRAPS.md on 2026-08-17, after this note
was written, and were re-keyed to stable IDs T01-T22 on 2026-08-26; T19 is the same
trap it always was.)

---

You're producing a PM briefing for the non-technical PM on this SwingVision
tennis-video-analysis project (single-camera video -> match.json -> React
dashboard). I cannot read code. Ground yourself before judging anything:

1. Look back through this conversation (or, if it's fresh, run `git log
   --oneline -15` and `git diff` / `git status`) for what was actually done
   recently — files touched, decisions made, walls hit, numbers reported.
2. Read CLAUDE.md's most recent Status entries and Gotchas section, and all
   of docs/STATE.md — especially "What has not worked" — and of docs/TRAPS.md. Do not
   evaluate anything without checking it against that table first; this
   project's biggest recurring risk is re-proposing an idea already measured
   and killed.
3. If the work touched any model (ball, court, pose), read ML_PRACTICES.md
   and ML_PLAYBOOK.md — required reading per CLAUDE.md for any ML work.

Then hold it against real-world ground truth, not just the code's own
comments: a tennis court is fixed regulation geometry (23.77m
baseline-to-baseline, 10.97m doubles / 8.23m singles width, net at 11.885m,
service line 6.40m from net — backend/swingvision/court.py, mirrored in
frontend/src/lib/court.js); a ball is ~6.7cm and a racket ~68cm, so at
far-court range a racket HEAD subtends roughly what a near ball does — that
is why the BALL DETECTOR confuses the two, but it is NOT why racket-box
negation failed. That failed for a separately measured reason: stock COCO
racket detection kept finding the NEAR player's racket while the detector was
firing on the FAR player's (locks sat 737-869px from the nearest box), and
racket-head position is statistically indistinguishable from a real ball
(0.57 vs 0.55 on the wrist-to-head axis). Its catch rate also re-scored to
23.3% on the current detector, not the 55% first reported — cite STATE's
"Racquet-box negation" row, not the size argument.

Also true of the physical world here: a ball in flight obeys gravity, drag and
(at speed) Magnus, never a straight line or a hover; scoring is standard
tennis only (deuce/ad, tiebreak at 6-6, best-of-3); and the camera is assumed
fixed and often low-mounted (1-2m, amateur footage), not broadcast TV, so
measurable accuracy is a direct function of that height.

And hold it against real ML/CV technique, not a vibe check: diagnose any
model weakness into one of five buckets before accepting a fix —
evaluation/leakage, data, domain shift, architecture/representation, or
optimization (a fix aimed at the wrong bucket wastes a training run). Check
any proposed fix against STATE's "What has not worked" table BEFORE
recommending it — if it's a variant of something already killed (raise the
score threshold, lower the court-consensus vote bar, negate on a racket
box, add training data alone, tighten a gate radius), say so and cite the
row. Know what's actually shipped: BallNet is a TrackNet-style heatmap CNN
(512x288, 3-frame stack, easily confused with racket heads and HUD
graphics — this project's most-fought failure mode); smoothing is a
constant-acceleration Kalman + RTS filter that interpolates gaps but must
never extrapolate; court detection is line-fit consensus first, a CourtNet
heatmap model second; pose is YOLO-pose. Apply the project's #1 rule: a
number means nothing without stating what it was measured against — "84%
accuracy" alone is not usable, "84% agreement with held-out human gold
clicks, never trained on" is. And remember the project's own hard-won
finding: a detector-level gain has repeatedly failed to reach the actual
rendered output, so a better detector number is not by itself evidence the
product got better.

Now give me, in plain English, specific to what actually happened (not
generic advice):

1. **What just happened** — translated out of code jargon.
2. **Does it still serve the goal** — has focus drifted from what moves the
   product (the gold-benchmark numbers, the rendered dashboard) or from what
   was actually asked for?
3. **What's quietly hampering the feature** — fragile workarounds, debt, a
   weakened guardrail, a number that isn't really independent evidence. Name
   the file or decision, not just the vibe.
4. **Recommended next steps** — concrete, prioritized, checked against the
   dead-end table so nothing on the list has already failed. Rough cost and
   what it's waiting on.
5. **Cut-or-keep call** — if something isn't worth its cost relative to what
   it delivers, say so plainly and explain why. If nothing qualifies, say
   that plainly instead of manufacturing a verdict.

If a section has nothing real to say, say that in one line rather than
padding it.
