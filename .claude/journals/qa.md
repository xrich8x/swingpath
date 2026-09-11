# qa - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK - 2026-09-10 (SECOND TASK THIS SESSION): verify the lead's repo cleanup
REPORT ONLY. No fixes, no edits to any project file. Items A-H:
A tests (lead claims 782 passed) B pose.py resolve_weights no-op/network proof
C deleted root weights yolo11m/x-pose.pt - adversarial check of direct-YOLO callers
D broken md links (script in scratchpad) E dangling refs to moved docs
F frontend npm run build G run.py demo H hooks/tests depending on moved paths
Report shape: VERDICT, one line per A-H, then findings with file:line.

## STATE
- Previous task (innovation-gate §5 audit) COMPLETE, see LOG archive below.
- New task started.

## LOG
- 2026-09-10: prior task COMPLETE (evidence section 6 appended to
  docs/evidence/innovation-gate-noise-calibration.md; memory written).
- 2026-09-10: cleanup-verification task recorded. Starting A (pytest, background) + C greps.
