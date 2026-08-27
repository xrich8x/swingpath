---
name: point-boundary-ground-truth
description: Point boundaries are two different problems with two different ceilings — the count is near-perfectly agreeable, the exact frame is not; and boundaries are LOGIC so labels are for evaluation only
metadata:
  type: project
---

Researched 2026-08-27 for R4, against `[[../pm-agent/score-layer-reopened-no-ground-truth]]`.

## Split the problem before costing it

1. **How many points, and roughly where** — needed for clip segmentation and scoring.
   Humans agree on this essentially perfectly; a point is a discrete countable event.
2. **The exact boundary frame** — genuinely ambiguous, and the product does not need it,
   because clips get padding.

Published human agreement on temporal action extents (Sigurdsson et al., ICCV 2017,
re-annotating Charades and MultiTHUMOS): **72.5% and 58.7% mean tIoU**, with **median
start error 0.9 +/- 0.8 s and end error 1.4 +/- 1.4 s** — the *end* is the ambiguous
half, which maps exactly onto "when did the point stop". Agreement rises with activity
duration, and a tennis point (5-30 s) is longer than a Charades action, so expect better
than 72.5% — but do not quote a number that has not been measured on tennis.

**Consequence: any point-boundary metric must be tolerance-based** (event-spotting within
+/- N seconds, plus a count/alignment score), never tIoU against a single annotator's
frame. Publishing a tIoU here would be measuring annotator noise.

## The labelling cost is an order of magnitude off, in a fixable way

15 matches is 15-22 hours of video. **5 human hours cannot label that from scratch** —
scanning alone is ~1x realtime. 5 hours is a **correction** budget: review and fix an
automatic proposal. That is fine, but it must be specified that way, and the proposer
must exist first.

**The bigger point: point boundaries are LOGIC under this project's own architecture
rule, not perception.** A rule over ball-in-play state and bounces has no training set.
So labels are needed for **evaluation only** — which needs 3-5 matches (~500 points),
not 15. That collapses the line item.

## Compliant automated signals, ranked by evidence

- **Audio racquet/ball impacts — the strongest and cheapest.** Measured on-court:
  **95% in controlled ML testing, 85% for the whole system applied on court** (Sensors /
  PMC11843912, n=10, GoPro 11 built-in stereo mic, 5 m laterally, 1.10 m high, outdoor,
  ambient wind and adjacent-court noise). That setup is close to our target footage.
  This project already has an unwired `audio.py`. Audio is derived from the game, so it
  is rule-11 compliant. Caveat: it shells out to a bundled ffmpeg today and has no iOS
  path; `AVAssetReader` replaces it.
- **Ball-in-play / bounce sequences** — compliant by construction. Blocked by the
  project's own open defects (24-27% far-court detector dropout, 9 solid ghost balls).
- **Broadcast rally detection: DO NOT IMPORT.** The published 81% average
  (91% hard / 82% grass / 71% clay, Sports Technology 2013) works by classifying the
  **camera shot** — overhead court view = rally. A fixed phone on a fence never cuts, so
  the entire signal is absent. TennisExpert (2026) segments 202 broadcast matches by
  audio impacts but publishes **no segmentation accuracy at all** and filters to clips
  with a visible scoreboard.
- **No published inter-annotator agreement for tennis point boundaries exists.** TenniSet
  (DICTA 2017, 5 broadcast matches) publishes dense event annotations and a tool, but no
  agreement study and no annotation-hour figures.
