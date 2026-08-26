> **SUPERSEDED / READ WITH CARE** — stamped 2026-08-15.
> Its scoreboard-derived truth route was BUILT AND REJECTED ON ITS PREMISE (2026-08-15, reverted in afffb5a) - a burned-in scoreboard is manual data entry, so it is independent but not true. The ~1.6x over-split figure it reports rests on that route and is WITHDRAWN. The rally layer still has NO ground truth. See SCOREBOARD's dead-end table.

# Rally segmentation and scoring — what the code does, and what it can be scored against

**Date:** 2026-08-13 · **Evidence:** `data/output/rallycheck.json` (yt_match40, re-run from the
committed perception cache), `scoreboard_probe.png`, `score_panel_survey.png`,
`score_states_check.png`. No code changed.

## 1. What the code actually does

`events.segment_rallies` (events.py:447) splits on two rules:

- a **time gap** between consecutive hit times greater than `gap_s`
- `force_break_after` — hit indices after which the rally must end, fed from
  `pipeline.py:1718`'s **second-bounce** test (the tennis rule that a second bounce ends
  the point)

The default `gap_s` is 4.0, but **the pipeline overrides it to 2.0** (pipeline.py:1868).

`Rally.end_s` is `rshots[-1].bounce_t_s` — the last shot's **landing**, not its hit
(pipeline.py:1876).

## 2. Which rule is firing — measured on yt_match40, 196 shots / 63 rallies

| | |
|---|---|
| breaks from the **time rule** | **62 of 62** |
| breaks from the **second-bounce force rule** | **0 of 62** |

So the double-bounce path contributes nothing on this clip. Everything is `gap_s`.

**And `gap_s = 2.0` is cutting into the real distribution.** Within-rally hit-to-hit
intervals run median 0.97 s, p90 1.69 s, **max exactly 2.00 s** — a distribution truncated
precisely at the threshold is the signature of a threshold inside the data, not beside it.
Of the 62 breaks, **30 came from gaps of only 2–3 s**, which is ordinary rally play for a
deep or high defensive ball.

## 3. The layer has NO ground truth — and the footage already contains it

Ball detection has 1851 human clicks. Court has 20 hand-labelled clips. Speed has the HUD
and `synth_truth`. **Rallies and score have nothing.** Nobody has ever labelled a point
boundary, so "63 rallies is wrong" has been an assertion, not a measurement.

It does not have to stay that way. **Three of the ten gold clips carry a burned-in,
point-by-point score:**

| clip | panel |
|---|---|
| `am_hard_utr` | ANIRUDH (UTR 10) / JACK (UTR 11) — **games + points + server dot**, large clean font, fixed position |
| `yt_match40` | D. Tan / Opponent — games + points + server dot |
| `gold_sAjkpeRq4P4` | FRANK — sets/games/points |

This is exact ground truth for four things the project currently guesses at: **point
boundaries, per-point winner, the score state machine, and who is serving.** It costs no
annotation — and `hud_ocr.py` already implements the right technique for it (connected-
component glyph matching against templates bootstrapped from the clip, no OCR dependency),
because the font is fixed and the panel is static.

## 4. How badly is it actually over-splitting? Counted without OCR

The panel is static except when the score changes, so distinct stable pixel-states of the
panel box are scoring events. On yt_match40, sampling every 0.5 s:

**40 distinct panel states over 354 s.**

Some of those are the server dot moving at a game change rather than a point, so the true
point count is **≈35–40**. Against that, the pipeline emits **63 rallies**.

**Over-split ≈ 1.6×.** Real, worth fixing, and consistent with `gap_s = 2.0` splitting deep
rally balls — but *not* the 4–8× failure this was first written up as.

## 5. Three claims from earlier today, corrected

1. **"Median inter-rally gap 0.00 s"** — measured `next.start_s − prev.end_s`, but `end_s`
   is the last shot's *bounce*, which lands 1–2 s after its hit. On the criterion the code
   actually uses (hit-to-hit) the boundary gaps are median **3.10 s, min 2.03 s** — every
   one above the threshold, exactly as designed. The 0.00 s figure was bookkeeping.
2. **"0 of 62 gaps ≥10 s, so it never found a real between-point break"** — yt_match40 is
   **edited**: only 12% of its human-labelled frames are no-ball, where an unedited match
   is mostly dead time. There are no 20–25 s breaks in this clip to find.
3. **"The dashboard reports ~63 points where reality is 8–15"** — that estimate assumed
   unedited footage. The burned-in score says ≈35–40. The defect is ~1.6×, not ~5×.

## 6. Also sized from the same run

Speed is not trusted for **95 of 196 shots (48%)** on yt_match40. The largest single named
cause is **"landing not tracked past bounce" (22×)** — losing the ball *after* it lands,
which is what closes the hit→landing span a path integral needs. That is a narrower target
than "far-court recall".

## 7. What this implies for order of work

Building the score reference comes **before** touching `gap_s`. Tuning a threshold against
no reference is the failure this project has already recorded twice (Session J trap T12,
and the standing rule that a model must never grade its own homework). The reference is
cheap, the technique already exists in the repo, and it converts rally segmentation,
scoring, serve detection and point-winner attribution from unmeasured to measured in one
step.
