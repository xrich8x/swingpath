# TODO — what the user wants (plain-language, prioritized)

Living checklist of everything requested, newest thinking on top. Companion to
RESUME_BALLNET_V2.md (the exact commands) and HANDOFF.md §11 (the evidence).

## Done this session
- [x] First HUMAN ball benchmark — nothing self-graded anymore.
  - [x] Browser labeling tool (blind, magnifier, resume) — tools/gold_label_server.py
  - [x] Stratified frame picker + eval scorer — tools/select_gold_frames.py, eval_gold.py
  - [x] Labeled clip 1: yt_rally2 (300 frames)
  - [x] Labeled clip 2: yt_match40 (300 frames, cold generalization clip)
  - [x] Scored all 4 tracks vs my clicks → first honest numbers (HANDOFF §11)
- [x] Rebuild BallNet's training data junk-free + with "no ball" examples
  (21,591 labels + 2,783 negatives; ready to train)

## Next (staged, one command away)
1. **BallNet v2** — retrain so it keeps its strong ball-finding but STOPS
   firing at nothing (v1 false-fires on ~59% of empty frames). Then score it
   against MY clicks on both clips — including yt_match40, which it has never
   seen. Steps in RESUME_BALLNET_V2.md.

## The ball-prediction upgrade (my ask — track smarter when the ball is hard to see)
This is TRACKER logic, separate from v2 (which just sharpens raw detection).
Both to be proven with before/after scores on my two gold clips.

2. **Track only the LIVE ball.** Don't lock onto a ball sitting on the ground,
   a spare ball by the fence, or the next court's ball — only the ball actually
   in play. (Half-handled today: a fully-still ball already gets dropped after
   5 frames; the gap is slow-rolling / spare balls, and only STARTING a track
   on a ball that's just been hit.)
3. **When the ball can't be seen, assume its path from the hit.** On a fast
   serve or put-away the ball blurs out and currently just vanishes mid-shot.
   Instead: the moment it's struck, compute its flight as a physics arc
   (gravity + how hard it was hit + the court geometry) and keep drawing the
   ball along that assumed arc until it's seen again or it bounces. This is
   maths we can compute exactly — not a guess, and not more AI. Doubles as the
   fix for the serve-speed problem below.

## Accuracy fixes I've flagged before
4. **Serve speed reads too high** (e.g. 166 km/h). Root cause: a ball in the
   air gets flattened onto the ground, inflating distance. Fix by measuring the
   ball's height from its arc (same physics as #3), NOT by copying SwingVision.
5. **Ball missing in some shots** — addressed by #1 (better detector) plus
   #2/#3 (better tracking through gaps).

## Optional / whenever
6. Drag yt_match40's court corners (~5 min) to unlock speeds + line-calls on
   that clip too (only needed if I want full analysis on it, not for the ball
   benchmark).
7. Label a 3rd clip for an even broader generalization test.
8. Bigger features later: serve stats, shot-placement/position heatmaps,
   auto-highlight rally clips.

## Ground rules (don't break)
- My gold labels (data/gold/*.labels.json) are a TEST set — never train on them.
- Keep perception = AI, geometry/physics = maths, scoring = rules. Don't
  "AI-ify" the arc maths in #3.
