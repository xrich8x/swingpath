# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-09: CANDIDATE PROPOSAL RECALL (court only)

Question: on what fraction of gold clips does a court candidate within the accept
tolerance (WRONG_PX_640 = 20.0 px @640) EVER appear — regardless of whether the vote
accepts it? Separates "the search never found it" from "it found it and lost the vote".
GATES backend-dev's CNN-global/classical-local reorder. Message backend-dev with the
headline as soon as I have it.

DELIVERABLE: docs/evidence/candidate-proposal-recall.md
STOP-WHEN: audit run + verdict written, or ~40 tool calls.
Instrument: eval/candidate_audit.py (exists, marked UNRUN as of 2026-08-24).

## PRE-REGISTERED BAR — written BEFORE any result was seen (this is the whole point)

Let R = (# gold clips where >=1 per-frame lock lands <= 20.0 px @640 from the human
court) / (# gold clips audited).

- **VOTING BINDS** if R >= 0.80. The search reaches the right answer on nearly every
  clip; the loss is downstream (scoring/agreement/accept-conjunction). A CNN global
  localiser would then be replacing a stage that is already working -> external
  document's premise COLLAPSES.
- **SEARCH BINDS** if R <= 0.60. On >=40% of clips no correct candidate is ever
  produced, so no downstream gate/score/vote change can recover them -> external
  document's premise HOLDS, rebuild justified.
- **MIXED / INDETERMINATE** for 0.60 < R < 0.80. Say so; do not round either way.

Secondary, also pre-registered:
- HEADROOM H = (# clips with >=1 good candidate) - 12 (clips the shipped gate already
  accepts). H >= 4 clips => materially recoverable recall exists downstream.
- SHELL (indoor, historically 0/5 accepted): search binds on shell if shell recall
  <= 1/5; voting binds on shell if >= 4/5; between = mixed.
- MOUNT HEIGHT mechanism (net tape overlapping far baseline below ~2.0-2.2 m) is
  CONFIRMED as a distinct mechanism only if recall drops by >= 40 percentage points
  across the 2.0-2.2 m boundary AND the low group has >= 3 clips. Otherwise: not
  established, report the numbers only.

A failed bar stays failed. I will not read the threshold off the results.

## KNOWN CAVEAT TO STATE UP FRONT (identified from source before running)
`audit()` calls `cf.auto_fit_frame` per frame, which returns ONE winner per frame,
already past the per-frame accept conjunction. So what this instrument measures is
**per-frame ACCEPTED-LOCK recall across k frames**, which is a LOWER BOUND on true
proposal-stage recall (raw quad candidates before scoring are strictly a superset).
=> a HIGH R is strong evidence for "voting binds". A LOW R is weaker evidence for
"search binds" — it could still be the per-frame accept rule killing a proposed
candidate. The script's `truth_would_pass` / `truth_fails` columns address exactly
that second half (would the accept rule take the human court if handed it), so I
must report BOTH.

## LOG
- 2026-09-09: read journal + memory; read eval/candidate_audit.py in full (339 lines,
  docstring says UNRUN, no number in repo produced by it yet). Bar pre-registered above.
