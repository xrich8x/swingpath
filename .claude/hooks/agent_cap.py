"""agent_cap.py — project-wide agent doorman v2: concurrency cap + RUN BUDGET + parked queue.

WHY THIS EXISTS: the cap has to count agents the lead cannot see, and — new in v2 — it
has to limit total SPEND, not just crowding. A concurrency cap alone never protected the
quota: ten serial runs cost the same tokens as ten parallel ones. So there are now two
independent gates:

  GATE 1 — CONCURRENCY (unchanged idea): at most CAP agents alive at once, whole tree.
           A refused dispatch is PARKED verbatim and handed back when a slot frees.
  GATE 2 — BUDGET (new): at most BUDGET agent runs per rolling WINDOW (default 12 per
           5 h, matching plan-quota reset cadence). A budget refusal is NOT parked —
           no slot will "free" within the turn; the model is told to stop asking and
           the human decides what is worth one of the remaining runs.

v2 changes, in full:
  1. Run budget (above). Spend is recorded at SubagentStart in .claude/.agent-spend.log,
     one timestamp per line, compacted on read.
  2. Abandoned tasks are MOVED to .claude/.agent-queue/abandoned/ — never deleted.
     "Saved, not lost" now has no shredder at the bottom.
  3. Reservations are keyed by tool_use_id. SubagentStart consumes ITS OWN reservation
     when the id matches, falling back to the oldest. (Previously a slow starter could
     eat a stranger's reservation and over-free a slot.)
  4. The Stop-hook hand-back gate counts LOCKS ONLY. A stale 120 s reservation must not
     block a legitimate hand-back.
  5. Unknown / future events fail open EXPLICITLY instead of falling through into the
     PreToolUse gate.
  6. Observability: every deny, park, hand-back, drop and budget refusal appends one
     line to .claude/doorman.log. "Did the doorman ever save anything?" is now a
     question the file answers.
  7. MAX_PROMPT_ECHO cut to 2000 chars. The truncation notice instructs the model to
     READ THE PARKED FILE and dispatch its full tool_input.prompt VERBATIM — the task
     key then matches and the parked copy self-clears, so dedup still holds.

Unchanged and still load-bearing:
  - Locks written at SubagentStart, removed at SubagentStop, NEVER at PostToolUse
    (which returns immediately for background agents and would collapse the count).
  - Reservation written at PreToolUse approval time, so N dispatches in one message
    cannot all walk past a read-only check.
  - safe_name() = sanitised id + sha1 suffix of the RAW id (collision fix, qa-found).
  - TTL sweep of dead locks; SessionStart REPORTS held slots, never auto-clears.
  - Fail OPEN on any unexpected input. A broken guard must never wedge the session.

Reset by hand:  rm -rf .claude/.agent-locks .claude/.agent-queue .claude/.agent-reservations
Budget reset:   rm -f  .claude/.agent-spend.log
"""

import hashlib
import json
import os
import pathlib
import sys
import time

CAP = int(os.environ.get("TENNIS_AGENT_CAP", "3"))
TTL = int(os.environ.get("TENNIS_AGENT_TTL", "1800"))        # a lock older than this is dead
BUDGET = int(os.environ.get("TENNIS_AGENT_BUDGET", "12"))    # max agent RUNS per window
WINDOW = int(os.environ.get("TENNIS_BUDGET_WINDOW", "18000"))  # 5 h, plan-reset cadence
BRIEF_CONTRACT = os.environ.get("TENNIS_BRIEF_CONTRACT", "1") != "0"  # require DELIVERABLE/STOP-WHEN
MAX_HANDBACKS = 3          # bounds the Stop-hook loop if the model keeps ignoring a task
MAX_PROMPT_ECHO = 2000     # chars of prompt handed back inline; full text stays in the file

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCKS = ROOT / ".claude" / ".agent-locks"
QUEUE = ROOT / ".claude" / ".agent-queue"
ABANDONED = QUEUE / "abandoned"
RESV = ROOT / ".claude" / ".agent-reservations"
SPEND = ROOT / ".claude" / ".agent-spend.log"
LOG = ROOT / ".claude" / "doorman.log"
RESV_TTL = 120   # an approved dispatch that has not started in 2 min was abandoned


def allow():
    sys.exit(0)


def emit(obj):
    json.dump(obj, sys.stdout)
    sys.exit(0)


def log(kind, detail=""):
    """One line per doorman decision. Never allowed to break anything."""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with LOG.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"{ts} {kind} {detail}\n")
    except OSError:
        pass


def safe_name(s):
    """Sanitised id + a hash of the RAW id.

    Sanitising alone collides: `team:agent.7` and `team/agent 7` both flatten to
    `team_agent_7`, so two live agents would share one lock and the count would
    silently run one short. qa demonstrated this. The suffix makes distinct ids
    distinct regardless of what the sanitiser folds together.
    """
    raw = str(s)
    flat = "".join(c if c.isalnum() or c in "_-" else "_" for c in raw)[:100]
    return f"{flat}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8]}"


def _sweep(d, ttl):
    d.mkdir(parents=True, exist_ok=True)
    now = time.time()
    n = 0
    for f in d.iterdir():
        if not f.is_file():
            continue
        try:
            if now - f.stat().st_mtime > ttl:
                f.unlink()
                continue
        except OSError:
            continue
        n += 1
    return n


def live_locks():
    return _sweep(LOCKS, TTL)


def live_total():
    """Live agents = started locks + approved-but-not-yet-started reservations.

    Counting locks alone is a check-then-act race: PreToolUse had no side effect,
    so N dispatches emitted in one block all saw the same free slot and all passed.
    qa demonstrated it. A reservation written at approval time makes the check cost
    a slot immediately; SubagentStart then converts one reservation into a real lock.
    """
    return live_locks() + _sweep(RESV, RESV_TTL)


def spent():
    """Runs started inside the rolling window. Compacts the log while reading."""
    now = time.time()
    keep = []
    try:
        for line in SPEND.read_text(encoding="utf-8").splitlines():
            try:
                if now - float(line.strip()) <= WINDOW:
                    keep.append(line.strip())
            except ValueError:
                continue
        SPEND.write_text("\n".join(keep) + ("\n" if keep else ""),
                         encoding="utf-8", newline="\n")
    except OSError:
        return 0
    return len(keep)


def record_spend():
    try:
        with SPEND.open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"{time.time()}\n")
    except OSError:
        pass


def task_key(tool_input):
    canon = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:16]


def describe(tool_input):
    who = tool_input.get("subagent_type") or "general-purpose"
    what = tool_input.get("description") or (tool_input.get("prompt") or "")[:60]
    return f"{who} — {what}"


def main():
    try:
        ev = json.loads(sys.stdin.read())
    except Exception:
        allow()

    event = ev.get("hook_event_name", "")
    agent = ev.get("agent_id", "")
    QUEUE.mkdir(parents=True, exist_ok=True)
    ABANDONED.mkdir(parents=True, exist_ok=True)

    if event == "SubagentStart":
        if agent:
            LOCKS.mkdir(parents=True, exist_ok=True)
            (LOCKS / safe_name(agent)).write_text(str(time.time()), encoding="utf-8")
            record_spend()
            # Consume THIS dispatch's reservation when identifiable, else the oldest.
            RESV.mkdir(parents=True, exist_ok=True)
            tuid = ev.get("tool_use_id")
            mine = (RESV / safe_name(tuid)) if tuid else None
            if mine is not None and mine.exists():
                mine.unlink()
            else:
                held = sorted(RESV.glob("*"), key=lambda f: f.stat().st_mtime)
                if held:
                    held[0].unlink()
        allow()

    if event == "SubagentStop":
        if agent:
            try:
                (LOCKS / safe_name(agent)).unlink()
            except OSError:
                pass
        allow()

    if event == "SessionStart":
        # A usage limit kills an agent outright, so it never fires SubagentStop and its
        # slot stays held until the TTL sweep. We do NOT clear automatically: the cap is
        # project-wide, and another window's agents may genuinely be running. Report it.
        live = live_total()
        used = spent()
        if live or used:
            held = sorted(f.name for f in LOCKS.iterdir() if f.is_file()) if LOCKS.exists() else []
            parked = len(list(QUEUE.glob("*.json")))
            msg = (
                "%d of %d agent slots held from before this session%s. "
                "Budget: %d of %d runs spent in the current %d h window. "
                "If agents really are running elsewhere, leave them. If not, locks "
                "clear after %d min, or now with: rm -rf .claude/.agent-locks\nHeld: %s"
                % (live, CAP,
                   (", and %d task(s) parked" % parked) if parked else "",
                   used, BUDGET, WINDOW // 3600, TTL // 60,
                   ", ".join(held) or "(none)")
            )
            emit({
                "systemMessage": msg,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "Concurrency and budget at session start.\n" + msg +
                        "\nReconcile against ListAgents before dispatching; see the "
                        "RESTART CHECKLIST in .claude/journals/lead.md."
                    ),
                },
            })
        allow()

    if event == "Stop":
        # Hand a parked task back only if a REAL slot is free (locks only — a stale
        # reservation must not block this) AND the budget allows one more run.
        parked = sorted(QUEUE.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not parked:
            allow()
        if live_locks() >= CAP:
            allow()                      # no slot; let the turn end, tasks stay parked
        if spent() >= BUDGET:
            log("HOLD-BUDGET", f"{len(parked)} task(s) stay parked; budget spent")
            emit({"systemMessage": (
                f"{len(parked)} task(s) remain parked, but the agent-run budget is spent "
                f"({BUDGET} of {BUDGET} in the current window). They will be offered "
                f"again once the window rolls over. Nothing was lost."
            )})
        f = parked[0]
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            f.unlink(missing_ok=True)
            allow()

        rec["handbacks"] = rec.get("handbacks", 0) + 1
        label = describe(rec.get("tool_input", {}))

        if rec["handbacks"] > MAX_HANDBACKS:
            dest = ABANDONED / f.name
            try:
                f.replace(dest)          # MOVED, not deleted — "saved, not lost" holds
            except OSError:
                pass
            log("ABANDON", label)
            emit({
                "systemMessage": (
                    f"Parked agent task set aside after {MAX_HANDBACKS} ignored "
                    f"hand-backs: {label}. It is preserved verbatim at "
                    f"{dest.relative_to(ROOT).as_posix()} — re-ask for it if you still want it."
                )
            })

        f.write_text(json.dumps(rec), encoding="utf-8")
        ti = rec.get("tool_input", {})
        full = ti.get("prompt") or ""
        prompt = full[:MAX_PROMPT_ECHO]
        if len(full) > MAX_PROMPT_ECHO:
            where = f.relative_to(ROOT).as_posix()
            prompt += (
                "\n\n[...TRUNCATED at %d of %d chars. Before dispatching, READ the "
                "parked file %s and use its tool_input.prompt VERBATIM as the prompt — "
                "the exact text is what clears this task from the queue.]"
                % (MAX_PROMPT_ECHO, len(full), where)
            )
        remaining = len(parked) - 1
        log("HANDBACK", f"#{rec['handbacks']} {label}")

        payload = (
            f"A slot has freed ({live_locks()} of {CAP} agents live, "
            f"{spent()} of {BUDGET} runs spent) and a task is parked.\n\n"
            f"DISPATCH IT NOW with the Agent tool, using exactly these arguments:\n"
            f"  subagent_type: {ti.get('subagent_type', 'general-purpose')}\n"
            f"  description:   {ti.get('description', '')}\n"
            f"  model:         {ti.get('model', '(inherit)')}\n"
            f"  prompt: |\n{prompt}\n\n"
            f"Do not summarise or re-plan it — it was written earlier in this session and "
            f"refused only because the concurrency cap was full. "
            + (f"{remaining} further task(s) remain parked behind it." if remaining else "")
        )
        emit({
            "systemMessage": f"Re-dispatching parked agent task: {label}",
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "continue": True,
                "reason": f"A parked agent task is waiting and a slot is free: {label}",
                "additionalContext": payload,
            },
        })

    if event != "PreToolUse":
        allow()      # unknown or future events must never fall into the gate below

    # ---- The PreToolUse gate on Agent|Task -----------------------------------------
    ti = ev.get("tool_input", {}) or {}
    key = QUEUE / f"{task_key(ti)}.json"

    # GATE 0 — the brief contract. "One task per brief" was a prose rule the lead had
    # to remember; now it is checked. An A-to-Z brief that dies mid-run delivers
    # NOTHING for full price — the most expensive failure this system has. A malformed
    # brief is NOT parked and NOT budgeted: the fix is a rewrite, which is free.
    prompt_text = ti.get("prompt")
    if BRIEF_CONTRACT and isinstance(prompt_text, str) and prompt_text.strip():
        n_deliv = prompt_text.count("DELIVERABLE:")
        n_stop = prompt_text.count("STOP-WHEN:")
        if n_deliv != 1 or n_stop < 1:
            log("DENY-BRIEF", f"deliv={n_deliv} stop={n_stop} {describe(ti)}")
            emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"BRIEF REJECTED — not parked, no run spent. Fix the brief and "
                        f"re-dispatch; a rewrite is free, a dead half-run is not.\n\n"
                        f"Every brief must contain exactly ONE 'DELIVERABLE:' line and at "
                        f"least one 'STOP-WHEN:' line. This brief has {n_deliv} and "
                        f"{n_stop}.\n\n"
                        f"  DELIVERABLE: the ONE artifact this run must produce — a file, "
                        f"a verdict, an answer. Two deliverables is two runs.\n"
                        f"  STOP-WHEN:   the condition that ends the run even with "
                        f"questions still open.\n\n"
                        f"An agent killed by a usage limit delivers nothing it has not "
                        f"already written down. Scope the brief to what ONE run finishes "
                        f"comfortably: ask for A and B now, queue C onward on paper — the "
                        f"answer to A usually rewrites the rest of the list anyway."
                    ),
                }
            })

    # GATE 2 — budget. Checked FIRST: a task that cannot run this window must not be
    # parked (parking promises a hand-back "when a slot frees", which would be a lie).
    used = spent()
    if used >= BUDGET:
        log("DENY-BUDGET", describe(ti))
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"AGENT-RUN BUDGET SPENT: {used} of {BUDGET} runs used in the current "
                    f"{WINDOW // 3600}-hour window. This is the token-quota guard, not the "
                    f"concurrency cap — waiting for a slot will not help.\n\n"
                    f"This task was NOT parked. Do NOT retry it and do NOT try to do the "
                    f"agent's job inline as a workaround. Finish what you can without "
                    f"agents, then STOP and tell the human plainly: which agent tasks are "
                    f"waiting, what each would cost (~38k tokens minimum), and let THEM "
                    f"choose what is worth doing when the window rolls over.\n\n"
                    f"The human can raise the budget for a heavy day with "
                    f"TENNIS_AGENT_BUDGET, or reset it: rm -f .claude/.agent-spend.log"
                ),
            }
        })

    # GATE 1 — concurrency.
    live = live_total()
    if live < CAP:
        key.unlink(missing_ok=True)      # this dispatch satisfies any parked copy
        RESV.mkdir(parents=True, exist_ok=True)
        tuid = ev.get("tool_use_id") or str(time.time())
        (RESV / safe_name(tuid)).write_text(str(time.time()), encoding="utf-8")
        allow()

    if not key.exists():
        key.write_text(json.dumps({
            "tool_input": ti,
            "queued_at": time.time(),
            "handbacks": 0,
        }), encoding="utf-8")
        log("PARK", describe(ti))
    log("DENY-CAP", f"live={live} {describe(ti)}")

    depth = len(list(QUEUE.glob("*.json")))
    emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{live} agents are already live across this project; the cap is {CAP}.\n\n"
                f"THIS TASK IS SAVED, NOT LOST. It has been parked verbatim "
                f"({depth} task(s) now parked) and will be handed back to you automatically "
                f"as soon as a slot frees. Do NOT retry it now, and do NOT re-plan or shrink "
                f"it — a retry loop burns the quota this cap exists to protect.\n\n"
                f"Carry on with work that does not need an agent, or end the turn; the parked "
                f"task will be re-offered before the turn is allowed to finish.\n\n"
                f"This is a QUOTA-protecting cap, not machine load: every agent anywhere in "
                f"the tree spends the same shared account.\n\n"
                f"If you believe no agent is actually running, locks leaked from a killed "
                f"session: rm -rf .claude/.agent-locks .claude/.agent-queue"
            ),
        }
    })


if __name__ == "__main__":
    main()
