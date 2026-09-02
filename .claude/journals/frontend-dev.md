# frontend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/frontend-dev/`, and
findings go in `docs/STATE.md` + `docs/evidence/`. Do not duplicate those here.

---

## TASK 5 (current) — coordinator: characterise the int8 ball-detector failure mode.
Frame 0147 on am_hard_utr disagreed fp32-vs-int8 by 70.8px (full-178-frame run,
see docs/evidence/ball-detector-parity-tracknet.md "Full 178-frame int8 run" section).
Need: (1) named mechanism for 0147 specifically, (2) same probe on >=2 OTHER
calibrated clips so the rate has more than a 1-clip denominator, (3) report rate
per clip + worst frame + whether failures cluster or scatter. gold_sAjkpeRq4P4 is
slowest calibrated clip — told to leave last/skip.

### STATE (task 5)

- **0147 MECHANISM FOUND.** Inspected heat_0147.bin (PyTorch ref) / onnx_heat_0147.bin
  (fp32 ONNX) / int8_heat_0147.bin (int8 ONNX) directly with connected-components
  (script: scratchpad/inspect_0147.py). fp32 (both PyTorch ref AND fp32 ONNX,
  byte-identical): 2 blobs, real-ball blob area=15 peak=220 score=3300 WINS over a
  competing blob area=13 peak=242 score=3146 — a CLOSE margin (~5%). int8: the
  true-ball blob's pixel footprint is quantisation-eroded/fragmented from one
  15px component down to two tiny components (area=2 + area=1, well below
  threshold density), collapsing its area*peak score to 440 — the competing
  blob (unchanged, area=13 peak=242 score=3146) now wins outright, and the
  (correct, already-fixed) connected-component decode picks it. NOT a repeat of
  the old decode-algorithm bug (this uses the correct area*peak decode on both
  sides) — this is quantisation eroding the losing... er, the WINNING blob's
  pixel count right at a heatmap that was already a close two-blob call in fp32.
  Named mechanism: "quantisation flips a close two-blob score margin by eroding
  the true-ball component's area, not by moving either peak."
- Extended backend/ball_detector_parity_probe.py: VIDEO now reads
  BALL_PARITY_VIDEO env var (default unchanged, am_hard_utr.mp4) so other gold
  clips can run through the same probe without forking it. onnx_run_int8() now
  SKIPS any tag whose int8_heat_{tag}.bin already exists + logs per-frame progress
  — necessary because int8 inference is ~11-12s/frame on this x86 desktop (no
  int8 HW accel, expected/documented) and 178 frames (~35 min) exceeds one
  bounded shell call; this makes it resumable across several bounded calls
  instead of an unbounded background wait (my own memory file:
  background_wait_does_not_survive_ending_turn — do not repeat that mistake).
  TRAP CONFIRMED AGAIN: `timeout` killing mid-run with piped/buffered stdout
  (`| tail`) shows NOTHING even though the process made real progress — always
  redirect to a log file (`> file 2>&1`) so a killed call's partial output is
  still on disk, then inspect the file/directory state in a SEPARATE call.
- Clips available: tools/_goldset.py calibrated_map() = am_hard_utr (done),
  yt_rally2, yt_match40, gold_UHf0LeMU2pg, gold_sAjkpeRq4P4 (slowest, skip),
  gold_uR5q2cSM6AY, gold_L73ep7JHiJ4. Picked yt_rally2 (smallest file, 7.3MB)
  first, yt_match40 (35MB) second — both fast to extract.
- yt_rally2: FULL 178-frame pipeline done (extract 151/178 fp32-fire,
  build-decode, onnx-run fp32, decode-onnx, onnx-run-int8 all 178 via 4 resumed
  chunks, scratch dir .../scratchpad/ball_parity_yt_rally2). NEXT: decode-int8 +
  compare-int8, then inspect worst frame's heatmap same as 0147 if any >10px.
- yt_match40: NOT STARTED YET.
- Scratch dirs in use (NOT committed, per existing convention — only scripts +
  compact summary jsons are committed): scratchpad/ball_parity (am_hard_utr,
  pre-existing from lead's run), scratchpad/ball_parity_yt_rally2,
  scratchpad/inspect_0147.py (ad-hoc heatmap inspector, reusable for other
  clips' worst frame too — just change SP and tag).

## Nothing else in flight.

## TASK 4 — DONE (coordinator, 2026-09-02). Full int8 178-frame run: bar FAILS
(0147: 70.8px, 8 null mismatches). Full writeup already in
docs/evidence/ball-detector-parity-tracknet.md "Full 178-frame int8 run" section
(done by lead before this task started — not my work, inherited).

## TASK 3 — DONE. `mobile/ball_detector.js` decode bug (two-blob heatmaps,
argmax+window vs area*peak) found + fixed + verified 61/61 exact. Full writeup:
`docs/evidence/ball-detector-parity-tracknet.md`. Partial int8 sample (51/178)
also done in this task, superseded by the full run above.

## TASK 2 — DONE. `live_calls.js` doubles-alley bug fixed + verified 42/42.
`docs/evidence/doubles-alley-live-call-bug-fixed-and-exercised.md`.

## TASK 1 — DONE. `live_calls.js` vs `live.py` parity, degenerate-calibration
harness bug found + fixed, 7/7 exact. `docs/evidence/live-call-parity-verified-without-video.md`.

## LOG — newest first

- Task 5: yt_rally2 int8 stage complete (178/178), moving to decode-int8/compare-int8.
- Task 5: root-caused 0147 — quantisation erodes the winning blob's AREA (15px -> 2+1px
  fragments), not the peak value; flips a heatmap that was already a close 2-blob call.
- Task 5: made onnx_run_int8 resumable (skip-existing) since one call cannot fit 178
  frames at ~11.7s/frame; made VIDEO env-overridable for other clips.
