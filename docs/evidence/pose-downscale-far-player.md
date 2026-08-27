# Downscaling pose input destroys the far player — GATE FAILS (measured 2026-08-27)

> Evidence for the `pose-downscale-far-player` row in [docs/STATE.md](../STATE.md)
> (What has not worked). Runs the P0-2 arm of the approved iOS plan
> ([mobile-viability-audit.md](mobile-viability-audit.md)): the Neural Engine cannot
> afford `yolo11m-pose@1280`, and the two candidate mitigations were (a) drop the input
> resolution, (b) crop around the ball contact at native resolution. This measures (a).

**Measured against:** the pipeline's own per-frame player-detection record
(`player_counts` in the perception cache), on the two calibrated gold clips, fresh runs
on GPU at commit `892cf60`. This is a **detection rate**, not accuracy against human pose
labels — it counts whether the pipeline located a player on each processed frame.

## The gate, pre-registered before the runs

> Far-player detection must not fall more than **2 points absolute** below the 1280
> baseline, at the smallest input size that also preserves player selection.

## Result — FAILS, by roughly 11 points on the clip that could measure it

| Clip | Input | Far player | Near player |
|---|---|---|---|
| `yt_match40` (8.8 m mount, 26.4° hfov) | **1280** | **11.0%** | 80.3% |
| | 640 | **0.1%** | 78.1% |
| | 384 | **0.0%** | 72.5% |
| `am_hard_utr` (1.74 m mount, 86.3° hfov) | **1280** | **1.0%** | 74.2% |
| | 640 | **0.0%** | 69.2% |
| | 384 | **0.0%** | 66.7% |

`yt_match40` is the clip that carries the finding: it had 11 points of headroom, and 640
takes ~11 of them. `am_hard_utr` never had enough far-player detection to measure a
2-point drop against — its 1.0% baseline is itself the finding, not a control.

**The near player barely moves** (80.3 → 78.1 → 72.5), which rules out the obvious
confound. This is not the model degrading across the board; it is specifically the small,
distant player disappearing — the mechanism you would predict, now measured.

## What this closes and what it does not

**Closed:** full-frame input downscaling as the way to afford pose on an A13. It is not a
tuning question; the far player is gone at 640 on both clips.

**Not closed:** the crop-around-contact path. A first probe (`tools/probe_crop_pose.py`)
reported 78.8% for full-frame vs 78.8% for a 448 px crop and was **invalidated on visual
inspection** (`tools/render_crop_probe.py`): a 448 px box on a 1280×720 frame is wide
enough to catch the *near* player almost regardless of where the contact was, and the
contact population was wrong — the camera sits behind the near baseline, so near-player
hits project past the net into far-court coordinates and were selected as "far-half".
**That probe measured nothing; the number is withdrawn, and P0-3 is unmeasured rather
than negative.** A retry needs a correct population and a detection test tied to the
specific person, not any box overlap.

## Two supporting facts, so the numbers are not misread

- **These are PRE-guard numbers** — corrected 2026-08-28, having first been written up here
  as post-guard, which was wrong. The perception cache is written inside `_perceive`;
  `_reject_static_player` runs afterwards in `analyze_video`, so the cache never sees it.
  That makes this table directly comparable to the figures in
  [the-far-player-is-a-detection-problem.md](the-far-player-is-a-detection-problem.md),
  which are also pre-guard. The gap between its 14.5% on `yt_match40` and the 11.0%
  measured here is a genuine difference across code versions, not two different stages.
- **The guard discards most of what perception found — and that is already known not to
  be the lever.** On the `yt_match40` 1280 run: perception located a far player on **1125
  frames**, `_reject_static_player` dropped **885 as "static-fixture"**, and the surviving
  240 fell under its own 15% floor, wiping the track. 79% discarded, and the guard's
  docstring names the cause (20 px / 8 px radii are depth-blind, so a far player's real
  motion is smaller than a near player's jitter).
  **Do not read this as a cheap win in the guard.** `body_relative` is the depth-invariant
  fix and is already a measured negative
  ([depth-invariant-static-player-guard.md](depth-invariant-static-player-guard.md)):
  it improved 1 of 3 clips, and on `yt_match40` specifically it changed **0.0 → 0.0**
  because the far player is on only 14.5% of frames — **already below the guard's own 15%
  floor, so a perfect filter changes nothing.** This run's 11.0% is lower still, so the
  same reasoning holds a fortiori. The prior conclusion stands: on this footage the far
  player is a DETECTION problem, not a filtering one.
- **`yt_match40` runs at `frame_step=1`** (30 fps source) and `am_hard_utr` at
  `frame_step=2` (60 fps source), so the denominators differ. Both are the pipeline's own
  default `auto` behaviour, not a setting chosen for this experiment.

## Shipped alongside, and why

Two small changes were needed to run the sweep at all, both no-ops on the default path:

- **`POSE_IMGSZ` env hook** (`pose.py`) — points a benchmark at a resolution no named
  preset covers, the same pattern `BALLNET_INPUT` already uses in `ball.py`.
- **The provenance stamp now reads the RESOLVED estimator, not the preset table**
  (`pipeline.py`). Before the fix, a 640 run would have stamped its perception cache
  `yolo11m-pose.pt@1280` — a cache mislabelled as a different configuration, which is the
  exact shape of trap T02. Found before it produced a wrong number, not after.
