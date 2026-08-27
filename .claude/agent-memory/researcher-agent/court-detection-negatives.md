---
name: court-detection-negatives
description: Every court-detection approach already measured and rejected here, with the reason — check before proposing anything about the court search
metadata:
  type: project
---

Backfilled 2026-08-27 from `docs/STATE.md`, `docs/RESEARCH_BRIEF_indoor_shell_courts.md`,
`docs/archive/sessions/SESSION_O_shell_courts.md`, `docs/archive/resolved/`.
Also read `docs/STATE.md` "What has not worked" (~50 rows) before proposing anything.

| Approach | Outcome |
|---|---|
| **Widen the seed grid** (all 30 human-labelled courts fall outside the shipped far-width range — the grid searches 0.20-0.42 of frame width, real courts sit at 0.09-0.22) | **REJECTED.** Reaches courts the old grid could not and **gets every one of them wrong** — 26 px and 78 px. Would have been the first wrong court ever accepted. Corrected the earlier five/five split: the half called a search failure was really scoring, and reachability was hiding it. |
| **Global mask replacement — CLAHE local contrast, Lab a\*/b\* chroma fusion, both** | **REJECTED on the product gate.** Fixes clay, breaks hard courts: chroma_only 9/20, clahe_only 13/20 with two courts at 22.4 px, both 6/20. Key finding: **chroma and CLAHE are redundant substitutes** — either alone gives the whole gain, both gives no more. Reading single ablations alone said "neither matters", an artefact of removing one while the other covered. |
| **Surface-routed clay mask** | **SHIPPED 2026-08-20 — the only court change to clear the gate.** 11/20 -> 12/20, nothing lost, zero wrong courts, median error 8.3 -> 8.1 px. Judge the surface, then use the mask built for it. Non-clay frames take a **bit-identical** path (pinned by `test_court_surface_routing.py`). Surface separates on colour alone: clay a\* 148.0-163.5 vs 132.0 max for everything else, `CLAY_A_STAR = 140.0`. CLAHE ships over chroma because chroma loses `sAjkpeRq4P4`. |
| **Broadcast-pose seeding** (27 synthetic 6-18 m long-lens poses) | **REJECTED.** No change on any clip. |
| **Crop-and-upscale** ("the court is too small in the frame", x1.18 -> x2.50) | **REJECTED.** No change; one clip got *worse* as its corners cropped out. |
| **Camera-angle selection** (human-picked top-down-only frames on broadcast) | **REJECTED.** No change, 0 of 6. |
| Surface routing to the *existing* hue-agnostic clay mask | Bit-identical to baseline — the pipeline already falls back to it. A better clay mask was needed, not an earlier reach for the old one. |
| Building the court quad from the DETECTED LINES | **Wrong in principle, not mis-tuned.** Under perspective the two doubles sidelines converge, so they form no angular cluster. Best constructed quad 68-256 px from truth vs the lattice's 7-20. |
| Snapping a near-correct court onto detected lines | Median distance from truth: seed 9.8 -> refiner 8.4 -> **snap 70.5**. Needs joint line-to-model assignment. |
| Raising `topk` (12 -> 40 -> 150) | No clip moves, **7x compute** (32 s -> 229 s per 4 frames). |
| Removing the pose-prior weight from seed ranking | No clip improves; the prior is not what buries the true seed. |
| Reachability ("refinement cannot travel from seed to true court") | **STOPPING RULE FIRED.** On **31 of 38** clips the nearest seed is already within reach. The brief predicted the opposite in advance. |
| Narrowing `EVID_BAND` | **The band is INERT** — `n_included` = 10 of 10 on every clip at every band from 5.0 down to 1.0. The hypothesis the whole brief was built around is refuted. Narrowing is a *wrong-court* lever: it raises wrong courts' scores while leaving truth unmoved. |
| Observability from geometry instead of nearby paint | **+0.000 margin**, byte-identical. The free half buys nothing, so the expensive half is unjustified. Closed. |
| Behind-camera projection inflating the denominator | **0.0%** of samples affected. |
| Low true-court score being human click error | Swept `tol` x0.5 -> x4; no clip shows the steep-then-plateau signature click error would produce. |
| Player-foot gate as a wrong-court criterion | **DEAD, and its sign is backwards** — feet-in-court fraction is *higher* for WRONG courts at every margin. The statistic rewards a court for being large. Best catch 2.0% at the <=5% collateral ceiling. |
| The horizon crop (`movers.crop_row`) at `k = 1.0` | **Safe but inert** — a crop is proposed on 1 of 20 clips. `k` was NOT re-tuned, per the brief's own rule. |
| Lowering the consensus bar 6/8 -> 5/8 | Gate fails — the one 5-vote clip is wrong by 68.7 px. |
| Single-frame court auto-seed in the setup tool | **7 of 10 worse** than starting from a blank rectangle. |
| Improving CourtNet for auto-calibration | Wrong target. CourtNet is Tier 2 (20.2% held-out); `courtfit` consensus is Tier 1 and beats it. |
| Vanishing-point filtering as a court/not-court classifier | **Closed by argument.** A shared VP proves 3D parallelism, not coplanarity; floor and roof relate by a planar homology whose axis is the horizon. A building aligned with the court is indistinguishable by line direction alone. |

**Where court detection actually stands:** the detector **finds** the court's lines (the
four outer lines sit a median 1.3-4.1 px@640 from a detected line) but **cannot assemble
them**. The criteria *do* recognise the correct court (9 of 10). The search *does*
produce it (7 of 10). **The frames that each found it do not agree with each other** —
and 13 of 18 clips disagree principally about how **WIDE** the court is, not where it is.
The one build named and never tested is **joint line-to-model correspondence** (assignment
solved together with the homography, Farin-style); its gate was pre-registered 2026-08-27.

Related: [[sensor-court-priors]], [[open-questions]], [[project-method-rules]]
