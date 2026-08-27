# Subagent transcript — `aa678c1c69d506e58`

Source: `C:\Users\richm/.claude/projects\E--Claude-Outputs-Cowork-Tasks-Swing-Vision\7168a5a5-e837-47d6-bdb6-ab1e3b940119\subagents\agent-aa678c1c69d506e58.jsonl`
Messages: 75

Started: 2026-08-27T08:35:38.519Z
Ended:   2026-08-27T08:41:24.618Z

---

### Prompt / result

**Read first:** `docs/evidence/p0-0-coreml-export.md` — the problem this task solves. Also skim your own memory `.claude/agent-memory/researcher-agent/MEMORY.md` and `coreml-ane-budget.md` for context on why this measurement matters, but this task itself is new — it's not R1-R4 again.

**The situation.** The approved iOS plan's very first deliverable (P0-0) needs two things the user does not currently have access to:
1. A machine that can run `coremltools` to convert PyTorch models to Apple's `.mlpackage` Core ML format. This specifically requires macOS — confirmed today: on Windows, `coremltools` installs but its compiled native libraries (`libcoremlpython`, `libmilstoragepython`) are missing from the PyPI wheel, so the final weight-serialization step fails with `RuntimeError: BlobWriter not loaded`. The export script itself (`tools/export_coreml_p0.py`) is written and correct — it just needs to run somewhere with real macOS coremltools.
2. A physical iPhone 11 or iPhone SE (2nd gen) — an A13-chip device, the floor of the project's supported range — connected to Xcode, to run Xcode's built-in Core ML Performance Report. This is what measures actual on-device latency per model configuration AND which compute unit (ANE vs GPU vs CPU) each layer actually gets dispatched to. That compute-unit-dispatch data is not optional — it's a hard gate in the plan (any layer landing on GPU disqualifies that model configuration, because GPU work is refused in the background on iOS and can crash the process).

**The user does not have a capable Mac or an A13 device readily available right now.** They've asked you to find solutions.

**What I need you to research, concretely, with real options and real costs/tradeoffs — not a generic "here's how CI works" essay:**

1. **For the macOS export step (software only, no physical device needed):** What are the actual options to run `coremltools.convert(...)` on real macOS without owning a Mac? Consider: GitHub Actions macOS runners (does the free/included tier have enough minutes and disk for this, does `coremltools` install cleanly there, any known gotchas running coremltools in CI), cloud Mac rental services (MacStadium, MacinCloud, AWS EC2 Mac instances, Scaleway Mac mini, others), and anything else viable. For each: rough cost, turnaround time to get a working environment, and whether it's a one-time need (rent for an hour) or something that gets used repeatedly across the project (in which case cost structure matters more).

2. **For the on-device A13 measurement (the harder one — needs a physical device connected to Xcode):** Does Xcode's Core ML Performance Report specifically require a physically-attached, locally-connected device, or is there any way to get equivalent data (per-layer compute-unit assignment + latency) from a REMOTE device? Investigate device-cloud services that support iOS: AWS Device Farm, BrowserStack App Live / Automate, Sauce Labs, Firebase Test Lab, others. For each, answer specifically: can you install a custom test harness/app and retrieve detailed timing + compute-unit logs, or is it limited to UI-testing-style interaction that wouldn't give us this data? Also investigate whether a small custom benchmarking app (using `MLComputePlan` or similar APIs to programmatically read per-layer compute-unit assignment, rather than Xcode's GUI Performance Report specifically) could run on a rented/remote device and just log results to a file — that might be more portable than needing Xcode's interactive UI.

3. **Buying vs renting the physical device.** An iPhone 11 or SE 2nd gen is old hardware now. What does a real used unit cost today, and is owning one outright (given the project will need repeated on-device testing throughout the whole iOS build, not just this one measurement) actually cheaper than any per-use rental/cloud option over, say, 20-30 future test sessions? This is a real comparison the user should see, not just "here are cloud options."

4. **Whether Apple's own program helps at all.** Does an Apple Developer Program membership include any device-access or lab-access benefit relevant to this (it used to have things like "Testflight" for real-world testing, but that needs the tester to own a device too — is there anything Apple offers that helps here)?

**Discipline for your answer:** state what's confirmed from official docs/pricing pages vs. what's your judgement. Flag anything that changes based on how MANY times over the project this kind of access will be needed (one-off vs recurring). Recommend one concrete path forward for RIGHT NOW (unblock P0-0 specifically) and separately note what the right long-term setup probably is for the rest of the iOS build, since those may not be the same answer.

Do not write code. Do not edit files outside your own agent-memory directory. When done, update your memory with what you found, since this will come up again for every future device-dependent phase. Return your findings as your final message.

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\docs\\evidence\\p0-0-coreml-export.md"}

```
1	# P0-0 — Core ML export needs macOS, not just the measurement (found 2026-08-27)
2	
3	> Evidence for the `coreml-export-requires-macos` row in [docs/STATE.md](../STATE.md)
4	> (Open). The pm-agent iOS plan's P0-0 handoff assumed the export step (producing
5	> `.mlpackage` files) could run anywhere and only the Xcode measurement needed a Mac.
6	> **That assumption is wrong** — the export step itself is blocked on this Windows
7	> machine, before any measurement question is reached.
8	
9	## What was attempted
10	
11	`tools/export_coreml_p0.py` — traces `BallNet` (v21 weights) with `torch.jit.trace`
12	and converts with `coremltools.convert(..., minimum_deployment_target=ct.target.iOS18)`
13	to the modern `.mlpackage`/`mlprogram` format; exports `yolo11m-pose` at 1280/640/384
14	via ultraly
… [3460 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\coreml-ane-budget.md"}

```
1	---
2	name: coreml-ane-budget
3	description: Core ML / A13 ANE budget for the perception stack — the desktop CPU cost ratio INVERTS on ANE; pose@1280 is the whole budget and int8 buys no speed on A13
4	metadata:
5	  type: project
6	---
7	
8	Researched 2026-08-27 for R2. **No A13 measurement exists anywhere, public or in this
9	repo.** Everything below is either a published number on other silicon or my arithmetic,
10	labelled as such.
11	
12	## The one number that is published and close to relevant
13	
14	Ultralytics' own iOS docs: **YOLO26n-pose, 640x640, int8, iPhone 17 Pro (A19 Pro,
15	16-core ANE), iOS 26.5.2 — 3.9 ms on `.cpuAndNeuralEngine`, 11.9 ms CPU-only.**
16	That is the *nano* model, at 640, on the newest silicon. Our default is
17	`yolo11m-pose @ 1280` on an A13.
18	
19	## T
… [4609 chars total]
```

> **tool** `Read` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\mobile-port-split.md"}

```
1	---
2	name: mobile-port-split
3	description: What of the shipped Python stack ports to iOS as-is, what needs a rebuild, and what is blocked entirely — from the 2026-08-27 static audit
4	metadata:
5	  type: project
6	---
7	
8	Condensed from `docs/evidence/mobile-viability-audit.md` (static read, 2026-08-27 — no
9	code run, no phone involved). **The port is split, not uniform.**
10	
11	**Portable as-is**
12	- `live.py` (187 lines) — genuinely streaming and causal, one frame in / a call out, no
13	  cv2 and no torch. Already ported to `mobile/live_calls.js`, verified bit-identical.
14	- `court.py` (109 lines) — constants and geometry, mirrored to `frontend/src/lib/court.js`,
15	  parity-enforced by `tests/test_js_mirror_parity.py`.
16	- `schema.py`, `analytics.py`, `scoring.py`, `correction
… [2922 chars total]
```

> **tool** `WebSearch` — {"query": "GitHub Actions macOS runner coremltools install 2026 disk space minutes"}

> **tool** `WebSearch` — {"query": "GitHub Actions macOS runner pricing per minute 2026 free tier private repo"}

> **tool** `WebSearch` — {"query": "MacinCloud pricing 2026 macOS Xcode rental hourly"}

> **tool** `WebSearch` — {"query": "AWS EC2 Mac instance pricing mac1 mac2 2026 dedicated host minimum"}

```
Web search results for query: "GitHub Actions macOS runner coremltools install 2026 disk space minutes"

Links: [{"title":"Controlling access to macOS large runners for GitHub Actions | Eclipse Foundation Blog | Open source news, insights, and updates","url":"https://blogs.eclipse.org/post/thomas-neidhart/controlling-access-macos-large-runners-github-actions"},{"title":"GitHub Actions: Introducing faster GitHub-hosted x64 macOS runners - The GitHub Blog","url":"https://github.blog/news-insights/product-news/github-actions-introducing-faster-github-hosted-x64-macos-runners/"},{"title":"Controlling access to macOS large runners for GitHub Actions | netomi","url":"https://netomi.github.io/eclipse/2024/08/06/macos-large-runners.html"},{"title":"Running GitHub Actions on a Mac Mini - Matthieu N
… [2765 chars total]
```

```
Web search results for query: "GitHub Actions macOS runner pricing per minute 2026 free tier private repo"

Links: [{"title":"The best GitHub Actions runners in 2026 (and hidden pricing traps to avoid) - Bitrise Blog","url":"https://bitrise.io/blog/post/best-github-actions-runners-in-2026-and-hidden-pricing-traps-to-avoid"},{"title":"Update to GitHub Actions pricing - GitHub Changelog","url":"https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/"},{"title":"GitHub Actions Pricing 2026: Free Tier, Per-Minute Rates, Real Costs | CICDCalculator.com","url":"https://cicdcalculator.com/github-actions"},{"title":"GitHub Actions Pricing 2026: $0.006/min, ARM, macOS 10x | cicdpipelinecost.com","url":"https://cicdpipelinecost.com/github-acti
… [2442 chars total]
```

```
Web search results for query: "MacinCloud pricing 2026 macOS Xcode rental hourly"

Links: [{"title":"MacinCloud Alternatives: Dedicated M4 Mac From $3.30/Day","url":"https://rentamac.io/macincloud-alternatives/"},{"title":"MacinCloud Checkout","url":"https://checkout.macincloud.com/select"},{"title":"XcodeClub Cloud Mac Rental: Online virtual Mac OSX VPS with XCode - XCodeClub","url":"https://xcodeclub.com/"},{"title":"MacinCloud Reviews 2026: Details, Pricing, & Features | G2","url":"https://www.g2.com/products/macincloud/reviews"},{"title":"MacinCloud Managed Server Plans","url":"https://checkout.macincloud.com/select/managed"},{"title":"MacinCloud - Xcode","url":"https://www.macincloud.com/pages/xcode.html"},{"title":"Pay as you go Macintosh development? A MacInCloud.com review – GameFr
… [1679 chars total]
```

```
Web search results for query: "AWS EC2 Mac instance pricing mac1 mac2 2026 dedicated host minimum"

Links: [{"title":"How to Set Up EC2 Mac Instances for macOS Development","url":"https://oneuptime.com/blog/post/2026-02-12-set-up-ec2-mac-instances-for-macos-development/view"},{"title":"mac1.metal & mac2.metal EC2: Pricing, Specs & Review | devDosvid blog","url":"https://devdosvid.blog/2021/01/19/mac1.metal-and-mac2.metal-ec2-instances-user-experience/"},{"title":"Billing and cost Mac m2 Istance | AWS re:Post","url":"https://repost.aws/questions/QURgjEEC8GTeKiGfJ8b46rkA/billing-and-cost-mac-m2-istance"},{"title":"mac1.metal pricing and specs - Vantage","url":"https://instances.vantage.sh/aws/ec2/mac1.metal"},{"title":"Amazon EC2 Mac instances - Amazon Elastic Compute Cloud","url":"https://d
… [2815 chars total]
```

> **tool** `WebSearch` — {"query": "AWS mac2.metal EC2 pricing per hour dedicated host cost 2026"}

> **tool** `WebSearch` — {"query": "Scaleway Apple silicon Mac mini M1 M2 M4 pricing per hour"}

> **tool** `WebSearch` — {"query": "MacStadium pricing mac mini m2 monthly hourly rental 2026"}

> **tool** `WebSearch` — {"query": "\"MLComputePlan\" Core ML per layer compute unit programmatic API"}

```
Web search results for query: "AWS mac2.metal EC2 pricing per hour dedicated host cost 2026"

Links: [{"title":"mac2.metal pricing and specs - Vantage","url":"https://instances.vantage.sh/aws/ec2/mac2.metal"},{"title":"mac2-m2pro.metal pricing and specs - Vantage","url":"https://instances.vantage.sh/aws/ec2/mac2-m2pro.metal"},{"title":"mac2-m2.metal pricing and specs - Vantage","url":"https://instances.vantage.sh/aws/ec2/mac2-m2.metal"},{"title":"Billing and cost Mac m2 Istance | AWS re:Post","url":"https://repost.aws/questions/QURgjEEC8GTeKiGfJ8b46rkA/billing-and-cost-mac-m2-istance"},{"title":"mac2-m2.metal specs and pricing | AWS | CloudPrice","url":"https://cloudprice.net/aws/ec2/instances/mac2-m2.metal"},{"title":"mac2-m2.metal - Amazon EC2 Instance Type","url":"https://aws-pricing.co
… [2174 chars total]
```

```
Web search results for query: "Scaleway Apple silicon Mac mini M1 M2 M4 pricing per hour"

Links: [{"title":"Scaleway adds Mac Mini M4 to Apple Silicon as a Service line-up - Telecompaper","url":"https://www.telecompaper.com/news/scaleway-adds-mac-mini-m4-to-apple-silicon-as-a-service-line-up--1525943"},{"title":"The Apple Mac mini M4 as a Service with Scaleway | Scaleway","url":"https://www.scaleway.com/en/news/apple-mac-mini-m4-as-a-service-with-scaleway/"},{"title":"Apple silicon Pre-installed Runners | Scaleway","url":"https://www.scaleway.com/en/mac-mini-runners/"},{"title":"Apple silicon M1 as-a-Service. Cloud Mac | Scaleway","url":"https://www.scaleway.com/en/hello-m1/"},{"title":"Apple Mac mini | Scaleway","url":"https://www.scaleway.com/en/apple-mac-mini/"},{"title":"Apple Silicon
… [1861 chars total]
```

```
Web search results for query: "MacStadium pricing mac mini m2 monthly hourly rental 2026"

Links: [{"title":"MacStadium Software Pricing & Plans 2026: See Your Cost","url":"https://www.vendr.com/marketplace/macstadium"},{"title":"Mac Stadium Review 2026. Is macstadium.com good web ...","url":"https://www.whtop.com/review/macstadium.com"},{"title":"MacStadium Pricing: Orka Virtualization & Bare Metal Macs","url":"https://macstadium.com/pricing"},{"title":"Pricing for Single Mac minis to Private Clouds at MacStadium | Benjamin Oakes","url":"http://www.benjaminoakes.com/2023/11/16/Pricing-for-Single-Mac-minis-to-Private-Clouds-at-MacStadium/"},{"title":"MacStadium Pricing (2026): Explore Plans, Features & Key Insights","url":"https://www.softwaresuggest.com/macstadium/pricing"},{"title":"MacS
… [2183 chars total]
```

```
Web search results for query: ""MLComputePlan" Core ML per layer compute unit programmatic API"

Links: [{"title":"Model APIs — coremltools API Reference 8.1 documentation","url":"https://apple.github.io/coremltools/source/coremltools.models.html"},{"title":"MLModel Utilities — Guide to Core ML Tools","url":"https://apple.github.io/coremltools/docs-guides/source/mlmodel-utilities.html"},{"title":"GitHub - freedomtan/coreml_modelc_profling: per op profiling in using Core ML MLComputePlan","url":"https://github.com/freedomtan/coreml_modelc_profling"},{"title":"Optimize your Core ML usage - WWDC22 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2022/10027/"},{"title":"GitHub - fguzman82/CoreMLProfiler: Tool for visual profiling Core ML models, compatible with bo
… [2610 chars total]
```

> **tool** `WebSearch` — {"query": "AWS Device Farm iOS custom test run retrieve files instrumentation XCTest device console logs"}

> **tool** `WebSearch` — {"query": "BrowserStack App Automate iOS custom instrumentation retrieve files device logs real device"}

> **tool** `WebSearch` — {"query": "used iPhone SE 2nd generation price 2026 iPhone 11 used price"}

> **tool** `WebSearch` — {"query": "Apple Developer Program device lab benefit remote device testing benefits"}

```
Web search results for query: "AWS Device Farm iOS custom test run retrieve files instrumentation XCTest device console logs"

Links: [{"title":"AWS Device farm integration on iOS - Halodoc Blog","url":"https://blogs.halodoc.io/device-farms-ios/"},{"title":"Test User Interfaces in iOS Apps with XCTest UI and AWS Device Farm | Front-End Web & Mobile","url":"https://aws.amazon.com/blogs/mobile/test-user-interfaces-in-ios-apps-with-xctest-ui-and-aws-device-farm/"},{"title":"AWS Device Farm FAQs | Mobile & Web App Testing | Amazon Web Services","url":"https://aws.amazon.com/device-farm/faqs/"},{"title":"Integrating Device Farm with XCTest for iOS - AWS Device Farm","url":"https://docs.aws.amazon.com/devicefarm/latest/developerguide/test-types-ios-xctest.html"},{"title":"GitHub - aws-samples/aw
… [2985 chars total]
```

```
Web search results for query: "BrowserStack App Automate iOS custom instrumentation retrieve files device logs real device"

Links: [{"title":"How to use Device Logs in Android and iOS to report issue | BrowserStack","url":"https://www.browserstack.com/guide/use-device-logs-on-android-and-ios"},{"title":"View app and device logs on BrowserStack real devices using App Live | BrowserStack Docs","url":"https://www.browserstack.com/docs/app-live/session-debugging/app-device-logs"},{"title":"XCUITest Mobile App Testing on Real Device Cloud | BrowserStack","url":"https://www.browserstack.com/app-automate/xcuitest"},{"title":"BrowserStack App Automate: Mobile App Testing on Real Devices | Bug0","url":"https://bug0.com/knowledge-base/browserstack-app-automate"},{"title":"Debug iOS Apps on Real Dev
… [3150 chars total]
```

```
Web search results for query: "used iPhone SE 2nd generation price 2026 iPhone 11 used price"

Links: [{"title":"iPhone SE 2nd Generation Price Guide 2026","url":"https://electronics.alibaba.com/buyingguides/iphone-se-2nd-gen-price-guide-2026"},{"title":"iPhone SE 2 Price Guide: What It’s Worth in 2026","url":"https://electronics.alibaba.com/buyingguides/iphone-se-2-price-guide-2026"},{"title":"Apple iPhone SE 2nd Gen 2020 Prices, August 2026 - Swappa","url":"https://swappa.com/prices/apple-iphone-se-2nd-gen"},{"title":"How Much is an iPhone SE / SE 2 Worth? (2026)","url":"https://www.bankmycell.com/blog/how-much-is-an-iphone-se-worth"},{"title":"Apple iPhone SE (2nd Generation) Refurbished & Pre-Owned Phones - Best Buy","url":"https://www.bestbuy.com/site/searchpage.jsp?browsedCategory=pc
… [3676 chars total]
```

```
Web search results for query: "Apple Developer Program device lab benefit remote device testing benefits"

Links: [{"title":"Testing on Real iPhones at Scale: What the App Store's Top Developers Do Differently - AppleMagazine","url":"https://applemagazine.com/testing-real-iphones-at-scale-developers-a13b/amp/"},{"title":"Devices | Apple Developer Documentation","url":"https://developer.apple.com/documentation/appstoreconnectapi/devices"},{"title":"Registering iOS test devices - Codemagic Docs","url":"https://docs.codemagic.io/testing/ios-provisioning/"},{"title":"TestFlight","url":"https://en.wikipedia.org/wiki/TestFlight"},{"title":"How to test on device with 'Sign i… | Apple Developer Forums","url":"https://developer.apple.com/forums/thread/8789"},{"title":"Designating iOS Devices for De
… [2816 chars total]
```

> **tool** `WebSearch` — {"query": "Xcode Core ML Performance Report requires physically connected device Instruments"}

> **tool** `WebSearch` — {"query": "Sauce Labs real device cloud iOS custom app upload retrieve logs"}

> **tool** `WebSearch` — {"query": "MLComputePlan runs on device only host machine Apple Neural Engine query different device profile"}

```
Web search results for query: "Xcode Core ML Performance Report requires physically connected device Instruments"

Links: [{"title":"Deploy machine learning and AI models on-device with Core ML - WWDC24 - Videos - Apple Developer","url":"https://developer.apple.com/videos/play/wwdc2024/10161/"},{"title":"Core ML Model Performance report e… | Apple Developer Forums","url":"https://forums.developer.apple.com/forums/thread/767412"},{"title":"Core ML | Apple Developer Forums","url":"https://developer.apple.com/forums/tags/core-ml/?page=6"},{"title":"Xcode Instruments usage to improve app performance","url":"https://www.avanderlee.com/debugging/xcode-instruments-time-profiler/"},{"title":"Optimize your Core ML usage - WWDC22 - Videos - Apple Developer","url":"https://developer.apple.com/videos/
… [3035 chars total]
```

```
Web search results for query: "Sauce Labs real device cloud iOS custom app upload retrieve logs"

Links: [{"title":"Appium Testing with Real Devices | Sauce Labs Documentation","url":"https://docs.saucelabs.com/mobile-apps/automated-testing/appium/real-devices/"},{"title":"Private Devices from Sauce Labs","url":"https://saucelabs.com/products/private-devices-real-device-cloud"},{"title":"Sauce Labs Real Device Cloud Data Sheet","url":"https://saucelabs.com/resources/data-sheet/real-device-cloud"},{"title":"Real Device Cloud","url":"https://saucelabs.com/products/mobile-testing/real-device-cloud"},{"title":"Mobile App Testing FAQ | Sauce Labs Documentation","url":"https://docs.saucelabs.com/mobile-apps/mobile-faq/"},{"title":"Using Real and Virtual Mobile Devices for Testing | Sauce Labs Do
… [2301 chars total]
```

```
Web search results for query: "MLComputePlan runs on device only host machine Apple Neural Engine query different device profile"

Links: [{"title":"MLComputeUnits.cpuAndNeuralEngine | Apple Developer Documentation","url":"https://developer.apple.com/documentation/coreml/mlcomputeunits/cpuandneuralengine"},{"title":"MLComputeUnits | Apple Developer Documentation","url":"https://developer.apple.com/documentation/coreml/mlcomputeunits?language=objc"},{"title":"ML Compute | Apple Developer Forums","url":"https://developer.apple.com/forums/tags/ml-compute?sortBy=oldest"},{"title":"Apple - CoreML | onnxruntime","url":"https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html"},{"title":"Does my Core ML model run on Apple’s Neural Engine? - Fritz ai","url":"https://fritz.ai/d
… [2650 chars total]
```

> **tool** `WebSearch` — {"query": "Corellium iOS virtual device Core ML Neural Engine hardware accurate benchmark"}

> **tool** `WebSearch` — {"query": "AWS Device Farm custom artifacts XCTest write file device path retrieve after run"}

> **tool** `WebSearch` — {"query": "MacinCloud physical iOS device attached remote Xcode wireless debugging iPhone"}

```
Web search results for query: "Corellium iOS virtual device Core ML Neural Engine hardware accurate benchmark"

Links: [{"title":"Core ML performance benchmark iPhone 15 (2023) | Photoroom","url":"https://www.photoroom.com/inside-photoroom/core-ml-performance-benchmark-2023-edition"},{"title":"Corellium Virtual Hardware","url":"https://www.corellium.com/"},{"title":"GitHub - john-rocky/apple-silicon-llm-bench: Neutral, reproducible benchmark for local LLMs on Apple Silicon (Mac · iPhone · iPad) — MLX, llama.cpp, CoreML, Apple Foundation Models","url":"https://github.com/john-rocky/apple-silicon-llm-bench"},{"title":"iOS 26 Testing + Risk Scoring | Corellium 7.7 Release","url":"https://www.corellium.com/blog/corellium-introduces-ios-26-support-and-newest-mobile-device-models"},{"title":"Cor
… [2853 chars total]
```

```
Web search results for query: "AWS Device Farm custom artifacts XCTest write file device path retrieve after run"

Links: [{"title":"Test spec reference and syntax - AWS Device Farm","url":"https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environment-yaml-file-structure.html"},{"title":"Custom test environments in AWS Device Farm - AWS Device Farm","url":"https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments.html"},{"title":"Integrating Device Farm with XCTest for iOS - AWS Device Farm","url":"https://docs.aws.amazon.com/devicefarm/latest/developerguide/test-types-ios-xctest.html"},{"title":"Front-End Web & Mobile","url":"https://aws.amazon.com/blogs/mobile/custom-artifacts-on-aws-device-farm"},{"title":"Environment variables for cust
… [3510 chars total]
```

```
Web search results for query: "MacinCloud physical iOS device attached remote Xcode wireless debugging iPhone"

Links: [{"title":"Run and debug on a physical iPhone wirelessly in Xcode","url":"https://mszpro.com/article/xcode-wireless-physical-device-debugging"},{"title":"What is Wireless Debugging: A Complete Guide for iOS Development","url":"https://log.dog/blog/wireless-debugging/"},{"title":"How Do I Connect My Physical iPhone or USB device to MacinCloud Servers? : Support Portal","url":"https://support.macincloud.com/support/solutions/articles/8000007775-how-do-i-connect-my-physical-iphone-or-usb-device-to-the-server-"},{"title":"XCode - Remotely Debug iOS Device · digital.ai continuous-testing","url":"https://docs.digital.ai/continuous-testing/docs/lt/live-testing-home/resources-for-
… [2861 chars total]
```

> **tool** `WebSearch` — {"query": "AWS Device Farm device list iPhone 11 iPhone SE 2020 available 2026"}

> **tool** `WebSearch` — {"query": "BrowserStack device list iPhone 11 iPhone SE 2020 real device available 2026"}

> **tool** `WebSearch` — {"query": "AWS Device Farm pricing per minute private device unmetered plan 2026"}

```
Web search results for query: "AWS Device Farm device list iPhone 11 iPhone SE 2020 available 2026"

Links: [{"title":"IPhone SE (2nd generation)","url":"https://en.wikipedia.org/wiki/IPhone_SE_(2nd_generation)"},{"title":"How to create a custom device pool on AWS Device Farm","url":"https://github.com/pytorch/executorch/wiki/How-to-create-a-custom-device-pool-on-AWS-Device-Farm"},{"title":"IPhone 11","url":"https://en.wikipedia.org/wiki/IPhone_11"},{"title":"IPhone SE (3rd generation)","url":"https://en.wikipedia.org/wiki/IPhone_SE_(3rd_generation)"},{"title":"AWS Device farm integration on iOS - Halodoc Blog","url":"https://blogs.halodoc.io/device-farms-ios/"},{"title":"IPod Touch (7th generation)","url":"https://en.wikipedia.org/wiki/IPod_Touch_(7th_generation)"},{"title":"IOS 16","url"
… [2441 chars total]
```

```
Web search results for query: "BrowserStack device list iPhone 11 iPhone SE 2020 real device available 2026"

Links: [{"title":"BrowserStack - 3000+ Desktop & Mobile Browsers for Screenshot Testing","url":"https://www.browserstack.com/list-of-browsers-and-platforms/screenshots"},{"title":"Android and iOS Real Devices for Automated App Testing - BrowserStack App Automate","url":"https://www.browserstack.com/list-of-browsers-and-platforms/app_automate"},{"title":"BrowserStack - 3000+ Desktop & Mobile Browsers for Selenium Testing","url":"https://www.browserstack.com/list-of-browsers-and-platforms/automate"},{"title":"Android & iOS Real Devices for Manual App Testing - BrowserStack App Live","url":"https://www.browserstack.com/list-of-browsers-and-platforms/app_live"},{"title":"BrowserStack -
… [2253 chars total]
```

```
Web search results for query: "AWS Device Farm pricing per minute private device unmetered plan 2026"

Links: [{"title":"AWS Device Farm | Pricing Flashcards in Anti Gondu's ag-AWS 2018 - By Service Section - FAQs Collection","url":"https://www.brainscape.com/flashcards/aws-device-farm-pricing-13222863/packs/21349959"},{"title":"AWS Device Farm FAQs | Mobile & Web App Testing | Amazon Web Services","url":"https://aws.amazon.com/device-farm/faqs/"},{"title":"AWS Device Farm vs BrowserStack: Real Costs | DeviceLab","url":"https://devicelab.dev/blog/aws-device-farm-vs-browserstack"},{"title":"Why AWS Device Farm Pricing Surprises Teams at Scale? | Autonoma AI","url":"https://getautonoma.com/blog/aws-device-farm-pricing"},{"title":"AWS Device Farm Alternatives Compared for 2026","url":"https:/
… [2471 chars total]
```

> **tool** `WebSearch` — {"query": "GitHub-hosted macOS runner specs 2026 cores memory disk M1 M2 standard vs large"}

> **tool** `WebSearch` — {"query": "coremltools GitHub Actions CI known issues install failure macOS runner"}

> **tool** `WebSearch` — {"query": "MacinCloud dedicated server plan monthly price Xcode admin access"}

```
Web search results for query: "GitHub-hosted macOS runner specs 2026 cores memory disk M1 M2 standard vs large"

Links: [{"title":"GitHub Actions now offers M2 Pro-powered hosted runners in public preview - GitHub Changelog","url":"https://github.blog/changelog/2025-07-16-github-actions-now-offers-m2-pro-powered-hosted-runners-in-public-preview/"},{"title":"Faster macOS Runners for GitHub Actions | Bitrise Build Hub","url":"https://bitrise.io/platform/build-hub"},{"title":"Introducing the new, Apple silicon powered M1 macOS larger runner for GitHub Actions - The GitHub Blog","url":"https://github.blog/news-insights/product-news/introducing-the-new-apple-silicon-powered-m1-macos-larger-runner-for-github-actions/"},{"title":"Fast MacOS runners for GitHub Actions - WarpBuild Blog","url":"http
… [2581 chars total]
```

```
Web search results for query: "MacinCloud dedicated server plan monthly price Xcode admin access"

Links: [{"title":"Try a Mac server today with MacinCloud! : Support Portal","url":"https://support.macincloud.com/support/solutions/articles/8000044699-what-is-macincloud-s-managed-server-plan-"},{"title":"MacinCloud Checkout","url":"https://checkout.macincloud.com/select"},{"title":"Dedicated Server Plan - Monthly","url":"https://checkout.macincloud.com/select/dedicated?type=dedicated&tab=1&os=sn&cpucore=4&ram=8&hdint=50&rdp=1&preset=general&location=du&platform=i7&flavor=plain&payment_cycle=m&hdext=0&bandwidth=0"},{"title":"MacinCloud - Xcode","url":"https://www.macincloud.com/pages/xcode.html"},{"title":"MacinCloud - Dedicated","url":"https://www.macincloud.com/pages/dedicated.html"},{"tit
… [2327 chars total]
```

```
Web search results for query: "coremltools GitHub Actions CI known issues install failure macOS runner"

Links: [{"title":"Need help reproducing macos failure with GitHub actions · community · Discussion #118963","url":"https://github.com/orgs/community/discussions/118963"},{"title":"Cannot install on M-chip mac by following https://apple.github.io/coremltools/docs-guides/source/installing-coremltools.html · Issue #2396 · apple/coremltools","url":"https://github.com/apple/coremltools/issues/2396"},{"title":"Python 3.12 Support · Issue #2129 · apple/coremltools","url":"https://github.com/apple/coremltools/issues/2129"},{"title":"Numerous build issues with newer CMake, Python, virtual environments · Issue #2376 · apple/coremltools","url":"https://github.com/apple/coremltools/issues/2376"},{"
… [2942 chars total]
```

> **tool** `WebFetch` — {"url": "https://www.macincloud.com/pages/dedicated.html", "prompt": "What are the monthly and hourly prices for MacinCloud's Dedicated Server plans? List the cheapest tier price and specs (CPU/RAM/st…

> **tool** `WebSearch` — {"query": "Apple Developer Program annual fee $99 2026 benefits TestFlight device testing"}

```
# MacinCloud Dedicated Server Pricing

**Cheapest Tier: Intel Plan at $59/month**

The lowest-cost option features an "Intel 4-Core CPU, 8GB RAM, 120GB SSD Storage" at $59 monthly. Hourly pricing is not listed on this page.

**Admin Access:** Yes. The service provides "full macOS administrator/root/sudo access."

**Xcode:** The page does not mention whether Xcode is included. Users must "Bring and Use Your Own Software Licenses," suggesting they would need to provide their own copy if desired.
```

```
Web search results for query: "Apple Developer Program annual fee $99 2026 benefits TestFlight device testing"

Links: [{"title":"Apple Developer Account: $99/Year Program Cost and Benefits","url":"https://www.appaloosa.io/blog/what-is-the-apple-development-program"},{"title":"Apple Developer Fee 2026: What $99 a Year Actually Covers","url":"https://magora-systems.com/apple-developer-fee/"},{"title":"Membership Details - Apple Developer Program - Apple Developer","url":"https://developer.apple.com/programs/whats-included/"},{"title":"Apple Developer Program: Free vs. Paid Explained | Bitrig","url":"https://bitrig.com/blog/apple-developer-program-free-vs-paid"},{"title":"Apple Developer Program Cost: The $99/Year Fee Explained (2026)","url":"https://appbuilder24.com/blog/apple-developer-acc
… [2919 chars total]
```

### Assistant

## Two separate blockers, two separate fixes — don't try to solve them with one rental

**Finding.** The export step (needs macOS + `coremltools`, no physical device) and the on-device measurement step (needs a physically-reachable A13 iPhone + Xcode) have almost no infrastructure in common. Solve them separately; picking one "Mac in the cloud" service to cover both is the wrong shape for the problem.

---

### 1. macOS export — solved, cheaply, and repeatably, with GitHub Actions

**Recommendation: a GitHub Actions macOS CI job.** This is the right answer for right now AND for the rest of the build, not a stopgap.

- **Cost, confirmed:** Standard macOS runners are $0.062/min as of the Jan 2026 GitHub Actions price cut; a large M1/M2 Pro runner is $0.16/min. macOS minutes bill at a **10x multiplier** against your included-minutes allowance (not against a separate macOS quota). A GitHub Free private-repo plan includes 2,000 Linux-equivalent minutes/month → **~200 macOS-equivalent minutes/month at $0 marginal cost.**
- **Turnaround:** minutes, not hours — trigger on push or `workflow_dispatch`, `pip install coremltools`, run `tools/export_coreml_p0.py`, upload the `.mlpackage` as a build artifact. A convert-and-serialize job for BallNet + yolo11m-pose at three resolutions is very likely a 5–15 minute job, so you'd need ~15-20 runs/month before this stops being free.
- **Gotchas checked, not found:** `coremltools` on GH Actions installs the standard PyPI wheel (prebuilt, not built-from-source), so the M-series-build-from-source issues that dominate GitHub issue threads for `coremltools` don't apply here. Python 3.9–3.12 wheels are published; confirm your export script's interpreter version matches.
- **Gotcha flagged, not resolved:** the M1/M2 Pro large runners report **14 GB total storage**. `torch` + `ultralytics` + intermediate MIL/weights for a 1920px pose export could plausibly get close to that on a from-scratch runner image. Cheap to test — run it once before treating this as settled.
- Rejected for this step: MacinCloud (interactive, ~$1/hr — fine as a fallback if the CI job needs live debugging, but strictly worse than free CI for a scripted, repeated job); AWS EC2 Mac / Scaleway (Apple's EULA imposes a **24-hour minimum dedicated-host lease** on both — confirmed on AWS docs, and Scaleway states the same constraint — so even a 10-minute export job costs a minimum of ~$15.60 on AWS mac2.metal or ~€2.64–5.76 on Scaleway; wrong shape for a job you'll run dozens of times).

---

### 2. On-device A13 measurement — this is the real problem, and it has a wrinkle worth flagging on its own

**Confirmed from Apple's own developer forums (thread 767412):** Xcode's Core ML Performance Report requires the device to show as **"Connected,"** which needs the transport layer established by a physical USB pairing to that specific Mac — there is no remote-network-only mode. Renting a Mac in the cloud does not solve this by itself; you still need a device physically reachable *from that machine*.

**A second thing that same thread reports, which changes the plan, not just the access method:** Performance Reports profiled on an iPhone with compute unit set to **`.all`, `.cpuAndGPU`, or `.cpuAndNeuralEngine` are reported to crash** ("There was an error creating the performance report... crashed on device" / "Unable to compute the prediction using ML Program"). Only **CPU-only on iPhone**, or **any compute unit on Mac**, is reported to work reliably. If current, this directly blocks the exact measurement your plan's hard gate needs (ANE-vs-GPU dispatch, on iPhone, with `.cpuAndNeuralEngine`) — independent of which cloud/device path you pick. **Confidence: 55%** — one forum thread, unclear if still open in the current Xcode/iOS 18 toolchain. Cheapest falsifying observation: the very first thing anyone does with any physical iPhone should be exactly this test, before spending a cent on remote access.

**The workaround, which also happens to be the more portable path:** `MLComputePlan` (Swift API, on-device since iOS 17.4) lets you query per-op compute-device assignment and estimated cost **programmatically, inside your own app code**, instead of through Xcode's GUI. A small benchmark harness — load the model with a pinned `computeUnits`, run N predictions, call `MLComputePlan` for the op→device mapping, write JSON to a file — sidesteps the GUI crash risk entirely, and is exactly the shape of artifact a device farm can capture. **Important nuance, confirmed:** `MLComputePlan` reports the compute plan *for whatever hardware is executing it* — running it from Python/`coremltools` on a Mac tells you what the Mac's own Apple Silicon would do, **not** what an iPhone A13 would do. It only answers your question if it runs inside a compiled app on the actual iPhone.

**Device-access options for that harness (or for Xcode's GUI, if the crash risk turns out not to apply):**

| Option | What it actually gives you | Cost | Confirmed vs. judgement |
|---|---|---|---|
| **AWS Device Farm, custom XCTest** | Full custom test binary on a real device; writes to `$DEVICEFARM_LOG_DIR`, zipped and downloadable as an artifact after the run — this is a real, documented mechanism, not a UI-testing-only tool | $0.17/device-minute pay-as-you-go; unmetered private-device plans from $200-250/device/month (breakeven ~1,470 min/month, i.e., ~24 hrs — far more than this needs) | Mechanism confirmed from AWS docs. **iPhone 11 / SE2020 current live availability in the device pool is NOT confirmed** — these are 6–7-year-old units and farms retire old stock; check the live console before committing. |
| **BrowserStack App Automate** | Instrumentation + device logs, real devices; **iOS has no confirmed file upload/download from real devices** in their docs (Android does, iOS doesn't) — this may block getting a custom JSON artifact off the device | Not itemized here | Retrieval limitation confirmed from BrowserStack docs; treat as weaker than AWS Device Farm for this specific need. |
| **Corellium** (virtual ARM iOS device) | Marketed as hardware-accurate ARM CPU virtualization for security research | N/A | **Judgement, 60% confidence this is a dead end.** No confirmation anywhere that ANE silicon is passed through or faithfully emulated in a hypervisor-virtualized device. This is exactly the kind of silent-fallback-to-CPU/GPU your plan is designed to catch, from a tool least likely to represent it correctly. Don't pursue without an explicit vendor confirmation of ANE fidelity. |
| **MacinCloud (own the iPhone, tunnel it to a rented Mac)** | MacinCloud's own support docs describe this exact workflow: plug your physically-owned iPhone into any local machine, use **FlexiHub** (3rd-party USB-over-IP) to redirect it to a MacinCloud **Dedicated** server, then use Xcode normally | Dedicated tier from **$59/mo** (Intel, 4-core/8GB/120GB, confirmed root/admin access) or PAYG at ~$1/hr if PAYG supports the redirect (unconfirmed — the support article ties FlexiHub specifically to Dedicated) | Mechanism confirmed to exist and be MacinCloud-endorsed. **Not confirmed** that Xcode's Performance Report transport (as opposed to ordinary run/debug) tolerates the added latency of a USB-over-IP tunnel — real risk, untested. |

---

### 3. Buy vs. rent the physical device — buying wins, and by more than the raw price suggests

**Confirmed prices (Aug 2026, Swappa/BackMarket):** used iPhone SE 2nd gen $64–98 (best-price listing $68); used iPhone 11 $121–176 (low end from Swappa, refurb range from BackMarket). SE2 is the cheaper of the project's two named floor devices and shares the A13 chip.

**The breakeven math lines up almost exactly with your own framing.** At AWS Device Farm's $0.17/min, a realistic 15–20 minute benchmarking session costs $2.50–3.50. A $68–98 SE2 breaks even against that at **roughly 20–28 sessions** — you named "20-30 future test sessions" independently, and that's almost exactly the crossover point, meaning **owning wins under almost any reasonable usage projection**, not just an aggressive one.

**Two things a rental can't give you at any price, which matter to this specific plan:**
- **Unhurried, unmetered wall-clock testing.** `coreml-ane-budget` memory flags "no published sustained-ANE-throughput figure for any A13-generation device" as an open finding — measuring 3+ minutes of sustained inference to see real thermal derating is exactly the kind of test that per-minute billing actively discourages you from running long enough to be honest.
- **Interactive iteration.** Xcode's Instruments (Time Profiler, thermal/energy gauges) is built for a device sitting on your desk. A rented remote session turns every retry into a billed event.

---

### 4. Apple Developer Program — confirmed, does not help here

$99/year gets you App Store distribution, TestFlight (up to 100 internal / 10,000 external testers — but **testers must own their own device**, exactly the limitation you already knew about), beta OS access, and 2 DTS technical-support incidents/year. **No device-lab or remote-device-loan benefit is documented anywhere in Apple's own program page**, and nothing in general search turned one up. This is an absence-of-evidence finding (confidence 80% there is no such benefit), not a confirmed negative — if you want certainty, a DTS incident is the one channel that could actually answer "does Apple offer this" authoritatively, since it's a direct line to Apple engineers.

---

## For the PM

**Right now, to unblock P0-0 specifically:**
1. Stand up the GitHub Actions macOS CI job for the export step today — it's ~free, needs no device, and is reusable for every future model iteration, not just this one.
2. Buy a used iPhone SE 2nd gen (~$70-100) rather than renting device access. It breaks even against the cheapest device-farm option at almost exactly the usage volume you already expect, and it's the only path that gives you unmetered thermal/sustained-load testing — which is an open, unmeasured question the project already needs answered and a metered rental structurally discourages.
3. Before spending anything further, run the single cheapest test that exists: put a converted model on ANY physically reachable iPhone (borrowed for ten minutes is enough) and open Xcode's Performance Report with `.cpuAndNeuralEngine` selected. If it crashes as the Apple forum thread describes, build the `MLComputePlan`-based Swift harness instead — that decision changes the shape of the whole rest of the plan's measurement tooling, so it should happen before more infrastructure is built around the GUI tool.

**Long-term, for the rest of the iOS build:** the combination of (owned A13 device + GitHub Actions CI for exports) is very likely both cheaper and higher-quality than any recurring rental, given how many times this project will touch Core ML export and on-device measurement between now and ship. Device farms remain useful only as a supplementary breadth check (different iOS versions, different A13-class devices) later — not as the primary tool.

**Open questions I couldn't close:** whether the Xcode Performance Report ANE-profiling crash is still current; whether AWS Device Farm's live pool still carries iPhone 11/SE2020 hardware; whether FlexiHub's USB tunnel is fast/stable enough for Xcode's device-profiling transport specifically (vs. ordinary debugging, which it's documented to handle). All three are cheap to check directly and shouldn't be taken on my word.

Relevant existing file: `docs/evidence/p0-0-coreml-export.md` (the problem this research answers).

---

I've saved this to my agent memory (`macos-and-device-access-options.md`, indexed in `MEMORY.md`) since you flagged this will recur for every future device-dependent phase of the iOS build.

> **tool** `Write` — {"file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\macos-and-device-access-options.md", "content": "---\nname: macos-and-device-access-options\ndes…

```
File created successfully at: e:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\macos-and-device-access-options.md (file state is current in your context — no need to Read it back)
```

> **tool** `Edit` — {"replace_all": false, "file_path": "e:\\Claude Outputs\\Cowork Tasks\\Swing Vision\\.claude\\agent-memory\\researcher-agent\\MEMORY.md", "old_string": "- [Point-boundary ground truth](point-boundary-…

```
The file e:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\MEMORY.md has been updated successfully. (file state is current in your context — no need to Read it back)
```

### Assistant

Findings delivered above. Memory updated:

- `e:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\macos-and-device-access-options.md` (new)
- `e:\Claude Outputs\Cowork Tasks\Swing Vision\.claude\agent-memory\researcher-agent\MEMORY.md` (indexed)

Relevant existing file I read for context: `e:\Claude Outputs\Cowork Tasks\Swing Vision\docs\evidence\p0-0-coreml-export.md`

No code was written and no files outside my agent-memory directory were edited.
