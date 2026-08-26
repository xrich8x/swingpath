# The fourth smoother attempt: a second hypothesis, not a looser gate — GATE FAILS

**Date:** 2026-08-27 · **Measured against:** 532 human ball clicks and 74 no-ball frames
across the three calibrated gold clips, never trained on. **Evidence tag: MEASURED.**
Chain stages are *invoked*, not re-derived — `tools/chain_cache.py` calls the same
functions in the same order with the same parameters as `pipeline.analyze_video` (T15).

The gate was written **before** the code, in `docs/evidence/ball-chain-gate.md`, and is
not restated here so it cannot drift (one number, one home).

## The mechanism

Attempts one to three (`max_gap_s`, `reset_after`, `bounce_reset`) all widened what the
single constant-acceleration model would accept. Two independent routes had measured the
same **~7 real ball frames lost per ghost frame removed**, so widening rides that trade
rather than beating it.

This keeps `gate_chi2` **identical** and adds a second model. When a detection fails χ²
under *"the ball kept doing what it was doing"*, it is tested against the reflected
state — vy negated and damped by the restitution, vx carried through. A real post-bounce
detection fits that tightly; a ghost fits neither.

One implementation detail cost the first attempt: `x` inside the loop is the **propagated
prior**, so it has already taken a step at the pre-bounce descending velocity. Reflecting
it in place fixes the velocity and leaves the position a full frame wrong, and the branch
never fires. The prior has to be de-propagated, reflected, and re-propagated. The first
version looked inert on a synthetic bounce at every magnitude from 20 to 57 px/frame —
the same fixture trap `bounce_reset` hit, and the reason `test_flag_is_not_inert` exists.

## Harness validation

Before any A/B, the off-arm reproduces the committed per-stage table on `yt_match40`
**exactly** — raw 7640 → rectify 7403 → suppress 6474 → gate 6469 → smooth 5562,
matching `post_bounce_chain.md` part 1. The chain is genuinely being invoked.

`tools/chain_cache.py` **refuses to guess resolution or fps.** The caches record neither,
`res_scale = height/720` scales every pixel threshold in the chain, and defaulting to
1080p would have run both 720p clips 1.5× too loose while printing a clean-looking
result — trap T16 exactly. Measured from the videos: am_hard_utr 1920×1080 @59.94,
yt_match40 1280×720 @29, yt_rally2 1280×720 @60.

## Result — the gate FAILS

Seen frames through the full chain (detector saw it; coasted fills excluded):

| clip | off | on | Δ |
|---|---|---|---|
| am_hard_utr | 7566 | 7798 | **+232** |
| yt_match40 | 5562 | 5682 | **+120** |
| yt_rally2 | 619 | 628 | **+9** |

Scored against human clicks at 10 px, through the shipped chain:

| clip | ball | hit off → on | wrong off → on | no-ball | ghosts off → on |
|---|---|---|---|---|---|
| am_hard_utr | 90 | 31 → **36** (+5) | 21 → 21 (**0**) | 24 | 11 → 11 (**0**) |
| yt_match40 | 184 | 97 → **100** (+3) | 29 → 29 (**0**) | 24 | 5 → **6** (+1) |
| yt_rally2 | 258 | 109 → **110** (+1) | 38 → **37** (−1) | 26 | 4 → **5** (+1) |
| **pooled** | **532** | **237 → 246 (+9)** | **88 → 87 (−1)** | **74** | **20 → 22 (+2)** |

- **P1 recall — PASS.** Pooled 44.5% → 46.2%, up on all three clips, and `wrong` went
  *down*: the recovered frames are not mislocks.
- **P2 ghosts — FAIL on 2 of 3 clips.** +1 on yt_match40, +1 on yt_rally2.
- **P4 separation — FAIL.** 9 real hits recovered per 2 ghosts added = **4.50 : 1**,
  against a bar of >7. It does not beat the structural exchange rate; it is *worse* than
  it.
- **P5 power — met exactly**, 74 pooled no-ball frames.
- **P6 replication — FAIL.** A pass on one clip and a rise on another is a fail, which is
  precisely what killed `reset_after`.

**Not shipped. `bounce_hypothesis=False` stays the default**, byte-identical to the
shipped path and pinned by a test.

## What is honestly uncertain, stated rather than buried

**P4's ratio rests on a denominator of 2 ghost frames.** If the true delta were 1 the
ratio reads 9:1 and passes; if 3, it reads 3:1. The ratio is not well determined, and
±2 on 74 no-ball frames is inside the sampling noise T09 is about. The *recall* side is
much better determined: +9 hits on 532 clicks, positive on all three clips, with `wrong`
falling.

That does not rescue the result — the bar was pre-registered at >7 and is not met, and
rule 2 says a failed gate stays failed. But it does mean the **stopping rule should not
be applied mechanically**: as written it fires, and the finding it would close on is a
two-event denominator. The cheap, decisive follow-up is more no-ball frames, not another
mechanism.

## The one genuinely encouraging number

On `am_hard_utr` — the 1.74 m amateur mount this project actually targets — the result is
**+5 hits, zero new ghosts, zero new mislocks**. That is the separation signature the
gate was built to detect, on the clip that matters most for the product. P6 forbids
counting it as a win, and it is not counted as one. It is the reason the mechanism is
kept behind a flag with its numbers recorded rather than deleted.

## Reproduce

```
backend/.venv/Scripts/python.exe tools/chain_cache.py --keypoints data/am_hard_utr_pts.json \
    --out data/output/_amh_on.json --seen-only --width 1920 --height 1080 --fps 59.94 \
    --bounce-hypothesis data/output/am_hard_utr.perception.json
backend/.venv/Scripts/python.exe tools/eval_gold.py data/output/_amh_off.json \
    data/output/_amh_on.json --labels data/gold/am_hard_utr.labels.json --names off on
```
