---
name: v1-critical-path-is-founder-blocked
description: CORRECTED 2026-09-05 — the Mac blocker is DEAD (Core ML export runs on a GitHub macos-14 runner, push bar lifted). What remains is a physical A13 iPhone, and it is a scoping input, not a final verification step.
metadata:
  type: project
---

Established 2026-08-29, **materially corrected 2026-09-05**. Read the correction first.

## CORRECTION — the Mac half of this is stale, do not quote it

The original version of this memory said P0-0 Core ML export "needs a Mac. Procurement, not
minutes." **That is wrong as of 2026-09-05.** Verified by reading the file:
`.github/workflows/coreml-export.yml` is `workflow_dispatch` on a pinned `macos-14`
(Apple Silicon) runner, installs `coremltools` on real macOS where the compiled
`libmilstoragepython`/`libcoremlpython` missing from the Windows wheel exist, runs
`tools/export_coreml_p0.py` and uploads `ios/coreml_export/` with **14-day artefact
retention**. It was blocked only by (a) a standing push bar, **lifted by founder ruling
2026-09-04**, and (b) a hard-coded `backend/yolo11m-pose.pt` that `.gitignore` excludes from
a fresh CI checkout — **fixed**. It is a button press. `workflow_dispatch` only reads the
default branch's copy, so any brief must say **push `master` first**.

## What is genuinely still hardware-blocked

**A physical A13-or-newer iPhone.** Not a Mac, not a Simulator, not a cloud macOS VM (which
is a VM with no phone attached). Three v1 decisions dead-end there and nowhere else:

1. **Sustained throughput at thermal steady state** — the honest bar, never "fps". Desktop
   arithmetic is ~1.1 s/frame; a 60–90 min match needs roughly an order of magnitude more
   than desktop CPU. The single largest open unknown in v1.
2. **int8 vs fp32 for the ball graph** — 10.9 MB vs 43.0 MB, affordability unknown.
3. **The cost half of P0-2 pose affordability.** Its **accuracy** half is unblocked by five
   minutes of founder corner-clicking on `yt_match40` (rule 9 bars us editing it).

**Why this is urgent rather than a final verification step:** if throughput comes back bad,
the fix is not optimisation, it is a **product cut** (analyse a set not a match; downscale
pose; drop a stage) — and that cut is far cheaper at session 15 than at session 45. The
device is a **scoping input**.

**How to apply:** lead every status report with the hardware ask and the ~16-minute batched
founder sitting (re-click `yt_match40`, review the 27 corner sheets, re-label 8 gold frames),
per [[human-asks-are-a-scarce-batched-resource]]. Almost the entire remaining build — Core ML
artefacts, app shell, capture, calibration screen, refusal surface, results UI, batch job,
parity checks — proceeds at full speed without the device. See
[[v1-cut-line-after-court-closure]].
