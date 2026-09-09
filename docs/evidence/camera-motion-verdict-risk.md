# Does camera motion invalidate the human corner audit?

**qa, 2026-09-09.** Measurement about the VIDEO only. No corner placement is judged here,
and no `*_pts.json` was read for anything except the four corner coordinates.

## HEADLINE FOR THE FOUNDER

**7 of the 10 "placed wrong" verdicts are AT RISK from frame choice.**
One more is borderline (WATCH). Only **2 of the 10** are clean on this question.

| verdict at stake | D (px@640) | status |
| --- | --- | --- |
| `HoHxFSX_gLk_s3` | 212.9 | AT RISK |
| `A7vXlWIlyrI` | 162.6 | AT RISK |
| `HoHxFSX_gLk_s1` | 119.4 | AT RISK |
| `sAjkpeRq4P4` | 80.4 | AT RISK |
| `bump_ntrp30` | 60.5 | AT RISK |
| `CYqapSq5llo` | 38.8 | AT RISK |
| `UHf0LeMU2pg` | 29.2 | AT RISK |
| `uR5q2cSM6AY` | 13.2 (20.5 on frame corners) | **WATCH — borderline, straddles the line** |
| `L73ep7JHiJ4` | 5.95 | SAFE |
| `demo30` | 0.04 | SAFE |

"AT RISK" means the frame the founder judged and the frames the evaluation scores are
displaced by **at least the distance this project calls a wrong court**. It does **not**
mean the placement is correct. It means the sheet cannot settle it either way.

**It also runs the other way, which the brief did not anticipate: 2 of the 18
"correct" verdicts are equally unsupported** — `HoHxFSX_gLk_s2` (110.5 px) and
`bump_ntrp30b` (40.2 px) were both blessed on a frame that differs from the scored body
of their own clip by more than the wrong-court distance.

## PRE-REGISTERED BAR (written into `.claude/journals/qa.md` before any frame was decoded)

Quantity: estimate the background (static-scene) similarity transform between the
**rendered frame (frame 0)** and each **evaluation-sampled frame**
(`eval/run_refs.frame_positions(total, 8)`); apply it to that clip's four clicked
corners; take the max over corners, then `D_clip` = max over the 8 frames. Units px@640.
This is exactly the apparent corner displacement a *correct* placement would show if
rendered on the wrong frame.

Bands, justified from `WRONG_PX_640 = 20.0`:

- **AT RISK: `D_clip >= 20.0`** — frame choice alone reaches the distance at which this
  project calls a court wrongly placed.
- **WATCH: `10.0 <= D_clip < 20.0`** — half the wrong-court line, inside the range where
  accepted-correct courts already live (3.4–13.9 px). Reported, not counted in the headline.
- **SAFE: `D_clip < 10.0`.**

Group control, also pre-registered: motion is a plausible driver of the wrong/correct
split only if the WRONG group's median `D_clip` exceeds the CORRECT group's by >= 10 px.

Nothing here was re-banded after seeing results.

## INSTRUMENT AND ITS CONTROLS

ORB (6000 feat) + ratio-test matching + `estimateAffinePartial2D` RANSAC, on frames
downscaled to 960 px wide; result converted to px@640. RANSAC on the whole frame — players
are a small minority of features and fall out as outliers.

Two controls were run **on every one of the 28 clips**, not once:

- **NULL** (frame vs an identical copy): **0.000 px@640 on all 28.** No bias.
- **POSITIVE** (frame vs itself translated by a known 8.000 px@640): recovered
  **7.95–8.10 px on all 28.** The instrument responds correctly at the decision scale.

**Instrument qualifier, stated rather than folded in silently.** Some frame pairs return a
"transform" from <30 RANSAC inliers with absurd parameters (`scale 0.0014`, `rot 177°`).
Those are not displacement estimates — they are *no common background*, i.e. a cut to a
different shot. They are excluded from the reported max and counted separately in the `cut`
column. **Excluding them lowers those clips' numbers, so it cannot inflate the headline.**

**Confirmation that the sheets really are frame 0:** `data/output/corner_audit/
A7vXlWIlyrI_corners.png` carries the caption `frame 0` in its own header, and the image is
pixel-consistent with the frame 0 I decoded (a monochrome intro frame — see below).

## FULL TABLE — all 28 clips

`Dc` = max clicked-corner displacement, `Df` = max frame-corner displacement (a
frame-only measure, independent of the corner file), `agree` = how many of the 8 scored
frames sit within 5 px of frame 0, `cut` = frames with no common background.

| clip | group | res | Dc px@640 | Df px@640 | median | agree | cut | band |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A7vXlWIlyrI | WRONG | 1920x1080 | 162.55 | 187.71 | 40.04 | 2/8 | 0 | **AT RISK** |
| CYqapSq5llo | WRONG | 1920x1080 | 38.76 | 38.32 | 37.23 | 1/8 | 0 | **AT RISK** |
| HoHxFSX_gLk_s1 | WRONG | 1920x1080 | 119.37 | 129.91 | 33.22 | 0/8 | 3 | **AT RISK** |
| HoHxFSX_gLk_s3 | WRONG | 1920x1080 | 212.94 | 218.17 | 53.11 | 2/7 | 3 | **AT RISK** |
| L73ep7JHiJ4 | WRONG | 1920x1080 | 5.95 | 6.38 | 4.99 | 4/8 | 0 | SAFE |
| UHf0LeMU2pg | WRONG | 1920x1080 | 29.16 | 28.39 | 14.23 | 4/8 | 0 | **AT RISK** |
| bump_ntrp30 | WRONG | 600x298 | 60.52 | 60.63 | 30.21 | 4/8 | 0 | **AT RISK** |
| demo30 | WRONG | 1280x720 | 0.04 | 0.04 | 0.04 | 8/8 | 0 | SAFE |
| sAjkpeRq4P4 | WRONG | 1920x1080 | 80.42 | 100.55 | 79.09 | 0/8 | 0 | **AT RISK** |
| uR5q2cSM6AY | WRONG | 1920x1080 | 13.15 | 20.53 | 12.50 | 3/8 | 0 | WATCH |
| HoHxFSX_gLk_s2 | CORRECT | 1920x1080 | 110.45 | 110.39 | 53.68 | 1/8 | 2 | **AT RISK** |
| am_hard_utr | CORRECT | 1920x1080 | 11.88 | 11.63 | 9.81 | 0/8 | 0 | WATCH |
| bump_ntrp30b | CORRECT | 640x338 | 40.16 | 40.17 | 20.07 | 4/8 | 0 | **AT RISK** |
| e8T34KoJzOw_s2 | CORRECT | 1920x1080 | 9.74 | 9.83 | 0.82 | 5/8 | 0 | SAFE |
| eala_segment | CORRECT | 1280x720 | 4.09 | 4.11 | 2.95 | 8/8 | 0 | SAFE |
| flexi_franz_p01 | CORRECT | 3840x2160 | 0.04 | 0.04 | 0.02 | 8/8 | 0 | SAFE |
| flexi_franz_p07 | CORRECT | 3840x2160 | 0.25 | 0.26 | 0.10 | 8/8 | 0 | SAFE |
| flexi_joy_p01 | CORRECT | 3840x2160 | 0.32 | 0.33 | 0.11 | 8/8 | 0 | SAFE |
| flexi_joy_p07 | CORRECT | 3840x2160 | 0.14 | 0.14 | 0.09 | 8/8 | 0 | SAFE |
| hillsborough_p02 | CORRECT | 3840x2160 | 0.07 | 0.11 | 0.06 | 8/8 | 0 | SAFE |
| hillsborough_p08 | CORRECT | 3840x2160 | 0.05 | 0.06 | 0.02 | 8/8 | 0 | SAFE |
| mpc_mixed_p02 | CORRECT | 3840x2160 | 0.15 | 0.17 | 0.07 | 8/8 | 0 | SAFE |
| mpc_mixed_p08 | CORRECT | 3840x2160 | 0.01 | 0.02 | 0.01 | 8/8 | 0 | SAFE |
| mpc_tuesday_p01 | CORRECT | 3840x2160 | 0.34 | 0.35 | 0.03 | 8/8 | 0 | SAFE |
| mpc_tuesday_p07 | CORRECT | 3840x2160 | 0.07 | 0.07 | 0.03 | 8/8 | 0 | SAFE |
| tc8CGFxyRE8 | CORRECT | 1920x1080 | 0.40 | 0.35 | 0.17 | 8/8 | 0 | SAFE |
| yt_match40 | CORRECT | 1280x720 | 0.27 | 0.32 | 0.12 | 8/8 | 0 | SAFE |
| yt_rally2 | CORRECT | 1280x720 | 0.37 | 0.47 | 0.15 | 8/8 | 0 | SAFE |

## DO THE TWO GROUPS DIFFER?

| group | n | median Dc | mean Dc | >= 20 px | >= 10 px |
| --- | ---: | ---: | ---: | ---: | ---: |
| WRONG-marked | 10 | **49.64** | 72.29 | 7 | 8 |
| CORRECT-marked | 18 | **0.30** | 9.93 | 2 | 3 |

The pre-registered >= 10 px median gap is **met, by 49.3 px**. So motion is a **plausible**
driver of the split — but three things stop that being a finding of cause:

1. **It is confounded with clip type.** 13 of the 18 CORRECT-marked clips are short,
   locked-off tripod recordings (all 10 shell clips, `tc8CGFxyRE8`, `yt_match40`,
   `yt_rally2`), every one below 0.5 px. The WRONG-marked group is mostly long
   broadcast/YouTube material with cuts and zooms. Source type predicts both membership
   and motion; nothing here separates them.
2. **Motion is not sufficient.** `bump_ntrp30b` (40.2 px) and `HoHxFSX_gLk_s2` (110.5 px)
   moved a lot and were still marked correct.
3. **Motion is not necessary.** `demo30` (0.04 px) and `L73ep7JHiJ4` (5.95 px) were marked
   wrong on frames that are essentially identical to the scored ones.

## THE MECHANISM IS CUTS AND ZOOMS, NOT DRIFT — and it was rendered, not inferred

Frames were rendered and looked at before this was claimed. Sheets in the scratchpad; the
findings:

- **`A7vXlWIlyrI` frame 0 is a MONOCHROME intro frame at a different zoom.** The whole
  match body is colour and framed differently. The audit sheet for this clip shows a
  black-and-white title shot. 2 of 8 scored frames agree with it; the rest sit 36–163 px away.
- **`sAjkpeRq4P4`: frame 0 matches NOTHING in the scored clip.** All 8 scored frames sit at
  `scale 0.734` relative to frame 0 — frame 0 is a zoomed-in opening shot with a
  "Frank vs Tim" title banner; the body of the clip is a wider view. Agreement 0/8.
  **This directly contradicts the one spot-check already done.** Frame 0 vs frame 500 look
  identical because frame 500 is still inside that opening shot; the zoom change happens
  after it, and the eval never looks before frame 5262. The `sAjkpeRq4P4` verdict is
  **AT RISK**, not confirmed.
- **`HoHxFSX_gLk_s3` contains more than one venue.** Frame 1808 is a visibly different
  court (different trees, different shadows, different fence) — that is what the 3 "cut"
  rows are. Frames 160 and 984 are the same court at two different zooms (scale 1.59, 1.28).
- **`bump_ntrp30` / `bump_ntrp30b`: a clean step.** Frames 45–392 are within 0.15 px of
  frame 0; frames 508–855 are a constant 60.4 px (resp. 40.1 px) away. One framing change
  mid-clip, and the sheet shows only the first framing.
- **`CYqapSq5llo`, `UHf0LeMU2pg`, `e8T34KoJzOw_s2`, `uR5q2cSM6AY`** show the same step
  shape at 37, 27, 9 and 13 px.
- **`am_hard_utr` is the only clip with genuine slow drift**: 6.2–11.9 px, no step, agreement
  0/8 at the 5 px level. WATCH, not AT RISK.

## WHAT I COULD NOT MEASURE, NAMED

- **No clip failed to measure.** 28/28 produced a credible transform on at least 5 of 8
  frames.
- **`HoHxFSX_gLk_s3` frame 3044** would not decode (1 of its 8). Its D comes from 7 frames.
- **`eala_segment` has no clicked corner file.** There is no `data/eala_segment_pts.json`;
  the only candidate is `data/eala_pts_auto.json`, which `eval/run_refs.py` excludes by name
  as a detector output. Its `Dc` was computed from that file. This does not change its
  verdict: the corner-independent `Df` is 4.11 px, still SAFE. **Someone should establish
  what corner set the `eala_segment` audit sheet was actually drawn from.**
- **`HoHxFSX_gLk_s1` / `_s3` / `_s2`** each have frames with no shared background at all
  (3, 3, 2 of 8). For those frames "displacement" is undefined; they are counted as
  disagreement, not as a number.

## WHAT THIS DOES **NOT** ESTABLISH

- It does not say any placement is correct. AT RISK means *unresolvable from the sheet*.
- **Nothing in this repo records which frame a calibration was placed on.**
  `tools/render_corner_audit.py`'s own docstring says so. So the *actual* placement frame
  for each clip is unknown; I measured the full spread the choice could span, which is the
  bound, not the realised error.
- The `_pts.json` files were read for coordinates only. Nothing was edited (rule 9).

## THE CHEAP WAY TO RESOLVE IT — 9 clips, not 28

Re-render only the 9 clips that are AT RISK or WATCH in the wrong-marked group plus the 2
false-exoneration risks, using the existing switch:

```
./backend/.venv/Scripts/python.exe tools/render_corner_audit.py --pts data/<tag>_pts.json --eval-frames
```

That produces the 8 frames the scoring actually uses, per clip. A verdict that survives all
eight is settled; one that flips between them was never a corner problem.
`L73ep7JHiJ4` and `demo30` need no re-review on this question — their verdicts stand.

## RAW DATA

`scratchpad/measure_motion.py` and `scratchpad/motion.json` (per-frame rows: position,
match count, inlier count, corner displacement, frame displacement, scale, rotation) plus
the rendered comparison sheets `pair_*.png`. Written outside the repo because measurement
scaffolding is not product code; regenerate from the script if needed.
