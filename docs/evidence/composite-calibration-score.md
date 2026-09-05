# A COMPOSITE calibration score: mixing every signal we built

> backend-dev, 2026-09-05. Scoped from the lead's pre-registration
> ("PRE-REGISTRATION — a COMPOSITE calibration score", `.claude/journals/lead.md`) and the
> founder instruction *"Don't just use the net — it should be a mix of all we've worked on."*
> **Read-only on ground truth:** no `data/*_pts*.json` was written to. Every corruption is an
> in-memory copy of the loaded corner dict. qa is evaluating this independently in
> `docs/evidence/composite-score-qa.md`; this file is mine and does not read theirs.
>
> **This is NOT a sixth gate.** Five accept/reject gates have failed on this project. The
> output here is a **score plus a reason string** for the human confirming setup. Whether it
> ever gates anything is a founder call, not this run's.

## Verdict, upfront

(pending)

## The pre-registered bar (lead's, unchanged, not retuned)

- Choose the combination rule on a **TRAIN** split of clips; report on a **HELD-OUT** split.
- **PASS** = on held-out clips, flags **>= 80%** of synthetic corruptions at **<= 1 false
  flag** among the calibrations believed correct, with **`eala_pts_auto` included as a
  negative**.
- **FAIL** = anything else. A sixth failure is a fine outcome.
- **Mandatory ablation:** each signal's SOLO score beside the composite. If one signal alone
  matches the composite, say so plainly — that kills the ensemble.
- **Report by corruption TYPE, never pooled.** Depth compression is the one that matters.

## The train / held-out split

(pending)

## Signals in the mix

(pending)

## The rule, chosen on TRAIN only

(pending)

## Held-out results, by corruption TYPE

(pending)

## Solo-vs-composite ablation

(pending)

## The one real wrong calibration (n=1)

(pending)

## Reason strings it emits

(pending)

## NOT ESTABLISHED THIS RUN

(pending)
