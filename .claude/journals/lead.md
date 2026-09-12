# Working journal — live state

**If a session or an agent died, read this file first.** It is the durable record of what
is in flight, what is blocked, and what was decided. It is written DURING work, not after,
so a rate-limit kill or a crash leaves it usable.

**Rules for whoever writes here (lead or teammate):**
- Update it as you go, not at the end. A journal written at the end does not survive a kill.
- **NOW** and **BLOCKED** are rewritten in place — they describe the present, not history.
- **LOG** is newest-first and gets **compacted** when it passes ~40 lines: fold resolved
  entries into one line each, delete anything superseded. This file must stay short enough
  to re-read cheaply, or it stops getting read.
- Numbers here are pointers. The authority is `docs/STATE.md` + `docs/evidence/`.
- Never put a result here that belongs in STATE. This is working state, not findings.

**Last updated:** 2026-09-10, on picking up the innovation-gate brief.

---

## RESTART CHECKLIST — run this before anything else after a death

A usage limit kills a subagent outright; the session itself resumes
(`autoContinueAtUsageLimit`). The doorman does not know the agent died, because a killed
agent never fires `SubagentStop`. So the corpse keeps holding its slot, and the first
thing you try — re-dispatching the work that just died — is the thing it blocks.

1. **Read the journals.** `.claude/journals/lead.md` first, then the teammate's own.
2. **Reconcile live agents against held slots:**
   ```
   ls .claude/.agent-locks
   ```
   Compare with `ListAgents`. A lock with no matching live agent is a corpse — it frees
   itself after 30 min, or clear it now: `rm .claude/.agent-locks/<id>`.
3. **Check for parked work:** `ls .claude/.agent-queue` — refused dispatches live here and
   survive a death. The directory is gitignored, so nothing else will surface them.
4. **Then resume**, preferring the killed agent's uncommitted files over a restart.

## RUN STATE — the one thing that decides whether to wait for the founder

`NOW` opens with a `RUN-STATE:` line. It has exactly three values. **Read it before anything
else: it is the whole answer to "should I be working right now?"**

| RUN-STATE | Means | What you do |
| --- | --- | --- |
| `RUNNING` | Normal. The default. | Work. Do not ask permission to continue. |
| `KILLED` | A usage limit, crash or closed terminal ended the last session mid-work. | **Resume immediately, without asking.** Then set `RUNNING`. A death is not a pause. |
| `PAUSED-BY-FOUNDER` | The founder said stop. | Stop everything and end the turn. Only the founder's words clear it. |

**A founder pause stops the ENTIRE SESSION — founder ruling 2026-09-05.** Not just agent
dispatch. When the founder says "pause", "im sleeping", "stop for now" or anything like it:

- dispatch no agents;
- **start no background job** — however cheap, however well it seems to fit an unattended
  window. This is the exact mistake of 2026-09-04: "pause im sleeping" was read as "no
  agents", and a 1-3 hour parity run was launched *because* nobody was waiting;
- run no experiment, no training, no analysis, no commit;
- log the pause (below), set `RUN-STATE: PAUSED-BY-FOUNDER`, and **END THE TURN**.

A job that was ALREADY running is left alone — killing it throws away work — but name it in
the pause line and start nothing new.

**Logging a pause is mandatory, in both places:**

1. `NOW`'s state line becomes:
   `RUN-STATE: PAUSED-BY-FOUNDER — <YYYY-MM-DD HH:MM> — "<founder's exact words>" — still running: <job, or nothing>`
2. `## LOG`, newest-first, one line at pause and one at resume:
   `- **<date>** — PAUSED by founder ("<words>"). Left running: <...>.`
   `- **<date>** — RESUMED by founder ("<words>").`

**Only the founder sets `PAUSED-BY-FOUNDER`, and clearing it is not optional** — the moment
they say continue, that line goes back to `RUNNING` in the same turn. A stale PAUSED line is
indistinguishable from a live pause and will stop the next session too; that happened on
2026-09-04 and cost a day. **A kill never sets it** — a kill is `KILLED`, and `KILLED`
resumes on its own.

## REPORTING RULE — founder instruction 2026-09-02

**Do not surface founder-blocked items unless the founder asks for them.** They go in
`docs/DECISIONS_PENDING.md` silently and stay there. Ending a status with "waiting on
you..." is the interrupting this rule exists to stop — the founder asked to be left to
work, and asks for the list when they want it.

Report what was DONE. Keep the queue to yourself until requested.

## RESUME AFTER A KILL — usually automatic; one paste only if the terminal is gone

**This is `RUN-STATE: KILLED`, never a pause. Resume without asking.**

`autoContinueAtUsageLimit: true` is set in `.claude/settings.json`, so a usage limit hit
while the session process is still alive resumes it by itself when the quota rolls over —
no human message needed. Only a CLOSED terminal, a crash or a reboot needs a restart, and
nothing automates that: not this journal, not a scheduled job, not a cloud agent (which
cannot see this local repo). In that case, and only that case, resumption costs one paste:

    /loop Work docs/STATE.md's Open table continuously and autonomously, and ALWAYS
    use the teammate agents for feature work — 3-live-agent project cap, one direct
    child at a time. NEVER stop to ask; append anything needing a founder decision to
    docs/DECISIONS_PENDING.md and keep going. Pre-register a bar before running
    anything, one variable per A/B, a failed bar stays failed, never score a model
    against its own output, inspect the rejects not what a filter kept. Commit to
    master, DO NOT PUSH. Keep this journal's NOW current.

Then, before doing anything else, read in this order:
  1. `docs/STATE.md` — Open table. The live record. Authority for every number.
  2. `docs/DECISIONS_PENDING.md` — what is waiting on the founder, and what was done
     instead so the blocker was not also idle time.
  3. "What has not worked" in STATE — **13 hypotheses died there this week.** Do not
     re-derive them. Each row names the number that killed it.

## NOW — what is running

RUN-STATE: RUNNING — founder brief 2026-09-12 handed a new seven-item queue. The innovation-gate
task and the four-step project audit are both CLOSED; their records live in STATE + evidence, and
the compacted lines are in LOG.

**The iOS/sideloading line stays bound** (2026-09-10 pause): do not re-open Sideloadly, Apple ID,
or the harness install path. `ios/` builds green in CI; only the sideload is blocked.

**THE TASK: v1 is an ENGINE — 3D court mapping + drag+Magnus 3D trajectory + bounce triangulation.**
Outputs are exactly three: where the ball bounced, in or out, and a REFUSAL. `docs/SPEC.md` is the
LOCKED bar sheet. **Five of the seven queue items are MEASUREMENTS. Do not reorder a build above a
measurement without writing down why.**

### THE QUEUE — founder order, 2026-09-12

| # | Item | Kind | Owner | Blocked on |
|---|---|---|---|---|
| P1 | Monocular 3D ceiling on synthetic truth | MEASURE | backend-dev | nothing — **IN FLIGHT** |
| P2 | Occlusion census: the refusal floor | MEASURE | qa builds sheet, founder eyes it | sheet must exist BEFORE the founder is asked |
| P3 | Does any footage meet the v1 capture floor? | MEASURE | qa | nothing |
| P4 | **FOUR** contradictions inside a locked SPEC | DECIDE | founder | **WRITTEN AND DELIVERED 2026-09-12** -> `docs/DECISIONS_PENDING.md`. Awaiting the ruling; P7 cannot start without (i)/(ii)/(iv) |
| P5 | The capture protocol (artefact + target sheet) | BUILD artefact | pm drafts | P3, P4(iii) |
| P6 | INSTANT on paper, v1-only path | MEASURE | researcher | P4(i) |
| P7 | The live-path skeleton in Swift | BUILD | backend-dev/frontend-dev | P1 pass, P4, P6 |

**P1 IS IN FLIGHT — backend-dev, dispatched 2026-09-12.** Bars A-G pre-registered in the brief
below and NOT movable. The 2D ground-projection estimator already in `tools/synth_truth.py` is the
CONTROL ARM, so the answer says what 3D buys over what ships today.

**P1's pre-registered bars, recorded here so a kill cannot lose them:**
- **A PASS:** >=90% of flights place the bounce within 10 cm at pixel_noise=2.0 px, dropout=0.30,
  60 fps, 3.0 m mount, hfov exact.
- **B TIMING:** >=90% within +/-1 frame, >=99% within +/-2 frames.
- **C KILL:** if with PERFECT detections (noise 0, dropout 0) the 10 cm rate is below 50% at EVERY
  mount height, monocular 3D cannot reach SPEC §3 and the spec is renegotiated before more code.
- **D HEIGHT AXIS:** 10 cm rate at 1.0 / 1.5 / 2.5 / 4.0 / 8.0 m. CLAUDE.md's founding premise
  ("works regardless of mount height") HOLDS only if 1.5 m lands within 10 points of 8.0 m.
- **E NOISE AXIS (descriptive):** pixel noise 0 / 1 / 2 / 4 px. Most actionable output of the run:
  the detector precision the 10 cm bar demands.
- **F SELF-GRADING CONTROL, REQUIRED:** simulator and fitter share a physics model, so one arm runs
  the simulator's `cd` / `cl_max` offset +/-20% from the fitter's, reported separately. Without F,
  bar A is a ceiling under a perfectly-specified model and will be quoted as an accuracy.
- **G OUT OF SCOPE, report UNTESTED:** SPEC §5's depth-from-known-ball-size (6.7 cm). The rig emits
  (u,v) only, no apparent radius — so §5's self-declared weakest channel is NOT exercised here.

**P4 IS WRITTEN — four items, not three, and item (iv) changes a build.** Full text in
`docs/DECISIONS_PENDING.md`, 2026-09-12. The three the founder named are (i) §8-vs-§4 latency,
(ii) §1's drift RECOVERY having no mechanism under a manual four-tap, (iii) §10's shell blocker
being void. **The fourth, found while verifying the first: `live.py`'s bounce detector is NOT
SPEC §4's method.** Its own docstring calls it "a local minimum of the ball's court-plane speed
... a court-speed heuristic" with **no height channel at all**, while §4 mandates vertical-velocity
sign reversal. `v2/mobile/live_calls.js` faithfully ports that same heuristic — so P7's
"the JS port proves this is cheap" evidence is evidence about a detector v1 forbids. P7 must port
live.py's STRUCTURE and replace the bounce STAGE with §4 on P1's 3D fit.

**TWO NUMBERS I CORRECTED IN MY OWN DRAFT — do not re-derive them the wrong way:**
- **Shell calibrations: 2 usable at a spec-relevant height, not 4.** Ten exist (`7c8b8af`), four
  stamp `_audit: PASS` — but `mpc_tuesday_p01`/`p07` are **excluded as ground truth by their own
  commit** (two independent labels disagree by 25.4 px@640, past the 20 px wrong-court line).
  `_audit: PASS` and "valid truth" are DIFFERENT AXES. The usable set is 8 of 10; at >=2.5 m it is
  `flexi_franz_p01`/`p07` only, which are two labels of **one venue**.
- **Dropout latency tail: P(>6 frames) = 1.1%, not the 6% I first wrote.** Negative binomial,
  p=0.7, two detections needed. E = 2.9 frames = 48 ms; P(>4 frames) = 8.4%.

**The one design call the lead made in the brief, recorded because it shapes the answer:** the
PRIMARY arm fits `p0` FREE with `physical_bounds=True`. A striker-pinned launch was worth -3% in
`docs/evidence/arc-fit-observability.md`, but it is pinned by POSE, and SPEC §9 tossed all pose from
v1 — so v1 does not have that information. The anchored variant may be reported as a descriptive
secondary, labelled as needing information v1 does not have.

## THE OLD RESTART QUEUE — SUPERSEDED 2026-09-12 by NOW's P1-P7

The iOS-harness queue (A/B/C), the court maintenance lanes (D/E/G) and the calibration-provenance
queue are all superseded. Court AUTO-detection is v2 (`docs/court/CLOSED.md` + CLAUDE.md); the
sideload line is founder-paused; the provenance/re-placement asks are explicitly **not** to be
picked up (founder queue 2026-09-12, "do not do these next", item 2). Full text is in git history
at `79425f3`.

**Three things from it are still live and are carried here rather than re-derived:**
- **Core ML export cost lever, untested:** the `.mlpackage` export runs on `macos-14` at **10x
  billing**, and `docs/evidence/p0-0-coreml-export.md:5` says only the *Xcode measurement* needs a
  Mac. **`ubuntu-latest` was never tried.** Worth one attempt before any future export run.
- **Setup-time camera motion, and it has a measured reason:** calibrate LAST (four-tap on a frame
  captured after the phone is placed and untouched) plus an **IMU stillness gate** (CoreMotion,
  on-device, zero inference) as a refusal. The measured reason it must be the IMU: motionless
  tripods disagree with themselves about the court, so camera movement cannot be detected by
  watching the court fit wobble. **This is direct input to P4(ii)** — the drift-recovery ruling.
- **FOUNDER RULING 2026-09-09, standing:** pushes are ALLOWED but **only on the founder's explicit
  call, per push.** Never automatic at session end; a prior approval does not carry forward.


## PARKED — work that was started and stopped

- ~~**Court mask sweep: a possible gate pass, unclaimed.**~~ **CLOSED 2026-09-02 by qa —
  it was already shipped.** `f41a489` (2026-08-21) is the ship commit for surface routing
  and `calibration.court_line_mask` is unchanged since (qa read the live function, not the
  commit message). `court_mask_sweep.json`'s content was rewritten a week LATER by
  `040df9d` — a re-measurement of the shipped router banked for the record, not a new
  candidate. Both routed variants are bit-identical to shipped on gold; the only clip that
  ever differs is `am_rally32short`, and only because `baseline` predates the router.
  Gate re-run independently: 12/20, max 13.9 px, zero over 20. Nothing replaces it — the
  next court-mask idea has to be a genuinely new candidate.
- **Corner contact sheets for the 25 `*_pts.json` files.** BLOCKED item 3 asks the founder to
  audit calibrations by rendering corners. Rendering is the lead's job, not theirs: build a
  sheet per file with the four clicked corners drawn on a real frame, so the founder's task
  drops from "audit" to "look and say which are wrong." No tool does this today —
  `validate_new_clip.py --audit` is residual-only, which is precisely what T23 defeated.

## BLOCKED — needs the founder, nothing proceeds without it

Ranked by leverage (pm, 2026-08-29). **The v1 critical path is 100% founder-blocked** — the
two gates that decide whether an iPhone can run this (P0-0 Core ML export, P0-2 pose
affordability) both wait here, and nothing dispatchable is on that path.

1. **Re-click `yt_match40` corners** (~5 min) — unblocks P0-2, the top v1 runtime risk.
   Calibration confirmed wrong (T23). `near_br_doubles` runs off-frame and needs
   extrapolating. Sheet ready at `data/output/corner_audit/yt_match40_corners.png`.
2. **Look at `data/output/corner_audit/`** (~10 min) — 27 sheets BUILT and committed
   (`cc213d3`). Lead cannot settle two of them: on `am_hard_utr` and `sAjkpeRq4P4` the far
   corners land near the NET rather than the far baseline, and a still frame does not
   separate those at a low mount. The camera-height fit says both are fine (1.74 m, 3.33 m)
   but that is corroboration, not proof.
3. **A Mac + a physical A13.** The Core ML export itself fails on Windows — `coremltools`'
   wheel lacks the native library that writes an `mlprogram`'s weights.
4. **The TrackNet idea — or one sentence: detector-side or chain-side?** If detector-side,
   rule 6 leaves chain work open and speed coverage unparks to the front of the queue.
5. **~3-6 h point-boundary labels. DO NOT START** until researcher's protocol lands, or the
   hours get spent twice. Hardcourt + Clay only.
6. **Re-label 8 court gold frames** (~1 min). Rule 9 — recorded, never quietly fixed, so
   permanently the founder's. Lowest urgency; court is not v1-blocking.
7. ~~**Is the score layer settled in scope?**~~ **ANSWERED - not a founder question.** CLAUDE.md rule 12
   (2026-08-27) rules it IN, and that is the later ruling. Do not re-ask; the real blocker is ground truth.
8. **Is a Mac weeks or months away?** A sequencing input, not a nudge — pm would build a
   different plan for a months-long gap.

## DECIDED — binds everyone, do not reopen

- **iOS/iPadOS only, A13+**, Core ML/ANE the only inference target. **100% on-device
  forever** — a proposed network dependency is a scope violation.
- **Three live agents PROJECT-WIDE**, counting the whole tree — a teammate calling a
  teammate spends the same quota. Teammates MAY call each other. A Pro-plan QUOTA cap, not
  machine load; a one-word agent still costs ~38k. Enforced by
  `.claude/hooks/agent-cap.sh`; a refused call is PARKED verbatim, not lost, and handed
  back when a slot frees — never retry it and never shrink it to fit.
- **The rally/score layer is in scope but has no ground truth.** A compliant source is a
  prerequisite line item.
- Court auto-detection and the activity gate/trimmer are **not to be run unattended** —
  the first fires a stopping rule that closes a lane, the second needs a human to look at
  what it discarded.

- **v1 ships TRACKNET** (founder, 2026-08-29). The chain verdict was SPLIT, so this is a
  product call: fewer phantom balls beats more speed coverage, and it is the only detector
  with a Core ML path. BallNet v21 is the upgrade path, not a rejected option.
- **Line calling is PARKED** (founder, 2026-08-29). The 0.15/0.20 m refusal band is NOT
  chosen. `live.py` keeps its 0.05 m. qa's margin curve is filed in STATE, unactioned.
- **P0-3's substituted identity test is ACCEPTED** (founder, 2026-08-29).
- **A founder pause stops the WHOLE SESSION** (founder, 2026-09-05) — agents, background
  jobs, experiments, commits, everything; not just agent dispatch. It is written to `NOW`'s
  `RUN-STATE` line and to `LOG`, and only the founder clears it. **A kill is not a pause:**
  a killed session resumes itself and asks nobody. See "RUN STATE" at the top of this file.
- **P0-3 is no longer provisional** — 25 context tiles reviewed 2026-08-29. Both strict
  passes are real far-end figures; sampled rejections are real far players thrown out for
  anchor distance. The crop finds the far player.

## LOG — newest first

- **2026-09-12** — New founder queue (P1-P7) replaces the audit and innovation-gate tasks. **P1
  dispatched to backend-dev** (monocular 3D ceiling on synth truth, bars A-G pre-registered).
  **P4 written and delivered** to `docs/DECISIONS_PENDING.md` — four contradictions, not three.
  `ios/README.md`'s false "nothing here has been built or run" corrected (it compiled green
  2026-09-10; only the sideload is blocked). Stale restart queue compacted to its three live
  carries. Doc-only commit, NOT pushed.

- **2026-09-12** — **NEXT-SESSION QUEUE SET by pm** (agent `a030453975e9d4c47`, 104k tokens). P1 measure
  monocular 3D on synth truth (bars A-G, incl. a MANDATORY self-grading control: simulator and fitter
  share a physics model, so bar A without an offset-coefficient arm is a ceiling, not an accuracy) ->
  P2 occlusion census (refusal FLOOR; >20% occluded WITHDRAWS SPEC's <=5% target) -> P3 does any of
  the 116 clips meet 60fps+1080p -> P4 three spec self-contradictions needing a founder ruling ->
  P5 capture protocol -> P6 INSTANT costed on paper -> P7 Swift skeleton. Five of seven are
  MEASUREMENTS. Prompt written to scratchpad `NEXT_SESSION_PROMPT.txt` and handed to the founder.
  **pm CORRECTED THE LEAD ON THREE THINGS, all now fixed in CLAUDE.md:**
  (1) the "INSTANT is ~60x away" blocker measured the FULL OFFLINE pipeline **including the pose
  model v1 tossed**; v1's per-frame path is a ~2 MB conv net plus arithmetic, and it can be costed on
  paper for an A13 with **no phone** — so the sideload does NOT block that question.
  (2) the 10 cm gold set is **NOT LABELLABLE FROM VIDEO AT ALL** — a human clicking a monocular low
  mount cannot resolve 10 cm (our own height curve: 3.81 m bounce error at a 1.0 m mount). Truth at
  10 cm must be built **AT CAPTURE** with tape-measured marks. That is a court visit with lead time,
  not a labelling session, and the lead had it filed as the latter.
  (3) the indoor-shell blocker is **probably VOID for v1** — written against the auto-detection SEARCH
  failure, but v1's court is a manual four-tap and two shell gold calibrations exist.
  **Lead VERIFIED pm's two flagged unknowns** (it had no Bash): `tools/height_curve.py` SURVIVED the
  cut, and `synth_truth.py` emits **(u,v) only, no apparent radius** — so pm's bar G is right and
  SPEC §5's depth-from-ball-size channel genuinely cannot be exercised by that rig.
  **pm caveat carried forward: its Grep/Glob returned nothing in this environment** — it could only
  read known paths. Dispatch it with explicit file lists until that is understood.
  CLAUDE.md held at **150/150** non-blank after the three corrections.

- **2026-09-11** — **AUDIT EXECUTED AND COMMITTED** (`59d82a9`, amended; NOT pushed). Founder amended
  SPEC on four points: latency **INSTANT** not 2 s; **use the Neural Engine** (the "CPU-only" framing
  is withdrawn, so the ANE conflict resolves in favour of the standing project constraint); **iPhone
  only** (Android ML Kit struck); **§6 and §9 TOSSED from v1** — read as "both sections out, evaluate
  later", stated as a reading in the reply so it can be corrected. So v1 has **no pose of any kind**
  and **no occlusion bridging**, which makes every occluded bounce a refusal and SPEC's <=5% refusal
  target provisional. §10's CourtNet attribution corrected to the SEARCH/proposal problem (8/20).
  **The cut:** tools **116 -> 57**, eval **30 -> 9**, backend scripts **21 -> 8**, swingvision
  **25 -> 22** (`audio.py` never called by the pipeline, `calib_score.py` failed its bar,
  `profiles.py` zero importers). `mobile/` shelved to `v2/mobile/` + `v2/README.md`. 185 MB of unused
  YOLO + 8 superseded BallNet checkpoints gone. `event_audit.py` lost its HUD path (rule 12 retires
  that reference); `test_hud_match.py` went with it. **69 dead ends recorded** across five
  `docs/<pillar>/CLOSED.md` files, each with the killing number and the `git show <sha>^:<path>`
  incantation to recover the code.
  **RULE 9 PROOF:** 781 passed / 1 skipped before -> **702 passed / 4 skipped, ZERO failures** after.
  Collected test IDs diffed before/after: **every one of the 76 lost tests belongs to a file whose
  subject was deleted** (test_calib_score 15, far_player_motion_gate 11, p0_3_population 10, audio 9,
  hud_match 7, audio_streaming_floor 5, audio_floor_chunking 4). **No test in any other file moved.**
  **ONE LEAD ERROR, CAUGHT AND FIXED IN THE SAME TURN:** `git add -A` committed **73 MB of ONNX
  binaries** that `.gitignore` had deliberately excluded — shelving `mobile/` to `v2/` moved them out
  from under `mobile/models/*.onnx`, which silently stopped matching. Untracked and the rule fixed
  with BOTH spellings (`git rm --cached` + amend); the blobs survive in the reflog until gc.
  **Lesson worth keeping: a `git mv` of an ignored directory un-ignores its contents.**
  **NEXT, unchanged and unblocked:** measure monocular 3D against the **10 cm** bar with
  `tools/synth_truth.py`. The rig exists, the bar exists, and it has never been done.

- **2026-09-11** — **TARGET SPEC LOCKED. `docs/SPEC.md` created** (10 sections, founder-authored,
  verbatim). It answers the precision question that was blocking everything: **10 cm landing
  accuracy, >=90% of near-line contested calls**. Bounce timing **+/-1 frame 90% / +/-2 frames 99%**.
  Capture floor **60 fps + 1080p, both HARD** (below 60 fps: refuse, do not attempt bounce
  detection). **Abstention is designed in** — refuse when 1-sigma > 10 cm, target refusal <=5% on
  contested calls. Latency **2 s**, NOT frame-rate real-time — this materially softens the F1=B
  reversal and makes it reachable. CLAUDE.md updated to match (148/150 non-blank) and SPEC.md added
  to the doc map.
  **THE SPEC REVERSES THIS MORNING'S POSE DECISION:** pose is back IN v1, but FENCED (§9) — native
  Apple Vision API, 15-20 fps, qualitative output only, and a hard +/-15% confidence-modifier limit
  that can never turn a refusal into a call nor extend the occlusion budgets. Our **custom** YOLO
  pose stack goes to v2 instead. So "park pose" is superseded: v1 uses a DIFFERENT pose source.
  **FOUR CONFLICTS FLAGGED TO THE FOUNDER, NOT RESOLVED HERE:** (1) the spec says "CPU-only
  on-device" throughout and treats the **ANE as a v2 upgrade** (§8), but the standing project
  constraint and the whole Core ML/harness line are built on "ANE is the only inference target"
  (see [[ios-architecture-rules]]: pin `.cpuAndNeuralEngine`, never `.all`). These cannot both hold
  and it changes what "affordable" means. (2) §9 names **Android ML Kit** — project is iOS-only.
  (3) §10 blames the shell blocker on **CourtNet**; STATE says CourtNet is Tier 2 and `courtfit`
  consensus beats it — the shell failure is a SEARCH/proposal problem (recall 8/20), so that
  wording would send someone to fix the wrong component. (4) §6 uses **racket/arm pose for
  contact-event detection**, which reads as PRIMARY evidence and sits awkwardly against §9's
  "confidence modifier only" fence.
  **Still nothing deleted or moved.** Working tree: CLAUDE.md, docs/SPEC.md, this journal.
  **NEXT, in order:** (a) resolve the four conflicts; (b) measure monocular 3D against the 10 cm bar
  using `tools/synth_truth.py` — the rig exists, the bar now exists, nothing downstream is safe
  without the number; (c) THEN shelve to v2/ and cut the dead. Founder instruction standing:
  "anything that doesn't serve this target, shelve it into a different folder for v2."

- **2026-09-11** — **AUDIT: v1 SCOPE DECIDED and CLAUDE.md REWRITTEN.** Founder rulings, all this date:
  **F1 = B, REAL-TIME** (reverses offline-first, the project's founding architecture premise).
  **F2 = clear the ENTIRE scoring scope** — `scoring.py`, `highlights.py`, `corrections.py` CUT;
  CLAUDE.md rule 12's 2026-08-27 reopening is REVOKED. **Pose = PARKED, not killed** — `pose.py`,
  YOLO weights, `classify_shot`, `speedspin`'s player-proximity split, `annotate.py` all stay on
  disk, out of v1. **Shot SPEED deferred to v2** with shot type.
  **Then superseded mid-turn by a larger brief:** v1 is an ENGINE, not a feature list — (1) 3D
  spatial court mapping incl. lines the camera cannot see, from regulation dimensions; (2) 3D
  trajectory + physics tracking that survives loss of line-of-sight; (3) bounce-point triangulation
  from the arc's vertical reversal x ground plane. Founder premise: SwingVision does all three from
  one camera **regardless of mount height**.
  **TWO LEAD ERRORS CORRECTED, both recorded because both were stated to the founder:**
  (a) `ball_physics/` was called "a possible 35-file cut", then "dormant". **Wrong twice** — it is
  the only 3D machinery in the repo and is now v1's centrepiece. `analytics.shot_speed_kmh` and
  `speedspin` are a FALLBACK CHAIN, not rival paths (`pipeline.py:2023` overrides the former with
  the latter and sets `speed_confident`), so F5 was never a real fork and is WITHDRAWN.
  (b) The height evidence (bounce err 3.81 m @1.0 m mount, close calls 54%) was quoted AGAINST the
  3D brief. It measures the **2D ground-projection estimator** — exactly the method a
  physics-anchored 3D fit replaces. **It does not transfer.** The objection reduces to "measure it".
  **CLAUDE.md rewritten from scratch**, 135/150 non-blank lines. Nothing else touched: no file
  moved, nothing deleted, working tree is CLAUDE.md + this journal only. Baseline before any of it:
  **781 passed, 1 skipped**.
  **NOT DONE, and next:** the 5 pillar `CLOSED.md` files; the 59 dead tools + 21 dead eval scripts;
  the scoring excision (NOT a clean seam — `pipeline.py:227` and `:2079` construct
  `scoring.TennisScore` directly, so it touches the orchestrator and needs its own test proof);
  `tools/` foldering (deliberately deferred — lowest value, highest silent-break risk).
  **THE FIRST REAL TASK IS A MEASUREMENT, NOT A CUT:** monocular 3D has never been evaluated here.
  `tools/synth_truth.py` already generates known 3D trajectories, so the rig exists. **A precision
  bar was requested from the founder (5 cm / 20 cm / 50 cm) and NOT yet given.** Do not start
  without it — rule 2.

- **2026-09-11** — **RESUMED by founder** ("ok continue"). Read as Step 1 sign-off and a go-ahead for
  Step 2 — stated as an assumption in the reply so it can be corrected. Audit continues.

- **2026-09-11** — **PAUSED by founder** ("Pause first I have to go to work"). Nothing left running.
  Paused mid-audit: Step 1 (INVENTORY) delivered and awaiting sign-off, Steps 2–4 not started. No code,
  docs or data were touched this session — it was read-only apart from this journal entry. See NOW.

- **2026-09-10** — **HARD PAUSED by founder** ("Ok this is hard paused ... I want to move on to a diff
  session first while this phone issue and sideloading has problems"). Nothing left running. **The session
  ended on a WIN, not a failure**: the Core ML export ran for the first time ever and did it on Linux at
  **1x instead of 10x**, and the iOS harness — Swift written blind by an agent for a compiler nobody here
  can run — **compiled green on the first attempt**. What blocked the last mile is Apple ID login on
  Windows (Sideloadly -22410, then iCloud and iTunes failing too). Diagnosis: not ours. Options recorded
  for whoever picks this up: unlock at iforgot.apple.com and wait an hour, AltStore instead of Sideloadly,
  a throwaway Apple ID, or the $99 developer account which deletes the whole category (TestFlight installs
  are a tap on the phone, and the 7-day re-sign treadmill disappears). **A VM/simulator was considered and
  REJECTED on the merits, not the difficulty**: no ANE and no thermal envelope, so it cannot answer either
  question the harness exists to ask — the repo already said "a Simulator number is not a device number".

- **2026-09-10** — **RESUMED by founder** ("ok continue building"). Pause cleared. The
  harness run had already completed inside the pause window. Resuming on FREE work only:
  a read-review of the uncompilable Swift, and preparing an `ubuntu-latest` variant of the
  Core ML export so the first spend is 1x rather than 10x. No CI, no push.

- **2026-09-10** — **PAUSED by founder** ("pause when stopwatch is done. List out what features
  are next and hold until we restart again"). Left running: the `ios-harness-2` frontend-dev run
  writing `ios/` — a job already in flight is not killed. Queue written into NOW, sections A–G.
  Nothing dispatched, no CI triggered, no commit, no push. **Only the founder clears this.**
- **2026-09-09/10** — **The v1 blocker list was wrong in BOTH directions and the lead relayed it
  wrong twice.** (a) "You still need a Mac" — false since 2026-09-04; the Core ML export runs on
  a GitHub-hosted `macos-14` runner. (b) "Pushes are barred" — a stale heading; item −1 directly
  below it said the bar was lifted. (c) Then, having corrected those, the lead wrote into
  `DECISIONS_PENDING` that the founder's new iPhone 17 made the three hardware-blocked decisions
  "now measurable" — **also false: there is no iOS app to install.** No `.xcodeproj`,
  `.xcworkspace`, `Package.swift` or `Info.plist` exists anywhere; `mobile/` is JS+Python and the
  export produces model artifacts, not an app. **Three instances in one day of trusting a
  document's claim over the repo** (T24's exact species). All three corrected in place.
  Consequence: the harness is now being written, and the founder's phone is unblocked as
  *hardware* while the *software to run on it* was the real gap all along.

- **2026-09-09** — **The court gold pool's provenance was never established.** Founder marked
  **10 of 28** rendered corner sheets wrongly placed. `_exact: true`, which `run_refs` treated
  as "a human deliberately placed these", only ever meant the Shape-lock checkbox was off, so
  agent output entered the pool wearing a human label. Damage is LOCALISED: of 11 reviewed
  clips from the 2026-08-11/12 seven-commit agent session **8 are wrong (73%)**; of the 10
  shell clips from `7c8b8af` — half the pool, same unevidenced "human" claim — **0 are wrong**.
  Auditing by commit hash under-counts by a third (`3399d58` is the session's closing commit,
  wrote 6; `ac94aab` wrote 0). Fixed: `_provenance` on save incl. the `moved_px` that
  `lock_shape` was discarding (0.508 px on a test quad); corners byte-identical; `references()`
  returns the identical 20 clips; 693 tests pass. Trap **T26** written. Two STATE rows.
  **Then a second defect, in the audit instrument itself:** the 28 sheets were rendered at
  **frame 0**, but gallery-mode placement uses arbitrary mid-clip frames from
  `collect_frames.py` — so under camera motion a CORRECT placement renders as wrong, and the
  10 verdicts carry a false-accusation risk. `--tag` was also silently dropped on the corner
  path (five renders → one file, four destroyed, no error). Both fixed; frame index now in
  every filename; default is the eval's own sample 4/8 via an imported `frame_positions()`,
  pinned by 88 tests.
- **2026-09-09** — **Re-audit CLOSED the founder's 10: 4 misplaced, 5 mixed, 1 exonerated**, judged
  across all 8 eval frames with the prior verdict hidden. Only 3 of 8 original "wrong" calls
  survived; `sAjkpeRq4P4` reversed to HOLDS (and the lead's own frame-0-vs-500 spot-check had
  wrongly confirmed the accusation — both frames sat inside a title shot). qa's two predicted
  false-exonerations both landed. **pm's triage then shrank the damage twice over** and the lead
  verified both corrections: (a) **TWO pools exist** — the 12/20 gate scores against
  `data/gold/*.court.labels.json` (`run_eval.py:79-90`), a different 20-file truth set, so it
  NEVER inherited T26; the lead's STATE row saying otherwise was wrong and is fixed. (b) **In-pool
  damage is 2 clips, not 4** — `HoHxFSX_gLk_s3` is not `_exact`, `bump_ntrp30` sits in
  `data/amateur_clips/` which `run_refs.py:132`'s non-recursive glob never scans. So proposal
  recall can rise to at most 10/20 = 50%, still under the 60% line: **the headline verdict
  SURVIVES, do not re-measure it.** Archived `yt-match40-calibration-is-wrong.md` (its 3 dangling
  links repointed), READMEs on `corner_audit/` and the new `data/pre_reaudit_backup/`.
  **Then the re-placement was STOPPED before staging**: all four "misplaced" clips are MULTI-SHOT
  (s1 M_win 101.9 + 3 cut frames, s2 81.2 + 2, s3 two venues, bump_ntrp30 a cut at 508), so
  clicking fresh corners on one frame reproduces the exact defect just exposed. The open question
  is `clip-shot-map.md`: does one camera setup cover >=6 of 8 frames (ACCEPT_VOTES)? Outcome is a
  founder drop-or-restrict decision, not a labelling session.
- **2026-09-09** — **qa's shot-map brief KILLED by a session limit for the SECOND time in one day**
  (reset 18:20 Asia/Manila). It died just after writing its bar — **and the bar SURVIVED in
  `.claude/journals/qa.md` run 5**, which is the journal rule paying for itself. Re-dispatched
  pointing at that bar with an explicit instruction to honour it verbatim rather than re-derive
  (re-deriving after a kill is bar-shopping, and this repo has been caught choosing thresholds
  post-hoc twice). Its scratchpad survived too — same session id, `measure_motion.py` /
  `motion.json` / `window_motion.*` all reusable. Corpse lock cleared by hand, again.
- **2026-09-09** — **qa's camera-motion brief KILLED by the session limit at zero work** (whole
  output: "New task. Let me look at the relevant machinery"). Same failure as 2026-09-03. Its
  lock `aa0740a0a774fd8af-*` was a corpse holding a slot and was cleared by hand per the
  restart checklist. Limit reset 13:20 Asia/Manila; re-dispatched verbatim, not shrunk.
  **Nothing is re-placed until that measurement lands** — it decides whether the founder's 10
  verdicts are sound or partly false accusations, and it is his time being spent either way.

- **2026-09-05** — **Founder ruling: "pause" means the ENTIRE session, not just agent
  dispatch.** Came out of a review of the doorman, which found the doorman was not the
  blocker at all: `doorman.log`'s five entries are ALL synthetic self-tests — it has never
  refused a real dispatch. The real blockers were in this file. (a) `NOW` still read PAUSED
  from 2026-09-04, a day after being told to continue, so every restart read a live pause.
  (b) This file contradicted itself on whether a killed session self-resumes — l.22 and the
  2026-08-28 LOG entry said yes (`autoContinueAtUsageLimit`), the "read this first" section
  said "NOTHING restarts it — paste this". So a DEATH was read as a PAUSE and cost a human
  message every time. Fixed here: a `RUN-STATE:` line in `NOW` with three values
  (RUNNING / KILLED / PAUSED-BY-FOUNDER), a RUN STATE section defining each and making
  pause-logging mandatory, and the kill section corrected.

- **2026-09-03** — **doorman v2 installed** from `agent-team-package/swingvision-install/`
  (INSTALL.md steps 1-5). New `agent_cap.py`/`agent-cap.sh`; settings env teams flag 1->0,
  spawn depth 1, native concurrent cap 3; `Agent` removed from all five role files, replaced
  by NEEDS DISPATCH + deliver-as-you-go; CLAUDE.md dispatch section gained the run budget
  (12 / 5 h) and the DELIVERABLE/STOP-WHEN brief contract. Four gates verified by synthetic
  payload (brief reject, cap park, hand-back, budget refusal) — all logged to `doorman.log`.
  One real dispatch: SubagentStart recorded spend, SubagentStop freed the slot, no leak.
  **STEP 7 MEASURED AND IT CONTRADICTS THE PACKAGE:** identical zero-tool agent cost
  **36,836** tokens with the real 150-line CLAUDE.md vs **39,105** stubbed to 13 lines — the
  stub cost 2,269 MORE, so CLAUDE.md size is NOT what the ~38k floor is made of. Trimming it
  buys nothing on dispatch cost; run COUNT and brief scope are the only real levers.
  **NOT DONE — needs a fresh session:** check 6, the nesting test (spawn-depth 1 and the new
  role files only load at session start, so this session would report a false result).
  CLAUDE.md had to drop 4 lines to stay at its 150 cap — see the diff, nothing load-bearing
  cut. Note: `claude-md-cap.sh` (and its sibling guards) fire on EVERY write Bash command,
  not just commits — their `"if": "Bash(git commit*)"` is not honoured by this CC version.

- **2026-08-29** — **Far-player MOTION gate FAILS; the null control is CLEAN.** Nearest
  `movers.foot_points` blob to a post-hoc far-player box: **median 5.751 box-heights, 7/15**
  within 1.5, against a bar of <=1.5 on >=10/15. Random-blob control also fails (9.265, 2/15;
  0 of 1000 seeded draws pass), so the negative is a measurement, not candidate density.
  **Bimodal, not marginal** — nothing between 0.62 and 5.75: on him for 7, 173-632 px away
  for 8. Third negative in the player-foot-gate family; rule 3 closes it. All verified by the
  lead: 479 tests pass, `eval/movers.py` byte-identical, both arms re-read from the artifact.
  **A number in MY brief was wrong**: "median ~9 blobs per frame" is pre-`MAX_PLAYERS`;
  post-cap it is **median 2**. That made the control WEAKER than designed (1-in-2.5, and
  random picked the nearest blob outright on 6 of 15) — so the negative survived an easier
  test than intended, which strengthens it. Contrast rider is descriptive, no gate: the
  player's luminance offset **never reaches the court patch's own luminance spread**, colour
  is the stronger channel, and contrast does NOT separate the frames motion found from those
  it missed. Commits `7d002e0`, `be0415e`.
- **2026-08-29** — Corner audit sheets built for 27 of 29 calibrations (`cc213d3`), pm's
  top-ranked item. Reproduces T23 on sight. The **camera-height fit is the isolating screen**:
  `yt_match40` alone fits 11.3 m; everything else 1.3-3.4 m.
- **2026-08-29** — **P0-3 reviewed and STATE corrected.** Built
  `tools/p0_3_context_sheet.py` (full frame + blown-up crop, straight from the probe JSON,
  no model run, no court lines because the calibration is broken). Reviewing the 25 tiles
  **confirmed the crop finds the far player** — the two strict passes are real far-end
  figures distinct from the near-player box, and every sampled rejection is a real far
  player rejected for anchor distance, not a bad detection. **Caught a live rule-1 breach
  en route:** STATE quoted P0-3 as "15 of 25" — that is the POST-HOC relaxed criterion
  (far-sized person anywhere in the crop), while the pre-registered strict test is **2/25
  vs 0/25 control**. The evidence file labelled it correctly; STATE had dropped the label,
  and the lead repeated the unlabelled number to the founder. Row rewritten to carry both
  with their criteria. New design number: a ball-centred 192 px crop holds the far player
  only barely — **median 26.3 px from the crop edge**.
- **2026-08-28** — **pm's ranked queue is EMPTY.** Items 1, 2, 3 and 5 shipped; item 4
  (`bounce_hypothesis`) was measured and FAILED. Items 6 and 7 are the two pm ruled out for
  unattended work. Nothing further is dispatchable without a founder decision or a fresh
  sequencing pass.
- **2026-08-28** — `bounce_hypothesis` v2 **FAILED 4 of 7 bars** and does not ship (defaults
  unchanged, 468 tests pass). More valuable than the failure: it **disconfirmed its own named
  cause**. v2 removed `restitution_band` and gated tighter than v1, so the `wrong` rises
  should have gone to zero — they went 5 clips to 4. A one-variable ablation split the halves:
  removing the band is the good half, "more hypotheses" is the worse half. Reading the 17
  changed frames falsified the mechanism's core claim that a ghost fits neither hypothesis —
  the reflected hypothesis has its own false-acceptance region, covering a lock 502 px off
  track. **Correction to a claim the lead relayed:** `gate_ball_to_court` is NOT dead code —
  on gold caches it removes locks on 4 of 7 calibrated clips (`gold_sAjkpeRq4P4` -674). The
  earlier "14/14 no-op" was cache-family-specific.
- **2026-08-28** — Detector question **settled at the chain and the answer is SPLIT**, commit
  `2ead76a`. TrackNet: solid ghosts 88 -> 62 (-29.5%) for 8 hits. BallNet v21: more
  speed-confident shots, longer trails. `event_audit` underpowered. **This is now a founder
  decision**, because BallNet has no Core ML export path and TrackNet's ONNX already ships in
  `mobile/models/`.
- **2026-08-28** — **Concurrency doorman built, verified and fixed.** A cap kept only in
  CLAUDE.md could not hold, because the lead cannot see what its children spawn.
  `.claude/hooks/agent_cap.py` now counts every agent in the tree; a refused dispatch is
  parked verbatim and handed back when a slot frees. Teammates may now call each other.
  Measured: **~38k tokens is the floor for ANY agent**, so three at once is ~115k before a
  useful result; nested probe read BEFORE=1, INNER=2, AFTER=1.
  **qa passed it on nine checks and broke it on three.** The one that mattered: a read-only
  check is not a gate — counting had no side effect, so several dispatches in one message all
  saw the same free slot and all passed. Fixed with a reservation taken at approval time.
  Also fixed: sanitised agent ids colliding into one lock, and prompts truncated in the
  hand-back with no notice. Recreation guide at `master references/10`.
  **Two lead errors worth not repeating:** a `cd` leaked into a subagent's working directory
  (qa started in `master references/`, not the repo root); and Python's `write_text` silently
  rewrote seven LF files to CRLF, which the repo's own CLAUDE.md cap hook caught.

- **2026-08-28** — Detector comparison killed by usage limit. **Lesson: nothing restarts a
  dead subagent.** `autoContinueAtUsageLimit` resumes the SESSION; a subagent that hits the
  limit is killed outright and no mechanism polls for it. The failure notification IS the
  restart trigger — treat it as one, do not just report it.
- **2026-08-28** — Audio screen: **0 bail-outs of 88 clips, 0 of 62 Shell.** The feared
  correlated audio/vision failure on echo-heavy indoor courts did not occur. Two findings:
  the binding threshold is level-dependent (58-65% of candidates discarded on quiet indoor
  venues vs 17-25% outdoors — same class as the unscaled 720p constants), and
  `impact_envelope`'s rolling median is O(n·win) with a **13.5 GB peak allocation** on a
  28-min clip, never hit because nobody has run it on a full match. Committed `cae1dcc`.
- **2026-08-28** — Refusal band measured (qa). Both real mounts at/below the floor within
  10 cm; clear it from ~20 cm. `live.py`'s shipped `line_margin_m = 0.05` sits inside the
  unreliable zone. **qa correctly refused to write to the codebase** — its charter forbids
  it and my brief wrongly asked. Its findings still need filing by the lead.
- **2026-08-28** — P0-3 rebuilt. Crop finds the far player where full frame does not
  (0/25 control vs 15/25 crop192@640), and the mechanism is **upscale factor**, peaking at
  ~100-140 px of player in the tensor — a transferable design number. Found en route that
  `yt_match40`'s calibration is fabricated, which **withdrew P0-2's yt_match40 column**.
  Commits `10ed80f`, `8454e7e`.
- **2026-08-27** — P0-2 FAILED its gate: pose downscaling destroys the far player
  (11.0% → 0.1% → 0.0%). Closed full-frame downscaling as a way to afford pose on an A13.
- **Two lead errors worth not repeating:** sent execution work to `researcher`, which has
  no `Bash` by design; and claimed an agent was running without calling `ListAgents`.
  Match the task to the agent's `tools:` first, and verify state before asserting it.

---

## PRE-REGISTRATIONS — 2026-09-03. Full text is in git, not here

Compacted per this file's own rule (*numbers here are pointers; the authority is
`docs/STATE.md` + `docs/evidence/`*). Each bar was written and **committed before** its
result, which is the point of recording them; the commit named is the one that first
carried the text, and `git show <commit>:.claude/journals/lead.md` prints it in full.

| Pre-registration | Written in | Result | Verdict |
|---|---|---|---|
| int8 ball-graph parity — 6-clip set, rate definition, Arms B and C | `28ead70` | `28ead70` | 3 of 6 clips FAIL; both mitigations rejected |
| Smoother gate — backward-pass re-admit separation, >=3:1 + null control | `1fbcb6f` | `1fbcb6f` | **FAIL** 0 of 3; branch closed, rule 3 bars a fourth |
| `seen_frac >= 0.5` — does the gate predict speed error, G/N/I + n floor | `79c381d` | `6013653` | INDETERMINATE; G refuted everywhere; gate at chance |

**The one process lesson from these three, worth keeping in front of me:** on the int8
lane I picked a threshold *after* seeing which frames failed, and qa showed it collapsed
under a sweep. Both later briefs forbade naming a threshold from the data that revealed the
problem, and both agents complied. Keep that clause in every threshold brief.

---

## RATE-LIMIT KILL 2026-09-03 ~23:45 — and what the lead did instead

The `Definitive seen_frac gate numbers` run was **killed by a session limit before it did any
work** (its whole output was "I'll start by reading my journal"). Session limit resets 19:40
Asia/Manila. Locks checked and were already clear — no corpse to reap this time.

**Do not re-dispatch that brief while the limit holds**; a re-dispatch dies the same way and
spends a run for nothing. The lead is running the work directly instead: the harness is now a
committed tool (`tools/seen_frac_speed_error.py`, `cf556a5`) with clips, seed and arm as
arguments, so this particular task no longer needs an agent at all. That is a side benefit of
having promoted it out of the scratchpad an hour earlier.

**PARKED, verbatim, so it survives:** multi-seed classifier margin (accept-precision minus
base rate) on the FAITHFUL 2.5 m config, both arms, against the **>=10-point bar already
pre-registered in the evidence file's own section 7** — not a bar chosen after seeing the
number. Plus the restated reject characterisation, and an explicit supersedes-list naming
every number the 4.0 m defect invalidated.

Seed 0, faithful config, already in hand: accept-precision **0.500** vs base rate **0.467**
(unrestricted) and **0.500** vs **0.466** (shipped-shot) — a margin of **+3.3 / +3.4 points**
against a >=10 bar. One seed is not evidence, which is the whole lesson of the run before
this; 10 seeds x 2 arms are running now.

---

## PRE-REGISTRATION — the §7 held-out replacement-bar sweep. 2026-09-04, BEFORE it runs

Executing the pre-registration in §7 of `does-seen-frac-predict-speed-error.md`. Two things
§7 could not have known, both settled here BEFORE any sweep runs.

**1. §7's own named candidate clips are the two WORST available, and are rejected.** It named
`court_pts_refined` and `eala_pts_auto`. Their audit stamps fit camera heights of **12.28 m**
and **8.89 m**. That is the exact signature that exposed `yt_match40` - stamped PASS at 0.9 px
while grossly wrong, and STATE records the camera-height fit as *"the one screen that isolates
it"* (every sane clip fits 1.3-3.4 m). Using either would repeat T23 knowingly. **Rejected on
that ground, before seeing any result they would produce.**

**Held-out clips used instead** - all `_audit` verdict PASS, residual <=1.4 px, camera height
in the plausible court-side band, `img_wh` read from the actual clip (not assumed, which
`yt_court` is), and none used in the burned experiment:

| clip | residual | camera h | resolution |
|---|---|---|---|
| `L73ep7JHiJ4` | 0.7 px | 2.89 m | 1920x1080 |
| `mpc_tuesday_p01` | 0.9 px | 2.79 m | 3840x2160 |
| `flexi_franz_p01` | 0.2 px | 2.50 m | 3840x2160 |
| `tc8CGFxyRE8` | 1.4 px | 2.00 m | 1920x1080 |

Four distinct venues, exceeding §7's minimum of 3. `mpc_tuesday_p07` (0.5 px, 2.81 m) is
available as a fifth but is **the same venue as p01**, so it is not independent and is not
counted toward the >=3-of-N tally. Excluded and why: `sAjkpeRq4P4` (PASS 2.8 px but its corner
sheet is one of the two the lead could not settle), `uR5q2cSM6AY` (PASS but 9.3 px).

**2. The accuracy label must be FIXED across the sweep, and currently is not.**
`classifier_table` defines "accurate" as `<= median abs% error of the ACCEPTED set`. That is
defensible at a single fixed threshold - it scores the gate against the population it creates -
but it makes a **sweep meaningless**, because the label moves with every candidate `t` and
precisions at different `t` are then not comparable.

**For the sweep, and only the sweep, "accurate" is `<= the median abs% error of the WHOLE
clip population`, computed once, independent of `t`.** Base rate is then ~0.50 by
construction and identical at every step, so the >=10-point margin means the same thing
everywhere on the curve. The single-point table keeps its existing definition unchanged; the
two are reported separately and never mixed.

**Bar, unchanged from §7:** a replacement `t` is admissible only if on **>= 3 of the 4
held-out clips** (a) accept-precision at `t` beats the fixed base rate by **>= 10 points**,
and (b) both neighbours `t +/- 0.05` are within 3 points of `t`'s precision - the plateau
test. Sweep [0.20, 0.90] step 0.05, FULL curve reported.

**Multi-seed or it does not count.** >= 5 seeds; a `t` admissible on a single seed is not
admissible. This file's own instability finding is the reason.

**Court-coverage faces the identical sweep, as §7 requires** - named, not adopted, and with
its partly-mechanical confound restated at the point of reporting.

**Nothing ships from this.** An admissible `t` earns a real-footage confirmation arm (§7 item
4), which no compliant reference currently supports.

---

## PRE-REGISTRATION — top-2 blob margin as a REFUSAL signal. 2026-09-04, before any run

**Where this came from:** the activation diff (`2110964`) established that int8 is not the
disease — the failing frames carry the same quantisation noise as frames that decode
correctly, and what actually breaks is the fp32 model's own **~5% top-2 `area x peak` margin**.
The failure's defining property is a **confident wrong lock with no refusal signal**. So the
lead is not another precision arm (three have failed, rule 3 bars a fourth); it is giving the
decode a way to say "I don't know".

**Chain-side, so rule 6 does not close it.** It also protects the **fp32** path, which the ~5%
margin shows is one bad frame from the same error.

**The signal:** at decode time both blobs are already computed — `margin = 1 - (score_2 /
score_1)` over the connected components' `area x peak`. No new model, no retraining, no extra
inference. Cost is a comparison.

**PRE-REGISTERED BAR.** Measured on the 6-clip parity set already committed (528 both-fire
frames, 5 of them disagreeing by >10 px):
- **PASS:** some margin threshold flags **>= 4 of the 5** known bad frames while refusing
  **<= 5%** of correctly-decoded both-fire frames. Both halves required — a signal that
  catches every failure by refusing everything is the degenerate answer the seen_frac sweep
  just caught, and it is barred here in advance.
- **FAIL:** anything else. A failed bar stays failed.
- **Mandatory null control**, seeded, 1000 draws: permute the bad/good labels and report what
  fraction of permutations reach the same catch rate at the same collateral. Without it a
  5-frame result is uninterpretable.

**POWER IS THIN AND IS NAMED IN ADVANCE, not after: n = 5 failing frames.** That is a ceiling,
not a choice — it is every >10 px frame in the whole 6-clip set. **A PASS here is a screen,
not a verdict**, and earns a wider run on more clips; it does NOT earn a ship. If the null
control cannot separate at n=5, say so and report the branch as UNDERPOWERED rather than
passed — that is the honest outcome and I will take it.

**Also measure, reported not gating:** the same margin on the 8 + 2 + 8 + 3 + 5 + 1 null
mismatches (fp32 fires, int8 does not), since a refusal signal that also predicts dropout is
worth more than one that does not.

**Not authorised:** shipping, changing the decode's behaviour, or quoting a coverage number.

---

## PRE-REGISTRATION — least-squares over ALL line correspondences. 2026-09-04, before any run

**The target, from STATE's joint-correspondence row (measured 2026-08-29):** given the
**TRUE** line-to-model assignment, the solver's reconstruction is a median **17.1 px@640**
against the shipped **8.1 px**. Cause named there: a homography from exactly **four line
intersections** amplifies each line's error where the court is most foreshortened. That row
names two untested continuations; this is the first. The second (why `verify_court` rejects a
correct court) was taken up separately on 2026-09-04 and is now its own row.

**Why this is decisive either way, and worth a run:** it is tested **given the true
correspondence**, so it isolates the FIT from the SEARCH. If least-squares over all matched
lines cannot beat the exact-4-point fit when handed the right answer, then no improvement in
correspondence search can rescue the solver, and **the whole joint-correspondence branch dies
on a fit ceiling rather than on a matching problem**. That is worth knowing before anyone
spends another run on C6's 12.6x cost or on the 22-of-30 die-before-scoring.

**PRE-REGISTERED BAR** — same clips, same true assignments, one variable (the fit only):
- **PASS:** median reconstruction **<= 10.0 px@640**, i.e. it closes most of the 17.1 -> 8.1
  gap, on the same clip set the 17.1 px was measured over.
- **FAIL:** median > 13.0 px — less than half the gap closed. **Then the branch dies on the
  fit ceiling** and that verdict goes in STATE as such.
- **INDETERMINATE:** 10.0-13.0 px. Reported as indeterminate; nothing is built on it.
- **Mandatory control:** report the exact-4-point fit's median **recomputed in the same run**,
  not quoted from the 2026-08-29 row. If the control does not reproduce ~17.1 px, the harness
  is not measuring what that row measured and **nothing else in the run is trusted**.
- Report per clip, not only pooled; a pooled median can hide a split.

**Not authorised:** shipping, changing the shipped court path, or reopening the correspondence
SEARCH (C6's cost, the 22-of-30 kills). This is the fit and only the fit.

---

## PRE-REGISTRATION — an int8-COMPUTABLE refusal signal. 2026-09-04, before any run

**The gap this closes.** The top-2 margin refusal PASSES on fp32 (5/5 caught, 2.1%
collateral, three nulls at p<=0.001) and **FAILS on int8 at every threshold**, because on the
frames int8 gets wrong its own margin is *wide* — 0.86, and 1.00 with no runner-up at all.
Quantisation did not leave a close race, it **resolved** it. So the one cheap safety net is
computable only from the graph **mobile does not ship**, and that is now a stated cost against
int8 in `DECISIONS_PENDING` item 0.

**The question:** is there ANY quantity the int8 graph itself produces that flags its own bad
frames? Candidates visible in its own heatmap, all free at decode time: the winning blob's
**absolute area**, its **peak** value, the **blob count**, and the winner's **area x peak**
score in absolute terms. On `am_hard_utr/0147` the int8 true blob fragmented to area 2 + 1,
and on `yt_rally2/0108` int8 produced a **single** blob — so "small winner" and "exactly one
blob where fp32 saw two" are the mechanically-motivated candidates, named before looking.

**PRE-REGISTERED BAR** — same 6-clip parity set, 528 both-fire frames, 5 bad:
- **PASS:** some single int8-computable quantity, at some threshold, catches **>= 4 of 5** bad
  frames at **<= 5%** collateral on correctly-decoded frames. Both halves required.
- **FAIL:** anything else. Then **int8 cannot police itself**, and that is the finding — it
  makes the fp32-only refusal a hard constraint on the ship decision rather than an
  inconvenience.
- **Mandatory seeded null control**, 1000 draws, as before. And because several candidates are
  being tried, a **selection-adjusted null** is required too: each draw must search the same
  candidate x threshold grid, or the multiple-comparison advantage is unpriced.
- **Report refusal PRECISION, not only catch and collateral.** The fp32 signal passed its
  screen at **31% precision** and the honest reading was "a risk gate, not a detector". Any
  int8 candidate gets the same treatment and the same wording.

**Power is thin and named in advance: n = 5 bad frames, effective n ~3** (`yt_rally2`
0108-0110 is one consecutive event). A PASS is a SCREEN and earns a wider run, never a ship.

**Not authorised:** changing the decode, shipping, a fourth precision arm, re-running int8
inference (~10 s/frame; the heatmaps are on disk).

---

## PRE-REGISTRATION — the net tape as an INDEPENDENT camera-height estimator. 2026-09-05

**Where this came from.** qa measured the real net tape row on two clips by brightness
profile. Inverting the projection - `H = h / (1 - (tape-horizon)/(ground-horizon))` - turns
that row into a camera height that does **not** come from the four clicked corners. On the
three clips with a measured tape it disagrees with the fitted height by **-12.8%, -33.3%,
+12.2%**.

**Why this is not a footnote.** Camera height is the largest accuracy lever in this project
and the close-call table is indexed by it: **54.0% at 1.0 m, ~69% at 3 m, ~81% at 8 m**,
against a **56.2%** majority-class floor. A 13-33% height error moves which row of that table
a clip belongs in, so every quoted call-accuracy figure inherits it.

**Neither estimator is ground truth**, and the brief must not pretend otherwise. The fitted
height comes from the four corner clicks; the tape height assumes a regulation net (0.914 m at
centre) and a correctly measured tape row. **This is a CONSISTENCY check: disagreement proves
at least one is wrong, not which.**

**PRE-REGISTERED BAR**, over every clip with a visible net:
- **AGREE:** `|tape-implied H - fitted H| <= 10%` of fitted, on **>= 2/3** of clips measured.
  Then the fitted heights stand and this closes.
- **DISAGREE:** anything else. Then **the accuracy table's height axis is in question**, and
  the next step is a tiebreaker, not a correction - do not "fix" heights on the strength of
  the tape alone.
- **Mandatory:** report the **direction** per clip. A consistent sign is a systematic bias
  (a modelling error); mixed signs point at measurement noise in the tape row. Those imply
  different next moves and the distinction must not be blurred.
- **Minimum n:** >= 6 clips with a confidently measured tape, or the result is UNDERPOWERED.
  Three is what prompted this and three is not enough to conclude anything.

**Not authorised:** editing any calibration; changing any fitted height; restating the
close-call table. This measures a disagreement, it does not resolve it.

---

## PRE-REGISTRATION — the fitted hfov, which the code computes and throws away. 2026-09-05

**qa's finding, not a new idea of mine.** `cam_fit_quad` already fits an hfov per clip. Under
depth-anisotropic compression - the ONE corruption invisible to every shipped gate - that hfov
**collapses monotonically**: 91 -> 55 -> 34 -> 18 -> 9 -> 2 deg on `yt_match40`, leaving this
repo's own stated **60-90 deg amateur-lens prior** by about **15% compression**. Nobody reads
it. `camera_height_m()` **hardcodes a default 70 deg** instead of the value the fit computed
a few lines earlier.

**So this is a reporting gap, not a new instrument**, and that framing is load-bearing: the
number already exists and is discarded.

**PRE-REGISTERED BAR** - and it is deliberately two-sided, because **four autonomous gates have
already failed here and the fifth must clear a higher bar than "it flags the bad one":**
- **SEPARATES:** an hfov-plausibility window flags **>= 4 of 5** synthetic depth-compressions at
  the magnitude qa used, AND flags **0 of the calibrations believed correct** - `eala_pts_auto`
  **specifically included**, since it is a real Wimbledon broadcast camera and is exactly what
  false-rejected the camera-height screen. A window that catches compressions by also rejecting
  broadcast footage has reproduced the previous failure, not fixed it.
- **DOES NOT SEPARATE:** anything else. Then it is **reported as a number and not gated on** -
  which is still a win, because it is currently not reported at all.
- **The window must be justified BEFORE the sweep** from the lens prior already written down
  (60-90 deg), not chosen from the results. If the justified window fails, it stays failed; do
  not widen it to fit.

**Not authorised:** a fifth accept/reject gate shipped on this evidence; editing any
calibration; changing `cam_fit_quad`'s fit. Surfacing a computed number is authorised.

---

## PRE-REGISTRATION — a COMPOSITE calibration score. 2026-09-05, founder instruction

**Founder: "Don't just use the net - it should be a mix of all we've worked on."** Correct, and
the lead had over-indexed on the net because it was the one thing that worked alone.

**Why a mix is principled here and not just hopeful.** Every signal failed as a solo gate, but
**they fail for DIFFERENT reasons**, which is the condition under which an ensemble beats its
members:

| signal | what it sees | how it fails alone |
|---|---|---|
| net-tape clearance | far baseline vs tape, pre-calibration | geometric only; says nothing below the crossover |
| net-tape height | camera height, off-plane | precision-limited (3.2%/px at 720p); net SAG |
| net posts (1.07 m) | off-plane, RIGID - no sag | 7x worse row precision; confidently wrong on 4/11 |
| fitted hfov | depth-anisotropic compression | false-rejects broadcast (`eala`) and 6 correct clips |
| camera height | mount plausibility | mount-TYPE test, not correctness |
| line coverage | lines on real paint | orders by line VISIBILITY, not correctness |
| fit residual | corner self-consistency | T23: 0.9 px on a grossly wrong court |
| centrality | court centred | never fires |
| player feet -> depth | an object standing ON the court | needs a person, one frame |

Coverage fails on contrast; hfov fails on broadcast; height fails on mount type. **Those are
decorrelated failure modes.** A wrong court has to fool all of them at once.

**THE HARD PROBLEM, named before anyone starts: n = 1 confirmed-wrong calibration.**
(`yt_match40`'s `.bak`.) You cannot fit or validate an ensemble on one positive. **So the
positive class MUST be synthetic** - qa's corruption harness already generates depth
compression, isotropic scale, shift, rotation and asymmetric scale, and it is the only way to
get a positive class with any n at all.

**PRE-REGISTERED BAR:**
- **Fit the combination rule on a TRAIN split of clips; report on a HELD-OUT split.** Any number
  quoted from clips the rule was chosen on is worthless, and this project has been caught
  choosing thresholds post-hoc twice this week.
- **PASS:** on held-out clips, flags **>= 80%** of synthetic corruptions at **<= 1 false flag**
  among the calibrations believed correct - **`eala_pts_auto` included as a negative**, since it
  broke two previous screens.
- **FAIL:** anything else. **A sixth failure is a fine outcome** and would say the signals are
  not merely weak but redundant - all reading the same thing.
- **Mandatory ablation:** report each signal's solo score and the composite's, so the reader can
  see whether the mix adds anything or one member is carrying it. **If one signal alone matches
  the composite, say so** - that is the honest result and it kills the ensemble.
- **Report by corruption TYPE, not pooled.** Depth compression is the one that matters; a
  composite that shines on rotation (which residual already catches at 5 deg) and misses
  compression has solved nothing.

**Still not a gate.** Five have failed. Output is a score and a reason string for the human who
confirms setup. Whether it ever gates is a founder call, not this run's.
