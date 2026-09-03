# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK — CURRENT (started 2026-09-04)

Execute the lead's PRE-REGISTRATION "top-2 blob margin as a REFUSAL signal" (last
section of .claude/journals/lead.md). margin = 1 - score_2/score_1 over connected
components' area*peak.
BAR (pre-registered, unchanged): some threshold flags >=4 of the 5 known >10px bad
frames AND refuses <=5% of correctly-decoded both-fire frames. Both halves required.
Mandatory seeded null control: 1000 permutations of bad/good labels.
Also report margin on the null mismatches (fp32 fires, int8 does not; 8/2/8/3/5/1).
Ask the question of the fp32 heatmap (the graph that ships), not only int8.
n=5 is a CEILING. PASS = screen not verdict. If null can't separate at n=5 =>
report UNDERPOWERED, not passed. Inspect the rejects (rule 10).
DELIVERABLE: docs/evidence/top2-margin-refusal-signal.md
STOP-WHEN: verdict + null control written, or ~35 tool calls.
NOT-THIS-RUN: change ball_detector.js/ball.py, ship, 4th precision arm, re-run int8
inference, edit docs/STATE.md, git commit.

## STATE — 2026-09-04 — TASK COMPLETE

DELIVERABLE SHIPPED: docs/evidence/top2-margin-refusal-signal.md (7 sections, full).

VERDICT: **PASS on fp32 (as a SCREEN, not a verdict). FAIL on int8.**
- fp32 t=0.10: catch 5/5, collateral 11/523 = 2.1%. Any t in [0.077,0.30] passes
  (plateau); t=0.077 excluded as post-hoc (= widest bad margin 0.0769).
- int8: no t reaches 4/5 anywhere. On frames int8 gets WRONG its own margin is WIDE
  (0.86; 1.0000 = single blob). Quantisation RESOLVED the race rather than leaving one.
  => the signal is only computable on the fp32 graph. A real constraint, not a footnote.
- Guard failures 0/528 on BOTH heatmaps.
NULL CONTROLS all separate (so NOT underpowered): A pre-registered free permutation
  p=0.0000 (exact hypergeom P(>=5)=1.30e-08); B selection-adjusted (each draw searches
  the same grid) 0.0000; C cluster-preserving within-clip circular shift catch>=4
  p=0.0010, >=5 0.0000.
NULL MISMATCHES (27): fp32 margin median 1.0000, min 0.4421, 0% below 0.15 => margin has
  ZERO dropout signal. Mechanism: a dropout frame has no runner-up to argue with.
REJECT INSPECTION (the real qualifier): the 11 refused good frames decode PERFECTLY
  (max 0.318 px, three at exactly 0.000). At IDENTICAL margin incl. an exact 0.0000 tie
  the decode is right 3 of 4. Refusal precision 5/16 = 31%. Only 37/528 frames have 2+
  blobs. => the margin identifies the POPULATION AT RISK; it does not predict WHICH
  member flips.
Scripts live in the ephemeral scratchpad (top2_margin.py, top2_null.py) — promotion
question appended to docs/DECISIONS_PENDING.md.
Working tree touched: evidence file, DECISIONS_PENDING.md, journal, memory. No commit,
no STATE row, no code change.

## LOG — this task

- CARRIED FORWARD: `python` is a broken Store shim. Use backend/.venv/Scripts/python.exe
- CARRIED FORWARD: `grep -rn` across repo root TIMES OUT — use the Grep tool.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- CARRIED FORWARD: bash `/tmp` is NOT visible to the Windows python.exe. Never hand a
  /tmp path to the venv interpreter; use the scratchpad absolute path.
- 2026-09-04 TASK COMPLETE. Every number is in STATE above and in the evidence file.
