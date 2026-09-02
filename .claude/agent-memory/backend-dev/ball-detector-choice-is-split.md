---
name: ball-detector-choice-is-split
description: BallNet v21 vs TrackNet was settled at the chain 2026-08-28 and SPLIT — TrackNet wins ghosts, BallNet wins speed coverage; do not reopen it as if undecided
metadata:
  type: project
---

**BallNet v21 vs TrackNet is measured at the chain and the answer is SPLIT, not a
winner.** Measured 2026-08-28, 10 gold clips, 1658 clicks, 272 no-ball frames, one
variable. TrackNet: solid ghosts 88 -> 62 (-29.5%) for 8 hits. BallNet: more
speed-confident shots and longer trails on both clips run end to end. `event_audit`
underpowered and indeterminate. Full detail:
`docs/evidence/ballnet-v21-vs-tracknet-at-the-chain.md`.

**Why:** `mobile/models/*.onnx` bundled TrackNet while the desktop default was BallNet
v21 — a silent divergence, and the two published detector-level verdicts (hit@10 vs
F1@4) point opposite ways. Rule 5 says ball work is judged at the chain, so neither
detector number could settle it.

**How to apply:**
- Do **not** re-run this as if it were open, and do not quote hit@10 or F1@4 as the
  answer. If a new ball detector appears, score it the same way:
  `tools/eval_detector_chain_ab.py` + `tools/run_detector_ab_analyze.py` +
  `tools/compare_match_products.py`.
- **Report the absolute `speed_confident` COUNT, never the percentage.** On
  gold_UHf0LeMU2pg the pct rose 51.2 -> 56.4 while the count was identical at 22,
  purely because the denominator shrank. The pct rewards a detector for emitting
  fewer shots.
- **There is no shot-count ground truth.** "shots 43 -> 39" is not better or worse.
  Only `event_audit.py` adjudicates emitted events, it runs on `yt_rally2` alone, and
  its own bar is that a raw count must move by >= 3.
- **On-device consequence:** BallNet v21 has **no Core ML export path today**;
  TrackNet's ONNX already exists in `mobile/models/`. Export TrackNet first; a BallNet
  conversion (512x288, 3-frame stack, fixed shapes, ANE validation) is a scoped line
  item, not a footnote.

**The split is now quantified on the coverage side (2026-09-02, matched
`detector_ab/` caches).** Shots clearing the 50% `seen_frac` speed bar after the full
shipped chain: `am_hard_utr` BallNet **73** vs TrackNet **50**; `yt_match40` **138** vs
**103**. BallNet's advantage is present from the raw tracker row (77.7 vs 69.6 / 81.9 vs
68.8), so it is a detector gap, not something the chain creates. The founder's TrackNet
decision therefore costs measurable speed coverage and that cost is now on the record —
it is a known trade, not an open question.

Related: [[traps-this-project-paid-for]], [[mobile-port-split]],
[[ios-architecture-rules]], [[smoother-two-metrics-opposite-verdicts]],
[[perception-cache-families]].
