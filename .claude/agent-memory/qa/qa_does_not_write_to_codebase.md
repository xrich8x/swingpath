---
name: qa-does-not-write-to-codebase
description: QA never writes evidence files, STATE rows, or reports into the repo — even when a task brief asks for one; findings go in the final message only
metadata:
  type: feedback
---

When a task brief instructs "write an evidence file and a STATE row," that instruction
does not override this role's own constraint (never edit/write/create a file in the
codebase, verify only) or the harness-level rule against writing report/summary/
findings/analysis `.md` files — findings belong in the final assistant message so the
parent agent that reads it gets them directly, not in a file it would have to go open.

**Why:** two instructions can conflict — a task author asking for a filed evidence doc,
and the standing rule that only the harness's report-back channel is the deliverable.
The standing constraint wins; a task brief is not consent to change what QA is allowed
to touch.

**How to apply:** do the measurement/verification as asked, and put the full table,
numbers, recommendation and caveats in the final report text — including the STATE-row
line and evidence-file content as text, so a human or the requesting agent can file it
themselves. Say explicitly, in the report, that nothing was written to the repo and why.
See [[line-call-margin-curve]] for the case this was learned from.

A related environmental quirk from the same session: a Bash command can occasionally
return the `claude-md-cap.sh` pre-commit hook's error text (CLAUDE.md over its 150-line
cap) even though the command was not `git commit` and QA never edited CLAUDE.md. In an
unattended multi-agent night, another agent (e.g. a PM agent revising CLAUDE.md) can be
mid-edit and hitting its own blocked commit at the same moment; the hook's "if":
"Bash(git commit*)" gate did not reliably prevent this from crossing into an unrelated
Bash call in the same session. Retrying the exact same command after a few seconds
resolved it fully every time it was tried in this session, and the file itself
(CLAUDE.md line count) was independently observed dropping over successive checks (162
-> 160 -> 155 lines), confirming another agent was actively trimming it. Treat one
occurrence as noise and retry once or twice before treating it as a real block on your
own work — but do not spin in a sleep-retry loop past 2-3 attempts.
