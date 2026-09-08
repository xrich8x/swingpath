# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-09 (NEW TASK, supersedes the 2026-09-06 court-research task)

Reconcile the founder's EXTERNAL RESEARCH DOC (dated 8 Sep 2026: models, repos, one
benchmark paper; court/ball/player/bounce/shots/mobile/licensing) against what THIS
project measured. Its §8 "what actually transfers" and §9 "ignore" lists get graded
CONFIRMED / CONTRADICTED / NEWLY ACTIONABLE / NOT APPLICABLE with the specific
measurement that settles each.

Central claim to test hardest: our court failure is ONE systematic cause — ordering.
yastrebksv/TennisCourtDetector = CNN-global -> classical-local; we = classical-global
-> CNN fallback. It claims shell-court failure is a GLOBAL SEARCH failure (trusses/
lights/mesh outnumber the 8 court lines in Hough), CNNs robust via appearance, and
that this unifies 5 prior rejections into 1 error.
CRUX (decide, do not hedge): our measured ceiling is the LINE DETECTOR (~6.4px rms vs
truth, vs ~5.8px human click noise) — is that even the same axis as their CNN-global
localisation claim?

Also: (a) TrackNet-for-ball founder decision vs its §2.3 (TrackNetv2 20fps RTX3070;
YOLOv4 > TrackNetv2 on F1, arXiv 2302.09657) — ours chosen on chain accuracy vs human
gold, not fps. (b) Verify HF claims first-hand: CourtSide v1 card 85.6% vs v0.1 card
67.87%; kjfk bounce 0.951 LOMO; Gholamreza dataset provenance/licence. (c) Ultralytics
AGPL on a shipped commercial iOS app — resolve as far as reading allows.

FACTS GIVEN BY LEAD (do not re-derive): backend/weights/court_detector.pt = Jun 2023 =
UPSTREAM released weights -> we fine-tuned from their CHECKPOINT (courtnet_ft.pt Jul
2026, courtnet_split.pt Aug 2026), NOT their training script -> defuses its issue #13.
Our CourtNet figure is a FIRE RATE on amateur frames, not per-keypoint precision @7px
— confirm from code, say whether the two numbers were ever comparable.

DELIVERABLE: docs/evidence/external-research-reconciled.md
STOP-WHEN: written, or ~35 tool calls.
NOT-THIS-RUN: code, STATE.md, git commit, the other agents' files
(docs/evidence/candidate-proposal-recall.md, evid-band-has-a-correct-value.md).
CAUTION T25: Grep/Glob unreliable — prefer Read on known paths.

## STATE — **DONE 2026-09-09.** Deliverable written:
`docs/evidence/external-research-reconciled.md`. Verdict: diagnosis CONTRADICTED (0.80),
prescription NOT retired by the line ceiling (0.90), 15th keypoint ALREADY DONE (upstream's
own), duty-cycle NOT APPLICABLE (we are one-time; 1-in-30 would be 91x WORSE), Gholamreza =
upstream's own training set (strike it), CourtSide = ball/racket + axis-aligned court REGIONS,
cannot calibrate. Q1+Q2 answered; Q3-Q5 ungraded (never saw the doc). Nothing else to resume.

## STATE (history) — IN PROGRESS (resumed 2026-09-09, second attempt)

SCOPE NARROWED BY FOUNDER: **COURT ONLY**. Ball/bounce/shot-class/AGPL sections of the
doc are PARKED — mention only where they bear on a court decision.
Teams mode ON: qa is measuring proposal-stage recall (ask it for the number),
backend-dev is building CNN-global/classical-local. Do NOT touch their evidence files.

Read: journal, court-detection-negatives.md, STATE.md head, lead.md (full), DECISIONS_PENDING.
**GLOB AND GREP ARE 100% BROKEN this run (T25) — every call returns "No files found",
including `*` on the repo root. Read-on-known-path is the ONLY working file tool.**
External research doc NOT on disk under the obvious names (docs/EXTERNAL_RESEARCH.md,
docs/external_research.md, root EXTERNAL_RESEARCH.md all ENOENT).
FALLBACK IF NOT FOUND: reconcile against the lead's verbatim summary of its claims in
lead.md NOW section (lines 136-164) — that is a faithful restatement of §8/§9 court items.

**NO SendMessage TOOL IN MY FUNCTION LIST** despite the brief saying teams mode is on.
Tools I actually have: Read, Write, Edit, WebSearch, WebFetch, Grep(broken), Glob(broken).
So I CANNOT ask qa for the proposal-recall number. Say so in the report; do not fake it.

**DOC NOT FOUND after 8 guessed paths** (docs/EXTERNAL_RESEARCH.md, docs/external_research.md,
root EXTERNAL_RESEARCH.md, docs/research/external-research-2026-09-08.md, docs/research_notes.md,
docs/FOUNDER_RESEARCH.md, docs/evidence/external-research-reconciled.md). With Glob dead I
cannot enumerate. DECISION: proceed on the FALLBACK — lead.md NOW lines 136-164 is a verbatim
restatement of the doc's court claims, plus the five items itemised in my brief. Limitation
stated in the deliverable.

CONFIRMED ALREADY: `_courtnet.py` docstring — 15 heatmaps = 14 keypoints + 1 court centre,
"used only for training convergence", "kept byte-for-byte compatible with the published
checkpoint". So the 15th-keypoint recommendation is not just ALREADY DONE here, it is
UPSTREAM'S OWN ARCHITECTURE — the doc recommends adding something inherent to the checkpoint
it recommends. Stronger than the brief's framing.

STATE read (What has not worked, full). Two rows are decisive for the central claim:
- 2026-09-06 near-baseline+net solve: **availability binds harder than precision** — right
  doubles sideline found on 18/40 clips, net ground line 24/40, all four needed lines
  coexisting on only **10/40**. "Everything failing is DETECTION", control exact to 0.007 px.
- 2026-09-05 closure: line detector ~6.4 px vs ~5.8 px click noise; LS-fit over ALL matched
  lines drives line residual to 3.01 px (below the HUMAN homography's 6.44) yet reconstruction
  is WORSE (19.80 vs 17.10) — the fit is not the problem.

NEXT: (1) [done - fallback accepted]; (2) CourtNet fire-rate code (_courtnet.py,
train_courtnet.py:40, eval_court.py) to confirm 21.6% is a fire rate not px precision;
(3) court_detector.pt provenance; (4) 8-frame vote / duty cycle in calibration.py;
(5) web: CourtSide cards, Gholamreza dataset, yastrebksv repo health; (6) SendMessage qa.

## LOG

- 2026-09-09 start. Journal rewritten for new task.
- 2026-09-09 resume #2. Court-only directive. Glob/Grep dead — noted above.
