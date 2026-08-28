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

**BallNet v21 vs TrackNet, scored at the CHAIN (not the detector).** RESUMED 2026-08-28
after a usage-limit kill. Predecessor left uncommitted:
`tools/eval_detector_chain_ab.py`, `tools/build_detector_ab_caches.py`,
`tools/compare_match_products.py`, `data/output/detector_ab/`.
Predecessor wrote NOTHING to this journal — resuming from artifacts only.

Product metrics to report: solid ghost balls, `event_audit`, speed coverage. NOT hit@10 /
F1@4 (secondary at most). Must state which metrics route through the homography
(`yt_match40` calibration confirmed WRONG, trap T23; `am_hard_utr` visibly skewed right).
Do not change shipped defaults. Update docs/STATE.md in the same commit.

Consequence to record: if BallNet v21 wins it has NO Core ML export path today.

## STATE — where I got to

**MEASUREMENT IS ESSENTIALLY DONE. Remaining: am_hard_utr product pair, STATE row, commit.**

### Chain half — FULL POWER, 10 clips, 1658 clicks, 272 no-ball frames. H-FREE.
`data/output/detector_ab_chain.json` + `..._nogate.json`, payloads byte-identical except
the flag. `gate_ball_to_court` removes 0 locks on 7 calibrated clips x 2 arms = **14/14**.
So T23's broken yt_match40 calibration cannot have touched this verdict.
  solid ghosts **88 -> 62 (-26, -29.5%)**, all ghosts 125 -> 83, hits 869 -> 861 (-8),
  recall 52.4 -> 51.9. Cost **0.31 hits per solid ghost removed**.
  18% frame overlap between arms' solid ghosts => different failure modes, not a
  threshold shift. Per-clip SPLIT: T wins 6/10 at 7:1, 5/10 at 1:1 (pooled utility +18).
  Secondary: far_px (H-free) 53.3 -> 53.8; far_geo (H-DEP) 50.5 -> 48.9.

### Product half — 2 of 3 pairs done (BallNet ahead or level on BOTH)
  yt_rally2:        shots 12->10, speed_confident **7->5**, calls 3->2, track 252->231
  gold_UHf0LeMU2pg: shots 43->39, speed_confident **22->22**, calls 16->14, track 932->879
  Use ABSOLUTE speed_confident, never the pct (pct rewards emitting fewer shots).
  H-DEPENDENT: everything except shots/rallies.
  event_audit (yt_rally2 only): phantom hits 1/8 -> 0/6, landings 1/4 -> 1/5. Moves by 1
  vs the tool's own >=3 bar => **INDETERMINATE**.

RUNNING: background **bajq91mja**, am_hard_utr both arms (~45 min/arm). The first analyze
driver (bdzto98i9) was KILLED at run 5/6 — 4 of 6 match.json survived, relaunched only the
missing clip. If it dies again: report on 2 pairs and say the third was cut.

### THE VERDICT (write it this way)
**SPLIT, and it does not favour a switch.** TrackNet wins the ghost half decisively;
BallNet wins or ties the product half (speed coverage, trail length) on both measured
clips. No gate was pre-registered — this is a measurement, not a pass/fail.
=> **Do not switch the desktop default.** For the FIRST Mac session the honest read is
that TrackNet's Core ML path already exists (mobile/models/*.onnx) and BallNet's does
NOT, and the chain evidence does not establish BallNet as better at the product.
Recommend: export TrackNet FIRST, keep BallNet's export as a follow-up, and resolve the
divergence by MEASUREMENT on device rather than by assuming the desktop default.

## LOG — newest first

- 2026-08-28 **gold_UHf0LeMU2pg product pair done — and it exposes a metric trap.**
  shots 43 -> 39, speed_confident **22 -> 22 (IDENTICAL)**, but speed_confident_**pct**
  51.2 -> 56.4 (+5.2). The percentage moves ONLY because the denominator shrank.
  **Report the ABSOLUTE speed-confident count, not the pct** — the pct rewards a detector
  for emitting fewer shots. Same trap on yt_rally2 (7 -> 5 absolute, 58.3 -> 50.0 pct;
  there they agree, but only by luck).
  Also: call_confident 16 -> 14, ball_track_points 932 -> 879 (BallNet draws a longer trail
  on both clips). **There is NO shot-count ground truth**, so 43 -> 39 cannot be scored as
  better or worse — only event_audit can adjudicate and it is underpowered. Say that.

- 2026-08-28 **yt_rally2 analyze pair done. BallNet wins the PRODUCT half on this clip.**
  compare_match_products: shots 12 -> 10, speed_confident 7 (58.3%) -> 5 (50.0%),
  call_confident 3 -> 2, ball_track_points 252 -> 231. All H-DEPENDENT except shots/rallies.
  event_audit (yt_rally2 is the ONLY adjudicable clip): phantom hits **1/8 -> 0/6**,
  phantom landings 1/4 -> 1/5. The raw count moved by **1**, and the tool's own docstring
  says do not claim a change unless it moves by **>=3**. So event_audit is **INDETERMINATE
  — report it as such, do not spend it as a TrackNet win.**
  Consistent with the chain half: yt_rally2 is one of the 4 clips where BallNet wins.
- 2026-08-28 Court gate verified a **complete no-op: 0 locks removed, 7 calibrated clips x
  2 arms = 14/14**, hfov 20.7-93.7. Dead code at the chain. Own STATE line.

- 2026-08-28 **Operating-point confound is BOUNDED by existing evidence, not by a new run.**
  Caches store no per-detection score (keys: frame_step/src_fps/eff_fps/bgsub/ball_model/
  provenance/ball_px), so BallNet cannot be re-thresholded offline to match TrackNet's lock
  rate. But `docs/evidence/expecting-a-detector-gain-of-any-kind.md` records score_thresh as
  ONE OF FOUR detector changes that cut detector false fire substantially and delivered
  NOTHING at the chain. So a pure threshold move on BallNet is already measured not to buy
  -26 solid ghosts. State it that way; do not spend GPU re-deriving it.
- 2026-08-28 This A/B is the first chain-level answer to the OPEN STATE row *"whether a
  better detector can reach the ghost ball at all"*. Four PARAMETER-level detector gains
  reached nothing; a wholesale detector SWAP moves solid ghosts 77 -> 51. Worth its own
  STATE line.

- 2026-08-28 **THE VERDICT IS WEIGHT-DEPENDENT — do not report the pooled number alone.**
  Interim 8 clips: T removes 26 solid ghosts for 3 hits = **8.67:1**, above the project's
  ~7:1 structural exchange rate. BUT pooled recall being flat is CANCELLATION, not
  stability: gold_shell +20 hits, gold_clay +13, gold_am **-24**, gold_uR5q2cSM6AY **-25**.
  Weighting 1 ghost = 7 hits, T wins 6/8 clips. Weighting 1:1, it is 4-4.
  Also: T fires **13-21% FEWER raw locks** than B on 7 of 8 clips (T/B 0.79-1.00), so part
  of the ghost cut is a lower operating point, not better discrimination. Mitigating
  precedent to check, not assume: STATE says score_thresh was one of four detector gains
  that moved the detector and nothing downstream.
  => The TIEBREAKER must be the analyze half: `speed_confident` is set from
  real_fraction(hit,landing) >= 0.5, so recall losses hit the product directly through
  SPEED COVERAGE. Run run_detector_ab_analyze.py. Do not call this on ghosts alone.

- 2026-08-28 Wrote `backend/tests/test_detector_chain_ab_ladder.py` (7 tests, pass).
  Pins the A/B tool's ladder to `pipeline.analyze_video` by AST source comparison —
  order, tuning literals, res_scale, H-guard. VERIFIED IT CAN FAIL: dropping
  remove_outliers -> 2 fail; 35.0 -> 30.0 -> 1 fail. File restored, git diff clean.
- 2026-08-28 `event_audit.py` runs on **yt_rally2 ONLY** (label density; am_hard_utr is
  5.5% adjudicable and unmeasurable). Power ~12 hits: do NOT claim a phantom change
  unless the raw count moves by >=3. Its own docstring says so — quote that limit.
- 2026-08-28 `tools/run_detector_ab_analyze.py` ALREADY EXISTS (committed) — full
  pipeline, both arms, serial, --ball-model forced. Use it for the analyze half.
  Predecessor's tools were all committed by the lead; my tree is clean but for this file.

- 2026-08-28 Build relaunched, 2 caches missing, background b0hyw9ad6.
- 2026-08-28 RESUMED. Journal was empty; lead.md PARKED section is the only handoff.
  Predecessor left a finished 3-tool harness and 13 of 15 caches.
