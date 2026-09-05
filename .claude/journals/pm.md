# pm — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

Write DURING the work. Rewrite TASK/STATE in place; append to LOG; compact past ~30 lines.
Durable learnings -> `.claude/agent-memory/pm/`. Findings -> `docs/evidence/`.

---

## TASK — what I was asked to do

2026-09-05. **Re-sequence v1** against three closures of the last 48 h (do NOT re-derive):
1. Court auto-detection CLOSED for v1 (line detector ~6.4 px vs ~5.8 px human click
   neighbourhood; manual calibration IS the product answer). Frees the ~2,900-line
   courtfit/calibration mobile port.
2. `seen_frac >= 0.5` speed gate weak, not rescuable by re-tuning; replacement needs a
   real-footage absolute speed reference that does not exist (rule 11 bars HUD).
3. int8 ball graph fails parity 3 of 6 gold clips; all three mitigations spent; ship
   choice is int8-vs-fp32 and both turn on an unmeasured A13 fps.

DELIVERABLE: `docs/evidence/v1-resequenced-after-court-closure.md` — (a) what v1 is,
(b) the cut line, (c) ranked founder-time queue, (d) dispatchable queue in order,
(e) hardware dead-ends, ending with THE single next dispatch.
STOP-WHEN: those five written, or ~30 tool calls.
NOT-THIS-RUN: code, docs/STATE.md, re-deriving measurements, git.

## STATE — where I got to

Read: journal (stale 2026-08-29 task, this is fresh), DECISIONS_PENDING (full),
court-detection-path-after-the-line-ceiling.md (full), STATE.md lines 1-202.
Deliverable skeleton written. Now filling sections in priority order.

## LOG — newest first

- Founder ruling 2026-09-04 "I said yes to all" is on record in DECISIONS_PENDING:
  push bar LIFTED (Core ML export via workflow_dispatch now triggerable), int8 option 3
  authorised AND since measured out, five of seven carried items now await founder TIME
  not a decision.
- Prior run's headline still holds but has SHIFTED: v1 critical path was 100%
  founder-blocked; the push-bar lift means Core ML export is now dispatchable.
