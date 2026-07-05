# HANDOFF — SwingVision-clone: state, evidence, and claims audit

Written 2026-07-05 for a fresh Claude session. Purpose: everything done, with
evidence levels, so the next session can find real fixes and catch any
hallucinated/overclaimed results. **Trust the artifacts, not the narrative.**

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
labels as training data; see ROADMAP.md for the full PM version)

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
