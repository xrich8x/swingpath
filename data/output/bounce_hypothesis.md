# A second bounce hypothesis in the smoother

> Evidence for the `bounce-hypothesis` row in [docs/STATE.md](../../docs/STATE.md) (What has not worked).
> Full write-up mirrored from `data/output/bounce_hypothesis.md`.

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
- **P4 separation — FAIL as measured here, and this figure is WITHDRAWN.** 9 real hits per
  2 ghosts added = **4.50 : 1** against a bar of >7. **WITHDRAWN 2026-08-27**: the
  denominator was two events. Re-run over all ten gold clips it is **9.00 : 1**, which
  PASSES — see the correction below. The conclusion drawn from it, that the mechanism is
  worse than the structural exchange rate, is retracted.
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

## CORRECTION 2026-08-27, same day: re-run at 4.2x the power, and P4 REVERSES

The verdict above used the three clips that had perception caches - 74 of the
gold set's 308 no-ball frames - and its separation ratio came down to a
denominator of two ghost frames. That was flagged at the time as not
well-determined. It was not: the seven missing caches were built
(`tools/build_gold_caches.py`, 104k frames, 37 min on the GPU) and the same
comparison re-run over all ten clips by `tools/eval_chain_gate.py`.

| clip | cal | ball | hit off -> on | wrong d | no-ball | ghosts off -> on |
|---|---|---|---|---|---|---|
| am_hard_utr | Y | 90 | 31 -> 36 (**+5**) | +0 | 24 | 11 -> 11 (0) |
| gold_shell | n | 184 | 99 -> 100 (+1) | +2 | 55 | 20 -> 18 (**-2**) |
| gold_clay | n | 111 | 47 -> 48 (+1) | +1 | 7 | 2 -> 2 (0) |
| gold_am | n | 181 | 95 -> 97 (+2) | +1 | 32 | 10 -> 11 (+1) |
| yt_rally2 | Y | 258 | 109 -> 110 (+1) | -1 | 26 | 4 -> 5 (+1) |
| yt_match40 | Y | 184 | 97 -> 100 (+3) | +0 | 24 | 5 -> 6 (+1) |
| gold_UHf0LeMU2pg | Y | 168 | 82 -> 79 (**-3**) | **+5** | 9 | 4 -> 5 (+1) |
| gold_sAjkpeRq4P4 | Y | 151 | 55 -> 57 (+2) | -1 | 33 | 4 -> 5 (+1) |
| gold_uR5q2cSM6AY | Y | 163 | 85 -> 85 (0) | +3 | 32 | 21 -> 20 (-1) |
| gold_L73ep7JHiJ4 | Y | 168 | 79 -> 85 (**+6**) | -3 | 30 | 5 -> 5 (0) |
| **pooled** | | **1658** | **779 -> 797 (+18)** | **+7** | **272** | **86 -> 88 (+2)** |

- **P1 recall - PASS.** 47.0% -> 48.1%, +18 hits on 1658 clicks.
- **P2 ghosts - FAIL.** +2 pooled, but they rise on **5 of 10** clips and the bar
  is *must not rise on any*.
- **P4 separation - PASS, reversing the 3-clip run.** 18 real hits per 2 ghosts
  = **9.00 : 1** against the >7 bar.
- **P5 power - PASS**, 272 no-ball frames against a bar of 74.
- **P6 replication - FAIL.** Recall *falls* on `gold_UHf0LeMU2pg` (-3 hits) and
  `wrong` rises +5 there: on that clip the reflected hypothesis is adopting
  positions that are not the ball.

### What this changes

**The gate still FAILS, and the mechanism still does not ship** - but on P2 and
P6, which are well-determined, rather than on P4, which was not.

**The stopping rule does NOT fire.** Its trigger was *"a mechanism designed to
separate still lands at or below the ~7:1 exchange rate"*. At full power it
lands at **9.00:1**, above the rate. So the premise the stopping rule was built
on - that ~7:1 is a property of the signal rather than of the filter - is
**disproved**: a second hypothesis does beat it. Ball-chain work is NOT closed.

**The figure `4.50:1` is WITHDRAWN.** It was a two-event denominator reported as
a ratio, and the whole-day-old conclusion drawn from it - *"it is worse than the
structural exchange rate"* - was wrong. The failure mode is not that this
mechanism admits ghosts faster than it recovers ball; it is that on one clip it
adopts the wrong position.

### The lesson, which is about the test set and not the mechanism

Every chain measurement this project has made ran on the three clips that
happened to have caches. Nothing chose those three - they were an artifact of
which clips someone had once run perception over - and they carried **24% of the
gold set's no-ball frames**. A pre-registered power floor (P5) was in the gate
precisely to catch this, it was met *exactly* at 74, and the result still
inverted when the denominator grew. **A power bar met exactly is not a power bar
met.** The caches are now built for all ten, so no future chain or detector A/B
inherits this.
