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
