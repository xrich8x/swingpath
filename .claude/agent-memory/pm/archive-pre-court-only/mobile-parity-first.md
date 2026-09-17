---
name: mobile-parity-first
description: Mobile parity plan — the three perception stages have DIFFERENT binding constraints; pose binds runtime, court binds sessions, ball is fine. Order: ball, pose, court.
metadata:
  type: project
---

Direction set 2026-08-27: recreate the existing product on mobile, perception stack
first. See [[parity-before-features]] for the rule, [[mobile-v1-scope-live-calls]] for
what it superseded.

**The central analytical finding: the three stages are constrained by different things,
and conflating them produces the wrong plan.**

- **Court — binds SESSIONS, not runtime.** Detection is **one-time calibration, not
  per-frame** (`docs/modules.md`), so it costs almost nothing at run time. But it is
  ~2,900 lines of classical CV (`courtfit.py` 1,118 + `calibration.py` 1,793) with no
  conversion toolchain, becoming a shared C++ core. It is also the **weakest** subsystem
  (12/20 gate, 0/5 indoor shell). Most expensive to port, least valuable per session.
- **Pose — binds RUNTIME.** `yolo11m@1280` at ~0.4 s/frame, not exported at all, and
  1280 input is the expensive dimension. This is the thing most likely to make on-device
  batch analysis impossible.
- **Ball — largely fine.** Already exported, tiny, int8 path, in-graph argmax
  (0.9 MB/frame not 236 MB).

**Recommended order: ball, then pose, then court.** Order by information-per-session and
put the irreversible expensive thing last. The obvious objection — that court is
*upstream* in the data flow so must port first — does not hold: manual 4-corner tap
already supplies the homography and is already pure JS.

**The argument that court AUTO-detection is not required for parity:** parity of *output*
is a correct homography; auto-detection is a *mechanism*. Manual tap is the desktop
product's own designed fallback, used whenever auto fails — 8 times in 20, and 5 in 5
indoors. And the platform change works in its favour: tap-and-drag with a magnifier loupe
on a touchscreen is a **better** corner-picking interface than a desktop mouse. This is
the one subsystem where going mobile improves the fallback.

**Compute arithmetic that frames everything:** ball 0.7 + pose 0.4 = ~1.1 s/frame on
desktop CPU. A 10-min 30 fps clip is 18,000 frames = **~5.5 hours**. For a 20-minute
on-device job you need ~11x desktop CPU; users record *matches* (60-90 min), which is
6-9x more again. So the unit-of-analysis question is a real product decision, and the
honest bar is not "fps" but **sustained throughput at thermal steady state, resumable,
overnight**.

**Two platform facts that bite late if not designed for:**
1. **iOS and Android background execution are fundamentally different.** Android:
   foreground service with a notification, just runs. iOS: BGProcessingTask, OS-scheduled,
   killable, realistically overnight-on-charger. A multi-hour analysis job is therefore
   **two different features**, not one.
2. **The phone starts the job HOT.** Recording 10+ minutes of 1080p heats the device, and
   the analysis begins immediately after. Never benchmark from a cold phone.

**Honest cost:** parity without court auto ~40-50 sessions; full parity ~55-70. The
viability gate is ~9 sessions in.
