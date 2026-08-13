# Looking at the false fires

**Date:** 2026-08-13 · **Tool:** `tools/inspect_false_locks.py --stage raw`, viewer
`tools/false_fire_viewer.py` · **Evidence:** `data/output/false_fires/*/locks.json`
**Measured against:** every frame a human marked "no ball" on the ten-clip gold benchmark
(308 frames; "unsure" excluded). Detector alone, no tracker — the same population and the
same 3-frame window `eval_detector_gold.py` scores, so the counts reconcile exactly.

## The counts

| model | fires | of 308 | note |
|---|---|---|---|
| `ballnet_v21` (**shipped**) | 102 | **33.1%** | reproduces the standing figure |
| `pool_old_s0` (arm A) | 176 | 57.1% | |
| `pool_new_s0` (arm B, +57% data) | 166 | **53.9%** | |

Overlap between the shipped model and arm B:

| | frames |
|---|---|
| fire on all three | 86 |
| **arm B fires, v21 does not** | **76** |
| v21 fires, arm B does not | 12 |
| arm B only (neither v21 nor arm A) | 28 |

**This is the decision-relevant number and the A/B did not show it.** Arm-vs-arm, arm B
looks like a clean recall win at flat precision. Against what is actually shipped it is a
trade: **+12 pts of recall for +20.8 pts of per-frame false fire**, and the 76 extra
frames are spread across all ten clips (3–14 each), not concentrated in one venue that
could be dismissed.

Per-frame false fire is *not* the product (Session F), so this does not by itself block
promotion — but it does mean the chain test is now the deciding measurement rather than a
formality.

## What the detector is actually firing at

Classified by eye from the context sheets, all ten clips. Where Session F had already
classified a lock (`data/gold/false_lock_classes.json`, 78 of the 166), those classes are
carried through: racquet 30, player 19, fence 8, court_line 7, background 5,
court_surface 5, held_ball 2, signage 1, net 1. The remaining 88 are on clips that
postdate that pass and are **not** formally classified.

The recurring objects, per clip:

- **`am_hard_utr`** — *the green racquet*. This player's racquet frame is bright
  optic-green, the same hue as a tennis ball, and it is the single most common lock in
  the clip. Nothing in the pipeline distinguishes a ball-coloured ellipse on an arc from
  a ball.
- **`gold_uR5q2cSM6AY`** — *the racquet head at the top of the serve*. Almost every lock
  in this clip is a player mid-serve with the crosshair on the racquet head, which at
  that moment is a ball-sized bright blob at exactly the height a toss would be.
- **`gold_am`** — *background clutter*. Clubhouse, umbrellas, stacked chairs, potted
  plants, spectators. Plus this player's green-strung racquet.
- **`gold_shell`** — split between racquet/player and the venue: the green mesh fence
  with white numbers, and a red sponsor banner.
- **`yt_match40`** — the hedge. Includes the known ball-coloured foliage at frame 4773.
- **`gold_clay`, `gold_sAjkpeRq4P4`** — a far player at the baseline, loose balls and
  bare clay, treeline.
- **`gold_uR5q2cSM6AY`, `gold_L73ep7JHiJ4`** — *white shoes*. A recurring lock on a
  player's shoe against green court. Not a class in the Session F taxonomy.

### Some of these are real tennis balls

Confirmed at 44 px zoom, unambiguous: **`gold_L73ep7JHiJ4:1918`** is a tennis ball, seam
visible, being bounced in front of the player before a serve. **`gold_L73ep7JHiJ4:210`**
is a ball held at the hip. Both frames are human-labelled "no ball".

The labels are not wrong — the convention is *no ball in play* — but it means the metric
named "false fire" is counting two different failures: the detector inventing a ball, and
the detector correctly finding a ball that does not count. The four clips promoted to gold
on 2026-08-11 are serve-practice and warm-up heavy, with loose balls on court and balls
held before serving, so they carry more of the second kind than the legacy six do. **Not
quantified** — adjudicating all 166 is a Lab job, and the viewer exists to make it a
half-hour of clicking rather than a re-render each time.

## Two hypotheses killed

**"Some of these frames aren't tennis at all."** Four `am_hard_utr` locks looked like
close-ups of a face in the 140 px context tiles — apparently commentary cutaways, which
would have meant the old gold clips need trimming. **Wrong.** The full frames are
ordinary wide tennis shots with a player walking past the near corner; a head fills a
140 px tile taken from 1920×1080. The shipped face test agrees — 0 frames with a face
above `FACE_FRAC` across all 308. Recorded as Trap 18.

**"They're landing on the burned-in scoreboards."** Several gold clips do carry one
(`am_hard_utr` has a UTR score panel, `yt_rally2` the SwingVision HUD). Measured: **1 of
166** locks falls in the top-left corner region where those panels sit, and 17 anywhere in
the outer 12% band of the frame. Burned-in graphics are not the source.

So what survives is what Session F found and this extends: the confusers are on and around
**people, their racquets, and their shoes**, in the middle of the frame, in play.

## The viewer

```
py tools/false_fire_viewer.py --locks data/output/false_fires/new/locks.json \
    --compare v21=data/output/false_fires/ballnet_v21/locks.json \
    --compare armA=data/output/false_fires/pool_old_s0/locks.json \
    --out data/output/false_fires/false_fires.html
```

One self-contained HTML file, no server, no network. Every lock as a context tile; click
for context + zoom side by side; arrow keys to walk the set; filter by clip, by which
models fire, or to the 28 that only this model produces. The two crops exist because the
two questions need opposite framing — *what object is this* needs context, *is this
literally a ball* needs magnification — and judging either from the wrong one is how the
cutaway hypothesis above got written down in the first place.
