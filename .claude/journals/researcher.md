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

## STATE — IN PROGRESS

Read: journal, court-detection-negatives.md (full — 6.4px line ceiling, CLOSED
2026-09-05, CourtNet Tier2 20.2% held-out loses to courtfit Tier1).
NEXT: locate the external research doc itself (not yet found), then STATE.md rows,
then CourtNet fire-rate code, then web verification.

## LOG

- 2026-09-09 start. Journal rewritten for new task.
