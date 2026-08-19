# Far-player tracking: do `--pose-quality accurate` or `--far-player-rescue` help?

**Date:** 2026-08-17 · **Status:** RUN. Both gates FAIL — and the reason is not the levers ·
**Tool:** `run.py analyze` + `stats.player_track_coverage`

## Why

Session N part 2 gated `distance_run_m` on track coverage, because the far player
is located on **0.0%** of frames on yt_rally2 (1.0% am_hard_utr, 9.6% demo30,
11.0% yt_match40). That fixed the SYMPTOM — the dashboard no longer reports a
fabricated 0.0 m — and left the CAUSE open. Two levers are already built and
have never been measured on this axis:

- `--pose-quality accurate` — yolo11x@1920 instead of the default yolo11m@1280.
  CLAUDE.md records that the `fast` default is what gives the far player up.
- `--far-player-rescue` — a native-resolution crop of the far half, run only on
  frames where the full-frame pass found nobody past the net.

## Pre-registered gate (written BEFORE any run)

**PRIMARY (product):** far-player coverage must reach **>= 50%** on a clip where
it is currently near zero. That is not an arbitrary bar — it is
`pipeline.MIN_TRACK_COVERAGE`, the threshold that decides whether
`distance_run_m` is reportable at all. Below it the lever changes nothing a user
can see, however much it moves coverage.

**SECONDARY (knowledge, reported either way):** the coverage delta, the cost in
wall-clock, and whether near-player coverage or shot count regress.

**Clip:** `yt_rally2` — 1108 processed frames, calibrated, and the cleanest
possible signal because its far-player coverage is **0.0%**, so any non-zero
result is attributable. Not `am_hard_utr`: at ~2.4 s/frame `accurate` would take
about 9.7 hours there.

**Honest prior:** this may be unfixable rather than untried. The far player on a
3.2 m mount may simply be too few pixels to resolve, in which case the correct
outcome is a documented physical limit and the coverage gate stays as the answer.
A negative here is a result.

## Results — both gates FAIL, and the second one fails for an interesting reason

| Arm | far coverage | near coverage | distance B | verdict |
|---|---|---|---|---|
| baseline (`fast`) | **0.0%** | 90.8% | None | — |
| `--pose-quality accurate` | **0.0%** | 91.6% | None | **GATE FAILS** — no change whatsoever |
| `--far-player-rescue` | **0.0%** | 90.8% | None | **GATE FAILS** as shipped |

`accurate` is a clean negative: yolo11x@1920 finds the far player on exactly as
many frames as yolo11m@1280, which is none. Near coverage moves +0.8 pts and
costs ~2x pose time. **Do not reach for `--pose-quality accurate` to fix the far
player.**

## But `--far-player-rescue` is NOT a negative — it works and is then cancelled

The rescue arm reports 0.0% in the product and that number is an artefact. Taken
apart stage by stage:

| Stage | far-player frames | |
|---|---|---|
| rescue tile fires | 144 pose frames | the crop runs |
| far person ON COURT (`count_on_court`) | 89 of 370 pose frames | it finds someone |
| `far_court` written to the perception cache | **412 / 1108 = 37.2%** | it is tracked |
| after `_reject_static_player` | **0 / 1108 = 0.0%** | it is deleted |

**The lever reaches 37.2% coverage and a downstream guard throws all of it away.**
The near player on the same clip passes that guard untouched (90.8% -> 90.8%).

## Why the guard eats the far player — depth-blind pixel radii

`_reject_static_player` flags a fixture as "many samples piled inside a small
image neighbourhood", with the neighbourhood fixed at **20 px** (and an 8 px
recurrence test). Those constants were written against a near player. A far
player on this 3.2 m mount is a fraction of the near player's pixel size, so
metres of real running map to a handful of image pixels and sit *inside* the
fixture radius. It drops **304 of 412** frames as static, then bins the 108
remnants under its own <15% rule.

This is the **same family as the resolution-scaling trap** already in TRAPS.md,
on the DEPTH axis rather than the resolution axis: a constant that is correct for
one part of the frame is wrong everywhere else in it.

## The depth-invariant variant, measured

`_reject_static_player(..., body_relative=True)` expresses the radii as fractions
of that track's **own median body height** (0.18 / 0.072 body heights, matched to
20 px / 8 px on a ~110 px near-player body). That is depth-invariant, and it keeps
the fixture test honest: a poster does not move relative to its own size either.

| Variant | far coverage after the guard |
|---|---|
| shipped (fixed 20 px / 8 px) | **0.0%** (drops 304/412, then bins the rest) |
| `body_relative=True` | **28.2%** (drops 99/412, track survives) |

**A 28-point swing, and it is the difference between "we never saw player B" and
"we saw player B on 28% of frames".**

## What this does and does not license

**PRIMARY GATE STILL FAILS.** 28.2% is under the 50% a path integral needs, so
`distance_run_m` for player B stays `None` either way. Nothing user-visible about
the movement stat changes.

What does change is the *honesty* of the coverage number and the skeleton
overlay: 0.0% is a false statement about how much we saw.

**NOT SHIPPED, deliberately.** `body_relative` is off by default:
- one clip, one measurement;
- the fixture population the guard exists to catch (poster, bag, chair mistaken
  for a player) is **not represented in any gold clip**, so the thing that would
  regress cannot currently be measured;
- and this project's record is four-for-four on perception gains that did not
  reach the product.

To ship it, pre-register: far coverage up on >=2 of 3 calibrated clips, near
coverage flat within 1 pt, and a fixture clip that still gets rejected.

## Cost

`accurate` 73 s vs `fast` 39 s perception on 1108 frames (GPU, `pose_every=3`) —
note this is far cheaper than CLAUDE.md's "~2.4 s/frame", which is a
full-resolution per-frame figure and does not describe this path. Rescue: 63 s.
