"""Turn a subagent's raw JSONL transcript into readable markdown.

Subagent reasoning is NOT lost when a task notification comes back empty — the
full transcript is written to
  ~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl
The `tasks/<id>.output` file beside the session is only a mirror, and is often
empty; reading that and concluding the reasoning was gone is a mistake this
project already made once.

This renders one of those JSONL files as markdown: every assistant message, the
tool calls it made (name + a one-line argument summary), and tool results
truncated so a long file stays readable.

  backend/.venv/Scripts/python.exe tools/export_agent_transcript.py \
      --id aa678c1c69d506e58 --out docs/archive/agent-transcripts/mac-device-research.md
"""

import argparse
import glob
import json
import os

SUBAGENT_GLOB = os.path.expanduser(
    "~/.claude/projects/*/*/subagents/agent-{aid}.jsonl")


def _find(agent_id: str) -> str:
    """Locate a transcript under ~/.claude — OUTSIDE the project folder.

    This is the one thing here that reaches past the project boundary, and it is
    deliberate: Claude Code owns that directory and there is no in-project copy
    until this script makes one. It therefore only works from a context allowed to
    read ~/.claude — the main session, not an agent restricted to the project.
    Run it from the main session and commit the markdown it produces; agents then
    read the in-project copy under docs/archive/agent-transcripts/ and never need
    to leave the folder.
    """
    hits = glob.glob(SUBAGENT_GLOB.format(aid=agent_id))
    if not hits:
        raise SystemExit(
            f"no transcript found for agent id {agent_id!r}.\n"
            f"Looked in: {SUBAGENT_GLOB.format(aid=agent_id)}\n"
            "If that path is unreadable from here, this is the project-folder "
            "boundary doing its job — run this from the main session instead, or "
            "read an already-exported copy in docs/archive/agent-transcripts/."
        )
    return max(hits, key=os.path.getmtime)


def _blocks(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return c or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="agent id, e.g. aa678c1c69d506e58")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-result-chars", type=int, default=800)
    args = ap.parse_args()

    path = _find(args.id)
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    out = [f"# Subagent transcript — `{args.id}`", ""]
    out += [f"Source: `{path}`", f"Messages: {len(rows)}", ""]
    if rows:
        out += [f"Started: {rows[0].get('timestamp','?')}",
                f"Ended:   {rows[-1].get('timestamp','?')}", ""]
    out.append("---")
    out.append("")

    for r in rows:
        msg = r.get("message") or {}
        role = r.get("type")
        for b in _blocks(msg):
            t = b.get("type")
            if t == "text" and b.get("text", "").strip():
                out.append("### Assistant" if role == "assistant" else "### Prompt / result")
                out.append("")
                out.append(b["text"].rstrip())
                out.append("")
            elif t == "thinking" and b.get("thinking", "").strip():
                out.append("<details><summary>reasoning</summary>")
                out.append("")
                out.append(b["thinking"].rstrip())
                out.append("")
                out.append("</details>")
                out.append("")
            elif t == "tool_use":
                arg = json.dumps(b.get("input", {}), ensure_ascii=False)
                if len(arg) > 200:
                    arg = arg[:200] + "…"
                out.append(f"> **tool** `{b.get('name')}` — {arg}")
                out.append("")
            elif t == "tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                c = (c or "").strip()
                if c:
                    if len(c) > args.max_result_chars:
                        c = c[: args.max_result_chars] + f"\n… [{len(c)} chars total]"
                    out.append("```")
                    out.append(c)
                    out.append("```")
                    out.append("")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"wrote {args.out} ({len(rows)} messages, {os.path.getsize(args.out)/1000:.0f} KB)")


if __name__ == "__main__":
    main()
