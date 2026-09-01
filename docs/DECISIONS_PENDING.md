# Decisions waiting on the founder

**Do not interrupt to ask these.** Founder instruction 2026-09-02: keep working,
record what needs a decision, hand it over when asked. This file is that handover.

Newest first. Each entry says what is blocked, what it costs to unblock, and what
was done instead so the blocker is not also idle time.

---

## 1. A push is required before the Core ML export can ever run — and pushes are barred

**Status: the job is ready and cannot be triggered.**

`.github/workflows/coreml-export.yml` already exists, is already on `origin/master`,
and is `workflow_dispatch` (manual) — deliberately, to dodge the 24-hour minimum
lease AWS and Scaleway both charge for any macOS instance under Apple's EULA.

So the Core ML export was **never blocked on hardware**. It is blocked on:
- a standing instruction from 2026-08-24: *"Do not push anything until I say so"*,
  never lifted; and
- **a defect that would have made it fail anyway**, now fixed (below).

**Cost to unblock: one sentence lifting the push bar.** GitHub-hosted `macos-14`
minutes bill at 10x on a private repo, but this job is minutes.

**Found and fixed while it was blocked:** `tools/export_coreml_p0.py` hard-coded
`backend/yolo11m-pose.pt`, which is **not in the repo** — `.gitignore`'s `*.pt`
excludes it and only `ballnet*.pt` is excepted. A CI runner checks out a fresh tree,
so the job would have exported the ball model and then failed at the pose step, which
is the whole reason the job exists. Now falls back to the bare name so ultralytics
fetches the stock checkpoint; a local run still prefers the file on disk.

**Still genuinely hardware-blocked, and not by the same thing:** on-device fps on an
A13. A cloud Mac is a VM with no iPhone attached, and a Simulator number is not a
device number. This project has a standing rule against quoting an unmeasured fps.

---

## 2. `data/tennis_sample.mp4` is missing, and it is the mobile port's only reference

`mobile/verify_live.js` is the sole parity check on the JS live-call port. Its header
expects *7 calls, 5 in / 2 out*, matching `live_demo.py replay`. That replay cannot
run: the video is not in the repo.

The harness itself was dead until 2026-09-02 (it never stripped `_`-prefixed
calibration keys) and now runs, giving **6 in / 1 out** against `court_pts.json` and
**7 in / 0 out** against `court_pts_refined.json` — which is the file `live_demo.py`
actually names.

**Nothing can say which is right until the reference runs.** Do not "fix" the port
against either number. **Cost to unblock: restore one video file.**

---

## 3. Carried over from the pre-existing BLOCKED list (lead journal, 2026-08-29)

Unchanged and still founder-only. Ranked there by leverage:

1. **Re-click `yt_match40` corners** (~5 min) — unblocks P0-2, the top v1 runtime
   risk. Sheet ready at `data/output/corner_audit/yt_match40_corners.png`.
2. **Look at `data/output/corner_audit/`** (~10 min) — 27 sheets built. Two the lead
   cannot settle: on `am_hard_utr` and `sAjkpeRq4P4` the far corners land near the
   NET rather than the far baseline, and a still frame cannot separate those at a low
   mount.
3. **TrackNet: detector-side or chain-side?** One sentence. If detector-side, rule 6
   leaves chain work open and speed coverage unparks to the front of the queue.
4. **~3-6 h of point-boundary labels — DO NOT START** until the researcher's protocol
   lands, or the hours get spent twice.
5. **Re-label 8 court gold frames** (~1 min). Rule 9 — recorded, never quietly fixed.
6. **Is the score layer settled in scope?** It flipped out 2026-08-20, back in
   2026-08-27.
7. **Is a Mac weeks or months away?** A sequencing input — pm would build a different
   plan for a months-long gap.

---

## 4. Dispatchable without the founder — listed so it is not mistaken for blocked

- **Court mask sweep needs a qa gate run.** `data/output/court_mask_sweep.json` shows
  12 accepted vs baseline 11, deliberately NOT claimed: the gate is >=12 of 20 AND
  zero accepted court beyond 20 px, and an accept count alone cannot clear it.
