# `data/yt_match40_pts.json` is MISCALIBRATED, and it PASSED the audit
# (found 2026-08-28)

> Evidence for the `yt-match40-calibration-wrong` row in [docs/STATE.md](../STATE.md).
> Found while rebuilding the P0-3 crop probe
> ([p0-3-crop-around-contact.md](p0-3-crop-around-contact.md)), not while looking
> for it.

**RECORDED, NOT FIXED.** The keypoints file is human-supplied ground truth. Rule 9
says a mislabel gets recorded and a human relabels it. Nothing in this repo was
edited to compensate, and no downstream number was quietly adjusted.

## The finding

All four clicked corners in `data/yt_match40_pts.json` lie on **no court line**:

| Landmark | Clicked | What is actually there |
|---|---|---|
| `near_bl_doubles` | (200, 620) | blank run-off asphalt, ~170 px below the real baseline |
| `near_br_doubles` | (1150, 600) | blank run-off, over the SwingVision watermark |
| `far_bl_doubles` | (415, 250) | the hedge, above the left net post |
| `far_br_doubles` | (1015, 235) | the fence and the trees behind it, off the court entirely |

Rendered, at 2× on frame 0: **`data/output/p0_3_calib_corners_yt_match40.png`**.

The real court on frame 0 (read off the pixels, sequential decode, no seeking):

- near-baseline **left doubles corner ≈ (103, 448)** — the baseline runs from there
  off the RIGHT edge of the frame, so `near_br_doubles` is not visible at all and
  cannot have been clicked;
- net tape ≈ y 288–292, net base at the posts ≈ y 330, posts at x ≈ 424 and 915;
- the far court is a ~20 px band and its baseline is **occluded by the net tape**,
  which is only possible when the camera is BELOW about 2.2 m.

The projected court from the committed file puts the near baseline at y ≈ 585 and
`NET_Y` at y ≈ 365 — both far below the real lines.

## Consequences, in order of how much they cost

### 1. The clip is not the camera the docs describe

The audit reports **11.3 m** and the pipeline's PnP solve **8.83 m at 26.4° hfov**;
`pose-downscale-far-player.md` describes the clip as an "8.8 m mount" — a description
now withdrawn along with that file's `yt_match40` column. All of those
are the bad homography talking. From the pixels: the doubles width spans ~1425 px at
the near baseline and ~475 px at the net, a 3:1 ratio over half a court, which puts
the camera **~5.4 m behind the near baseline** and, from the tape occlusion,
**under ~2.2 m high**. `yt_match40` is a phone on a tripod, the same class as
`am_hard_utr` — not a broadcast mount. **Both calibrated gold clips are low
cameras**, and neither has a measurable far court.

### 2. The P0-2 far-player numbers on this clip are withdrawn

`select_players_on_court` splits people by back-projecting their feet and comparing
to `NET_Y`. With the net line 35–75 px too low in the image, the NEAR player is
labelled FAR whenever they stand forward of it. Rendered:
**`data/output/p0_3_who_is_far.png`** — six frames sampled across the clip where the
cache holds a "far" player. In all six the red FAR box is on the near player, no
green NEAR box exists at all, and the real far player, plainly visible near the net,
is unboxed.

The arithmetic matches exactly: `far_kpts` is non-null on **1125 of 10268** frames =
**11.0%**, which is the number P0-2 published as the far-player detection rate at
1280. It is not a far-player rate. It is how often the near player stood forward of
a mislocated net line.

That does not automatically overturn P0-2's *conclusion* — but the 11.0 → 0.1 → 0.0
collapse is now at least as consistent with **label reassignment** under downscaling
(a jittering foot position crossing a wrong boundary) as with the far player
vanishing. It cannot be told apart from this data. The `am_hard_utr` arm of P0-2
(1.0 → 0.0 → 0.0) is unaffected by this specific defect but was never enough to
measure a 2-point gate against.

### 3. Everything downstream of the shot list on this clip inherits it

`striker = "A" if track[h][2] < court.NET_Y else "B"` (`pipeline.py`), and hit
detection runs through `ball_player_gap(ball_px, near_kpts, far_kpts, n)`. So on
this clip the shot list's player attribution is wrong and its hit times are partly
corrupted. Any per-player statistic measured on `yt_match40` should be re-checked
after recalibration.

## The audit cannot catch this, and that is the trap

`tools/validate_new_clip.py --audit` stamps the file **PASS, fit residual 0.9 px**.
The residual measures whether the four clicked points form a plausible projective
image of a regulation court. **Four arbitrary points in a sane trapezoid do.** The
audit has no term for "are these points ON the lines", because it never looks at the
frame. See `T23` in [../TRAPS.md](../TRAPS.md).

The one signal it does emit is the camera height, and 11.3 m for a clip that is
plainly a tripod behind a public court should have been read as an alarm.

## What needs doing (not done tonight — this is a human relabel)

1. Re-click `yt_match40` in `tools/court_setup_server.py`. `near_br_doubles` is off
   the right edge and will have to be extrapolated along the visible baseline; the
   left corner at ~(103, 448) is unambiguous and should anchor it.
2. Re-run perception on the clip; every `data/output/p0_*_yt_match40.*` cache is
   stamped with `homography_sha256` and will correctly refuse to be reused.
3. Re-run P0-2 against the corrected split before quoting 11.0% again.
4. Audit the other committed `data/*_pts.json` the same way — by rendering the
   clicked corners on the frame, not by reading the residual. `am_hard_utr` was
   checked tonight and its overlay is close but visibly skewed on the right side;
   it is not in the same category as this file, but it has not been verified either.
