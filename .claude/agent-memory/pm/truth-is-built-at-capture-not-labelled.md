---
name: truth-is-built-at-capture-not-labelled
description: The 10 cm truth set is made BALL-FIRST at a court visit (measure the print), never MARK-FIRST or from video; and the lever on visit cost is CAMERAS, not balls
metadata:
  type: project
---

# Truth at 10 cm is BUILT AT CAPTURE. The design that makes it affordable.

Settled 2026-09-15 while writing `docs/CAPTURE_PROTOCOL.md` (pm). P3
(`docs/evidence/capture-floor-census.md`) fired: no clip we own is >=60 fps AND >=1080p AND
fixed-mount AND high enough for 10 cm. So truth is not a labelling problem — it is a
capture problem.

**Why:** a human clicking a monocular low-mount video cannot resolve a landing to 10 cm
(this project's height curve puts bounce error at 3.81 m on a 1.0 m mount). Truth has to be
established by a physical measurement the video never touches.

**How to apply — the five design calls, each of which the team will get wrong by default:**

1. **BALL-FIRST, not MARK-FIRST.** Do NOT ask a ball to land on a pre-placed mark — that
   rejects ~90% of feeds. Let the ball land, let it leave a print (coloured chalk/talc on
   hard court, the natural ball mark on clay), then tape-measure the PRINT's offset from
   the line. Every fed ball yields a truth point. Marks become AIM POINTS and FIDUCIALS,
   not targets. A "missed" ball is not a miss — the natural scatter IS the margin ladder,
   and it must span the estimator's own p90 (0.611 m lateral), not ±20 cm.

2. **THE LEVER IS CAMERAS, NOT BALLS.** Measuring a print is the bottleneck (~30 s + walk).
   Every extra camera pointed at the same bounce is free, and makes every comparison a
   PAIRED test on identical bounces. Four cameras turn one ball session into four answers.
   This is the single highest-leverage logistics decision at any capture visit.
   See [[capture-framing-is-a-scope-lever]].

3. **PIN THE TRUTH DEFINITION OR THE BUDGET IS GONE.** First contact = the REAR
   (incoming-side) edge of the print, not its centre — a skid streak is 6-8 cm long, so
   centre-vs-contact ambiguity alone is 3-4 cm, the whole budget. And ITF measures a court
   to the OUTSIDE of the lines (centre service line to its CENTRE); paint is 5-10 cm wide,
   so measuring to the wrong edge is 1.7-3.3x the budget. `court.py` does not document this.

4. **ROW ORDER IS THE ATTRIBUTION KEY.** One paper row per BOUNCE, in time order, including
   voids and net-cords. Nothing else may bounce during a take. A skipped bounce shifts every
   later row and turns clean measurements into confident wrong labels.

5. **THE VISIT'S OWN GATE MATTERS MORE THAN THE DATA GATE**, and the truth-quality check
   (blind re-measure of 5 prints, must repeat within 2 cm) must run after the FIRST 10
   prints, not at the end. Every gate must be answerable with a phone and paper, and every
   failure mode must have a same-day remedy.

**Related:** [[project-owns-no-confirmed-metric-footage]], [[blind-axis-splits-the-accuracy-bar]].
