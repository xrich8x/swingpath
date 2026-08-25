> **STATUS: P1 RUN 2026-08-25 — THE STOPPING RULE FIRED. This brief's mechanism is
> REFUTED.** Reachability is not the cause: on **31 of 38** clips the seed nearest the
> true court is already within refine reach. The brief predicted the opposite and said
> so in advance, which is the only reason the result is worth anything.
>
> **What P1 found instead is sharper and is now the live lead** — see
> [§ P1 results](#p1-results--the-stopping-rule-fired-and-the-real-stage-is-named).
> Everything above that section is the ORIGINAL pre-registered text, left unedited.
>
> Evidence: `data/output/seed_reach.{log,json}`.

# Session P — the search cannot reach the true court

## Where this sits

Session O measured, against 20 human-placed calibrations, that **the scoring criteria are
not the bottleneck**: at a median 4.9 px from the human clicks the true court clears the
accept gate on 19 of 20 clips. Seven hypotheses aimed at scoring and gating measured to
zero. The failure is upstream, in candidate generation.

The 10 clips that never reach the true court split three ways:

| | clips | what it means |
|---|---|---|
| **truth OUTRANKS every lock the detector produced** | **6** | the scorer would pick the right answer; it is never offered one |
| locks outrank truth | 1 | a genuine scoring failure (`HoHxFSX_gLk_s1`) |
| no lock produced at all | 3 | nothing to rank |

**The 6 are this session's population.** The other 4 are outliers and must not be pooled
with them — they have different causes and would blur any attribution.

## The finding this brief is built on

The nearest point of the shipped coarse seed grid to the human court, against how far the
bounded refinement can actually travel:

| clip | nearest coarse seed | refine reach | |
|---|---|---|---|
| `tc8CGFxyRE8` | 22.2 px@640 | 18.3 | out of reach |
| `UHf0LeMU2pg` | 32.2 | 18.3 | out of reach |
| `hillsborough_p02` | 42.1 | **9.2** | out of reach |
| `mpc_tuesday_p01` | 41.9 | **9.2** | out of reach |
| `mpc_mixed_p08` | 46.5 | **9.2** | out of reach |
| `flexi_joy_p07` | 48.8 | **9.2** | out of reach |

`refine_homography_bounded(max_move_px=55)` is an **absolute pixel constant**. On the
640-wide gold clips that is 55 px@640; on a 1920 reference 18.3; on 4K shell **9.2**.

> **This is the second instance of the identical defect Session O found in `AGREE_PX`.**
> Two independent stages of the detector — how far a candidate may be refined, and how
> close two candidates must be to agree — are both governed by absolute pixel constants,
> and both are ~6× tighter on 4K than on the population the gate is built from.

## The mechanism, stated before the work

> The seed grid lands 22–49 px@640 from the true court. Refinement may travel 9.2 px@640.
> So on high-resolution footage the true court is **unreachable by construction** — not
> mis-scored, not out-ranked, not gated out. Never generated.

This predicts something specific and falsifiable, which is the point:

**PRIMARY PREDICTION.** Normalising the reach constants to 640-equivalent will make the
true court *reachable* on the 6 clips, and because the scorer already ranks truth above
every lock on all 6, reaching it should mean **winning**. If reach improves and the true
court still does not win, the mechanism is wrong and the rest of the session is void.

**SECONDARY PREDICTION — the blocker may dissolve.** Session O's agreement-radius fix is
blocked by `tc8CGFxyRE8`, a reproducible wrong court that votes itself in once the radius
widens. But truth outranks that wrong court by **+0.161**. If truth becomes reachable there,
it should displace the wrong court as the consensus and the blocker disappears. **The
wrong-court problem may be a symptom of the reach problem rather than an independent one.**
If so, the two fixes ship together; if not, they must be separated again.

---

## Steps

### P1 — complete the reachability measurement *(no product change, ~20 min)*

The table above measures the **coarse grid only**. `autodetect` also seeds from 500
Monte-Carlo samples of the learned pose prior, from synthetic low-camera poses, and from a
coarse-to-fine local rescan around the top-3. Effective reach is therefore *better* than the
number above, and the honest version has to include all of them.

Per clip, record the nearest seed to truth across the **full** seed set, and the fate of
that seed through each stage: degeneracy floor → refine → sufficiency → structure → pose →
`verify_court` → `_cam_refine`. Deliverable: a per-stage kill table over all 20 clips, in
the shape of Session M's chain attribution.

**No fix is proposed until this table exists.** The coarse-grid number is suggestive, not
sufficient — three causes remain live and they have different fixes:

| if the table says | the cause is | the fix is |
|---|---|---|
| no seed within refine reach of truth | reachability | P2, then P3 |
| a seed is in reach but refine walks away | a trapped optimiser | bound or restart, not seeding |
| a near candidate survives refine and a gate kills it | the gate | identify which; likely shared across clips |

### P2 — normalise the reach constants *(the measured fix)*

`max_move_px` and `AGREE_PX` both become 640-equivalent: `k · (w/640)`.

**Both are exact no-ops on all 20 gold clips**, which are every one of them 640 wide — the
same structural safety property Session O verified for `AGREE_PX` (12/20 at 13.9 px,
byte-identical). That is the whole reason this is safe to try, and also the reason **the
gate cannot validate it**: a no-op produces no evidence. Evidence must come from the
references, with shell held back.

Measured **separately first, then together** — two changes shipped as one is how a null
result gets mistaken for a win, and vice versa.

### P3 — seed from the detected lines, only if P1 says seeds do not reach

**Not a blind grid widening.** That is a measured dead end: it reached new courts and got
every one of them wrong (26 px, 78 px). Do not re-propose it.

The alternative is a data-driven seed: the strongest near-horizontal pair and the strongest
near-vertical pair among the detected lines imply a quadrilateral directly. That produces a
handful of candidates grounded in the image rather than 1024 grid points that ignore it —
and it is finally the generator that **cross-ratio screening** (deferred in Session O as
having nothing to screen) can act on, since it produces line quadruples by construction.

### P4 — re-test the wrong-court blocker

Re-run Session O's agreement sweep after P2. Specifically: does `tc8CGFxyRE8` still accept a
58.7 px court, or does the now-reachable true court displace it?

---

## The gate — unchanged, pre-registered before the first run

> **≥12 of 20 gold clips accepted, AND zero accepted court more than 20 px from the human
> clicks** (at 640 wide).

Reported beside it, not gating: the 10 original references (currently 2/10) and the 10 shell
clips (currently 0/10).

**A wrong court on ANY population is a failure**, whatever the gold gate says. Session O's
`30·(w/640)` cell passed the letter of the gate at 12/20 and was rejected because it admitted
a 58.7 px court on the references. That standard carries forward.

## The tuning rule, carried forward from Session O

> Tuning happens on the 20 gold clips and the 10 original references. **The 10 shell clips
> are VERIFICATION ONLY** — no constant may be chosen, swept or adjusted against them.

`mpc_tuesday` is additionally excluded from truth: its two independent labels disagree by
**25.4 px@640**, above the wrong-court line. Report it; do not score against it.

## Stopping rule — written now, not after the result

Court auto-detection has been closed once as a model problem and reopened twice. It closes
again if:

- **P1 shows seeds DO reach truth on most of the 6** — the mechanism above is then wrong and
  this brief is void; go to refine/gate attribution before proposing anything else; and
- **P2 fails the gate or admits a wrong court on any population.**

At that point the reach hypothesis is spent and the correct output is the documented refusal
path plus camera guidance — not a fourth reopening.

## Explicitly NOT in this session

- **Blind seed-grid widening** — measured dead end, see P3.
- **Any scoring change.** Session O measured the criteria recognising the correct court on
  19 of 20 clips. `UHf0LeMU2pg` (the one genuine scoring failure) and `HoHxFSX_gLk_s1` (the
  one clip where locks outrank truth) are 2 of 20 and are not the pattern; fixing them is a
  separate, smaller question and must not be bundled in.
- **The player-foot gate.** Closed: its discriminative power is inverted, catching 2.0% of
  wrong locks at the ≤5% collateral ceiling.
- **The horizon crop.** Closed as safe-but-inert: fires on 1 of 20 clips.
- **Vanishing-point classification** — geometrically impossible to separate coplanar ground
  lines from parallel elevated structure by direction alone.

## P1 results — the stopping rule fired, and the real stage is named

Run 2026-08-25. 40 clips with human truth (20 gold + 10 references + 10 shell), 3 frames
each, following the seed nearest the human court through all nine stages of `autodetect`.
Two excluded from truth (`mpc_tuesday`, labels disagree 25.4 px).

### 1. Reachability is NOT the cause — this brief's mechanism is refuted

On **31 of 38** clips the nearest seed is already within the refine bound. The brief
predicted the opposite. **The stopping rule as written fires.**

The coarse-grid figure that motivated the brief was a lower bound and I said so: the full
seed set is ~2,200 seeds per frame, not 1,024, once the pose-prior samples, the low-cam
poses and the coarse-to-fine rescan are counted.

### 2. The kill stage is unambiguous: `in top-k`, on 35 of 38 clips

| population | SURVIVED | died at `in top-k` |
|---|---|---|
| gold (the gate) | 3 | 17 |
| original references | 0 | 10 |
| shell | 0 | 8 |

The truth-nearest seed exists and is often close — 7–20 px@640 — but ranks **13 to 993**
against `topk = 12`. The three gold clips that survive rank **0, 1 and 7**. Nothing else
gets tried at all.

### 3. The pose prior is NOT what demotes it — second hypothesis refuted

`rank = g · exp(−0.5·maha/6)`, and `autodetect`'s own comment says the learned prior "only
knows elevated framings", with an escape hatch added to the **accept gate** but never to the
**ranking**. That looked like the classic one-caller-patched defect. It is not the cause:

- measured maha of the truth-nearest seed is **1.3–19.8**, far below `PRIOR_MAHA_MAX = 55`,
  so the penalty is mild, not the 100× a saturated prior would give;
- re-ranking by `g` alone promotes the true court into the top-12 on **2 of 38** clips;
- on many clips the prior is actively **helping** — `hillsborough_p02` 193 → 761,
  `am_wingfield_clay` 436 → 754, `sAjkpeRq4P4` 93 → 407 when it is removed.

### 4. Trying more seeds does not help — third hypothesis refuted

| clip | topk=12 | topk=40 | topk=150 | cost |
|---|---|---|---|---|
| `am_hard_utr` | 4/4 true | 4/4 | 4/4 | already accepts |
| `flexi_franz_p01` | 2/4 | 2/4 | 2/4 | 20 s → **155 s** |
| `hillsborough_p02` | 1/4 | 0/4 | **0/4** | 32 s → **229 s** |

**7× the compute for zero gain, and one clip gets worse.** So "raise `topk`" is a measured
dead end — do not re-propose it.

### What the three negatives add up to

The mechanism is circular, and it is a property of the *generator*, not of any threshold:

> The seed lattice's nearest court is 7–20 px@640 from truth while support is counted within
> `tol ≈ 3.8 px@640`. So the truth-nearest seed **cannot fit the paint well enough to rank**,
> and when it is force-tried anyway it refines to something still 12–17 px out — close enough
> to be called correct by the gate, not close enough to beat the alternatives on
> `g·(0.5+0.5·st)`.

Session O measured that the **human court** outranks every lock on these clips. That remains
true, and is not a contradiction: the human court is not a court this search can construct.
**The binding constraint is the precision the generator can reach, not how many candidates it
tries or how it orders them.**

## P3 results — the lines ARE there, and neither way of using them works

### The premise is confirmed, and it is the session's most useful positive

Projecting the human court's four outer lines and looking for the nearest detected line:

| court line | found within 8 px | median distance |
|---|---|---|
| near baseline | 36 / 40 clips | 2.7 px@640 |
| far baseline | 38 / 40 | 2.9 |
| left doubles sideline | 38 / 40 | 1.3 |
| right doubles sideline | 27 / 40 | 4.1 |

**`_detect_lines` is finding the court.** The information is in the mask and in the Hough
output. Every failure in this session is downstream of that.

### P3a — build the quad from the lines: WRONG IN PRINCIPLE, not mis-tuned

Choosing two "baseline" lines and two "sideline" lines requires splitting the detected
lines into two families by direction. **Under perspective the two doubles sidelines
converge toward their vanishing point, so they are not parallel in the image and do not
form an angular cluster.** Measured on `am_hard_utr`: the split put 24 of 26 lines in one
family while both true sidelines sat in the detected set at 0.1 and 2.2 px. Replacing the
fixed 45° threshold with parameter-free double-angle clustering improved it and did not fix
it — because the premise, not the parameter, is wrong. Best constructed quad: **68–256 px**
from truth against a lattice that manages 7–20.

### P3b — snap a near-correct court onto the lines: INCONSISTENT ASSIGNMENT

Sidesteps the grouping problem — a candidate already knows which projected line is its left
sideline, so each model line looks up its own nearest real line. It fails for a different
reason: **matching the four lines independently lets them pick a mutually inconsistent
set**, and intersecting an inconsistent set produces a wildly wrong quad.

| | seed | after `refine_homography_bounded` | after snap |
|---|---|---|---|
| median distance from truth | 9.8 px | **8.4** | 70.5 |

Tightening the match tolerance from 12 px@640 to 4 does not rescue it — it just makes the
snap refuse and fall back (median 10.0, i.e. the seed unchanged), winning on 1 of 5 clips.

### What the correct version would require

Joint line-to-model correspondence: solving the assignment **and** the homography together,
rather than matching each line independently — the combinatorial court-model calibration
Farin's work is built around, and the setting cross-ratio screening was deferred for. That
is a real build, not a session step, and nothing in this session should be read as having
tested it.

---

## Conclusion — the stopping rule applies

Every branch pre-registered in this brief has been measured and none survives:

| branch | result |
|---|---|
| reach (the brief's own mechanism) | refuted — 31/38 already in reach |
| the pose-prior weight in the ranking | refuted — promotes 2/38, often harmful |
| `topk` | refuted — no gain, one clip worse, 7× compute |
| P3a line-construction | fails; wrong in principle under perspective |
| P3b line-snapping | fails; independent matching is inconsistent |

**Court auto-detection closes again**, but with a far sharper characterisation than the last
two closures had:

> The detector finds the court's lines. It cannot assemble them into the court, because
> every candidate it can construct comes off a 5-parameter lattice whose nearest point is
> 7–20 px@640 from truth, and its refiner walks away from truth as often as toward it. The
> scoring criteria are not implicated — Session O measured them recognising the correct
> court on 19 of 20 clips.

The correct output is the documented refusal path plus camera guidance, not a fourth
reopening. The one item still worth shipping on its own evidence is **normalising
`max_move_px` to 640-equivalent** — it is an exact no-op on all 20 gold clips and fixes the
7 genuinely-out-of-reach ones — and it has not yet been run through the full gate.

## The honest gap

The shell evidence is 5 venues and the clay evidence is essentially one club. And the reach
finding above is measured against the coarse grid alone — P1 exists precisely because that
is not yet the whole seed set.
