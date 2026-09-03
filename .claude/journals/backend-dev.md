# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — CURRENT (started 2026-09-03): does `seen_frac >= 0.5` predict speed error?

MEASUREMENT ONLY. Do NOT change the 0.5 constant, do NOT propose a replacement number,
no commit, no STATE edit. Bar pre-registered at the END of `.claude/journals/lead.md`
("PRE-REGISTRATION — does `seen_frac >= 0.5` actually predict speed error?").
G = median |err| in [0.35,0.50) >= 1.5x that in [0.50,0.65) on >=2 of 3 clips.
N = ratio <= 1.1x on >=2 of 3. I = anything between. Floor: n>=15 in EACH band per clip;
<2 clips clearing the floor => UNDERPOWERED.
DELIVERABLE: `docs/evidence/does-seen-frac-predict-speed-error.md`.
STOP-WHEN: verdict written, or ~40 tool calls.

## STATE — where I got to

**STEP 1 ANSWERED — a compliant per-shot absolute error IS obtainable, but ONLY on
synthetic flights.** Real clips have no absolute speed reference (HUD is barred), so the
paired dataset must be manufactured. `tools/synth_truth.py::measure()` already does
truth-vs-shipped-estimator per flight; it thins the pixel track with a `dropout`
parameter, which is the SAME quantity `seen_frac` measures.

MISMATCH FOUND AND MUST BE FIXED IN MY HARNESS: synth_truth simply DELETES dropped
points; the shipped pipeline REPLACES them with smoother forecasts and then integrates
over the filled track (`pipeline.py:1756` `analytics.shot_speed_kmh(track[h:land+1])`,
track includes coasted frames; `ball_seen` at :1460 = emitted and NOT coasted;
`real_fraction` :1716 = fraction of [h,land] with ball_seen). So my harness must run
the thinned pixel track through the SHIPPED `ball.smooth_forecast` and use its
`coasted` output to compute seen_frac exactly as the pipeline does.

TRUTH COMPARATOR, FIXED BEFORE ANY NUMBERS: `avg_ground_kmh` (synth_truth's error
budget component 3 — the only part that is our error). Using `launch_kmh` would add the
shared -21.7% drag bias to both bands and compress the ratio toward 1 (biased toward N).
Launch-based reported as secondary descriptive only.

CLIPS (= calibrations): `yt_rally2` (1.4 px, 3.31 m, 1280x720), `am_hard_utr`
(0.7 px, 1.74 m, 1920x1080), `yt_court` (2.1 px, 2.42 m, 1280x720 assumed).
EXCLUDED: `yt_match40` (T23 corners off the lines — speed needs the homography),
`demo30` (STATE: speeds never citable).

## LOG — newest first

- 2026-09-03 New task. Previous task (smoother backward re-admit) CLOSED: verdict FAIL,
  file `docs/evidence/smoother-gate-backward-readmit-separation.md`, not committed.
- CARRIED FORWARD: `python` is a broken Store shim. Use `backend/.venv/Scripts/python.exe`
  (CPU), `backend/.venv-train/Scripts/python.exe` (CUDA).
- CARRIED FORWARD: `grep -rn` across repo root TIMES OUT — use the Grep tool.
- CARRIED FORWARD: hardcode REPO in scratchpad scripts; `while not (REPO/"backend").is_dir()`
  spins forever from a drive root.
- 2026-09-03 HARNESS BUILT + SMOKE-TESTED (scratchpad/seen_frac_vs_error.py, 40 flights/clip).
  Mirrors the shipped speed chain per flight: smooth_forecast -> image_to_court + runoff
  gate -> cap_court_jumps -> smooth_and_fill -> analytics.shot_speed_kmh; seen_frac from
  (emitted AND not coasted) exactly as pipeline.real_fraction. ONE VARIABLE = per-flight
  dropout ~ U(0.05,0.80), drawn INDEPENDENTLY of the flight. seed=0 all clips => same
  launches, different cameras (paired). hfov per clip from height_curve.hfov_of:
  yt_rally2 93.7, am_hard_utr 86.1, yt_court 60.0.
  Import gotcha: smooth_and_fill lives in swingvision.ball, NOT pipeline.
  SMOKE FINDING: errors are LARGE overall (median |%| ~56) and dominated by a CONFOUND —
  the runoff gate + cap_court_jumps delete most of a LOB's flight (courtfrac 0.09), so
  smooth_and_fill fills flat and speed collapses. This is shipped behaviour, kept. It is
  independent of dropout by construction so it adds noise, not bias, to the band
  comparison; medians + large n absorb it. Confound correlations to be REPORTED.
  PRIMARY METRIC pre-committed before the full run: absolute PERCENT error vs
  `avg_ground_kmh`. km/h error and launch-referenced error reported as secondary.
- 2026-09-03 **PRIMARY RESULT IN (n=1200 req/clip, 2557 usable flights).** Ratio
  med|%|[0.35,0.50) / [0.50,0.65): yt_rally2 **1.35**, am_hard_utr **0.86**,
  yt_court **0.76**. ALL THREE clear the n>=15 floor (155/201, 132/171, 143/197).
  G needs >=1.5x on >=2 of 3: NO clip reaches it. N needs <=1.1x on >=2 of 3: TWO clips
  do (0.86, 0.76). => **VERDICT N — the gate does NOT predict error at its own threshold.**
  Mann-Whitney adjacent bands p=0.50/0.92/0.68, pooled 0.86.
  Whole-range Spearman IS weakly negative (-0.169/-0.030/-0.097) — a trend exists at the
  EXTREMES, not at 0.5. Descriptive only; does not override the registered test.
  REJECTS: refused-but-accurate n=268 (38.1% of refused, med |%| 18.8 — BETTER than the
  accepted median 46.9). Accepted-but-inaccurate n=927 (50.0% of accepted). Neither set
  is small. What actually separates accurate from inaccurate is court-coverage fraction
  (rho -0.749) i.e. max_z / the runoff gate, NOT seen_frac.
  Artifacts (scratchpad): seen_frac_vs_error.py, analyse.py, paired.json.
  NEXT: sensitivity arm applying the pipeline's OWN shot filters (5 < speed < 250, and
  speed<=160 from the same conjunction) — my population currently includes flights the
  pipeline would never have scored as shots. Labelled SECONDARY; verdict stays primary.
- 2026-09-03 **DELIVERABLE COMPLETE**: docs/evidence/does-seen-frac-predict-speed-error.md,
  all 7 sections + NOT ESTABLISHED. **VERDICT: INDETERMINATE** (G refuted in all 4
  populations; N holds on the unrestricted population 1.35/0.86/0.76 but NOT on the
  shipped-shot population 1.11/1.21/0.97, so the honest read is the weaker one, I).
  Sensitivity arms A/B/C added because my first population included flights the pipeline
  drops as non-shots (est<5 or >250 km/h) — a fidelity oversight, bar unchanged.
  Reject/classifier headline: accept-precision 0.500 vs 0.472 base rate.
  Real driver of speed error is COURT-COVERAGE fraction (rho -0.749) not seen_frac (-0.098).
  Heredoc gotcha: `cat > f <<'EOF'` FAILED on this long markdown ("unexpected EOF looking
  for matching '") — used the Write tool instead. Do that for long docs.
  REMAINING: memory update, DECISIONS_PENDING entry. No commit, no STATE (both barred).
- 2026-09-03 TASK CLOSED. Memory written (speed-error-is-geometry-not-detection,
  synth-truth-as-a-paired-error-rig + MEMORY.md index). DECISIONS_PENDING entry appended.
  No commit, no STATE row, no threshold touched — all barred by the brief.
