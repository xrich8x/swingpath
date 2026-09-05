# Ground-plane-blindness claim: turned into a measurement

> Tests the claim in `docs/evidence/independent-calibration-references.md` ("Every
> calibration check that has failed on this project reads only the ground plane...
> This is structural... invisible by construction"), pre-registered STATE row. QA,
> 2026-09-05. Read-only: no `data/*_pts*.json` file was written to; all corruptions
> are in-memory copies via `backend/.venv/Scripts/python.exe`.

## Verdict, upfront

**NARROWS.** The claim survives only in a form much narrower than stated, and its own
supporting anecdote does not survive at all.

1. **The anecdote is gone.** The exact numbers cited (`yt_match40`, residual 0.0 px,
   camera 1.64 m, coverage 0.944) belong to the calibration `verify-court-false-rejects.md`
   itself **withdrew as CORRECT the same hour it was written** — "The calibration was
   CORRECT; I mis-read the net." There is no confirmed instance in this repo of a
   near-half-compressed, actually-WRONG `yt_match40` scoring well on ground-plane stats.
   The one calibration that IS confirmed wrong (the `.bak` file, corners on asphalt/hedge,
   11.3 m) **was caught by the camera-height screen** — the same check the claim calls a
   "failed ground-plane check." On the one real data point this project has, the
   camera-height screen worked.
2. **"Invisible by construction" is too strong.** Built synthetically below: a
   depth-compression corruption is invisible to the *shipped* gates (`verify_court`,
   the camera-height screen) — but a ground-plane-only quantity that is **already computed
   by the same fit and simply not looked at** (the fitted horizontal FOV) moves sharply
   and would flag the same corruption at a small magnitude. Blind is a choice of what to
   read, not a law of the geometry.
3. **What does survive, sharply:** the blindness is specific to **anisotropic, depth-axis
   compression** (far corners moved toward near corners, width preserved) — not to
   "ground-plane" corruptions in general. An **isotropic** scale error (the textbook pure
   scale ambiguity) is visibly caught by `court_line_coverage`, a ground-plane statistic,
   confirming researcher's cross-feed prediction directly. The honest restatement is
   **"blind to depth-anisotropic compression," not "blind to ground-plane readings."**

## Method

Base clips: `yt_match40` (current, correct re-click: residual 0.0 px, height 1.641 m,
recomputed and matching the file's own `_audit` stamp) and `flexi_franz_p01` (high-coverage
amateur clip, 2.503 m). For each, corrupted the four clicked doubles corners **in memory**
in five families, then recomputed on a real decoded frame + a real clean net-tape plate:

- `coverage`, `visible_frac`, `centrality`, `verify_court().ok` — `calibration.py`'s shipped
  gate, run on `H = homography_from_landmarks(corrupted_kp)` (the same call the product uses).
- `fit_residual_px`, `camera_height_m`, fitted `hfov_deg` — `courtfit.cam_fit_quad`, the same
  function `validate_new_clip.py --stamp` uses for the `_audit.camera_height_m` field.
- `tape_H_m` / `delta_pct` / refusal — `tools/net_tape_height.py`'s `measure_tape_height`
  against the clip's own real clean plate (unchanged by the corruption — only the *predicted*
  row moves with a corrupted `H`), the one off-plane statistic in the repo.

Corruption families:
- **near-half compress (anisotropic)**: far corners interpolated toward the near corner on
  their own side by fraction α (0.15 → 0.90). This is the mechanism the claim describes.
- **isotropic scale**: all 4 corners scaled uniformly about the quad centroid (researcher's
  requested control — the textbook pure-scale case).
- **sideways shift**: all 4 corners translated by a fixed px offset (5/10/20% of frame width).
- **rotate**: quad rotated about the image centre (5/15/30°).
- **asym-scale**: only the two LEFT corners moved inward (breaks L/R symmetry).

## Result table — `yt_match40` (1280×720, baseline coverage 0.941, height 1.641 m)

| corruption | coverage | centrality | verify_court | residual px | height m | hfov° | tape delta% | tape verdict |
|---|---|---|---|---|---|---|---|---|
| baseline | 0.941 | 0.926 | **PASS** | 0.00 | 1.64 | 91.0 | +6.7% | agree |
| depth α=0.15 | 0.824 | 0.952 | **PASS** | 0.08 | 1.66 | **55.3** | **-18.5%** | **disagree** |
| depth α=0.30 | 0.807 | 0.928 | **PASS** | 0.09 | 1.66 | **34.4** | — | **refused (R5)** |
| depth α=0.50 | 0.723 | 0.881 | **PASS** | 0.07 | 1.67 | **18.3** | **-30.8%** | **disagree** |
| depth α=0.70 | 0.723 | 0.839 | **PASS** | 0.04 | 1.67 | **8.7** | — | **refused (R5)** |
| depth α=0.90 | 0.926 | 0.803 | **PASS** | 2.99 | 1.20 | **2.4** | — | **refused (R5)** |
| isotropic 0.95 | 0.883 | 0.930 | PASS | 0.08 | 1.64 | 94.0 | -5.6% | agree |
| isotropic 0.85 | 0.622 | 0.937 | PASS | 0.23 | 1.66 | 100.3 | — | refused |
| isotropic 0.70 | **0.313** | 0.946 | **FAIL** | 0.47 | 1.67 | 111.0 | — | refused |
| isotropic 0.50 | **0.290** | 0.953 | **FAIL** | 0.79 | 1.67 | 127.2 | — | refused |
| shift 5%w | 0.676 | 0.878 | PASS | 2.38 | 1.67 | 89.4 | +5.1% | agree |
| shift 10%w | 0.718 | 0.815 | PASS | 8.19 | 1.56 | 90.0 | — | refused |
| shift 20%w | 0.694 | **0.680** | **FAIL** | 37.4 | 1.73 | 62.5 | — | refused |
| rotate 5° | 0.697 | 0.929 | PASS | 13.0 | 1.79 | 93.6 | — | refused |
| rotate 15° | 0.580 | 0.935 | PASS | 32.1 | 0.89 | 134.2 | — | refused |
| rotate 30° | 0.588 | 0.945 | PASS | 82.6 | 1.83 | 133.9 | — | refused |
| asym-scale 0.05 | 0.748 | 0.901 | PASS | 1.81 | 1.71 | 112.3 | — | refused |
| asym-scale 0.15 | 0.771 | 0.839 | PASS | 28.0 | 1.86 | 116.7 | -20.4% | disagree |
| asym-scale 0.30 | 0.855 | **0.731** | PASS (borderline) | 72.7 | 2.57 | 124.3 | — | refused |

Full raw JSON: scratchpad (not committed; reproduce with the method above).

## Result table — `flexi_franz_p01` (4K-ish, baseline coverage 0.996, height 2.503 m)

Same shape, condensed: **`verify_court` never once flips to FAIL** for any depth
compression (α up to 0.90), any isotropic scale down to 0.5, any shift up to 20%, or any
rotation up to 30° — because this clip's baseline coverage margin (0.996) is so far above
the 0.40 bar that nothing in the tested range crosses it. Only `asym-scale 0.30` trips
centrality (0.693 < 0.70). **But the underlying coverage NUMBER still separates the two
mechanisms cleanly**: at matched "50%" severity, isotropic scale drives coverage to 0.781
while depth compression only reaches 0.956 — the same ordering as `yt_match40`, just not
far enough to cross this particular clip's very generous margin. `camera_height_m` stays
flat (2.50–2.55 m) through α=0.70 of depth compression, only breaking at α=0.90 (0.996 m,
residual jumps to 123 px — the quad has gone numerically degenerate, not delicately caught).
hfov again collapses monotonically with depth compression (60.6° → 38.2° → 24.8° → 13.7°),
crossing outside a 60–90° amateur-lens prior already at α≈0.15. The tape refuses (does not
falsely agree) from α=0.15 onward on this clip too.

## Reading the mechanism, not just the numbers

**Depth-axis (anisotropic) compression survives the entire tested range on both clips**
against every SHIPPED ground-plane gate: `verify_court` never fails from it, and
`camera_height_m` stays inside or near the "plausible amateur mount" band (1.36–3.35 m)
the whole time it is tested. This is the real, reproducible core of the claim.

**But it is not invisible to every ground-plane quantity — only to the ones actually
gated.** `cam_fit_quad` already solves for focal length (hence hfov) as part of the exact
same fit that produces the reported height. That hfov **collapses monotonically and
sharply with compression severity on both clips** (91°→55°→34°→18°→9°→2° on one; 61°→38°→
25°→14°→7°→5° on the other) — outside the repo's own stated "mounts run 60–90°" prior
already by α≈0.15. **Nobody reads it.** `camera_height_m()`'s production call even uses a
FIXED default 70° hfov rather than the one the fit already computed. This is the sharpest
adversarial finding here: the claim frames the miss as structural/geometric; the evidence
says it is a **reporting gap** in code that already has the number.

**Isotropic scale is caught, confirming the researcher's cross-feed prediction.** On
`yt_match40`, `verify_court` correctly FAILS at isotropic factor ≤0.70 (coverage 0.31, well
under 0.40) while remaining blind to depth compression at every tested severity. The
mechanism is not really "ground-plane vs off-plane" — it is **whether the corrupted homography
still projects onto REAL PAINT that happens to be nearby**. Depth compression keeps pointing
at real lines (the near baseline, near service line, centre line — genuinely painted, just
the wrong ones), so coverage stays high; isotropic shrink/shift/rotation move the projected
lines into paint-free space, so coverage collapses. `verify-court-false-rejects.md`'s own
framing ("coverage measures whether lines land on paint, not whether they land on the paint
they are named for") already says this — this run is the first place it is quantified
against a controlled corruption rather than one historical anecdote.

**Rotation/shift/asym-scale get caught mainly through `fit_residual_px`, and mainly because
they are NOT achievable by any valid camera pose the model allows** (±3° roll cap, fixed
principal point at image centre) — not because they defeat some geometric symmetry. Residual
explodes at small magnitudes for all three (13 px at 5° rotation on `yt_match40`, 45 px at 5°
on `flexi_franz_p01`). Depth compression, by contrast, IS well-approximated by an alternate
legal camera pose (closer, steeper pitch, narrower lens) — that is mechanically why its
residual stays near 0 up to α=0.7–0.9. This is a more precise mechanism than "z=0 symmetry":
**degenerate along the camera's own pose manifold, vs not.**

## Magnitude: how much compression before anything shipped notices

**Nothing shipped notices at any magnitude tested.** `verify_court` and the camera-height
screen pass every depth-compression level from α=0.15 to α=0.90 (far corners moved 90% of
the way to the near corners — a severe, visually obvious corruption) on both clips. No
magnitude bound was found within what is numerically testable before the quad degenerates.

**The off-plane tape notices earliest, at the smallest tested magnitude (α=0.15)**, either
as a clear disagreement (-18.5%, -30.8% on `yt_match40`, both failing the 10% AGREE bar) or
as an honest refusal (unable to confirm) rather than a false pass — on both clips.

**An unshipped-but-free ground-plane quantity (fitted hfov) would notice at a comparable
magnitude (α≈0.15, crossing outside the stated 60–90° amateur-lens prior)** — i.e., the
tape's advantage over a properly-read ground-plane statistic is not in sensitivity, it is
that the tape is the one that actually got built and shipped.

## What this does NOT establish

- A rate. Two clips, synthetic corruption, not a corpus sweep.
- That `verify_court`'s 0.40/0.70 bars are "fine otherwise" — `flexi_franz_p01`'s result
  shows those bars are also generically too lax (nothing but the most extreme asym-scale
  trips them), independent of the depth/isotropic distinction; this is consistent with,
  not new evidence against, the existing `verify-court-false-rejects.md` finding.
- Anything about the net POSTS candidate (`independent-calibration-references.md` §1) —
  out of scope here; this run only exercised the tape, coverage/centrality, and the
  camera-height/hfov fit.
- A recommendation to gate on hfov. Rule (this brief, NOT-THIS-RUN) — reported as an
  observation for whoever reads this, not proposed as a new gate.

## For the record — which artefact each anchoring number belongs to

`docs/evidence/verify-court-false-rejects.md` has, in order: (1) a 25-clip measurement
(coverage 0.245–1.000, three real refusals, `yt_match40`'s **confirmed-wrong** `.bak`
passing at 0.436/11.3 m/0.9 px — the ONE real positive this project has for a wrong
court passing coverage); (2) a camera-height table where 11.3 m was the one confirmed
catch and two others were later found to be a correct broadcast height (`eala`, 8.89 m,
unverified→correct) and an unverifiable file; (3) a **SUPERSEDED** section (re-click
"wrong: corners on the NET", residual 0.2 px, height 1.61 m, coverage 0.944) that was
**withdrawn the same hour** as a misreading, with the correction stating the calibration
was actually right (residual 0.0 px, height 1.64 m, coverage 0.948). The
`independent-calibration-references.md` anecdote (0.0 px / 1.64 m / 0.944) blends the
withdrawal's residual+height with the superseded section's coverage digit — none of it
describes a confirmed-wrong court. This should be corrected wherever it is cited as
supporting evidence; it is not QA's place to edit that file, so it is reported here.

## NOT ESTABLISHED THIS RUN

- A corpus-wide sweep (only 2 of ~28 clips tested).
- Any test of the net-POST candidate specifically.
- Whether `hfov` outside 60–90° would false-reject any CORRECT broadcast/elevated
  calibration the way the camera-height screen already does on `eala` — not checked here.
