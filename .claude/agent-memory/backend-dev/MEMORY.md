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
- [Chain-gate mechanism findings](chain-gate-mechanism-findings.md) — six failed attempts on the smoother: the reflected hypothesis's own false-acceptance region, tightness is not the lever, and the RTS backward pass is confounded with the forward gate
- [Null controls and pre-registered populations](null-controls-and-pre-registered-populations.md) - a FAILING null control is what makes a failed gate clean; a population described two ways is two sets
- [Smoother: two metrics, opposite verdicts](smoother-two-metrics-opposite-verdicts.md) — ghosts/recall are detector-PAIRING dependent, speed coverage is NOT; coasted frames are why
- [Perception cache families](perception-cache-families.md) — three incompatible families in data/output/; only detector_ab/ is a one-variable detector pair
- [int8 ball-graph mitigations, both rejected](int8-per-channel-is-a-noop-for-conv.md) — per_channel is a silent no-op (byte-identical graph); last-conv-in-fp32 barely moves it, the erosion starts upstream
- [Speed error is geometry, not detection](speed-error-is-geometry-not-detection.md) — rho -0.749 vs -0.098; both now CLOSED as gates — no `seen_frac` threshold is admissible
- [synth_truth as a paired-error rig](synth-truth-as-a-paired-error-rig.md) — the only compliant per-shot absolute speed error, and the recipe that keeps it faithful to the shipped chain
- [Band ratio of medians is a weak instrument](band-ratio-of-medians-is-a-weak-instrument.md) — seed-unstable enough to flip a sign; use accept-precision vs base rate, and seed-sweep before quoting
- [Top-2 margin is a risk gate, not a detector](top2-margin-is-a-risk-gate-not-a-detector.md) — passes on fp32, FAILS on int8, blind to dropout; at an exact tie the decode is right 3 of 4
- [Court fit ceiling is the LINES](court-fit-ceiling-is-the-lines.md) — all-lines least squares FAILS at 19.80 px; it out-fits the human homography, so the evidence floor is upstream of the fit
- [Net GROUND vs net TAPE](net-ground-vs-net-tape.md) — two rows, 0.914 m apart; confusing them condemned a CORRECT calibration, and band_ratio is a FAILED instrument
- [Net tape height is precision-limited](net-tape-height-is-precision-limited.md) — AGREES with the fitted heights; the 10% bar is ~3 px of tape row at 720p, so eyeball reads say nothing
