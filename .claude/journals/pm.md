# pm — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

Write DURING the work. Rewrite TASK/STATE in place; append to LOG; compact past ~30 lines.
Durable learnings -> `.claude/agent-memory/pm/`. Findings -> `docs/evidence/`.

---

## TASK — what I was asked to do

2026-09-09. **COURT WORK: TRIAGE AND CUT LINE.** Court only (ball/speed/score/mobile out).

DELIVERABLE: `docs/evidence/court-triage-2026-09-09.md`, four parts:
A. SURVIVES — findings independent of the compromised 20-clip gold pool.
B. PROVISIONAL — scored against the pool; for each say what re-run is needed AND whether
   re-placing the 4 misplaced calibrations would change the CONCLUSION or only the decimal.
C. DEAD — exact file paths to move to `docs/archive/resolved/` + one-line reason (LIST only,
   lead executes).
D. WHAT NEXT, ranked, with an explicit cut line (what I would NOT do and why). Must cover
   (i) the AGREE_PX=30 raw-pixel thread, (ii) whether "5 MIXED" clips mean one-homography-
   per-clip is the wrong data model for clips with cuts/zooms — worth testing? cost?
   (iii) the founder's product input: "the user moving around to set up the view" — SETUP-time
   camera motion is a different regime from mid-match drift and is nowhere in scope.
End with coverage confession: read fully / skimmed / did not open.

CONTEXT GIVEN (do not re-derive): pool provenance never established (`_exact` never meant
human placement; a Claude agent placed 9-10 clips and verified itself; = T26). Audit
instrument broken: all 28 corner sheets rendered on frame 0; 7 of 10 founder "wrong"
verdicts at risk from frame choice alone. RE-REVIEW DONE: 4 MISPLACED (HoHxFSX_gLk_s1/s2/s3,
bump_ntrp30), 5 MIXED (A7vXlWIlyrI, CYqapSq5llo, UHf0LeMU2pg, uR5q2cSM6AY, bump_ntrp30b),
1 HOLDS (sAjkpeRq4P4). Camera motion tested: NOT the cause — 0 of 20 clips change acceptance.
AGREE_PX raw-pixel: 30/10/5 px@640 at 640/1920/3840; normalising = shell 0->2 accepted but
admits two wrong courts at 1920.

NOT-THIS-RUN: moving/deleting files, docs/STATE.md, code, git commit, re-placing calibrations.
NO BASH. Grep/Glob unreliable (T25) — Read known paths only.
STOP-WHEN: doc written, or ~40 tool calls.

## STATE — where I got to

**RUN COMPLETE.** `docs/evidence/court-triage-2026-09-09.md` written — all four parts (A
SURVIVES / B PROVISIONAL / C DEAD+do-not-archive / D ranked next with explicit cut line),
plus coverage confession and NOT-ESTABLISHED. ~21 tool calls. Nothing left but the report
and one memory file.

Headline calls in the doc: (1) TWO pools, only the references pool is compromised — STATE's
"the 12/20 gate inherits it" is not established, flag to lead; (2) only 2 of 20 pool clips
confirmed misplaced, so 40% proposal recall / SEARCH BINDS survives any correction (worst
case 10/20 = 50%, still inside the <=60% band); (3) archive list is ONE file
(`yt-match40-calibration-is-wrong.md`) + a hazard note that withdrawn-guard does not skip
`docs/archive/resolved/`; (4) D1 = gold-pool archaeology, 1 session, do first; D3 = MIXED
clips are pool hygiene not a data model change (the product records one continuous take);
D4 = setup motion answered by CALIBRATE LAST + IMU stillness, not vision; D5 = AGREE_PX
REJECTED as a ship, court-normalised metric named and parked.

## LOG — newest first

- **THE BIGGEST FINDING OF THIS RUN — THERE ARE TWO POOLS, AND ONLY ONE IS COMPROMISED.**
  (a) REFERENCES pool = `data/<clip>_pts.json` with `_exact`, 20 clips, 1920/3840 px,
  names `A7vXlWIlyrI / flexi_* / mpc_* / hillsborough_* / am_hard_utr`. Read
  `eval/run_refs.py` lines 1-120 myself: this is the pool `_exact` gates, this is what
  T26 compromises, this is what the founder's 28 corner sheets rendered.
  (b) GOLD pool = `data/gold/*.court.labels.json`, 20 clips, all exactly 640 wide, names
  `am_classB am_college am_fr_sud am_grass1 am_ntrp30 am_ntrp40 am_ntrp45_courtlevel
  am_rally32short am_rec30 am_usta40 am_usta45 am_usta60` (+8 refused). **This is what the
  pre-registered >=12/20 + zero-over-20px gate scores against** — qa states the path
  explicitly in `court-mask-sweep-item-is-already-shipped.md` §2, and
  `cnn-global-classical-local.md` reports "Gold gate 12/20 -> 2/20" and "References 2/20
  -> 0/20" as SEPARATE lines.
  => **STATE row 241's claim that "the 12/20 gate" inherits the provenance defect is
  NOT established.** Different files, different tool, different resolution, different
  clips. It is not established CLEAN either — nobody has ever rendered a gold court
  label onto its frame (`render_corner_audit.py` reads `*_pts.json`). **UNEXAMINED, and
  that is the #1 item for part D.** Flag as a correction to the lead, do not edit STATE.
- **The AGREE_PX objection survives its own scrutiny.** Normalising admits `tc8CGFxyRE8`
  at 58.7 px. tc8CGFxyRE8 is (i) marked CORRECT by the founder and (ii) one of the 13
  short locked-off tripods with frame-choice spread <0.5 px (STATE:240), so its reference
  is corroborated by BOTH instruments. A 58.7 px accept against a corroborated reference
  is a real wrong court => the pre-registered gate forbids it. REJECT as a ship.
- **The principled alternative already exists in the repo, untested:** an agreement metric
  normalised in COURT terms not image pixels, which is resolution-independent by
  construction AND can weight width separately — the disagreement is `w_near`/`w_far` on
  13 of 18 clips (`court-detection-frames-that-each-find-the.md`). That is the right
  version of the AGREE_PX idea and it is NOT the one already in "What has not worked".
- **The SURVIVES spine is already visible and it is large.** Court findings that never
  touched the 20-clip pool: (a) least-squares-court-fit — FAILS <=10 px bar, control exact
  0.00 px vs committed corr_attrib, and the ceiling is the DETECTED LINES (6.4 px) not the
  fitter; (b) net-baseline-solve — synthetic solve-back exact 0.0000 m, truth-fed control
  reproduces far baseline to 0.007 px median on all 40 clips => geometry exact, DETECTION is
  what fails; availability binds (all four lines coexist on only 10/40); (c) the net-tape
  occlusion crossover ~2.0-2.2 m — derived from court geometry, not the pool; (d) camera
  motion NOT the cause — decisive control is self-disagreement on MOTIONLESS 4K tripods
  (29.9-37.5 px@640) + 0.01 px no-op on static clips; (e) CNN-global mechanism: CourtNet
  returns None because only 2-3 of 14 peaks clear 0.40 (min_points 6, homography needs 4) —
  a code/behaviour reading, pool-independent; (f) A13 cost of the court CNN (~300 GFLOPs x 8
  frames ONCE per video, all ANE-native ops); (g) T26 itself + the frame-0 audit defect.
- **The PROVISIONAL list is short but load-bearing:** 40% proposal recall (8/20), the 12/20
  gate itself, shell 1/5 recordings, CNN arm 2/20 vs classical 12/20, verify_court 3/25
  false rejects, composite calibration score 57%, and `courtnet_ft.pt` (trained on a pool
  holding 17 of 20 gold clips — that is a LEAK finding, separate from provenance).
- **Rule 3 hazard found:** "Widening / height-scaling AGREE_PX" is ALREADY a row in
  "What has not worked" (STATE:141). Any AGREE_PX recommendation must be framed as a
  CORRECTNESS/scale-invariance fix, not a recall recovery — and the new evidence file says
  normalising admits TWO WRONG COURTS at 1920, which the pre-registered gate forbids
  (zero accepted court >20 px). Leaning REJECT-as-shipped-change.
- (start 2026-09-09)

### Carried forward from prior runs (still binding on my recommendations)
- Manual 4-tap calibration IS v1's setup story; court auto-detect is NO for v1 and v1.x.
  Court port cut ~15-20 sessions. Scoring deferred, rally clips kept.
- The mount crossover (~2.2 m) splits v1 outputs: below it, warn at capture, ship
  shots/rallies, WITHHOLD speed and bounce map. Ball PIXEL numbers provably safe (the ball
  chain does not consume the calibration — `--no-gate` is byte-identical).
- Project owns NO confirmed metric footage; all four named mounts 1.36-1.74 m. Top founder
  ask: record ONE clip above 2.5 m, ~15 min.
- Human asks are scarce — batch into ONE update, ranked by leverage.
