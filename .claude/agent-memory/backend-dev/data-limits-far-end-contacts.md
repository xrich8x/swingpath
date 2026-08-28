---
name: data-limits-far-end-contacts
description: What this project's gold data cannot support — thin far-end contact populations, contaminated criteria, and a corrupted shot list
metadata:
  type: project
---

- **Far-end contact populations are THIN.** The homography-free criterion (far-end hit =
  local MINIMUM of the ball's raw image y-track) yields 25 usable contacts on
  `yt_match40` and 12 on `am_hard_utr` out of 196 and 120 shots. n=12 is underpowered;
  say so and stop rather than quoting a rate.
- **On a LOW camera the trajectory APEX is also a local image-y minimum**, so the
  criterion admits mid-flight points. It refuses rather than guesses (most shots come
  back `undecided`), but contamination survives and dilutes every arm equally.
- **`am_hard_utr`'s contacts are partly anchored on balls lying on the court** — the
  static-fixture false lock, visible on the contact sheet.
- **`yt_match40`'s shot list is downstream of the bad calibration** (`striker = "A" if
  track[h][2] < NET_Y`, and hit detection runs through `ball_player_gap`), so its hit
  times and player attribution are partly corrupted until it is re-calibrated. See
  [[calibration-trap-check-corners-first]].

**How to apply:** before designing an A/B on far-court behaviour, check whether the
population can carry it. Reporting "underpowered, n too small" is the correct output.

Related: [[ane-cost-and-far-player-crop]].
