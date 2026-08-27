# Subagent transcript — `a8f02ade667576f3c`

Source: `C:\Users\richm/.claude/projects\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\7168a5a5-e837-47d6-bdb6-ab1e3b940119\subagents\agent-a8f02ade667576f3c.jsonl`
Messages: 29

Started: 2026-08-27T05:32:08.539Z
Ended:   2026-08-27T05:32:45.651Z

---

### Prompt / result

**Read these first, in this order:**
1. Your own memory: `.claude/agent-memory/researcher-agent/MEMORY.md` — backfilled 2026-08-27 from ~2 months of project history that predates you. It records what has already been investigated and rejected. Do not re-propose anything in it.
2. **pm-agent's memory: `.claude/agent-memory/pm-agent/MEMORY.md` and the topic files beside it.** The user has asked that the agents learn from each other. pm-agent produced the plan you are researching; its memory records the reasoning, the reversals and the verified findings behind it. Read it so you build on it rather than re-deriving it.
3. `docs/evidence/mobile-viability-audit.md` — the audit underneath the whole plan.

**Context.** pm-agent's iOS plan was APPROVED by the user today (2026-08-27). Your job is the four research questions it raised. This is step 2 of the project's feature workflow: your findings go back to the user for approval before any implementation starts.

**Rulings now in force — these are settled, do not reopen them:**
- **iOS / iPadOS only, A13 or newer** (iPhone 11, SE 2nd gen, 2020 iPad Pro and newer; iOS/iPadOS 18+). Android is NOT a recording or inference device — companion only (remote control, line-call challenges). Your HARD CONSTRAINTS have been updated: Core ML / ANE is the only inference target, and you budget to the FLOOR of the range (A13), not a recent Pro.
- **There is no desktop product.** The Python backend is a training and evaluation lab.
- **The rally/score layer is BACK IN SCOPE** (superseding the 2026-08-20 closure). But reopening scope did not create ground truth, and a burned-in scoreboard remains barred by rule 11.
- Singles and doubles both. Session (Match or Rally/Practice) is the macro unit; the individual shot is the tracking unit; the point-by-point clip is the viewing unit.

**The four questions, in priority order. R1 first — it constrains the architecture and is cheap.**

**R1 — iOS background compute limits.** What are the real limits on sustained background compute on iOS 18+: `BGProcessingTask` scheduling behaviour and realistic per-invocation wall-clock, kill conditions, and whether any shipped consumer app performs multi-hour on-device ML inference on user media in the background. What pattern do on-device-analysis apps (Photos, Lightroom, video upscalers) actually use, and what do they tell the user while it runs? This decides whether resumable checkpointing is core architecture (the plan assumes it is) and whether "analyse my match" is one feature or two.

**R2 — Core ML export for YOLO11-pose, single platform.** For `yolo11m-pose` at 1280 / 640 / 384 input: Core ML export maturity, ANE operator coverage, known triggers for silent fallback to GPU or CPU, and reported int8/fp16 accuracy loss for pose specifically (not classification). Are there published *sustained* on-device throughput figures for YOLO11-class pose models on **A13-generation** Neural Engine? Sustained, not peak — and say which any cited number is. Pose is the binding runtime constraint in the plan.

**R3 — sensor-assisted court calibration, prior art.** How are IMU gravity vectors and known camera intrinsics used to constrain court/pitch registration in published camera-calibration and sports-CV work, and what accuracy is reported? Specifically: what is realistic error on gravity-derived roll and pitch from a phone IMU on a **fence mount subject to vibration**, and what is ARKit's reported plane-height error on a flat outdoor surface at 5-10 m range? These bound how much the search can safely be narrowed before the priors start excluding the true court — which is the failure mode that matters, because this project rejects any change that admits a wrong court.

**R4 — point-boundary ground truth, compliant sources only.** What compliant methods exist for establishing tennis point boundaries from video *without* a scoreboard — derivation from ball-in-play state, bounce sequences, or player position — and what agreement with human labels do they achieve? What inter-annotator agreement do humans achieve on point boundaries? That sets the ceiling on any automated method and determines how many labelled matches are actually needed. Note the project has costed ~5 human hours across ~15 matches; say whether that is the right order of magnitude.

**Discipline that applies to your answers:**
- Say what footage or hardware every number was measured on. A benchmark figure from a flagship phone tells you little about an A13; a court-registration figure from broadcast footage tells you nothing about a phone on a fence.
- Distinguish what is published from what is your judgement. Grade your own confidence as a number.
- Name what would disprove you, and say which of your findings is cheapest to falsify.
- If a question cannot be answered from published work, say so plainly rather than dressing an estimate as a finding. "There is no public number for this" is a valid and useful answer.
- Flag anything that changes pm-agent's plan — especially anything that would move a phase estimate, invalidate a pre-registered gate, or change the ordering.

**When you finish: update your memory** at `.claude/agent-memory/researcher-agent/MEMORY.md` (and topic files beside it) with what you established, what remains unknown, and anything a future session should not re-derive. That is how the next agent learns from you.

Do not write code. Do not edit any files outside your own agent-memory directory. Return your findings as your final message, in your default output shape.

### Assistant

I'll start by reading the memory files and the audit, then work the four questions.

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\MEMORY.md"}

```
1	# researcher-agent memory
2	
3	Backfilled 2026-08-27 by the main session from git history, `docs/STATE.md`,
4	`docs/TRAPS.md`, `docs/RESEARCH_BRIEF_indoor_shell_courts.md`,
5	`docs/archive/sessions/SESSION_O_shell_courts.md` and `docs/archive/resolved/`.
6	Everything here is sourced; anything uncertain is marked. Covers ~2026-06-20 → 2026-08-27,
7	all of which predates this agent existing.
8	
9	**Before proposing any investigation, read `docs/STATE.md` "What has not worked"** —
10	~50 rows, each already measured here under a pre-registered gate. Nine distinct ideas in
11	it were re-proposed at least once.
12	
13	---
14	
15	## Approaches already investigated — court detection
16	
17	The named ones first, since they recur.
18	
19	| Approach | Outcome |
20	|---|---|
21	| **Widen the seed gr
… [15959 chars total]
```

> **tool** `Glob` — {"pattern": ".claude/agent-memory/**/*.md"}

```
.claude\agent-memory\researcher-agent\MEMORY.md
.claude\agent-memory\pm-agent\line-call-numbers-assume-perfect-bounce.md
.claude\agent-memory\qa-verifier\MEMORY.md
.claude\agent-memory\pm-agent\live-path-has-no-refusal-surface.md
.claude\agent-memory\pm-agent\mobile-v1-scope-live-calls.md
.claude\agent-memory\pm-agent\parity-before-features.md
.claude\agent-memory\pm-agent\mobile-parity-first.md
.claude\agent-memory\pm-agent\ios-only-no-desktop-product.md
.claude\agent-memory\pm-agent\sensor-assisted-court.md
.claude\agent-memory\pm-agent\score-layer-reopened-no-ground-truth.md
.claude\agent-memory\pm-agent\MEMORY.md
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\MEMORY.md"}

```
1	# pm-agent memory
2	
3	## Index
4	
5	- [Parity before features](parity-before-features.md) — USER RULE: recreate the existing product on mobile first; do not let port-readiness drive product sequencing
6	- [iOS-only, and no desktop product](ios-only-no-desktop-product.md) — two rulings that reshape everything: Python is a lab; target is iOS/iPadOS A13+, Android companion-only
7	- [Sensor-assisted court](sensor-assisted-court.md) — IMU/intrinsics/ARKit collapse the search; REBUILD not port; blocked on a sensor gold set that does not exist
8	- [Score layer reopened, still no ground truth](score-layer-reopened-no-ground-truth.md) — 2026-08-20 closure superseded; stroke type is an unmeasured pose heuristic
9	- [Mobile plan](mobile-parity-first.md) — pose binds runtime, court binds sessions, 
… [10370 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\ios-only-no-desktop-product.md"}

```
1	---
2	name: ios-only-no-desktop-product
3	description: Two rulings of 2026-08-27 — the Python backend is a lab not a product, and the target is iOS/iPadOS A13+ only with Android as companion-only
4	metadata:
5	  type: project
6	---
7	
8	Two user rulings, 2026-08-27, that reshape every mobile decision.
9	
10	**1. There is no desktop product.** Verbatim: *"There should be no more desktop product,
11	at most the desktop is only here to help the ML training of the feature."* The Python
12	backend + React frontend are a **training and evaluation lab**. The phone is the product.
13	
14	Consequences worked through:
15	- **"Parity" is the wrong word** and should be retired. There is no shipping thing to
16	  match. The goal is *the iOS app becomes the product, using the Python lab as reference
1
… [3525 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\sensor-assisted-court.md"}

```
1	---
2	name: sensor-assisted-court
3	description: Phone sensors (IMU, AVCaptureDevice intrinsics, ARKit) collapse the court search space — argues for a sensor-first REBUILD, not a C++ port; blocked on a new gold set that does not exist
4	metadata:
5	  type: project
6	---
7	
8	**Verdict reversal, 2026-08-27: do not port `courtfit.py`. Rebuild court detection
9	sensor-first.** I had scoped a faithful C++ port and sequenced it last as the worst
10	ratio in the stack. Phone sensors change the problem.
11	
12	**The mechanism, and it is specific — not hand-waving.** Desktop court failure is a
13	**search** problem. `autodetect` searches a 5-parameter grid `(cx, y_near, y_far,
14	half_width_near, half_width_far)`. Verified in `courtfit.py` (`COARSE_GRID`, ~line 758):
15	the far-half-width axis i
… [3606 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\score-layer-reopened-no-ground-truth.md"}

```
1	---
2	name: score-layer-reopened-no-ground-truth
3	description: The rally/score layer was reopened 2026-08-27, superseding the 2026-08-20 closure — but it still has no ground truth and the easy source is still barred
4	metadata:
5	  type: project
6	---
7	
8	**The 2026-08-20 out-of-scope ruling on the rally / score layer was SUPERSEDED on
9	2026-08-27.** User: *"I think follow what I said now."* CLAUDE.md rule 12 rewritten to
10	record the supersession. In scope again: **match scoring (sets, games)**, **point-by-point
11	clip segmentation with automatic dead-time trimming**, and **shot-filtered playlists**.
12	
13	**Reopening scope created a requirement, not a measurement.** Carry all of this forward:
14	
15	- **That layer still has NO ground truth of any kind**, and **rule 11 still bars 
… [3336 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\mobile-parity-first.md"}

```
1	---
2	name: mobile-parity-first
3	description: Mobile parity plan — the three perception stages have DIFFERENT binding constraints; pose binds runtime, court binds sessions, ball is fine. Order: ball, pose, court.
4	metadata:
5	  type: project
6	---
7	
8	Direction set 2026-08-27: recreate the existing product on mobile, perception stack
9	first. See [[parity-before-features]] for the rule, [[mobile-v1-scope-live-calls]] for
10	what it superseded.
11	
12	**The central analytical finding: the three stages are constrained by different things,
13	and conflating them produces the wrong plan.**
14	
15	- **Court — binds SESSIONS, not runtime.** Detection is **one-time calibration, not
16	  per-frame** (`docs/modules.md`), so it costs almost nothing at run time. But it is
17	  ~2,900 lines of cl
… [3364 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\docs\\evidence\\mobile-viability-audit.md"}

```
1	# Mobile viability — the port is SPLIT, not uniform (audited 2026-08-27)
2	
3	> Evidence for the `mobile-viability` row in [docs/STATE.md](../STATE.md) (Open).
4	> Read-only audit of the shipped stack against the iOS + Android on-device target.
5	> Nothing was changed to produce it. **No code was run and no phone was involved** —
6	> this is a static read of dependencies, call sites and control flow.
7	
8	**The headline: live line calls are a straightforward port that is largely done; the
9	offline match analyzer is a significant rebuild.** The concern that prompted this audit
10	— that the codebase was built assuming a PC — is directionally right but narrower than
11	feared. There are no Windows paths, no GUI calls and no exotic OpenCV usage in the
12	shipped core. What is desktop-class
… [10767 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\parity-before-features.md"}

> **tool** `WebSearch` — {"query": "BGProcessingTask iOS 18 time limit background processing task how long can it run"}

```
1	---
2	name: parity-before-features
3	description: User rule — recreate the existing product on mobile before proposing anything new; establish perception viability first, fix what is broken, only then layer features
4	metadata:
5	  type: feedback
6	---
7	
8	**Recreate the existing product on mobile before proposing new features. Establish
9	whether the perception stack (court, ball, player) can run on-device at all, fix
10	whatever is broken there, and only then move to things like scoring or live calls.**
11	
12	**Why:** given 2026-08-27, after I proposed shipping live line calls as mobile v1 because
13	they were the most-ported component. The user's reasoning is that "most ported" is not
14	"most valuable" — a phone app that does something *different* from the desktop tool means
15	one
… [1704 chars total]
```

```
Web search results for query: "BGProcessingTask iOS 18 time limit background processing task how long can it run"

Links: [{"title":"iOS Background Execution Limits: What Every Developer Must Know (2026)","url":"https://www.appsonair.com/blogs/background-execution-limits-in-ios-what-every-developer-must-know"},{"title":"iOS Background Tasks","url":"https://oneuptime.com/blog/post/2026-02-02-ios-background-tasks/view"},{"title":"BGProcessingTask | Apple Developer Documentation","url":"https://developer.apple.com/documentation/backgroundtasks/bgprocessingtask"},{"title":"Best practice: iOS background processing - Background App Refresh Task - Uy Nguyen","url":"https://uynguyen.github.io/2020/09/26/Best-practice-iOS-background-processing-Background-App-Refresh-Task/"},{"title":"iOS Background
… [2822 chars total]
```

> **tool** `WebFetch` — {"url": "https://developer.apple.com/forums/thread/690666", "prompt": "What are the CPU usage limits that kill a BGProcessingTask? Quote any Apple engineer statements about CPU percentage thresholds, …

> **tool** `WebSearch` — {"query": "iOS background task CPU limit \"80%\" 60 seconds terminated requiresExternalPower unlimited CPU"}

```
You've hit your session limit · resets 3:10pm (Asia/Manila)
```

```
Web search results for query: "iOS background task CPU limit "80%" 60 seconds terminated requiresExternalPower unlimited CPU"

Links: [{"title":"Handling Background Tasks and Multitasking in iOS Apps","url":"https://reintech.io/blog/handling-background-tasks-multitasking-ios-apps"},{"title":"Energy Efficiency Guide for iOS Apps: Work Less in the Background","url":"https://developer.apple.com/library/archive/documentation/Performance/Conceptual/EnergyGuide-iOS/WorkLessInTheBackground.html"},{"title":"Modern Backgrounds Tasks in iOS 13 - Andy Ibanez","url":"https://www.andyibanez.com/posts/modern-background-tasks-ios13/"},{"title":"iOS BackgroundTasks. As an iOS Developer, i always find that… | by Amit Thakur | Medium","url":"https://medium.com/@i.m.amit.k.thakur/ios-backgroundtasks-435a8e58
… [3267 chars total]
```

### Assistant

You've hit your session limit · resets 3:10pm (Asia/Manila)
