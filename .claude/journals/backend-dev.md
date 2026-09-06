# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-06) CLEAN PLATE / MTI - MEASURE WHAT IT BUYS

Founder raised "MTI and temporal integration" for court detection. BOTH ALREADY EXIST.
Establish empirically what they buy, so researcher runs on measurement not speculation.
ORDER: (1) has tools/eval_court_cleanplate.py EVER been run + what did it report
(T24: do NOT trust a docstring's claim about its own run history); (2) run it across
the labelled court corpus, lock + err per clip vs SINGLE-FRAME and BLANK-RECTANGLE
baselines; (3) MECHANISM: line support on single frame vs plate - does the plate
actually recover occluded lines; (4) COST: decode time for ~80 frames / 60 s span.
DELIVERABLE: docs/evidence/cleanplate-mti-measured.md
NOT-THIS-RUN: editing data/*_pts*.json; changing court_setup_server.py behaviour; a new
gate; run.py parser; docs/STATE.md; any git commit. DO NOT TOUCH
docs/evidence/court-detection-research-2026-09-06.md (researcher is live).
STOP-WHEN: eval run + written up, or ~40 tool calls.

## PRE-REGISTERED BAR (written 2026-09-06 BEFORE running anything)

STATE records single-frame auto-seed FAILED: 7 of 10 worse than a blank rectangle.
Primary metric: per-clip median corner err px vs human clicks, and lock rate.
Corpus: every clip in data/gold/*.court.labels.json that the tool accepts (fixed,
declared before seeing results; no clip dropped after the fact).

- WORTH BUILDING ON (PASS): clean plate LOCKS on >=60% of corpus clips AND, on the
  clips where both it and single-frame produce a court, it beats single-frame on err
  on a MAJORITY of clips, AND it beats the blank-rectangle baseline on a MAJORITY.
- RETIRE (FAIL): clean plate does NOT beat the blank rectangle on a majority of
  clips, OR it locks on <30% of the corpus. (i.e. it repeats the single-frame
  failure - temporal integration bought nothing.)
- AMBIGUOUS in between -> report as ambiguous, do not round to PASS.

MECHANISM BAR (independent of score, item 3): "the plate recovers occluded lines"
is SUPPORTED only if line support (fraction of court-line samples landing on white
line pixels), computed with the SAME human homography on both images, is HIGHER on
the plate than on a single frame for a MAJORITY of clips tested. If score moves but
line support does not, the score is measuring something other than the premise --
report that as the headline.

COST BAR (item 4, declared BEFORE sweeping n): a reduced (n, span) is "as well" if
it locks the same set of clips AND its median err is within 2.0 px of the full
(n=150, span=90) setting on every clip where both lock. Anything else is worse.

## STATE - 2026-09-06 - bar pre-registered; next: T24 run-history check

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- NOTE: brief says court_setup_server.py:39 clean_plate_and_motion(n=80, span_s=60).
  eval_court_cleanplate.plate_from_video defaults n=150, span_s=90 and does NOT call
  the MTI path at all - it calls its own median. Two different implementations.
