TASK: DONE. Built ios/ latency harness (Swift app, XcodeGen project.yml, CI
workflow, README) per lead brief. All deliverables written; NOT built, NOT
triggered (no CI run), NOT pushed — per brief. Agent memory updated
(ios_latency_harness_built.md + MEMORY.md index). Reported to lead.

DELIVERABLES (final):
- ios/project.yml — XcodeGen spec, deploymentTarget iOS 18.0, unsigned
  (CODE_SIGNING_ALLOWED=NO etc), bundle id com.swingpath.latencyharness.
- ios/App/{Info.plist, LatencyHarnessApp.swift, ContentView.swift,
  ModelRunner.swift, Stats.swift, ResultsLogger.swift}.
- ios/.gitignore (excludes generated .xcodeproj/build/ipa).
- ios/README.md — design rationale, exact Windows transfer + sideload steps,
  how to read the numbers, explicit "what I could not verify" section.
- .github/workflows/ios-latency-harness.yml — workflow_dispatch ONLY, xcodegen
  generate -> unsigned xcodebuild -> zip to .ipa -> upload-artifact.

KEY DESIGN DECISIONS (see ios/README.md + agent-memory for full reasoning):
- Documents-directory model loading, NOT bundling at build time (bundling would
  tie every model swap of 8 variants to a fresh 10x-billed macOS CI build).
- On-device runtime compile via MLModel.compileModel(at:) (public API, accepts
  .mlpackage), NOT Xcode build-time compile.
- Pose model's exact CoreML input name/type unknown without a Mac -> solved by
  building dummy inputs GENERICALLY from model.modelDescription rather than
  hardcoding, so the same code covers BallNet's known `frames` (1,9,288,512)
  input and the pose model's unknown one.
- Model transfer: zip .mlpackage on Windows -> Apple Devices (MS Store) File
  Sharing -> iOS Files app native Extract. Avoids the unverified question of
  whether nested-folder drag-and-drop preserves structure.
- Caught + fixed a real bug before finishing: sustained-loop was rebuilding the
  1.3M-element dummy MLMultiArray on every single sample instead of once per
  sweep, which would have added spurious CPU/heat unrelated to the model and
  confounded the thermal-steady-state measurement this harness exists for.
- Xcode-version selection in CI is a soft hedge (prefers Xcode_16* if present,
  else falls through) since I can't verify what macos-14 currently ships.

NOT DONE (explicitly out of scope per brief): triggering CI, pushing,
docs/STATE.md (lead owns it), any camera/UI/product work.
