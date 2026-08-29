# researcher memory

Index. Detail in the topic files. Inherited 2026-08-28.

**Before proposing any investigation, read `docs/STATE.md` "What has not worked"** — ~50
rows, each measured here under a pre-registered gate. Nine were re-proposed at least once.

## The existing pipeline

- [Court detection negatives](court-detection-negatives.md) — ~20 rejected approaches; the detector finds the lines but cannot assemble them
- [Player detection negatives](player-detection-negatives.md) — far-player: pose-quality, body_relative, foot-gate (x2) all dead; motion+contrast partially tested, docstring "UNRUN" traps found stale twice
- [Ball negatives](ball-negatives.md) — detector work is CLOSED; chain work is open
- [Project method rules](project-method-rules.md) — gold discipline, threshold scaling, the screening proxy that does not predict the gate
- [Open questions](open-questions.md) — what is genuinely unresolved

## iOS / on-device

- [Mobile port split](mobile-port-split.md) — what ports, what is a rebuild, what is blocked
- [iOS background compute](ios-background-compute.md) — no multi-hour background job exists; ANE-only is mandatory
- [Core ML / A13 ANE budget](coreml-ane-budget.md) — the desktop ball-vs-pose cost ratio INVERTS on ANE; int8 buys no speed on A13
- [Sensor court priors](sensor-court-priors.md) — gravity usable, yaw useless, LiDAR does not reach the far baseline; 1 deg pitch = 6 px
- [Point-boundary ground truth](point-boundary-ground-truth.md) — boundaries are LOGIC, so labels are evaluation-only; audio is the strongest compliant signal; priced 2026-08-28: 3-6h, Hardcourt+Clay only, Shell/Grass have no eligible footage
- [macOS + A13 device access](macos-and-device-access-options.md) — GH Actions CI for Core ML export; Xcode Performance Report needs a local USB device
- [Audio hit detection mobile port](audio-hit-detection-mobile-port.md) — corpus audio-track presence unverified since Session E3b; rolling-median floor is O(n·win), vDSP has no equivalent; this session had no exec tool at all

**Settled:** iOS only, A13+, Core ML/ANE only. No Android, no TFLite, no NNAPI.
