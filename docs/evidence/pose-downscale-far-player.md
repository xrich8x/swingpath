# Downscaling pose input destroys the far player — GATE FAILS (measured 2026-08-27)

> ## CORRECTION 2026-08-28 — the `yt_match40` column is WITHDRAWN
>
> `data/yt_match40_pts.json` is miscalibrated: all four clicked corners lie on blank
> asphalt, hedge or fence rather than on any court line
> ([yt-match40-calibration-is-wrong.md](yt-match40-calibration-is-wrong.md)). The
> near/far split runs through that homography, so on this clip the pipeline labels
> the NEAR player as the far player — rendered in `data/output/p0_3_who_is_far.png`,
> six frames, red FAR box on the near player every time, real far player unboxed.
>
> The arithmetic is exact: `far_kpts` is non-null on 1125 of 10268 frames = **11.0%**,
> the figure quoted below. **It is not a far-player detection rate.** The 11.0 → 0.1 →
> 0.0 collapse is now equally consistent with label reassignment under downscaling as
> with the far player disappearing, and the two cannot be separated from this data.
>
> **Withdrawn:** the `yt_match40` rows, the "8.8 m mount" description of the clip, and
> the claim that this gate failed "by roughly 11 points". **Not withdrawn:** the
> `am_hard_utr` rows, and the near-player column, which is a near-player number either
> way. **The verdict is now UNMEASURED on the clip that carried it**, not reversed —
> re-run after the clip is re-calibrated by a human.

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

**Every `yt_match40` row below is WITHDRAWN (2026-08-28) — see the correction at the
top of this file. They measure the near player under a wrong net line, not the far
player.**

| Clip | Input | Far player | Near player |
|---|---|---|---|
| `yt_match40` — **WITHDRAWN**, and its "8.8 m mount, 26.4° hfov" is retracted with it | **1280** | **11.0%** | 80.3% |
| | 640 | **0.1%** | 78.1% |
| | 384 | **0.0%** | 72.5% |
| `am_hard_utr` (1.74 m mount, 86.3° hfov) | **1280** | **1.0%** | 74.2% |
| | 640 | **0.0%** | 69.2% |
| | 384 | **0.0%** | 66.7% |

`yt_match40` used to read as the clip that carried the finding — 11 points of headroom,
of which 640 took ~11. That reading is WITHDRAWN: the 11 points were the near player. `am_hard_utr` never had enough far-player detection to measure a
2-point drop against — its 1.0% baseline is itself the finding, not a control.

**The near player barely moves** (80.3 → 78.1 → 72.5), which rules out the obvious
confound. The reading that followed — *"it is specifically the small, distant player
disappearing"* — is WITHDRAWN: on this clip the collapsing column was the near player
seen through a wrong net line, so the two columns are the same person and the contrast
between them is not the contrast it was read as.

## What this closes and what it does not

**Closed — DOWNGRADED 2026-08-28 to NOT ESTABLISHED.** The claim was that full-frame
input downscaling is closed as the way to afford pose on an A13. With the `yt_match40`
column withdrawn, the surviving evidence is `am_hard_utr`'s 1.0 → 0.0 → 0.0, which the
file itself says was never enough to measure a 2-point gate against. Re-run after
recalibration before treating this as closed.

**Not closed — now MEASURED, provisionally.** See
[p0-3-crop-around-contact.md](p0-3-crop-around-contact.md): rebuilt with a
homography-free population and a person-specific test, the full 1280 frame finds the far
player at **0 of 25** far-end contacts on `yt_match40` while a 192 px native crop fed at
640 finds one at **15 of 25**, and the causal variable is the UPSCALE FACTOR, not the
crop. The history below is kept because it is why that rebuild was needed. A first probe (`tools/probe_crop_pose.py`)
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
  frames** (WITHDRAWN — those 1125 frames are the near player, see the correction at the
  top), `_reject_static_player` dropped **885 as "static-fixture"**, and the surviving
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
