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

(DONE — reported to lead 2026-08-28.) Verified the doorman + journal system, all 10
items. See `.claude/agent-memory/qa/agent_cap_doorman_verified.md` for the durable
writeup. Lock/queue confirmed clean at end (queue empty, locks contain only this
agent's own real lock, restored after being safely parked during testing).

## STATE — where I got to

Task complete. Nothing in flight.

## LOG — newest first

- All 10 items tested by feeding synthetic hook payloads to agent_cap.py directly
  (never re-derived by reading). Cap denies exactly at live>=3. Fail-open confirmed on
  4 malformed-input shapes + no-git-repo + no-python-on-PATH. Parking verbatim confirmed
  (model+prompt survive). Hand-back confirmed bounded at 3 offers then dropped on the
  4th. No-double-fire confirmed (matching tool_input self-clears queue entry). TTL sweep
  confirmed (backdated lock removed same call). Wiring confirmed (all 4 events + PM gate
  Stop hook coexist, JSON valid). Journals confirmed (6/6 exist, tracked, correct paths;
  locks/queue gitignored). Restart checklist claims (30-min TTL, queue survives session)
  confirmed true in code. Found 3 real gaps (not fixed): TOCTOU race at PreToolUse
  (no reservation side-effect — demonstrated), safe_name() collision undercounting live
  agents (demonstrated), silent >8000-char hand-back truncation (storage itself is not
  truncated). Also flagged: declared session cwd was a decoy/stale subfolder, not repo
  root — worked from the real root throughout, doorman itself proven robust to this.
