# QA verification — the net-anchor calibration check

**VERDICT (top line): the RENDER/GEOMETRY half of the net-anchor check is safe to
rely on (constants, mirror, `court.LINES`, the rows it prints); the TWO
PRE-REGISTERED BARS are not, and are correctly reported as failed — my own
independent measurement makes the case for that stronger, not weaker, than
backend-dev's own write-up. Neither `am_hard_utr` nor `sAjkpeRq4P4` is settled.
sAjkpeRq4P4 in particular should NOT be treated as the safer of the two — an
independent pixel measurement below finds a larger unexplained offset on it than
on `am_hard_utr`, despite the automated bar reading it as clean.**

Verifies `docs/evidence/net-anchor-calibration-check.md` and
`tools/net_anchor_check.py` (backend-dev, 2026-09-05), against the four items
asked for. Python: `backend/.venv/Scripts/python.exe`.

---

## 1. The claimed bar failure and its inversion — CONFIRMED

Independently re-ran `tools/render_corner_audit.py --net-anchors` myself (not
read off the doc) on both `data/yt_match40_pts.json` (current) and
`data/yt_match40_pts.json.bak-2026-09-05` (the known-wrong predecessor):

| file | my re-run | doc's table |
| --- | --- | --- |
| current (CORRECT) | `band_ratio 0.78, dy +49.0, FLAG` | 0.78 / +49 / FLAG |
| `.bak` (WRONG) | `band_ratio 7.84, dy -15.0, ok` | 7.84 / -15 / ok |

Exact match, both numbers, both directions. The inversion is real: the bar
flags the calibration now known correct and passes the one known wrong.

Also independently re-ran the full sweep (`render_corner_audit.py --net-anchors`,
no `--pts` filter, all 29 `*_pts.json`, frame 0) and parsed the resulting
`net_index.json` myself:

* **27 rendered of 29** — matches (`court`, `yt_court` have no `.mp4`, same as
  the doc).
* **14 of 27 flagged** — list reproduced exactly: `A7vXlWIlyrI, am_hard_utr,
  bump_ntrp30, bump_ntrp30b, CYqapSq5llo, e8T34KoJzOw_s2, flexi_franz_p01,
  HoHxFSX_gLk_s2, HoHxFSX_gLk_s3, L73ep7JHiJ4, mpc_mixed_p08, UHf0LeMU2pg,
  uR5q2cSM6AY, yt_match40`.
* **4 of those are stamped `PASS`** — reproduced exactly:
  `flexi_franz_p01, L73ep7JHiJ4, UHf0LeMU2pg, uR5q2cSM6AY`.

**Is "FAIL" the right word?** Yes, for what it is being used to mean here —
*disqualified as a gate*. The doc is careful not to overclaim a general
inversion from n=1, and I agree that's the right caution: one settled pair
cannot prove the bar is backwards everywhere. But "FAIL" as "cannot be trusted
to gate anything" is earned twice over: once by the inversion on the only
truth-bearing pair, and — see §3 below — a second time by my own finding that
the bar also produces a false **negative** (waves through a clip with a real,
independently-measured ~30 px net-position discrepancy). I would not soften
this to "borderline" or "inconclusive"; "FAIL, not moved" is accurate.

Likely mechanism as stated in the doc (control strip picking up net shadow /
service-area clutter) is plausible and consistent with what I saw rendering
`am_hard_utr` (background fence + trees give the `dy` search a same-magnitude
"better" ratio at dy=-136, clearly not the net — see §3).

---

## 2. `horizon_row` independence — CONFIRMED, with one precision nuance

Traced the actual call chain rather than taking the claim at face value:

* `net_anchor_check.horizon_row(H, img_wh)` takes **only `H`** — no `hfov`
  parameter at all — and computes the image row of the ground plane's vanishing
  line (`l = H^-T [0,0,1]^T`). `H` itself is the exact 4-point DLT homography
  from `compute_homography()`, i.e. a function of the four clicked corners and
  nothing else.
* `calibration.camera_height_m(H, img_wh, hfov_deg)` needs `H` **and** an
  assumed/fitted `hfov`. That `hfov` (via `courtfit.cam_fit_quad`) is seeded
  directly from `calibration.focal_from_homography(Hq, ...)` (confirmed by
  grep: `courtfit.py:589` `f0 = calibration.focal_from_homography(Hq, (w, h))`)
  — a self-calibration that reads the same homography's vanishing-point
  structure that `horizon_row` reads directly.

So both quantities are provably downstream of the same four clicks and the
same vanishing-line geometry; no new pixel evidence enters `horizon_row`. The
reasoning holds: it should not be graded as independent evidence, and no bar
on it would be legitimate.

**Nuance:** "the existing camera-height screen re-expressed" slightly
overstates the mechanical relationship — `horizon_row` needs no `hfov` at all
(it's a strictly simpler function of `H` alone), while `camera_height_m` is a
PnP solve that additionally consumes the fitted `hfov`. They are not the same
formula in different clothing; they are two different functions of the same
underlying (and non-independent) source data. The conclusion the doc draws
from this — "not independent evidence, no bar proposed" — is correct either
way, but "re-expressed" is a slightly loose description of why.

---

## 3. The two unsettled clips — CORRECTED (both must stay open; do not accept the frame-read at face value)

I did not stop at eyeballing the rendered PNGs — the brief specifically warns
that reading a rendered frame by eye has burned the lead twice today, and my
own first pass at eyeballing the annotated renders was **also unreliable** (I
initially misjudged crop coordinates on `sAjkpeRq4P4` and nearly reported the
wrong region as "no net visible"). To get an answer that doesn't depend on my
eye, I decoded frame 0 fresh from each source `.mp4` (`data/incoming/Clay/
sAjkpeRq4P4.mp4`, `data/incoming/Hardcourt/am_hard_utr.mp4`) **with no overlay
drawn on it**, and measured the row of the real white tape band directly by
mean-brightness profile across disjoint column ranges (so a single-column
fluke can't explain it).

### `am_hard_utr`
Profiled columns 450-900 (single band) plus checked with the annotated crop.
Real tape band: sharp brightness rise starting row 518, peak ~525
(brightness ~100 against a ~46-48 dark background) → tape centre ≈ **row 522**.
Modelled `net_tape_row` = 530.5. **Offset ≈ 8-9 px**, model too low (deeper into
the court) — same direction, similar magnitude to the lead's own eyeball read
("perhaps 10-15 px high"). Ground/base transition in the clean frame (rows
581→589, dark→bright) centres at **row ≈ 585**, against modelled
`net_ground_row` 585.0 — **essentially an exact match, no offset.**
→ Small (~9 px, ~15% of the 58.6 px modelled net height), one-sided (tape only,
not ground) discrepancy. Consistent with "plausibly correct, not settled."

### `sAjkpeRq4P4`
Profiled **three disjoint column ranges** on the clean frame (x=400-900,
500-800, and separately x=200-400 / x=900-1150 near each post) — all four
agree: a sharp, low-variance (smooth) bright band peaks at **row 406-409**
(brightness up to 233-243 against a ~180-190 background), continuous across
essentially the full net width, i.e. the real tape. Modelled `net_tape_row` =
437.5. **Offset ≈ 29-31 px, model too low.** The ground/base transition (a
darkening from ~188 down to ~167-173) centres at **row ≈ 465-468** against
modelled `net_ground_row` 490.1 — **offset ≈ 22-25 px, same direction.**

This is a **larger, two-sided (tape AND ground), consistently-directed
discrepancy — roughly half the clip's own modelled net height (52.6 px) —
on the clip the automated bar rated `ok` (`band_ratio 5.64, dy_best -2`, "not
flagged at all") and that a first eyeball pass (mine included) read as a good
match.** This is the opposite of reassuring: the automated screen and a quick
visual pass both missed something my independent measurement did not.

I cannot conclude from a frame-0 brightness profile alone that the calibration
itself is wrong — a ~30 px net-position gap is consistent with either a
genuine corner-fit error or a camera-pose (hfov) error specific to projecting
height off the ground plane, and the corner fit passed at 2.8 px residual
(which, by this whole check's own premise, tells you nothing about the net).
But it flatly contradicts treating `sAjkpeRq4P4` as more settled than
`am_hard_utr`. **Neither clip is settled. If anything, `sAjkpeRq4P4` deserves
more scrutiny, not less, precisely because the tool said "ok."**

**Do not read this as me overriding the lead's read with my own** — I am
reporting a measurement (brightness-profile peak row, cross-checked on 3+
disjoint column ranges, on the undecorated source frame), not a rendered-image
eyeball judgement. The measurement disagrees with "not flagged" and is a
reason for the founder's eye to look harder at `sAjkpeRq4P4`, not to skip it.

---

## 4. The geometry constants and `court.LINES` — CONFIRMED

* `NET_POST_OFFSET = 0.914` m (3 ft) — regulation: net posts stand 0.914 m
  outside the doubles sideline. Correct.
* `NET_HEIGHT_POST = 1.07` m, `NET_HEIGHT_CENTER = 0.914` m — regulation net
  heights at the posts and centre strap. Correct.
* `X_LEFT_STICK = X_LEFT_SINGLES - NET_POST_OFFSET = 0.456`,
  `X_RIGHT_STICK = X_RIGHT_SINGLES + NET_POST_OFFSET = 10.514` — singles sticks
  sit the same 0.914 m outside the **singles** sideline (1.37 m alley width);
  arithmetic checks out (`1.37 - 0.914 = 0.456`; `9.60 + 0.914 = 10.514`).
  Correct, and correctly noted in the code as standing *inside* the doubles
  alley rather than outside the court.
* **JS mirror** (`frontend/src/lib/court.js`): `NET_POST_OFFSET`,
  `NET_HEIGHT_POST`, `NET_HEIGHT_CENTER`, `X_LEFT_STICK`, `X_RIGHT_STICK` all
  byte-identical to the Python values (checked by grep on both files).
* Ran the test suite myself:
  `backend/.venv/Scripts/python.exe -m pytest tests/test_net_anchor_geometry.py
  tests/test_js_mirror_parity.py -q` → **13 passed**, including the parity
  test that would catch a constants mismatch.
* **`court.LINES` unchanged** — confirmed by reading `git diff HEAD~3 --
  backend/swingvision/court.py` directly: the entire diff is additions only (no
  `-` lines) inserted before and after the existing code; the new block is
  explicitly commented `# Deliberately NOT added to LINES: LINES is what
  overlay.py draws and what validate_new_clip.py counts horizon crossings
  over`. `overlay.py`'s and `validate_new_clip.py`'s behaviour on `LINES` is
  therefore untouched by this change.

---

## What was NOT re-verified this run

* The other 25 clips' rendered net anchors were only checked at the aggregate
  flag-count level (§1), not individually eyeballed or brightness-profiled —
  only `am_hard_utr` and `sAjkpeRq4P4` got the frame-0 clean-decode treatment,
  since those are the two the brief asked about.
* Did not check whether the flag list or the two clips' offsets would change
  on a mid-rally frame instead of frame 0 (the doc itself flags this as open).
* Did not attempt to build a working tape/post pixel detector — my brightness
  profiling here is a one-off verification measurement, not a proposed
  replacement instrument, and should not be read as one.

## For the lead — a founder-facing note, not filed by me

`docs/DECISIONS_PENDING.md` already carries backend-dev's "two calibrations
need a human eye" entry for `am_hard_utr` and `sAjkpeRq4P4`. QA does not edit
that file (out of QA's write-allowlist), but the entry should be updated to
say: **`sAjkpeRq4P4` is not the cleaner-looking case its `ok`/not-flagged
status suggests** — an independent brightness-profile measurement on the raw
decoded frame (not the automated bar, not a rendered-PNG eyeball) finds a
~29-31 px tape offset and ~22-25 px ground offset there, larger than
`am_hard_utr`'s ~9 px tape / ~0 px ground offset. Both still need the
founder's eye; `sAjkpeRq4P4` should not be assumed to need it less.
