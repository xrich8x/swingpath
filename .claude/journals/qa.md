# qa - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK - 2026-09-15: P2 OCCLUSION CENSUS (build the sheet, do NOT label it)
Build a contact sheet of candidate bounce frames on near-line bounces, from the 3
cached clips (am_hard_utr 1.74m, demo30 1.38m, yt_match40 1.64m). Founder does the
yes/no occluded pass (~45 min). Deliverables: sheet + tally form, evidence file
docs/evidence/occlusion-census.md with RESULT SECTION EMPTY, journal, commit no push.
BAR (pre-reg): >20% of near-line bounces occluded => SPEC <=5% refusal WITHDRAWN.
CORE TRAP: a detector-derived candidate set is biased AGAINST occluded bounces and
under-states the answer. Must state the anti-bias route + residual bias BEFORE building.
NEVER fix/tune anything. yt_match40 calibration KNOWN BAD (T23) - no near-line from it.

## STATE
- Read: CLAUDE.md, SPEC §3/§6, capture-floor-census.md (+2026-09-15 addendum),
  lead.md P2 pre-registration. Journal reset from prior (2026-09-10) task, which is DONE.
- RESUMED 2026-09-16 after kill. Pre-reg committed 29d2e3e. SHEET BUILT + VERIFIED:
  docs/evidence/occlusion-census/{sheet.html,items.js,tally_form.csv,build_sheet.py,
  _audio_from_git.py,audio_am_hard_utr_raw.json,pool.json,source_key.json}. 360 items
  (2 batches of 180). Rebuild byte-identical (items.js sha1 6d588d33). Headless Chrome:
  video decodes from file://, zone lights, HUD masks correct, page makes 0 network calls.
- NEXT: write amendments A1-A3 + §9 build record into evidence file, commit [no-state],
  update memory, report. DO NOT PUSH.
- WRITE-LOCATION DECISION: qa may not write tools/ or data/. Builder scripts go in
  docs/evidence/occlusion-census/ (sheet + form + the script that made them), NOT tools/.
  So no state-guard trip expected. Say so in report.

## INVENTORY (2026-09-16)
- am_hard_utr.mp4 1920x1080 59.94fps 28998 fr 483.8s, AUDIO yes. perception.json
  frame_step 1, ballnet v21, cuda. match.json fps 29.97 (shipped step 2), 120 shots.
- demo30.mp4 1280x720 29fps 870 fr 30s, no audio. perception tracknet. demo30.json's
  video.filename says "yt_rally2.mp4" -> check source identity (eval/recordings.py).
- yt_match40.mp4 1280x720 29fps 354s, no audio. NO yt_match40.perception.json; only
  _fusion/_tracknet/_v1/_v2 variants. Calibration KNOWN BAD (T23).
- Ball gold (data/gold/*.labels.json) is UNIFORM every ~116 frames -> useless as a bounce
  candidate source.

## LOG
- 2026-09-15: task recorded. Prior cleanup-verification task from 2026-09-10 archived/closed.
- 2026-09-16 FINDING: demo30 == yt_match40 frames 2552..3421 (thumb match 48x27 gray,
  mean abs diff 0.09-0.12 vs median 7.6-10.5; offset constant). ONE recording, not two.
  Yet fitted mounts differ (1.38 vs 1.64) on the same static camera -> calibration
  disagreement. Dedupe demo30 candidates into yt_match40 frame space.
- audio: shipped detect_impacts (git 7570a2a^, defaults) on am_hard_utr -> 811 events /
  483.8 s. Saved docs/evidence/occlusion-census/audio_am_hard_utr_raw.json.
- STATE l.197: net tape covers FAR BASELINE on all 3 clips (mounts < 2.0-2.2 m) ->
  far-baseline bounces structurally net-occluded; mount-specific, report separately.
- FINDING: demo30.perception.json has 1108 entries vs demo30.mp4's 870 frames; demo30.json
  names yt_rally2.mp4 (36.9s*30=1107). The "demo30 cache" is NOT from demo30.mp4. Moot for
  P2 since demo30 is a slice of yt_match40 -> use yt_match40 caches for that span.
- am perception ball_px len 14499 = 30fps-eff index (t=i/29.97). yt_match40 has 4 Jul-6
  tracks (v1/v2 ours-early, fusion, tracknet), none is BallNet v21; yt_match40.json (Aug 8)
  196 shots all with bounce_t_s; am_hard_utr.json 120 shots all with bounce_t_s.
- DESIGN: HTML viewer plays SOURCE video in-browser (h264, file://) looping a 0.55 s window
  at 0.25x — no media copied into git. Founder blind to source. 160 items batch 1
  (120 am + 40 yt), seeded permutation so any prefix is a random sample; batch 2 optional.
- NEXT: write evidence pre-reg (defs+bar+bias method) BEFORE building candidates.
- 2026-09-16 pre-reg committed 29d2e3e. First build: am pool 1102 (AV180/A631/V291),
  yt 549. SYNC CHECK: audio trails pipeline bounces by +0.10..+0.20 s (excess over null);
  pre-reg match window [-0.05,+0.15] splits events -> duplicates biased toward visible.
  Chance coincidence ~30% at 0.2 s (audio 1.68/s). AMENDMENT A1 (pre-label): greedy
  start-anchored clustering of ALL A+V events, span<=0.35 s; centre = median V time else
  onset-0.12; per-item TARGET ZONE = Voronoi between neighbour centres clipped to +-0.175 s,
  shown lit in viewer; AV membership chance-corrected with a shifted-audio null. Rebuilding.
- A1 rebuild: am pool 756 (AV329/A334/V93), zones cover 53.5% of video; yt pool 443
  (43.8%). CHANCE NULL (5 circular audio shifts): P(A|V-item) 0.758 null vs 0.780 obs;
  P(V|A-item) 0.484 null vs 0.496 obs -> membership ~uninformative; LP (§4.1) unusable.
  AMENDMENT A2 (pre-label): NEGATIVE-SPACE audit — blind-mixed seeded windows from
  UNCOVERED time; missed = density_uncov x T_uncov. Batch1 = 110 am pool + 20 am neg +
  35 yt pool + 15 yt neg = 180 (~45-50 min @15 s). Batch 2 same. Shuffle within batch.
- A3 (pre-label): rendered P2-001 and P2-003 (both am) are PRE-SERVE ball bounces ->
  added "only IN-PLAY bounces count" to Q1. Power risk: in-play yield/item may be <<50%.
- yt_match40 has SwingVision HUD incl. mini-court WITH BOUNCE DOTS + shot panel; am has a
  scoreboard -> masked in viewer (rule 12). Boxes: am [0,0,600,185]@1920; yt [0,0,310,170],
  [1075,0,1280,335]@1280.
- Slip: one command briefly wrote a hash file one dir ABOVE the repo; deleted, verified gone.
