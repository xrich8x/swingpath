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
- **Joint line-to-model correspondence** — the one build named and never tested. Gate
  pre-registered 2026-08-27.
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
