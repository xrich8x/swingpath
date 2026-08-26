# Session log

> Moved out of CLAUDE.md on 2026-08-26, where it cost context on every turn of
> every session. **Cold storage.** One entry per session: the finding and its
> number. For the consolidated state of play read [STATE.md](STATE.md); for the
> evidence behind a row read its file in [evidence/](evidence/); for the
> pre-registered briefs read [archive/sessions/](archive/sessions/).

Text preserved verbatim from CLAUDE.md.

One entry per session: the finding and its number. **The detail lives elsewhere
on purpose** — [docs/STATE.md](STATE.md) holds the consolidated wins, the
dead-end table and the traps; `data/output/*.md` holds the evidence with its
denominators; [docs/archive/sessions/](archive/sessions/) holds the pre-registered briefs.
Read those before re-proposing anything here.

- **2026-07-05 setup.** Git initialised; perception caches carry a provenance stamp
  (models, weight hashes, device, hfov, gates, homography hash, commit) and warn on a
  mismatched load. The demo30 "968-lock archive" regression resolved: 183 of the 968
  were static junk (HUD, net posts). NEW static-lock gate — a lock moving <3 px/frame
  for 5 frames is a fixture. yt_rally2 686 locks with **zero** static junk. 57 tests.
- **Session 2 (2026-07-05).** THE GOLD BENCHMARK EXISTS — 300 hand-labelled yt_rally2
  frames (258 ball / 26 no-ball / 16 unsure), TEST-only, never trained on. First honest
  numbers vs human clicks: ballnet 65.9% / archive 65.5% / fusion 43.0% / tracknet 41.5%.
  Far court is the whole gap. HANDOFF §11.
- **Session 3 (2026-07-06).** 2nd gold clip yt_match40 (cold). HUMBLING: on unseen
  footage custom BallNet does NOT beat off-the-shelf TrackNet — all four cluster 61-65%,
  and v1's earlier lead was a data leak. HANDOFF §12.
- **E5+ (2026-07-25) false alarms.** Court+vertical gate is a DEAD END (real far balls
  span court-y −229..+1667 m). NEW `ball.suppress_false_locks`; live-ball filter RETIRED.
  Pooled no-ball false-fire **14% → 6.0%** at flat recall. `ballnet_v21` becomes default.
- **E5+ smoothing.** `ball.smooth_forecast` = constant-acceleration Kalman + RTS smoother
  in image pixels. Jerkiness **9.9 → 4.1 px/frame²** at −1.6 pt hit@10. CRITICAL: it emits
  only INTERPOLATION — extrapolation ran off-screen and painted a phantom ball through
  dead time. `overlay.draw_court` now clips at the horizon. 148 tests.
- **E6 (2026-07-28).** The ball stack becomes geometry-aware. `gate_ball_to_court`'s
  margins were frozen at 720p and kept only **15.4%** of far balls at 1080p; replaced by a
  projected 3D box → **100%** retention. `events.drop_events_without_ball` kills phantom
  bounces (yt_rally2 6 → 3). `avg 0.0 km/h` diagnosed as coverage, not a bug.
- **E6 part 2.** Every pixel threshold now scales by `frame_height/720` — an exact no-op at
  720p, pinned by tests AND a byte-identical match.json. The before/after pair first
  recorded here is **WITHDRAWN** (bad scorer, see part 3). One deliberate exception:
  `static_radius_px` does NOT scale — scaling halves false-fire but costs 4.3 pts far recall.
- **E6 part 3.** MEASUREMENT BUG fixed: the scorer compared gold frame `f` against index
  `f//step` without checking `f` was processed. yt_rally2 is 100% even so its numbers stand;
  am_hard_utr was understated. `avg 0.0` FIXED → **62.8 avg / 91.9 top km/h**. `scale_ok` is
  measured ANTI-correlated with speed accuracy and is off the speed test. 171 tests.
- **Session F (2026-08-01).** Per-frame false-fire is NOT the product. THE CONFUSERS MOVE:
  71 raw false locks classified (`data/output/false_fires.md`) — **59.2% travel with a
  person**, 38.0% static scenery. So
  motion attention is skipped on evidence. `score_thresh` swept for the first time: **0.5
  stays** (0.6/0.7 fail the recall gate). `max_gap_s` swept: **0.4 stays**, and solid ghost
  fires sit at **9 at every setting** — nothing downstream removes a solid ghost. 209 tests.
- **Session G (2026-08-02).** POSE PROXIMITY IS A MEASURED NEGATIVE: **11.4%** catch at the
  5% collateral ceiling against a 60% gate. Why: the racquet sits **2.12 body heights** from
  the nearest keypoint — a skeleton has no racquet.
- **G part 2 (2026-08-03).** Calibration stops failing SILENTLY — every committed file
  carries an `_audit` verdict and `calibrate_video` warns on DEGENERATE. demo30
  re-calibrated **564.6 px → 0.5 px** (camera 1.38 m). Honest limit: at 1.38 m it measures
  only 5.2 m of 23.77 — **do not cite demo30 speeds**. 213 tests.
- **G part 3.** FAR COURT IS NOT GATE-SHAPED. The court gate costs **exactly zero**
  far-court recall on all three calibrated clips; the gap is DETECTOR-shaped.
  `suppress_false_locks`' shipped parameters already dominate all nine sweep alternatives.
- **G part 4.** Racquet-box negation (COCO class 38) FAILS at **54.5%** catch / 4.5%
  collateral against a 60% gate — but 4.8× better than pose proximity. Free external
  baseline: COCO "sports ball" scored **32.1%** recall on the six-clip gold set then;
  re-measured on the current ten-clip set it's **35.4%** (656/1851) vs BallNet v21's
  69.4% — data/output/racquet_negation_k.md.
- **Session H (2026-08-06).** THE COURT TEST SET WAS THE TRAINING SET — **17 of 20** gold
  clips were in `data/court_dataset/` and the court trainer had NO guard. Fixed with
  `court_split.json` + `assert_no_court_gold_leak`. Honest baseline on the clean split:
  **20.2%** held-out detect. The bottleneck is REFUSAL, not accuracy. 228 tests.
- **H part 2.** COURT AUTO-DETECTION CLOSED AS A MODEL PROBLEM. `courtfit` consensus is
  Tier 1 and beats CourtNet; the 6/8 bar is empirically correct (the one 5-vote clip is
  wrong by **68.7 px**, every ≥6-vote clip lands 3.4-13.9 px; evidence
  `data/output/court_consensus_bar.md`). 11 of 20 clips auto-calibrate with a perfect
  precision record. Also: 8 `am_indoor_hard1` gold frames are MISLABELLED — deliberately
  not "fixed", because human ground truth is never quietly edited. The valid court score
  table is `data/gold/court_scores_split.md`; `court_scores.md` is the pre-split leaked one.
- **H part 3.** SYNTHETIC GROUND TRUTH — the first ABSOLUTE accuracy here. Line calls
  **95.9%** correct, bounce **0.75 m** median. The −15..−20% speed rule CONFIRMED as physics
  (drag −21.7%; losing the vertical only −0.9%). New limit: flat z=0 back-projection is
  unusable for an airborne ball (**+72%** median).
- **H part 4.** WHAT CAMERA HEIGHT COSTS, in errors not bounds. Close-call accuracy
  **54.0% at 1.0 m → 69% at 3 m → 81% at 8 m**, against a **56.2%** majority-class floor —
  so a 1 m mount is worse than a constant answer. Pooled agreement is the WRONG metric
  (87-99% at every height). Real calibrations track the curve within ~3 pts. 243 tests.
- **H part 5.** FRAME RATE IS A REAL LEVER: 30 → 60 fps is worth **+5.8 pts** of close-call
  accuracy at 1.5 m — about as much as a *perfect* detector — and cuts bounce error 24-35%.
  Arc reproj **148 → 91 px**, HUD speed MAE **38.9 → 33.1%**. The cost is entirely the smoother.
- **H part 6.** `max_gap_s` at 60 fps is a MEASURED NEGATIVE: 0.60 passes cleanly on
  yt_rally2 and COLLAPSES on am_hard_utr. **The optimal gap policy scales with detection
  density — never tune it on one clip.**
- **Session I (2026-08-09).** Localised confuser weighting: PRODUCT GATE FAILS (solid ghosts
  14 → 15) while the DETECTOR improved on **6 of 6** clips (false fire 53.9 → 42.2%). NOT
  ATTRIBUTABLE — the trainer had **no seed**; `--seed` and `recipe_stamp` added. The ghost
  floor is **five universal frames**, not nine, and **all 19 chain false locks have
  `run_len = 1`** — every survivor carries the kinematic signature of a real ball.
- **Session J (2026-08-10).** The far-court queue's blocker was NOT the HUD — **RETRACTED**,
  only 5 of 36 clicks were inside a graphic. The real blocker: the ANCHORS bracketing the
  gaps were themselves false locks (≥1 anchor confirmed → 5 of 5 midpoints on a real ball;
  neither → 0 of 7). Then the sharper finding: **the anchor control measures agreement with
  the tracker, not correctness.** 326 tests.
- **Session K (2026-08-13).** MORE DATA IS A LEVER: +57% frames buys **+5.6 pts** pooled
  detector recall (74.8 → 80.4%, 4.1σ), up on 9 of 10 clips, and it GENERALISES (legacy six
  77.0 → 82.2%). **False fire did not move.** Not shipped — the chain test later failed
  (solid ghosts 9 → 13).
- **Session L (2026-08-13).** Far-court labels, under a pre-registered STOPPING RULE.
  Nothing predicts a findable gap: the best single feature keeps 73.0% / drops **50.0%**
  against a 70/60 bar, and 569 passing feature pairs cross-validate to **0-3%**. The null
  control (shuffled labels → **0** passing pairs) proves the signal is real and far too weak
  to screen on. Fourth failure on that lever. **The stopping rule fired: ball-detector work
  is closed.**
- **Session M (2026-08-15).** DELIVERY, not accuracy — no model touched, no gold number
  moved. The height guidance finally reaches users (`run.py check` + the Court Setup tab);
  `check` now invokes `pipeline.calibrate_video` so it can no longer disagree with `analyze`
  (**trap T15 recurrence** — the audit tool got the same fix a session earlier and nobody
  grepped the other callers); both JS mirrors are enforced by tests proved to fail; 60 fps
  shipped opt-in as `--full-rate`. **Scoreboard-derived score truth was BUILT THEN REJECTED
  ON ITS PREMISE — do not rebuild it** (a burned-in scoreboard is manual data entry;
  independence is not truth). 387 tests.
- **Session M part 2 (2026-08-15).** CHAIN ATTRIBUTION. In-rally coverage is the binding
  constraint on the target footage: the raw detector clears the ≥50% seen-fraction bar on
  **106 of 120** shots on am_hard_utr and only **69** survive the chain. Per stage,
  identical order on both clips: **`smooth_forecast` largest (−12.0 pts), `suppress_false_locks`
  second (−7.2), `gate_ball_to_court` exactly zero.** Two smoother fixes (`reset_after`,
  `bounce_reset`) both FAIL their pre-registered gate — loosening the outlier gate buys
  coverage and pays in ghosts. `am_hard_utr` finally has a perception cache. 391 tests.
- **Session N (2026-08-17).** RESPONSE TO THE 2026-08-16 REVIEW. Carved out a permanent
  blind holdout (2 of 10 gold clips) that `tune_smoother.py`/`tune_suppress.py` can no
  longer select (P0-1) — pre-registering each sweep's gate never stopped the cumulative
  drift of a dozen sweeps against one fixed set. Seeded CourtNet training to match
  BallNet's discipline (P2-1). Fixed a COCO baseline number that had gone stale (32.1%
  from the six-clip set, quoted with no qualifier; current is 35.4% on ten clips).
  Re-ran BallNet v21 vs TrackNet vs WASB (P1-1) on the current 10-clip gold set: BallNet
  still wins pooled hit@10 but by **+2.9 pts, not the +10.5 an undated `pipeline.py`
  comment claimed** — corrected in place, and not a clean win (TrackNet beats it
  outright on 2 of 10 clips). 391 tests.
- **Session N part 2 (2026-08-17).** THE DASHBOARD WAS INVENTING A STAT. `distance_run_m`
  is a path integral and was reported unconditionally, so **player B read a confident
  `0.0 m` on every real clip** — on yt_rally2 integrated over **0.0%** coverage (far
  player located on ZERO frames; 1.0% am_hard_utr, 9.6% demo30, 11.0% yt_match40).
  Forward-filling makes a sparse track *flat*, so it fails small-and-precise rather than
  obviously broken. Gated on the project's existing **≥50% seen-fraction** bar: below it
  the value is **None (not measurable), never 0.0**, and `stats.player_track_coverage`
  ships the denominator. UI says "not tracked" with the percent. **The cause is NOT
  fixed** — the far player really is untracked, now a named Open row with two unmeasured
  levers (`--pose-quality accurate`, `--far-player-rescue`).
  **A SECOND gate covers the axis coverage cannot see:** player tracking is deliberately
  **two-slot** (one per court half), so in DOUBLES the slot swaps between partners while
  coverage stays HIGH — distance is now refused there too, with its own reason in
  `stats.distance_run_note`. Verified by forcing `--doubles`: player A at **90.8%**
  coverage would have reported a confident 61.4 m. This is review finding P2-5 in its
  real form — doubles, not the singles net-exchange the review described (feet cannot
  legally cross the net mid-point). Also corrected a **SCOREBOARD self-contradiction**:
  its Open row told the next session to build score truth from burned-in scoreboards
  while its own dead-end table recorded that as built-then-rejected-on-premise and
  reverted; the `~1.6x` over-split came from that same withdrawn source and is now
  WITHDRAWN too (trap T20 fired twice — the second time on its own correction).
  400 tests.
