# `smooth_forecast` adds ghosts on every clip and removes none

> Evidence for the `smooth-forecast-adds-ghosts` row in [docs/STATE.md](../STATE.md) (Open).
> Measured 2026-08-29 with `tools/eval_model_filters.py`, which runs the SHIPPED
> post-chain ladder stage by stage against the human gold clicks. Nothing here
> scores a model against its own output.

## Why this was measured

STATE records `smooth_forecast` as the largest single cost to speed coverage
(−12.0 pts on `am_hard_utr`, −9.7 on `yt_match40`) and says **no fix is proposed**,
because two attempts have failed and a third needs a mechanism that *separates*
real from false rather than admitting more of both.

What had never been measured is the shape of that cost. `suppress_false_locks` has
a real:ghost ratio on the record (~7 real ball frames per ghost, Session L). The
larger stage did not. Rule 10 — inspect the rejects.

## The result, on all 7 calibrated gold clips

Change across the `smooth_forecast` step (the row before it → FULL):

| clip | recall | Δ | ghost fires | Δ |
|---|---|---|---|---|
| `yt_match40` | 59.2 → 65.2 | **+6.0** | 6 → 7 | +1 |
| `yt_rally2` | 68.2 → 72.5 | **+4.3** | 5 → 6 | +1 |
| `gold_sAjkpeRq4P4` | 41.1 → 44.4 | **+3.3** | 3 → 6 | +3 |
| `am_hard_utr` | 55.6 → 54.4 | −1.2 | 1 → 6 | **+5** |
| `gold_UHf0LeMU2pg` | 65.5 → 61.3 | −4.2 | 0 → 0 | 0 |
| `gold_L73ep7JHiJ4` | 70.8 → 63.7 | −7.1 | 0 → 0 | 0 |
| `gold_uR5q2cSM6AY` | 73.0 → 65.0 | **−8.0** | 16 → 18 | +2 |

**Mean recall change −1.0 pt. Ghost fires +12 across the seven clips, and −0 — it
never removes one.** Recall is up on 3 clips and down on 4, so the sign is not
stable either.

`am_hard_utr` is the sharpest case: **1 → 6 fires while recall falls 1.2 pts.**
Four of the five added are FADED, and the tool's own note says a change that only
converts solid ghosts to faded ones has removed nothing — here it is *creating*
faded ones.

## What this does and does not establish

**Does:** the stage is not buying precision. A filter that adds 12 false fires and
removes none, for no reliable recall gain, is not making a trade — it is losing on
both axes at the per-frame level.

**Does not:** it does not explain the −12.0 pt *speed-coverage* cost, which is a
different metric — `seen_frac` over whole hit→landing spans, not per-frame recall.
Interpolated frames (4–20 per clip here) count as a ball for recall; whether they
count for coverage is exactly the open question. **Both numbers can be true and
this one does not supersede that one.**

**An n=1 read of this was wrong and is worth recording.** On `yt_rally2` alone
`smooth_forecast` looks clearly recall-positive (+4.3 pts). Across seven clips the
mean is −1.0 and the sign flips on four of them. The single-clip conclusion would
have been backwards.

## Caveat that bounds all of the above

Run with **`ballnet_v21.pt`**. The v1 ball detector is a founder decision for
**TrackNet** (STATE, 2026-08-29), so this describes the chain under a detector that
is not the shipped v1 choice. The obvious next check is the same ladder with
TrackNet weights: if the ghost-additive behaviour holds there too it is a property
of the stage, and if it does not it is a property of the pairing.
