# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-06) NEAR-BASELINE + NET LINE DETECTION PRECISION

Falsifier for `docs/evidence/net-baseline-solve-without-far-line.md`. Measure the
detected-vs-truth error of FOUR observables separately: (a) near baseline ROW,
(b) net line ROW, (c) near baseline WIDTH, (d) court WIDTH at the net. Then feed my
own measured errors into the solver and report where the EXTRAPOLATED FAR BASELINE
lands vs truth on REAL clips. Verdict: does the <=2 px premise hold / borderline / fail.
Message qa FIRST with the protocol (qa is measuring whether the clean plate sharpens
the same two lines - numbers must be comparable), message again with the result.
DELIVERABLE: docs/evidence/near-line-detection-precision.md
NOT-THIS-RUN: editing data/*_pts*.json; a court detector; docs/STATE.md; git commit;
qa's docs/evidence/cleanplate-mti-measured.md.
STOP-WHEN: sweep + end-to-end written up, or ~40 tool calls.

## PRE-REGISTERED BAR (written 2026-09-06 BEFORE measuring anything)

UNITS: everything in **px@640** (frame resized to width 640). The 8.1 px shipped bar
and the 6.4 px line floor are both px@640, so the Monte Carlo's <=2 px is px@640 too.

- PASS: pooled median error <=2.0 px@640 on ALL FOUR observables, AND end-to-end
  extrapolated far-baseline row error on real clips <=8.1 px@640 at the MEDIAN.
- FAIL: any of the four observables at >=6.4 px@640 pooled median, OR end-to-end
  median >8.1 px@640, OR the net line is MISSED on >50% of clips (availability
  failure counts as FAIL regardless of the error on clips where it is found).
- BORDERLINE: in between (2.0-6.4 px on the observables, or end-to-end median inside
  8.1 with p90 outside). Report as borderline; do NOT round to PASS.
- Population fixed before looking: every clip with BOTH a `data/*_pts*.json` human
  4-corner click AND a locatable video. No clip dropped after the fact; misses are
  reported as misses, not excluded.

## STATE - 2026-09-06 - DONE. Deliverable written, verdict FAIL, memory updated. Only open item: qa exchange (SendMessage disabled).

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- FOUND: `eval/line_snap.py` docstring already reports the nearest-detected-line
  distance for the four OUTER lines: near baseline median **2.7 px@640** (within 8 px
  on 36/40), far 2.9, left sideline 1.3, right 4.1. That is a strong PRIOR for (a).
  It does NOT cover the NET line, and it is a line-to-line distance, not the four
  solver observables. Data said to be in data/output/.
- KEY RISK, stated before measuring: **there is NO painted line at the net.** The
  solve needs the net GROUND row (y=11.885 m); the detectable object is the net TAPE
  (0.914 m above ground at centre, 1.07 at posts) or the net's base/shadow. Memory
  `net-ground-vs-net-tape` says confusing them condemned a CORRECT calibration. I will
  measure BOTH interpretations and report which is actually found.
- Detector to use = the SHIPPED one: `calibration.line_ridge_mask` -> `courtfit._detect_lines`.
- SendMessage TOOL IS DISABLED this session ("No such tool available: SendMessage.
  SendMessage is disabled ... in subagents as well"). Protocol therefore published in
  docs/evidence/near-line-detection-precision.md SS1 as the channel to qa. Reported up.
- HARNESS: eval/near_line_precision.py -> data/output/near_line_precision.json (n=40).
- RESULT 1 (CONTROL): solve fed TRUTH observables reproduces the human far baseline row
  to 0.007 px@640 median / 0.75 max over 40 REAL clips. The pinhole model is NOT the
  limit. Only detection is.
- RESULT 2: shipped corr_attrib._match_line gates on |rho| from the IMAGE ORIGIN -> for
  long oblique lines a 6 deg tilt barely moves rho. It accepted right-sideline matches
  up to 316 px@640 off the truth segment (median 34.9 of 27 accepted). Under a geometric
  perp matcher only 18/40 right sidelines match. BUG-CLASS, affects corr_attrib pops.
- RESULT 3 (four observables, px@640, perp matcher, gate 12): (a) near row 0.83 med
  n=16; (b) net row 6.22 med n=11; (c) near WIDTH 12.44 med; (d) net WIDTH 44.63 med.
- RESULT 4 (end-to-end n=10): far ROW 3.99 med / 6.77 p90 / 8.01 max  BUT far WIDTH
  32.7 med -> far CORNER ~17.4 px@640 median vs the shipped 8.1 bar. FAIL.
- MECHANISM: r_net - r_far = (r_near - r_net) * D/(D+23.77) -- compressive, so a 20% k
  error costs only ~4 px of ROW. The far WIDTH = f*W/(D+23.77) inherits the D error in
  full. Camera HEIGHT is recovered to 0.02-0.16 m even at 40% D error.
- NET: there is no paint at the net. ground line found 24/40 (med 5.80); TAPE found
  38/40 (med 4.10) and sits 15-47 px@640 above ground. Substituting tape for ground
  puts the far baseline 32 px@640 out (min 19 max 59) = 4x the bar.
- VERDICT: the <=2 px premise FAILS. Only (a) is near it.
