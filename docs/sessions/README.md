# Session plans

One file per planned Claude Code session. Each is self-contained: goal, what
the user brings, the RESEARCHED technical approach with sources, a step plan
with measurement gates, and a kickoff prompt. Start a session by pasting its
kickoff prompt; finish one by filling in its Results section.

Recommended order (B/C/D are independent and can be reordered):

| Session | File | One-liner | Size |
|---|---|---|---|
| A | SESSION_A_lens_and_watchdog.md | Lens un-bending (plumb-line k1) + watchdog on a moving camera | ~1 session |
| B | SESSION_B_serve_stats.md | Serve placement (T/body/wide) + expanded match stats | ~1 session |
| C | SESSION_C_flow_polish.md | Refuse→overlay handoff, camera events in UI, player heatmap | ~1 session |
| D | SESSION_D_highlights.md | Per-rally clips + top-rallies reel (stream-copy strategy) | ~1 session |
| E | SESSION_E_ball_push.md | Ball detection on hard footage (multi-session arc) | multi |

Standing rules for every session (from CLAUDE.md + project memory):
- Measure after each step; show the user the numbers before continuing.
- Never test on training data; gold labels are TEST-only, never trained on.
- Never emit a court shape no real camera could see; 720p+ for new footage.
- Plain language for the user; exact copy-paste commands.
