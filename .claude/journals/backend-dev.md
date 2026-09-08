# backend-dev - working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-09) CANDIDATE PROPOSAL RECALL

External-research item ranked 3rd of 9: the PROPOSAL-STAGE RECALL TEST. Measure what
fraction of gold clips EVER produce a court candidate within accept tolerance of the
human-clicked corners - regardless of whether the vote accepts it. Separates
"the search never found it" from "it found it and lost the vote".
Instrument: eval/candidate_audit.py (exists, UNRUN as of its docstring). Extend
minimally, do not fork.
Splits required: (2) mount height above/below ~2.0-2.2 m; (4) indoor shell vs outdoor.
DELIVERABLE: docs/evidence/candidate-proposal-recall.md
MESSAGE: researcher with the headline number; qa if it bears on EVID_BAND.
NOT-THIS-RUN: data/*_pts*.json edits; retraining; docs/STATE.md; git commit;
docs/evidence/external-research-reconciled.md; docs/evidence/evid-band-has-a-correct-value.md
STOP-WHEN: audit run + verdict written, or ~40 tool calls.

## PRE-REGISTERED BAR (written 2026-09-09 BEFORE running the audit)

DEFINITIONS fixed before looking:
- "correct candidate" = a per-frame court fit whose mean projected-DBL-landmark
  distance to the HUMAN court is <= 20.0 px@640. That is candidate_audit.WRONG_PX_640,
  the SHIPPED empty-band number. I am not inventing a tolerance.
- "proposal recall" R = (# gold clips with >=1 correct candidate on >=1 of K frames)
  / (# gold clips audited). K = 8 frames per clip, the script default.
- Population fixed before looking: every reference run_refs.references() returns
  (human `_exact` calibrations only; eala_pts_auto excluded by that function's rule).
  No clip dropped after the fact. Skips are reported as skips.

VERDICT BARS:
- SEARCH IS THE BINDING FAILURE if R < 0.50.
- VOTING/SCORING IS THE BINDING FAILURE if R >= 0.80 AND the shipped end-to-end
  correct-consensus rate is at least 25 points below R.
- MIXED / NEITHER DOMINATES if 0.50 <= R < 0.80, or if R >= 0.80 and the consensus
  rate is within 25 points of it (in which case nothing is badly broken at either stage
  on this corpus and the failures are clip-specific).
- CATASTROPHIC PROPOSAL CAP (the bounce-detector analogue) if R <= 0.20.
A failed bar stays failed. I will NOT read the threshold off the results.

SPLIT BARS (pre-registered):
- Mount-height mechanism is SUPPORTED only if R(low mount, <2.2 m) is at least 30
  points below R(high mount, >=2.2 m) AND n>=4 in each arm. Below n=4 in either arm
  I report the split as UNDERPOWERED and draw no mechanism conclusion.
- The shell global-search claim is SUPPORTED only if R(indoor shell) is at least 30
  points below R(outdoor), same n>=4 rule.

CAVEAT STATED BEFORE RUNNING: cf.auto_fit_frame returns ONE winner per frame, so the
"candidate set" this measures is the union of per-frame ACCEPTED fits over K frames,
not the raw pre-accept proposal pool. That is an UPPER bound on how bad the search is
and a LOWER bound on proposal recall. If R is low I must check whether the raw
pre-accept pool contains the truth, or the finding is about the accept gate, not the
proposal stage. Report which one I measured.

## STATE - 2026-09-09 - pre-registration written. Next: inspect run_refs.references(), mount-height + surface metadata sources, then run the audit.

## LOG
- CARRIED FORWARD: `python` broken Store shim -> backend/.venv/Scripts/python.exe
- CARRIED FORWARD: grep -rn at repo ROOT times out (walks .venv) - grep explicit dirs.
- CARRIED FORWARD: Grep/Glob TOOLS false "no matches" (T25); use bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS -> use Write tool for long docs.
- CARRIED FORWARD: bash /tmp not visible to Windows python.exe - use scratchpad abs path.
- eval/candidate_audit.py READ. It already computes exactly this: per-clip `n_good`,
  `best_err`, `agree_good`, `votes`, `cons_err`, `within_margin`, plus which accept
  TERMS the human court itself fails. Verdict strings already name the two failures.
  It needs NO new logic for Q1/Q3 - only the mount-height and surface SPLITS (Q2/Q4).
