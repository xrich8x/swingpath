# Subagent transcript — `a830b8eb5b9d70219`

Source: `C:\Users\richm/.claude/projects\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\7168a5a5-e837-47d6-bdb6-ab1e3b940119\subagents\agent-a830b8eb5b9d70219.jsonl`
Messages: 202

Started: 2026-08-27T07:30:28.709Z
Ended:   2026-08-27T07:47:29.930Z

---

### Prompt / result

**Read these first, in this order:**
1. Your own memory: `.claude/agent-memory/researcher-agent/MEMORY.md` — backfilled 2026-08-27 from ~2 months of project history that predates you. It records what has already been investigated and rejected. Do not re-propose anything in it.
2. **pm-agent's memory: `.claude/agent-memory/pm-agent/MEMORY.md` and the topic files beside it.** The user has asked that the agents learn from each other. pm-agent produced the plan you are researching; its memory records the reasoning, the reversals and the verified findings behind it. Read it so you build on it rather than re-deriving it.
3. `docs/evidence/mobile-viability-audit.md` — the audit underneath the whole plan.

**Context.** pm-agent's iOS plan was APPROVED by the user on 2026-08-27. Your job is the four research questions it raised. This is step 2 of the project's feature workflow: your findings go back to the user for approval before any implementation starts. (Note: an earlier attempt at this exact task failed on an Opus rate limit before doing any work — you are the first real attempt, not a continuation.)

**Rulings now in force — these are settled, do not reopen them:**
- **iOS / iPadOS only, A13 or newer** (iPhone 11, SE 2nd gen, 2020 iPad Pro and newer; iOS/iPadOS 18+). Android is NOT a recording or inference device — companion only (remote control, line-call challenges). Core ML / ANE is the only inference target, and you budget to the FLOOR of the range (A13), not a recent Pro.
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

I'll start by reading the memory files and the audit that underpins the plan.

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\MEMORY.md"}

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

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\MEMORY.md"}

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

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\mobile-parity-first.md"}

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

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\ios-only-no-desktop-product.md"}

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

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\sensor-assisted-court.md"}

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

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\pm-agent\\score-layer-reopened-no-ground-truth.md"}

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

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\docs\\evidence\\mobile-viability-audit.md"}

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

> **tool** `Glob` — {"pattern": "docs/**/*.md"}

> **tool** `Glob` — {"pattern": ".claude/agent-memory/**/*.md"}

```
docs\REVIEWER.md
docs\LABELLING.md
docs\NEXT_FIXES.md
docs\RESEARCH_BRIEF_indoor_shell_courts.md
docs\REVIEW-2026-08-16.md
docs\TRAPS.md
docs\archive\HANDOFF.md
docs\archive\resolved\court-auto-detection-2.md
docs\archive\resolved\court-auto-detection.md
docs\archive\resolved\processing-60-fps-clips-at-full-rate.md
docs\archive\resolved\rally-segmentation-score.md
docs\archive\resolved\speed-coverage.md
docs\archive\resolved\whether-the-5-6-pt-recall-gain.md
docs\archive\sessions\README.md
docs\archive\sessions\SESSION_A_lens_and_watchdog.md
docs\archive\sessions\SESSION_B_serve_stats.md
docs\archive\sessions\SESSION_C_flow_polish.md
docs\archive\sessions\SESSION_D_highlights.md
docs\archive\sessions\SESSION_E_ball_push.md
docs\archive\sessions\SESSION_F_false_fire.md
docs\archive\sessions
… [4997 chars total]
```

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

> **tool** `Grep` — {"pattern": "yolo11|yolo11m|pose_model|imgsz", "path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\backend\\swingvision", "output_mode": "content", "-n": true, "head_limit": 40}

```
backend\swingvision\pose.py:9:Weights (yolo11n-pose.pt) download automatically on first use.
backend\swingvision\pose.py:56:    "fast": ("yolo11m-pose.pt", 1280),
backend\swingvision\pose.py:57:    "balanced": ("yolo11m-pose.pt", 1600),
backend\swingvision\pose.py:58:    "accurate": ("yolo11x-pose.pt", 1920),
backend\swingvision\pose.py:74:    `weights`/`imgsz` to override it. Default is "fast" — analysis throughput
backend\swingvision\pose.py:83:        imgsz=None,
backend\swingvision\pose.py:86:        preset_weights, preset_imgsz = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["fast"])
backend\swingvision\pose.py:88:        self.imgsz = imgsz or preset_imgsz
backend\swingvision\pose.py:104:            frame, conf=self.conf, device=self.device, imgsz=self.imgsz, verbose=False
backend\swin
… [1237 chars total]
```

> **tool** `WebSearch` — {"query": "BGProcessingTask iOS 18 time limit background execution real world minutes"}

```
Web search results for query: "BGProcessingTask iOS 18 time limit background execution real world minutes"

Links: [{"title":"iOS Background Execution Limits: What Every Developer Must Know (2026)","url":"https://www.appsonair.com/blogs/background-execution-limits-in-ios-what-every-developer-must-know"},{"title":"Best practice: iOS background processing - Background App Refresh Task - Uy Nguyen","url":"https://uynguyen.github.io/2020/09/26/Best-practice-iOS-background-processing-Background-App-Refresh-Task/"},{"title":"iOS Background Processing Mastery: Tasks, Limits, and Real-World Patterns - The Sheldon Wang Site","url":"https://sheldonwangrjt.github.io/posts/2025/06/ios-background-processing/"},{"title":"developer.apple.com","url":"https://developer.apple.com/forums/thread/766206"},{"ti
… [2653 chars total]
```

> **tool** `WebFetch` — {"url": "https://developer.apple.com/forums/thread/766206", "prompt": "What does this thread say about BGProcessingTask execution time limits, scheduling, and kill conditions on iOS 17/18?"}

> **tool** `WebSearch` — {"query": "\"BGProcessingTask\" expiration handler how long does it actually run CPU intensive iOS 18"}

```
# BGProcessingTaskRequest Execution Behavior on iOS

Based on this Apple Developer Forums thread, here are the key points about `BGProcessingTaskRequest` execution:

## Key Findings

### No Guaranteed Execution Schedule
- **BGProcessingTaskRequest is NOT guaranteed to run on any particular schedule.** The `earliestBeginDate` is only a minimum threshold, not a guarantee.
- According to the DTS Engineer response: *"A background processing task (created with `BGProcessingTaskRequest`) is not guaranteed to run on any particular schedule. Rather, the schedule is an implementation detail."*

### Actual Execution Pattern
- These tasks typically run **overnight**, not on the frequent schedule developers might expect
- Execution can be delayed significantly (sometimes 1+ hours instead of the reques
… [1675 chars total]
```

```
Web search results for query: ""BGProcessingTask" expiration handler how long does it actually run CPU intensive iOS 18"

Links: [{"title":"Swift iOS BackgroundTasks framework — Background App Refresh in 4 Steps | by Myrick Chow | ITNEXT","url":"https://itnext.io/swift-ios-13-backgroundtasks-framework-background-app-refresh-in-4-steps-3da32e65bc3d?gi=cd943b2764f3"},{"title":"iOS Background Tasks","url":"https://oneuptime.com/blog/post/2026-02-02-ios-background-tasks/view"},{"title":"Background Tasks | Apple Developer Forums","url":"https://developer.apple.com/forums/tags/backgroundtasks?page=3&sortBy=newest"},{"title":"iOS Background Processing Mastery: Tasks, Limits, and Real-World Patterns - The Sheldon Wang Site","url":"https://sheldonwangrjt.github.io/posts/2025/06/ios-background-proce
… [2871 chars total]
```

> **tool** `WebSearch` — {"query": "BGContinuedProcessingTask iOS 26 long running background work Live Activity progress limits"}

> **tool** `WebFetch` — {"url": "https://developer.apple.com/forums/thread/818873", "prompt": "What does this thread say about BGContinuedProcessingTask expiration reasons, CPU/thermal limits, GPU/ANE usage, and how long it …

```
# Summary of BGContinuedProcessingTask Discussion

Based on the thread content, here's what it reveals:

## Expiration Reasons
The developer identified that `expirationHandler` may be triggered by multiple reasons:
- User tapping Stop in the Live Activity
- Time expiration (task duration limit)
- System resource pressure (CPU, memory, battery)
- Other system-driven termination cases

## Key Problem
**There is no official way to distinguish between these stop reasons.** The developer explicitly stated:

> "However, at the moment, it is difficult or practically impossible to distinguish these cases reliably."

## Duration Expectations
For long-running work (30 minutes to 1 hour):
- The developer reported that `expirationHandler` was invoked **irregularly**
- No clear or consistent pattern co
… [1564 chars total]
```

```
Web search results for query: "BGContinuedProcessingTask iOS 26 long running background work Live Activity progress limits"

Links: [{"title":"Background Tasks | Apple Developer Forums","url":"https://developer.apple.com/forums/tags/backgroundtasks?page=5&sortBy=lastUpdated"},{"title":"Finish tasks in the background - WWDC25 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2025/227/"},{"title":"iOS 26 + BGContinuedProcessingTask","url":"https://developer.apple.com/forums/thread/807957"},{"title":"iOS Background Execution Limits | Apple Developer Forums","url":"https://developer.apple.com/forums/thread/685525"},{"title":"Mastering iOS 26 Background Tasks: A Complete Guide for Smarter Apps | by Himali Marasinghe | Medium","url":"https://medium.com/swlh/mastering
… [2849 chars total]
```

> **tool** `WebFetch` — {"url": "https://developer.apple.com/videos/play/wwdc2025/227/", "prompt": "Summarize everything about BGContinuedProcessingTask: how long it runs, submission rules, GPU resource opt-in, device suppor…

> **tool** `WebSearch` — {"query": "BGContinuedProcessingTaskRequest resources gpu opt-in \"GPU\" background task iOS 26 supported devices"}

```
Web search results for query: "BGContinuedProcessingTaskRequest resources gpu opt-in "GPU" background task iOS 26 supported devices"

Links: [{"title":"BackgroundTasks iOS xcode26.0 b1 · dotnet/macios Wiki","url":"https://github.com/dotnet/macios/wiki/BackgroundTasks-iOS-xcode26.0-b1"},{"title":"Background Tasks in iOS | Coconote","url":"https://coconote.app/notes/898b6b2c-932d-42e8-a30e-84ace877a157"},{"title":"swift-ios-skills/skills/background-processing/SKILL.md at main · dpearson2699/swift-ios-skills","url":"https://github.com/dpearson2699/swift-ios-skills/blob/main/skills/background-processing/SKILL.md"},{"title":"BGContinuedProcessingTask | Apple Developer Documentation","url":"https://developer.apple.com/documentation/backgroundtasks/bgcontinuedprocessingtask"},{"title":"BGContinue
… [2628 chars total]
```

```
# BGContinuedProcessingTask Summary

## Overview
`BGContinuedProcessingTask` is a new API in iOS and iPadOS 26 that allows apps to continue user-initiated work in the background after the app is backgrounded, with system UI showing progress.

## Runtime Duration
The video doesn't specify an exact time limit, but emphasizes:
- Tasks must make **measurable progress** and report it regularly
- **Tasks that don't report progress will be expired** by the system
- If progress is slower than expected, the system prompts the user to continue
- The system may interrupt tasks early if device conditions change

## Submission Rules

**Must be user-initiated:**
```swift
// Explicit action required (button tap, gesture)
let request = BGContinuedProcessingTaskRequest(
    identifier: "com.colorfeed.wwdc2
… [3088 chars total]
```

> **tool** `WebFetch` — {"url": "https://developer.apple.com/forums/thread/794072", "prompt": "Which devices support background GPU access for BGContinuedProcessingTask? Any Apple engineer answer about device list, A-series …

> **tool** `WebSearch` — {"query": "iOS background Core ML Neural Engine allowed in background app suspended ANE inference background task"}

```
# Background GPU Access Device Support

Based on the Apple Developer Forums discussion, **there is no published list of devices that support background GPU access**. Here's what you need to know:

## How to Check Device Support

The only way to determine if a device supports background GPU access is to check at runtime:

```swift
BGTaskScheduler.supportedResources.contains(.gpu)
```

If this returns `false`, the device does not support background GPU access, even with the proper entitlements configured.

## Key Points

1. **No Device List Available**: Apple has not published a definitive list of which devices support this feature. The feature is still evolving and "transcends GPU usage."

2. **Requirements**:
   - The `Background GPU Access` entitlement is required
   - Device must report 
… [1549 chars total]
```

```
Web search results for query: "iOS background Core ML Neural Engine allowed in background app suspended ANE inference background task"

Links: [{"title":"The Tiered Inference Strategy: Solving the iOS LLM Background Crash | by Rajesh Naga Nekkanti | Medium","url":"https://medium.com/@nnrajesh3006/the-tiered-inference-strategy-solving-the-ios-llm-background-crash-7e1195453188"},{"title":"neural-engine/docs/is-model-using-ane.md at master · hollance/neural-engine","url":"https://github.com/hollance/neural-engine/blob/master/docs/is-model-using-ane.md"},{"title":"Deploying Transformers on the Apple Neural Engine - Apple Machine Learning Research","url":"https://machinelearning.apple.com/research/neural-engine-transformers"},{"title":"Stop Wasting GPU Cycles! CoreML-LLM Unlocks ANE for Insane 
… [3255 chars total]
```

> **tool** `WebSearch` — {"query": "Metal command buffer background app terminated iOS \"IOGPUCommandQueue\" Core ML MLComputeUnits background crash"}

> **tool** `WebFetch` — {"url": "https://medium.com/@nnrajesh3006/the-tiered-inference-strategy-solving-the-ios-llm-background-crash-7e1195453188", "prompt": "What exactly does this say about running Core ML inference in the…

```
The server returned HTTP 403 Forbidden.

The response body was not retrieved. If this URL requires authentication, use an authenticated tool (e.g. `gh` for GitHub, or an MCP-provided fetch tool) instead of WebFetch.
```

```
Web search results for query: "Metal command buffer background app terminated iOS "IOGPUCommandQueue" Core ML MLComputeUnits background crash"

Links: [{"title":"gpu::check_error() throws unhandled C++ exception on Metal command buffer error, crashing the process · Issue #3224 · ml-explore/mlx","url":"https://github.com/ml-explore/mlx/issues/3224"},{"title":"Metal background execution error · Issue #3172 · maplibre/maplibre-native","url":"https://github.com/maplibre/maplibre-native/issues/3172"},{"title":"iOS 26.x – Screen Flash, Then Permanent Black Screen (App Doesn’t Crash – Metal Device Lost?) - Unity Engine - Unity Discussions","url":"https://discussions.unity.com/t/ios-26-x-screen-flash-then-permanent-black-screen-app-doesn-t-crash-metal-device-lost/1695690"},{"title":"Use-after-free
… [3020 chars total]
```

> **tool** `WebSearch` — {"query": "Core ML background inference \"cpuAndNeuralEngine\" works in background GPU blocked workaround"}

> **tool** `WebSearch` — {"query": "iOS Photos on-device analysis background \"plugged in and locked\" face recognition scene analysis progress"}

```
Web search results for query: "Core ML background inference "cpuAndNeuralEngine" works in background GPU blocked workaround"

Links: [{"title":"Optimize your Core ML usage - WWDC22 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2022/10027/"},{"title":"Stop Wasting GPU Cycles! CoreML-LLM Unlocks ANE for Insane On-Device Speed - BrightCoding","url":"https://www.blog.brightcoding.dev/2026/05/23/stop-wasting-gpu-cycles-coreml-llm-unlocks-ane-for-insane-on-device-speed"},{"title":"neural-engine/docs/unsupported-layers.md at master · hollance/neural-engine","url":"https://github.com/hollance/neural-engine/blob/master/docs/unsupported-layers.md"},{"title":"Example of speeding up inference of PyTorch models on M1 via Core ML tools - Solyanka by DrSleep","url":"https
… [2771 chars total]
```

```
Web search results for query: "iOS Photos on-device analysis background "plugged in and locked" face recognition scene analysis progress"

Links: [{"title":"iPhone Photos Not Recognizing Faces? 7 Real Fixes for 2026","url":"https://fone.tips/iphone-photos-not-recognizing-faces/"},{"title":"Why Is My iPhone 16 Pro Photos App Running in Background?","url":"https://www.justanswer.com/software/rs6ei-can-t-understand-photos-app-running-20-50-min.html"},{"title":"How to Fix Apple Photos Face Recognition (People Album Not Working) | Real Web","url":"https://real4web.com/en/how-to-fix-apple-photos-face-recognition-people-album-not-working/"},{"title":"How to Fix Apple Photos Not Recognizing Faces","url":"https://www.macobserver.com/tips/how-to/apple-photos-not-recognizing-faces/"},{"title":"What i
… [2793 chars total]
```

> **tool** `WebSearch` — {"query": "SwingVision iPhone on-device processing real time during recording supported devices requirements overheating"}

> **tool** `WebSearch` — {"query": "iOS app long video processing keep screen on foreground \"idle timer\" thermal throttling ML export hours pattern"}

```
Web search results for query: "SwingVision iPhone on-device processing real time during recording supported devices requirements overheating"

Links: [{"title":"What is the SwingVision AI app and how can it improve your tennis?","url":"https://www.pocket-lint.com/apps/news/apple/161241-what-is-the-swingvision-ai-app-how-does-it-work-how-can-it-improve-your-tennis/"},{"title":"SwingVision - ITA #WeAreCollegeTennis","url":"https://wearecollegetennis.com/swingvision/"},{"title":"Try Swingvision for free - Tennisnerd.net - real-time video analysis","url":"https://www.tennisnerd.net/news/try-swingvision-for-free/24680"},{"title":"SwingVision Brings Its Award-Winning AI To Pickleball | Pickleball Union","url":"https://pickleballunion.com/swingvision-brings-its-award-winning-ai-to-pickleball/"},{
… [2340 chars total]
```

```
Web search results for query: "iOS app long video processing keep screen on foreground "idle timer" thermal throttling ML export hours pattern"

Links: [{"title":"You Can Turn Your Live Photos Into Long Exposures Loop - LifeTips","url":"https://lifetips.alibaba.com/tech-efficiency/you-can-turn-your-live-photos-into-long-exposures-loop"},{"title":"What Happens When You Max Out an iPhone: Thermal Throttling in Real-Time AR | HackerNoon","url":"https://hackernoon.com/what-happens-when-you-max-out-an-iphone-thermal-throttling-in-real-time-ar"},{"title":"Finish tasks in the background - WWDC25 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2025/227/"},{"title":"Disable/Enable the iOS idle times to prevent screen dimming · GitHub","url":"https://gist.github.com/da
… [2996 chars total]
```

> **tool** `WebFetch` — {"url": "https://developer.apple.com/forums/thread/675166", "prompt": "What does this say about BGProcessingTask being killed for CPU utilization (signal 9 / CPU Monitor), the thresholds, and how to a…

> **tool** `WebFetch` — {"url": "https://developer.apple.com/forums/thread/685525", "prompt": "Summarize Quinn's \"iOS Background Execution Limits\" — the categories of background execution, which ones allow sustained CPU wo…

```
# BGProcessingTask CPU Termination Issue

Based on this forum discussion, here's what's revealed about BGProcessingTask being killed for CPU utilization:

## The Problem

**BGProcessingTask is being terminated by CPU Monitor** despite it being designed to disable CPU limits. The developer's process was killed with:
- **Signal 9** (process termination)
- **Reason**: CPU usage exceeded 80% average over 60 seconds
- **Actual usage**: 97% CPU average (48 seconds over 50 seconds)

## Expected vs. Actual Behavior

**Expected** (per Apple's WWDC 2019 documentation):
- BGProcessingTask should disable CPU Monitor for the duration
- Allow full CPU utilization while device is plugged in

**Actual**: CPU Monitor still enforces an 80% CPU threshold over 60 seconds, killing the process after ~1 minute


… [1653 chars total]
```

```
# iOS Background Execution Limits Summary

## Core Principle
**iOS suspends apps shortly after they move to the background.** There is no general-purpose mechanism for running code continuously, at specific times, or at guaranteed intervals.

## Categories of Background Execution

### 1. **Special-Purpose Mechanisms** (Task-Specific)
These are designed for specific use cases and **do not allow sustained CPU work**:
- **Audio background mode** – for music players
- **AlarmKit** – for timer apps
- **AVFoundation download support** – for video players
- Local notifications – for time-based alerts

### 2. **General-Purpose Mechanisms**

| Mechanism | Use Case | Sustained Work? |
|-----------|----------|-----------------|
| **Silent Push Notifications** | Resume app in response to server events
… [2193 chars total]
```

> **tool** `WebSearch` — {"query": "SwingVision upload existing video processing cloud \"upload\" analyze video not recorded in app"}

> **tool** `WebSearch` — {"query": "iOS app on-device video ML processing hours \"keep the app open\" progress screen user experience transcription upscaling"}

```
Web search results for query: "SwingVision upload existing video processing cloud "upload" analyze video not recorded in app"

Links: [{"title":"GitHub - therealfrankshaw/swingvision-transcoder: Change the video format, to be swingvision compatible · GitHub","url":"https://github.com/therealfrankshaw/swingvision-transcoder"},{"title":"How to Import Videos on Swingvision | TikTok","url":"https://www.tiktok.com/discover/how-to-import-videos-on-swingvision"},{"title":"Analyze my tennis post-game videos from a Mac - Analytics, Digital and Sports","url":"https://bubbletao.com/2020/12/31/analyze-my-tennis-post-game-videos-from-a-mac/"},{"title":"SwingVision Review: Boost Your Tennis with AI","url":"https://techinthesun.com/swingvision/"},{"title":"Import Existing Footage to SwingVision","url":"h
… [2604 chars total]
```

```
Web search results for query: "iOS app on-device video ML processing hours "keep the app open" progress screen user experience transcription upscaling"

Links: [{"title":"Finish tasks in the background - WWDC25 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2025/227/"},{"title":"Advances in App Background Execution - WWDC19 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2019/707/"},{"title":"Explore the machine learning development experience - WWDC22 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2022/10017/"},{"title":"Progress Indicators - Controls - iOS - Human Interface Guidelines - Apple Developer","url":"https://developers.apple.com/design/human-interface-guidelines/ios/controls/progress-
… [3013 chars total]
```

> **tool** `WebFetch` — {"url": "https://swing.vision/guides/import-existing-footage", "prompt": "Does SwingVision process imported footage on-device or in the cloud? How long does processing take, what does it tell the user…

> **tool** `WebSearch` — {"query": "SwingVision imported video processing time \"processing\" on device or cloud how long takes app open reddit"}

```
I cannot answer your questions about SwingVision's processing location, speed, output, or app requirements based on the provided content. The webpage excerpt only contains the product name and tagline ("SwingVision: AI Stats for Tennis & Pickleball") with no technical details about how the service operates.

To get accurate information, you would need to consult SwingVision's full documentation, FAQ, or contact their support team directly.
```

```
Web search results for query: "SwingVision imported video processing time "processing" on device or cloud how long takes app open reddit"

Links: [{"title":"apps.apple.com","url":"https://apps.apple.com/us/app/-/id6447277080"},{"title":"Compare SwingVision vs VideObserver","url":"https://www.cbinsights.com/compare/swingvision-vs-videobserver"},{"title":"SwingVision Alternatives","url":"https://alternativeto.net/software/swingvision/?p=2"},{"title":"apps.apple.com","url":"https://apps.apple.com/app/id1381051713"},{"title":"SwingVision icon","url":"https://alternativeto.net/software/swingvision/about"},{"title":"building swingvision an ai powered","url":"https://thenextnext.substack.com/p/building-swingvision-an-ai-powered"},{"title":"Compare SwingVision vs WGP Media","url":"https://www.cbin
… [4849 chars total]
```

> **tool** `WebSearch` — {"query": "Ultralytics YOLO11 pose CoreML export benchmark iPhone Neural Engine ms latency"}

> **tool** `WebSearch` — {"query": "YOLO CoreML export ANE fallback CPU \"Neural Engine\" ops not supported nms pose export issue"}

```
Web search results for query: "Ultralytics YOLO11 pose CoreML export benchmark iPhone Neural Engine ms latency"

Links: [{"title":"CoreML Export for YOLO26 Models | Ultralytics Docs","url":"https://docs.ultralytics.com/integrations/coreml"},{"title":"Best iOS Object Detection Models: RF-DETR for On-Device ...","url":"https://blog.roboflow.com/best-ios-object-detection-models/"},{"title":"YOLO26: Key Architectural Enhancements and Performance Benchmarking for Real-Time Object Detection","url":"https://arxiv.org/html/2509.25164v3"},{"title":"GitHub - ultralytics/yolo-ios-app: Ultralytics YOLO iOS App source code for running YOLO in your own iOS apps 🌟","url":"https://github.com/ultralytics/yolo-ios-app"},{"title":"Ultralytics YOLO Evolution: An Overview of YOLO26, YOLO11, YOLOv8, and YOLOv5 
… [2971 chars total]
```

```
Web search results for query: "YOLO CoreML export ANE fallback CPU "Neural Engine" ops not supported nms pose export issue"

Links: [{"title":"CoreML Export for YOLO26 Models | Ultralytics Docs","url":"https://docs.ultralytics.com/integrations/coreml"},{"title":"Export YOLO11-pose to onnx with NMS · Issue #17149 · ultralytics/ultralytics","url":"https://github.com/ultralytics/ultralytics/issues/17149"},{"title":"Questions about new NMS Export for Detect, Segment, Pose and OBB YOLO · Issue #19213 · ultralytics/ultralytics","url":"https://github.com/ultralytics/ultralytics/issues/19213"},{"title":"when exporting to coreml (mlmodel format) NMS is not added. · Issue #7011 · ultralytics/yolov5","url":"https://github.com/ultralytics/yolov5/issues/7011"},{"title":"Question about converting yolov8
… [2617 chars total]
```

> **tool** `WebFetch` — {"url": "https://docs.ultralytics.com/integrations/coreml", "prompt": "What does it say about CoreML export for pose models, int8/fp16 quantization, NMS support, ANE support, and any device benchmark …

> **tool** `WebFetch` — {"url": "https://github.com/ultralytics/yolo-ios-app", "prompt": "Any benchmark table of FPS by iPhone model and YOLO model size? What input resolution do they use? Any mention of pose, quantization, …

```
# CoreML Export for YOLO26 Models: Key Insights

**Pose Model Support:**
Pose estimation is among the seven supported tasks for CoreML export, with "NMS ML Programs use FP16 (for Xcode preview, and required by segment and pose)."

**Quantization Options:**
The exporter supports multiple precision levels: INT8, FP16, and FP32. The documentation notes that "The official Ultralytics app models ship as INT8, which minimizes download size," while FP16 serves as "a conservative alternative with essentially no accuracy loss."

**NMS Support:**
NMS embedding differs between model generations. For YOLO26, "the exported graph already emits final detections" without requiring NMS, but for earlier versions like YOLO11, the `nms=True` option embeds suppression into the model.

**Neural Engine Support:*
… [1305 chars total]
```

```
# Performance Benchmarks for Ultralytics YOLO iOS

Based on the provided content, there is **no detailed FPS benchmark table by iPhone model and YOLO size** included in this README.

However, the document does mention:

**Performance reference**: "Camera-rate (~30 FPS) real-time inference on recent iPhones — see docs/performance.md for on-device profiling"

The README indicates that comprehensive performance metrics exist in a separate `docs/performance.md` file, but that specific document isn't included in the provided content.

**What is confirmed:**
- The SDK runs on Apple's Neural Engine and GPU
- It supports both YOLO26 (NMS-free) and YOLO11 models
- Input resolutions vary: "224 cls; 640 others" for Core ML exports
- Pose estimation is a supported task
- Models use int8 quantization f
… [1119 chars total]
```

> **tool** `WebFetch` — {"url": "https://raw.githubusercontent.com/ultralytics/yolo-ios-app/main/docs/performance.md", "prompt": "Report all benchmark numbers: device, chip, model, task, input size, precision, latency/fps, c…

> **tool** `WebSearch` — {"query": "A13 Bionic Neural Engine 5 TOPS vs A17 Pro 35 TOPS A16 17 TOPS comparison table"}

```
# Summary of Ultralytics YOLO iOS SDK Real-Time Performance

## Key Findings

The document provides comprehensive benchmarking data for the Ultralytics YOLO iOS SDK running on iPhone 17 Pro with A19 Pro chip. Here are the critical takeaways:

**Device Performance (Ground Truth):**
- Detection inference: 3.2 ms (with CPU + Neural Engine)
- Segmentation: 4.8 ms
- Classification: 1.9 ms
- The page emphasizes that "host benchmarks predict the wrong winner — always confirm on device"

**Core Insight on Frame Rate:**
The authors demonstrate that "frame rate is camera-bound, not inference-bound." At ≤13 ms per frame, the processing pipeline completes well before the camera delivers the next frame, meaning faster inference yields latency and power benefits rather than increased FPS.

**Preprocessi
… [1523 chars total]
```

```
Web search results for query: "A13 Bionic Neural Engine 5 TOPS vs A17 Pro 35 TOPS A16 17 TOPS comparison table"

Links: [{"title":"Apple A17 Pro vs A16 Bionic: Which iPhone chipset is better?","url":"https://pocketnow.com/apple-a17-pro-vs-a16-bionic/"},{"title":"A17 Pro vs A16 Bionic","url":"https://9to5mac.com/2024/06/12/a17-pro-vs-a16-bionic-comparison/"},{"title":"neural-engine/docs/supported-devices.md at master · hollance/neural-engine","url":"https://github.com/hollance/neural-engine/blob/master/docs/supported-devices.md"},{"title":"What’s wrong with Apple A17 Pro and A18 series | by John William Archer | Medium","url":"https://medium.com/@willrarcher/whats-wrong-with-apple-a17-pro-and-a18-series-3b3e3cb4a714"},{"title":"Apple A17 Pro vs Apple A13 Bionic - Benchmark, comparison and d
… [2582 chars total]
```

> **tool** `WebFetch` — {"url": "https://github.com/hollance/neural-engine/blob/master/docs/supported-devices.md", "prompt": "List the Neural Engine generations, cores, TOPS per chip especially A12/A13/A14, and any notes on …

> **tool** `WebSearch` — {"query": "Apple Neural Engine int8 compute support only A17 Pro M4 older ANE fp16 weight quantization decompressed coremltools"}

```
# Neural Engine Generations: A12, A13, A14 Comparison

## A12 Bionic
- **Cores:** 8
- **Performance:** "up to 5 trillion operations per second"
- **Notes:** First generation usable by Core ML (iOS 12+). Apple claimed "9 times faster at 1/10th the energy usage compared to the A11."

## A13 Bionic
- **Cores:** 8
- **Performance:** 20% faster than A12, 15% lower power consumption
- **Additional feature:** Performance cores include machine learning accelerators (AMX blocks) enabling matrix multiplications up to 6x faster than A12's CPU

## A14 Bionic
- **Cores:** 16
- **Performance:** "11 trillion operations per second" (double previous generation speed)
- **Additional features:** Second-generation AMX blocks for CPU-based ML acceleration, including on Efficiency Cores

---

**Note:** The docu
… [1015 chars total]
```

```
Web search results for query: "Apple Neural Engine int8 compute support only A17 Pro M4 older ANE fp16 weight quantization decompressed coremltools"

Links: [{"title":"need help about both model weight and activation quantization with only a float32 mlmodel · Issue #2227 · apple/coremltools","url":"https://github.com/apple/coremltools/issues/2227"},{"title":"Performance — Guide to Core ML Tools - Apple","url":"https://apple.github.io/coremltools/docs-guides/source/opt-quantization-perf.html"},{"title":"Using Mixed Precision in Core ML. This guide explains how to improve… | by Takehiko TERADA | ailia Tech BLOG (EN) | Medium","url":"https://medium.com/axinc-ai/using-mixed-precision-in-core-ml-77c2428ba728"},{"title":"Overview — Guide to Core ML Tools","url":"https://apple.github.io/coremltoo
… [3104 chars total]
```

> **tool** `WebFetch` — {"url": "https://apple.github.io/coremltools/docs-guides/source/opt-quantization-perf.html", "prompt": "What does Apple say about int8 vs fp16 latency on Neural Engine across hardware generations? Any…

> **tool** `WebSearch` — {"query": "quantization accuracy loss pose estimation keypoint int8 PTQ heatmap degradation mAP OKS"}

```
# Apple's Statement on int8 vs fp16 Performance

According to the documentation, Apple highlights generational differences in Neural Engine capabilities:

**Newer Hardware Advantage**: "In newer hardware with A17 Pro or M4 chips, such as iPhone 15 Pro, there is increased throughput possible for int8-int8 compute on Neural Engine, compared to previous versions."

**Implicit Older Hardware Limitation**: The document contrasts this with older chips, implying that previous generations lack this enhanced int8 throughput, though it doesn't explicitly state they gain "nothing."

**Accuracy & Performance Data**: The benchmarks show concrete examples—ResNet50 with weight & activation quantization maintained 76.80% accuracy (vs 76.14% baseline) while reducing latency from 1.52ms to 0.94ms on iPhone 
… [1050 chars total]
```

```
Web search results for query: "quantization accuracy loss pose estimation keypoint int8 PTQ heatmap degradation mAP OKS"

Links: [{"title":"YOLO-Pose: Enhancing YOLO for Multi Person Pose Estimation Using Object   Keypoint Similarity Loss","url":"https://arxiv.org/pdf/2204.06806"},{"title":"AHPPEBot: Autonomous Robot for Tomato Harvesting based on Phenotyping   and Pose Estimation","url":"https://arxiv.org/pdf/2405.06959"},{"title":"PTQAT: A Hybrid Parameter-Efficient Quantization Algorithm for 3D Perception Tasks","url":"https://arxiv.org/html/2508.10557"},{"title":"Yolo Pose Output Splitting for Full Integer Int8 Accuracy · Issue #21625 · ultralytics/ultralytics","url":"https://github.com/ultralytics/ultralytics/issues/21625"},{"title":"MiLSD: A Micro Line-Segment Detector for Resource-C
… [3127 chars total]
```

> **tool** `WebFetch` — {"url": "https://github.com/ultralytics/ultralytics/issues/21625", "prompt": "What accuracy loss is reported for int8 quantization of YOLO pose models, and what is the cause (output head structure)? A…

> **tool** `WebSearch` — {"query": "ultralytics coreml export int8 \"quantize_weights\" weight-only palettization exporter.py nbits 8"}

```
# Int8 Quantization Accuracy Loss for YOLO Pose Models

The GitHub issue does not provide specific numerical data on accuracy loss from int8 quantization of YOLO pose models.

However, the issue identifies the **root cause** as the current unified output structure. The user explains that the model combines keypoints, bounding boxes, and confidence scores in a single output [batch, nKeypoints+5, nFeatures], which causes problems during post-training quantization (PTQ).

The underlying problem stems from mismatched characteristics:

- **Statistical distributions differ**: Landmarks cluster regionally, bounding box coordinates spread uniformly, and confidence scores cluster bimodally
- **Precision requirements vary**: Landmarks need high precision, while confidence scores are more critical fo
… [1202 chars total]
```

```
Web search results for query: "ultralytics coreml export int8 "quantize_weights" weight-only palettization exporter.py nbits 8"

Links: [{"title":"CoreML Export for YOLO26 Models | Ultralytics Docs","url":"https://docs.ultralytics.com/integrations/coreml"},{"title":"Export for Deployment | Train your first YOLO model | Ultralytics Academy","url":"https://academy.ultralytics.com/courses/train-your-first-yolo/export-for-deployment"},{"title":"Model Export with Ultralytics YOLO | Ultralytics Docs","url":"https://docs.ultralytics.com/modes/export"},{"title":"ultralytics/docs/en/modes/export.md at main · ultralytics/ultralytics","url":"https://github.com/ultralytics/ultralytics/blob/main/docs/en/modes/export.md"},{"title":"Exporting to tflite with int8 quantization for edge deployment - Support
… [2637 chars total]
```

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\docs\\evidence\\the-far-player-is-a-detection-problem.md"}

```
1	# The far player is a DETECTION problem on the target footage
2	
3	> Evidence for the `the-far-player-is-a-detection-problem` row in [docs/STATE.md](../STATE.md) (Open).
4	> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.
5	
6	**Settled 2026-08-17 across all three calibrated clips, correcting the sharper-sounding claim first filed here.** `--far-player-rescue` does recover far-player frames the shipped guard then deletes — 37.2% -> 0.0% on yt_rally2 via depth-blind pixel radii — but fixing the guard (`body_relative`, see the dead-end table) changes the outcome on **1 of 3 clips only**. On yt_match40 the far player is detected on **14.5%** of frames and on am_hard_utr **26.7%**; both are under the 50% a path integral needs regardless of any filter, and yt_match40 is un
… [1565 chars total]
```

> **tool** `WebSearch` — {"query": "Core ML Neural Engine large input resolution tensor size limit falls back to GPU segmentation 1280 model ANE tiling memory"}

```
Web search results for query: "Core ML Neural Engine large input resolution tensor size limit falls back to GPU segmentation 1280 model ANE tiling memory"

Links: [{"title":"Exact Tile-Based Segmentation Inference for Images Larger than GPU Memory","url":"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10914126/"},{"title":"Dynamic variable bit width neural processor","url":"https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11593628"},{"title":"Dynamic variable bit width neural processor","url":"https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12050987"},{"title":"CUDA Cores Vs Tensor Cores: Which One Powers ML Better?","url":"https://acecloud.ai/blog/cuda-cores-vs-tensor-cores/"},{"title":"On Device Llama 3.1 with Core ML - Apple Machine Learning Research","url
… [3210 chars total]
```

> **tool** `WebSearch` — {"query": "Apple Neural Engine sustained throughput thermal throttling measurement continuous inference minutes degradation iPhone"}

> **tool** `WebFetch` — {"url": "https://arxiv.org/pdf/2606.22283", "prompt": "This is \"Apple Neural Engine: Architecture, Programming, and Performance\". Report: measured throughput figures by chip generation, any sustaine…

```
# Apple Neural Engine Report Analysis

I've reviewed the PDF metadata for "Apple Neural Engine: Architecture, Programming, and Performance" by Spencer H. Bryngelson (arXiv:2606.22283). However, the provided content consists almost entirely of PDF structural data (object definitions, font specifications, page references) rather than the actual document text.

Based on the available metadata, I can confirm this is a 302-page academic paper covering ANE architecture, programming, and performance. However, **I cannot extract the specific technical details you requested** without access to the actual document content, including:

- Measured throughput figures by chip generation
- Sustained/thermal measurements
- Int8 vs FP16 behavior comparisons
- Operator coverage and fallback trigger informat
… [1443 chars total]
```

```
Web search results for query: "Apple Neural Engine sustained throughput thermal throttling measurement continuous inference minutes degradation iPhone"

Links: [{"title":"iPhone 17 - Argmax","url":"https://www.argmaxinc.com/blog/iphone-17-on-device-inference-benchmarks"},{"title":"LLM Inference at the Edge: Mobile, NPU, and GPUPerformance Efficiency Trade-offs Under Sustained Load","url":"https://arxiv.org/html/2603.23640v2"},{"title":"Understanding Large Language Models in Your Pockets: Performance Study on COTS Mobile Devices","url":"https://arxiv.org/pdf/2410.03613"},{"title":"LLM Inference at the Edge: Mobile, NPU, and GPU Performance Efficiency Trade-offs Under Sustained Load","url":"https://arxiv.org/pdf/2603.23640"},{"title":"On neural networks and CPU throttling in iPhones | by Geo
… [2840 chars total]
```

> **tool** `WebFetch` — {"url": "https://www.argmaxinc.com/blog/iphone-17-on-device-inference-benchmarks", "prompt": "Report any ANE benchmark numbers across iPhone generations, especially older devices, sustained vs peak th…

> **tool** `WebFetch` — {"url": "https://arxiv.org/html/2603.23640v2", "prompt": "Report the sustained-load thermal findings: which devices, which accelerator (NPU/ANE vs GPU vs CPU), how throughput degrades over time, and a…

```
# iPhone 17 ANE Benchmark Analysis

## Key ANE Performance Data

The article provides limited ANE (Apple Neural Engine) benchmark comparisons across generations:

**Peak Throughput:**
- iPhone 16 Pro ANE: "15+ Tflops/s on the iPhone 16 Pro Neural Engine, near-peak utilization of the 17.5 Tflops/s theoretical max throughput"
- iPhone 17 lineup ANE improvement: Only "1-1.15x" speedup versus 2.5-3.1x GPU gains

**Workload Performance (Burst File Transcription):**
The neural processing unit showed marginal gains on Nvidia Parakeet v3 across the new lineup, despite Apple's marketed 25% improvement.

## Sustained vs Peak Behavior

The report distinguishes these scenarios:
- **Burst workloads** (Workload 1): Peak compute measurement using speech-to-text
- **Sustained real-time transcription** (Wo
… [1376 chars total]
```

```
# Sustained-Load Thermal Findings from Edge LLM Inference Study

## Devices and Accelerators Tested

The benchmark evaluated four platforms:
- **iPhone 16 Pro** (Apple A18 Pro GPU, 6-core)
- **Samsung Galaxy S24 Ultra** (Snapdragon 8 Gen 3, Adreno 750 GPU)
- **Raspberry Pi 5 + Hailo-10H NPU** (dedicated edge accelerator)
- **NVIDIA RTX 4050** (laptop GPU, baseline)

## Thermal Degradation Patterns

**iPhone 16 Pro** showed the most severe degradation:
- "The iPhone 16 Pro loses roughly 40% of its peak throughput within three iterations" and settles at 23.7 tok/s
- Peak performance of 40.49 tok/s drops to 23.67 tok/s in Hot state—a 41.5% reduction
- Device transitions: Normal (iterations 1–2) → Warm (3–16) → Hot (17–20)

**Samsung Galaxy S24 Ultra** demonstrated milder decline:
- Throughput
… [1930 chars total]
```

> **tool** `WebSearch` — {"query": "IMU gravity vector known vertical direction reduces homography degrees of freedom camera calibration minimal solver accuracy"}

> **tool** `WebSearch` — {"query": "ARKit plane detection accuracy measurement error outdoor distance meters study LiDAR range limit 5 m"}

```
Web search results for query: "IMU gravity vector known vertical direction reduces homography degrees of freedom camera calibration minimal solver accuracy"

Links: [{"title":"Homography-Based Egomotion Estimation Using Gravity and SIFT Features | Computer Vision – ACCV 2020","url":"https://dl.acm.org/doi/10.1007/978-3-030-69525-5_17"},{"title":"Homography-Based Egomotion Estimation Using Gravity and SIFT Features | Springer Nature Link","url":"https://link.springer.com/chapter/10.1007/978-3-030-69525-5_17"},{"title":"Homography-based Egomotion Estimation Using Gravity and SIFT Features","url":"https://eprints.sztaki.hu/10042/1/Ding_1_31797599_ny.pdf"},{"title":"A high-precision calibration approach for Camera-IMU pose parameters with adaptive constraints of multiple error equations - Scie
… [3351 chars total]
```

```
Web search results for query: "ARKit plane detection accuracy measurement error outdoor distance meters study LiDAR range limit 5 m"

Links: [{"title":"Assessing the Robustness of LiDAR, Radar and Depth Cameras Against   Ill-Reflecting Surfaces in Autonomous Vehicles: An Experimental Study","url":"https://arxiv.org/pdf/2309.10504"},{"title":"Development and Validation of an Integrated LiDAR-Camera System for Real-Time Monitoring of Underground Longwall Operations","url":"https://arxiv.org/pdf/2605.02516"},{"title":"Quantitative assessment of low-cost iPad Pro LiDAR for accurate detection of replicated rock planes in a controlled environment - ScienceDirect","url":"https://www.sciencedirect.com/science/article/abs/pii/S0263224126003295"},{"title":"ARKit 911 — Scene Reconstruction with a LiD
… [3250 chars total]
```

> **tool** `WebSearch` — {"query": "smartphone accelerometer tilt roll pitch accuracy degrees static Core Motion device motion gravity error vibration"}

> **tool** `WebSearch` — {"query": "sports field registration camera calibration TVCalib reprojection error meters SoccerNet single image tennis court"}

```
Web search results for query: "sports field registration camera calibration TVCalib reprojection error meters SoccerNet single image tennis court"

Links: [{"title":"[PDF] TVCalib: Camera Calibration for Sports Field Registration in Soccer | Semantic Scholar","url":"https://www.semanticscholar.org/paper/TVCalib:-Camera-Calibration-for-Sports-Field-in-Theiner-Ewerth/4a127b41ba5c6ed09a7dd8b30562611787806bf4"},{"title":"[2207.11709] TVCalib: Camera Calibration for Sports Field Registration in Soccer","url":"https://arxiv.org/abs/2207.11709"},{"title":"TVCalib: Camera Calibration for Sports Field Registration in Soccer","url":"https://www.researchgate.net/publication/368313361_TVCalib_Camera_Calibration_for_Sports_Field_Registration_in_Soccer"},{"title":"TVCalib: Camera Calibration for Sports 
… [3053 chars total]
```

```
Web search results for query: "smartphone accelerometer tilt roll pitch accuracy degrees static Core Motion device motion gravity error vibration"

Links: [{"title":"Smartphone sensor accuracy varies from device to device in mobile research: The case of spatial orientation | Behavior Research Methods | Springer Nature Link","url":"https://link.springer.com/article/10.3758/s13428-020-01404-5"},{"title":"Air Resistance From the Acceleration of a Falling Smartphone","url":"https://arxiv.org/pdf/2410.14172"},{"title":"Method and apparatus for movement detection by evaluating elementary movement patterns","url":"https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9398536"},{"title":"Position sensors | Sensors and location | Android Developers","url":"https://developer.android.com/d
… [3355 chars total]
```

> **tool** `WebSearch` — {"query": "smartphone IMU assisted court line calibration tennis badminton mobile app homography gravity prior published"}

> **tool** `WebSearch` — {"query": "CMDeviceMotion attitude yaw drift per minute gyroscope bias iPhone accuracy degrees measured"}

```
Web search results for query: "smartphone IMU assisted court line calibration tennis badminton mobile app homography gravity prior published"

Links: [{"title":"(PDF) Evaluation of real time motion tracking accuracy of customised IMU sensor for application in a mobile badminton virtual reality training system","url":"https://www.academia.edu/83295075/Evaluation_of_real_time_motion_tracking_accuracy_of_customised_IMU_sensor_for_application_in_a_mobile_badminton_virtual_reality_training_system"},{"title":"(PDF) Tennis Ball Tracking: 3D Trajectory Estimation using Smartphone Videos","url":"https://www.academia.edu/38895415/Tennis_Ball_Tracking_3D_Trajectory_Estimation_using_Smartphone_Videos"},{"title":"IMU gyroscopes are a valid alternative to 3D optical motion capture system for angular kin
… [3398 chars total]
```

```
Web search results for query: "CMDeviceMotion attitude yaw drift per minute gyroscope bias iPhone accuracy degrees measured"

Links: [{"title":"CMDeviceMotion - NSHipster","url":"https://nshipster.com/cmdevicemotion/"},{"title":"Core motion attitude reference frame","url":"https://developer.apple.com/forums/thread/773168"},{"title":"Use CoreMotion in Landscape mode","url":"https://developer.apple.com/forums/thread/737178"},{"title":"CoreMotion Aligning IPhones CMAttitude","url":"https://developer.apple.com/forums/thread/689640"},{"title":"100% found this document useful (1 vote)","url":"https://www.scribd.com/document/127080912/Core-Motion"},{"title":"Portable electronic device adapted to compensate for gyroscope bias","url":"https://patents.justia.com/patent/8896301"},{"title":"CMMotionMa
… [2570 chars total]
```

> **tool** `WebSearch` — {"query": "TenniSet dataset tennis annotated events point rally annotation tool Faulkner Dick DICTA 2017"}

> **tool** `WebSearch` — {"query": "automatic rally segmentation tennis video without scoreboard ball in play detection accuracy point boundary"}

```
Web search results for query: "TenniSet dataset tennis annotated events point rally annotation tool Faulkner Dick DICTA 2017"

Links: [{"title":"TennisExpert: Towards Expert-Level Analytical Sports Video Understanding","url":"https://arxiv.org/html/2603.13397"},{"title":"GitHub - paris0120/TennisEvent: A Tennis dataset and models for event detection & commentary generation","url":"https://github.com/paris0120/TennisEvent"},{"title":"P2ANet: A Large-Scale Benchmark for Dense Action Detection from Table Tennis Match Broadcasting Videos","url":"https://arxiv.org/html/2207.12730v2"},{"title":"GitHub - HaydenFaulkner/Tennis: A Tennis dataset and models for event detection & commentary generation · GitHub","url":"https://github.com/HaydenFaulkner/Tennis"},{"title":"PingTactics: A Multimodal Data
… [3251 chars total]
```

```
Web search results for query: "automatic rally segmentation tennis video without scoreboard ball in play detection accuracy point boundary"

Links: [{"title":"TennisExpert: Towards Expert-Level Analytical Sports Video Understanding","url":"https://arxiv.org/pdf/2603.13397"},{"title":"(PDF) Players tracking and ball detection for an automatic tennis video annotation","url":"https://www.researchgate.net/publication/221144146_Players_tracking_and_ball_detection_for_an_automatic_tennis_video_annotation"},{"title":"Automatic rally detection on broadcast tennis videos: Sports Technology: Vol 6 , No 2 - Get Access","url":"https://www.tandfonline.com/doi/full/10.1080/19346182.2013.819007"},{"title":"Automatic rally detection on broadcast tennis videos | Request PDF","url":"https://www.researchgate
… [3041 chars total]
```

> **tool** `WebSearch` — {"query": "inter-annotator agreement temporal action boundaries video seconds tIoU humans disagree Sigurdsson Moltisanti action boundary ambiguity"}

> **tool** `WebFetch` — {"url": "https://arxiv.org/pdf/1801.01430", "prompt": "SmartTennisTV: how do they segment points/rallies? What accuracy do they report, on what footage, and do they use the scoreboard? Any human annot…

```
I apologize, but the content provided appears to be a corrupted or improperly encoded PDF file that doesn't contain readable text about SmartTennisTV or their point/rally segmentation methodology.

The document shows binary/encoded data rather than accessible information about:
- Point/rally segmentation methods
- Accuracy metrics or benchmarks
- Footage specifications tested
- Scoreboard usage
- Annotation costs

To answer your questions about SmartTennisTV's technical approach, I would need access to actual research papers, technical documentation, or articles describing their system. If you have a properly formatted document or link to their published work, I'd be happy to analyze it.

[Binary content (application/pdf, 917.5KB) also saved to C:\Users\richm\.claude\projects\e--Claude-Out
… [915 chars total]
```

```
Web search results for query: "inter-annotator agreement temporal action boundaries video seconds tIoU humans disagree Sigurdsson Moltisanti action boundary ambiguity"

Links: [{"title":"GolfDB: A Video Database for Golf Swing Sequencing","url":"https://arxiv.org/pdf/1903.06528"},{"title":"What Actions are Needed for Understanding Human Actions in Videos?","url":"https://arxiv.org/pdf/1708.02696"},{"title":"A frame-level video annotation tool for dynamic gestures ...","url":"https://jmst.mod.gov.vn/index.php/jmst/article/download/2077/2244/14388"},{"title":"(PDF) Diagnosing Error in Temporal Action Detectors: 15th European Conference, Munich, Germany, September 8–14, 2018, Proceedings, Part III","url":"https://www.researchgate.net/publication/328127797_Diagnosing_Error_in_Temporal_Action_D
… [3489 chars total]
```

> **tool** `WebFetch` — {"url": "https://arxiv.org/html/2603.13397", "prompt": "What method do they use for rally/point segmentation? Is it audio-based? What accuracy/agreement numbers are reported, on what footage (broadcas…

> **tool** `WebSearch` — {"query": "audio racquet ball impact detection tennis rally start end serve detection accuracy amateur video microphone"}

```
# Rally Segmentation Method

The paper uses **audio-based segmentation**. Specifically, they "train a lightweight audio neural network to detect the distinctive acoustic signatures of racquet–ball impacts from the broadcast audio track."

## Accuracy and Coverage

The document does **not report explicit accuracy metrics** for the segmentation pipeline itself. However, it notes the segmentation applies filtering to retain only clips with:
- Standard broadcast top-down court views
- Clearly visible scoreboards

## Dataset Scope

The segmentation was applied to **202 professional broadcast matches** (471.9 hours total) from major tournaments between 2019-2025, yielding 40,523 rally-level clips.

## Annotation and Agreement

The paper provides **no inter-annotator agreement statistics** for th
… [1136 chars total]
```

```
Web search results for query: "audio racquet ball impact detection tennis rally start end serve detection accuracy amateur video microphone"

Links: [{"title":"(PDF) Detection of ball hits in a tennis game using audio and visual information","url":"https://www.researchgate.net/publication/261119682_Detection_of_ball_hits_in_a_tennis_game_using_audio_and_visual_information"},{"title":"The Influence of Tennis Serve Kinematics on Ball Impact Sound and Post Impact Ball Speed and Spin","url":"https://www.redalyc.org/journal/7757/775784494003/"},{"title":"(PDF) Ball Hit Detection in Table Tennis Games Based on Audio Analysis","url":"https://www.researchgate.net/publication/224649455_Ball_Hit_Detection_in_Table_Tennis_Games_Based_on_Audio_Analysis"},{"title":"Wearable Audio and IMU Based Shot Det
… [2925 chars total]
```

> **tool** `WebSearch` — {"query": "\"BGProcessingTask\" real app how many minutes runs practice \"10 minutes\" OR \"several minutes\" limit developer measured 2025"}

> **tool** `WebFetch` — {"url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11843912/", "prompt": "Report the accuracy numbers for the acoustic tennis impact detection, the recording setup (microphone, distance, indoor/out…

```
REDIRECT DETECTED: The URL redirects to a location that was not fetched automatically.

Original URL: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11843912/
Redirect URL (from the server's Location header — server-supplied, not verified): https://pmc.ncbi.nlm.nih.gov/articles/PMC11843912/
Status: 301 Moved Permanently

To complete your request, I need to fetch content from the redirected URL. Please use WebFetch again with these parameters:
- url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11843912/"
- prompt: "Report the accuracy numbers for the acoustic tennis impact detection, the recording setup (microphone, distance, indoor/outdoor), the number of participants, and what exactly the 95% and 85% figures refer to."
```

```
Web search results for query: ""BGProcessingTask" real app how many minutes runs practice "10 minutes" OR "several minutes" limit developer measured 2025"

Links: [{"title":"iOS Background Execution Limits: What Every Developer Must Know (2026)","url":"https://www.appsonair.com/blogs/background-execution-limits-in-ios-what-every-developer-must-know"},{"title":"nativephp/mobile-background-tasks - Plugin - NativePHP","url":"https://nativephp.com/plugins/nativephp/mobile-background-tasks"},{"title":"Swift iOS BackgroundTasks framework — Background App Refresh in 4 Steps | by Myrick Chow | ITNEXT","url":"https://itnext.io/swift-ios-13-backgroundtasks-framework-background-app-refresh-in-4-steps-3da32e65bc3d?gi=cd943b2764f3"},{"title":"iOS Background Tasks","url":"https://oneuptime.com/blog/post
… [2813 chars total]
```

> **tool** `WebFetch` — {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11843912/", "prompt": "Report the accuracy numbers for the acoustic tennis impact detection, the recording setup (microphone, distance, indoor/outdoor…

```
# Tennis Acoustic Detection System Accuracy and Setup

## Accuracy Figures

The study reports two different accuracy metrics:

- **95% accuracy**: Refers to the ML algorithm's detection performance during controlled testing with the 1400-sample training dataset. "The ML algorithm showed a detection accuracy higher than 95%"

- **85% accuracy**: Represents the system's real-world on-court performance. "The average accuracy of the whole system that was applied on-court was 85%"

## Recording Setup

**Microphone and Distance:**
- Source: GoPro 11 built-in stereo microphone
- Sampling rate: 48 kHz
- Camera placement: 5 meters laterally from the player, 1.10 meters above ground
- The researchers noted this position was "chosen to capture the entire technical gesture and bounce of the ball"

**E
… [1097 chars total]
```

> **tool** `WebSearch` — {"query": "YOLOv8 YOLO11 CoreML benchmark iPhone 11 A13 fps ms measured older device"}

```
Web search results for query: "YOLOv8 YOLO11 CoreML benchmark iPhone 11 A13 fps ms measured older device"

Links: [{"title":"Best iOS Object Detection Models: RF-DETR for On-Device ...","url":"https://blog.roboflow.com/best-ios-object-detection-models/"},{"title":"YOLO11 vs YOLOv8: Model Comparison","url":"https://www.labellerr.com/blog/yolo11-vs-yolov8-model-comparison/"},{"title":"GitHub - THU-MIG/yoloe: YOLOE: Real-Time Seeing Anything [ICCV 2025] · GitHub","url":"https://github.com/THU-MIG/yoloe"},{"title":"(PDF) YOLOv8 to YOLO11 Performance Benchmark and Comprehensive Architectural Comparative Review","url":"https://www.researchgate.net/publication/404077516_YOLOv8_to_YOLO11_Performance_Benchmark_and_Comprehensive_Architectural_Comparative_Review"},{"title":"Ultralytics YOLO11 Hits 10
… [2767 chars total]
```

> **tool** `WebFetch` — {"url": "https://github.com/Photoroom/coreml-benchmark", "prompt": "List the benchmark results: which models, which devices (especially iPhone 11 / A13), input resolution, and latency in ms. Any fp16/…

```
Based on the webpage content provided, I cannot provide the specific benchmark results you're asking for. 

The page shows this is a GitHub repository for "Benchmark Core ML on the iPhone 11 and previous devices," but the actual detailed results—including which models were tested, specific device comparisons, input resolutions, latency measurements in milliseconds, and any fp16/int8 comparisons—are not displayed in the text content provided.

The page mentions that "the important code is in `benchmark/ViewController.swift`" and references an external article at "artizans.ai/posts/coreml-benchmark-on-iphone-11/," but neither the code details nor that external article's content appears in what was shared here. To find the actual benchmark data, you would need to visit the repository directly
… [830 chars total]
```

> **tool** `Grep` — {"pattern": "INPUT_|input_size|360|640|width|height|n_frames|SEQ", "path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\backend\\swingvision\\_tracknet.py", "output_mode": "content", "-n": true, "…

> **tool** `Glob` — {"pattern": "backend/swingvision/*ball*.py"}

```
7:Input : 9 channels = 3 consecutive RGB frames stacked, resized to 360x640.
8:Output: (B, 256, 360*640) logits; argmax over the 256 channels gives a per-pixel
```

```
backend\swingvision\_ballnet.py
backend\swingvision\ball.py
```

> **tool** `Read` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\backend\\swingvision\\_ballnet.py", "limit": 60}

```
1	"""Our own ball-detection network (compact 3-frame heatmap U-Net).
2	
3	Unlike the vendored TrackNet (yastrebksv) and WASB (nttcom) checkpoints — which
4	carry opposite domain biases (broadcast vs amateur) — this net is trained on OUR
5	footage domains via pseudo-labels from the tracker's confident locks (see
6	backend/train_ballnet.py). Deliberately small (~1.3M params) so it is fast on CPU
7	and exportable to the phone.
8	
9	Input : 3 consecutive RGB frames, NEWEST first, resized to 512x288, /255,
10	        stacked to 9 channels (same convention as ball.WASBDetector).
11	Output: (B, 1, 288, 512) heatmap logits; sigmoid -> per-pixel ball confidence.
12	"""
13	
14	import torch
15	import torch.nn as nn
16	
17	
18	def _block(cin, cout):
19	    return nn.Sequential(
20	        nn.Conv2d(ci
… [2605 chars total]
```

### Assistant

Now let me record what I established, before writing up.

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\ios-background-compute.md", "content": "---\nname: ios-background-compute\ndescription: iOS 18/2…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\ios-background-compute.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\coreml-ane-budget.md", "content": "---\nname: coreml-ane-budget\ndescription: Core ML / A13 ANE …

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\coreml-ane-budget.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\sensor-court-priors.md", "content": "---\nname: sensor-court-priors\ndescription: What phone sen…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\sensor-court-priors.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\point-boundary-ground-truth.md", "content": "---\nname: point-boundary-ground-truth\ndescription…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\point-boundary-ground-truth.md (file state is current in your context — no need to Read it back)
```

> **tool** `Edit` — {"replace_all": false, "file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\MEMORY.md", "old_string": "**Before proposing any investigation, read `doc…

```
The file E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\MEMORY.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

### Assistant

The index is now over its limit. Let me split it properly.

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\court-detection-negatives.md", "content": "---\nname: court-detection-negatives\ndescription: Ev…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\court-detection-negatives.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\ball-negatives.md", "content": "---\nname: ball-negatives\ndescription: Ball detector/chain appr…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\ball-negatives.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\project-method-rules.md", "content": "---\nname: project-method-rules\ndescription: Standing tec…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\project-method-rules.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\open-questions.md", "content": "---\nname: open-questions\ndescription: Unresolved technical que…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\open-questions.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\mobile-port-split.md", "content": "---\nname: mobile-port-split\ndescription: What of the shippe…

```
File created successfully at: E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\mobile-port-split.md (file state is current in your context — no need to Read it back)
```

> **tool** `Write` — {"file_path": "E:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\MEMORY.md", "content": "# researcher-agent memory\n\nIndex only. Detail lives in the topic files…

```
The file E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\MEMORY.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

### Assistant

## Headline: three findings change the plan

1. **iOS has no multi-hour background compute, on any API, at any tier.** Resumable checkpointing isn't just core architecture — the *foreground* becomes the primary execution surface and background becomes a top-up. "Analyse my match" is one feature with two execution modes, not two features.
2. **The desktop cost ratio between ball and pose inverts on the Neural Engine.** On desktop CPU, pose (0.4 s/frame) was cheaper than ball (0.7). On an A13 ANE, `yolo11m-pose@1280` is roughly **25× the ball's cost**. Every compute estimate inherited from the desktop numbers is wrong in direction, not just magnitude — and the biggest available lever is not quantisation but **not running pose on every frame**.
3. **Point boundaries are LOGIC, not perception, under this project's own architecture rule.** So labels are needed for *evaluation only*, not training — which collapses the corpus from ~15 matches to ~3–5, and reframes the 5 hours as a correction budget rather than a labelling budget.

---

# R1 — iOS background compute limits

**Finding.** There is no supported mechanism on iOS for sustained multi-hour compute in the background, and no shipped third-party consumer app does it. The universal pattern for on-device analysis of user media is **foreground, screen on, progress bar**, with the OS-blessed background APIs used only for short top-ups. Separately and decisively: **submitting GPU work from the background is refused by the OS**, which forces Core ML onto the Neural Engine and makes any ANE fallback a crash rather than a slowdown.

**Evidence.**

- Apple DTS's canonical thread, *iOS Background Execution Limits*, enumerates every background mechanism and states none permits continuous execution. `BGProcessingTask` is described by DTS as scheduled at the system's discretion — "the schedule is an implementation detail" — and typically runs **overnight**, not on demand. Reported per-invocation wall clock ranges from "several minutes" to ~10–30 minutes; nobody has a guarantee.
- **Kill conditions, all documented or reported by developers:**
  - **CPU Monitor: 80% average CPU over 60 s → SIGKILL.** `BGProcessingTask` is supposed to disable this while on charger. A developer measured it firing anyway at 97% average, and DTS's suspected cause is that **declaring another background mode — specifically `audio` — re-enables the limit.** A tennis recorder is exactly the kind of app that reaches for the audio mode. Flag this now.
  - **The system terminates background processing tasks when the user picks the phone up.**
  - **Force-quitting from the app switcher permanently blocks background launches** until the user manually reopens the app. No documented override. Users force-quit apps after long recording sessions.
  - **Attaching LLDB disables the watchdogs**, so none of this reproduces under a debugger.
- **The GPU rule.** Metal submission from a backgrounded app fails with `IOGPUCommandQueueErrorDomain`, "Insufficient Permission (to submit GPU work from background)". On **iOS 26.2 this became a hard Metal abort — a process crash**, where previously the job was silently revoked. Consequence: Core ML must be pinned to `.cpuAndNeuralEngine`, never `.all`. This is the join between R1 and R2 — an operator that silently falls off the ANE onto the GPU is a *fatal* bug in the background, not a performance regression.
- **iOS 26's `BGContinuedProcessingTask`** is the purpose-built API for exactly this UX (user-initiated, system progress UI, user-cancellable), and iPhone 11 / A13 does receive iOS 26. But GPU use needs a separate entitlement, is **not supported on all devices** (developers report iPhone 16 Pro Max and M1 iPad Pro returning `false` from `BGTaskScheduler.supportedResources`), and a developer testing 30–60 minute workloads reported the expiration handler firing "irregularly" with no discoverable pattern and no API to learn *why* it fired.
- **What shipped apps do.** Apple Photos' background ML (face/scene analysis) runs only when charging + locked + Wi-Fi + not Low Power — and it is a **system-app privilege**, an aspirational UX pattern, not an API third parties can call. **SwingVision — the direct competitor — runs real-time on-device tracking in the foreground on iPhone 11 / SE 2020 and up, iOS 18+.** That is the honest comparable, and it is third-party proof that a full-match thermal envelope exists on the floor device.

**Confidence: 90%** on the shape (no multi-hour background job; foreground is the real surface). **70%** on the specific `audio`-background-mode / CPU-Monitor interaction — one developer report plus a DTS hypothesis, not a documented rule. What would move it: a one-page test app that declares the audio mode, runs a 100%-CPU loop under `BGProcessingTask` on charger, and reports whether it is killed.

**What would disprove this.** A shipped App Store app that demonstrably completes an hour-plus of ML work on user media with the app backgrounded and the screen off, without a Live Activity. I looked and did not find one. If someone names one, I'm wrong about the ceiling.

**Feasibility on our constraints.** No issue with the ruling — this is iOS-specific and A13-compatible. But it reshapes the UX: the honest promise is *"keep the app open while we analyse; you can lock the phone and we'll continue as far as the system lets us, then resume when you come back."* Refusal-and-resume, not silent completion.

**Proposed experiment — pre-registered.**
> **Question:** Can a `BGProcessingTask` on an A13, on charger, screen off, sustain ANE-only Core ML inference for ≥10 minutes without being killed?
> **Metric:** wall-clock seconds of task execution before `expirationHandler` fires or the process dies, across 10 overnight scheduling attempts.
> **Threshold:** median ≥ 600 s to call background a useful top-up channel.
> **Held-out set:** n/a — device behaviour, not data. Run on an actual iPhone 11, not a Pro, not the simulator, not under LLDB.
> **Kill condition:** if median < 120 s, or if fewer than 5 of 10 attempts launch at all, background is a top-up only and the plan should stop budgeting anything for it.
> **Second arm, same harness:** identical app with the `audio` background mode declared. If that arm dies at ~60 s and the other doesn't, the CPU-Monitor interaction is confirmed and the audio mode is banned.

**For the PM.** The product tradeoff: you can promise "analyse in the background overnight" only as best-effort, never as a completion guarantee. The alternative is an explicit foreground job with a progress bar and a "keep the screen on" instruction — honest, and it is what the competitor does. A middle path exists: **foreground primary + `BGContinuedProcessingTask` for the tail** (iOS 26 only, so it degrades on iOS 18). Decision is yours; my only strong recommendation is that checkpointing be per-segment and resumable from the first commit, because every path needs it.

**Open questions.** Actual A13 `BGProcessingTask` wall clock. Whether `BGTaskScheduler.supportedResources` even matters for us (it shouldn't, if we're ANE-only — but nobody has published whether ANE submission from background is subject to an analogous permission check; I found only blog-level assertions that it isn't).

---

# R2 — Core ML export for YOLO11-pose on an A13

**Finding.** `yolo11m-pose @ 1280` is not viable on an A13. My arithmetic puts it near **1 second per frame** — worse than the desktop CPU it's replacing. There is **no published sustained-throughput figure for any YOLO11-class pose model on A13-generation silicon**; there is no published *peak* figure either. Export maturity is fine; the problem is compute, and the fix is architectural, not a conversion flag.

**Evidence.**

The one published number that is close to relevant, from Ultralytics' own iOS docs: **YOLO26n-pose, 640×640, int8, iPhone 17 Pro (A19 Pro, 16-core ANE), iOS 26.5.2 — 3.9 ms on `.cpuAndNeuralEngine`, 11.9 ms CPU-only.** That is the *nano* model, at *640*, on the *newest* silicon. Scaling it:

| Stage | GFLOPs | Desktop CPU (measured, this repo) | A13 ANE — **my estimate** |
|---|---|---|---|
| BallNet, 512×288, 9-ch U-Net, 1.3M params | ~8–12 | ~0.7 s/frame | ~30–50 ms/frame |
| `yolo11m-pose` @ 640 | ~72 (published) | — | ~250 ms/frame |
| `yolo11m-pose` @ **1280** | ~287 | ~0.4 s/frame | **~1,000 ms/frame** |

Method: scale 3.9 ms by the FLOP ratio (×38 for m@1280 vs n@640) and by nominal ANE throughput (A13 ~5–6 TOPS vs A19 Pro ~35–40, so ~7×). **This is arithmetic, not a measurement**, and it is *optimistic* — it ignores memory bandwidth at 1280² and any thermal derate.

**The inversion is the finding.** On desktop CPU pose was cheaper than ball. On the ANE, pose@1280 is ~25× the ball. My explanation, offered as judgement: ANE is a fixed-function fp16 matrix engine, so relative cost tracks FLOPs closely; on CPU it tracks cache behaviour, and a high-resolution U-Net is cache-hostile while Ultralytics' CPU path is heavily optimised. Either way, **`mobile-parity-first`'s "ball 0.7 + pose 0.4 = ~1.1 s/frame → need ~11× desktop CPU" does not survive the platform change.**

**Export maturity and fallback triggers:**
- Core ML export for pose is a first-class supported task in Ultralytics. INT8/FP16/FP32 all supported. **The NMS ML Program is fp16 and is *required* for pose** — so the decode/NMS tail is a separate, non-quantisable pipeline stage; budget it apart from the backbone.
- **`computeUnits = .all` silently places unsupported ops on GPU or CPU.** Pin `.cpuAndNeuralEngine`. Ultralytics reached the same conclusion independently for their shipping app.
- **Flexible/ranged input shapes push work off the ANE.** Use fixed or enumerated shapes only.
- Ultralytics' own on-device profiling found **preprocessing (~8 ms) exceeded inference (~7 ms)** in a live camera app on an A19 Pro. Preprocessing does not shrink when you shrink the model — it's a floor.

**int8 is not a speed lever on an A13.** This is the cleanest published fact in the whole brief and it contradicts a common assumption:
- **int8×int8 ANE compute arrived with A17 Pro / M4.** On earlier silicon Core ML stores int8 weights and **dequantises to fp16** (`constexpr_affine_dequantize`). On an A13, int8 buys download size and memory bandwidth. Not throughput.
- Ultralytics' `int8=True` CoreML export is **weight-only palettization (W8A16)**, so its accuracy cost is small — and its A13 speed benefit is correspondingly small.
- The literature on int8 hurting pose concerns **full W8A8 activation quantization**. The reported mechanism (ultralytics#21625) is YOLO's unified `[batch, nKeypoints+5, nFeatures]` head mixing keypoints (regionally clustered, high precision needed), boxes (uniform) and confidences (bimodal) into one tensor with one scale. **No published OKS or keypoint-mAP delta was found for YOLO11-pose under int8.** That is a genuine gap, not a number I can give you.
- For calibration of expectations only: Apple's own W8A8 example is ResNet50, **1.52 → 0.94 ms on A16, → 0.77 ms on A17 Pro**, accuracy 76.14% → 76.80%. Classification, not pose, on a flagship.

**Sustained vs peak — there is no public ANE curve for anything.** Every sustained-load number I found is GPU or CPU. The best available (arXiv 2603.23640, LLM decode via MLX on iPhone 16 Pro **GPU**) shows **−40% of peak within three iterations**, settling at −41.5% — and the paper explicitly states MLX does not target the ANE. Argmax's iPhone 17 work reports ANE hitting ~15 of a 17.5 TFLOP/s theoretical peak on an iPhone 16 Pro, but that is burst. **The honest answer to "are there published sustained figures for A13-generation ANE" is: no, and there are no peak figures either.**

**Confidence: 85%** that pose@1280 is infeasible on an A13 (the gap is ~10×, far larger than my error bars). **40%** on the specific ~1,000 ms figure. **95%** on int8-buys-no-A13-compute (Apple's own documentation). **95%** that no A13 pose benchmark is published.

**What would disprove this — and it is the cheapest falsification in the whole brief.** Export `yolo11m-pose` at 1280, 640 and 384 to Core ML and run **Xcode's built-in Core ML Performance Report on a physical iPhone 11**. It takes under an hour, needs no app, and reports both latency *and* the per-layer compute-unit assignment, which simultaneously answers the fallback question. If it comes back under 100 ms at 1280, my whole estimate is wrong and the plan is easier than I think. **Run this before anything else in the mobile phase.**

**Feasibility on our constraints.** The route to viability is not quantisation. It is, in descending order of value:

1. **Don't run pose every frame.** The ball needs every frame; pose does not. `events.classify_shot` and `classify_spin` need pose *at the contact frame*; movement stats need a few Hz. A ball-first pass yields contact frames; pose then runs on contacts ± a window plus a low-rate sample. That is a **5–10× cut at no measured accuracy cost**, and nothing else comes close. It is a real architecture change and the plan should absorb it explicitly.
2. **Drop input resolution.** 1280 → 640 is ~4×. But this collides directly with a measured finding of yours: `docs/evidence/the-far-player-is-a-detection-problem.md` records the far player detected on only **14.5%** (yt_match40) and **26.7%** (am_hard_utr) of frames *at 1280*, both below the 50% a path integral needs. Halving the resolution will make that worse, and `--pose-quality accurate` (1920) was already a measured no-op on that axis. **A far-court pose tile — analogous to `--far-ball-tile`, and already named as unexplored in that evidence file — is the resolution-independent answer, and it is now also the compute answer**: two 640 tiles cost half of one 1280 frame.
3. **Drop model size.** `yolo11s-pose` is ~3× cheaper than m; `yolo11n-pose` ~9×. Unmeasured on your footage.

**Proposed experiment — pre-registered.**
> **Question:** What is `yolo11m-pose`'s per-frame Core ML latency on an iPhone 11 at 1280 / 640 / 384, and what fraction of the graph is assigned to the ANE?
> **Metric:** median latency (ms) over 100 predictions from Xcode's Core ML Performance Report, plus the count of layers assigned to CPU/GPU vs ANE.
> **Threshold:** ≤120 ms/frame at the chosen resolution to keep pose in the per-frame budget at all.
> **Held-out set:** n/a for latency. For *accuracy*, any resolution or model-size change must be re-scored against the existing pose evidence on the three calibrated clips — and specifically against far-player detection rate, which is the axis that will break first.
> **Kill condition:** if ≥1 layer lands on GPU at the chosen configuration, that configuration is disqualified for background execution regardless of its latency (R1's GPU rule).

**For the PM.** This changes the ordering argument. `mobile-parity-first` put ball first, pose second, court last, on information-per-session. That ordering is still fine, but **the viability gate at ~9 sessions in should be moved forward to a one-hour Xcode measurement before any porting starts**, because pose@1280 being infeasible would change what "ball first" is even in service of. The tradeoff you'll be asked to make later is: *accept a lower-resolution pose (and a worse far player, which you already can't measure well) or accept a much longer analysis job.* Don't decide that now — get the measurement.

**Open questions.** Actual A13 latency at each configuration. Whether the far-court pose tile works at all. Whether int8 W8A16 costs anything in keypoint accuracy on your footage (unmeasured anywhere, but likely small).

---

# R3 — Sensor-assisted court calibration

**Finding.** The DOF reduction in `sensor-assisted-court` is real and the mechanism is sound, but **the sensors are much weaker priors than the memo implies, and one of them (yaw) is worthless.** The critical number: **1° of pitch error is ~6 px at 640 — a third of your 20 px `WRONG_PX_640` budget — and published per-device smartphone tilt accuracy spans 0.05° to ~2.1°.** So gravity may *narrow* the search window; it may not *fix* the pose. At the worst end of the device spread the prior alone consumes ~13 of your 20 px. Meanwhile there is **no published work applying phone IMU priors to sports-court registration at all** — the gravity-prior literature is robotics/SfM and the sports-field literature is broadcast.

**Evidence.**

*The arithmetic (mine, and checkable in five minutes):*
- A ground-plane homography is 8 DOF. Known intrinsics from `AVCaptureDevice` removes the intrinsic unknowns → 6 (R:3, t:3). **Gravity fixes roll and pitch → 4** (yaw + 3 translations). Add camera height → **3** (yaw + two ground translations). Published gravity-prior solvers (Ding et al., ACCV 2020, tested on iPhone 6s image+IMU sequences; Fraundorfer et al.) rest on exactly this reduction — but they solve egomotion and report solver accuracy, not registration error in metres.
- **The strongest version of the argument is not "fewer parameters."** It's that the current grid `(cx, y_near, y_far, hw_near, hw_far)` is parameterised in *image* space and **does not enforce a physically consistent court** — which is precisely why frames disagree about *width*. Replacing 5 unconstrained image parameters with 3–4 physically meaningful ones is the real mechanism.
- **Error budget at 640-wide, ~86° FOV, f ≈ 343 px:** 1° pitch = ~6 px vertical image shift. 1° roll = up to ~5.6 px at the image edge. Your 20 px gate ≈ 3.3° of pitch.
- **On the ground the same 1° is catastrophic, and this must never be forgotten.** At a 1.74 m mount, the far baseline at 23 m sits at a 4.33° depression; `dd/dθ = h/sin²θ ≈ 305 m/rad ≈ **5.3 m of ground error per degree of pitch**`. **Sensors constrain the image-space horizon. They must never be used to place the far baseline directly.**

*What each sensor is worth:*
- **Gravity (roll + pitch): usable.** Published multi-device smartphone tilt accuracy (Springer, *Behavior Research Methods*, 2020): mean deviations as low as **0.05° pitch / 0.20° roll**, but **up to ~2.1° mean inaccuracy per device**, varying by model. **It is the device-to-device spread, not the sensor noise, that sets the safe window.** ±2–3° is honest; ±0.5° is not.
- **Yaw: useless.** Two iPhones held at the same true orientation showed **15–45° discrepancy** in magnetometer-referenced yaw. Leave yaw to the image or the user. (The memo already assumed this; now it's evidenced.)
- **ARKit: only good near the camera.** Use it for **camera height above the local ground plane at 1–3 m** — which is exactly the parameter that sets apparent court *width*, i.e. your actual failure mode. Do **not** use it to detect the court plane at range; monocular VIO on a low-texture court surface at 10–20 m will not produce a reliable plane extent.
- **LiDAR: out of range and off the floor device.** Apple LiDAR measures to **~5 m** (occasionally 7 m). The near baseline may be inside that; the far baseline never is. And there's no LiDAR on an iPhone 11 anyway. Progressive enhancement at best; I'd cut it from the plan.
- **Fence-mount vibration: there is no published number.** Say so plainly. My reasoning, offered as judgement: Core Motion fuses gyro and accelerometer, so high-frequency shake largely averages out. The real risk isn't noise — it's a **bump that changes the true pose**, after which the homography is stale and the IMU is the *only* thing that knows. **That reframes vibration from a cost into a benefit: the IMU is your stale-calibration detector.** That's a feature the desktop product cannot have.

*Transfer warning.* TVCalib (WACV 2023), PnLCalib, SoccerNet-Calibration and Farin et al. 2003 (">91% feature detection" on badminton/tennis/volleyball) are **all broadcast long-lens footage**. None of their numbers tells you anything about a phone on a fence in a Manila shell court. I am deliberately not quoting them as a target.

**Confidence: 90%** on the error-budget arithmetic (it's elementary trigonometry — check it). **85%** that yaw is unusable. **80%** that ARKit-at-range is the wrong use and ARKit-at-camera-height is the right one. **95%** that no prior art exists for phone-IMU sports-court registration.

**What would disprove this.** The pitch arithmetic is falsified by one measurement: take a calibrated clip, perturb the fitted camera pitch by exactly 1°, reproject the court, measure the max corner displacement at 640. If it isn't ~6 px, my model of the geometry is wrong. That costs about twenty minutes and needs no phone.

**Feasibility on our constraints.** `AVCaptureDevice` intrinsics, Core Motion gravity and ARKit plane detection are all A13-available, all native, all free at runtime. No conversion toolchain involved — this is geometry, which stays closed-form and portable by your own rule. **One flag: `SOLVEPNP_IPPE` and `findHomography` are already in your cv2 usage and exist in OpenCV's iOS build, so the sensor-seeded fit adds no new dependency.** Also: **video stabilisation must be OFF** on the capture path — it silently warps the frame and destroys homography consistency across frames, and it interacts badly with an IMU prior because the IMU reports the *true* camera pose while the pixels have been re-warped. That belongs in the capture spec, not discovered later.

**Proposed experiment — pre-registered.**
> **Question:** Does a gravity + intrinsics prior with a ±3° window contain the human-clicked court in its candidate set more often than the current grid does?
> **Metric:** fraction of clips where the human court is inside the sensor-narrowed search volume (the "truth is in the candidate set" statistic — currently **3 of 10 on shell**).
> **Threshold:** ≥7 of 10 shell clips, matching the 7/10 that *would be accepted if the search produced them*.
> **Held-out set:** the new sensor gold set only. **Tuning stays on the 10 original calibrated clips; shell remains verification-only.** The ±3° window must be chosen on the calibrated set and not adjusted against shell.
> **Kill condition:** if narrowing to ±3° *excludes* the true court on any clip where the current grid contained it, the prior is admitting a wrong court by omission and the window must widen — which is the failure mode this project cares about most.

**For the PM.** Two things move in the plan. First, **the sensor gold set is the critical path and it is bigger than it looks** — every existing recording is sensor-less, so this is new shooting, and it now also needs *device diversity*, because the 0.05°-to-2.1° tilt spread is per-model. One iPhone's calibration does not characterise the fleet. Second, **LiDAR should come out of the plan** — 5 m range, absent on the floor device, and it doesn't reach the thing you'd want it for. The upside I'd add: the IMU gives you a **free stale-calibration detector** ("your phone was bumped — re-tap the corners"), which is a genuinely new product capability, not just a search accelerator.

**Open questions.** Fence-mount vibration amplitude in practice — no published number, and cheap to measure once the capture tool exists (log Core Motion gravity for 10 minutes on a fence and report the standard deviation of derived pitch). Whether ARKit produces a usable camera height on a plain hard court with no texture — genuinely unknown, and a plausible failure.

---

# R4 — Point-boundary ground truth

**Finding.** Split the problem before costing it, because it is two problems with two different ceilings. **"How many points and roughly where"** — humans agree near-perfectly, and this is what the product needs for clip segmentation and scoring. **"The exact boundary frame"** — genuinely ambiguous even for humans, and the product doesn't need it because clips get padding. And the load-bearing structural point: **under this project's own Perception/Geometry/Logic rule, point boundaries are Logic. A rule over ball-in-play state and bounces has no training set. So labels are for evaluation only — which needs 3–5 matches (~500 points), not 15.**

**Evidence.**

- **Human agreement on temporal action extents.** Sigurdsson et al. (ICCV 2017) re-annotated Charades and MultiTHUMOS and found **72.5% and 58.7% mean tIoU** between annotators. Median **start error 0.9 ± 0.8 s; end error 1.4 ± 1.4 s** — the *end* is the ambiguous half, which maps precisely onto "when did the point stop". Agreement rises with activity duration, and a tennis point (5–30 s) is longer than a Charades action, so expect better than 72.5% — **but I will not quote a number that has not been measured on tennis.**
- **Consequence for your metric design:** any point-boundary metric must be **tolerance-based** (event spotting within ±N seconds, plus a count/alignment score), never tIoU against a single annotator's frame. Publishing a tIoU here would be measuring annotator noise and calling it accuracy. This matters — it determines what the pre-registered gate can even say.
- **No published inter-annotator agreement for tennis point boundaries exists.** TenniSet (Faulkner & Dick, DICTA 2017 — 5 broadcast matches, dense temporal events, annotation tool released) publishes neither an agreement study nor annotation-hour figures.
- **Compliant automated signals, ranked:**
  - **Audio racquet/ball impacts — strongest and cheapest.** Measured on-court: **95% in controlled ML testing, 85% for the whole system applied on court** (Sensors / PMC11843912, n=10, **GoPro 11 built-in stereo mic, 5 m laterally, 1.10 m high, outdoor, with wind and adjacent-court noise**). That capture setup is genuinely close to your target footage — a rare case where the transfer is plausible. Audio is derived from the game, so it is rule-11 compliant. You already have an unwired `audio.py`.
  - **Ball-in-play / bounce sequences** — compliant by construction, but blocked by your own open defects: 24–27% far-court detector dropout and 9 solid ghost balls. A point boundary derived from a track with 25% dropout will over-split.
  - **Broadcast rally detection — DO NOT IMPORT.** The published 81% average (91% hard / 82% grass / 71% clay, *Sports Technology* 2013) works by classifying the **camera shot**: overhead court view = rally in play. A fixed phone on a fence never cuts, so the entire signal is absent. TennisExpert (2026) segments 202 broadcast matches by audio impacts but publishes **no segmentation accuracy at all**, and filters to clips with a visible scoreboard.

- **On the 5 hours / 15 matches costing.** 15 matches is 15–22 hours of video. Scanning alone is ~1× realtime, so **5 hours cannot label that from scratch** — it is off by roughly 4–6×. 5 hours *is* a realistic **correction** budget: review and fix an automatic proposal, ~7 s per point across ~2,500 points. That's fine, but it must be specified that way, and **the proposer has to exist before the labelling starts.** So the order is: build the audio/activity gap proposer, then label by correction.

**Confidence: 85%** that boundaries are Logic and labels are evaluation-only. **80%** that audio is the strongest compliant signal on this footage (the 85% figure was measured on a close analogue, but n=10 and a GoPro, not an iPhone at a different mount). **90%** that the 5-hours-from-scratch arithmetic is wrong and 5-hours-as-correction is right.

**What would disprove this.** Two annotators independently mark point boundaries on one 30-minute clip. If their **point counts differ by more than 2%**, my "the count is near-perfectly agreeable" claim is wrong and the whole framing collapses back into one hard problem. That is two hours of human time and it should be the first thing run in this lane.

**Feasibility on our constraints.** The audio path needs work: `audio.py` currently shells out to a bundled ffmpeg binary and has **no iOS equivalent** — replace with `AVAssetReader` reading the audio track, which is native and cheap. An impact classifier over a spectrogram is a tiny model, trivially ANE-viable, and does not compete with pose for the frame budget. **One flag for the geometry side: nothing here adds a SciPy dependency if the spectrogram is computed with a hand-rolled FFT or Accelerate's `vDSP`, but the obvious Python prototype will reach for `scipy.signal` — that has no C++/iOS equivalent and must be reimplemented, so cost it now rather than at port time.**

**Proposed experiment — pre-registered.**
> **Question 1 (run first):** Do two humans independently agree on the *number* of points in a clip?
> **Metric:** absolute difference in point count, and median absolute difference in start/end times for matched points.
> **Threshold:** count agreement within 2%; median start difference < 1.0 s.
> **Kill condition:** if count agreement is worse than 5%, stop — there is no ground truth to build against and the scoring feature cannot be gated.
>
> **Question 2 (only if 1 passes):** Does an audio-impact + ball-activity rule reproduce human point boundaries?
> **Metric:** F1 of point-start spotting at a ±2 s tolerance, plus over-split and under-split rates.
> **Threshold:** pre-register against the human-agreement ceiling measured in Q1, not against an absolute number.
> **Held-out set:** 3–5 matches, one-way TEST-only, under the same `assert_no_*_leak` discipline as ball and court. **A new guard is needed — the project's own rule 4 notes that a discipline enforced on one model is not enforced on the project.**
> **Kill condition:** if over-split exceeds 1.3×, the point-by-point clip feature ships with manual correction or not at all.

**For the PM.** Three plan changes. **(1) The corpus shrinks** from ~15 matches to 3–5, because there is no training set to build — this is a real saving. **(2) The 5 hours is a correction budget, so it depends on a proposer existing first** — the sequencing in the plan needs that dependency made explicit or the estimate is unfundable. **(3) Audio moves onto the critical path.** It is the cheapest compliant signal, it has a measured on-court number from a close analogue, it costs essentially nothing at runtime, and it doubles as the unevaluated bounce-height signal already sitting open in `docs/STATE.md`. That's two open items served by one build. Whether that's worth pulling forward is your call.

**Open questions.** Whether the 85% on-court audio figure survives an iPhone's mic (different directionality, different AGC) at a fence mount rather than 5 m lateral. Whether indoor shell courts — where every sound reverberates off a metal roof — destroy it entirely. That second one worries me: your hardest venue for vision may also be your hardest venue for audio, which would mean the two failure modes are correlated rather than complementary.

---

## Cheapest falsifications, ranked

1. **R2 — one hour, no app, no code.** Export `yolo11m-pose` at 1280/640/384 to Core ML, run Xcode's Core ML Performance Report on a physical iPhone 11. Gets you latency *and* per-layer compute-unit assignment in one shot. **Run this before anything else in the entire mobile phase** — it is the single measurement that most constrains the architecture.
2. **R3 — twenty minutes, no phone.** Perturb a calibrated clip's fitted pitch by 1°, reproject, measure max corner displacement at 640. Confirms or destroys my error budget.
3. **R4 — two human hours.** Two annotators, one 30-minute clip, count the points. Establishes whether ground truth exists at all before anything is built.
4. **R1 — one throwaway app, one night.** Two arms (with and without the `audio` background mode), 100%-CPU loop under `BGProcessingTask` on charger. Answers both the wall-clock question and the CPU-Monitor interaction.

## What this changes in pm-agent's plan

| Plan element | Change |
|---|---|
| Compute arithmetic ("ball 0.7 + pose 0.4 = ~1.1 s/frame, need ~11× desktop CPU") | **Invalid.** The ratio inverts on ANE. Ball becomes nearly free; pose@1280 becomes the entire budget. Re-derive from FLOPs, not from the desktop timings. |
| "Court binds sessions, pose binds runtime, ball is fine" | Directionally right, but "ball is fine" was reasoned from *model size*; it happens to be true from FLOPs too, **except that the shipped `mobile/` ONNX is the heavier TrackNet, not BallNet.** That divergence now has a compute cost, not just a correctness cost. |
| Viability gate at ~9 sessions in | **Move a one-hour Xcode measurement to session 0.** It could invalidate the pose approach entirely, and it is nearly free. |
| Resumable checkpointing | **Confirmed as core architecture** — and the foreground becomes the primary execution surface, not the background. |
| "iOS: BGProcessingTask, realistically overnight-on-charger" | Too optimistic. Minutes, not hours; killed when the user picks up the phone; blocked entirely after a force-quit. |
| LiDAR as progressive enhancement | **Cut it.** 5 m range, absent on the A13 floor device, doesn't reach anything useful. |
| Sensor gold set | **Bigger than scoped** — needs device *diversity*, because tilt accuracy varies 0.05°–2.1° by phone model. One phone does not characterise the fleet. |
| Point-boundary corpus (~15 matches, ~5 h) | **Corpus shrinks to 3–5 matches** (evaluation-only, no training set). **5 h is a correction budget and depends on a proposer built first** — make that dependency explicit. |
| Audio | **Promote onto the critical path.** Cheapest compliant point-boundary signal, measured 85% on close-analogue on-court footage, and it also serves the open bounce-height question. |
| New constraint not in the plan | **Video stabilisation OFF** in the capture spec. It warps frames, breaks homography consistency, and conflicts with an IMU prior. |
| New constraint not in the plan | **Do not declare the `audio` background mode** without testing — it may re-enable the 80%/60 s CPU kill on `BGProcessingTask`. |

## Files

- `E:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\MEMORY.md` (rewritten as an index; was over its 200-line read limit and silently truncating)
- `...\researcher-agent\ios-background-compute.md`, `coreml-ane-budget.md`, `sensor-court-priors.md`, `point-boundary-ground-truth.md` (new, R1–R4)
- `...\researcher-agent\court-detection-negatives.md`, `ball-negatives.md`, `project-method-rules.md`, `open-questions.md`, `mobile-port-split.md` (existing memory split out of the oversized index; content preserved)

Sources: [iOS Background Execution Limits (Apple DTS)](https://developer.apple.com/forums/thread/685525) · [BGProcessingTask scheduling (Apple DTS)](https://developer.apple.com/forums/thread/766206) · [BGProcessingTask killed for CPU (signal 9)](https://developer.apple.com/forums/thread/675166) · [BGContinuedProcessingTask expiration reasons](https://developer.apple.com/forums/thread/818873) · [Finish tasks in the background — WWDC25](https://developer.apple.com/videos/play/wwdc2025/227/) · [Background GPU Access availability](https://developer.apple.com/forums/thread/794072) · [Metal background execution error (maplibre-native #3172)](https://github.com/maplibre/maplibre-native/issues/3172) · [SwingVision on the App Store](https://apps.apple.com/us/app/swingvision-tennis-pickleball/id989461317) · [Ultralytics CoreML export docs](https://docs.ultralytics.com/integrations/coreml) · [Ultralytics YOLO iOS app](https://github.com/ultralytics/yolo-ios-app) · [coremltools quantization performance](https://apple.github.io/coremltools/docs-guides/source/opt-quantization-perf.html) · [YOLO pose int8 output-head issue](https://github.com/ultralytics/ultralytics/issues/21625) · [Apple Neural Engine supported devices (hollance)](https://github.com/hollance/neural-engine/blob/master/docs/supported-devices.md) · [LLM Inference at the Edge under Sustained Load](https://arxiv.org/html/2603.23640v2) · [Argmax iPhone 17 inference benchmarks](https://www.argmaxinc.com/blog/iphone-17-on-device-inference-benchmarks) · [Homography-Based Egomotion Using Gravity](https://eprints.sztaki.hu/10042/1/Ding_1_31797599_ny.pdf) · [Smartphone sensor accuracy varies device to device](https://link.springer.com/article/10.3758/s13428-020-01404-5) · [TVCalib](https://arxiv.org/abs/2207.11709) · [What Actions are Needed for Understanding Human Actions in Videos?](https://arxiv.org/pdf/1708.02696) · [Tennis Timing Assessment by ML Acoustic Detection](https://pmc.ncbi.nlm.nih.gov/articles/PMC11843912/) · [Automatic rally detection on broadcast tennis videos](https://www.tandfonline.com/doi/full/10.1080/19346182.2013.819007) · [TennisExpert](https://arxiv.org/html/2603.13397) · [TenniSet](https://www.semanticscholar.org/paper/TenniSet:-A-Dataset-for-Dense-Fine-Grained-Event-Faulkner-Dick/4ee94572ae1d9c090fe81baa7236c7efbe1ca5b4)
