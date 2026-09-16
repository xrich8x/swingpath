# P2 — Occlusion census: how often is the ball hidden at the bounce, on near-line bounces?

> Run by **qa**, 2026-09-16 (resumed after a 2026-09-15 usage-limit kill).
> Brief and bar: `.claude/journals/lead.md`, P2. This file was written and committed
> **before** any candidate was built. The definitions below are frozen from that commit on.

**STATUS: SHEET BUILT, NOT LABELLED. No number exists yet. See §RESULT.**
**Three pre-label amendments (A1-A3, §4.2) were made after the pre-registration commit and before
any label existed. Each one was triggered by a property of the instrument, never by an answer.**

**THIS IS NOT A v1 FIGURE, AND MUST NEVER BE QUOTED AS ONE.** No clip here meets the v1 capture
floor (P3, `capture-floor-census.md`). Both recordings are low standing mounts (1.64-1.74 m), and at
a low mount a player hides far more court than from a fence mount. The occlusion rate measured here
is therefore an **UPPER BOUND** for v1's target mount. Note the other direction too: occlusion is only
ONE source of refusal (§3's 10 cm 1σ abstention adds more), so for the refusal rate on THESE clips it
is a **FLOOR**.

---

## 1. The question and the pre-registered bar (copied from the brief, not moved)

**How often is the ball hidden at the bounce frame, on near-line bounces, in footage we already own?**
With SPEC §6 tossed, every occluded bounce is a refusal.

> **If more than 20% of near-line bounces are occluded, SPEC's <=5% refusal target is formally
> WITHDRAWN in writing, and §6's return becomes a live scope question for the founder — not a
> quiet restore.**

## 2. Clips — fixed before the build

There are **two recordings, not three.** The three cached clips resolve to two source videos:

| Clip | Fitted mount | Video | Audio | Role in this census |
|---|---|---|---|---|
| `am_hard_utr` | **1.74 m** (measurable to court-y 7.5 m of 23.77) | 1920x1080, 59.94 fps, 483.8 s | **yes** | **PRIMARY.** The only clip where the candidate source can be made occlusion-independent (audio). Carries the verdict. |
| `yt_match40` | **1.64 m** (calibration KNOWN BAD, trap T23 — fitted camera 11.3 m on another solve) | 1280x720, **29 fps**, 354 s | no | **SECONDARY, visibility only.** Candidate source is detector-derived, so its rate is biased LOW (§5). No calibration is used for it. |
| `demo30` | **1.38 m** | 1280x720, 29 fps, 30 s | no | **DROPPED as a separate clip — it IS `yt_match40`.** Frames 0-869 of `demo30.mp4` are frames 2552-3421 of `yt_match40.mp4` (48x27 grey thumbnails, mean abs diff 0.09-0.12 at the matched offset vs a median 7.6-10.5 to other frames, constant offset at 5 probe frames). It is covered by `yt_match40`'s sampling and would otherwise double-count. |

Two side findings from the inventory, recorded, not fixed:
- The same static camera has been fitted at **1.38 m** (`data/demo30_pts.json`) and **1.64 m**
  (`data/yt_match40_pts.json`), with near-baseline rows ~500-530 vs ~454 px. At least one of the two
  calibrations is badly wrong. That is another reason no calibration is used for `yt_match40` here.
- `data/output/demo30.perception.json` has **1108** per-frame entries for an **870**-frame video, and
  `data/output/demo30.json` names `yt_rally2.mp4` as its video (36.9 s x 30 fps = 1107). **The cache
  labelled `demo30` was not computed from `demo30.mp4`.** Any number that used it as demo30's
  perception is suspect.

Neither video meets v1's 60 fps floor except `am_hard_utr`, and neither meets the 1080p+60 fps pair
except `am_hard_utr`. At 29 fps v1 refuses bounce detection outright, so `yt_match40`'s number is a
property of the footage only, not of v1 behaviour.

## 3. Definitions — PRE-REGISTERED

### 3.1 Bounce
A ground contact of the match ball on or beside the court. The founder decides whether a bounce occurs
in the looped window (question Q1), using motion and, on `am_hard_utr`, the sound. A hidden bounce is
still a bounce if the trajectory (falling into the occluder, rising out of it) or the sound makes it
evident. "Cannot tell" is a legitimate answer and is NOT counted as a bounce.

### 3.2 Near-line — 0.5 m, the repo's existing "contested" population
A bounce is **near-line** if its contact point is **within 0.5 m of any painted line** of the doubles
court. The 0.5 m band is the one this repo already uses for "where a call is a call"
(`backend/swingvision/calibration.py:319`, `tools/height_curve.py:431`, `run.py check`). SPEC §3
says "contested (near-line)" but gives **no number** — flagged in §7.

Lines, from `backend/swingvision/court.py` (metres, x across, y along):
- sidelines x = `X_LEFT_DOUBLES` 0.0, `X_LEFT_SINGLES` 1.37, `X_RIGHT_SINGLES` 9.60,
  `X_RIGHT_DOUBLES` 10.97 (doubles alley is in scope for v1, so both pairs count);
- centre service line x = `X_CENTER` 5.485, **only between** `Y_NEAR_SERVICE` 5.485 and
  `Y_FAR_SERVICE` 18.285;
- baselines y = `Y_NEAR_BASELINE` 0.0 and `Y_FAR_BASELINE` 23.77;
- service lines y = 5.485 and 18.285 (between the singles sidelines).

**Who decides it: the founder's eye (Q3), not a calibration.** `yt_match40`'s calibration is known bad,
and `am_hard_utr`'s is measurement only to court-y 7.5 m, so a geometric flag would be wrong or
recall-only on most of the court. As a visual aid the sheet states: *0.5 m is about a third of the
doubles-alley width (1.37 m), or a little under a racquet's length (0.69 m).* The founder answers
YES / NO / CANNOT TELL. On a hidden bounce the founder may still answer from where the ball entered
and left the occluder; otherwise CANNOT TELL.

### 3.3 Occluded — with the cause kept separate
At the contact frame **(±1 frame, SPEC's own timing tolerance)**, can the founder see the ball well
enough to say where it touched the ground? If yes: **VISIBLE**. If not, the cause (Q2):

| Code | Cause | Why it is separate (different v2 answer) |
|---|---|---|
| `PLAYER` | hidden by a player's body or racquet | trajectory bridging (§6) / a second camera |
| `NET` | hidden by the net, net tape or post | **mount height** — at these mounts the net tape covers the far baseline (STATE l.197); a fence mount removes most of it |
| `FRAME` | out of frame / cropped | framing guidance at setup |
| `BLUR` | present but blurred or too small to recognise | frame rate, shutter, resolution |
| `OTHER` | anything else (fence, umpire, ball kid, graphic) — the founder writes what | case by case |
| `?` | a bounce happened but visibility cannot be judged | excluded from rates, counted |

A partially visible ball whose contact point can still be placed counts as VISIBLE.

### 3.4 Q4 — which half
NEAR half (the camera's side of the net) / FAR half / cannot tell. Cheap to answer. Lets the result be
split near/far, which matters because the far half is where the net-tape and near-player occlusion
live, and it is where `am_hard_utr`'s audio is quietest (§5).

## 4. Candidate sources — the anti-bias route, stated BEFORE the build

**The trap:** a candidate set built from the ball detector never contains the bounces the detector
could not see, so it under-states occlusion. The route:

- **A — AUDIO (`am_hard_utr` only).** The shipped impact detector `detect_impacts` with its shipped
  defaults (band 1.5-7 kHz, k_mad 6, min_contrast 4, min_sep 0.22 s), **invoked from git at
  `7570a2a^`** (the last commit where `backend/swingvision/audio.py` shipped, before the 2026-09-11 cut),
  not re-implemented and not tuned. A bounce makes a sound whether or not it is seen; rule 12 permits
  it (it is the game). Every onset is a candidate, whether it is a hit, a bounce or noise; Q1 sorts them.
  **Propagation lag:** sound arrives ~29 ms per 10 m late (`docs/CAPTURE_PROTOCOL.md`), up to ~5
  frames at 60 fps for a far-baseline bounce. The window is placed to absorb it: centre = onset −
  0.04 s, window [centre − 0.30 s, centre + 0.25 s].
- **V — VISION (both clips).** (a) The pipeline's own bounce times (`shots[].bounce_t_s` in
  `data/output/<clip>.json`, cached shipped output, invoked not re-derived). (b) **Bracketed
  reversals** in the cached per-frame ball track: image-y moving DOWN (median dy over the previous 3
  valid points > +1 px/frame x H/720) then UP (median over the next 3 < −that), with up to 0.5 s of
  missing detections allowed between them. The centre is the lowest point, or the middle of the gap if
  the gap exceeds 2 frames. This is the part of V that can reach a bounce the detector missed at the
  contact frame itself. Tracks: `am_hard_utr.perception.json`; for `yt_match40`, the **union of all
  four** cached tracks (`_v1`, `_v2`, `_fusion`, `_tracknet`), because none of them is the shipped
  BallNet v21 and the union maximises V's reach. Extra false candidates only cost founder time.
- **Merge rule:** a V candidate at t_v is the same event as an A onset in [t_v − 0.05, t_v + 0.15] s.
  V candidates within 0.15 s of each other are merged. The founder is **blind to source**: every item
  uses the same window shape and the page never shows where an item came from. The source key is kept
  in a separate file.

### 4.1 How the residual bias is estimated (pre-registered)
On `am_hard_utr` each labelled bounce falls in one cell: A∩V, A-only, V-only. Scaling each cell's
labelled bounce fraction by its pool size gives estimated bounce counts. Then:
1. **V's blind spot, measured directly:** among A-found bounces, P(V found it | occluded) vs
   P(V found it | visible). This is the size of the trap, and it is the correction that applies to
   `yt_match40`'s V-only number.
2. **A's blind spot:** among V-found bounces, P(A found it | occluded) vs P(A found it | visible),
   and P(A | near half) vs P(A | far half). Audio should not care about occlusion; if it cares about
   range, that correlates with far-half occlusion and biases the census LOW too.
3. **Missed by both (Lincoln-Petersen):** N̂ = (n_A · n_V) / n_AV; the unfindable fraction is
   1 − (n_A ∪ V) / N̂. A and V are positively correlated (both are weaker on the far half), which
   makes Lincoln-Petersen **under**-estimate N̂, so this fraction is a **lower bound on the residual
   bias**. Stated as such.

### 4.2 Pre-label amendments (the registered text above is left as it was; these supersede it)

**A1 — the A/V merge rule was wrong for this audio.** I histogrammed audio onsets against the
pipeline's own bounce times (±1 s, 0.05 s bins). The audio excess over a random-time null sits at
**+0.10 to +0.20 s**, outside the registered [−0.05, +0.15] window, so that rule split one event into
two pool items. A split event gets sampled twice. The events split this way are the ones BOTH sources
saw, which means the visible ones, so the headline would have been biased LOW.

Replacement:
- Every A and V event goes into one greedy, **start-anchored** clustering (span ≤ 0.35 s, no chaining).
- Audio times are first moved to onset − **0.12 s**, the measured peak (it includes propagation).
- An item's centre is its median V time, or its median A time if it has no V event.
- **Each item gets a TARGET ZONE**: the Voronoi cell between neighbouring item centres, clipped to
  ±0.175 s. The founder judges only a bounce whose contact falls inside the zone, which the viewer
  lights green. Zones never overlap, so no bounce can be counted twice.

**A2 — cluster membership cannot say which source found a bounce, so §4.1 is replaced.** I built a
null by shifting the audio circularly against the vision events (5 shifts: −37.3, −19.1, +11.7,
+23.9, +41.3 s) and re-clustering:

| | By chance (null) | Observed |
|---|---|---|
| An A event lands in a V-bearing item | **0.758** | **0.780** |
| A V event lands in an A-bearing item | **0.484** | **0.496** |

At 1.68 audio events per second, cluster membership is essentially chance. The A∩V / A-only / V-only
cells and the Lincoln-Petersen estimate in §4.1 therefore **cannot be computed meaningfully**.

**Replacement — audit what the candidate source REJECTED.** Each batch blind-mixes **negative-space
items**: windows drawn uniformly (seeded) from video time that **no** target zone covers. Each zone is
±0.175 s clipped to its uncovered stretch; a draw shorter than 0.05 s, or one overlapping another
negative, is redrawn. The founder labels these exactly like any other item. Then, per clip:
- missed bounces M̂ = (bounces found in negative items ÷ negative-zone seconds labelled) × uncovered
  seconds;
- found bounces F̂ = (bounces per labelled pool item) × pool size;
- **residual bias = M̂ / (M̂ + F̂)**, the fraction of bounces the candidate source could not have
  offered;
- **the occlusion rate among missed bounces against found ones**, which measures the trap directly.

This needs no independence assumption. It also works for `yt_match40`, whose vision-only source is
the one under suspicion.

**The verdict (§6) now uses the population estimate.**
- Pool and negative bounces are weighted by inverse sampling rate: pool = pool size ÷ pool items
  labelled; negative = uncovered seconds ÷ negative seconds labelled.
- The unweighted pool-only H is reported beside it.
- The weights are unequal, so the interval is a seeded (20260916), stratified bootstrap of 2000
  resamples instead of Wilson.
- The H_low / H_high bound rules are unchanged.

**A3 — in-play bounces only.** Rendering items P2-001 and P2-003 showed a server bouncing the ball
before serving, and the audio source picks that up. Q1 now says **only in-play bounces count**: from a
serve or a shot until the point ends. The founder answers "no" for a pre-serve bounce, a ball being
fed, knocked back or collected, and a ball from another court.

**A viewer change, not a definition change: burned-in overlays are masked (rule 12).** `yt_match40`
carries SwingVision's HUD: a **mini-court with its own bounce dots**, a shot-type/speed panel and a
scoreboard. `am_hard_utr` has a scoreboard. A bounce dot or a score change would leak somebody else's
call into the founder's label. Masked boxes, in source pixels:
- `am_hard_utr`: [0,0,600,185]
- `yt_match40`: [0,0,310,170] and [1075,0,1280,335]

No mask covers the court surface.

## 5. Sampling — seeded, never hand-picked
- Pool per clip = the merged candidate list. **Seeded permutation, seed 20260916**, per clip.
  Items are dealt 3 `am_hard_utr` : 1 `yt_match40` down the two permutations, so **any prefix of
  the sheet is a random sample** and the founder can stop at a batch boundary without biasing it.
- **Batch 1 = 160 items (120 `am_hard_utr` + 40 `yt_match40`)**, sized to ~45 min at ~15-17 s per item.
  Batch 2 (optional, the next 160) exists on the same page for extending the sample without a rebuild.
- **Superseded by A2:** each batch is **180 items**:

  | Stratum | Items per batch |
  |---|---|
  | `am_hard_utr` pool | 110 |
  | `am_hard_utr` negative | 20 |
  | `yt_match40` pool | 35 |
  | `yt_match40` negative | 15 |

  Items are shuffled WITHIN the batch (seed 20260916), so a **batch boundary** is the clean stopping
  point. A mid-batch stop is still unbiased within each stratum, but leaves the strata unequally
  filled. A batch takes ~45 min at 15 s/item, ~60 min at 20 s/item.
- `demo30` contributes no items of its own (§2).

## 6. How the bar will be evaluated (pre-registered)
Computed on **`am_hard_utr` only** (the only candidate source not biased by the detector), among
bounces (Q1 = YES) with a visibility answer (Q2 ≠ `?`):
- **point:** H = occluded ∧ near-YES / near-YES
- **low:** H_low treats near-CANNOT-TELL occluded bounces as not near-line and near-CANNOT-TELL visible
  bounces as near-line
- **high:** H_high treats every near-CANNOT-TELL occluded bounce as near-line
- Wilson 95% interval on H.

**Verdict:** FIRES if H_low > 20%. DOES NOT FIRE if H_high ≤ 20%. Otherwise **INDETERMINATE**. The
bar says "more than 20%", so the verdict is on the point bound, and the Wilson interval is reported
next to it; **if the interval straddles 20% the verdict is labelled UNDERPOWERED**, with the n that
would resolve it. Reported next to it, and **not** gating: the all-bounce occlusion rate, the cause
breakdown, the near/far split, `yt_match40`'s V-only rate with the §4.1(1) correction, and the §4.1
bias figures.

**Power, priced before the labels exist:** if ~50% of candidates are bounces and ~35% of bounces are
near-line, batch 1's 120 `am_hard_utr` items give ~21 near-line bounces, a Wilson half-width of about
±17 pp at H = 20%. Separating 20% from 35%, or from 10%, needs **~40 near-line bounces, about 230
`am_hard_utr` items** — batch 1 plus most of batch 2, roughly 80-90 min of founder time in total.
**Batch 1 alone will very likely read UNDERPOWERED unless H is far from 20%.** These are
assumptions, not measurements; the real bounce and near-line fractions come from the labels.

**After A2 and A3 the power is worse, not better.** Batch 1 now carries 110 `am_hard_utr` pool items,
not 120. Both `am_hard_utr` items I rendered while building were pre-serve bounces, so the in-play
yield per item may be well under 50%. At a 30% yield and 35% near-line:
- batch 1 gives ~12 near-line bounces, a half-width of about ±23 pp;
- both batches give ~23.

**Expect UNDERPOWERED from batch 1 alone. A verdict likely to resolve needs both batches, ~90-120
min.**

## 7. What makes the 20% bar hard to evaluate as written
1. **"Near-line" has no number in SPEC.** 0.5 m is adopted from the repo's existing contested band.
   pm's line-call margin work recommended a **0.20 m** band; a 0.20 m population would be smaller still
   and harder for an eye to judge on a low mount.
2. **Near-line is unobservable exactly when the ball is hidden.** Conditioning on "near-line" needs a
   landing position, and an occluded bounce is the one without one. Hence the H_low / H_high bounds and
   an INDETERMINATE outcome.
3. **A human cannot place a bounce to ±0.5 m in depth on a 1.6-1.7 m mount** (the reason P5 builds
   truth at capture). Q3 is therefore more reliable for sideline bounces than for baseline and
   service-line bounces, and the near-line population will lean toward sidelines.
4. **Power** (§6): the 45-minute budget and the 20% bar are not jointly sized.
5. **Pre-serve bounces take a large share of the audio source's items** (A3). They are excluded by
   definition, but labelling them still costs founder time, so 45 minutes buys fewer counted bounces.
6. **v1 would refuse every bounce on `yt_match40` anyway.** At 29 fps it is below the 60 fps floor,
   where v1 does not attempt bounce detection, so that clip's rate describes the footage, not v1's
   refusals.
7. **The bar pools causes.** A `NET` occlusion at a 1.7 m mount is a mount-height artefact that a
   fence mount largely removes; a `PLAYER` occlusion is the §6 question. The cause split is reported
   so the founder can see how much of H belongs to each.

## 8. Where the sheet lives, and how the founder runs it

**Open `docs/evidence/occlusion-census/sheet.html` in Chrome or Edge from inside the repo**
(double-click). The page plays the two source videos in place from `data/incoming/Hardcourt/`. That
folder is gitignored, so the page only works on a machine that has both files at those paths; this
machine does.

**What the founder sees:**
- One item at a time: a ~0.55 s window looping at 0.25x (0.1x, 0.5x and 1x also available). Sound
  is available on `am_hard_utr` only.
- **The picture border turns green while the playhead is inside the target zone.**
- Four questions per item, each with a "cannot tell" option. Q2-Q4 unlock only when Q1 = yes.

**Batch 1 is P2-001 to P2-180 (~45 min at 15 s/item). Batch 2, P2-181 to P2-360, is optional.**

**Keys:**

| Key | Action |
|---|---|
| `1` / `2` / `3` | Q1 |
| `v` `p` `t` `f` `b` `o` `x` | Q2 |
| `7` / `8` / `9` | Q3 |
| `4` / `5` / `6` | Q4 |
| Enter | save and next |
| `,` / `.` | step one frame back / forward |
| Space | play / pause |

Clicking the picture sets the zoom centre; the zoom buttons are 1x, 2x and 3x.

**Saving:**
- Answers autosave in the browser (localStorage).
- **"Download answers (CSV)"** writes the tally, including seconds spent per item as a pace check.
- "Resume from CSV" reloads a saved tally, e.g. in another browser.
- `tally_form.csv` is the same form as a plain spreadsheet, for use without a browser.

**`source_key.json` records which items are negatives and which source offered each item. The
founder must not open it before labelling.** The page never shows it.

**No network.** The page source contains no URL, and its Content-Security-Policy sets
`connect-src 'none'`. I logged network traffic during a headless Chrome page load: the only requests
were Chrome's own browser-process traffic (time sync, account check), none started by the page.

## 9. Build record

Everything below describes the candidate pool. **None of it is a label or an occlusion figure.**

| | `am_hard_utr` (1.74 m) | `yt_match40` (1.64 m) |
|---|---|---|
| Audio onsets (shipped `detect_impacts`, git `7570a2a^`, defaults) | **811** in 483.8 s (1.68/s) | none (no audio track) |
| Vision events after the 0.15 s pre-merge | 471 (120 pipeline bounces plus image-y reversals) | 549 (196 pipeline bounces plus reversals from 4 tracks) |
| Pool items after A1 clustering | **756** (A-only 334, V-only 93, both 329; membership ≈ chance, see A2) | **443** (all V) |
| Items with a bracketed (gap-spanning) reversal | 30 | 51 |
| Video time inside target zones | 258.8 s (**53.5%**) | 155.0 s (**43.8%**) |
| Video time the candidate source cannot offer (negative stratum) | 225.0 s | 199.1 s |
| Items on the sheet, both batches | 220 pool + 40 negative | 70 pool + 30 negative |

**Files**, all in `docs/evidence/occlusion-census/`:

| File | What it is |
|---|---|
| `sheet.html` | the viewer and form |
| `items.js` | the 360 blind items |
| `tally_form.csv` | the same form as a spreadsheet |
| `source_key.json` | **sealed:** which items are negatives and which source offered each one |
| `pool.json` | the full pools, the negatives and the chance-coincidence null |
| `build_sheet.py` | the builder |
| `_audio_from_git.py` | loads the cut `audio.py` from git without restoring it to the tree |
| `audio_am_hard_utr_raw.json` | the 811 onsets |

- **Reproducible.** `backend/.venv/Scripts/python.exe docs/evidence/occlusion-census/build_sheet.py`
  re-ran byte-identical: `items.js` sha1 `6d588d33`, `source_key.json` `886c9db8`, `pool.json`
  `7045ba70`, `tally_form.csv` `eb3750a8`.
- **Checked before hand-off.** In headless Chrome, items P2-001, P2-002, P2-003 and P2-005 loaded,
  decoded, looped, lit the zone and masked the HUD.
- **No code under `tools/`, `backend/` or any test was added or changed.** The builder sits beside its
  evidence file because qa does not write to `tools/`. Moving it to `tools/` would be a lead or
  backend-dev change.

## RESULT

**EMPTY — NO LABELS EXIST YET.** No occlusion rate, no verdict and no bias figure may be quoted from
this file until the founder's pass is done and §6 has been computed from it.

```
[ PLACEHOLDER — founder pass not done ]
am_hard_utr (1.74 m) : near-line bounces n = __ ; occluded __ ; H = __ [H_low __, H_high __] Wilson95 __
                       verdict: __  (FIRES / DOES NOT FIRE / INDETERMINATE / UNDERPOWERED)
cause split          : PLAYER __  NET __  FRAME __  BLUR __  OTHER __
all-bounce rate      : __
yt_match40 (1.64 m)  : V-only rate __ ; corrected by §4.1(1) __
bias (§4.1)          : P(V|occ) __ vs P(V|vis) __ ; P(A|occ) __ vs P(A|vis) __ ; LP unfindable >= __
```
