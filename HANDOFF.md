# HANDOFF — SwingVision-clone: state, evidence, and claims audit

Written 2026-07-05 for a fresh Claude session. Purpose: everything done, with
evidence levels, so the next session can find real fixes and catch any
hallucinated/overclaimed results. **Trust the artifacts, not the narrative.**

> **⚠️ HISTORICAL — this is a point-in-time evidence log from 2026-07-05, kept
> for its evidence-tagged findings and `§` references (ML_PLAYBOOK.md and
> ML_PRACTICES.md cite them by number, so the sections are stable and must not be
> renumbered). It does NOT reflect current state.** Much has shipped since:
> line-fit court auto-calibration + physical shape lock + camera-change watchdog,
> clay-aware snap, lens/roll correction, serve analytics, and a big refactor. For
> where the project is *now*, read CLAUDE.md's Status section and the Results
> blocks in [docs/sessions/](docs/sessions/). This file is the paper trail, not the roadmap.

Evidence levels used below:
- **[MEASURED]** — command output produced in-session; log/artifact exists on disk
- **[VISUAL]** — a human-readable image artifact exists; interpretation is stated
- **[INFERRED]** — conclusion from indirect evidence; re-verify before building on it
- **[UNKNOWN]** — explicitly unresolved

## 0. Environment gotchas (verified this session)

- `python`/`python3` are broken Windows Store shims. Use `py` or the venv exes.
- `backend/.venv` = CPU runtime (pytest runs here). `backend/.venv-train` =
  CUDA (torch 2.11.0+cu128, RTX 5060 Ti 16GB; now also has torchvision
  0.26.0+cu128, ultralytics 8.4.87, scipy — installed this session).
- GPU perception works: `run.py analyze ... --device cuda` ≈ 0.11 s/frame at
  pose=accurate [MEASURED].
- OpenCV in .venv-train returns HoughLinesP rows as (N,4) not (N,1,4); both
  call sites normalized with `.reshape(-1, 4)` (calibration.py
  `_hough_segments`, `_refine_keypoint`) [MEASURED — crashed, fixed, reran].
- 50/50 backend tests pass (`backend/.venv/Scripts/python.exe -m pytest tests/`)
  [MEASURED, run repeatedly].

## 1. What the product is

Backend (`backend/swingvision/`) turns a tennis video into `match.json`
(shots, speeds, bounces, line calls, score); React frontend (`frontend/`)
renders it. Architecture contract (CLAUDE.md): perception = ML; geometry =
closed-form math; logic = deterministic rules. Never ML-ify geometry/logic.

## 2. Canonical current build (what the user sees)

- Dashboard video: `frontend/public/analyzed.mp4`; data:
  `frontend/src/data/analyzed_match.json`; 30s cut: `demo_30s.mp4` (repo root).
- All three re-synced from `data/output/demo30.{annotated.mp4,json}` after the
  restore described in §6. Current match output [MEASURED]:
  5 shots / 4 rallies; serve B 166.8 km/h IN; backhand A 30.4 IN;
  forehand A ~33.8 OUT?; slice-forehand A ~44.1 IN; forehand A 22.5 IN?;
  ball 968/1108 frames; movement A=97.9m, B=0.
- **The ball track in this build is the ARCHIVED perception cache**
  (`data/output/demo30.perception.json`, backup at
  `demo30.perception.OLD.json`). It is NOT reproducible by current code — see
  §6, the most important open problem.

## 3. This session's code changes (all in git-less working tree — no VCS!)

Backend:
- `events.py`: `segment_rallies(force_break_after=...)` (double-bounce ends
  rally); overhead test now requires wrist-above-head AND ball-above-shoulders;
  new `contact_side()`, `infer_handedness()` (majority contact side, ≥6 shots,
  ≥60% majority, default "right"), `classify_spin()` (wrist vertical travel
  through contact ±3 frames, ±0.35 torso threshold → topspin/slice/flat/"").
- `pipeline.py`: two-phase shot building in `_build_match_from_events`
  (gather → infer handedness → classify); MIN_SPEED_KMH=5 ghost filter;
  per-shot `ends_point` (2nd bounce ≥0.25s and ≥0.3m after landing) feeds
  force_break; physics topspin_rpm overrides spin_style when |rpm|>300;
  focal self-calibration wired into `analyze_video` (camera_hfov_deg=None →
  auto); court-gate height threshold 4.0→3.0 m; `--ball-model all` (3-way
  fusion); `--device` exposed on analyze.
- `calibration.py`: `focal_from_homography()` (IAC self-calibration; two
  linear constraints in 1/f²; sanity 25–110° hfov); HoughLinesP shape fixes.
- `ball.py`: all 3 detectors expose `last_sub` (best sub-threshold response);
  BallTracker `rescue: bool = False` opt-in sub-threshold rescue (velocity +
  court + player-box gated, bg-run budgeted). **Default OFF** — see §6.
- `schema.py`: `Shot.spin_style: str = ""` (additive).
- `annotate.py`: top-left shot-chart HUD (mini court, landing dots colored by
  hitter, latest-shot readout incl. spin style); filename moved top-right;
  labels include spin style.
- `run.py`: `--camera-hfov` default None (auto), `--ball-model all`, `--device`.
- Tests: `test_events.py` rewritten (overhead both-conditions, high-camera
  regression case, handedness, force-break, spin); `test_calibration.py` +2
  focal recovery tests (synthetic pinhole cams, f recovered within 2%
  [MEASURED]); `test_ball.py` +2 rescue tests (opt-in).

Frontend:
- `App.jsx`: video cache-buster now from HEAD Last-Modified+Content-Length.
- `format.js`: `fmtStroke()` (spin style + type); `Court.jsx` tooltip uses it
  ("Slice Forehand · ~44 km/h · IN" verified in DOM [MEASURED]).

## 4. Training runs (logs in scratchpad tasks dir; copy summaries below)

Data:
- 10 user-provided YouTube clips downloaded to `data/train_clips/<id>.mp4`
  (ids: RZ_wyJ9rI3Q TilAFMPc0yg tC0z7FYvMks VZWi6Vf-sX0 ewqSn18xdsY
  8-BkpjFFIhQ rz4T0-VALNw WjHZrIYteDA nQan0M5JDM8 6jp23ghDY9Q) [MEASURED].
- GPU pseudo-labeler (scratchpad `label_train_clips.py`): TrackNet+WASB fusion
  tracker, no bg-sub, 3×1200-frame windows/clip → `data/ball_dataset/yt_*`;
  23,558 labels total [MEASURED]. Base rebuild added yt_rally2:
  broadcast 107 + amateur 275 + indoor_elev 968 = 1,350 [MEASURED].
- Court dataset rebuilt CLEAN from the user's yt_rally2 corners
  (`data/yt_rally2_pts.json`): 25 + 85 + 222 = 332 frames [MEASURED].

**BallNet v1** (`backend/weights/ballnet.pt`, train_ballnet.py --epochs 30
--batch 32, cuda): train 19,932 / val 4,976; best val median 1.0px,
**84.7% within-10px** [MEASURED].
⚠️ **CRITICAL HONESTY NOTE: this metric is agreement with PSEUDO-LABELS
(the fusion tracker's own locks) on held-out frames — NOT ground-truth
accuracy. No human-labeled ball benchmark exists yet.** Do not quote 84.7%
as "accuracy".

**CourtNet v3** (`backend/weights/courtnet_ft.pt`, train_courtnet.py
--epochs 30 --lr 1e-4): baseline 3.4% within-8px → best 19.9%, val median
12.2px [MEASURED]. Same honesty note: labels are homography-projected from 3
calibrated clips; val = temporal split of the SAME 3 angles.
Post-adoption checks [MEASURED]:
- Broadcast (`tennis_sample.mp4`) auto-calibration: source=learned,
  reproj 0.99px (previously 2.38px) — improved, no regression.
- yt_rally2 UNAIDED: source=learned 4.30px; corners vs the USER's own
  drag-truth: far 10px/5px, near 47px/41px (near corners are at/off frame
  edge). This is the strongest genuinely-verified win of the session.
- **Generalization to unseen angles: FAILS.** Survey of all 10 train clips at
  t=10s (`data/output/court_survey.jpg` [VISUAL]): 6 "learned FAILED" (several
  correctly — intro/title frames), 3 low-confidence fits of which ≥2 visually
  wrong, ~1 acceptable. CourtNet v3 only knows its 3 training angles.
- Classical fallback FALSE-FIT hazard: TilAFMPc0yg auto-classical reported
  4.48px reproj but the overlay is visually wrong
  (`data/output/showcase.overlay.png` [VISUAL]). Reprojection-vs-own-points
  is self-grading, not truth.
- Failed prior runs for context: court v0 (catastrophic forgetting,
  withdrawn as `courtnet_ft_v0_notready.pt`), v1 frozen-encoder (nothing
  saved), v2 on poisoned labels (222/332 labels came from a WRONG calibration
  — never beat baseline). Poison root cause: assistant had used the near
  SERVICE line as the BASELINE on yt_rally2; the USER's corner drag fixed it.

## 5. Ground truth discovered (unused so far — user has since said DON'T
build on SwingVision's labels; keep only as evaluation reference)

The yt_rally2 source video carries SwingVision's own burned-in per-shot HUD
(top-right). Frames extracted this session [VISUAL]
(`data/output/track_compare.jpg`, `chart_check_*.jpg`) show:
"Flat Serve 61 MPH", "Topspin Forehand 56", "Topspin Forehand 53",
"Topspin Backhand 49", "Flat Forehand 50".
- Our serve on the same clip: 166.8 km/h vs their 61 MPH (98 km/h)
  [INFERRED that they refer to the same serve — timing matches; verify].
  Root cause hypothesis: ball-in-flight projected onto the ground plane
  inflates distance (no height model). Fix direction: height-from-gravity
  parabola fitting (single camera + known g), NOT copying their numbers.
- Our spin labels (flat/slice) disagree with their "Topspin" on the
  overlapping shots [VISUAL, small sample n≈3] — the wrist heuristic is
  suspect at 30fps effective sampling.

## 6. THE UNRESOLVED REGRESSION (most important open problem)

The archived perception cache (`demo30.perception.json`, 968/1108 locks)
CANNOT be reproduced by current code. Fresh full re-perceptions of yt_rally2
this session [ALL MEASURED, cuda, pose=accurate]:
- fusion (tracknet+wasb): 865 locks
- tracknet only, rescue ON: 781 (model 497 + bg 284)
- tracknet only, rescue OFF: 781 (model 497 + bg 282)
- ours (ballnet): 990 locks but WRONG structure (see below)
- 3-way "all": 922

Facts: (a) rescue is NOT the cause (identical 781 with it off — the
assistant initially blamed rescue in-session; that explanation was WRONG and
is retracted); (b) model-lock count halved vs what the archive implies;
(c) visual diff `data/output/track_compare.jpg` [VISUAL]: where old/new
disagree, OLD is on the real ball; NEW781 sits on SwingVision's HUD logo
(t≈1.5s) and near a net post (t≈19.4s).
Unverified suspects [UNKNOWN — investigate in this order]:
1. The archive's provenance: WHICH model/device/gate built it? It predates
   this session; its build parameters are NOT recorded. It may have been
   built CPU-side and/or under different court-gate state (hfov 70 → cam
   height 4.4m) vs today (self-cal 93.5° → 3.3m). Cache keys do NOT include
   H/keypoints/device, so a cache can silently outlive the calibration it
   was built under.
2. CUDA-vs-CPU TrackNet numeric differences (argmax over 256-class map may
   flip near-threshold blobs). Cheap A/B: re-run tracknet-only on CPU,
   compare lock count.
3. median_background sampling differences between runs (bg bridge
   contributed 282-284 locks fresh; archive's bg share unknown).
4. Court-gate threshold change 4.0→3.0m (this session) alters gating vs
   whatever built the archive.
NOTE: 968 > 781 does NOT by itself mean 968 is more CORRECT — but the visual
diff at disagreement points favors the archive. A gold-label set (§8, fix
1.4) is the only way to settle it.

Also measured: BallNet standalone on yt_rally2 (990 locks) produces
misattributed shots (all "B", landings behind far baseline) [MEASURED].
Interpretation [INFERRED]: it locks the ADJACENT court's cleaner ball / HUD
graphics; pseudo-label training never contained "wrong-ball" negatives.
Supporting fact: lock y-median 230, p25 215 (top of frame) — but note the
ARCHIVE's y-median is also ~221, so y-distribution alone does not prove
this; the shot-structure difference is the evidence. Re-verify visually
before retraining.

## 7. Claims audit — where hallucination risk is highest

Things asserted in-session that the next session should NOT take at face
value:
1. "84.7% accuracy" — it is pseudo-label agreement (§4). No ground truth.
2. "Rescue caused the regression" — RETRACTED, measured false (§6).
3. "Court model found the user's court unaided" — TRUE and verified vs the
   user's corners (§4), but only for THIS angle; do not generalize.
4. "Ball coverage 87.4%" (and the archive itself) — denominator is tracker
   locks incl. bg-bridge; correctness at disagreement points checked only
   on ~6 frames visually.
5. Serve-speed comparison vs SwingVision (61 MPH) — single shot, HUD-frame
   pairing not rigorously aligned.
6. Spin/slice disagreement — n≈3 shots.
7. Speed numbers generally: average-flight-speed by design (reads under
   radar peak) AND inflated by ground-plane projection on serves — two
   overlapping effects; nobody has decomposed them quantitatively.
8. Anything sourced from pre-session summary/memory (compaction can drift):
   verify against code before building on it. Memory files:
   `C:\Users\richm\.claude\projects\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\memory\`.

## 8. Agreed roadmap (user-approved framing: self-reliant ML, no SwingVision
labels as training data) — HISTORICAL; the live plan is now [docs/sessions/](docs/sessions/)

R1 "Trust what you see": (1.1) solve §6 regression; (1.2) BallNet v2 with
hard negatives (adjacent-court balls, HUD logos); (1.4) gold-label tool
(~200 human-clicked frames — creates the first real benchmark); (2.1)
white-paint self-check gate before trusting any auto court fit.
R2 "Believe the numbers": (3.1) ball-height-from-gravity (parabola fit,
single camera + g) → fixes serve inflation from first principles; (1.3)
synthetic motion-blurred ball training data; (3.2) re-tune gates for
self-calibrated focal; (4.1) far-player recovery via enlarged far-half crop.
R3: serve analytics, heatmaps, auto-highlights, winners/errors, spin v2
(slow-mo + physics cross-check). R4: history DB, mobile shell.
User inputs needed: one clean 1080p+ elevated clip; ~30 min ball-clicking;
corner-drag per new angle; optional 240fps rally.

## 9. Artifact map

- Canonical: `data/output/demo30.{json,annotated.mp4,perception.json}`;
  backup `demo30.perception.OLD.json`; experiment caches
  `demo30.perception.NEW781.json`, `demo30b/c/d.*` (ours / ours+70° /
  all-fusion runs).
- Evidence images: `data/output/track_compare.jpg` (old-vs-new ball, 6
  frames), `court_survey.jpg` (learned court on 10 clips),
  `showcase.overlay.png` (classical false-fit), `chart_check_*.jpg` (HUD).
- Weights: `backend/weights/{ballnet.pt (v1), ballnet_v0.pt, courtnet_ft.pt
  (v3), courtnet_ft_v0_notready.pt, court_detector.pt (base), tracknet.pt,
  wasb_tennis_best.pth.tar}`.
- Datasets: `data/ball_dataset/*` (13 dirs), `data/court_dataset/*` (3 dirs).
- Training logs: scratchpad `tasks/` dir of session cf49ba9e… (may be
  cleaned by OS; key numbers are transcribed in §4 and in memory files).
- **No git repo — nothing is version-controlled. Strongly consider `git init`
  + first commit before further changes.** (Done 2026-07-05 — see §10.)

## 10. Session 2026-07-05 — §6 regression investigated: VERDICT

Session scope: git init (commits e223d40, 39782a3, 4f6464b + this doc commit),
provenance stamping for all new perception caches (§6 suspect 1's "cache keys
don't record H/device" is fixed for the future; tests 50 -> 54), then the §6
experiments in the prescribed order. Archived caches and canonical demo30
outputs untouched (enforced by git — they are committed and show no diff).

Experiments (yt_rally2.mp4 + user corner calibration, frame_step 2, pose
accurate, bgsub on — matching every demo30 cache; outputs demo30_exp_*):

| run                                   | total locks | static junk | ball-only |
|---------------------------------------|------------|-------------|-----------|
| ARCHIVE demo30.perception.json        | 968        | 183 (19%)   | 785       |
| fresh tracknet cuda (NEW781)          | 781        | 103 (13%)   | 678       |
| 3a tracknet cuda hfov=70 gate=4.0m    | 781        | 103         | 678       |
| 3a fusion   cuda hfov=70 gate=4.0m    | 862        | 115         | 747       |
| 3b tracknet CPU  hfov=70 gate=4.0m    | 781        | 103         | 678       |

("static junk" = locks that move <3 px/frame for >=5 consecutive frames —
a ball never does that; these sit on SwingVision's burned-in HUD labels,
its logo, and net posts. Filter is analysis-side only, not in the pipeline.)

MEASURED facts:
- 3a tracknet is bit-identical to NEW781 on all 1108 frames: forcing the old
  hfov (70 vs self-cal 93.5) and old gate threshold (4.0 vs 3.0 m) changes
  NOTHING. §6 suspects 1(partial: hfov/gate state) and 4 are ruled out.
- 3b CPU: 1098/1108 frames exactly identical to cuda, all 781 locks within
  2 px (one lock flipped model<->bg attribution). §6 suspect 2 ruled out.
- Rescue was already ruled out in-session last time (§6 fact a).
- The archive's extra 240 locks vs fresh: 99% in the far half (y median 200),
  in 48 sustained streaks (longest 24 processed frames ~0.8 s).
- The visual diff (data/output/regression_diff.jpg, 6 frames) shows fresh781
  stuck on the 61 MPH HUD box at t=1.2 s (archive plausibly on the ball) BUT
  ALSO the archive stuck on a 50 MPH HUD box at t~18.5-18.9 s. Neither track
  is pristine; §6's "where they disagree, OLD is on the real ball" was
  over-generous to the archive.

VERDICT [INFERRED from the above]: the archive was built by a pre-git version
of the code that no longer exists. No configuration of current code
(tracknet/fusion x cpu/cuda x old/new hfov+gate x rescue on/off) reproduces
it, and current code is bit-deterministic, so the difference is code, not
settings or hardware. That older code kept weak far-court detections that
current code rejects — real ball AND HUD junk alike (its junk rate is higher:
19% vs 13%). The headline regression was ~half illusory: 968 vs 781 is
785 vs 678 ball-only (gap 107), and current FUSION reaches 747 (gap 38).
The archive's recorded ball_model=tracknet was written by that unknown code
and cannot be verified [UNKNOWN]; fusion's ball-only count being far closer
to the archive's is weak evidence the archive build was fusion-like.

Still open (unchanged from §8 roadmap, now sharper):
- Gold-label set (fix 1.4) is the only way to decide whether the archive's
  107 extra ball-only locks are real ball or residual junk — i.e. whether
  ANYTHING was actually lost.
- A static-lock gate in the pipeline (this session's junk filter, ~20 lines)
  would remove 103-183 false locks from every run and should precede any
  BallNet v2 training on pseudo-labels (the junk is in the labels too).
  -> DONE later the same day (commit after this one): BallTracker
  static_step_px=3/static_min_run=5 gate + fixture blacklist. MEASURED on
  yt_rally2 cuda: tracknet 686 locks / 0 static junk / ball-only 678->686
  (real ball RECOVERED where the track had been HUD-glued); fusion 746 / 0
  junk (vs 747 ball-only ungated). Params recorded in cache provenance.
  Pseudo-label REGENERATION for BallNet v2 should rerun with this gate on.

## 11. Session 2 (2026-07-05 evening) — the FIRST human gold benchmark

Fix 1.4 is DONE. Tools (commit 733b374): `tools/select_gold_frames.py`
(stratified 250-frame selection: 50 each of serve / near / far / disagree /
noball buckets, manifest carries video sha1 + params),
`tools/gold_label_server.py` (blind browser labeler — no model output or
bucket names shown to the labeler; magnifier loupe; atomic per-click saves),
`tools/eval_gold.py` (hit@radius, miss vs wrong split, no-ball FP rate,
per-bucket breakdown). Eval self-check: archive scored against fake gold
derived from its own locks = 100% hit / 0% FP [MEASURED].

THE USER hand-labeled all 250 frames blind (~15 min), then a +50 no-ball
extension round (tools/extend_noball_frames.py: 25 FP-candidate frames where
archive/ballnet fire but the gated fresh tracks are silent + 25 near the
human's confirmed no-ball labels). Final: 300 labels = 258 ball + 26 no-ball
+ 16 unsure (excluded). Labels: `data/gold/yt_rally2.labels.json`.
**These labels are a TEST set — never train on them.**
Notable: even in the frames selected as likely-no-ball, the human found a
visible ball in 41/50 — this clip has almost no true dead time, and the
"eager" tracks were often RIGHT to fire where the gated ones were silent.

Results [MEASURED — first non-self-graded numbers in the project; 284
scored frames]. CAVEAT: buckets deliberately oversample hard/disagreement
frames (incl. frames chosen BECAUSE the fresh tracks were silent), so
overall percentages compare tracks; they are not clip-wide uniform rates:

| track | hit@10 | wrong>10 | miss | hit@5 | hit@25 | med.err | FP (no-ball) |
|---|---|---|---|---|---|---|---|
| archive968 | 65.5% | 19.8% | 14.7% | 56.2% | 71.3% | 2.8px | 61.5% |
| fusion746 | 43.0% | 23.3% | 33.7% | 30.2% | 48.1% | 6.1px | 26.9% |
| tracknet686 | 41.5% | 20.2% | 38.4% | 31.8% | 45.7% | 4.7px | 19.2% |
| ballnet990 | 65.9% | 19.0% | 15.1% | 51.2% | 69.8% | 3.8px | 65.4% |

| track (hit@10 per bucket) | serve | near | far | disagree | noball | noball-FP |
|---|---|---|---|---|---|---|
| archive968 | 75.0% | 91.5% | 64.3% | 53.7% | 51.2% | 58.8% |
| fusion746 | 66.7% | 87.2% | 31.0% | 19.5% | 21.2% | 5.9% |
| tracknet686 | 64.6% | 87.2% | 31.0% | 19.5% | 17.5% | 5.9% |
| ballnet990 | 68.8% | 83.0% | 76.2% | 61.0% | 51.2% | 58.8% |

VERDICTS [MEASURED unless noted]:
1. §10's open question is ANSWERED: the archive's extra far-court locks were
   largely REAL ball. On disagreement frames the archive hits 53.7% vs the
   fresh runs' 19.5%. The pre-git code genuinely tracked the far court
   better; something real WAS lost.
2. §6's dismissal of BallNet v1 ("locks the adjacent court's ball / HUD") is
   PARTLY RETRACTED: per human truth it is the best ball-FINDER overall
   (65.0% hit@10) and by far the best far-court (76.2%). Its real defect is
   precision-when-no-ball (60% FP) — it fires at something whenever play
   stops. The misattributed-shots finding (§6) still stands; the cause is
   [INFERRED] its no-play FPs feeding events.py, not bad ball-finding.
3. Near court is near-solved for every track (83–92%); the far court is the
   entire battleground (31% fresh vs 76% ballnet).
4. HUD/adjacent-court per FP location analysis: at frame 1602 ALL FOUR
   tracks (incl. static-gated) lock the burned-in HUD box — the static gate
   kills sustained HUD glue but not brief flickers. Other shared FP sites:
   above the far curtain (adjacent-court motion, y≈200) and the frame edge
   (x≈1–12). These regions are the hard-negative shopping list for BallNet v2.
5. Honest headline: the best track finds the ball within 10px on ~65% of
   human-verified frames. The self-graded "84.7%" was flattery, as §4 warned.
6. Precision/recall split, cleanly measured on true dead time (round-2
   no-ball frames): gated fresh tracks false-fire 5.9%, archive/ballnet
   58.8%. Recall vs restraint is THE axis: the eager tracks find more real
   ball everywhere AND fire at over half of genuinely empty frames.

Caveats: FP rates rest on 26 no-ball frames (~4%/frame granularity);
one clip, one camera angle; hit@10 at 1280x720 (far-court ball is ~4-6px);
ballnet trained on this clip's frames w/ archive labels (indoor_elev
dataset) — home-field advantage; v2 must exclude yt_rally2 from training.

Implication for the roadmap: BallNet v2 with hard negatives (fix 1.2) is now
clearly the highest-value move — v1 already beats everything at finding the
ball and only needs its false-fire problem trained out. Regenerate pseudo-
labels with the static gate ON, add negatives from the FP regions above, and
score v2 against THIS benchmark (eval_gold.py), never against pseudo-labels.

## 12. Session 3 (2026-07-06) — BallNet v2, live-ball filter, 2nd gold clip

Built this session: 2nd gold clip yt_match40 (300 UNIFORM frames, real match
w/ changeovers, NO calibration — a cold generalization set neither v1 nor v2
trained on; 184 ball/24 no-ball/92 unsure). Regenerated pseudo-labels gated +
with negatives (relabel_train_clips.py; 21,591 labels + 2,783 negatives over 9
clips, yt_rally2 excluded). Trained BallNet v2 (train_ballnet.py, negatives,
selection = hit@10 − false-fire; val proxy ended 84% hit / 49% false-fire).
Built ball.filter_live_ball (offline live-ball trajectory filter) +
tools/{ball_perception.py, filter_cache.py}. Fixed a latent trainer crash
(xy tensor dtype). 57 backend tests pass.

**Result A — the live-ball filter is the session's biggest false-fire win**
[MEASURED, yt_rally2 gold, raw → +live]:
| track | hit@10 | FP(no-ball) | far-court |
|---|---|---|---|
| archive | 65.5% → 62.4% | 61.5% → **7.7%** | 64.3% → 64.3% |
| ballnet_v1 | 65.9% → 64.7% | 65.4% → **34.6%** | 76.2% → 76.2% |
Strips off-court + flicker segments; far-court recall UNCHANGED. Needs
calibration for the off-court test (motion-only without it).

**Result B — v2 vs v1, the honest read.** On yt_rally2 v2 looks far worse
(hit 47.7 vs 65.9, far 40.5 vs 76.2) — but that gap is almost entirely
**v1's data leak**: v1 trained on yt_rally2 (indoor_elev/archive labels), v2
did not. On the COLD clip yt_match40 (neither trained on it; uniform sample;
no calibration → no court gate/live filter) the truth [MEASURED]:
| track (cold) | hit@10 | hit@25 | FP(no-ball) |
|---|---|---|---|
| tracknet | 64.1% | 65.8% | 50.0% |
| fusion | 60.9% | 65.8% | 58.3% |
| ballnet_v1 | 65.2% | 66.8% | 75.0% |
| ballnet_v2 | 63.6% | 65.2% | 62.5% |

VERDICTS [MEASURED]:
1. v2 is a real but MODEST win over v1: on the fair clip, recall is tied
   (65.2 vs 63.6, within noise) and v2 false-fires less (75.0% → 62.5%). The
   "v2 regressed" story on yt_rally2 was v1's home-field advantage; the
   benchmark caught a ~11–18 pt data leak. v2 is the new honest baseline.
2. HUMBLING: on UNSEEN footage our custom BallNet does NOT beat off-the-shelf
   TrackNet — recall clusters 61–65% for all four, and TrackNet actually
   false-fires LEAST (50%) while v1 fires MOST (75%). BallNet's big prior
   leads were overfitting to its training clips. Custom training has not yet
   earned its keep on new footage.
3. The dead-time negatives only nudged false-fire (v1→v2 on cold clip 75→62%,
   on yt_rally2 gold 65.4→61.5%). They were the WRONG negatives — quiet
   frames, not the confusers (HUD/adjacent court/edges). §11 fix stands: mine
   HARD negatives from the FP regions. That is v2.1.
4. Far court still unsolved by training (v2 cold has no per-bucket split, but
   yt_rally2 far 40.5% cold). Needs the far-court recipe: sharper model input
   (far ball is ~2px at the 512-wide model input) + real far labels (the
   archive's verified far locks), NOT more epochs.

Net: the two proven levers are (a) the live-ball filter for false-fire [built,
needs calibration on new clips], (b) a far-court-specific retrain for recall
[designed, not built]. Ship v2 as baseline; keep v1 for reference. Artifacts:
weights/ballnet_v2.pt; data/output/yt_{rally2,match40}_*.perception.json;
data/gold/yt_match40.benchmark.md. Deferred tracker work (live-ball gate +
hit-anchored arc, TODO.md) unchanged; the filter is the offline first half.

## 13. Session E1 (2026-07-20) — fps priced; the arc gate found to be no gate

Goal was to price frame rate (docs/sessions/SESSION_E_ball_push.md). Frame rate
priced out as second-order, and the experiment built to test it exposed the
first-order problem. Full tables in the session doc's Results; headlines:

1. **Premise correction.** `tools/clip_inventory.py`: 13 of our 32 clips are
   60 fps, including the gold-labelled **yt_rally2 (1280x720/60fps)**. Past runs
   sampled it at frame_step=2, so "our evidence is all 24-30fps" was an artifact
   of our own sampling. The fps experiment therefore ran against real human gold
   labels at zero annotation cost.

2. **fps buys precision, not recall** [MEASURED, yt_rally2, 284 gold frames].
   tracknet hit@10: 43.4% @60 vs 42.6% @30 (flat, and 38.6% @15). What moves is
   junk rejection: mislocks 10.6/12.9/21.2% and no-ball false fires 15.4/30.8%
   at 60/30 fps. Far court is fps-INDEPENDENT (23.8% at both) — an apparent-size
   problem for E2's inference-side work, not a frame-rate one. Harness validated:
   tnet@30 reproduces Session 2's 41.5% (measured 42.6%).
   What 60fps does buy is sample density: 29.7 vs 16.8 locks/s, and `analyze`
   built 2 candidate arcs at 60fps vs 0 at 30fps (min_arc=6 unreachable).

3. **THE finding — `reproj_px` does not constrain speed** [MEASURED on noise-free
   ground truth, tools/arc_observability.py]. Walk the launch point along its
   viewing ray from z=0.3m to 3.0m: recovered speed spans 54.6 -> 151.5 km/h for
   one true 86.9 km/h ball, and EVERY depth reprojects under 0.15px. Identical at
   60/30/24 fps — geometry, not sampling. A hit->bounce arc pinned only at its
   bounce leaves launch depth free; the fit trades depth against speed and spin
   for nothing in pixels. With today's bounce-anchor-only fit the ground-truth
   arc returns +107% (60fps) to +143% (24fps) speed error.
   Corollary [MEASURED, arc_error_budget.py]: event-timing is NOT dominant —
   anchoring +-2 frames off costs only 1.5-3.4px, all inside the 6px gate. The
   session doc's "timing poisons the fits" hypothesis is disconfirmed.
   The fix, priced: an exact contact-height prior recovers speed to -2/-3/-4% at
   60/30/24 fps. Sensitivity: 0.25m of height error -> ~13% speed error, 0.5m ->
   ~25%. So E4's <5% MAE needs launch height to ~0.2m — pose (wrist height +
   striker court position) is the obvious source. This is E3's real job.

4. **Confirmed on real footage; gate FIXED and shipped.** analyze on yt_rally2
   @60fps produced an arc at reproj 3.5px — inside the gate — claiming 110 km/h
   and 10,361 rpm, and was promoting it to speed_source="physics",
   speed_confident=True, into the dashboard. speedspin.py now requires a
   plausibility band (20-250 km/h, |spin| <= 3500 rpm) in ADDITION to the
   reprojection gate, and records a reject_reason per arc. That clip's headline
   drops from a fabricated 110 km/h to the honest plane-average 81.7 km/h.
   114 backend tests pass (6 new: tests/test_speedspin_gate.py).

5. **E3's stated gate is void.** "≥1 arc passes at 6px with a physically sane
   speed" is satisfiable by noise. Replace it with agreement against an
   independent measurement (OCR'd SwingVision MPH, or a radar gun), or with a
   demonstrated collapse of the ray-walk speed spread once the launch point is
   constrained.

Not done (needs the user or a download): gold labels on a clay clip and a second
60fps clip; the image-level miss taxonomy (near-vs-far split came free and
already implicates apparent size); the TrackNet-dataset hit/bounce external check.

New/changed: tools/{clip_inventory,arc_error_budget,arc_observability}.py,
tools/run_fps_sweep.sh, ball_perception.py --target-fps, eval_gold.py
--common-frames, speedspin.py plausibility band, pipeline.py reject_reason print,
tests/test_speedspin_gate.py, data/output/fps/*, data/gold/yt_rally2.fps.md.
