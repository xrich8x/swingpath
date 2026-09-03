# `verify_court`'s coverage gate does not separate correct courts from wrong ones

> Evidence for the `verify-court-false-rejects` row in [../STATE.md](../STATE.md) (Open).
> Measured 2026-09-04 (lead).

## Why this was run

STATE's joint-line-to-model row names `verify_court` as the **largest single kill
category** in that solver — 9 of 30 tuning clips — and describes them as *"shipped
criteria rejecting a correctly-labelled court"*. That names the function but not which of
its three gates fires, so nothing actionable followed. This measures that.

**Different population, deliberately, and it is not a reproduction of the 9-of-30.** That
figure came from the solver's own 30-clip tuning set. This runs over **every committed
human calibration that has a video** — 25 clips — and asks a narrower question the shipped
pipeline cares about directly.

## Method

For each clip: build `H` from the **four human-clicked corners** (never a detector), take
one real frame, and run the shipped `calibration.verify_court` and its three components.
A refusal here is the shipped gate rejecting a court a human labelled — a false reject by
construction. Nothing trained, tuned, or written back. `H` comes from human clicks, so the
gate is the only thing under test.

The three gates (`calibration.py:1087`): `coverage >= 0.40`, `visible >= 0.30`,
`centrality >= 0.70`.

## Result: 3 of 25 human-clicked courts are REFUSED

| clip | coverage | visible | centrality | which gate fires |
|---|---|---|---|---|
| `CYqapSq5llo` | **0.328** | 0.955 | 0.946 | coverage |
| `HoHxFSX_gLk_s3` | **0.245** | 0.991 | 0.819 | coverage |
| `UHf0LeMU2pg` | 0.517 | 0.968 | **0.661** | centrality (a near miss on 0.70) |

`visible` never fires on any clip — its 0.30 bar is far below the observed range
(0.927–1.000), so on this evidence **it is inert**.

## The finding is not the 3 rejects — it is that the bar sits inside the correct-court distribution

Coverage on courts a human clicked spans **0.245 to 1.000**, and the 0.40 bar cuts through
the middle of it. Correct courts sitting just above the line:

| clip | coverage | |
|---|---|---|
| `HoHxFSX_gLk_s1` | 0.426 | correct, passes by 0.026 |
| `yt_match40` | 0.436 | **grossly wrong (T23), passes by 0.036** |
| `sAjkpeRq4P4` | 0.464 | passes |

> **`yt_match40` PASSES `verify_court`.** Its four corner clicks sit on run-off asphalt, a
> hedge and a fence — STATE calls it *"visibly, grossly wrong"* and it is the clip that
> defines trap T23. The gate designed to catch *"a self-consistent but WRONG court that
> doesn't lie on any white lines"* scores it 0.436 and accepts it, **above two courts that
> are correct**.

So the coverage statistic is not ordering correct courts above wrong ones. It is largely
ordering clips by **how visible their white lines are** — line contrast, surface, exposure —
which is a property of the footage, not of whether the court is right. `courtfit.py:171`
already says as much for one surface (*"verify_court is white-mask-blind"* on clay), and
one of the two coverage rejects here is the clay clip.

## What this does NOT establish

- **A false-accept RATE.** There is exactly **one** court here known to be grossly wrong
  (`yt_match40`). One example proves the gate *can* accept a wrong court; it cannot give a
  rate, and none is quoted.
- **That the 9-of-30 has been explained.** Different clip set, different pipeline stage. It
  is consistent with this, not established by it.
- **Anything about other frames.** One frame per clip (frame 30). Coverage varies with what
  is on the court at that instant — players, shadows, ball marks.
- **A replacement threshold.** None is proposed. Lowering 0.40 would admit `yt_match40`
  further, and the sweep discipline this project just applied to `seen_frac` says a
  threshold must be chosen on held-out clips against a pre-registered bar with a coverage
  floor — not read off the table that revealed the problem.

## What follows

The actionable statement is **not** "retune 0.40". It is that **coverage and centrality are
being asked to do a job neither can do**: separate a correct court from a wrong one using a
white-mask statistic that is dominated by line visibility. The T23 audit already showed the
same thing from the other direction — a 0.9 px reprojection residual also accepted
`yt_match40`, and the **camera-height fit** was the one screen that isolated it. That
suggests the discriminative signal here is **geometric plausibility of the implied camera**,
which `verify_court` does not look at, rather than a better white-mask threshold.

Reproduce: the script is in the lead's scratchpad (`verify_court_rejects.py`) and writes
`verify_court_rejects.json`; it imports the shipped `calibration` module and reads only
committed `data/*_pts*.json` plus their videos.
