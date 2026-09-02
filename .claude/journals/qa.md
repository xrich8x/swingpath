# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/qa/`, and
findings go in `docs/STATE.md` + `docs/evidence/`. Do not duplicate those here.

---

## TASK — what I was asked to do

DONE 2026-09-02. Verified whether the parked court-mask-sweep item
(`data/output/court_mask_sweep.json`, routed variants 12/20 vs baseline 11/20) is a
real pending gain or already shipped via surface routing (shipped 2026-08-21 per
f41a489, not 08-24 as the brief guessed). Verdict: DEAD, already shipped, nothing
pending. Evidence committed:
docs/evidence/court-mask-sweep-item-is-already-shipped.md (commit 333d38b).

## STATE — where I got to

RESUMED 2026-09-02 (predecessor killed by usage limit). Found: sweep file's routed
variants (routed_clay_chroma, routed_clay_clahe) BOTH accept the identical 12-clip
list on gold, matching gate_after.log's shipped accept list exactly, clip for clip.
Confirmed via git show f41a489 (2026-08-21, "Route the line mask by court surface")
that CLAHE variant (clay_line_mask in calibration.py) is what shipped; chroma was
rejected because it lost a DROP-set clip (sAjkpeRq4P4) not in the gold 20 — so on
gold both tie. My own independent gate run (not gate_after.log, not the predecessor's)
is running in background now: `eval/run_eval.py --gold --all --k 8`, log at
scratchpad/qa_gate_run.log, started as bg PID 1559 (first attempt timed out at 2 min
foreground limit, runtime is ~4 min per the script's own docstring). Need to check
back on it, then write verdict: PARKED ITEM IS DEAD, already shipped in f41a489,
12/20 is the current gate state, no pending gain to bank.

NOTE: git status shows uncommitted changes to .claude/hooks/agent_cap.py (+111/-3),
.gitignore, and new .claude/slots.py — NOT made by me, untouched, likely a concurrent
agent's in-progress work per memory note on cross-talk. Left alone.

ADDITIONAL CONFIRMATION via git history:
- court_mask_sweep.json's CURRENT content was written by commit 040df9d "Bank the P0
  sweep results and the re-run court mask sweep [no-state]" (2026-08-28, AFTER f41a489
  the ship commit of 2026-08-21). Commit message explicitly says the new arms
  (routed_clay_chroma/clahe) "changed SHAPE... NOT recorded as a gate result... that
  is qa's verdict to reach" -- i.e. the lead already knew this file post-dates the
  ship and deliberately left the verdict to me.
- f41a489's own commit message states the exact numbers: "routed 12/20 median 8.1
  range 1.7-13.9 no wrong PASS" and "CLAHE ships over the chroma variant because
  chroma loses sAjkpeRq4P4 (6 votes to 5)" -- that loss is on the 7-clip DROP set,
  not gold, so on the 20-clip gold set chroma and clahe tie (confirmed: identical
  accept lists AND identical median 8.101665063397835 in the sweep JSON).
- Prior (pre-routing) attempt ec2167e "clahe_only" global swap is the ~22.4px pair
  the system prompt warns about (am_beginner 22.4, am_classB 22.4) -- a DIFFERENT,
  already-dead global-swap idea, not to be confused with the routed version.
- calibration.py's court_line_mask() = clay_line_mask() [CLAHE ridge] if
  court_surface()=="clay" else line_ridge_mask() unchanged -- this is live in HEAD
  (cb37352), confirmed by reading the diff in f41a489 which is still present.

## LOG — newest first

- 2026-09-02: TASK COMPLETE. My own independent `eval/run_eval.py --gold --all --k 8`
  run (foreground, waited it out properly this time — first attempt lost by ending
  the turn on a background wait, which does not auto-wake me; second attempt used a
  foreground poll loop and it finished in ~20s of that call) gave 12/20 accepted, 0
  wrong, median 8.1px range 1.7-13.9 — third independent confirmation of the same
  number (mine, predecessor's gate_after.log, and f41a489's own commit message).
  Accept list is byte-identical to both sweep routed variants; only am_rally32short
  differs vs the sweep's `baseline` arm (which predates the router). Verdict: DEAD,
  already shipped 2026-08-21 (f41a489), re-banked (not re-proposed) by 040df9d on
  08-28. Evidence committed to master (not pushed): commit 333d38b.
- LESSON: ending a turn while "waiting" on a Bash run_in_background job does NOT
  keep you alive to receive its notification if the harness resets between turns —
  confirmed by the coordinator's correction this session. If a background job must
  be awaited, either stay in a foreground poll loop within the SAME tool call
  (generous timeout, e.g. a `for`/`until` loop with `sleep`), or accept the
  notification may only arrive if the session itself persists. Do not just say
  "waiting" and stop calling tools.
- (prior task, done 2026-08-28) doorman+journal verification — see memory file
  agent_cap_doorman_verified.md.
