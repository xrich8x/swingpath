#!/usr/bin/env bash
# agent-cap.sh — thin wrapper. All logic lives in agent_cap.py; see its docstring.
#
# The wrapper exists to pick an interpreter and to FAIL OPEN if it cannot find one, the
# same discipline as the sibling guards: a broken guard must never wedge the session.
#
# v2 change: failing open is no longer SILENT. A dead doorman used to be
# indistinguishable from a working one. Now every fail-open appends one line to
# .claude/doorman.log, and if the event is a SessionStart the human is told in-session.
# Note `python`/`python3` on this machine are Microsoft Store shims that print an ad and
# exit non-zero, so the probe runs each candidate before trusting it.

set -uo pipefail

payload=$(cat 2>/dev/null || true)

note_and_allow() {
  # $1 = reason. Log if we can find a root; tell the human if this is SessionStart.
  if [ -n "${repo_root:-}" ]; then
    printf '%s DOORMAN-INACTIVE %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" \
      >> "$repo_root/.claude/doorman.log" 2>/dev/null || true
  fi
  case "$payload" in
    *SessionStart*)
      printf '{"systemMessage":"DOORMAN INACTIVE (%s): the agent cap and budget are NOT being enforced this session."}' "$1"
      ;;
  esac
  exit 0
}

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || note_and_allow "not a git repo"
[ -f "$repo_root/.claude/hooks/agent_cap.py" ] || note_and_allow "agent_cap.py missing"

PY=""
for c in py python3 python; do
  command -v "$c" >/dev/null 2>&1 || continue
  "$c" -c "pass" >/dev/null 2>&1 || continue
  PY="$c"; break
done
[ -n "$PY" ] || note_and_allow "no working python interpreter"

# stdin was already consumed into $payload (needed for the SessionStart check above),
# so feed it back to python explicitly.
printf '%s' "$payload" | "$PY" "$repo_root/.claude/hooks/agent_cap.py"
exit $?
