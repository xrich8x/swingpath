---
name: open-questions
description: Unresolved technical questions as of 2026-08-27 — what is genuinely open, and what has been shown to be a dead end within it
metadata:
  type: project
---

Backfilled 2026-08-27 from `docs/STATE.md` and the archived sessions.

- **Frame-to-frame disagreement between CORRECT court locks.** The live problem, and
  nothing in the shell brief addresses it. Untested on shell entirely. An agreement metric
  normalised in **court terms rather than image pixels** would be resolution-independent by
  construction and could weight width separately from position — *an untested idea, not a
  result.*
- **Joint line-to-model correspondence** — BUILT, MEASURED, KILLED (2026-08-29 build,
  2026-09-04 continuations). See [[court-detection-negatives]] UPDATE 2026-09-05: the
  ceiling is the line detector's ~6.4 px rms disagreement with truth, not the fitter or
  the search. Court auto-detection is now CLOSED for v1; manual calibration is the
  recommended product answer. One cheap, un-run decomposition test remains if anyone
  wants the underlying science question (not the product question) settled — see
  `docs/evidence/court-detection-path-after-the-line-ceiling.md` §1.
- **`AGREE_PX` is 6x tighter on 4K than on the gate.** Real artefact — three
  high-resolution clips have good locks 38-46 native px apart that are only 12.8-15.3 px
  apart at 640. But height-scaling *loses* a gold clip, and the cell that lifts references
  accepts a 58.7 px court. Cannot ship before the search problem.
- **Far-court recall** — the detector fires on nothing in 24-27% of frames. Needs 4,087
  human-labelled frames (4-5 h). Automating the selection is a **measured dead end** under
  cross-validation (569 passing feature pairs cross-validate to 0-3%; the shuffled-label
  null returns 0, so the signal is real and far too weak).
- **9 solid ghost balls.** All 19 chain false locks have `run_len = 1` — every survivor
  carries a real ball's kinematic signature. Needs a better detector, and whether a
  detector gain can reach them at all is itself unresolved.
- **Bounce height** — no true ball height from one camera. Unevaluated: audio impact
  (module exists, unwired) and monocular 3D. *Audio is now doubly interesting — see
  [[point-boundary-ground-truth]].*
- **Whether more data caused the recall gain** — n = 1 training run per arm, and the
  datasets differ in size so batch composition differs too.
- **Indoor shell courts.** Ground truth now exists (10 human calibrations, 2 per venue,
  repeatability 1.2-7.0 px on 4 of 5 venues). The human court **would be accepted on 7 of
  10 shell clips if the search produced it**, but truth is in the candidate set on only 3
  of 10. **The cause is not the surface** — the masks visibly contain the court lines; what
  drowns them is the *building* (roof trusses, strip lights, fence lattice) at 395k-1,257k
  mask px. A better shell mask cannot fix it.
- **Real-time on-device.** No phone benchmark exists anywhere in this repo. Never quote a
  phone fps. See [[coreml-ane-budget]] for what is and is not published elsewhere.
- **Does a motion blob's per-frame POSITION identify the far player specifically?**
  (2026-08-29, founder hypothesis.) **CLOSED same day — see below, this is now a negative,
  not an open question.**
- **Far player vs. far ball: same problem or two?** (2026-08-29, founder question, framed
  deliberately as one.) **ANSWERED: not the same problem.** Shared root cause (optical
  undersampling at 15-24m from a fixed amateur mount) but divergent failure mode: the
  player is SEARCH-limited (full-frame model 0/25, a crop+upscale escapes it — a real,
  weak, measured positive); the ball is DISCRIMINATION-limited (detector already fires on
  73-76% of far-court frames; the ball's own analog of the crop trick — a whole-frame
  resolution bump — was already tried and its entire recall gain arrived as extra solid
  ghosts, one of the four-for-four closed detector items). The player's fix does not
  trivially transfer to the ball, and that non-transfer IS the evidence the two problems
  differ. Two narrow items left open, one gated, one sketched:
  [docs/evidence/far-end-player-and-ball-what-is-left.md](../../../docs/evidence/far-end-player-and-ball-what-is-left.md).
- **What else can independently validate a calibration, given coverage/camera-height/
  net-anchor-bar all failed as GATES?** (2026-09-05.) Assessed, ranked, not built.
  Organising finding: every FAILED check so far used only the ground plane (`z=0`);
  the one check that WORKED (net tape) is the only one off-plane. A regulation
  court's own paint is near/far and left/right symmetric (net excepted), so no
  ground-plane-only statistic can in principle separate the `yt_match40`-class error
  (a plausible court compressed onto its near half) from a correct one — this is why
  four separate gates in this family have now failed the same way. Ranked: (1) **net
  posts at 1.07m** — build next, cheap, off-plane, rigid (no sag confound unlike the
  tape), framing-limited on low mounts in an unmeasured way (falsifier: count post
  visibility across the 27 existing `*_netanchor.png` renders before building
  anything — zero-cost). (2) **ball/gravity arc fit** — theoretically the sharpest
  reference (an actual physical constant + real fps-timed seconds, not another
  game-object assumption) but this project's own history gives three reasons to
  expect it fails cheaply if funded now: T22 (naive z=0 airborne-ball projection is
  already known wrong), the arc-fit-observability finding that `reproj_px` cannot
  certify an arc (23.8x span passes), and unmeasured per-shot drag bias (-21.7%
  measured on average speed already) that would fire on every CORRECT calibration.
  (3) people-as-scale-reference — works, but stacks a ~4-5% population-height term
  plus uncharacterised pose keypoint head/foot bias on top of the same off-plane
  logic; noisier per-observation than the tape, no repeatability structure. (4) other
  court markings (service lines/T/singles sidelines) and (5) vanishing points —
  REJECTED as new work, both already tried under a different name (`verify_court`
  coverage and joint line-to-model correspondence respectively) and both inherit the
  same ground-plane symmetry blindness. (6) shadows — genuinely independent in
  principle but inapplicable on Shell (64/116 clips, indoors), already shown to
  confound the net-anchor `band_ratio` check via the net's OWN shadow, needs a wholly
  new detector. Recommendation: build the post detector as a NUMBER shown to the
  human confirming calibration (same shipped pattern as the tape), never a fifth
  autonomous gate — four gates in this family have failed identically.
  `docs/evidence/independent-calibration-references.md`.
