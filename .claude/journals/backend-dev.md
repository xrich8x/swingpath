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

**DONE AND COMMITTED as `7d002e0`. Nothing outstanding.**

VERDICT: **the motion gate FAILS.** Nearest blob median **5.751** box-heights, **7 of
15** within 1.5, against a bar of <=1.5 on >=10 of 15 — fails both halves. Random null
control also fails (9.265, 2/15, 0.0% of 1,000 draws), so the negative is CLEAN. Failure
is BIMODAL (nothing between 0.62 and 5.75). No tiles rendered — those were pre-committed
to the PASS branch only. No fix/variant/v2 proposed. Contrast rider shipped as
DESCRIPTIVE with no gate. STATE: negative filed in "What has not worked"; the Open
pre-registration row retired and replaced by an ungated contrast-characterisation row.
479 tests pass (11 new). Memory updated (new file
`null-controls-and-pre-registered-populations.md` + 2 bullets on traps).

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

- 2026-08-29 **### MECHANISM FOUND — IT IS A MISSING PROVENANCE KEY, NOT A GATE PROPERTY. ###**
  `ball.play_volume_polygon` has TWO RUNGS (backend/swingvision/ball.py:501):
    Rung A (`if hfov_deg:`) -> `calibration.project_court_3d` extruded 6 m play
      volume, convex hull of 8 projected corners. WIDE, self-scaling.
    Rung B (fallback)       -> ground trapezoid + fixed 220 px top / 120 px side band
      (resolution-scaled). MUCH TIGHTER. Gate docstring: Rung B kept only **15.4%**
      of far-court gold balls on am_hard_utr vs Rung A's 100%.
  Which rung runs is decided by whether `hfov_deg` is truthy. And the harnesses
  source it DIFFERENTLY:
    `tools/eval_detector_chain_ab.py:hfov_for()` **FITS** it (courtfit.cam_fit_quad,
       fallback 70.0) -> ALWAYS truthy -> **Rung A** -> removes 0. 
    `tools/eval_chain_gate.py:105` + `tools/chain_cache.py` read
       `provenance.camera_hfov_deg` from the CACHE -> **the gold caches do not have
       that key** -> hfov=None -> **Rung B** -> the -674.
  VERIFIED by direct inspection of provenance keys:
    gold_sAjkpeRq4P4 / gold_uR5q2cSM6AY / gold_L73ep7JHiJ4 / gold_UHf0LeMU2pg
      (both plain and detector_ab/*.tracknet): hfov = **None**,
      keys = [court_gate, date, device, score_thresh, static_gate, tool, video,
      weight_files]  (old build_gold_caches.py schema)
    am_hard_utr: hfov = **86.31**, full modern provenance schema.
  => the two "cache families" are really TWO PROVENANCE SCHEMAS.
- 2026-08-29 **SHIPPED PATH TAKES RUNG A.** `pipeline.analyze_video` passes
  `camera_hfov_deg`, set at pipeline.py:1244-1260 by lens lock -> focal self-cal ->
  **hard default 70.0**. It is never None. So the shipped product resembles the
  DETECTOR A/B ARMS, and the -674 is a harness artefact. STILL TO PROVE: per-clip
  Rung A vs Rung B removal counts, and the ghost/real split of the rejects vs gold
  clicks. Do not publish the conclusion before that is measured.

- 2026-08-29 **### T23 VERDICT: `data/sAjkpeRq4P4_pts.json` IS MISCALIBRATED. SETTLED BY EYE. ###**
  Rendered frame 0 at 1920x1080 with the clicks AND the full projected court model
  (scratchpad saj_courtmodel.png / saj_farband.png).
    far_bl (760,417) and far_br (1151,409) sit **ON THE NET BAND**, not the far
      baseline. Proof, three independent: (a) net POSTS visible at x~460 and x~1470,
      both clicks well INSIDE them; (b) the white band SAGS in the middle
      (y 407 at the posts, ~425 mid) - a straight far baseline projects to a
      STRAIGHT image line, a sagging net does not; (c) dark net MESH texture and the
      white CENTRE STRAP hang below the band.
    near_bl (148,819) sits **on the AmateurTennis.tv watermark banner**, off court
      entirely. near_br (1830,822) sits on **bare clay ~85 px above** the real
      sideline x baseline corner (~1810,907).
    ALL FOUR CLICKS ARE OFF ANY COURT LINE. Stamped PASS at 2.8 px. Second instance
    of T23 after yt_match40.
  CONSEQUENCE: H maps 23.77 m onto ~half the court, so the model's own net line
  lands mid near-service-box and camera_height 3.33 m is inflated. RULE 9: the pts
  file is human ground truth - NOT EDITED, recorded only.
  => Every sAjkpeRq4P4 number in this run is **CONTINGENT** and must be reported
  separately. It is now contingent for a KNOWN reason, not an unverified one.
