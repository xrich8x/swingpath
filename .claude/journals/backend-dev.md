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

## STATE — 2026-09-04

KEY ASSET FOUND, do not re-derive: `backend/ball_parity_margin_census.py` already
implements the exact blob scoring (threshold 127, 8-connected, area*peak) with a
GUARD that the top blob centroid == what the real _decode recorded in
js_results.json. On the 6-clip run guard failures were 0/528.

PARITY DIRS (all present on disk, each has js_results.json + onnx_heat_<tag>.bin):
  am_hard_utr  C:\Users\richm\AppData\Local\Temp\claude\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\90dad6dd-87a4-4ac2-a50e-c4dab20c69f4\scratchpad\ball_parity
  yt_match40   ...\90dad6dd-...\scratchpad\ball_parity_yt_match40
  yt_rally2    ...\90dad6dd-...\scratchpad\ball_parity_yt_rally2
  gold_am      ...\ccc041b7-...\scratchpad\ball_parity_gold_am
  gold_clay    ...\ccc041b7-...\scratchpad\ball_parity_gold_clay
  gold_shell   ...\ccc041b7-...\scratchpad\ball_parity_gold_shell
Bad-frame identity comes from data/output/ball_detector_int8_parity_summary__<clip>.json
(worst_frames[].dist_px > 10) + null_mismatch_tags.

PRIOR KNOWLEDGE from the census docstring (qa swept it 2026-09-03): "all five int8
failures are close races" holds at close=0.15 but drops to 2/5 at 0.05. Widest of the
five failures' margins is 7.69%. yt_match40 and gold_clay contain ZERO close races.

## LOG — this task

- CARRIED FORWARD: `python` is a broken Store shim. Use backend/.venv/Scripts/python.exe
- CARRIED FORWARD: `grep -rn` across repo root TIMES OUT — use the Grep tool.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- 2026-09-04 Located all 6 parity dirs + the existing census script. Next: write a
  margin-extraction script into scratchpad that dumps per-frame margins (fp32 AND int8
  heatmaps) + labels, then sweep t, then null control.
