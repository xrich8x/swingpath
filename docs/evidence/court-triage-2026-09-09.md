# Court triage, 2026-09-09 — what survives, what is provisional, what to archive, what to do next

> **Written by pm, 2026-09-09.** Scope: **COURT ONLY**. Ball, speed, score and mobile are
> out except where a court finding reaches them.
> **Nothing here re-derives a measurement.** Every number is cited from a file I read, with
> the path. Nothing here moves a file, edits `docs/STATE.md`, or changes a corner value —
> Part C is a list for the lead to execute, and re-placing calibrations is the founder's
> under rule 9.
> Coverage confession is the last section. Read it before quoting this document.

---

## 0. The call, first

**The damage is much smaller than it looks, and it is smaller than `docs/STATE.md` currently
says. Two things are load-bearing and neither has been done.**

Three corrections drive the whole triage:

1. **There are TWO court pools, not one, and only one of them is compromised.** The
   pre-registered gate — **≥12 of 20 accepted, zero accepted court more than 20 px from
   human clicks** — is scored against `data/gold/*.court.labels.json`, a *different set of
   files, placed with a different tool, on differently-named clips, at a different
   resolution* from the `_exact` `*_pts.json` references that T26 is about. STATE's row
   listing "the 12/20 gate" among the numbers inheriting the provenance defect is **not
   established** (§B.0).
2. **Only 2 of the 20 clips in the compromised pool are confirmed misplaced**, not 4 and not
   9. Two of the four MISPLACED clips are not in the scoring pool at all (§B.1).
3. **Because of (2), the headline court verdict survives any reasonable correction.**
   Proposal recall 8/20 = 40% against a pre-registered "search binds at ≤60%" could rise to
   at most **10/20 = 50%** if both misplaced references were re-placed and both clips then
   passed. **SEARCH BINDS either way.** That conclusion does not need re-measuring (§B.2).

**What is genuinely unresolved is the gold pool's own provenance — nobody has ever rendered
a `data/gold/*.court.labels.json` court onto its frame.** `tools/render_corner_audit.py`
reads `*_pts.json`; the founder's 28 sheets were all references. The gate that has cleared
or killed every court change in this project has never had its own truth looked at.
**That is item 1 in Part D and it costs one session.**

The second unaddressed thing is not in the record at all: **the user walks away from the
phone.** Setup-time camera movement is a different regime from mid-match drift, nothing
measured here touches it, and the answer is a five-minute ordering change to the setup
screen rather than any perception work (§D.4).

---

# A. SURVIVES

Findings whose validity does **not** depend on the `_exact` reference pool. These stand and
can be built on today. Grouped by why they are independent.

### A.1 Measured against synthetic truth or against themselves (no human court involved)

| Finding | The number, and what it was measured against | Path |
|---|---|---|
| **The net tape physically covers the far baseline below ~2.0–2.2 m** | A net is **0.914 m**; at 3 m back / 80° / 720p the tape sits *above* the far baseline at 1.40, 1.64 and 2.00 m and clears it by 10 px only at **2.50 m**. Stable across 2–5 m standoff, 65–100°, 720p/1080p, because it is set by the net's physical height against the far half's depth — **a property of the court, not of any calibration**. All four measured mounts (1.64 / 1.74 / 1.38 / 1.36 m) sit below it. | `docs/STATE.md` (What has not worked, row "Below ~2.2 m the net TAPE covers the FAR BASELINE"), `docs/evidence/setup-envelope-net-occludes-far-baseline.md` |
| **The near-baseline + net solve is geometrically exact; everything failing is DETECTION** | Synthetic solve-back **0.0000 m** on four cameras. The decisive control: fed **truth** observables the solve reproduces the human far-baseline row to **0.007 px median / 0.75 max on all 40 clips** — so roll, off-centre principal point and real lens do not break it. End-to-end from *detected* lines it fails: far corner **17.4 px@640** against the 8.1 px bar. And availability binds harder than precision — right doubles sideline found on **18/40**, net ground line **24/40**, all four coexisting on only **10/40**. | `docs/STATE.md` (What has not worked, row "The camera SOLVES from the near baseline + net alone"), `docs/evidence/net-baseline-solve-without-far-line.md` |
| **Camera height survives a 40% standoff error** (1.64→1.62, 2.11→1.95, 2.88→2.92 m) | Same solve. If that work has a use it is **mount-height estimation for the setup criterion**, not calibration. | same row |
| **The close-call curve** | 54.0% at 1.0 m, ~69% at 3 m, ~81% at 8 m against a **56.2% majority-class floor**; bounce error 3.81 → 0.37 m. From `tools/synth_truth.py`, the only absolute accuracy reference in the repo. | `docs/STATE.md` (What has worked, "Camera-height curve"), `docs/evidence/camera-height-curve.md` |

### A.2 Negative results established by reading code or by a control, not by a score

| Finding | What makes it pool-independent | Path |
|---|---|---|
| **Camera motion is NOT the cause of court instability** | The verdict rests on a **control**, not on the references: motion compensation is a **0.01 px no-op** on static clips, and four *motionless* 4K shell tripods disagree with **themselves** by **29.9 / 31.9 / 36.3 / 37.5 px@640** — more than the project's own 20 px wrong-court line. Compensation removes a median **24.0 px@640** on the 5 clips that move and leaves **26.4** against **24.8** for the 11 that do not; **0 of 20 change acceptance**. The instrument was validated against numbers it did not produce (null **0.000**, injected 8.000 recovered **7.98–8.04 on all 20**). The founder's mechanism is real and quantified; **it rescues nothing.** | `docs/STATE.md` (Open, first row), `docs/evidence/camera-motion-vs-court-agreement.md` |
| **Corollary, and it is the useful half for the product:** a court disagreement of 25–37 px@640 tells you **nothing** about whether the camera moved. You cannot detect camera movement by watching the court fit wobble. | Same control. This is what makes §D.4's answer an IMU/ordering answer rather than a vision answer. | same |
| **The CNN-global → classical-local prescription fails because the CNN REFUSES, not because it is inaccurate** | `detect_court_learned` returned `None` on all 8 frames of 4 of 6 probed clips: only **2–3 of 14 heatmap peaks clear 0.40** on amateur footage, `min_points` is 6, and **4** are needed for any homography at all. That is a behaviour reading of the shipped code on our footage — it does not depend on any reference being right. **Not a tunable threshold: the upstream broadcast checkpoint does not see these courts.** | `docs/STATE.md` (What has not worked, "CNN-global -> classical-local FAILS"), `docs/evidence/cnn-global-classical-local.md` |
| **The court CNN is cheap on an A13** | ~**151 G MACs ≈ 300 GFLOPs/frame**, but **8 frames ONCE per video** ⇒ **~2–5 s one-off, no thermal exposure**. ~11M params ≈ 22 MB fp16. Operator coverage zero-risk: only Conv2d/ReLU/BatchNorm2d/MaxPool2d/Upsample-nearest, all ANE-native, BatchNorm folds at export. Summed layer-by-layer from `_courtnet.py` — arithmetic, not a score. (Timing confidence self-reported at 0.6.) | `docs/STATE.md` (Open, "The court CNN is CHEAP on an A13") |
| **The line detector is the ceiling, and the optimiser is not the problem** | Least-squares over all matched line correspondences **FAILS its ≤10.0 px bar** (LS-geom 19.80, LS-DLT 73.50) — but the control is exact: the 4-point fit recomputed in the same run gives **17.10 px@640** with an identical survivor set and **0.00 px** max per-clip difference from the committed artefact. LS-geom drives the *line* residual below the human homography's own on **13 of 13** (3.01 vs 6.44 px rms). **A better fitter converges harder onto a biased target.** | `docs/STATE.md` (What has not worked, "Least-squares over ALL matched line correspondences"), `docs/evidence/least-squares-court-fit.md` |
| **`AGREE_PX = 30.0` is raw-pixel and scaled nowhere** | `courtfit.py:774` = 30 / 10.0 / 5.0 px@640 at 640 / 1920 / 3840. That is a **code fact**, true regardless of which court is correct. What it *costs* is provisional (§B.6). | `docs/evidence/agree-px-is-6-tighter-on-4k.md` |

### A.3 Process findings — the most durable things produced today

| Finding | Why it survives | Path |
|---|---|---|
| **T26: `_exact` never meant "a human placed this"** | Established by reading `tools/court_setup_server.py`'s `/api/save` against `eval/run_refs.py`'s docstring. A code-vs-doc contradiction; no measurement can overturn it. | `docs/TRAPS.md` T26, `docs/evidence/calibration-provenance.md` §1 |
| **The second hole in the same handler** | On the shape-lock-ON path, Save stored `lock_shape()`'s *adjusted* corners and **discarded** the distance moved. On a synthetic quad that drift is **0.508 px** — small, real, and previously invisible on every lock-ON save ever made. | `docs/evidence/calibration-provenance.md` §1 |
| **Auditing by commit hash under-counts by a third** | `3399d58` last wrote the corner values of **6** pool clips (7 by any touch), not 9; `ac94aab` wrote **zero**. The founder's 9-of-20 reproduces exactly when the unit is the **seven-commit session** of 2026-08-11/12, not the two named commits. Derived by diffing non-underscore keys of every historical version against its parent. | `docs/evidence/calibration-provenance.md` §6 |
| **The audit instrument rendered frame 0 while the eval scores frames 5%–95%** | All 28 reviewed sheets were frame-0 renders; in **gallery** mode `court_setup_server.py` gets its image from `eval/collect_frames.py`, which seeks mid-clip. So a gallery-placed calibration was judged on a frame it was never placed against. Risk runs **both ways** — both of qa's false-exoneration predictions validated. Instrument controls ran on every clip: null **0.000 px on all 28**, injected 8.000 px recovered **7.95–8.10 on all 28**. | `docs/evidence/calibration-provenance.md` §8.2, `docs/STATE.md` (Open, second row) |
| **`--tag` was accepted and silently ignored on the corner path** | Five renders of one clip at five frame indices produced **one** file, four silently destroyed, no error. That is a chain-of-custody failure one layer downstream of T26 — the artefact backing a "wrong" verdict could be overwritten. Fixed; the point survives as a lesson. | `docs/evidence/calibration-provenance.md` §8.1 |
| **T24 fired a second time** (`eval/candidate_audit.py` claimed UNRUN while `424ecdc` committed its own output in the same commit) | Established from git and from consuming artefacts, never from prose. **Permanent cost:** shell recall moved 3/10 → 2/10 between two runs with no per-clip record, so a possible `4a33635` regression is **unconfirmable rather than refuted**. | `docs/evidence/calibration-provenance.md` §8.3, `docs/STATE.md` (Open) |
| **Rule-8 proof that the provenance change moved nothing** | Corner values byte-identical (structural + end-to-end + golden at 1e-9 px), `references()` returns the identical 20 clips before and after, 605 tests pass, 693 after the addendum. | `docs/evidence/calibration-provenance.md` §3–§4, §8.4 |

### A.4 The product decision that rests on none of this

**Court auto-detection is closed for v1 and v1.x; manual 4-tap calibration IS the setup
story.** That call was made 2026-09-05 and **the provenance defect does not weaken it — it
strengthens it.** The case for closing was that a *successful* auto-detector would not have
beaten manual entry, because manual entry is the reference standard. If the reference
standard now needs re-establishing in places, the argument for not shipping a detector that
is silently wrong 8 times in 20 gets stronger, not weaker.

`docs/evidence/court-detection-path-after-the-line-ceiling.md`,
`docs/evidence/v1-resequenced-after-court-closure.md` §2.2.

---

# B. PROVISIONAL

Findings scored against the `_exact` reference pool. **They are not wrong; they are
unsupported until re-measured.** For each: what would have to be re-run, and — the judgement
that matters — whether re-placement would change the **conclusion** or only the **decimal**.

## B.0 First, the correction that shrinks this section

**`docs/STATE.md`'s row on the provenance defect names "the 12/20 gate" among the numbers
inheriting it. I do not think that is right, and the lead should check it before it hardens.**

Two different pools:

| | REFERENCES pool | GOLD pool |
|---|---|---|
| Files | `data/<clip>_pts.json` with `"_exact": true` | `data/gold/*.court.labels.json` |
| Selected by | `eval/run_refs.py::references()` | `eval/run_eval.py --gold --all --k 8` |
| Clips | `A7vXlWIlyrI`, `CYqapSq5llo`, `HoHxFSX_gLk_s1/s2`, `e8T34KoJzOw_s2`, `tc8CGFxyRE8`, `UHf0LeMU2pg`, `uR5q2cSM6AY`, `sAjkpeRq4P4`, `am_hard_utr`, 10× `flexi_*`/`hillsborough_*`/`mpc_*` | `am_classB`, `am_college`, `am_fr_sud`, `am_grass1`, `am_ntrp30`, `am_ntrp40`, `am_ntrp45_courtlevel`, `am_rally32short`, `am_rec30`, `am_usta40`, `am_usta45`, `am_usta60` (+8 refused) |
| Resolution | 1920 / 3840 | all exactly 640 wide |
| Placed with | `tools/court_setup_server.py` | the Lab's court labelling tool |
| What it scores | reference error, proposal recall | **the pre-registered ≥12/20, zero-over-20-px gate** |

Sources I read for this: `eval/run_refs.py` lines 1–120 (the pool definition and the
`CORNER_SOURCE_COMMIT` map, 20 clips); `docs/evidence/court-mask-sweep-item-is-already-shipped.md`
§2, where qa names the gate's truth source explicitly and independently re-ran it (12/20,
median **8.1 px**, range **1.7–13.9 px**, zero accepted over 20 px);
`docs/evidence/agree-px-is-6-tighter-on-4k.md` ("All 20 gold clips are exactly 640 wide, the
references 1920, shell 3840"); and `docs/evidence/cnn-global-classical-local.md`, which
reports **"Gold gate 12/20 → 2/20"** and **"References 2/20 → 0/20"** as two separate lines.

**What this means in one sentence:** T26 is a defect in the pool we use to measure *how far
off* the detector is, not in the pool we use to *decide whether anything ships* — so the
gate that has killed two court changes is probably still standing.

**What it does NOT mean.** The gold pool is not established *clean*. Nobody has ever
rendered one of its courts onto its frame; the founder's 28 sheets did not include a single
one. And it has its own known defect: **8 frames of `am_indoor_hard1` are marked
`court: false` while plainly showing a full usable court** (3 of 3 inspected) —
`docs/evidence/8-court-gold-frames-are-mislabelled.md`. Plus T06: **17 of the 20 gold clips
had been inside `data/court_dataset/`** before the split guard existed
(`docs/TRAPS.md` T06). **UNEXAMINED, not clean.** That is Part D item 1.

## B.1 The damage inside the reference pool: 2 of 20, not 4

Joining the re-review verdicts against `eval/run_refs.py`'s 20-clip map and
`docs/evidence/calibration-provenance.md` §5b/§7:

| Re-review verdict | Clip | In the 20-clip scoring pool? |
|---|---|---|
| **MISPLACED** | `HoHxFSX_gLk_s1` | **yes** |
| **MISPLACED** | `HoHxFSX_gLk_s2` | **yes** |
| **MISPLACED** | `HoHxFSX_gLk_s3` | **no** — `_exact` is `no`; §5b lists it outside the pool |
| **MISPLACED** | `bump_ntrp30` | **no** — §7: no matching `*_pts.json` exists in the repo; untracked |
| MIXED | `A7vXlWIlyrI`, `CYqapSq5llo`, `UHf0LeMU2pg`, `uR5q2cSM6AY` | yes (4) |
| MIXED | `bump_ntrp30b` | **no** — same as above |
| HOLDS | `sAjkpeRq4P4` | yes — a **false accusation** by the frame-0 sheet |

**So: 7 of 20 pool clips were touched by the review; 2 are confirmed misplaced; 1 was
exonerated; 4 are MIXED, which is a different problem (§B.2, §D.3).** The other 13 are
untouched, and 10 of those are the `7c8b8af` shell block that the founder marked **0 of 10
wrong** — provisionally corroborated by the one instrument that can settle it, though its
"human" claim still rests on a commit message
(`docs/evidence/calibration-provenance.md` §6).

**This is the number that resizes the whole problem, and it is not in `docs/STATE.md`.**

## B.2 The findings, each with a conclusion-or-decimal call

| Finding & number | Re-run needed | Conclusion or decimal? |
|---|---|---|
| **Proposal recall 8/20 = 40%; "SEARCH BINDS"** (pre-registered: search binds ≤60%, voting binds ≥80%). Three failure classes: reached 8, near-miss 2, wrong court 7, nothing produced 3. Robust across tolerance 20–35 px. — `docs/STATE.md` Open, `docs/evidence/candidate-proposal-recall.md` | `eval/candidate_audit.py` over the pool, after re-placement. **~0.5 session.** | **DECIMAL — the conclusion is safe.** Best case, both misplaced references flip from fail to pass: **10/20 = 50%**, still inside the ≤60% "search binds" band. It would take all four MIXED clips flipping too (14/20 = 70%) to reverse it, and **MIXED clips cannot be fixed by re-placing** — that is the whole point of §D.3. **Treat this as effectively an A-list finding.** |
| **The ≥12/20 gate itself, median 8.1 px, range 1.7–13.9, zero over 20 px** | **Nothing, if §B.0 holds.** If the gold pool turns out to share the defect, everything ever cleared "on the gate" is void — including `4a33635`'s refiner-reach scaling. | **CONCLUSION-CRITICAL, and it is the one thing worth spending on.** Not because it is likely wrong, but because it is the only court number whose failure would invalidate the others. See D.1. |
| **Shell 1 of 5 recordings (2 of 10 clips); 3 shell clips produce no lock at all** | Same re-run. Shell references come from `7c8b8af`, **0 of 10 marked wrong**. | **DECIMAL, and barely that.** The shell block is the untouched half of the pool. Independently corroborated: repeatability **1.2–7.0 px@640** on 4 of 5 venues, camera audit **2 PASS / 3 LOW-CAMERA / 0 fail** at **0.0–2.5 px** residual, implied camera height reproducing to **0.02 m** across independent labels — `docs/evidence/indoor-shell-courts.md`. Self-consistency at that level is hard to fake. |
| **CourtNet arm: gold 12/20 → 2/20, references 2/20 → 0/20, 3 of 160 frames locked vs 89** | Nothing. | **DECIMAL.** The mechanism (§A.2 — the CNN refuses before our gate runs) is established by code behaviour, and a 12→2 collapse cannot be produced by two bad references. |
| **`verify_court`'s coverage gate: 3 of 25 correct courts refused; the 0.40 bar sits inside the correct-court distribution (0.245–1.000); the grossly-wrong `yt_match40` PASSES at 0.436** — `docs/STATE.md` Open, `docs/evidence/verify-court-false-rejects.md` | Re-run over the re-placed set. **~0.3 session, ride-along.** | **DECIMAL for the headline, CONCLUSION for the count.** "3 of 25" will move. "Coverage orders clips by line VISIBILITY, not correctness" will not — it is anchored by `yt_match40`, which is **confirmed** wrong independently of the pool (T23, all four corners on asphalt and a hedge) and passes anyway. **Do not retune 0.40** stands. |
| **Composite calibration score: held-out 57% of corruptions flagged against an ≥80% bar = FAIL** | Re-run. **~0.5 session.** | **DECIMAL.** Its positives are *injected* corruptions of real calibrations, so the corruption is synthetic even when the base is suspect. Two sub-findings are structural and survive outright: **isotropic scale 0/36** (coverage catches scale only relative to a clip's own baseline, and at setup time there is no baseline) and **the composite scores 0.0 on the one CONFIRMED-wrong calibration** — pinned by a test so nobody quietly fixes it. |
| **Net-anchor check: both pre-registered bars FAIL, flagging 14 of 27, and INVERT on the only pair with settled truth** | Re-run **and** re-render — every published `--net-anchors` number was measured at **frame 0**. Pass `--frame 0` to reproduce; a different frame is a different measurement, not a changed result. | **DECIMAL, but with a second hazard.** The bars failed; re-placement can only change how badly. The frame-0 caveat is the bigger issue and it is already recorded (`calibration-provenance.md` §8.4). |
| **Net-tape camera height: AGREE 13 of 15 within 10%, and the instrument is precision-limited at 3.2%/px at 720p** | Re-run. **Ride-along.** | **DECIMAL.** The finding is that the instrument's resolution is ~3 px of tape row, so a 10% bar is ~3 px — an instrument property, not a pool property. |
| **The live setup criterion sweep: 16 poor / 6 marginal / 6 good over 28 calibrations; Spearman(width ratio, clearance) = +0.189 vs Spearman(camera height, clearance) = +0.937; every clip below 2.0 m poor, every clip at/above 2.89 m good** — `docs/STATE.md` Open | Re-run the sweep. **Ride-along.** | **DECIMAL — and this is the one with a v1 consumer, so say it plainly.** Two of 28 points moving cannot invert a 0.189-vs-0.937 correlation gap or move a band boundary that lands independently on the derived **1.98–2.21 m** crossover. **The shipped `min_elevation = 0.28` refutation stands.** The crossover itself is in Part A — derived from court geometry, no calibration involved. |
| **`courtnet_ft.pt`** | — | **DEAD ON ARRIVAL, not provisional.** Fine-tuned on a pool containing **17 of the 20 gold clips** (T06). Any number from it is self-graded. Separately, `detect_court_learned` **silently prefers it** — the CNN experiment had to force `court_detector.pt` through `COURTNET_WEIGHTS` to avoid grading itself. That silent preference is a live trap in shipped code and belongs in a backend-dev brief (§D.6). |

---

# C. DEAD — archive

**The archive list is short, and that is the finding.** Two rules constrained it:

1. **A measured negative is never archived.** Rule 3 works only if the ~65 rows in
   "What has not worked" stay where people trip over them. Nine ideas in there have already
   been re-proposed at least once; burying one guarantees a tenth. So
   `snapping-a-near-correct-court-onto-the.md`, `single-frame-court-auto-seed-in-the.md`,
   `lowering-the-court-consensus-bar-6-8.md`, `least-squares-court-fit.md`,
   `court-correspondence-gate.md` and
   `widening-height-scaling-agree-px-to-recover.md` all **STAY**, however finished they look.
2. **A superseded artefact is not deleted, it is captioned.** §8.1 of the provenance file is
   precisely about destroying the evidence behind a verdict. Nothing that backs a founder
   judgement gets moved.

### C.1 Move to `docs/archive/resolved/`

| File | One-line reason |
|---|---|
| `docs/evidence/yt-match40-calibration-is-wrong.md` | **Fully discharged.** Its four "what needs doing" items are done: the clip was re-clicked and confirmed (corners last written by `11044fc`, 2026-09-05 — `calibration-provenance.md` §5b), the two figures it withdrew are in STATE's Withdrawn table, and its item 4 ("audit the other committed `data/*_pts.json` by rendering, not by residual") became the 28-sheet review. Its lesson survives permanently as **T23**. |

**That is the whole list, and I am not padding it.** A one-file archive after a day that
felt like it invalidated everything is the honest answer.

**One hazard the lead must check before moving it,** because it is three steps out and
nobody will catch it otherwise: that file contains the literal strings `11.0%` and
`8.8 m mount`, both registered in STATE's **Withdrawn figures** table, which
`.claude/hooks/withdrawn-guard.sh` machine-reads. The guard's documented skip list is
`docs/archive/HANDOFF.md`, `docs/archive/sessions/`, `docs/REVIEW-*` and `data/output/*` —
**`docs/archive/resolved/` is not on it.** The file does carry withdrawal markers in the
same blocks, so it should pass; if the commit is refused, that is the reason, and the fix is
a skip-list line, not an edit to the archived text.

### C.2 Looks dead, is not — do NOT archive

| File | Why it is now more valuable than it was |
|---|---|
| `docs/evidence/court-mask-sweep-item-is-already-shipped.md` | Its *queue item* is dead (already shipped `f41a489`, 2026-08-21) and I orphaned it myself in `v1-resequenced-after-court-closure.md` §2.2. But it is the **best independent record of what the ≥12/20 gate is actually scored against** — qa names `data/gold/*.court.labels.json` and lists the twelve accepted clips. That is the second witness for §B.0. **Keep, and consider re-titling the row so the gate-definition content is findable.** |
| `docs/evidence/8-court-gold-frames-are-mislabelled.md` | **Promoted, not retired.** It is now the only known defect in the *gate's own* pool, and one of two things D.1 must resolve. A minute of founder time. |
| `docs/evidence/scaling-the-court-refiner-s-reach-with.md` | Its claim — `max_move_px 55 → 55*w/640` is an **exact no-op on the gate (12/20 → 12/20)** — is **narrowed, not dead**. The gate pool contains **no 4K shell clip**, so a shell-only effect was invisible to its own control, and shell recall moved 3/10 → 2/10 across that window with no per-clip record kept. **Unconfirmable rather than refuted.** Keep; the row needs the caveat, not the bin. |
| `data/output/corner_audit/*_corners.png` — the 28 frame-0 sheets | **Do not move, do not delete, do not overwrite.** They are the artefacts backing ten founder verdicts; destroying them is exactly the chain-of-custody failure `calibration-provenance.md` §8.1 names. They should get a `README.md` in that directory saying they are frame-0 renders, superseded by `_f<N>` sheets, and must not be mixed with them in a re-review. **A caption, not a move.** |
| Everything in "What has not worked" | Rule 3. Stated above. |

---

# D. WHAT TO DO NEXT

Ranked by what each buys per session, with the cut line drawn explicitly.

**Standing constraint on this whole section:** court auto-detection is closed for v1 and
v1.x. So the only item below with a direct v1 consumer is **D.4**. Everything else is
truth-in-the-record work, and it is priced accordingly — total funded spend here is
**~3 sessions plus ~30 minutes of founder time**, and none of it displaces the head of the
dispatch queue (backend-dev's Core ML export) or the setup screen.

---

## D.1 — Establish the GOLD pool's provenance. **1 session. Do this first.**

**Call:** run the same git archaeology and the same rendered audit on
`data/gold/*.court.labels.json` that `calibration-provenance.md` §5 ran on `*_pts.json`.

**Why, including the failure mode being avoided:** the ≥12/20 gate is the only
pre-registered court gate this project has, and **two changes have already been killed by
it**. If its own labels have the T26 defect, then every "cleared on the gate" verdict is
void — including `4a33635`'s refiner-reach scaling, which is *already* under suspicion from
the shell side. The failure mode is spending the next month re-measuring against the wrong
pool, or worse, discovering in three weeks that the gate we trusted to kill bad ideas was
itself agent-placed. **This is the cheapest thing on the board that changes the most rows.**

**Cost, and what does not get built:** 1 session, qa or backend-dev (needs Bash + git). It
displaces the *second* backend-dev item on my standing queue — the refused-frame downstream
cost measurement — by one session. It does **not** touch the Core ML export dispatch.

**What we are cutting to pay for it:** nothing is re-measured against the reference pool
until this returns. Re-running proposal recall against a pool you are about to re-place is
paying twice.

**Definition of done, written before the work starts:**
- A table in the shape of `calibration-provenance.md` §5a: for each of the 20 gold clips,
  which commit last wrote its corner *values* (non-underscore keys diffed against the
  parent, `_audit`-only touches listed separately).
- An explicit yes/no on whether any gold label's values were written by the 2026-08-11/12
  seven-commit session, by `7c8b8af`, or by any commit whose message is written in the first
  person by an agent.
- A named answer to: **which tool wrote these files, and does it have the `_exact`-shaped
  defect** (a flag whose meaning was documented as provenance and is not)?
- The 8 known-mislabelled `am_indoor_hard1` frames recorded against the gate's denominator.
- **A bar is required before the rendered half runs (rule 2).** I am not writing it; qa or
  the lead must pre-register what "clean" means — e.g. *N of 20 gold courts rendered at the
  eval's own sampled frames show all four corners on paint by the founder's eye*, with the
  threshold fixed before the first render. Do not render first and decide after.

**On-device catch:** nothing here. Local git and local files; no network, no inference.

**Handoff brief — qa** (Bash, and it must not fix anything it finds):
> Establish the provenance of `data/gold/*.court.labels.json` by the method in
> `docs/evidence/calibration-provenance.md` §5 (parse every historical version, drop
> underscore keys, credit a commit only if the four corner values changed). Report the
> per-clip table, the tool that wrote them, and whether that tool carries an `_exact`-shaped
> flag. Do NOT re-place, edit or "fix" any label — rule 9. Do NOT render sheets until a bar
> is pre-registered. Deliverable is one evidence file plus the exact STATE row text you would
> want, handed to the lead.

---

## D.2 — Re-render the four MISPLACED clips at the eval's own frames, then ONE batched founder ask. **0.5 session + ~30 min founder.**

**Call:** build the artefact first, then ask. `tools/render_corner_audit.py --eval-frames`
now writes all eight, named by frame index. Re-render `HoHxFSX_gLk_s1`, `HoHxFSX_gLk_s2`,
`HoHxFSX_gLk_s3`, `bump_ntrp30` — and, because it costs nothing extra, the four MIXED
in-pool clips so the founder can see for himself what "right on some frames, wrong on
others" looks like. Then one ask, one sitting.

**Why:** only 2 of the 4 are in the scoring pool (§B.1), so this is a ~20-minute job, not a
re-labelling programme. Re-placing is the founder's under rule 9 — **an agent placing them
again is the literal cause of T26.**

**Bundle into the same sitting** (standing rule: a founder ask is a scarce batched
resource): the 8 mislabelled `am_indoor_hard1` gold frames (~1 min in the Lab), and — if
D.1 comes back saying the gold pool needs eyes — whatever gold sheets that produces.

**What we are cutting:** a second full 28-sheet review. The re-review is done; asking again
wholesale would burn the founder's scarcest resource on clips the record already settles.

**Definition of done:** four `*_pts.json` files re-placed by the founder with a
`_provenance` block (`placed_by` filled in by hand, since the tool writes `"unattributed"`
for agent and human alike and **that must never be read as "human"**), plus the 8 gold
frames relabelled. Recorded, with the old values kept — never quietly overwritten.

**On-device catch:** nothing here.

---

## D.3 — The "5 MIXED" / one-homography-per-clip hypothesis. **Worth 1 session as pool hygiene. NOT worth funding as a data-model change.**

**The lead's hypothesis is right about the data and wrong about the remedy, and the
distinction is the product.**

**It is right about the data, and it is already half-measured.** qa's frame-choice
instrument reports how far a clip's clicked corners move by frame choice alone:
`HoHxFSX_gLk_s3` **212.9 px**, `A7vXlWIlyrI` **162.6**, `HoHxFSX_gLk_s1` **119.4**,
`sAjkpeRq4P4` **80.4**, `bump_ntrp30` **60.5**, `CYqapSq5llo` **38.8**, `UHf0LeMU2pg`
**29.2**, `uR5q2cSM6AY` **13.2**, `L73ep7JHiJ4` 5.95, `demo30` 0.04 — against the project's
own 20 px wrong-court line. Confirmed mechanisms: `A7vXlWIlyrI`'s frame 0 is a **monochrome
intro at a different zoom**; `HoHxFSX_gLk_s3` contains **two different venues**;
`sAjkpeRq4P4`'s eight scored frames all sit at **scale 0.734** relative to frame 0, inside a
zoomed opening title shot, and the eval never looks before frame 5262. **A single homography
cannot describe those clips over the scored window. That is not a bad label.**

**It is wrong about the remedy, and here is the product reason.** Our v1 user props an
iPhone on a fence and records one continuous take. **There are no cuts and no zooms in the
footage this product will ever process.** One homography per clip is the *correct* model for
the product; it is wrong only for a scoring pool sourced from edited YouTube uploads.
Building multi-homography support would be a seventh court-detection branch, on a subsystem
closed for v1, to fit footage the app will never see. **That is a no.**

**So: 1 session of pool hygiene, not a data-model change.** For each pool clip, measure
corner displacement across the eval's own 8 sampled frames (the instrument exists and is
validated — null 0.000 px on all 28, injected 8.000 recovered 7.95–8.10 on all 28) and
either restrict the sampled window to a single camera setup or **drop the clip and record
the exclusion in the open**. A pool that scores a detector against a court that does not
exist in those frames is measuring nothing.

**A bar is required before it runs (rule 2)** — the exclusion threshold must be fixed in
advance, and the obvious candidate is the project's own `WRONG_PX_640` = 20 px. Pre-register
it, do not choose it after seeing which clips it removes.

**The consequence three steps out, stated because it is not obvious:** if 4 MIXED clips
leave the pool, the pool is **16 clips, not 20**, and the "≥12 of 20" phrasing of the gate
does not survive contact with that. **The gate does not move — it is pre-registered and it
does not move.** If the reference pool shrinks, the gate's *fraction* must be restated
before any re-run, not after, and by the lead, not by whoever is running the eval.

---

## D.4 — Setup-time camera movement. **+1 session, riding on the setup-screen brief. This is the only item here with a v1 consumer.**

**Call: fix it by ORDERING, not by perception. Calibrate LAST.**

The founder is right that this is a real regime and right that nothing addresses it. The
current work is all post-hoc, on recorded files, on edited clips. What he is describing is:
a person props a phone on a fence, walks fifteen metres to the baseline, and the phone is
not where it was when they were fiddling with it.

**Three sub-regimes, three different answers:**

**(a) Movement while propping / before recording — the real one. Answer: reorder the
screen.** The 4-tap calibration must happen on a frame captured *after* the phone is in its
final position and the user has stopped touching it — ideally the first frame of the actual
recording, confirmed by the user when they walk back, not a frame captured while they are
still setting up. **This deletes the entire regime by sequencing and costs no perception
work at all.** It is the single highest-value thing in this document per session spent, and
it is a frontend ordering decision.

**(b) Is the phone settled? Answer: an IMU stillness check, not a court check.** And the
reason it must be the IMU is a measured finding from Part A: **four motionless 4K tripods
disagree with themselves about the court by 29.9–37.5 px@640**, and motion compensation is a
**0.01 px no-op** on static clips. **You cannot tell whether the camera moved by watching
the court fit wobble** — the fit's own noise is larger than a wrong court. `CMMotionManager`
gives accelerometer and gyro at zero inference cost, and "phone not settled — wait" is a
**refusal**, which is the largest un-owned area in v1 and already on frontend-dev's plate.

**(c) Drift during the match. Answer: CUT from v1, and say why.** A threshold for "the
court moved" cannot be set: the instrument's own self-disagreement (24.8 px@640 on
motionless footage) exceeds the 20 px wrong-court line, so any drift detector would fire on
tripods. The honest v1 behaviour is to do nothing and let the user see it. Naming this as a
deliberate cut is better than leaving it as an unowned gap someone re-proposes in a month.

**Rule-3 check:** nothing about setup-time motion appears in "What has not worked". This is
new ground, not a re-proposal. Mid-match motion compensation *is* measured and dead
(§A.2) — and (a)/(b) are not that.

**On-device catch:** CoreMotion is on-device by construction. No network, no inference, no
ANE budget, no new model. **Nothing here touches the 100%-on-device constraint.**

**Definition of done:** the setup screen cannot reach the calibration tap until the IMU
reports the device still for a stated window; the tap operates on a frame captured after
that point; and there is a visible refusal state, not a warning. **A bar is needed before
the stillness window is chosen (rule 2)** — someone must pre-register what "settled" means
in accelerometer terms, before tuning it on one phone on one fence.

**Handoff brief — frontend-dev** (fold into the existing setup-screen item; do not spawn a
second run):
> Add to the 4-tap calibration screen: (1) calibration happens on a frame captured after the
> device is in final position, not before — reorder the flow so the user props, walks away,
> walks back, then taps; (2) a `CMMotionManager` stillness gate that blocks arming until the
> device is settled, presented as a refusal, not a warning. Pre-register the stillness
> threshold before tuning it. Do not attempt any court-based motion detection — the court
> fit's own noise on motionless footage is 24.8–37.5 px@640, larger than the wrong-court
> line, so it cannot see what you would be asking it to see
> (`docs/evidence/camera-motion-vs-court-agreement.md`).

---

## D.5 — `AGREE_PX`. **My call: fix nothing today. Do not ship the normalisation.**

**Reject the `30·(w/640)` change.** Three reasons, in order of weight:

1. **It admits a wrong court, and the gate forbids exactly that.** On the 1920 references it
   accepts `tc8CGFxyRE8` at **58.7 px** and `e8T34KoJzOw_s2` at **28.7 px**; `tc8CGFxyRE8`
   is described as a *reproducible* wrong court the tight radius was accidentally
   suppressing. **I checked whether that objection survives the provenance defect, and it
   does:** `tc8CGFxyRE8` was reviewed by the founder and marked **correct**, and it is one of
   the short locked-off tripods whose corners move under **0.5 px** by frame choice — so its
   reference is corroborated by *both* instruments, the eye and the frame sweep. A 58.7 px
   accept against that is a real wrong court. **The court precision gate does not move, and
   two changes have already died on exactly this.**
2. **A sibling of this idea is already a measured negative.** "Widening / height-scaling
   `AGREE_PX`" sits in "What has not worked": at the shipped vote bar, height-scaling
   **loses a gold clip (12 → 11)**, and the cell that lifts references 2 → 5 does it by
   accepting a **58.7 px** court. Rule 3 applies. Re-proposing the same trade under a
   different scaling law would make it the tenth re-proposed idea in that table.
3. **It has no v1 consumer.** `AGREE_PX` governs the auto-detect consensus vote. v1 ships
   manual 4-tap calibration. Even a clean win buys the product nothing.

**But the defect is real and should be recorded, not silently tolerated.** `courtfit.py:774`
violates the repo's own convention that every pixel threshold scales by `frame_height/720`
(CLAUDE.md, Conventions), and the consequence is that 4K shell clips must agree **~6× tighter
than the detector's own self-spread**. Two honest options: document it as a deliberately
resolution-dependent constant with a comment pointing at
`docs/evidence/agree-px-is-6-tighter-on-4k.md`, or fix it properly — and "properly" is not a
width multiplier.

**The properly-fixed version already exists in the repo as an untested idea, and it is not
the one in the negatives table:** *an agreement metric normalised in **court terms** rather
than image pixels — resolution-independent by construction, and able to weight width
separately* (`docs/evidence/court-detection-frames-that-each-find-the.md`). That matters
because the disagreement is dominated by **`w_near`/`w_far` — how wide the court is, not
where it is — on 13 of 18 clips**, and corner-distance agreement cannot weight width apart
from position. **That is the right experiment. I am not funding it**, because its consumer
is a subsystem closed for v1, and an idea that buys accuracy in a feature we are not
shipping loses to one that buys anything at all in a feature we are. Record it as the
correct first move **if** auto-detection ever reopens, with the gate pre-registered as:
≥12/20 on gold, **and zero accepted court over 20 px on gold AND references** — i.e. it must
not admit `tc8CGFxyRE8`.

---

## D.6 — Small, cheap, real

- **`detect_court_learned` silently prefers `courtnet_ft.pt`**, which was fine-tuned on a
  pool containing **17 of the 20 gold clips**. The CNN experiment had to force
  `court_detector.pt` through `COURTNET_WEIGHTS` to avoid self-grading. **That silent
  preference is a live trap in shipped code**: the next person to run court evaluation will
  self-grade without knowing. Make it refuse, or warn loudly, on any evaluation path.
  **backend-dev, ~0.3 session.**
- **A `README.md` in `data/output/corner_audit/`** stating that the 28 `*_corners.png` are
  frame-0 renders, superseded by `_f<N>` sheets, and must never be mixed with them in a
  review. **A caption, not a move** (§C.2). **~0.1 session.**

---

## D.7 — THE CUT LINE: what I would NOT do, and why

| Not doing | Why |
|---|---|
| **Re-measuring any court number before D.1 returns** | Re-running against a pool you are about to re-place is paying twice. D.1 is one session and may collapse half of Part B into Part A. |
| **A seventh court auto-detection branch** | Six measured, all closed; the ceiling is the line detector's ~6.4 px against a human click neighbourhood of ~5.8 px. Rule 3. |
| **Multi-homography support for clips with cuts or zooms** | The product records one continuous take from a propped phone. This fits footage the app will never see (§D.3). |
| **Shipping the `AGREE_PX` normalisation** | Admits a court 58.7 px from a doubly-corroborated reference; the gate forbids it; a sibling is already a measured negative (§D.5). |
| **Building the court-normalised agreement metric** | It is the *right* experiment and it has no v1 consumer. Named and parked, not forgotten. |
| **The direct-line-click falsifier** (click points *along* the four outer lines, ~30–60 min founder) | Still lowest leverage, unchanged from 2026-09-05. Its three outcomes are: detector fine → court stays closed; detector matches the gap → court stays closed; detector >10 px off → reopens a branch we are not funding for v1. **Its best case changes no v1 decision.** Ranking a cheap item last is the point of ranking by leverage rather than cost. |
| **A second full 28-sheet founder review** | The re-review is done. Ask only for what D.1 and D.2 specifically need, in one sitting. |
| **Moving or deleting the 28 frame-0 sheets** | They back ten founder verdicts. Destroying evidence behind a judgement is `calibration-provenance.md` §8.1 (§C.2). |
| **Anything with `courtnet_ft.pt` in it** | 17 of 20 gold clips in its training pool. Not a model, a mirror. |
| **Any of this ahead of the phone** | No part of this pipeline has ever run on an iPhone. Court is closed for v1; the Core ML export and the setup screen keep the head of the queue. **The court lane is now a maintenance lane, and it should look like one.** |

---

## D.8 On-device catch, for the whole document

**Nothing proposed here adds a network dependency, and nothing adds ANE load.** D.1 and D.3
are local git and local eval runs. D.2 is a human clicking in a localhost tool. D.4's IMU
stillness check is `CMMotionManager`, on-device by construction, zero inference. D.5 is
explicitly *not funded*. The one thing that would have cost ANE budget — a learned court
network — is closed for v1, and the costing that survives (§A.2) says it would have been
~2–5 s one-off anyway, which was never the problem.

---

## D.9 Open questions

1. **Does the gold pool share the defect?** Everything above is conditional on D.1. If it
   does, this triage is re-run with a much shorter Part A.
2. **`e8T34KoJzOw_s2` is not named anywhere in the review record I read.** It is in the
   pool, its corners were last written by `3399d58`, and normalising `AGREE_PX` admits it at
   28.7 px. Was it among the 28 sheets and marked correct, or was it never reviewed? That
   changes whether the §D.5 objection has one leg or two.
3. **`bump_ntrp30{,b}` are untracked and have no git history at all.** They carry two of the
   ten founder verdicts. What are they, where did they come from, and should they be in any
   pool?
4. **Was `7c8b8af`'s "Ten human court calibrations" claim ever verified by a human other
   than its author?** Half the scoring pool rests on a first-person commit message with no
   evidence in any of the ten files. The founder marking 0 of 10 wrong is the only
   corroboration, and it was made from frame-0 sheets — though all ten are short locked-off
   tripods under 0.5 px of frame-choice spread, which is why I treat it as corroboration
   rather than a coin flip.
5. **If four MIXED clips leave the pool, what does "≥12 of 20" become?** The gate does not
   move; its denominator might. That restatement is the lead's, in advance, in writing.

---

# Coverage — what I read, skimmed, and did not open

Honesty about coverage, since a triage that hides it is worth less.

**Read in full (every word):**
`docs/TRAPS.md` (all, incl. T23, T24, T25, T26) · `docs/evidence/calibration-provenance.md`
(all 8 sections + addendum) · `docs/evidence/court-detection-path-after-the-line-ceiling.md`
· `docs/evidence/court-mask-sweep-item-is-already-shipped.md` ·
`docs/evidence/yt-match40-calibration-is-wrong.md` ·
`docs/evidence/agree-px-is-6-tighter-on-4k.md` ·
`docs/evidence/widening-height-scaling-agree-px-to-recover.md` ·
`docs/evidence/court-detection-frames-that-each-find-the.md` ·
`docs/evidence/indoor-shell-courts.md` ·
`docs/evidence/8-court-gold-frames-are-mislabelled.md` ·
`docs/evidence/v1-resequenced-after-court-closure.md` · `eval/run_refs.py` lines 1–120 (the
docstring, `CORNER_SOURCE_COMMIT`, `FLAGGED_COMMITS`, `FLAGGED_SESSION`,
`provenance_warning`) · `CLAUDE.md` · my own journal and agent memory index.

**Read in `docs/STATE.md` (it exceeds the read limit; I read it in four targeted slices, not
whole):** lines 1–140 (header, the stack, all 35 "What has worked" rows), 140–205 (the
court-relevant span of "What has not worked", ~65 rows), 209–228 (Withdrawn figures, in
full), 235–254 (the top 20 rows of "Open", including all three court rows added today).
**I did not read STATE past line 254** — the tail of "Open" and "Recently closed". If a
court row lives down there, I missed it.

**Not opened at all — and each is a real gap:**
`docs/evidence/camera-motion-verdict-risk.md` and
`docs/evidence/camera-motion-vs-court-agreement.md` (I worked from their STATE rows, which
are unusually long and carry the numbers and the controls; but the two files themselves are
unread, and the camera-motion claims in §A.2 rest on the row, not the source) ·
`docs/evidence/candidate-proposal-recall.md` (same — §B.2's 8/20 comes from the STATE row) ·
`docs/evidence/cnn-global-classical-local.md` (same) ·
`docs/evidence/external-research-reconciled.md` (same) ·
`docs/evidence/composite-calibration-score.md` (same) ·
`docs/evidence/net-anchor-calibration-check.md` (same) ·
`docs/evidence/court-correspondence-gate.md` ·
`docs/evidence/least-squares-court-fit.md` (§A.2's numbers are from the STATE row) ·
`docs/evidence/verify-court-false-rejects.md` (same) ·
`docs/evidence/single-frame-court-auto-seed-in-the.md` ·
`docs/evidence/snapping-a-near-correct-court-onto-the.md` ·
`docs/evidence/lowering-the-court-consensus-bar-6-8.md` ·
`docs/evidence/scaling-the-court-refiner-s-reach-with.md` ·
`docs/evidence/independent-calibration-references.md` ·
`docs/evidence/setup-envelope-net-occludes-far-baseline.md` ·
`docs/evidence/net-baseline-solve-without-far-line.md` ·
`docs/ML_PRACTICES.md`, `docs/ML_PLAYBOOK.md`, `docs/modules.md`.

**Where that bites hardest:** §C's decision to keep the five auto-detection negatives is made
from their STATE rows, not their contents. If one of them is *superseded* rather than merely
finished, I would not have seen it. Anyone executing Part C should open those five before
concluding the archive list is complete.

**What I did NOT do this run, per the brief:** moved or deleted nothing, edited
`docs/STATE.md` not at all, wrote no code, ran no git command (no Bash available), re-placed
no calibration.

---

## NOT ESTABLISHED THIS RUN

- **§B.0's two-pool separation is an inference from four sources, not a direct check.** I did
  not read `eval/run_eval.py`, and I could not run `git log` or `grep`. If
  `run_eval.py --gold` in fact resolves its truth through `*_pts.json`, §B.0 is wrong and
  most of Part B gets worse, not better. **This is the single load-bearing assumption in the
  document and the lead should verify it in one command before acting on it.**
- **"2 of 20 confirmed misplaced" (§B.1)** is a join of the re-review verdicts against
  `run_refs.py`'s 20-clip map and `calibration-provenance.md` §5b/§7. It is arithmetic on
  files I read, not a re-run.
- **Session prices are pm estimates**, not bottom-up plans.
- **The claim that our footage contains no cuts or zooms (§D.3)** is a statement about the
  product's intended capture path, not a measurement of any recording we hold.
