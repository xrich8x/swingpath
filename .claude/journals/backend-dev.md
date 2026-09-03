# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK — CURRENT (started 2026-09-03, follows the seen_frac run + qa verification)

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
