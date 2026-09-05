# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/researcher/`, and
findings go in `docs/STATE.md` + `docs/evidence/`. Do not duplicate those here.

---

## TASK — what I was asked to do (2026-09-05c, NEW TASK, prior one below is DONE)

Write docs/evidence/gravity-arc-pilot.md: design + pre-register the gravity-arc
calibration pilot (candidate #2 from independent-calibration-references.md). Six
points: what's measured/from what, error budget vs net tape's 3.2%/px, three warning
signs (T22, reproj_px non-certification, drag bias) each answered, confounds (spin,
wind, fps, degenerate scale-vs-g), pre-registered bar with a kill condition, on-device
feasibility. End with one RUN/DO-NOT-RUN + the one deciding number. STOP-WHEN: six
points written or ~30 tool calls. Concurrent with backend-dev (net-post detector) and
qa (ground-plane-blindness test) — do not touch their files.

## STATE — DONE 2026-09-05c

Deliverable written in full: docs/evidence/gravity-arc-pilot.md (all 6 points +
RUN/DO-NOT-RUN + PM tradeoff + NOT ESTABLISHED). KEY FINDING (not previously known):
read ball_physics/tennis_tracker/estimation/trajectory_fit.py::fit_arc directly —
it ALREADY fits drag+Magnus physics to a 2D pixel arc but holds g=9.81 FIXED
(physics/constants.py:24) and solves for launch state, camera scale assumed correct.
The inverted fit the brief describes (fix g, solve for scale k) does NOT exist —
new code, not a config flag. Derived analytically (not measured): pure isotropic
scale error gives g_apparent = k*g_true exactly, but this project's actual measured
failure (yt_match40) is an ANISOTROPIC hfov/depth misfit, not a scalar k — so even a
clean g reading resolves only 1 DOF of a multi-parameter error. Hand-derived
precision estimate: single-arc SE(g) ~20% from pixel noise alone at a low mount
(1.38-1.74m caps usable window to 8-15 frames, curvature-fit error scales 1/T² not
1/sqrt(N)) — already worse than the tape's proven 10% bar/3.2%/px. Drag shown
mechanistically (from the actual a_z formula) to bias asymmetrically by flight phase
in a way that actively masquerades as scale error, not just adds noise — a sharper
version of the tape's sag confound. reproj_px-cannot-certify carried at memory-index
detail only (primary evidence file un-locatable again this session, same T25 failure
as last session — flagged, not re-derived). Recommended: DO NOT build as a shipping
check; a narrow SIMULATION-ONLY pilot (extend synth_truth.py, inject known scale
error, recover k, ~half day, no GPU/footage/labels) with a sharp kill condition
(non-monotonic k-recovery OR >20% error at null k=1) is worth running only to settle
the science question. On-device: confirmed zero new ANE inference, pure arithmetic,
Accelerate/vDSP cost class same as the net tape. Also found and used: hfov_deg is a
GUESSED input (default 70°) in the desktop calibration path (calibration.py) but a
KNOWN AVCaptureDevice intrinsic on-device — the scale ambiguity this pilot targets is
smaller in the shipped product than in this project's own desktop gold clips, flagged
as an asymmetry not sized.

agent-memory updated: open-questions.md (new bullet appended with full summary +
pointer). MEMORY.md needed no edit (open-questions.md already indexed generically).
No DECISIONS_PENDING write (outside allowlist per this session's system prompt,
consistent with prior sessions) — no founder decision was generated needing it; the
RUN/DO-NOT-RUN call is a research recommendation, not a founder decision, left in the
deliverable and the final report.

~24 tool calls used, under 30. Nothing further to do this task.

---

## TASK — what I was asked to do (2026-09-05b, DONE, prior task)

Write docs/evidence/independent-calibration-references.md: rank OTHER independent
references (beyond net tape, already built) for validating a court calibration /
estimating camera height — net posts, people-as-scale, ball/gravity physics, other
court markings, vanishing points, shadows. Error budget each, confounds, low-mount
feasibility, on-device A13/CoreML feasibility. STOP-WHEN: ranked + ~30 tool calls.

## STATE — DONE 2026-09-05b

Deliverable written in full: docs/evidence/independent-calibration-references.md.
Organising finding (the throughline for the whole ranking): every FAILED check so
far (coverage, camera-height screen, net-anchor band_ratio/dy) reads only the
ground plane (z=0); the one check that WORKED (net tape) is off-plane. A
regulation court's own paint is near/far + left/right symmetric (net excepted), so
no ground-plane-only statistic can in principle separate the yt_match40-class error
(court compressed onto its near half, every ground-plane statistic still plausible)
from a correct one. Ranked: (1) net posts 1.07m - BUILD NEXT, cheap, off-plane,
rigid vs tape's sag confound, framing-limited in an UNMEASURED way (falsifier:
count post visibility across the 27 existing *_netanchor.png renders BEFORE
building anything, zero cost - flagged NOT ESTABLISHED). (2) ball/gravity arc -
theoretically sharpest (real physical constant + fps-timed seconds, not another
game-object assumption; corroborated as a real technique via WebSearch, e.g.
arXiv:2407.00574 gravity+body-height camera-scale calibration in mocap, and
several single-camera ballistic-trajectory sports papers - all broadcast/lab, none
amateur-phone-tennis, flagged as benchmark-transfer) but THIS PROJECT's own history
gives 3 reasons to expect a naive version fails cheaply if funded now: T22 (z=0
airborne-ball projection already known wrong), arc-fit-observability's own finding
that reproj_px cannot certify an arc (23.8x span passes - could not re-read the
exact evidence file, path unknown/T25-suspect, relied on the agent-memory MEMORY.md
index line which already had enough detail), and unmeasured per-shot drag bias
(-21.7% measured on average speed) that would fire on every CORRECT calibration.
Recommended as a narrow pilot only, not a build. (3) people-as-scale - works,
computed error budget (~4-5% population height term + uncharacterised pose
keypoint head/foot bias, stacked on the same off-plane logic) is wider than the
tape's measured 3-10%, no repeatability structure (every player a different
height) - corroborating signal only, not primary. (4) other court markings and (5)
vanishing points REJECTED as duplicate work already tried under different names
(verify_court coverage; joint line-to-model correspondence) - both inherit the same
ground-plane symmetry blindness, explained via court.py's own LANDMARKS dict
already containing all these points. (6) shadows - genuinely independent idea, not
rejected on argument, but ranked last: inapplicable on Shell (64/116 clips,
indoors), already shown to confound net-anchor band_ratio via the net's OWN shadow,
needs a wholly new detector with no existing component. Recommendation section:
build the post detector as a NUMBER for the human confirming calibration, never a
fifth autonomous gate (four gates in this family already failed identically:
coverage, camera-height screen, band_ratio, dy). Explicit "what would falsify this"
given for both the top candidate (post-visibility count) and the built detector
(reuse tape's own AGREE bar). Rejected-candidates table + NOT ESTABLISHED section
both present.

agent-memory updated: open-questions.md (new bullet, full ranking summary),
MEMORY.md index needed no edit (existing line already points at open-questions.md
generically). ~16 tool calls used this task, well under 30. No DECISIONS_PENDING
addition - no founder decision was generated, this is a research ranking with an
explicit recommendation and the "build first" item already named.

Nothing further to do. Final response to lead: point to the deliverable path, the
one-line recommendation (build the post detector as a diagnostic number, not a
gate; treat gravity-arc as a pilot not a build; reject markings/VP as duplicates;
shadows deprioritised), and the two falsifiers.

---

## TASK — what I was asked to do (2026-09-05, DONE, prior task)

Write assessment at docs/evidence/court-detection-path-after-the-line-ceiling.md: given
today's least-squares-court-fit.md result (fit ceiling is the LINE DETECTOR, not the
fitter/search — LS-geom fits detected lines BETTER than truth, 3.01px vs human's 6.44px
rms, yet reconstructs WORSE, 19.8 vs 17.1px, against 8.1px shipped bar) — what is the
right next build for court detection, or is there none? 5 points: (1) is 6.4px
detector/labelling/definitional, what's irreducible; (2) alternatives vs same bar
(classical line detect, CourtNet keypoints @ 21.6% fire rate, dense segmentation, manual
calibration as product answer); (3) hard constraints iOS/A13/CoreML/on-device only;
(4) is auto-detect even on v1 critical path given manual calib ships; (5) rule 11 (truth
=game not HUD). Negative assessment ("ship manual") is a fine, even expected, outcome.
STOP-WHEN: 5 points written or ~30 tool calls.

## STATE — DONE 2026-09-05

Deliverable written in full:
docs/evidence/court-detection-path-after-the-line-ceiling.md (all 5 points + recommendation
+ falsifier + NOT ESTABLISHED). Recommendation: STOP funding court auto-detection branches;
manual calibration IS the product answer for v1 (not a fallback). Key reasoning: the 6.4px
line-truth gap (least-squares-court-fit.md §3) is the SAME ORDER as the human corner-click
neighbourhood (~5.8px, eval/truth_neighbourhood.py / withdrawn 0.18-0.31 row) - so much of
the "ceiling" may be label/definitional noise, not a fixable detector defect. CourtNet
alternative already closed (STATE: wrong target, Tier2<Tier1 even capped) - did not reopen
it. Dense segmentation: judged untested but wrong-axis (attacks coverage, not the binding
precision ceiling) - recommend against funding, reasoning not measurement. iOS constraints
don't disqualify any candidate technically, just add ANE-budget cost on top of a weak
accuracy case. v1 impact: auto-detect confirmed OFF v1 critical path, frees the ~2900-line
courtfit/calibration C++ port (mobile-port-split.md already said skip-able, this
corroborates with the accuracy ceiling as the reason). One cheap falsifier proposed, not run:
click points ALONG lines (not just corners) on gold frames, measure detector residual
against that - >10px would reopen a narrow detector-bias branch, ~5-7px corroborates
near-irreducible.

agent-memory updated: court-detection-negatives.md (UPDATE 2026-09-05 block appended),
open-questions.md (joint-correspondence line updated to point at closure), MEMORY.md index
line updated. Nothing else pending - all 5 asks covered, ~17 tool calls used, well under
30. No DECISIONS_PENDING addition needed (no founder decision generated - this is a
research assessment, the "reopen if" condition is already fully specified in the
deliverable itself).

Nothing further to do on this task. Final response to lead should point to the deliverable
path and give the one-line recommendation + falsifier.

---

## TASK — what I was asked to do (2026-09-03, NEW TASK, prior one below is DONE/unrelated)

Write a point-boundary LABELLING PROTOCOL (not code, not the scoring state machine) at
docs/evidence/point-boundary-label-protocol.md. Six required items: (1) a boundary
definition precise enough for agreement + refusal option, (2) minimum field set with
purpose tags, (3) footage + n with a justified claim, (4) verification with no 2nd
labeller, (5) leak guard spec (name fn, don't write it), (6) file format vs schema.py.
Ends with founder's literal step sequence + hours vs the 3-6h budget. Blocks ~3-6h of
founder labelling time (DECISIONS_PENDING item 4) — cost of vagueness is founder hours,
not a re-run. STOP-WHEN ~30 tool calls.

## STATE — IN PROGRESS 2026-09-03

Read: prior journal (unrelated, done), point-boundary-ground-truth.md (memory),
audio-hit-detection-mobile-port.md (memory), the-score-and-rally-count-stop-pretending.md,
using-a-burned-in-scoreboard-as-ground.md, telling-labellers-the-rule-instead-of-
enforcing.md, DECISIONS_PENDING.md, backend/swingvision/schema.py, tools/_goldset.py,
backend/swingvision/audio.py, data/incoming/README.md (stale but has the gold table),
docs/evidence/audio-impact-screen-blocked-by-tooling-plus-gt-cost.md (has the 9 raw-file
table verbatim: 7 Hardcourt + 2 Clay, 0 Shell/Grass — reused directly, not re-derived).

TOOLING NOTE: Grep/Glob do not work with a directory `path` in this session (return "No
files found" even for dirs known to have matches) — only work when `path` points at a
single known file. Worked around entirely via Read on guessed/known paths. Flag for
next session: don't burn calls re-discovering this.

KEY REUSE DECISION: ball/court gold precedent is `data/gold/<clip>.labels.json` +
`train_ballnet.gold_source_videos` (leak guard, keys on basename per T17). Point-boundary
gold should mirror that shape (`data/gold/<clip>.points.json`) but NOT reuse schema.py's
Rally dataclass — kept separate, reasons in the deliverable §6.

## STATE — DONE 2026-09-03

docs/evidence/point-boundary-label-protocol.md WRITTEN, all 6 items + founder step
sequence + hours estimate (~5.6h worst case inside 3-6h budget) + "what this cannot fix"
section. agent-memory point-boundary-ground-truth.md updated with full pointer/summary.
DECISIONS_PENDING text (Shell/Grass footage gap) handed to the lead in the final report,
not written directly (outside write allowlist). Nothing else pending on this task.

## STATE — DONE 2026-08-29 (prior task, unrelated)

Read: journal (prior task DONE, unrelated), full STATE.md, agent-memory (player-detection-
negatives, ball-negatives, open-questions, coreml-ane-budget, project-method-rules), and
evidence files: far-player-motion-gate-result.md, 9-solid-ghost-balls.md,
expecting-a-detector-gain-of-any-kind.md, p0-3-crop-around-contact.md,
ballnet-v21-vs-tracknet-at-the-chain.md, far-court-recall.md, motion-attention.md,
raising-the-detector-s-input-resolution.md, speed-coverage-is-chain-shaped-and-the.md.

WebSearch done: SAHI (aerial VisDrone/xView, +5-7% AP untuned — smaller gain than our
own crop trick, different domain), Kalman-tiny-object survey (arxiv 2509.18451,
racquetball, ADE 31-114px / 3-11cm, 3-4x worse than standard MOT benchmarks — corroborates
tiny-fast-object tracking is hard generically, tempers the ball-side proposal), TOTNet
(arxiv 2508.09650, table tennis/badminton/tennis, BROADCAST/Paralympic footage, mechanism =
3D convs + visibility-weighted loss + occlusion aug — the loss/aug half we ALREADY shipped
and it worked; 3D convs is the new untested piece, but occlusion != far-end-smallness).

VERDICT REACHED: NOT the same problem. Shared root cause (optical undersampling at
15-24m from a fixed amateur mount), divergent failure mode: player is SEARCH-limited
(0/25 full-frame, crop+upscale escapes it — proven, weak, real signal); ball is
DISCRIMINATION-limited (detector already fires 73-76% of far-court frames; the ball's
own analog of "more resolution" — a whole-frame bump — was already tried and FAILED at
the chain, recall gain arriving as extra solid ghosts). That whole-frame-resolution result
is the single most important piece of evidence that the player's fix does not trivially
transfer.

Top ranked item PLAYER: re-center the P0-3 crop using a prior beyond the ball position
(the measured weak link is median 26.3px from crop edge) — cheap, zero new labels, reuses
existing P0-3/motion-gate infrastructure, not in the dead list. Full gate pre-registered
in the evidence doc.

Top ranked item BALL: Kalman/track-gated LOCAL re-query at higher effective resolution,
only in a small physically-constrained window, only during low-confidence/ambiguous
frames — argued as a genuinely different selectivity mechanism from the four closed
detector-level gains (local+constrained vs global+blanket). Flagged LOW-MODERATE
confidence (~25-30%) given the Kalman-tiny-object literature and the whole-frame-
resolution precedent. Lighter gate sketch, not fully specced — second priority, and I
say plainly the ball's far end has less genuinely open ground than the player's.

Closed explicitly in the answer: motion+contrast family (already closed as of yesterday,
3rd negative); any GLOBAL/whole-frame ball detector change (already closed by rule 6 +
four-for-four, and specifically the resolution bump); far-court label interpolation
(already a measured negative, different from my ball proposal — flagged so the two don't
get conflated).

DELIVERED: docs/evidence/far-end-player-and-ball-what-is-left.md written. agent-memory
updated (open-questions.md, player-detection-negatives.md, ball-negatives.md, MEMORY.md
index). Final answer + STATE row text handed to the lead in my closing report — I did not
and cannot touch docs/STATE.md.

## LOG

- (see STATE above — this is the first and only work session on this task)
