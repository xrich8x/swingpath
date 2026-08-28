# backend-dev memory

Index only. Content lives in the linked files. Restructured 2026-08-28 from a single
monolithic file; nothing was dropped.

- [Where authoritative detail lives](where-authoritative-detail-lives.md) — the repo docs to read before scoping or proposing anything
- [Mobile port split](mobile-port-split.md) — what ports as-is, what is a rebuild, what is blocked on-device
- [iOS architecture rules](ios-architecture-rules.md) — ANE pinning, fixed shapes, sequential decode, checkpointing; constraints not preferences
- [ANE cost and the far-player crop](ane-cost-and-far-player-crop.md) — pose dominates on ANE, int8 buys nothing pre-A17, and upscale (not crop size) is the far-player lever
- [Calibration trap: check corners first](calibration-trap-check-corners-first.md) — a 0.9 px residual passed a calibration with no corner on any court line
- [Data limits: far-end contacts](data-limits-far-end-contacts.md) — thin populations, contaminated criteria, one corrupted shot list
- [Audio lane: screened, not measured](audio-lane-screened-not-measured.md) — 0 bail-outs on 88 clips incl. 62 indoor shell; the rolling floor is O(n·win) and the rewrite is prototyped
- [Traps this project paid for](traps-this-project-paid-for.md) — unscaled constants, stale stamps, fps confusion, rates about the wrong subject, counts nobody rendered
- [Ball detector choice is SPLIT](ball-detector-choice-is-split.md) — settled at the chain 2026-08-28: TrackNet wins ghosts, BallNet wins speed coverage; export TrackNet first
- [Chain-gate mechanism findings](chain-gate-mechanism-findings.md) — five failed attempts on the smoother: the reflected hypothesis has its OWN false-acceptance region, and tightness is not the lever
