# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-09 LATE (WHAT WOULD MOVE COURT RECALL; supersedes the literature survey below,
## whose findings are RETAINED as STATE and feed part (b))

Deliverable: `docs/evidence/court-recall-what-would-actually-move-it.md`
(a) FIRST: is ~30 px@640 frame-to-frame self-spread on STATIC 4K shell footage EXPECTED
    (inherent precision floor of Hough/line-fit at that res) or ANOMALOUS (a specific bug)?
    Reason from method: sub-pixel line localisation, seed grid, downscaling, UNSEEDED RANSAC.
(b) Ranked lit list for OUR regime, each vs iOS A13/Core ML/on-device/PROPOSAL-stage +
    TRAINING DATA needed (we have NO indoor-shell gold).
Rule 3 check stated explicitly per recommendation. Name what I could not reach.
Must ENGAGE with pm cut line (docs/evidence/court-triage-2026-09-09.md): no 7th branch,
no multi-homography, don't ship AGREE_PX normalisation, don't touch courtnet_ft.pt.
STOP-WHEN: written or ~35 calls. NO code, NO measurement (no Bash), NO STATE.md edit.

## OLD TASK — 2026-09-09 (LITERATURE SURVEY) — findings retained below, task closed

**COURT ONLY.** Find out whether anyone has SOLVED or MEASURED court detection on
AMATEUR, LOW-MOUNT, often INDOOR-SHELL footage.

1. Fetch **arXiv 2404.06977** "Accurate Tennis Court Line Detection on Amateur Recorded
   Matches" — the PAPER, not the abstract. Method / dataset / mount heights / numbers /
   reproducibility. Highest-value fetch available.
2. Survey beyond the doc: court/field registration on amateur/consumer footage — tennis,
   padel, pickleball, badminton, basketball, football. Transferable question is METHOD:
   localise a known planar layout under clutter, low oblique, no broadcast framing.
3. Look for OUR failure specifically: line detection drowned by structural clutter
   (trusses, ceiling lights, fencing). Temporal/multi-view evidence, learned line/edge
   detectors (vs Hough), segmentation-then-fit, direct homography regression.
4. Assess strictly vs: iOS A13, Core ML, 100% on-device, must run at the **PROPOSAL**
   stage. State TRAINING DATA each needs — we have NO shell ground truth.

RANK by expected value. **Be willing to conclude nothing published helps.**
Say which sources I actually REACHED vs could not.

CONTEXT THAT DEFINES THE QUESTION (given by lead, do not re-derive):
- SEARCH binds, not the vote: proposal recall **8/20** gold clips; **shell worst 1/5
  recordings**; three shell recordings **no lock at all**.
- Criteria do not bind: a court median **4.9 px** from human clicks clears accept on 19/20.
- Upstream CNN cannot supply missing proposals: **2-3 of 14 keypoints** on amateur, below
  the 4 needed. Gold 12/20 -> 2/20; shell 20/80 frames -> **0/80**.

DELIVERABLE: `docs/evidence/amateur-court-detection-literature.md`
STOP-WHEN: 2404.06977 read AND survey ranked — or ~35 tool calls.
NOT-THIS-RUN: code; ball/speed/score/mobile; docs/STATE.md; git commit;
docs/evidence/shell-4k-refiner-reach.md; docs/evidence/search-ranking-defect.md.
CAUTION T25: Grep/Glob unreliable — prefer Read on known paths.
NOTE: **SendMessage does NOT exist in subagents** — established last run, do not look.

## STATE — IN PROGRESS. ~14 tool calls used.

**2404.06977 full text NOT REACHABLE.** arXiv has NO html/ar5iv version (404 / 307 back to
abs). PDF downloads but Read cannot render it (no poppler). r.jina.ai 403, academia.edu 403,
aimodels.fyi 403, themoonlight.io 429 (x3), semanticscholar API 429. papers.cool = metadata only.
So everything below is from arXiv abs + search-engine-indexed PDF text. SAY SO IN THE REPORT.

ESTABLISHED about 2404.06977 so far:
- Agrawal, Sundararajan, Sagar; submitted 10 Apr 2024; accepted to **5th Intl Conf on Image,
  Video Processing and AI (IVPAI)** — a minor venue, not a CV conference.
- Method = **enhanced Hough + homography estimation**, i.e. the FARIN-family court-model fit
  (gchlebus/tennis-court-detection is the open implementation of that lineage). Adds
  (a) shadow removal via **MTMT (Multi-Task Mean Teacher)** pretrained shadow detector ->
  binary shadow mask, (b) pretrained **object detection** (player/occluder removal),
  (c) **court-colour-based filtering**.
- Claimed result: **"94% accuracy in the best case"** — metric definition NOT yet found.
- No code release found; no GitHub repo located for the authors.
**CRITICAL for us: its base algorithm is the Farin-style joint line-to-model fit that this
project BUILT AND KILLED 2026-08-29 (C3 reconstructs 17.1 px@640 even given TRUE
correspondence, worse than shipped 8.1).** And its three additions all attack OUTDOOR
degradations (shadows, worn paint, players) — none attacks indoor structural clutter.

## STATE — **DONE 2026-09-09.** Deliverable written:
## `docs/evidence/court-recall-what-would-actually-move-it.md`. ~19 calls.
## Memory updated: court-detection-negatives.md + amateur-court-literature.md.
## Nothing outside the allowlist was written. No STATE.md edit, no code, no commit.
## If restarted: the work is FINISHED — just report it. Headline in STATE-2 below.

## STATE-2 (part a) — HYPOTHESIS FORMED, from reading courtfit.py. ~7 calls used.

ANSWER FORMING: 30 px@640 is **neither an inherent Hough precision floor NOR a bug** — it is
an ILL-CONDITIONED / near-null-space direction in the objective, plus MODE SWITCHING in a
discrete argmax search. Three legs:
1. **Quantisation cannot produce 30 px@640.** `_detect_lines` (courtfit.py:73) HoughLinesP
   theta bin = 1 deg, rho bin = 1 px, at NATIVE res; merge averages segments weighted by
   length so effective angular precision ~0.3 deg. On a 1500 px sideline at 3840 that is
   ~8 px = **1.3 px@640**. An order of magnitude below 30. Floor hypothesis DIES on arithmetic.
2. **The error is ANISOTROPIC, which noise is not.** Same static frames: near-baseline
   spread 3.3% (hillsborough_p02) vs far-baseline **93.9%**. flexi_joy_p07 9.8 near / 34.9 far.
   A quantisation floor is roughly isotropic; a 5-30x near/far asymmetry along the DEPTH
   direction is a conditioning problem.
3. **Mechanism named:** `_ori_detail` (courtfit.py:137-174) EXCLUDES lines with no nearby
   paint as UNMEASURABLE (`ev`, EVID_MIN) — correct for faded paint, but on a LOW MOUNT the
   net tape physically covers the far baseline (<2.0-2.2 m, Part A of pm triage). Drop the far
   baseline from the evidence set and the only observable pinning court DEPTH EXTENT is gone,
   so the fit slides along a ~1-param depth/width family at near-constant score. All shell
   mounts are low. Predicts exactly the observed near-pinned/far-free signature.
4. `autodetect` is a discrete **argmax over <=topk=12 refined seeds** (rankv), not a continuous
   estimator. One player crossing a line flips WHICH seed wins -> the 8 fits are a MIXTURE over
   hypotheses, not a scatter. So "self-spread" is not a precision measure at all.

CHEAPEST FALSIFIER, data ALREADY EXISTS: qa's `scratchpad/interframe_agreement.py` ->
`interframe.json` holds ALL pairwise distances per clip. Test MODALITY: if the per-clip fits
form tight clusters (<8 px@640 within, >30 between) it is mode-switching, not a floor.
Unimodal 30 px smear = floor. NO new measurement needed, just re-read the artefact.

Also a code fact, unproposed anywhere: HoughLinesP params are MIXED-scaling —
threshold=45 and maxLineGap=12 are ABSOLUTE, minLineLength scales with w. At 3840 that means
45 votes is ~6x EASIER (more spurious lines) while a 12 px gap is ~6x STRICTER (more
fragmentation). They pull opposite ways. Must rule-3 check before naming it.

## LOG

- 2026-09-09 previous task DONE: `docs/evidence/external-research-reconciled.md`.
- 2026-09-09 new task (literature survey) started. Journal rewritten.
- 2026-09-09 2404.06977: 10 fetch attempts, full text unreachable; facts above from abs+search.
