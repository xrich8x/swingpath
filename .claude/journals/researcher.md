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

## TASK — what I was asked to do

Founder ONE question, framed deliberately as one: "What is left to try at the FAR END of
the court — for the player and for the ball — and which of it has a chain-level reason to
reach the rendered output?" Must test the one-problem framing (same root cause wearing two
hats, or two different problems — say which and why), rank what's left with mechanism +
why-not-dead-already + chain justification for ball items, pre-register a gate for the top
item, name what's now CLOSED, use WebSearch for outside literature and flag footage
mismatches. Write docs/evidence/*.md + ONE STATE row text. No code writes.

## STATE — DONE 2026-08-29

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
