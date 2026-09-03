# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK — CURRENT (started 2026-09-04)

EXECUTE the REPAIRED bar written at the end of §"§7's held-out sweep, EXECUTED" (lead
wrote it; I execute it — authorship/execution deliberately separated).
Bar (pre-registered, unchanged): a replacement `t` is admissible iff
 (1) >=10 pts margin on >=3 of 4 held-out clips, AND
 (2) +/-0.05 plateau (both neighbours within 3 pts), AND
 (3) accepts >=60% of the shots shipped t=0.5 accepts (COVERAGE FLOOR).
 Flat-margin-across-whole-sweep => mechanically confounded => rejected.
Held-out clips FIXED: L73ep7JHiJ4, mpc_tuesday_p01, flexi_franz_p01, tc8CGFxyRE8.
>=5 seeds, both populations. Also run court-coverage. Also: sensitivity of the verdict
to the 60% floor value (does 50% vs 70% flip it? then the floor is itself arbitrary).
DELIVERABLE: section "The repaired bar, executed" appended to
  docs/evidence/does-seen-frac-predict-speed-error.md
STOP-WHEN: verdict + floor-sensitivity written; or ~35 calls.
NOT-THIS-RUN: change 0.5, adopt any t, add clips, edit STATE, git commit.

## STATE — 2026-09-04

REUSED the lead's 5 seed runs + ran seeds 5-9 => 10 seeds in
scratchpad/holdout/s{0..9}.json. Analysis scripts: scratchpad/repaired_bar.py,
scratchpad/tables.py (tables.md = emitted markdown).

STALE-STAMP CAUGHT: s0-s4 stamp commit `bce6678`, s5-s9 stamp `7dc81c6`, but the tool
was UNCOMMITTED at the lead's run time, so bce6678 is stale. PROVED equivalent: re-ran
seed 0 at HEAD -> `results` JSON identical to s0.json. Pooling the 10 is legitimate.

RESULTS (10 seeds, mean margin pts):
- seen_frac unrestricted: 4/4 clips >=+10 only at t=0.85 (cov 26.5% of shipped accepts)
  and t=0.90 (15.4%, sweep edge so plateau not evaluable). Last t meeting the 60% floor
  is 0.65 (69.4%) at 0/4. => **NONE ADMISSIBLE**. Holds for ANY floor above 26.5%;
  0.85 only becomes admissible at a floor <=25%. Floor is NOT load-bearing.
- seen_frac shipped_shot: max 1/4 anywhere => NONE at every floor incl. 20%.
- court_cov unrestricted: 4/4 at EVERY t, +38.6..+43.3, spread 4.69 on mean 40.7
  (11.5%); passes floor easily => admissible by the LETTER, rejected by the flatness
  clause. Mechanism evidence: precision already 0.887 at t=0.20 and only 0.933 at 0.90
  (all discrimination is at court_cov~0; 53.6% of rows sit below 0.20), and on
  shipped_shot (drops 33.8% of rows, the out-of-range speeds) the margin collapses to
  +1.3..+25 with only 1/4 (2/4 at t>=0.80) clearing.
- Reject inspection: at t=0.85 seen_frac REFUSES 76.8% of all accurate shots (21.6% at
  t=0.5) to buy precision 0.556 -> 0.621.

## LOG — this task

- 2026-09-04 **DELIVERABLE SHIPPED**: section "The repaired bar, EXECUTED" appended to
  docs/evidence/does-seen-frac-predict-speed-error.md (file now 919 lines). Contains the
  three-condition per-threshold tables for both metrics x both populations, the
  NONE-ADMISSIBLE verdict, the floor-sensitivity table (20/25/30/40/50/60/70/80%), the
  reject inspection, and a section 5 criticising the bar itself (flat-margin clause has
  NO NUMERIC DEFINITION -> must be fixed before reuse; 60% floor arbitrary but not
  decisive). Nothing adopted, 0.5 untouched, no commit, STATE not edited.
- 2026-09-04 **TASK COMPLETE.** Memory updated: speed-error-is-geometry-not-detection
  (gate CLOSED, not just weak), traps (stale `git rev-parse HEAD` when the tool is
  uncommitted), null-controls (precision bar with no coverage floor is degenerate-
  satisfiable; report an arbitrary constant as a sensitivity; "flat" needs a number),
  + MEMORY.md line 20. Working tree touched: the evidence file + journal + memory only.

---

## TASK — DONE 2026-09-03 (kept for context)

A. Promote the seen_frac harness into `tools/` (args: clips, seed; defaults = evidence
   config; qa's correlated-dropout positive control as an OPTION not a fork).
B. **The real work:** diagnose WHY my ratios (1.11/1.21/0.97 restricted) and qa's rebuild
   (1.18/1.46/1.89) diverge, flipping sign on yt_court. Report the CAUSE. If the ratio is
   inherently unstable, that instability IS the finding.
C. Fix the pipeline.py citation + add qa's saturation limitation + state the
   court-coverage/error correlation is PARTLY MECHANICAL.
DELIVERABLE: tool under tools/ + reconciliation appended to
  docs/evidence/does-seen-frac-predict-speed-error.md
STOP-WHEN: tool in working tree + divergence explained or shown inherent; or ~40 calls.
NOT-THIS-RUN: change 0.5, propose replacement, re-litigate verdict, edit STATE, git commit.

## STATE — where I got to

**BOTH IMPLEMENTATIONS FOUND IN MY OWN SCRATCHPAD** (qa's session shared the same temp
dir id ccc041b7-...). Paths: scratchpad/seen_frac_vs_error.py (mine), analyse.py (mine),
positive_control.py + full_check.py (qa's).

**CAUSE #1 FOUND, AND IT IS MY BUG: `RUNOFF_M`.** Mine used 4.0. The SHIPPED pipeline
uses **2.5** (`backend/swingvision/pipeline.py:1352`). qa used 2.5 = correct. Since §6
established court-coverage is the dominant error driver (rho -0.749), a wrong runoff box
changes exactly the quantity that dominates the error. This is a fidelity defect in the
evidence file's harness, NOT merely an RNG difference.

Other diffs catalogued (to be ablated one at a time):
- MIN_ALIVE: mine 5, qa 6.
- RNG scheme: mine draws dropout/noise/alive from the SINGLE rng returned by
  ST.simulate, sequentially, and `continue`d flights consume no draws (so assignment
  shifts); qa uses separate streams seed+1000 (dropout) / seed+2000 (noise+alive) and
  indexes dropout over the FILTERED flight list.
- Track assembly: mine keeps a FULL-LENGTH [0..j] list with None holes into
  smooth_and_fill; qa COMPRESSES out frames where smooth_forecast returned None, so
  Savitzky-Golay's window spans a different real duration.
- Noise: mine adds to all j+1 points, qa only to in-frame points (RNG draw-count differs).
- N: mine 1200 req/clip, qa 500 (control) / 800 (full_check).

CITATION CONFIRMED (task C): 1759 `if speed < MIN_SPEED_KMH: continue`;
1761-1762 `if not is_serve and (disp < 0.8 or speed > 250.0): continue`. Note the
conjunction ALSO contains `disp < 0.8`, which my Arm A/B did not apply either.

## LOG — newest first

- CARRIED FORWARD: `python` is a broken Store shim. Use `backend/.venv/Scripts/python.exe`.
- CARRIED FORWARD: `grep -rn` across repo root TIMES OUT — use the Grep tool.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- CARRIED FORWARD: hardcode REPO in scripts; upward-search for "backend" spins forever.
- 2026-09-03 Read both scripts, diffed them, found the RUNOFF_M 4.0-vs-2.5 defect.
  NEXT: write tools/seen_frac_speed_error.py with runoff/min-alive/rng-scheme/track-mode
  as flags so each can be ablated as ONE VARIABLE; reproduce my old numbers with
  --runoff 4.0 --legacy flags (refactor must prove it changed nothing); then sweep seeds.
- 2026-09-03 **TOOL WRITTEN AND IT REPRODUCES BOTH IMPLEMENTATIONS EXACTLY.**
  `tools/seen_frac_speed_error.py`.
  * defaults, --n 1200: unrestricted 1.346/0.855/0.756 with band n 155/201, 132/171,
    143/197 = published 1.35/0.86/0.76 and published counts EXACTLY. n_usable 2557 exact.
  * `--max-speed-kmh 160` (= evidence Arm B) 1.114/1.207/0.969, n 125/163, 78/97, 97/118
    = published Arm B 1.11/1.21/0.97 EXACTLY.
  * `--runoff-m 2.5 --min-alive 6 --rng-scheme split --track-mode compressed --n 800`
    (= qa's rebuild) shipped_shot 1.180/1.465/1.893 with n 81/95, 38/54, 55/66
    = qa's table 1.18/1.46/1.89 with n 81/95, 38/54, 55/66 EXACTLY.
  * The refactor proof is therefore two-sided: one file, two flag sets, both prior
    numbers land on the digit.
  **CAUSE #0 (framing error in the brief, not either agent's fault):** the brief compares
  my Arm **B** (1.11/1.21/0.97, `5<est<160`) with qa's Arm **A** (`5<est<250`). My Arm A
  is 1.110/1.223/1.017 — so part of the yt_court "0.97 vs 1.89" gap is a population
  mismatch. Arm A vs B on my side only moves yt_court 1.02 -> 0.97, so it is NOT the
  main cause. Ablations of the 4 real flags next.
  Stream-order gotcha that was load-bearing for exact repro: the original harness
  `continue`d on `alive.sum() < MIN_ALIVE` BEFORE drawing pixel noise, so a rejected
  flight consumes no normal() draws. Replicated explicitly.
- 2026-09-03 **CAUSE FOUND: THE RATIO IS SEED-UNSTABLE. It is not any implementation choice.**
  One-variable ablations from the default, Arm A, n=1200, yt_court (the clip that flipped):
  baseline 1.017; --runoff-m 2.5 -> 1.038; --min-alive 6 -> 0.961; --rng-scheme split ->
  1.013; --track-mode compressed -> 0.965. **No single flag moves it more than 0.06.**
  Largest single-flag move on ANY clip: --min-alive 6 on am_hard_utr 1.223 -> 1.559.
  SEED SWEEP (seeds 0-9, Arm A ratio):
    evidence default n=1200: yt_rally2 mean 1.312 sd 0.338 range 0.826-1.944;
      am_hard_utr 1.070 sd 0.256 range 0.554-1.377; yt_court 1.088 sd 0.166 range 0.924-1.395.
    qa config n=800: yt_rally2 1.715 sd 0.445 range 0.962-2.274; am_hard_utr 1.394 sd 0.352
      range 0.800-1.972; yt_court 1.304 sd 0.404 range 0.623-1.893.
  => seed 0's yt_court 1.017 vs 1.893 is ~2 sd of pure sampling noise, not a bug in either.
  **IMPORTANT AND MUST BE STATED, NOT HIDDEN:** under qa's (shipped-fidelity) config the
  pre-registered G would PASS on 4 of 10 seeds (2,3,6,9 have >=2 clips at >=1.5x). Under the
  evidence-file default config G passes on 0 of 10. So "G fails" is robust to seed ONLY in
  the config with the runoff bug. This does NOT establish G — it establishes the test cannot
  decide at n~1200/clip, which STRENGTHENS the INDETERMINATE verdict and kills the digits.
  Secondary: the 4 flags together DO shift the MEAN ratio up ~+0.3 on every clip; it is the
  seed noise on top of that shift that produced the sign flip.
  NEXT: bootstrap CI on seed 0 to state what precision IS defensible; then write §8 + fix
  citation + add saturation + mechanical-correlation caveats.
- 2026-09-03 §8 APPENDED to docs/evidence/does-seen-frac-predict-speed-error.md +
  citation fixed (1759/1761-1762 + `not is_serve` + `disp<0.8`) + §7 item 5 now states the
  court-coverage correlation is PARTLY MECHANICAL + NOT-ESTABLISHED bullets updated
  (harness resolved; "why populations disagree" WITHDRAWN as noise; saturation ceiling added).
  Boundary trap found while writing: **74 of 2557 rows sit EXACTLY on seen_frac==0.5** (2.9%).
  Both implementations use the same half-open convention so it is not the cause, but a
  `<` -> `<=` slip would move 3% of the sample in the direction that flatters the gate.
  REMAINING: positive-control (--arm correlated) smoke test, memory update.
- 2026-09-03 **POSITIVE CONTROL ALSO REPRODUCES EXACTLY** (`--arm correlated`, qa flags,
  n=500): 1.583/0.905/1.046 random and 1.763/1.000/1.142 correlated, every band count
  matching qa's 1.58/0.91/1.05 and 1.76/1.00/1.14. So the one promoted tool reproduces
  THREE prior result sets: my primary+ArmA+ArmB, qa's shipped-shot arm, qa's control.
  NEW FINDING from running the control through the tool: pooled accept-precision vs base
  rate goes 0.500/0.462 (+3.8 pts) random -> 0.501/0.353 (+14.8 pts) correlated, and
  refused-but-accurate collapses 36.4% -> 4.5%. So the CLASSIFIER metric detects the
  injected effect strongly and would clear §7's >=10-point bar, while the BAND RATIO barely
  moves on 2 of 3 clips. The ratio-of-medians estimator is the weak instrument, not the
  harness or the data. Added to §8.1.
  REMAINING: memory update. Everything else done.
- 2026-09-03 **TASK COMPLETE.** Working tree: tools/seen_frac_speed_error.py (new),
  backend/tests/test_seen_frac_speed_error.py (new, 4 pass in 3.3s),
  docs/evidence/does-seen-frac-predict-speed-error.md (§8 + citation + caveats),
  docs/DECISIONS_PENDING.md (metric note). Memory: new
  band-ratio-of-medians-is-a-weak-instrument.md + 2 existing updated + index.
  No commit, no STATE row, 0.5 untouched, no replacement threshold — all barred.
