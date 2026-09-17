---
name: int8-parity-verified-but-close-race-threshold-is-post-hoc
description: int8 ball-graph parity headline (5/528, 3/6 clips) reproduced exactly; the "close race" mechanism explanation is threshold-tuned to the failures, not independent
metadata:
  type: project
---

Verified 2026-09-03 (docs/evidence/int8-parity-qa-verification.md). The int8 vs fp32
ball-graph parity headline **stands**: recomputed 5/528 both-fire frames >10px
(0.95%) and 3/6 clips failing condition 3 (am_hard_utr, yt_rally2, gold_shell)
directly from `data/output/ball_detector_int8_parity_summary__*.json`'s full
`diffs_px` lists — matches the claimed table exactly, and `worst_frames` (top-10
truncation) happened to agree with the full list because no clip has >3 failures.
Arm B (`per_channel=True`) confirmed byte-identical to shipped (same sha256, same op
histogram). Arm C (`nodes_to_exclude=[final Conv]`) confirmed a real different graph
(17 ConvInteger + 1 fp32 Conv, 11.36MB) that still fails, with a primary blob-dump
match on the cited "area 15→2→3" figure for one of its 4 screen frames.

**Why:** the one place the lead's own narrative overreached — worth remembering as a
class of error, not just this instance. `<scratchpad>/margin_census.py`'s `CLOSE=0.15`
"close race" threshold was picked *after* seeing which 5 frames failed, chosen with
headroom over their exact margins (its own code comment says so). I recomputed the
margins directly (widest 7.69%, not the commented "7.4%" — small unexplained gap) and
swept CLOSE over 0.05/0.10/0.20/0.30: **"0 close races in the 2 clean-passing clips"
is robust at every threshold tried — that part is real signal.** But **"all 5 failures
are close races" collapses to 2 of 5 at CLOSE=0.05** — it only reaches 5/5 once the
threshold opens past the widest margin actually observed, which is circular by
construction.

**How to apply:** when a mechanism is claimed to "explain" a small set of already-known
failures via a threshold chosen after seeing them, always (a) ask whether the threshold
predates the result, (b) sweep it over a range wider than the one used, and (c) look
specifically for which sub-claims stay true across the whole range (independent) vs.
which only hold near the tuned value (circular). Report both halves — the pooled rate
and per-clip pass/fail numbers were fully independent and correct; only the causal
"why" story was the tuned part.
