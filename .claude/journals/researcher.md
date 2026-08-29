# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/researcher/`, and
findings go in `docs/STATE.md` + `docs/evidence/`. Do not duplicate those here.

---

## TASK — what I was asked to do

Founder question: is the FAR player better found by MOTION+CONTRAST vs court than by
person-detection? Read eval/movers.py (written 2026-08-24, UNRUN, no number from it
anywhere). Deliver: pre-registered gate, verdict, cheapest falsifying experiment.
Write docs/evidence/*.md + ONE STATE row. No code writes.

## STATE — DONE 2026-08-29

Delivered. docs/evidence/far-player-motion-contrast-hypothesis.md written.
.claude/agent-memory/researcher/player-detection-negatives.md created (new file, indexed
in MEMORY.md). open-questions.md updated. Final answer (verdict + STATE row text) given
to the lead in my closing report — I did not and cannot touch docs/STATE.md.

## LOG — newest first

- KEY CORRECTION TO BRIEF: eval/movers.py's docstring says "UNRUN" but that is STALE.
  Session O (2026-08-24) DID run its core primitive (foot_points/clean_plate) at scale via
  eval/candidate_audit.py --movers and eval/foot_gate_power.py, producing real numbers in
  data/output/court_scoring_diagnosis.md and two STATE rows: "horizon crop k=1.0 -> safe
  but inert" and the player-foot-gate rows. eval/candidate_audit.py's OWN docstring is also
  stale-UNRUN for the same reason (same-day run, header never updated).
- THE SINGLE MOST IMPORTANT NUMBER: movers.py's own comment (lines 56-62) — size/aspect
  filters alone let through a MEDIAN OF ~9 mover blobs PER FRAME (up to 18) on the 20 gold
  clips, before the MAX_PLAYERS=4 cap. Named confusers: crowd, scoreboard flicker, trees,
  high-contrast edges shivering under camera shake. This is a direct, footage-matched
  confuser census for "motion finds player-sized moving things" — and it does NOT cleanly
  find just the far player.
- The identical primitive (feet_in_court, aggregate) was tested as a court-hypothesis
  discriminator on 216 locks / 30 clips: DEAD, sign BACKWARDS (wrong courts contain feet
  BETTER than right ones, gap -0.033 to -0.071 at every margin). Closest existing test to
  the founder's question but NOT the same question (aggregate fraction, not per-frame
  single-blob identity/position).
- Horizon-crop (crop_row) use: safe but inert, crop proposed on only 1/20 clips. Confirms
  mechanism runs without catastrophic failure on 9 gold clips measured over 120 frames
  spanning WHOLE recordings (not just 8 frames) -- so camera is static enough for clean-
  plate to not blow up, at least on those 9. Not a full camera-motion-failure-rate number.
- ball.py:1641 `_bg_candidates` (ball background-sub) has an explicit bail-out: "if
  th.mean()/255 > max_fg_ratio: # camera moved / lighting jump; return []" -- camera motion
  breaking background-diff is a KNOWN risk in this codebase, not measured with a rate.
- P0-3 (already reviewed, evidence/p0-3-crop-around-contact.md): far player 25-35px tall,
  crop192@640 finds 2/25 strict / 15/25 post-hoc (label both), upscale factor is the
  variable, ball-centred crop holds far player at median 26.3px from crop edge -- the
  identified WEAK LINK a crop-centring signal could target.
- Racquet-box-negation: far player's racket found by COCO only at conf 0.12 (37x56px) --
  corroborates extreme small-object regime at the far end for ANY appearance detector.
- WebSearch: SAHI/tiling literature converges with P0-3's own crop+upscale finding
  (detector-based, not motion-based). No footage-matched (amateur phone, off-centre) motion
  benchmark found; broadcast-only numbers exist and are NOT to be quoted for our footage.
- VERDICT: worth a narrow, cheap, pre-registered falsification re-using P0-3's existing
  yt_match40 population (no new labeling) -- NOT worth building anything yet. Full writeup
  going to docs/evidence/far-player-motion-contrast-hypothesis.md now.
