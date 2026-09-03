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

## **Labelling protocol WRITTEN 2026-09-03** — `docs/evidence/point-boundary-label-protocol.md`.
Full spec: boundary definitions (start = first-serve contact, a fault does not start a
new point; end = the event that decides the point, 5-reason enum), REFUSAL for lets,
no-decision rallies, off-screen gaps, stoppages; minimum field set tagged by consumer
(scoring/clip-seg/dead-time); footage = the same 9 raw files (7 Hardcourt + 2 Clay, 0
Shell/Grass) priced below, stopping rule "3h soft / 4.5h hard" instead of a fixed clip
list; verification = single-labeller self-relabel of a FIXED 15-20 min segment (not a
random 10%) against a 1.0 s median-disagreement bar (Sigurdsson's own noise floor, not
tighter); leak guard `assert_no_point_boundary_gold_leak` proposed in `tools/_goldset.py`,
flags that 4 of the 9 raw files are ALREADY ball gold under the same basename
(`L73ep7JHiJ4`, `sAjkpeRq4P4`, `UHf0LeMU2pg`, `uR5q2cSM6AY`) — different task, same match,
named so nobody tunes a boundary heuristic against one and evaluates on the other's ball
numbers without noticing; file format `data/gold/<clip>.points.json`, deliberately NOT
`schema.py`'s `Rally` (computed-output shape, would risk gold being wired into the
product's own load path). Hours: 45 min scrub + <=4.5h labelling + ~20 min self-relabel
= ~5.6h worst case, inside the 3-6h budget only because the hard-stop was set below the
priced range's own top end. One DECISIONS_PENDING text handed to the lead, not written
directly (Shell/Grass footage gap — not currently blocking anything).

Priced 2026-08-28 (overnight R-task) — see `[[audio-hit-detection-mobile-port]]` for the audio-screen half

The evaluation-only set is now costed against actual repo contents, not just the
literature. **Only 9 files in the repo qualify as continuous, full-length source
video** (`data/incoming/Raw - Do Not Process/`, 7 Hardcourt + 2 Clay + 0 Shell +
0 Grass) — everything else is either already trimmed to a single point
(`split_by_serve.py` output, which bakes in its own boundary guess and so cannot
serve as an independent label) or a court-calibration frame set. **Shell and Grass
have zero eligible full-match footage today** — this is a scoping gap, not a
labelling-hours problem, and it needs new recordings before either surface can get
a point-boundary number.

Priced (title-based length estimate, unmeasured — flag before use): **4–5 Hardcourt
+ Clay matches, ~3–6 human hours total** (labelling at the brief's own 30–45 min /
30 min-video rate, plus a ~5 min/clip prerequisite scrub to rule out pre-edited/
jump-cut YouTube uploads, which would silently destroy dead-time-trim ground truth
even though they'd still support a point count). Same order of magnitude as the
approved far-court queue (4,087 frames / 4–5 h). Full pricing table:
`docs/evidence/audio-impact-screen-blocked-by-tooling-plus-gt-cost.md`.
