# pm — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

Write DURING the work. Rewrite TASK/STATE in place; append to LOG; compact past ~30 lines.
Durable learnings -> `.claude/agent-memory/pm/`. Findings -> `docs/evidence/`.

---

## TASK — what I was asked to do

2026-09-05. **Re-sequence v1** against three closures (court auto-detection CLOSED;
`seen_frac` speed gate unrescuable, no compliant real-footage speed reference; int8 ball
graph fails 3/6 gold clips, all mitigations spent, ship call turns on unmeasured A13 fps).

DELIVERABLE: `docs/evidence/v1-resequenced-after-court-closure.md` — (a) what v1 is,
(b) the cut line, (c) ranked founder-time queue, (d) dispatchable queue in order,
(e) hardware dead-ends, ending with THE single next dispatch.
NOT-THIS-RUN: code, docs/STATE.md, re-deriving measurements, git.

## STATE — where I got to

**ALL FIVE SECTIONS WRITTEN. Deliverable complete.** Remaining: agent-memory updates
(retire the stale "P0-0 needs a Mac" claim; add the re-sequencing memory), then report.

DECISIONS_PENDING appended with two new founder items (−1 buy an A13 iPhone; −0.5 match
scoring deferred out of v1, with two pre-registered accuracy floors).

## LOG — newest first

- **THE FINDING OF THIS RUN: the Mac blocker is DEAD and my own memory is stale.**
  `.github/workflows/coreml-export.yml` VERIFIED present by Read: workflow_dispatch,
  pinned macos-14, installs coremltools on real macOS, runs tools/export_coreml_p0.py,
  uploads ios/coreml_export/ with **14-day retention**. Push bar LIFTED 2026-09-04; the
  hard-coded `backend/yolo11m-pose.pt` defect is fixed. It is a button press nobody has
  pressed. => THE SINGLE NEXT DISPATCH. Caveat in the brief: push master FIRST
  (workflow_dispatch only reads the default branch's copy).
- Calls made: court auto-detect as a low-accuracy convenience = NO (yt_match40 is the
  standing proof a wrong court inverts numbers rather than degrading them). Speed gate =
  leave it (option 1) AND stop denominating anything in it => the speed-coverage lane is
  PARKED not cut, unparks only when a compliant real-footage speed reference exists.
  Score layer SPLIT: rally clips in, match scoring out.
- Ranked founder queue deliberately puts the CHEAP §1 line-click falsifier LAST: its best
  case changes no v1 decision, because the court cut rests on manual calibration being the
  reference standard, not on the detector being unfixable. Ranking by leverage, not cost.
- New #0 founder item invented this run: buy a used A13 iPhone. Three v1 go/no-go calls
  dead-end there and nowhere else, and a bad throughput number is a SCOPING input (a
  product cut), far cheaper at session 15 than session 45.
- Court cut frees ~15-20 sessions (40-50 vs 55-70 parity range, agent-memory
  mobile-parity-first). Stated as a pm estimate, not a measurement.
