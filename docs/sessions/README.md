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
| D | SESSION_D_highlights.md | Per-rally clips + top-rallies reel. **SHIPPED 2026-08-08.** | done |
| E | SESSION_E_ball_push.md | The ball stack: tracking → trajectory → arc → speed + spin (multi-session arc, E1-E4). **Read its frame-rate finding first — it constrains the footage the user records.** | multi |
| F | SESSION_F_false_fire.md | Ball false-fire, without giving back the recall E6 bought. **Steps 1-2 are diagnosis and gate everything else — the static-lock gate never fires on the worst clip, so the confusers are not fixtures.** | ~1 session |
| I | SESSION_I_localised_negatives.md | Localised hard negatives. **RUN 2026-08-09: product gate FAILED** (solid ghosts 14→15) but the detector improved on 6 of 6 clips — unattributable, because the trainer had no seed. Also found the universal ghost core is **5 frames**, all with `run_len=1`. | done |
| G | SESSION_G_pose_proximity.md | Pose-proximity hard negatives — the only lever left after F proved nothing downstream removes a **solid** ghost. **Step 1 scores the criterion against the 71 human-classified false locks before any GPU time; if it fails its gate, stop.** | ~1 session |
| J | SESSION_J_farcourt_labelling.md | Make far-court labelling usable. **RUN 2026-08-10: the HUD diagnosis was RETRACTED** — only 5 of 36 clicks were inside a graphic; the real blocker was that both anchors bracketing a gap were often false locks. Shipped the mask, the converter and the anchor control, then found the anchor control measures **agreement with the tracker, not correctness**. | done |
| K | *(no brief — ran from SCOREBOARD)* | +57% training data. Detector recall **74.8 → 80.4%** pooled (4.1σ), best ever on the legacy six. **Product gate FAILED**: solid ghosts 9 → 13 at flat chain recall. First time a detector RECALL gain was tested at the product; it did not arrive either. | done |
| L | SESSION_L_farcourt_labels.md | **NEXT UP.** Far-court human labels — the one input never exercised, and the first ball idea with a **chain-level mechanism**: denser far-court detections → longer runs → survive `suppress_false_locks`' min-segment test, which was measured to destroy **~7 real balls per ghost**. 173 labels are already collected and unconverted. **Carries a pre-registered STOPPING RULE**: if the mechanism gate fails, ball work is closed. | ~1 session |

Standing rules for every session (from CLAUDE.md + project memory):
- Measure after each step; show the user the numbers before continuing.
- Never test on training data; gold labels are TEST-only, never trained on.
- Never emit a court shape no real camera could see; 720p+ for new footage.
- Plain language for the user; exact copy-paste commands.
