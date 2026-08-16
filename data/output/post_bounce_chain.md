# The chain loses the ball after it lands — the stage is named, the fix fails

**Date:** 2026-08-15 · **Measured against:** the committed `yt_match40` and `yt_rally2`
perception caches + `match.json`, and 300 human gold labels per clip (never trained on).
**Evidence tag: MEASURED.** Chain stages are *invoked*, not re-derived — same functions,
same order, same parameters as `pipeline.analyze_video` (trap 15).

## 1. The diagnosis stands: it is the SMOOTHER

Session M measured that **81%** of untrusted speeds on yt_match40 had the detector firing
past the bounce and the chain discarding it. Attributed to a stage, counting locks in the
6-frame window after each of 196 shot landings:

| stage | locks in clip | in landing windows |
|---|---|---|
| raw (tracker out) | 7640 | 965 |
| `rectify_track` | 7403 (−237) | 949 (−16) |
| `suppress_false_locks` | 6474 (−929) | 877 (−72) |
| `gate_ball_to_court` | 6469 (−5) | 877 (**0**) |
| **`smooth_forecast`** | 5562 (−907) | **691 (−186)** |

**The smoother is 68% of the post-bounce loss** (−186 of −274), 2.6× larger than
suppression. And it is *disproportionate*: 21% loss rate inside the landing window against
14% clip-wide — the signature of a bounce-specific mechanism, not uniform gating.

On the test that actually gates speed (`real_landing`, ≥40% of the window real), shots
passing fall **177 → 160 → 139 of 196** across suppression and smoothing: the smoother
alone costs **21 shots**, suppression 16.

**The mechanism is in the docstring.** A reset needs `reset_after` **consecutive gated
detections**, so at a bounce the constant-acceleration model must first *reject 3 real
detections* before accepting the arc changed. In a 6-frame window that is fatal.

## 2. The obvious fix FAILS on replication

`reset_after` had **never been swept or recorded** (no mention in any evidence file).

**Pre-registered gate**, written before running, guards first:
- **G1 recall** hit@10px on human clicks must not fall > 2.0 pts
- **G2 ghosts** solid fires on human no-ball frames must not increase
- **G3 prize** `real_landing` pass rate must rise ≥ 5 pts

### yt_match40 (184 ball / 24 no-ball / 196 landings)

| `reset_after` | recall@10px | solid ghosts | real_landing |
|---|---|---|---|
| 1 | 57.6% | 8 | 81.6% |
| **2** | **54.3%** | **5** | **77.0%** |
| 3 *(shipped)* | 52.7% | 5 | 70.9% |
| 4 | 52.2% | 5 | 59.7% |
| 6 | 50.0% | 6 | 52.0% |

`reset_after=2` **PASSES all three**: recall +1.6, ghosts +0, real_landing +6.1.

### yt_rally2 (258 ball / 26 no-ball / 15 landings) — **GATE FAILS**

| `reset_after` | recall@10px | solid ghosts | real_landing |
|---|---|---|---|
| 1 | 42.6% | 7 | 80.0% |
| **2** | 43.0% | **5** | **80.0%** |
| 3 *(shipped)* | 42.2% | 4 | 80.0% |
| 4 | 41.5% | 3 | 73.3% |

`reset_after=2`: recall +0.8 [ok], **ghosts +1 [NO]**, **real_landing +0.0 [NO]**.

**VERDICT: FAIL. `reset_after` stays at 3.**

## 3. Why the two clips disagree — the transferable part

On yt_rally2 `real_landing` is **already 80% at every setting from 1 to 3**. There is no
headroom: that clip's ball is densely detected, so the reset delay rarely straddles a gap
that matters. The prize exists only where detections are **sparse** (yt_match40), while the
ghost cost is paid everywhere.

**The optimal reset policy scales with detection density** — the same shape as the
`max_gap_s` finding (Session H part 6), reached by an independent route. Tuning this on the
clip with the visible win would have shipped a setting that buys nothing and costs ghosts on
the other.

## 4. Power caveat, stated rather than buried

The ghost guard rests on **24 and 26 no-ball frames**. That is smaller than the 74 the
standing product gate uses, where sampling alone moves the count ±3.4 (trap 9). The +1 ghost
on yt_rally2 is **well inside noise**, so the honest reading is *"failed to replicate the
win"*, not *"proved to make ghosting worse"*. Both clips' `real_landing` columns are the
stronger signal, and they disagree decisively (+6.1 vs +0.0).

`am_hard_utr` — the 1.74 m amateur mount that killed the last smoother tuning — has **no
perception cache**, so replicating there needs a multi-hour run. It was not done, and no
claim here covers it.

## 5. What this leaves

The diagnosis is worth more than the failed fix. **The smoother's bounce handling is the
largest single cause of untrusted speeds**, and the same starvation is why the tennis
second-bounce rule contributes 0 of 62 rally breaks. A fix has to keep real post-bounce
detections *without* loosening the outlier gate globally — e.g. resetting on a *detected
bounce* rather than after N rejections, which is a mechanism change rather than a threshold
change, and is not what was tested here.

---

# Part 2 — the MECHANISM fix also fails, on all three clips

**Date:** 2026-08-15 (same session). `am_hard_utr` now has a perception cache
(14,499 frames, `frame_step 2`, **cuda**, thresh 0.5, hfov 86.3 — built to match the
device and settings of the yt_match40 / yt_rally2 caches so the three are comparable).

## The change

Part 1 concluded a real fix "must reset on a *detected bounce* rather than after N
rejections — a mechanism change, not a threshold change". That is `ball.smooth_forecast`'s
new `bounce_reset` (default **off**).

The discriminator is physical rather than a counter: in image pixels y grows downward, so a
descending ball has `vy > 0` and a bounce flips it. A rejected detection sitting **above**
the prediction while the model is still descending — with horizontal continuity required, so
an overhead false lock cannot trigger it — is a reflection, and resets on that frame instead
of two frames later.

## Result — same pre-registered gate, and it FAILS on all three

| clip | recall@10px | ghosts | real_landing | verdict |
|---|---|---|---|---|
| yt_match40 | 52.7 → **53.8** | 5 → 6 | 70.9 → **74.5** (+3.6) | FAIL |
| yt_rally2 | 42.2 → 41.5 | 4 → 5 | 80.0 → 80.0 (+0.0) | FAIL |
| am_hard_utr | 34.4 → 34.4 | 11 → **10** | 74.2 → 75.0 (+0.8) | FAIL |

Gate was recall ≥ −2 pts, ghosts must not rise, real_landing ≥ +5 pts. The prize misses on
every clip; +3.6 on yt_match40 is the best of them and is short of the bar. **Not shipped.**
Kept as an off-by-default parameter with the numbers in the docstring, so it is not retried.

## The finding that corrects Part 1's framing

Part 1 named "the chain stops following the ball after it lands" as one root cause with two
payoffs. **On the footage this project actually targets, it is a smaller lever than that
implied.** On `am_hard_utr`, `real_landing` is already **74.2%** at baseline, yet speed is
untrusted for **64 of 120 shots** — and the printed reasons are dominated by *coverage*
(`seen 10–49% < 50%`), with "landing not tracked past bounce" appearing in only ~20 of the
64. On yt_match40 the landing cause dominated; on the 1.74 m amateur mount it does not.

So the post-bounce loss is real, attributed and worth knowing — but **the binding constraint
on the target footage is overall in-rally coverage, not the frames after the bounce.** Two
attempts (threshold, then mechanism) have now failed to convert the post-bounce diagnosis
into a product gain, and the third clip says why it would not have paid much there anyway.

## Method notes

- **Trap 4 handled explicitly**: `am_hard_utr`'s gold is 50% odd frames and the cache is
  `frame_step 2`, so **125 of 250 labels land on a processed frame** and the rest are
  dropped rather than compared against a neighbour. Scoreable: 90 ball clicks, 24 no-ball.
- Ghost counts rest on 24–26 no-ball frames per clip, under the 74 the product gate uses
  (trap 9). The ±1 movements are inside sampling noise; the `real_landing` columns carry the
  verdict.
- `bounce_reset=False` is verified **byte-identical** to the default path, and the flag is
  proven non-inert (3,732 frames differ on real data). 4 tests pin both.

---

# Part 3 — the DOMINANT failure is in-rally coverage, and the same two stages own it

Part 2 found that on the target footage the binding constraint is overall in-rally
coverage, not the frames after the bounce. This attributes *that* loss, by the same
method: `seen_frac = real_fraction(hit, landing)` must be ≥50% for a speed to be trusted,
so the whole hit→landing span is counted at every chain stage.

| stage | am_hard_utr mean seen_frac | shots ≥50% | yt_match40 | shots ≥50% |
|---|---|---|---|---|
| raw (tracker out) | **75.5%** | **106**/120 | **79.3%** | **182**/196 |
| `+rectify_track` | 72.1% (−3.4) | 101 | 77.5% (−1.8) | 174 |
| `+suppress_false_locks` | 64.9% (−10.6) | 90 | 69.4% (−9.9) | 150 |
| `+gate_ball_to_court` | 64.9% (**0**) | 90 | 69.4% (**0**) | 150 |
| **`+smooth_forecast`** | **52.9% (−22.6)** | **69** | **59.7% (−19.6)** | **124** |

## The headline

**The detector already gives ≥50% coverage on 106 of 120 shots (88%) on am_hard_utr. Only
69 (58%) survive the chain.** 37 shots lose their speed to the chain, not to the detector.
yt_match40 is the same shape: 182 → 124.

Per-stage, consistent on both clips and in the same order:

- **`smooth_forecast` is the largest** — −12.0 pts on am_hard_utr, −9.7 on yt_match40
- **`suppress_false_locks` second** — −7.2 and −8.1
- **`gate_ball_to_court` costs exactly zero**, on both, reproducing Session G part 3
- together the two own **~85%** of the loss

The smoother's cost here is real detections its innovation gate **rejected** — a coasted
frame is drawn but does not count as seen, which is precisely what `real_fraction` measures.

## Why this supersedes the post-bounce framing

Parts 1–2 chased the frames *after* the landing. That is a real effect and it is 68% of the
*post-bounce* loss — but post-bounce is the minor failure mode. Across the whole flight the
same two stages cost **20–23 points of coverage**, which is what actually pushes shots under
the 50% gate. **The target is the same code, measured on the population that matters.**

## Deliberately NOT proposing a fix here

Two attempts at the smoother (a threshold, then a bounce-aware mechanism) have already
failed their pre-registered gate, and the reason both failed is that loosening the gate
buys coverage and pays in ghosts. Nothing in this measurement changes that trade — it only
says the trade is worth **20–23 pts of coverage** rather than the 3–4 the post-bounce window
suggested. A third attempt needs a mechanism that separates *real* from *false* better,
not one that admits more of both. Recorded and stopped.
