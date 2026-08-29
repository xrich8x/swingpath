# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/backend-dev/`, and
findings go in `docs/STATE.md` + `docs/evidence/`.

---

## TASK — what I was asked to do

**Execute the ALREADY-WRITTEN pre-registered gate** in
`docs/evidence/far-player-motion-contrast-hypothesis.md` §"Pre-registered gate, before
anything is built". Do not design it, do not improve it. Rule 2: bar does not move.

- Population: P0-3's `yt_match40` far-end contacts, restricted to the 15/25 where the
  POST-HOC `crop192@640_x` (yolo11x) arm found a far-sized non-near person. Zero new
  human labelling. Reference stays labelled POST-HOC in every number.
- Method: `eval/movers.py` **unmodified**, `foot_points`. Homography-free (T23).
- Metric: distance nearest returned foot point -> known far-player box centroid, in
  box-heights.
- BAR: median <=1.5 box-heights on >=10 of 15 frames, **AND the random-blob null
  control must FAIL the same bar.** If random passes too, the real arm proved nothing.
- Rider, STRICTLY DESCRIPTIVE, NO GATE: luminance/chroma contrast of far player vs
  surrounding court on the same 15 frames. Cannot pass or fail anything.
- PASS => mark PROVISIONAL, render 15 contact tiles (style of
  `tools/p0_3_context_sheet.py`, NO court lines), STOP. Do not propose a build.
- FAIL => final, no eye needed. Say so plainly.
- Either way: do NOT propose a fix/variant/v2. Write to docs/evidence/, hand STATE row text.

Record whatever the outcome: (1) `eval/movers.py` is in `eval/`, NOT the shipped package,
so the mobile-viability audit's "every cv2 symbol exists in mobile builds" does NOT cover
it — prerequisite line item, do not do it this run. (2) `clean_plate` needs a rolling
buffer of up to 31 frames: harmless offline, fatal for live.

## STATE — where I got to

Previous task (bounce_hypothesis v2) is DONE + COMMITTED `39dbc75`. This is a NEW task.

Now: population resolved, building the runner.

## LOG — newest first

- 2026-08-29 **DISCREPANCY IN THE GATE DOC'S POPULATION — record, do not silently pick.**
  The gate says "the **15** of 25 contacts ... within **1.5 box-heights** of the ball
  anchor". Those are two DIFFERENT sets in `p0_3_tolerance_sweep.json`
  (`yt_match40.mp4/arms/crop192@640_x`):
    `far_sized_candidate_found_anywhere_in_crop` = **15**  (i.e. any distance)
    `by_rel_box_h["1.5"]`                        = **14**
    `by_rel_box_h["2.0"]`                        = **15**
  So N=15 is the found-ANYWHERE set; <=1.5 box-heights is 14. The BAR is written
  ">=10 of 15", so the denominator 15 is load-bearing => use the found-anywhere set as
  primary, and report the 14-subset alongside so nothing hinges on my reading.
- 2026-08-29 Selection logic reproduced from `tools/p0_3_tolerance_sweep.py`: candidate =
  entry in `arms[key]["accepted"] + ["rejected"]` with `small_enough and
  not_the_near_player`; nearest by EDGE distance from box to `ball_px_at_contact`.
  Reference box for a contact = that nearest candidate's `box`; normaliser = its
  `box_h_px`.
- 2026-08-29 **T24 CHECKED, run history established from git+STATE not prose.**
  `eval/movers.py` docstring says "UNRUN" — STALE. `git log`: written in `424ecdc`
  ("The court diagnosis harness, and the twelve negatives it produced"). Imported by
  `eval/candidate_audit.py:222`. STATE.md:140-141 carries the results; TRAPS T24 is
  already written. Never trust the docstring.
- 2026-08-29 ENV: `python` is a broken Store shim. Use `backend/.venv/Scripts/python.exe`
  (numpy 2.5.0, cv2 4.13.0, torch cpu). This task needs NO GPU — no inference runs, it
  reads cached probe JSON + decodes video with cv2.
- 2026-08-29 CRLF trap (carried forward): `docs/STATE.md` is CRLF on disk / LF in HEAD.
  Normalise the WHOLE file after editing. `data/output/*` is gitignored -> `git add -f`.

- 2026-08-29 **### GATE RESULT — FAILS. FINAL. NUMBERS BELOW ARE THE ANSWER. ###**
  `eval/far_player_motion_gate.py --arm crop192@640_x --seed 0`, 15/25 contacts,
  31-frame windows, movers UNMODIFIED, no homography.
    NEAREST blob : median **5.751** box-heights, **7 of 15** within 1.5   BAR: <=1.5 and
                   >=10 of 15  -> **FAIL on both halves**
    RANDOM (null): median **9.265**, **2 of 15** within 1.5              -> **also FAILS**
                   1000-seed repeat: median-of-medians 9.265 (p5-p95 8.11-9.92),
                   mean 2.99 within, **0.0%** of draws pass the bar.
    subset (anchor <=1.5 box-h, n=14): median 6.396, 6 within.
  => The null control is CLEAN (random fails decisively), so this is a genuine failure,
  not the ambiguous "control passed too" outcome. Nearest IS better than random
  (5.75 vs 9.27) so there is SOME positional signal — but the bar is absolute and it
  misses by ~3.8x on the median. **Rule 2: failed gate stays failed. Do NOT propose a v2.**
  No eye needed per the stop condition: a nearest blob that is far away is far away.
  CONTRAST RIDER (DESCRIPTIVE, NO GATE, cannot pass/fail anything), n=15:
    |dL| median **5.96** (min 0.11, max 13.3); dChroma_ab median 11.71 (6.04-25.28);
    dE median 14.67; surround SD of L median **20.99**;
    **|dL| / surround_sd median 0.30** (0.01-0.59) — the player's luminance offset is
    consistently SMALLER than the court patch's own luminance spread.
  Artifacts: data/output/far_player_motion_gate.json
