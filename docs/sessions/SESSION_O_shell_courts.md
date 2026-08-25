> **STATUS: O2 RUN 2026-08-24 — THREE NEGATIVES, NO SHIPPED CHANGE.** The
> EVID_BAND hypothesis this brief was built around is **refuted**, and so are two
> follow-on hypotheses. No shipped code has been touched. Results in
> [§ O2 results](#o2-results--three-negatives-and-a-method-correction);
> evidence in `data/output/evid_band_sweep.log`, `behind_camera.json`,
> `tol_sweep.log`, `truth_neighbourhood.log`.
>
> Everything above that section was written BEFORE the first run and is left
> unedited, which is the only reason the numbers below are worth anything.

# Session O — indoor shell courts: what the research got right, what it got wrong, and the order to find out

## Where this sits

[docs/RESEARCH_BRIEF_indoor_shell_courts.md](../RESEARCH_BRIEF_indoor_shell_courts.md) asked
six questions. The reply ranked five recommendations. Before building any of them the reply
was checked line-by-line against `backend/swingvision/courtfit.py`. **Three of its five
load-bearing claims are wrong about this codebase**, and a fourth rests on ground truth that
does not exist yet.

That does not make the reply useless — Q2's answer is decisive and closes a branch we would
otherwise have spent a session on. But the build order it proposes is wrong for us.

---

## Correction 1 — the scorer is ALREADY model-length-normalised

The reply's whole case for recommendation #2 is that we run Farin's absolute additive score
(+1 per covered court-line pixel, −0.5 per non-line pixel) and that it "saturates on your
395k–1,257k-pixel clutter mask".

We do not run that score. `courtfit._ori_detail`, line 161:

```python
agree = float(sup_cnt[ev].sum()) / float(max(1.0, inb_cnt[ev].sum()))
```

That is a **fraction of the projected model** — numerator and denominator are both counts of
model samples. It is arithmetically independent of how many pixels the mask contains. It is
also already oriented (`align >= athr`, athr 0.80 in double-angle = ±18.4°) and already
evidence-gated (a model line with no paint near it is excluded rather than scored zero).

So "add model-length normalisation" and "add orientation" are **already done**, and the
stated mechanism for the 0.18–0.31 under-scoring is not the mechanism. Two things survive
from #2 and both are worth having:

- **the a-contrario / NFA test** — genuinely absent, and see the prediction in B3;
- **best-vs-next-best** — built as a diagnostic (`eval/score_truth.py` computes the margin),
  never part of the accept rule.

**A likelier mechanism for the low true-court score, from reading the same function:**
`EVID_BAND = 5.0` marks a model line "measurable" when paint sits within **5×tol**, but
`sup` only counts paint within **1×tol**. A fence rail or truss 3–4 tol away from a model
line therefore promotes that line into the denominator while contributing nothing to the
numerator. On a cluttered frame that is a direct, mechanical drag on `agree` at the *true*
court. Cheap to test, and the research did not raise it.

**MEASURED 2026-08-24: REFUTED.** See [§ O2 results](#o2-results--three-negatives-and-a-method-correction).
The gate excludes nothing at the true court on any of the 10 calibrated clips.

### Two conditions on any EVID_BAND change, pre-registered

1. **`n_included` is reported on every hypothesis, and guarded.** Lowering the band
   inflates every score, and a wrong court that falls back to 3 well-supported lines
   scores ~0.95 on them. So the sweep scores three guards beside the raw number —
   `n_included >= 7`, `g · min(n_inc,8)/8`, and `g · n_inc/n_geometrically_in_frame`.
   Without a guard the "fix" is a recall lever that ships a confident wrong court.
   *(Note: `court.LINES` has **10** entries — 8 regulation lines plus the centre
   service line and the net — so a fixed `/8` is not the observable count. The third
   guard uses the real one.)*
2. **The deciding number is the MARGIN between the true court and the best wrong
   court, not the level at the true court.** Both are reported; a level that rises
   while the margin falls is the failure mode, not the fix.

### Deciding observability from geometry instead of from paint — the cost

Asked for before building. The answer is that the **in-frame half is free** and was
therefore measured rather than estimated: dropping the `EVID_MIN` test makes
`ev = seen`, a one-line change, and it runs in the sweep as the `geom` config. The
**un-occluded half** is what costs — knowing a line is hidden behind a player needs
the mover blobs from `eval/movers.py` (~1 h on top of what B1 builds anyway), and
knowing it is hidden behind the net or a post needs more than that.

**Measured: `geom` is a byte-identical no-op**, +0.000 margin on all 10 clips. The
free half buys nothing, so there is no evidence to justify the half that costs. **Do
not build it.**

## Correction 2 — recommendation #1 cannot turn 0/5 into acceptances

The reply's headline pick is a player-foot / horizon consistency **gate**, and correctly
notes it "can only refuse bad courts, so it cannot spend your precision record". That is the
same sentence as: **it cannot produce an acceptance.** Every gate joins the `ok = ...`
conjunction in `autodetect`; conjunctions only remove candidates.

Its one indirect route to recall is vote concentration. `consensus` keeps the largest group
of frames agreeing within `AGREE_PX = 30`; `flexi_franz` locks 7 of 8 frames and scores
**1 vote**, i.e. seven different courts. Refusing the wrong ones raises the vote count **only
if at least two of those seven were already near-correct and mutually agreeing.**

Nobody has checked whether that is true. It is checkable in minutes and it decides whether
the entire #1/#3/#4 branch has any recall upside on shell at all. That check is step O1.

**And vote concentration does not work under the current accept rule either.** The rule
is ≥6 of **8 sampled frames**, not ≥6 of the survivors. A gate that kills 5 frames and
leaves 3 agreeing survivors has produced 3 of 8 — still a refusal. So the gate alone
cannot convert anything; it only pays if the rule becomes:

> **≥6 of the frames that SURVIVED the gate**, with a floor on how many may be discarded.

That is a second, separate change, and **it is where the precision cost actually sits** —
it lowers the effective evidence bar for an acceptance, which is the direction that
spends the record. It must be pre-registered and gated **on its own**, never shipped in
the same change as the gate that feeds it. A gate that refuses and a rule that accepts
more easily are not one idea.

## Correction 3 — cross-ratio screening (#3) has nothing to screen

#3 assumes a line-combinatorial generator: choose 4 of the 40 detected lines, screen the
quadruple by cross-ratio, fit. **That step does not exist here.** `autodetect` generates
courts from a 5-parameter seed grid, a learned pose prior and synthetic low-cam poses, then
refines and scores. Lines are matched to the model *after the fact*, in `_structure`, which
already enforces regulation spacing implicitly (each of 8 model lines must claim its own
distinct real line at 7° / `max(8, w*0.018)` px tolerance).

To use #3 we would have to add a whole new hypothesis generator. That is not a filter, it is
a second search path — and widening the search is what already failed this month (the
seed-grid widening reached new courts and got every one of them wrong, 26 px and 78 px).
Not necessarily a bad idea, but it is a session, not a step, and it must not be sold as cheap.

**Deferred, not dead — the non-vacuous version, for whoever picks this up.** Applied to the
**detected** lines that `_structure` has already assigned to model lines, rather than to the
projected model lines, the test has real content: it asks whether the four *claimed real*
lines are mutually consistent at regulation spacing, not merely whether each one is
individually close to where the model put it. A shifted or wrong-rung court can pass eight
individual proximity checks and still fail a cross-ratio on the four lines it claimed.
~30 lines, and it composes with the existing structural test instead of replacing it.

## The gap the research could not see — THERE IS NO SHELL GROUND TRUTH

Every recommendation ends with "test against your gate". The gate is 20 gold clips plus 10
human-calibrated references. **None of them is a shell court.** All five shell recordings are
refusals, and a refusal carries no error measurement.

So today, on the target footage, we cannot score anything: not whether a fix helped, not
whether the true court is even inside the candidate set, not whether `score_truth`'s margin
is positive there. The gate can currently only prove a change **did not break** what already
works.

This is the binding constraint on the session and it takes ~10 minutes of human time to lift.

---

## Build order

The scoring diagnostics do not need shell ground truth — they are search-free on the 10
already-calibrated clips — so they run in parallel with the labelling rather than behind it.

| # | step | needs shell truth? | status |
|---|---|---|---|
| 1 | user labels the shell clips (2 per recording) | — | **waiting on the user** |
| 2 | the EVID_BAND / scoring diagnostics (O2) | no | **RUN 2026-08-24 — three negatives** |
| 3 | `candidate_audit.py --movers` (O1) | yes, for shell | run on the 10 refs; shell pending |
| 4 | branch per the decision tree | yes | not started |

## The plan, as a decision tree — measure first, build second

### O0 — human truth for the five shell recordings *(user, ~10 min, blocking)*

Place four corners by hand on one clip per recording, using the Court Setup tool with
**shape-lock OFF** — that is what writes `"_exact": true`, which is what `eval/run_refs.py`
and `eval/score_truth.py` both accept as human ground truth.

```bash
py tools/court_setup_server.py
```

Save as `data/<clip>_pts.json` matching the video stem, one per recording:

| recording | clip to label | save as |
|---|---|---|
| flexi_franz | `data/incoming/Shell/flexi_franz_p01.mp4` | `data/flexi_franz_p01_pts.json` |
| flexi_joy | `data/incoming/Shell/flexi_joy_p01.mp4` | `data/flexi_joy_p01_pts.json` |
| mpc_mixed | `data/incoming/Shell/mpc_mixed_p02.mp4` | `data/mpc_mixed_p02_pts.json` |
| mpc_tuesday | `data/incoming/Shell/mpc_tuesday_p01.mp4` | `data/mpc_tuesday_p01_pts.json` |
| hillsborough | `data/incoming/Shell/hillsborough_p02.mp4` | `data/hillsborough_p02_pts.json` |

**Label TWO clips per recording, not one** — ten references, not five. Five points is thin
enough that any threshold fitted to them is overfit to three venues.

### The tuning rule — where numbers may be fitted, and where they may only be checked

> **Tuning happens on the 10 existing calibrated clips. The shell set is VERIFICATION
> ONLY.** No threshold, constant or gate may be chosen, swept or adjusted against the shell
> recordings. They are the held-out answer to "did this generalise", and a number tuned
> against them stops being able to answer that — permanently, because you cannot un-see a
> test set.

This is the same discipline as the blind holdout carved out of the gold set in P0-1, and it
exists for the same reason: pre-registering each individual sweep never stopped the
cumulative drift of a dozen sweeps against one fixed population.

Both harnesses pick these up automatically by stem — no code change needed.

**Nothing else in this session can be scored on shell until this exists** — but see the
build order: the scoring diagnostics do not depend on it and run first.

### O1 — is the right answer even in the candidate set? *(~15 min compute)*

`eval/candidate_audit.py` (written, unrun). For every clip with a human court, dump all 8
per-frame locks and measure each against that court in px@640.

Three outcomes, each selecting a different branch:

| what O1 finds | what it means | branch |
|---|---|---|
| **≥2 locks within 20 px**, mutually agreeing | the search already finds the truth; wrong locks are drowning it | **B1 — gate** (refuse-only; the reply's #1) |
| **exactly 1 lock within 20 px** | truth is reachable but rare | **B1**, plus more sampled frames |
| **no lock within 20 px** | the search never produces the right answer | **B2 — generator/mask.** A refuse-only gate is precision-only here and must not be sold as the shell fix |

Run `eval/score_truth.py` over the same five at the same time. If the margin is negative at
the human court, the criteria cannot recognise truth even when handed it, and **B3 —
scoring** comes first regardless of what O1 says.

### B1 — the player-plausibility gate *(refuse-only, precision-safe)*

Simpler and stronger than the reply's horizon fit, and it reuses machinery this repo has.
Do **not** fit a horizon from foot points: our 8 frames come from one short clip cut at a
serve boundary, so the players barely move and the fit is badly conditioned exactly where we
need it.

Project the feet through the candidate homography into court metres instead:

> Movers' foot points, pushed through `calibration.image_to_court(H, …)`, must land inside
> the court plus a generous surround. The `am_ntrp45w` failure collapses all 23.77 m onto a
> curtain band near the horizon — real players standing on the real floor project to absurd
> court coordinates under that H. No vertical VP, no cross-ratio, no horizon fit; closed-form
> geometry that is already tested.

Movers come from `eval/movers.py`: temporal median clean-plate → absdiff → components in a
player-sized band, taller than wide → foot = (centroid x, bottom y). Pure OpenCV, no torch,
so the court path keeps its zero-ML-dependency property.

**The gate's tolerance is COARSE and must stay coarse: court ± 10 m.** Two independent
reasons, both about what the measurement can resolve. The foot points come back from a
downscaled pass, so they carry ±1 scale factor of pixel error — and near the far baseline,
where the ground plane is nearly edge-on, a few pixels is **several metres** on the court.
And players legitimately stand well behind a baseline, so a tight gate fires on a deep
return. This separates "on the court" from "hundreds of metres away", which is the only
distinction the evidence supports and the only one the failure needs. Fine as a bound;
never read as a position.

### B2 — the horizon crop, derived from where players stand *(recall-positive)*

The one lever in this session that can actually raise shell recall, and it falls out of the
same foot points.

Roof trusses, strip lights and the upper fence lattice are **above** every point a player can
stand on. A player behind the far baseline appears with feet at or slightly above the far
baseline in image y. So:

    y_deep      = 5th percentile of foot_y over the WHOLE recording  (95th of DEPTH)
    y_court_top = y_deep − k · spread − floor,  capped by the hard rule below

Zero the mask above that row. This removes architecture from the Hough pool *before* the
lines are detected, which changes which candidates are generated — unlike everything else in
this session, it is not refuse-only.

**This is the only genuine precision risk in the plan, and its failure directions are
asymmetric.** Too permissive costs nothing: a spectator on a balcony or a shadow on the
fence pushes the row up, the crop removes less clutter, and the fit is what it is today.
Too aggressive is the dangerous direction: a recording where no player ever goes deep puts
the row below the far baseline, the crop deletes true court lines, and the detector returns
a **wrong court rather than a refusal**. Wrong courts are the one thing the gate does not
tolerate. A `min` over 8 frames is a max-statistic on 8 samples, which is exactly where that
fails — so four mitigations are required, not optional:

1. **Robust percentile over the WHOLE recording**, not the 8 fitting frames — the 5th
   percentile of foot *y*, which is the 95th percentile of *depth*.
   (`run_refs.frames_from(video, 120)` is the intended source; the median plate is
   subsampled internally so the cost stays flat.) The percentile buys **usefulness**, not
   safety: a raw min over 25 minutes picks up every spectator and puts the row near the top
   of the frame where the crop removes nothing. Reading it as a safety device gets the sign
   backwards.
2. **A generous safety margin below the line** — `k · spread` plus an absolute floor of 5%
   of frame height, because the spread term vanishes exactly when the evidence is thin.
3. **Hard rule: the crop never sits below the topmost candidate court line.** The only
   ingredient the foot statistics cannot fool. Sourced from the per-frame locks of the
   uncropped pass, or from the human court when verifying.
4. **Verify on all 20 gold clips that the crop never removes a clicked keypoint.** Cheap,
   and it is the check protecting the precision record.

**Pre-register `k = 1.0`.** If it fails the gate, it fails; do not tune `k` against the gold
set — that is exactly the cumulative-drift problem the blind holdout (P0-1) was carved out
to stop.

Requires one additive shipped change: thread `mask_fn` through `auto_fit_frame` to its three
mask consumers (`autodetect`, `snap_to_lines`, `line_distance_map`), defaulting to `None` so
the shipped return stays byte-identical — the same pattern and the same discipline as the
existing `with_score` kwarg.

### B3 — NFA, with its result predicted in advance

Replace the fixed `accept = 0.33` with a clutter-relative test. Per model line, estimate the
null hit rate empirically:

    p_i = mean over all in-frame pixels of [ dt <= tol AND align_i >= athr ]

then `NFA = N_candidates · P(Binomial(N, p̄) ≥ K)` over the measurable lines, accepting at
NFA < 1.

**Pre-registered in the terms that actually decide it — what it COSTS, not what it
spares.** "Makes shell worse" is not a cost anyone pays: shell is already 0/5, and zero
cannot fall. The number that decides B3 is:

> **How many of the 12 current gold acceptances does NFA lose?**
> Ship at **0 lost**. Anything above 0 has to be paid for by more than it buys, and the
> 20 px precision rule still binds absolutely.

Two further predictions, written down so they cannot be claimed as successes afterwards:

- **Ceiling on the win: at most 3 of the 10 references.** NFA reshapes a *threshold*. It
  cannot make the truth the maximum when the truth is not the maximum, so its reach is
  exactly the clips where the margin is already positive but the level is below 0.33.
  After the O2 correction that set is `A7vXlWIlyrI`, `am_hard_utr`, `sAjkpeRq4P4` — plus
  `HoHxFSX_gLk_s1`, whose margin turned out to be positive after all. Any clip with a
  negative margin is out of its reach by construction.
- **Shell stays 0/5 under B3 alone**, because at shell's clutter density the true court and
  the best wrong court both sit near chance. If shell improves under B3, the mechanism is
  wrong and the result needs explaining before it is believed, not after.

---

## The gate — unchanged, and pre-registered before the first run

> **≥12 of 20 gold clips accepted, AND zero accepted court more than 20 px from the human
> clicks** (`WRONG_PX_640 = 20.0`, the empty band between accepted 3.4–13.9 px and refused
> 25.5–111 px).

Secondary, reported but not gating: the existing references (currently 2/10), the independent
drop set (currently 11/45 — the honest denominator, not 19/54; see `eval/recordings.py`), and
shell (currently 0/5).

**Any change that buys shell recall by admitting one wrong court is rejected.** Two changes
have already died on exactly this: seed-grid widening and global mask replacement.

## The stopping rule — written now, not after the result

Court auto-detection was already closed once as a model problem (Session H part 2). This
session reopens it on a specific new venue class. It closes again if:

- **O1 finds no lock within 20 px on any of the five**, AND
- **B2's crop fails the gate**,

because at that point the search cannot reach the truth and the one recall-positive lever in
the tree has been spent. The correct output is then a documented refusal path for indoor
shell — the 30-second manual court — not a sixth attempt.

## Explicitly NOT in this session

- **Vanishing-point filtering as a court/not-court classifier.** The research settles this: a
  shared VP proves 3D parallelism, not coplanarity, and floor and roof are related by a planar
  homology whose axis is the horizon. A building aligned with the court is indistinguishable
  from the court by line direction alone. Closed.
- **Single-image multi-homography plane grouping** (J-/T-Linkage, Progressive-X, CONSAC) —
  two-view methods, ill-conditioned even there.
- **Fine-tuning the 14-keypoint CNN on hand-annotated shell frames.** A real option at a real
  cost (~300–600 labelled frames), and it should not start before the geometric tree above is
  exhausted.
- **Cross-ratio quadruple screening (#3)** — no generator to screen; see Correction 3.
- **Temporal median as a mask cleaner in its own right (#5)** — the clean plate gets built for
  B1/B2 anyway, but the reply is right that its ceiling is low, because the architecture is
  static too. A by-product here, not a step.

## O2 results — three negatives and a method correction

Run 2026-08-24. Search-free: 10 human-calibrated clips, 3 frames each, 1024 coarse-grid
distractors per frame, the real shipped `_ori_detail` throughout (module constants swept,
no scoring logic reimplemented). Evidence in `data/output/evid_band_sweep.log`,
`behind_camera.json`, `tol_sweep.log`, `truth_neighbourhood.log`.

### 1. EVID_BAND is inert — the hypothesis this brief was built around is refuted

`n_included = n_geometrically_in_frame = 10 of 10` on **every clip at every band** from the
shipped 5.0 down to 1.0. The evidence gate never excludes a line at the true court, so it
cannot be what depresses the score. The proposed mechanism is wrong.

### 2. Narrowing the band is a wrong-court lever — exactly as pre-registered

It does not move the truth (`g@true` identical to three decimals) and it *does* move the
wrong courts: their `n_included` falls 10 → 8.5, which raises their normalised score.

| band | 5.0 (shipped) | 3.0 | 2.0 | 1.5 | 1.0 |
|---|---|---|---|---|---|
| median margin, raw | **+0.123** | +0.123 | +0.116 | +0.111 | +0.102 |
| median `n@wrong` | 10.0 | 10.0 | 9.5 | 9.0 | 8.5 |

`band1.0` does lift 2 of the 5 low clips over the 0.33 gate — while cutting the pooled
margin. That is the "higher level, worse separation" failure, caught by the pre-registered
condition rather than shipped.

### 3. Geometric observability is a no-op — so don't build the expensive half

`geom` (drop the `EVID_MIN` test, `ev = seen`) is **+0.000 margin on all 10 clips**,
byte-identical to shipped. The free half of the cleaner fix buys nothing, so there is no
evidence to justify the un-occluded half that costs ~1 h+. **Closed.**

### 4. Two of my own follow-up suspicions, also refuted

- **Behind-camera projection.** `_apply` divides by the homogeneous coordinate without a
  sign check, so points beyond the horizon could mirror back into frame and inflate the
  denominator. Measured: **0.0% of samples behind the camera on every clip.** (My reason for
  suspecting it was also wrong: `reliable_court_span`'s "7.5 m of 23.77" is about
  metres-per-pixel precision near the horizon, not about lines being off-frame.)
- **Ground-truth registration error.** Swept `tol` ×0.5 → ×4. No clip shows the
  steep-then-plateau signature that click error would produce, and the median margin
  degrades monotonically (+0.147 → +0.123 → +0.049). Not a labelling artefact. *(Aside: the
  shipped `tol` is mildly conservative-optimal — ×0.5 scores +0.147 — but tightening it
  would trade against what the refine stage has to grab, so it is not a free win.)*

### 5. THE METHOD CORRECTION — a published claim is withdrawn

`eval/candidate_audit.py` showed `am_hard_utr`'s locks landing **within 20 px of the human
court and outranking it by 0.296**. So the human clicks are not the best-registered court in
their own tolerance band — and every search-free number this project has quoted scores the
clicks exactly.

Sweeping the neighbourhood the gate itself calls correct (`eval/truth_neighbourhood.py`), at
a median **5.8 px** from the clicks:

| | at the clicks | best court still inside the 20 px gate |
|---|---|---|
| clears the 0.33 accept gate | 5/10 | **9/10** |
| margin over best wrong court positive | 8/10 | **9/10** |
| median margin | +0.126 | **+0.210** |

**"The criteria reject the correct answer even when handed it" is false on 9 of 10 clips.**
Withdrawn in place in `data/output/court_why_it_fails.md` (finding A),
`docs/RESEARCH_BRIEF_indoor_shell_courts.md` §4, and `eval/score_truth.py`'s docstring.
One clip survives as a genuine scoring failure: **`UHf0LeMU2pg`** (best 0.279, margin −0.014).

## O1 results — the search finds it; the frames disagree

`eval/candidate_audit.py`, 10 references × 8 frames. Reproduces the shipped 2/10 accept rate
exactly (`am_hard_utr` 7 votes, `sAjkpeRq4P4` 6), which is the validity check.

| | clips |
|---|---|
| truth inside the candidate set (≥1 lock within 20 px) | **7 / 10** |
| ≥2 good locks that also agree with each other | 4 / 10 |
| truth never reached — gating cannot help | 3 / 10 |

The within-frame margin you asked for does the job the vote count cannot — it splits those
3 into two *different* failures: `HoHxFSX_gLk_s1` −0.112 (locks outrank truth → scoring),
`tc8CGFxyRE8` +0.161 and `UHf0LeMU2pg` +0.038 (truth outranks the locks → search/gate lost
it).

**And it kills B1's recall case outright.** A refuse-only gate plus the survivor-based vote
rule converts **zero** additional clips, because the good locks do not agree with each other:

| clip | good locks | largest agreeing subset | best possible survivor rate |
|---|---|---|---|
| `CYqapSq5llo` | 4 | 2 | 50% |
| `e8T34KoJzOw_s2` | 3 | 2 | 67% |

Even a perfect gate leaves both under a 75% bar. **B1 is precision-only.** So the separate
pre-registration you required for the vote-rule change is moot on this population — there is
nothing for it to convert, and it should not be built to find out.

*Caveat: `truth_fails` in that run is a union across 8 frames — "failed at least once", not
a rate. Do not quote it as one.*

## B2 result — safe, and inert

`eval/crop_safety.py` on all 20 gold clips, at the pre-registered `k = 1.0` with all four
mitigations. **A crop is proposed on 1 of 20**, and that one (`am_ntrp45w`) removes the top
20 rows of 360 with +172 px of clearance. Nine clips ran the real operating condition — 120
frames across the whole recording, 343–480 foot points each; eleven are streamed and were
checked on gold frames only. Neither population produced a crop.

Diagnosed, not guessed: the margin `k · spread` uses the near-to-far foot range, which is
approximately the whole court's image depth, so subtracting it from the deepest foot puts
the row off the top of the frame. Capping detections at `MAX_PLAYERS = 4` — the rules of the
game, not a threshold — halved the blob count and changed nothing, which is what identifies
the margin rather than the mover detection as the cause.

**`k` was not re-tuned**, per the rule in this brief. Re-registering it needs a principled
derivation — the quantity being protected against is a player at the service line rather
than the baseline, which is 5.485 m of 23.77 — but converting metres to pixels needs a
homography, and the crop runs before one exists.

## B1 result — DEAD, and its sign is backwards

`eval/foot_gate_power.py` over **216 per-frame locks** (118 within 20 px of truth, 98 not).
The feet-in-court fraction is **higher for WRONG courts at every margin** — gap −0.033 /
−0.054 / −0.071 at ±5/10/20 m. The statistic rewards a court for being *large*, and wrong
courts are frequently too large; it measures size, not correctness. Best catch at the
standing ≤5% collateral ceiling: **2.0%**, against pose proximity's 11.4% and racquet-box's
54.5%/4.5%, both already rejected on that bar. B1 is closed.

## The frame disagreement, characterised

`eval/agree_sweep.py`. The resolution artefact in `AGREE_PX = 30` is **real** and sits
exactly where the theory predicts — three high-resolution clips have good locks 38–46
*native* px apart that are only 12.8–15.3 px apart at 640. But the fix does not pass: at the
shipped vote bar, height-scaling **loses** a gold clip (12 → 11), and the cell that lifts
references 2 → 5 gets there by accepting a **58.7 px** court on the reference set.

The actionable finding is what they disagree *about*: `w_far` ×7, `w_near` ×6, `y_far` ×4,
`cx` ×1 — **13 of 18 clips disagree principally about how WIDE the court is, not where it
is.** Corner distance treats a width error and a position error identically, so the
agreement test spends its whole budget on the least-determined parameter.

**Untested idea, recorded so it is not mistaken for a result:** an agreement metric
normalised in court terms rather than image pixels would be resolution-independent by
construction and could weight width separately from position.

### What this does to the plan

Every branch in the tree above is now measured at or near zero on the reference set, and the
live question is one the plan never named:

- the criteria **do** recognise the correct court — 9 of 10;
- the search **does** produce it — 7 of 10;
- the frames that each found it **do not agree with each other** — so the vote fails;
- B1 converts 0, B2 fires on 1 of 20, B3's ceiling is bounded by argument (it reshapes a
  threshold, and on 9 of 10 clips the threshold is not what is wrong).

**Frame-to-frame disagreement between correct locks is the open problem.** Nothing in this
brief addresses it. It is also completely untested on shell, which still has no ground truth.

## The honest gap, restated

Five shell recordings from three venues, and the clay evidence is essentially one German club.
Whatever passes here is a result about *those* venues until it is checked on more.
