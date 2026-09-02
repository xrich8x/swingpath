# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — what I was asked to do

Re-measure the per-stage **SPEED-COVERAGE** attribution (`seen_frac = real_fraction(hit,
landing)`, >=50% required for a trusted speed) under **TrackNet**, beside the existing
BallNet numbers in `data/output/post_bounce_chain.md` part 3.

BallNet table already on record (do not re-derive, but DO re-run as the A arm):
  stage                  am_hard_utr mean / shots>=50%   yt_match40 mean / shots>=50%
  raw                    75.5%  106/120                  79.3%  182/196
  +rectify_track         72.1%  101                      77.5%  174
  +suppress_false_locks  64.9%   90                      69.4%  150
  +gate_ball_to_court    64.9% (0) 90                    69.4% (0) 150
  +smooth_forecast       52.9% (-12.0) 69                59.7% (-9.7) 124

WHY: `docs/evidence/smooth-forecast-adds-ghosts.md` (2026-09-02) established that
smooth_forecast's PER-FRAME behaviour is a property of the DETECTOR PAIRING not the
stage (BallNet -1.0pt recall/+12 ghosts; TrackNet +3.9pt/+3 ghosts). v1 detector is a
founder decision for TrackNet, so the -12.0 coverage cost may be a BallNet artefact.

MUST: build a probe (none exists; real_fraction lives inside pipeline.py:1716).
Mirror the SHIPPED chain order exactly. Pre-register a numeric bar BEFORE running.
Report both arms side by side. Commit to master, DO NOT PUSH. STATE.md same commit.

## STATE — where I got to

### ### RESULT IS IN. GATE **B** PASSES: THE COST **SURVIVES**. IT IS THE STAGE. ###

All 8 runs done, artifacts in `data/output/speed_coverage/`. Remaining: inertness test
for `span_sink`, evidence file, STATE row, commit.

PRIMARY (each arm on its OWN shots — what the shipped product would report):
| clip | arm | raw | rect | suppr | gate | smooth | **D_smooth** | shots>=50% at smooth | n_shots |
|---|---|---|---|---|---|---|---|---|---|
| am_hard_utr | BallNet  | 77.7 | 74.0 | 66.3 | 66.3 | 56.2 | **-10.1** | 87->73 (-14) | 124 |
| am_hard_utr | TrackNet | 69.6 | 67.2 | 62.0 | 62.0 | 51.1 | **-11.0** | 65->50 (-15) | 90 |
| yt_match40  | BallNet  | 81.9 | 80.3 | 73.3 | 73.3 | 63.1 | **-10.2** | 155->138 (-17) | 187 |
| yt_match40  | TrackNet | 68.8 | 67.5 | 63.1 | 63.0 | 55.0 | **-8.1**  | 131->103 (-28) | 186 |

CROSS-CHECK, identical shot populations (spans from BallNet for both arms):
  am_hard  BN -10.1 vs TN **-10.2** ; match40 BN -10.2 vs TN **-8.1**. Same answer.

GATE: A (pairing) needs |D_TN| <= 0.5|D_BN| on both -> 11.0 vs 5.1 and 8.1 vs 5.1 =>
**FAILS**. B (stage) needs |D_TN| >= 0.75|D_BN| on both (7.6 / 7.7), >=5.0 pts absolute
on both, and smooth still the largest single-stage cost -> 11.0 and 8.1, both, and
-11.0 vs -5.2 / -8.1 vs -4.4 => **PASSES**. LIVE-TARGET FLOOR met (>=5 pts on both
clips, 15 and 28 shots pushed under the bar).

MECHANISM, and it is detector-INDEPENDENT: real detections deleted by the smoother's
innovation gate (seen at gate -> seen at smooth): am_hard BN 9757->8278 (-15.2%),
TN 8330->6910 (-17.0%); match40 BN 6918->5927 (-14.3%), TN 5965->5148 (-13.7%).
14-17% in EVERY arm.

RECONCILES with the ghost/recall finding rather than contradicting it: recall counts a
COASTED frame within 10 px as a hit, `seen_frac` does not. The smoother trades real
detections for coasted fills -> it can raise recall and lower coverage at the same time.

FOOTNOTE, do not lose: `gate_ball_to_court` is NOT exactly 0.0 on yt_match40/TrackNet
(-0.05 pts, 9 frames). 0.0 exactly on the other three arms.

Probe = `tools/eval_speed_coverage_chain.py` (new). Hook = `span_sink=None` kwarg added
to `pipeline._build_match_from_events` (observability only, provably inert). Design:
spans FIXED once from the FULL shipped chain; each stage scored by handing the shipped
function a different `ball_seen` mask. Pose/cam_motion/player tracks come from the
clip's standard cache (detector-INDEPENDENT) so the ball track is the only variable.

VALIDATION vs published part-3 (same input: main `*.perception.json`, BallNet):
  am_hard_utr  mine 75.5 / 72.0 / 64.9 / 64.9 / **53.1**  shots 106/101/90/90/**71**
               pub  75.5 / 72.1 / 64.9 / 64.9 / **52.9**  shots 106/101/90/90/**69**
  yt_match40   mine 79.3 / 77.5 / 69.3 / 69.3 / **59.6**  shots 182/174/150/150/124
               pub  79.3 / 77.5 / 69.4 / 69.4 / **59.7**  shots 182/174/150/150/124
  => within +/-0.2 pt everywhere and +/-2 shots on one row. PASSES gate V (the am_hard
  smooth row is AT the shot tolerance, not inside it — say so). Corroborated
  independently: the tool printed "speed not trusted for 64/120 shots" on the smooth
  row, the exact figure part 2 of the doc quotes.
  D_smooth(BallNet, main cache): am_hard **-11.8**, match40 **-9.7**.

CACHE FAMILIES DIFFER — this is why the A/B must re-run BOTH arms:
  main `*.perception.json`      : court_gate **true** at perception time
  `detector_ab/*.perception.json`: court_gate **false**, both detectors, same day,
  same score_thresh 0.5, same static_gate, same frame counts (14499 / 10268).
  Only the detector_ab pair is one-variable. The main-cache numbers above are for
  probe validation ONLY and are never an arm.

### PRE-REGISTERED BAR — written 2026-09-02 BEFORE any run. Rule 2: it does not move.

Quantity under test: `D_smooth` = (mean seen_frac at `+gate_ball_to_court`) minus
(mean seen_frac at `+smooth_forecast`), in percentage points, per clip. Published
BallNet values: am_hard_utr **-12.0**, yt_match40 **-9.7**.
Both arms are RE-MEASURED on the matched `detector_ab/` caches. The published numbers
are the target for probe validation only, never an arm of the A/B.

**V. PROBE VALIDATION (gate on the tool, run first).** Run the probe on the SAME input
the published table used (`data/output/{am_hard_utr,yt_match40}.perception.json`,
BallNet). It must reproduce every row to within **+/-1.0 pt** of mean seen_frac and
**+/-2 shots** on the >=50% count. If it does not, the probe is not validated and every
number below is reported as UNVALIDATED.

**A. PAIRING PROPERTY (the -12.0 cost does NOT survive under TrackNet):**
  |D_smooth(TrackNet)| <= 0.5 x |D_smooth(BallNet)| on **BOTH** clips,
  AND the shots-dropping-below-50%-at-the-smoother count is likewise <= half on both.
  (D_smooth(TrackNet) >= 0 on both clips is a decisive instance of this.)

**B. STAGE PROPERTY (the cost SURVIVES):**
  |D_smooth(TrackNet)| >= 0.75 x |D_smooth(BallNet)| on **BOTH** clips,
  AND >= 5.0 pts absolute on both, AND `smooth_forecast` is still the LARGEST
  single-stage coverage cost in the TrackNet ladder.

**C. INDETERMINATE:** anything else, including a split across the two clips. Reported
  as indeterminate, NOT rounded to whichever side is closer.

**LIVE-TARGET FLOOR (separate, decides the STATE row's wording):** for speed coverage
to stay a live product target under v1's detector, the smoother must cost, under
TrackNet, **>= 5.0 pts** of mean seen_frac on at least one clip **AND** push **>= 10**
shots below the 50% bar on at least one clip. Below that floor the row needs rewriting
regardless of which of A/B/C fires.

## LOG — newest first

- 2026-09-02 Previous task (far-player motion gate) is DONE + committed `7d002e0`. This
  is a NEW task, not a restart.
- CARRIED FORWARD from last run: `docs/STATE.md` is CRLF on disk / LF in HEAD -> normalise
  the whole file after editing. `data/output/*` is gitignored -> `git add -f`.
- CARRIED FORWARD: `python` is a broken Store shim. `backend/.venv/Scripts/python.exe`
  (CPU), `backend/.venv-train/Scripts/python.exe` (CUDA).
- TRAP given by lead: a `timeout` killing a slow clip with buffered stdout looks EXACTLY
  like silent failure -> PYTHONUNBUFFERED=1 + generous timeouts. `gold_sAjkpeRq4P4` is
  the slowest clip by far.
- NOTE: `grep -rn` across the repo root TIMES OUT (huge data dirs). Use the Grep tool.
