# researcher-agent memory

Index only. Detail lives in the topic files. Covers ~2026-06-20 onward.

**Before proposing any investigation, read `docs/STATE.md` "What has not worked"** —
~50 rows, each already measured here under a pre-registered gate. Nine distinct ideas in
it were re-proposed at least once.

## The existing pipeline — what has already been tried

- [Court detection negatives](court-detection-negatives.md) — ~20 rejected approaches with reasons; the detector finds the lines but cannot assemble them
- [Ball negatives](ball-negatives.md) — detector work is CLOSED, chain work is open; four detector gains delivered nothing downstream
- [Project method rules](project-method-rules.md) — gold discipline, threshold scaling, the screening proxy that does not predict the gate
- [Open questions](open-questions.md) — what is genuinely unresolved, and the dead ends found inside each

## iOS / on-device (researched 2026-08-27)

- [Mobile port split](mobile-port-split.md) — what ports as-is, what is a rebuild, what is blocked; condensed from `docs/evidence/mobile-viability-audit.md`
- [iOS background compute](ios-background-compute.md) — no multi-hour background job exists on iOS; GPU work from background is refused, so ANE-only is mandatory
- [Core ML / A13 ANE budget](coreml-ane-budget.md) — the desktop ball-vs-pose cost ratio INVERTS on ANE; int8 buys no speed on A13; frame rate is the real lever
- [Sensor court priors](sensor-court-priors.md) — gravity usable, yaw useless, ARKit/LiDAR do not reach the far baseline; 1 deg pitch = 6 px = a third of the gate
- [Point-boundary ground truth](point-boundary-ground-truth.md) — two problems, two ceilings; boundaries are LOGIC so labels are evaluation-only; audio is the strongest compliant signal
- [macOS + A13 device access options](macos-and-device-access-options.md) — GH Actions CI for coremltools export (near-free); Xcode Performance Report needs local USB device + may crash on iPhone ANE profiling; buy-vs-rent breakeven for a used A13 device
