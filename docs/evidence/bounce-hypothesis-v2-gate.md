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
