# pm memory

Index. Detail in the topic files. Inherited 2026-08-28 from the prior planning work.

- [iOS-only, no desktop product](ios-only-no-desktop-product.md) — the Python backend is a training lab, not a product; target is iOS/iPadOS A13+
- [Parity before features](parity-before-features.md) — USER RULE: recreate the existing product on mobile before anything new
- [Mobile plan](mobile-parity-first.md) — phase order, session costs, what binds what
- [Sensor-assisted court](sensor-assisted-court.md) — IMU/intrinsics/ARKit collapse the search; REBUILD not port; blocked on a sensor gold set that does not exist
- [Score layer reopened, still no ground truth](score-layer-reopened-no-ground-truth.md) — scoring and point clips are in scope; a compliant truth source is a prerequisite line item
- [Line-call numbers assume a perfect bounce detector](line-call-numbers-assume-perfect-bounce.md) — 95.9% and the 54/69/81% curve are geometry ceilings, not end-to-end accuracy
- [The live path has no refusal surface](live-path-has-no-refusal-surface.md) — no confidence band, no false-lock suppression, no serve boxes
- [v1 cut line after court closure](v1-cut-line-after-court-closure.md) — 2026-09-05: manual calibration IS the setup story; court port cut (~15-20 sessions); scoring deferred, rally clips kept
- [v1 critical path: the Mac blocker is DEAD](v1-critical-path-is-founder-blocked.md) — CORRECTED 2026-09-05: Core ML export is a button press on a GitHub macos-14 runner; what remains is a physical A13 iPhone
- [Founder rulings 2026-08-29](founder-rulings-2026-08-29.md) — TrackNet ships v1, line calling PARKED, P0-3 accepted, a TrackNet idea withheld; surprising results go to researcher first
- [Human asks are a scarce batched resource](human-asks-are-a-scarce-batched-resource.md) — one batched update, ranked by leverage, artefact built first, dispatched before machine work
- [Cheap tests that close a line](cheap-tests-that-close-a-line.md) — price a cheap experiment by what its FAILURE closes; riders get no gate; pre-write the row both ways

**Settled, do not reopen:** iOS only, A13+, Core ML only. 100% on-device, no server ever.
