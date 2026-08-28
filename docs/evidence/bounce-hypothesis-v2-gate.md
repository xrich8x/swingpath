# `bounce_hypothesis` v2 — the pre-registered gate for the position fix

> Evidence for the `bounce-hypothesis-v2-gate` row in [docs/STATE.md](../STATE.md) (Open).
> **Written 2026-08-27, BEFORE any code.** Same bars as
> [ball-chain-gate.md](ball-chain-gate.md), which is not restated here — this
> file only records what changed and what the named failure mode is.

## Why there is a v2 at all

The v1 result ([bounce-hypothesis.md](bounce-hypothesis.md)) failed its gate, but
at full power it **passed the separation bar at 9.00:1 against >7**. That
disproves the premise the stopping rule rested on: the ~7:1 exchange rate is
**not** a property of the signal, because a second hypothesis beats it. Chain
work is open, and this is the first attempt with a *named* failure mode rather
than a general one.

## The failure mode, named

v1 fails on P2 (ghosts rise on 5 of 10 clips) and P6 (replication). The
diagnostic column is `wrong`, not `fp`:

| clip | hit Δ | wrong Δ | reading |
|---|---|---|---|
| gold_L73ep7JHiJ4 | **+6** | −3 | working as designed |
| am_hard_utr | **+5** | 0 | working as designed |
| yt_match40 | +3 | 0 | working as designed |
| **gold_UHf0LeMU2pg** | **−3** | **+5** | **the failure** |
| gold_uR5q2cSM6AY | 0 | +3 | same shape, smaller |
| gold_shell | +1 | +2 | same shape, smaller |

On `gold_UHf0LeMU2pg` the mechanism turns 3 hits into mislocks and adds 5
`wrong`. That is **not** "it admits ghosts": a ghost lands on a no-ball frame and
scores as `fp`. A rising `wrong` on *ball* frames means the reflected hypothesis
is being **accepted at the wrong position** — the ball is there, and the filter
is now placing it somewhere it is not.

**The hypothesis for v2:** the reflected state is accepted on the strength of a
χ² that the `restitution_band` variance inflation made too permissive in `y`.
v1 adds `(band·vy)²` to `S[1,1]`, and at a large pre-bounce `vy` that term
dominates the measurement noise, so the y-gate widens exactly when the ball is
fastest. **The x-gate stays tight, so a lock at the right x and a wrong y passes.**
That is a loosening hiding inside a mechanism that was supposed not to loosen
anything — the thing the whole design was meant to avoid, reintroduced by the
band.

## What v2 must change, and what it must not

**Change:** bound the y-inflation so it cannot exceed the measurement noise by
more than a fixed factor, or replace the band with a small discrete set of
restitution hypotheses (e.g. 0.6 / 0.75 / 0.9) each tested at the **unmodified**
`S`. The second is preferable: it keeps every gate exactly as tight as the
shipped path and makes "more hypotheses" the only difference, which is the
property that made the separation bar pass.

**Must not change:** `gate_chi2`, `reset_after`, `max_gap_s`, or anything in
`suppress_false_locks`. Those are the three failed threshold moves; folding one
in would make the arms differ by more than the flag under test (**T10**).

## The gate

All six bars from [ball-chain-gate.md](ball-chain-gate.md), unchanged, **plus one
added because v1 named a new failure axis**:

**P7 — `wrong` must not rise on any clip.** v1's real defect was mislocalisation
on ball frames, which P1–P6 only saw indirectly. Recall can rise while the track
gets less accurate, and this project has already shipped one metric that could
not tell those apart.

Run with `tools/eval_chain_gate.py` over all **10** cached clips — 1658 clicks,
272 no-ball frames. The 3-clip run is no longer an acceptable denominator.

## Stopping rule

**If v2 fixes the `wrong` regression and P2 still fails — ghosts still rising on
several clips — then the second-hypothesis idea has been given its fair test and
the smoother closes.** v1 has already shown the recall is real and the separation
bar is passable; if the ghosts cannot be held flat with the position bug fixed,
they are not a position bug.

This is the fifth attempt on this stage.

---

# RESULT, 2026-08-29 — the gate FAILS on 4 of 7 bars, and the named cause is DISCONFIRMED

**Measured against:** 1658 human ball clicks and 272 no-ball frames across all ten
gold clips, never trained on. **Evidence tag: MEASURED.** Chain stages are *invoked*,
not re-derived — `tools/chain_cache.py` calls the same functions in the same order
with the same parameters as `pipeline.analyze_video` (T15).

## What v2 is

The gate's preferred option: `restitution_band` is removed entirely and `e` is
enumerated over `{0.6, 0.75, 0.9}`, **each candidate tested at the unmodified `S`**,
lowest-χ² passing candidate wins. `gate_chi2`, `reset_after`, `max_gap_s` and
`suppress_false_locks` are untouched (T10). Shipped default is unchanged:
`restitution_set=None` reproduces v1 exactly, and the flag OFF is byte-identical to
the shipped path — both pinned by tests.

**Harness validated by reproduction before the A/B**: the v1 arm re-run after the
refactor reprints the committed v1 table row-for-row, and the P3 script's OFF arm
reprints `post_bounce_chain.md` part 3's committed counts exactly (am_hard_utr
**69**/120, yt_match40 **124**/196).

## The table

| clip | cal | ball | hit off → on | Δ | wrong Δ | no-ball | ghosts off → on |
|---|---|---|---|---|---|---|---|
| am_hard_utr | Y | 90 | 31 → 36 | **+5** | +0 | 24 | 11 → 11 (0) |
| gold_shell | n | 184 | 99 → 100 | +1 | **+2** | 55 | 20 → 18 (**−2**) |
| gold_clay | n | 111 | 47 → 48 | +1 | **+1** | 7 | 2 → 2 (0) |
| gold_am | n | 181 | 95 → 97 | +2 | +0 | 32 | 10 → 11 (+1) |
| yt_rally2 | Y | 258 | 109 → 109 | 0 | −1 | 26 | 4 → 5 (+1) |
| yt_match40 | Y | 184 | 97 → 100 | +3 | +0 | 24 | 5 → 6 (+1) |
| gold_UHf0LeMU2pg | Y | 168 | 82 → 82 | 0 | **+3** | 9 | 4 → 5 (+1) |
| gold_sAjkpeRq4P4 | Y | 151 | 55 → 57 | +2 | −1 | 33 | 4 → 5 (+1) |
| gold_uR5q2cSM6AY | Y | 163 | 85 → 85 | 0 | **+3** | 32 | 21 → 20 (−1) |
| gold_L73ep7JHiJ4 | Y | 168 | 79 → 83 | +4 | −1 | 30 | 5 → 5 (0) |
| **pooled** | | **1658** | **779 → 797** | **+18** | **+6** | **272** | **86 → 88 (+2)** |

| bar | result | |
|---|---|---|
| **P1** recall | 47.0% → 48.1%, +18 hits, no clip below the −2.0 pt floor | **PASS** |
| **P2** ghosts | 86 → 88, rising on **5 of 10** clips; bar is *must not rise on any* | **FAIL** |
| **P3** trusted-speed shots | am_hard_utr 69 → **73** (bar ≥77); yt_match40 124 → **127** (bar ≥132) | **FAIL** |
| **P4** separation | 18 real hits / 2 ghosts = **9.00 : 1** against >7 | **PASS** |
| **P5** power | 272 no-ball frames against ≥74 | **PASS** |
| **P6** replication | +5 hits on am_hard_utr, flat on three clips, ghosts up on five | **FAIL** |
| **P7** `wrong` must not rise on any clip | 285 → 291, rising on **4 of 10** — gold_shell +2, gold_clay +1, gold_UHf0LeMU2pg +3, gold_uR5q2cSM6AY +3 | **FAIL** |

**Not shipped. `bounce_hypothesis=False` and `restitution_set=None` stay the
defaults**, byte-identical to the shipped path and pinned by tests.

## v2 did move the named clip — and it was still not enough

On `gold_UHf0LeMU2pg`, the clip the gate was written around, v2 halves the defect:
**−3 hits / +5 wrong under v1 → 0 hits / +3 wrong under v2**. `gold_am`'s rise is
eliminated. But four clips still rise, so P7 fails as written.

## The gate's hypothesis is DISCONFIRMED, not merely unmet

The gate named `restitution_band`'s y-variance inflation as the cause. v2 removes
that inflation entirely, and gating at the unmodified `S` is **strictly tighter in y
than v1** — inflating a variance can only lower a χ² statistic, so v1 accepts a
superset. If the band were the cause, removing it should have zeroed the `wrong`
rises. It removed one clip of five, and 1 of 7 pooled.

A one-variable ablation isolates the two halves of v2 — a **single** `e = 0.75` at the
unmodified `S` (band removed, extra hypotheses *not* added):

| arm | hits | wrong | ghosts | separation | P7 rises |
|---|---|---|---|---|---|
| v1 (band, single e) | +18 | +7 | +2 | 9.00 : 1 | 5 of 10 |
| **band removed, single e** | **+21** | **+5** | +2 | **10.50 : 1** | 5 of 10 |
| v2 (band removed, three e) | +18 | +6 | +2 | 9.00 : 1 | 4 of 10 |

Two things follow. **Removing the band is the good half**; adding 0.6/0.9 costs 3 hits
and 1 `wrong` — the gate doc's preferred form is the worse of the two, and "more
hypotheses" does not help. And **the `wrong` rise is not gate looseness at all**: the
strictly-tightest arm reproduces the same 5 rising clips and the same +2 ghosts.

## What the added `wrong` frames actually are

Every frame that changed classification on three clips, with the distance from the
human click to the emitted position and to the **raw** pre-smoother detection:

**1. Ghost admission on ball frames** (miss → wrong). The raw detection was *already*
far off, and the reflected hypothesis admitted it at the unmodified `S`:

| clip | frame | d_raw | d_on |
|---|---|---|---|
| gold_shell | 226 | **502.2 px** | 501.6 |
| gold_uR5q2cSM6AY | 1162 | 76.0 | 69.1 |
| gold_uR5q2cSM6AY | 882 | 49.3 | 42.5 |
| gold_UHf0LeMU2pg | 1534 | 40.3 | 33.7 |
| gold_UHf0LeMU2pg | 852 | 20.2 | 13.4 |

**This falsifies the mechanism's core design claim.** The docstring argued that
*"all 19 chain false locks sit 208–829 px off the track, so a ghost fits neither
hypothesis"*. A lock **502 px** from the click fits the reflected one: negating `vy`
moves the predicted position far enough to cover it. The second hypothesis has its own
false-acceptance region, and these score `wrong` rather than `fp` only because a human
happened to mark a ball present on that frame. They are the same object as a ghost.

**2. Segment-restart degradation** (hit → wrong). A well-localised frame is pushed past
the 10 px radius because the branch inserted a segment boundary nearby, so the RTS pass
now smooths a different set of frames together:

| clip | frame | d_raw | d_off → d_on |
|---|---|---|---|
| gold_shell | 2146 | **0.7 px** | 1.5 → **11.3** |
| gold_uR5q2cSM6AY | 624 | 5.1 | **0.9** → **13.4** |

Neither mechanism is the band. Power caveat: 17 changed frames across 3 clips — these
name the failure modes, they do not quantify them. The 502 px case is not sampling noise.

## Which metrics route through the homography

- **P1, P2, P4, P7 — deltas are H-clean; levels are not, on 4 of 7 calibrated clips.**
  Scoring is a pixel distance to a human pixel click, so it is H-free. But the chain
  contains `gate_ball_to_court`, and on these caches that stage is **not** the no-op it
  was on the detector-A/B caches: it removes locks on `gold_sAjkpeRq4P4` (**−674**),
  `gold_uR5q2cSM6AY` (−43), `gold_L73ep7JHiJ4` (−30) and `yt_match40` (−5), and is a
  no-op only on `am_hard_utr`, `yt_rally2`, `gold_UHf0LeMU2pg`. It runs **before** the
  smoother and the flag only touches the smoother, so both arms receive byte-identical
  input and the **A/B deltas are uncontaminated**; the absolute recall *levels* on those
  four clips are shaped by H, and `yt_match40`'s calibration is confirmed wrong (T23).
- **P3 — window population is H-DEPENDENT on both clips.** The hit→landing spans come
  from the committed `match.json`, i.e. from the pipeline's H-dependent bounce
  detection. `yt_match40`'s H is wrong (T23) and `am_hard_utr`'s is skewed right, so the
  *set of windows* P3 scores over is placed by imperfect geometry. The spans are held
  identical across arms, so the delta is not biased — but P3's absolute 69 and 124 are
  not independent of the calibration.
- **P5** is a count of human labels. H-free.

## The stopping rule does NOT fire

Its trigger is *"if v2 **fixes** the `wrong` regression and P2 still fails"*. v2
**reduces** the regression (+7 → +6 pooled, 5 clips → 4) but does not fix it, so the
antecedent is not satisfied and the rule does not fire on its own terms. It is not
fired by reinterpretation here.

What the evidence does say is separate and stronger, and is for whoever sequences the
next attempt: the reflected hypothesis has a measured false-acceptance region of its
own, so a *sixth* attempt of this shape needs a mechanism that constrains **where** the
reflected state may be adopted — not another way of choosing `e`, and not another
tightening, both of which are now measured not to be the lever.

## A note on the fixture, recorded so it is not re-learned

The synthetic bouncing track in `test_bounce_hypothesis.py` **cannot distinguish v1
from v2**: swept over `vy` 18–42 px/frame against a post-bounce y-displacement of
6–44 px, all 100 combinations emit an identical number of real frames, because a
detection the bounce branch rejects is often re-seeded a frame or two later by the
ordinary `reset_after` path. Emitted-frame count is a poor proxy for branch
acceptance. This mechanism discriminates only on real footage, and a test now pins
that fact so a future attempt does not "validate" a change on the fixture and
conclude it is inert.

## Reproduce

```
backend/.venv/Scripts/python.exe tools/eval_chain_gate.py --bounce-hypothesis \
    --restitution-set 0.6,0.75,0.9
backend/.venv/Scripts/python.exe tools/eval_chain_gate.py --bounce-hypothesis   # v1
backend/.venv/Scripts/python.exe tools/eval_chain_gate.py --bounce-hypothesis \
    --restitution-set 0.75                                                      # ablation
```

CPU only — the chain runs off the cached perception, no GPU and no re-detection.
