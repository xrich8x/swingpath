# The innovation gate's noise model: is `meas_var` miscalibrated, and does it matter?

> Assessed 2026-09-10 by **researcher**, on the founder's brief to attack `smooth_forecast`'s
> innovation gate — the largest single speed-coverage cost (**−11.0 / −8.1 pts** under
> TrackNet, v1's detector, vs suppression's −5.2 / −4.4).
>
> **NOTHING WAS RUN.** No code was written, read-only. Every number below is either quoted
> from an existing evidence file (cited inline) or derived by arithmetic from constants read
> out of `backend/swingvision/ball.py`. Derived numbers are labelled DERIVED and carry a
> confidence. **No implementation is designed here** — that is backend-dev's run.

---

## 1. The family verdict

# The R-calibration line is INSIDE the barred family. It is dead.

**The specific reason, in one sentence:** at the moment a detection is judged, the
innovation covariance `S` is dominated by `R`, so multiplying `meas_var` by *k* multiplies
the accept radius by ~√*k* and changes nothing else about the decision — it is
arithmetically a `gate_chi2` sweep wearing different units, i.e. exactly the "move a
threshold to admit more of both real and false" move that `reset_after`, `max_gap_s`, the
`blocked` mask and the depth-aware-Q reference all already are; and the population it would
admit from has already been counted and is **21 real / 28 ghost (0.75 : 1)**, which is
below every bar this family has ever been held to.

I was asked to confirm or refute the lead's reading rather than agree with it. I **confirm**
the characterisation of the barred family (re-admit or widen) and I **refute** two of the
three supporting arguments offered for the R line. Five legs, in order of how load-bearing
they are:

### Leg 1 — the separation argument breaks on the WRONG POPULATION. This is the decisive one.

The brief argues: *"Session I measured all 19 chain false locks sitting 208–829 px off the
track … ghosts at 208+ px still cannot enter."*

**Those 19 are chain false locks — the ghosts that SURVIVED the whole chain and reached the
rendered output. They are not the gate's rejects.** The gate's reject population has been
measured directly, in
[smoother-gate-backward-readmit-separation.md](smoother-gate-backward-readmit-separation.md) §5,
and its ghosts sit at **24.0, 30.3, 49.8 and 386.2 px** from the human click — three of the
four squarely inside the 35–45 px radius the brief proposes to widen to. The 208–829 px
figure describes a different, more extreme sub-population, selected by the property of
having survived. Using it to bound what a widened gate would admit is a population swap.

**And the census caps the exchange rate before any tuning.** The same file, §3, adjudicates
the lost-rejection population against human gold clicks on three clips:

| clip | real rejects | ghost rejects |
|---|---|---|
| `am_hard_utr` | 9 | 9 |
| `yt_match40` | 6 | 7 |
| `yt_rally2` | 6 | 12 |
| **pooled** | **21** | **28** |

**Admit every rejection the gate has ever made and the exchange rate is 0.75 : 1.** That is a
ceiling, not an estimate — no choice of *k*, however principled, can exceed it. Against this
family's own bars it fails by 4× (the ≥3:1 pre-registered backward-readmit bar) to 9× (the
~7:1 structural rate the `blocked` mask and the `max_gap_s` sweep independently measured).
Confidence **0.92**; the residual doubt is whether the adjudicated frames are representative,
and the bias runs the *wrong way for the R line* — gold sets are ball-frame-heavy (175–258
ball vs 24–53 no-ball frames per clip), so the adjudicated rejects are enriched for real
detections and 43% real is if anything generous.

A crude read of the twelve chi²-labelled rejects in §5's table sharpens it further: sorting
by their recorded `chi2`, raising the gate from 13.8 to 20 admits **5 ghosts for 2 reals**,
and to 31 admits **7 ghosts for 4 reals**. **Flagged honestly:** those twelve were selected
by distance-to-RTS-track, a variable §5 shows is ghost-preferring, so this sub-sample is
biased *against* the R line and I do not rest the verdict on it. The pooled 0.75:1 needs no
such caveat.

### Leg 2 — S is dominated by R, so scaling R IS a `gate_chi2` sweep

`ball.py:815–817` builds `Q` from `sigma_jerk = 1.0`, giving `Q[0,0] = σ²/20 = 0.05 px²`
against `R = 25 px²`. With process noise three orders below measurement noise, a
constant-acceleration filter converges toward a least-squares fit and `P[0,0]` becomes small
relative to `R`. Taking the tracking index λ = σ_jerk·T³/σ_meas = 1.0/5 = 0.2, steady-state
`P[0,0]/R` is of order 0.2–0.4, so:

    S = Hm P Hmᵀ + R  ≈  (1.2 to 1.4) × R          DERIVED, confidence 0.80
    accept radius = √(13.8 · S)  ≈  18.6 to 21 px  DERIVED, confidence 0.80

which reproduces the brief's own ~19 px, independently. **R therefore supplies 70–85% of S.**
Scaling `meas_var` by *k* scales `S` by ~*k*, scales `d²` by ~1/*k*, and produces no change in
the *shape* of the decision boundary — only its radius. That is definitionally a widen.

### Leg 3 — brief-candidate (a) is REFUTED, and refuting it strengthens the kill

Candidate (a) was: *"P, not R, is what is stale at rejection time … so calibrating R may
barely move S."* Half right, wrong direction. A stale model's prior is indeed wrong AND
over-confident — but over-confident means `P` is **small**, which is precisely why `S ≈ R`
and why calibrating R moves S almost 1 : 1. The objection, if it had held, would have made
the R line an ineffective widen; its failure makes the R line a maximally effective one.

And there is a second-order cost the brief did not price. `K = P Hmᵀ S⁻¹`: raising `R`
lowers the Kalman gain, so the filter trusts each detection *less* and takes longer to follow
a genuine direction change. **Raising R widens the gate and makes the staleness that causes
the rejections worse.** DERIVED from the code, confidence 0.85.

### Leg 4 — Q and R are different mechanisms, but the Q negative is admissible evidence

The brief asks explicitly whether the depth-aware-Q negative (STATE: *"median-referenced made
false-fire worse, 19 → 27%"*) is the same family. **Judgement: not the same family — a Q
change moves the smoothing bandwidth AND the gate, an R change moves the gate AND the gain,
so a Q result does not automatically transfer.** But they share the *gate-widening
component*, and that component's only measurement in this repo is the one recorded in
`ball.py:686–692`:

> *"half the frames get LOOSER than the tuned value, and that near-court loosening both
> de-smooths the track and lets more junk through the innovation gate (false-fire 19 → 27%)"*
> — while tighten-only (p10 reference) held false-fire flat at 19.2% and bought +1.2 pts of
> far-court hit@10.

That is a **one-sided, measured, in-this-exact-gate** result: loosening cost +7.7 pts of
false-fire at a modest widen factor; tightening cost nothing. It does not by itself bar the R
line, and I do not use it to. It does mean the R line would be re-running the loosening half
of an experiment whose loosening half has already been run once and lost.

### Leg 5 — the only measured localisation errors in the repo are CONSISTENT with σ ≈ 5 px

The brief asks whether anything already measures raw-detection-to-human-click error.
**Answer: no distribution exists anywhere in this repo.** What exists is:

- `tools/eval_model_filters.py:199` — a **binary** at 10.0 px (`math.dist(p, click) <= 10.0`).
  Verified by reading the file. It reports a rate, never a σ.
- ~17 anecdotal per-frame errors scattered across two evidence files. In
  `smoother-gate-backward-readmit-separation.md` §5 the five REAL rejects carry lock errors of
  **3.9, 2.5, 3.4, 4.0 and 0.7 px**. In `bounce-hypothesis-v2-gate.md` the `miss → wrong`
  frames carry raw detections **20–502 px** from the click.

Read together those describe a **mixture**: a well-behaved core at σ ≈ 3–5 px — which is what
`meas_var = 25` already encodes — plus a heavy tail of genuine outliers two orders of
magnitude out. **A mixture is not an underestimated σ, and the correct response to a heavy
tail of real outliers is a tight gate, not a wide one.** This is brief-candidate (c) reaching
the opposite prescription from the one the brief suggested: the residuals are heavy-tailed,
and that is an argument *for* 13.8, not against it. Confidence **0.65** — the five-sample core
is selected (they are the rejects nearest the smoothed track, so biased toward well-localised
ones) and I would move on this readily if the §3 diagnostic showed otherwise.

**Caveat I will not smooth over:** the founder is right that the question has never been
asked. I found **no `gate_chi2` sweep and no `meas_var` sweep** anywhere in STATE's "What has
not worked" (all 78 rows read). The *question* is virgin. It is the *intervention* that is
barred, and it is barred by a census that already exists rather than by precedent.

### What this section does NOT close, and what would disprove it

- If the §3 diagnostic returns a median `d²` on gold-confirmed real accepted frames far above
  the χ²₂ median of 1.386 — say ≥ 4 — then R's **bulk** calibration is wrong by ~3× and Leg 5
  falls. Legs 1–3 would still stand, so the line would still be a widen with a 0.75:1 ceiling,
  but the framing would change from "R is fine" to "R is wrong and fixing it still does not
  pay." **That is the cheapest thing here to falsify** and it comes free with §3.
- If someone produces a reject census on a **larger, differently-sampled** adjudicated
  population that is real-majority, Leg 1 falls and with it the verdict. The existing power is
  thin (49 pooled) and is stated as such in the source.

**Per the brief's instruction the R line stops here, and no R-variant, no `gate_chi2`
variant and no soft-widen variant is proposed anywhere below.** Sections 2–4 answer the
brief's separate standing question — what, outside this family, could move the −11.0 / −8.1
pt cost — and every entry below is checked against a single test: *does it change the
radius the incumbent model accepts?* If yes, it is a widen and it is out.

---

## 2. Candidate mechanisms outside the barred family, ranked

**First, one code-read result that reshapes the whole list, and that kills brief-candidate
(b) without a run.**

`pipeline.py:1460` defines what coverage counts:

    ball_seen = [p is not None and not ball_coasted[i] for i, p in enumerate(ball_px)]

and in `ball.py` every **accepted** detection is emitted (`used[i] = True` →
`accepted_by_seg` → `emit`), while every bridged gap is marked `coasted` and therefore not
counted. Therefore:

> **`D_smooth` (−11.0 / −8.1 pts) IS the gate's rejection rate over span frames, minus the
> frames the `reset_after` re-seed path recovers. It is not a downstream reset cascade.**
> DERIVED from code, confidence 0.85 — no measurement needed, and brief-candidate (b) is
> refuted at zero cost.

That leaves exactly three routes to more coverage: **(i)** widen the gate — dead, §1;
**(ii)** stop counting frames as lost that are not lost; **(iii)** recover rejections into a
*new* segment where a *different* model accepts them. The ranking below follows the brief's
rule: (chance of moving coverage) × (cheapness to falsify).

---

### M1 — Are short interpolated bridges actually unmeasured? Rank 1.

**Mechanism, one sentence.** `seen_frac` excludes every coasted frame on the stated principle
that *"a forecast is a physics guess and not a measurement"* (`ball.py:667–669`), but a gap of
1–2 frames bounded by accepted detections on **both** sides inside **one** segment is
constrained by real measurements at both ends and may be as accurate as a detection — in
which case a measurable share of the −11.0 pts is an accounting rule, not a lost ball.

**Why it separates rather than widens.** It changes no filter behaviour whatsoever: same
gate, same `R`, same `Q`, same `gate_chi2`, same accept radius, same emitted track, same
pixels on screen. It changes only what the coverage statistic counts, and only if a
measurement against **human clicks** says the counted frames are on the ball.

**The hazard, stated loudly because it is the obvious objection.** Redefining a metric to make
its number better is the classic sin, and if this were proposed on aesthetics it would deserve
rejection on sight. It is not: the exclusion rule is an **empirical claim** ("a forecast is not
a measurement") and the repo already computes the number that tests it. Read
`tools/eval_model_filters.py:201–208` — it accumulates `coast_err` and `coast_by_gap`, binned
`"1-2" / "3-5" / "6-9" / "10+"`, as the distance in pixels from each coasted emitted position
to the human click. **That data may already be printed by a tool that has already run.**

**What would falsify it.** `coast_err` for the `"1-2"` bin, pooled over the three TrackNet
arms, must be **≤ 10.0 px median** — the project's own recall radius. If it is above, the
exclusion rule is empirically right, this branch dies in one command, and that is itself
worth knowing. Second, harder gate before anything ships: shots whose coverage crosses 0.5
*only* because short bridges are counted must show speed error against `tools/synth_truth.py`
(rule 11's compliant source) no worse than shots that cross on detections alone.

**Cost to measure.** Possibly zero — inspect existing `eval_model_filters.py` output. Worst
case one re-run of an existing tool on three cached arms, no video decode, no training.

**P(moves coverage) ≈ 0.9** (mechanically certain the number moves; the risk is entirely
legitimacy) × **cheapness ≈ 0.95**. Ranked 1 by the brief's own rule, and I rank it there
even though it is an accounting result rather than an algorithmic one, because that is what
the rule says.

---

### M2 — Rejection-run COHERENCE: the reset counter cannot tell a bounce from a fleck. Rank 2.

**Mechanism, one sentence.** `rej` (`ball.py:868`) increments on **every** gate rejection
alike, and when it trips `reset_after = 3` the code re-seeds the new segment at the **current**
frame (`ball.py:965–970`), silently discarding the `reset_after − 1 = 2` earlier rejections —
so replace the counter with a coherence test: rejections that are mutually consistent with
*each other* under a fresh constant-acceleration fit are a direction change and should seed
the new segment from the run's **first** frame, while a rejection inconsistent with its
neighbours is junk and should not increment `rej` at all.

**Why it separates rather than widens.** The accept radius, `gate_chi2`, `R` and `Q` are all
untouched, and nothing is ever re-judged against the incumbent model. Admission requires
**≥ 2 rejections agreeing with each other under a new model**. This project has already
measured the ghost signature that fails such a test: **all 19 chain false locks have
`run_len = 1`** (`docs/evidence/9-solid-ghost-balls.md`, carried in researcher memory). A
single-frame ghost cannot form a coherent run, so the ghost population is excluded by its own
measured property rather than by a chosen threshold.

**Why it escapes the §5 confound that killed the backward re-admit.** That negative closed
*"using the smoother's backward pass to re-admit detections the forward gate rejected"*, and
§5's mechanism is general: *any statistic derived from the incumbent motion model is a second
look at the evidence the first look got wrong.* Coherence is **not** derived from the
incumbent model — it is fit to the rejections themselves. That is a different model, not a
second look at the same one. **I flag the residual risk honestly: this is a fifth idea in a
family with four measured negatives. Its prior should be low and its bar high.**

**Second, independent win the brief did not ask about.** Today an isolated junk lock can trip
a reset, and the reset path then **seeds the filter on that lock** (`used[i] = True`,
`ball.py:970`) — so one ghost simultaneously destroys a converged model and gets emitted.
Not counting incoherent rejections fixes a coverage bug and a ghost bug with the same change.

**What would falsify it.** On the 49 pooled adjudicated rejects, the contingency table
*consecutive-run-length (1 vs ≥2)* × *real / ghost*. Pre-register: the real fraction in runs
of ≥2 must exceed the real fraction in runs of 1 by **≥ 25 percentage points on ≥ 2 of 3
clips**, with a seeded shuffled-label null control (1000 draws) reached by ≤ 5%. If run
length does not separate, the mechanism is dead before any code exists.

**A second, independent kill it must survive.** The prize is bounded above by
(number of resets) × 2 frames. **Nobody has ever counted the resets.** If they are rare the
mechanism is inert regardless of how well it separates. §3 prices this in the same pass —
and it is the risk most likely to end this candidate.

**Cost.** One instrumented pass over three cached arms (§3). **P(moves coverage) ≈ 0.35** ×
**cheapness ≈ 0.7**.

---

### M3 — DO NOT BUILD: three ideas that look outside the family and are not.

**(a) A robust / Student-t innovation gate.** Named in the brief as candidate (c). It is a
**soft widen** — it inflates the effective radius for every frame, uniformly, and therefore
draws from the same 21-real / 28-ghost pool at the same 0.75:1 ceiling. Worse, Leg 5 argues
the tail is made of *genuine* outliers at 20–502 px, and a heavy-tailed likelihood is
precisely an instruction to tolerate those. `bounce-hypothesis-v2-gate.md` already names what
that produces: `wrong` frames — the emitted position lands 20–502 px off a real ball while
recall and ghost counts barely notice. Do not build.

**(b) Speed- or depth-referenced process noise.** A near-repeat of STATE's *"Depth-aware
Kalman process noise — median-referenced made false-fire worse (19 → 27%)"*. Image speed and
court depth are strongly correlated, so a speed reference is the same experiment under a
different name, and it is a widen wherever it loosens. Rule 3. Do not build.

**(c) Cross-detector agreement as a re-admit signal.** Explicitly barred by STATE row
`smoother-gate-backward-readmit-separation`, which names the cross-detector variant in
advance: *"including the cross-detector variant, which the mechanism above makes tempting
and which this row bars."* Also disqualified independently on A13 grounds — running two ball
detectors doubles the only per-frame ANE cost in the pipeline. Do not build.

---

### M4 — Where the evidence actually points, out of this brief's scope. Rank 3.

`suppress_false_locks` costs −5.2 / −4.4 pts, and the pipeline's own comment at
`pipeline.py:1441–1444` says of it: *"the gaps suppression opens are mostly gaps where it
deleted a REAL far-court ball — it is already known to cost 5–10 pts of recall."* A lock
deleted there never reaches the gate: it costs coverage directly, cannot trip a reset, and
cannot be recovered by anything downstream. That is a stage whose own documentation records
it deleting real balls, and it is the stage the founder's evidence file pointed at when it
said *"attacking the −11.0 / −8.1 pt cost now means attacking a different stage."* Named for
completeness; not costed, not scoped here.

### iOS / A13 feasibility of M1, M2 and M4 — one line, so nobody assumes it binds

None of them adds an inference pass. `smooth_forecast` is a 6-state Kalman recursion in
NumPy running per **detection**, not per pixel — CPU work measured in microseconds per frame,
on the order of 10⁻⁵ of the ANE budget the ball detector consumes. **Compute is not a
constraint on any candidate in this file**, at any thermal state, on an A13. Confidence 0.9.

---

## 3. The diagnostic that must run before any build

**One instrumented pass, three clips, no video decode, no training, no fix authorised.**

The brief's proposed diagnostic is right in kind and has one defect I want corrected before
it runs.

> **The defect: you cannot estimate a 99.9th percentile from ~200 samples.** The brief
> proposes comparing the empirical `d²` distribution's 99.9th percentile against 13.8. One
> expected exceedance at p = 0.999 requires ≥ 1000 clean samples; the gold sets carry
> **175–258 ball clicks per clip**, so that percentile is unestimable and whatever number came
> back would be an artefact of the largest one or two points — which are exactly the mixture
> contamination Leg 5 describes. **Use the BULK instead: the median and p90 of `d²` on
> gold-confirmed real accepted frames.** χ²₂ has median **1.386** and p90 **4.605**, both
> estimable from ~50 samples. If the empirical median is ≈1.4 the noise model's core is
> correct; if it is ≈4 then `R` is understated by roughly 3× in the bulk. That is sharper,
> cheaper and actually answerable.

> **A second correction: `d²` on ACCEPTED frames is truncated at 13.8 by construction.**
> The pass must record `d²` for **every** frame carrying a detection, accepted or rejected,
> or the distribution is censored and the comparison is meaningless.

**What the pass emits, one row per frame carrying a detection:**

| column | answers |
|---|---|
| `d2` (recorded before the comparison at `ball.py:863`) | the bulk-calibration question above — is the statistic χ²₂? |
| `S[0,0]`, `S[1,1]`, `P[0,0]` | **Leg 2 becomes measured instead of DERIVED** — what fraction of S is R? |
| `accepted`, `rej_run_len`, `run_tripped_reset` | **M2's falsifier**: the run-length × real/ghost contingency |
| `seg_id`, and a clip-level reset count | **M2's prize ceiling** — resets × 2 frames. The most likely kill. |
| `in_span` (frame inside a hit→landing span) | confirms the code-read claim that D_smooth is the rejection rate over span frames |
| `gold_label` (real / ghost / unadjudicated) | the only ground truth in the pass |

**Named artefacts, and exactly how far I verified each.** Glob returned "no files found" for
every pattern I tried in this session, including paths I had just read links to, so **Glob is
non-functional here (T25) and absence of a Glob match is a claim about the tool, not the
repo.** Everything below was verified by `Read` or is cited from a named source:

- `tools/eval_speed_coverage_chain.py` — **VERIFIED by Read.** Produces the stage ladder and
  the `seen_frac` means. Its docstring's `--json` example writes a **flat** file
  `data/output/speed_coverage_amhard_tracknet.json`, whereas
  `speed-coverage-is-chain-shaped-and-the.md` cites a **directory**
  `data/output/speed_coverage/*.json`. **I could not reconcile these; backend-dev must check
  the layout on disk rather than assume either.**
- `tools/eval_model_filters.py` — **VERIFIED by Read.** Recall is `dist(p, click) <= 10.0`
  against human gold clicks (`:199`); it already accumulates `coast_err`, `coast_err_far` and
  `coast_by_gap` binned `"1-2"/"3-5"/"6-9"/"10+"` (`:201–208`) — **this is M1's falsifier
  data.**
- `tools/_goldset.py` — exists; imported at `tools/eval_speed_coverage_chain.py:62`.
- `data/output/detector_ab/{am_hard_utr,yt_match40,yt_rally2}.tracknet.perception.json` —
  cited with exact filenames in `smoother-gate-backward-readmit-separation.md` §6. **Not
  opened by me.** These are the one-variable TrackNet arms and are the only correct input.
- `data/gold/<clip>.labels.json` — same source, TEST-only, one-way, read via `_goldset`.
- `backend/tests/test_speed_coverage_span_sink.py` — cited; not opened by me.

**Instrumentation method, mandated not suggested:** the source-transform route the
backward-readmit run already proved — `inspect.getsource` → two textual insertions → `exec`,
with an in-run assertion that the instrumented copy and the shipped `B.smooth_forecast`
return identical output on identical input. **`backend/swingvision/ball.py` must not be
modified on disk.** That run recorded `identical: true` on all three clips.

**Gold-leak posture:** this pass trains nothing, fits nothing and writes no label file. Gold
is read one-way as TEST. No guard is bypassed. **No number in this pass is scored against any
model's own output** — `d²` and `S` are internal filter state, reported as such, and the only
labels are human clicks.

**Pre-registered kill conditions on the diagnostic itself:**

- **K1.** If median `d²` on gold-real accepted frames ∈ **[0.9, 2.2]** (χ²₂ median 1.386,
  ±~×1.6), the bulk noise model is calibrated, Leg 5 is confirmed, and **the R premise is
  dead outright** — no R arm ever runs.
- **K2.** If the M2 contingency shows < 25 pp enrichment on ≥ 2 of 3 clips, or the seeded
  shuffled-label null (1000 draws) is reached by > 5%, **M2 dies before any code.**
- **K3.** If clip-level resets × 2 < 1.0 pt of `seen_frac`, **M2 is inert regardless of K2**
  and dies anyway.

---

## 4. The pre-registered bar — written before any run

**Scope.** This bar governs any arm built on M1 or M2. **It is not written for an R arm; §1
bars one.** Clips: `am_hard_utr`, `yt_match40`, `yt_rally2` — the three that have a
one-variable TrackNet arm in `detector_ab/` *and* human gold clicks. All arms TrackNet, v1's
detector. `--seed` on both arms, `recipe_stamp` on any checkpoint.

### The bar is counted on MEAN `seen_frac`, not on shots crossing 0.5. Here is why.

`does-seen-frac-predict-speed-error.md` measured the 0.5 constant against synth truth over
10 seeds: **accept-precision margin over base rate +4.96 / +3.11 points against a
pre-registered ≥10-point bar, clearing it on 0 of 10 seeds**, and **33–38% of what it refuses
is nonetheless accurate**. A count of shots crossing that line is therefore a count of
crossings of a boundary that does not separate accurate speeds from inaccurate ones — a
threshold applied to a threshold, inheriting the inner one's failure and adding quantisation
noise on top (the published probe already showed a ±2-shot reproduction wobble at tolerance
on `am_hard_utr`). A **mean** is a monotone summary of the underlying quantity and does not
inherit the 0.5 line's failure. **Bar on the mean. Report the shot count alongside as
context, never as a pass condition.**

### Bars

| id | condition | measured against |
|---|---|---|
| **C — coverage** | Mean `seen_frac` at the `+smooth_forecast` stage rises by **≥ +2.0 pts on ≥ 2 of 3 clips**, and falls by **> 0.5 pts on none**. | **The tracker's own post-chain output**, over hit→landing spans the tracker's own events defined. A coverage statistic, **not** an accuracy one. `tools/eval_speed_coverage_chain.py`. |
| **G — ghost guard** | Ghost fires **rise on zero of 3 clips**, and the pooled total does not rise. | **Human gold clicks**, `data/gold/<clip>.labels.json`, via `tools/eval_model_filters.py`. |
| **R — recall guard** | Pooled recall@10 px falls by **≤ 1.0 pt**, and by **≤ 2.0 pts on any single clip**. | **Human gold clicks**, `dist(emitted, click) ≤ 10.0 px`, `tools/eval_model_filters.py:199`. |
| **W — mislocalisation guard** | `wrong` (a human-clicked ball frame whose emitted position is > 10 px off) **rises on ≤ 1 of 3 clips**. | **Human gold clicks**, same tool. |
| **P — replication** | Every bar evaluated on all 3 clips. An arm that wins on one clip and loses on another is a **FAIL**, not "promising". | — |

**Baselines.** `am_hard_utr` 51.1 and `yt_match40` 55.0 at the smoother stage (TrackNet arms,
`speed-coverage-is-chain-shaped-and-the.md`). **`yt_rally2` has no published smoother-stage
mean** and must be baselined in the same run, before the arm, or it is not a bar.

### Why each number is what it is, so it cannot be argued to a different value later

- **C at +2.0 pts** — the stage costs 11.0 / 8.1, so +2.0 claims ~20% of the prize. It sits
  10× outside the probe's demonstrated ±0.2 pt reproduction band, so it cannot be reached by
  measurement noise, and it is low enough that a real partial fix is not thrown away.
- **G at zero tolerance, not a ratio** — this family's last four attempts *passed* separation
  bars and died elsewhere. `bounce_hypothesis` hit **9.00 : 1 against a > 7 bar** and still
  failed, on ghosts rising on 5 of 10 clips and on replication. **A ratio bar has already been
  demonstrated here not to protect the product.** So G is absolute.
- **R exists to make C non-gameable, and this is the load-bearing guard.** `seen_frac` counts
  an emitted frame without checking whether it is on the ball. Every widen therefore buys C
  *mechanically*, by admitting locks 24–50 px off a click — brief-candidate (d), and stronger
  than the brief put it. R is the only bar that catches that, and any arm that moves C without
  holding R has bought the number and not the product.
- **W** — v2's named failure mode was mislocalisation on ball frames, which slipped past
  recall-and-ghost alone until a `wrong` bar (P7) caught it. Cheap; keep it.
- **P** — two of this family's four negatives died on **replication** (`reset_after`,
  `max_gap_s` at 60 fps), and STATE's own note reads *"the optimal gap policy scales with
  detection density; never tune it on one clip."*

### Power, stated in advance rather than after a result

The three clips carry **53 / 24 / 26 = 103** human-marked no-ball frames, against the **74
per clip** the product gate uses on the 10-clip pool. **A ghost movement of ±1 on a single
clip is inside sampling noise (T09)** — which is why G is stated pooled as well as per-clip,
and why a single-clip ghost result must not be quoted alone.

### T23

`yt_match40`'s calibration is known wrong (manual+snap, 9.1 px reprojection). **Bar C on that
clip inherits it**, because hit→landing spans come from events that depend on court geometry.
Bars G, R and W do **not** — they are pixel distances to human clicks in image space. **If
the verdict turns on `yt_match40`'s C alone, it is not a verdict.**

### What a PASS authorises

**A second run, and nothing else.** Not a shipped default, not a STATE row claiming a product
gain. And the honest limit that bounds every outcome here:

> **There is no measurement in this repo that a higher smoother-stage `seen_frac` produces a
> more accurate speed.** The 0.5 gate it feeds is measured only weakly predictive
> (+4.96 / +3.11 against a ≥10-pt bar, 0 of 10 seeds), so **the size of the prize behind the
> −11.0 / −8.1 pts is still not established.** The only rule-11-compliant instrument that
> could establish it is `tools/synth_truth.py`. Until someone runs that, every number in this
> file — including a clean PASS on C — moves a statistic whose product value is assumed, not
> demonstrated. That is the most important sentence in this document and it is the easiest one
> to skip.

### Nothing in this bar is measured against

A scoreboard, a HUD, a burned-in graphic, SwingVision's MPH panel, or any model's own output
(rules 1 and 11).

---

## 5. The §3 diagnostic, RUN — K1 / K2 / K3 and M1's falsifier adjudicated

> Measurement run 2026-09-10 by **backend-dev** against the kill conditions §3 pre-registered
> and §4's bar, both written before anything ran. **No bar below was restated, retuned or
> softened after seeing a number.**
>
> **This run authorised no fix.** `backend/swingvision/ball.py` was NOT modified on disk,
> nothing was shipped, no default was changed, M1 and M2 were not implemented, and
> `docs/STATE.md` was not touched.

**What every number here is measured against, in one sentence:** `d²`, `S`, `P` and the reset
counts are the Kalman filter's OWN internal state, reported as internal state and carrying no
accuracy claim; every `real` / `ghost` label is a **human gold click** in
`data/gold/<clip>.labels.json` (real = the emitted or rejected position within 10.0 px of the
click, the project's own recall criterion); `seen_frac` is the tracker's own coverage over the
tracker's own hit→landing spans and is a COVERAGE statistic, not an accuracy one. **Nothing
here is scored against a model's own output, a scoreboard, a HUD or any burned-in graphic**
(rules 1 and 11).

### 5.0 Verdict table

| id | what it tests | bar | measured | verdict |
|---|---|---|---|---|
| **K1** | is `d²` on gold-real accepted frames χ²₂? | median ∈ **[0.9, 2.2]** | pooled **0.113** (n=291) | **BAND NOT MET — miss is ~12× LOW.** See 5.2: the R premise dies anyway, by the opposite sign |
| **K2** | does rejection-run length separate real from ghost? | ≥ **25 pp** on ≥ 2 of 3 clips **and** seeded null p ≤ 0.05 | **1 of 3** clips ≥ 25 pp; null p = **0.105 / 0.589 / 0.585** | **KILL. M2 dies before any code.** |
| **K3** | is M2's prize big enough to matter? | ≥ **1.0 pt** of `seen_frac` | **+6.49 / +4.93 / +3.45 pts** | **PASS** — the most-likely kill did not fire. Moot for M2, which K2 already killed |
| **M1** | are 1–2 frame bridges as good as detections? | `"1-2"` bin median ≤ **10.0 px** | pooled **19.90 px** (n=16) | **KILL. The `seen_frac` coast-exclusion rule is empirically RIGHT.** |

**Both surviving candidates in §2 are dead.** M1 is killed by its own pre-registered falsifier,
M2 by K2. Everything still alive after this run is listed in 5.8.

### 5.1 Instrumentation identity — the assertion, and an unplanned second one that passed

Method as mandated: `inspect.getsource(B.smooth_forecast)` → three textual insertions (one
splitting the gate line at `ball.py:863` to capture `d²`, `S`, `P` and `R` **before** the
comparison; one at the reset check at `:965` to capture the `rej` / `miss` counters and whether
the reset tripped; one before the RTS loop at `:972` to export `used` / `seg_id`) → `compile`
→ `exec` in a namespace cloned from the `ball` module. All three anchors were asserted unique
in the source before substitution. `backend/swingvision/ball.py` was never opened for writing
(sha256 prefix `171932521dc3e796`, unchanged).

Every run calls the instrumented copy AND the shipped `B.smooth_forecast` on identical input
and compares all three returned lists:

    instrumented == shipped:  chain A (no court gate) True   chain B (full shipped) True   [x3 clips]

**`identical: true` on all three clips on BOTH chains — six of six.** Matching the backward-
readmit run's result.

**A second, stronger check nobody asked for.** §5 of
[smoother-gate-backward-readmit-separation.md](smoother-gate-backward-readmit-separation.md)
published a lost-rejection census from a different script three weeks earlier. This run
reproduces it **exactly**:

| clip | §5 published (real / ghost) | this run (real / ghost) | lost rejects |
|---|---|---|---|
| `am_hard_utr` | 9 / 9 | **9 / 9** | 18 = 18 |
| `yt_match40` | 6 / 7 | **6 / 7** | 13 = 13 |
| `yt_rally2` | 6 / 12 | **6 / 12** | 18 = 18 |

Three independent counts, three exact matches. The instrumentation is measuring the population
the pre-registration is about.

### 5.2 K1 — the R premise. The band is NOT met, and the miss kills the R line harder than a hit would have.

Measured against human gold clicks (`real` = within 10.0 px) on frames the gate ACCEPTED, as
§3 specifies. χ²₂ reference: median **1.386**, p90 **4.605**. Per §3's instruction **no 99.9th
percentile is estimated** — 32–153 samples per clip cannot support one.

| clip | n | median `d²` | p90 `d²` | in [0.9, 2.2]? |
|---|---|---|---|---|
| `am_hard_utr` | 32 | **0.265** | 6.764 | no — 5.2× low |
| `yt_match40` | 106 | **0.122** | 6.341 | no — 11.4× low |
| `yt_rally2` | 153 | **0.104** | 2.328 | no — 13.3× low |
| **pooled** | **291** | **0.113** | **4.776** | **no — 12.3× low** |

**Verdict: the pre-registered band [0.9, 2.2] is NOT met, on 0 of 3 clips and not pooled. K1
does not fire as written.** A failed bar stays failed and I am not moving it.

**But the direction of the miss is the whole result, and it is not a direction §3 anticipated.**
§3 named two outcomes: median ≈ 1.4 (calibrated, R premise dead) or median ≥ 4 (R understated
~3×, Leg 5 falls). The measured median is **an order of magnitude BELOW** χ²₂. The innovations
are far *smaller* than the filter's own `S` predicts, which means **`S` is over-stated, not
under-stated.** The R premise was *"`meas_var` may be too small, so raise it"* — raising
`meas_var` raises `S`, lowers `d²`, and moves the statistic **further** from calibration. **The
R premise is dead, by the opposite sign to the one §1 argued and to the one the founder's brief
proposed.**

**The censoring correction §3 demanded, applied.** `d²` on accepted frames is truncated at 13.8
by construction, so the same statistic is reported on **every** gold-real frame carrying a
detection, accepted **and** rejected — the uncensored distribution:

| clip | n (uncensored) | median | p90 |
|---|---|---|---|
| `am_hard_utr` | 41 | **1.033** | 37.799 |
| `yt_match40` | 112 | **0.138** | 11.431 |
| `yt_rally2` | 159 | **0.113** | 6.906 |

Censoring matters on `am_hard_utr` (0.265 → 1.033, which *is* inside the band) and barely on
the other two. **Recorded, not used to move the verdict:** the pre-registration says
*accepted*, so the accepted row is the verdict row. What the pair shows is that `am_hard_utr`'s
real detections are bimodal — a very tight accepted core plus 9 rejected reals sitting at a
median `d²` of **37.8** — and that is a mixture, not a mis-set σ.

**The shape confirms Leg 5's mixture reading and its prescription.** Pooled median is 12.3×
below χ²₂ while pooled p90 (**4.776**) is within 4% of χ²₂'s p90 (4.605). A distribution whose
median is 12× low and whose p90 is exactly right is **far more peaked and far heavier-tailed
than χ²₂** — a tight core plus genuine outliers, which is what Leg 5 described from 17
anecdotes and what this measures on 291 samples. Leg 5's *prescription* — the correct response
to a heavy tail of real outliers is a tight gate, not a wide one — is strengthened. Leg 5's
*premise*, that `meas_var = 25` "already encodes" the core correctly, is **not** confirmed: the
core is ~3× tighter in σ than the model says.

### 5.3 Leg 2 was DERIVED at confidence 0.80. It is now measured, and it is REFUTED.

§3 asked for `S[0,0]`, `S[1,1]` and `P[0,0]` so that *"Leg 2 becomes measured instead of
DERIVED"*. Leg 2 derived `S ≈ (1.2 to 1.4) × R`, i.e. **R supplies 70–85% of S**, and an accept
radius of 18.6–21 px. Measured over every gate-tested frame (n = 8,157 / 5,834 / 777):

| clip | `R[0,0]` | median `S[0,0]` | median **R/S** | p25 → p90 R/S | max R/S | median accept radius √(13.8·S₀₀) |
|---|---|---|---|---|---|---|
| `am_hard_utr` (1080p) | 56.25 | 300.6 | **0.187** | 0.100 → 0.310 | 0.310 | **64.4 px** |
| `yt_match40` (720p) | 25.0 | 97.4 | **0.257** | 0.100 → 0.309 | 0.310 | **36.7 px** |
| `yt_rally2` (720p) | 25.0 | 82.4 | **0.304** | 0.135 → 0.310 | 0.310 | **33.7 px** |

**R supplies 19–30% of S at the median and never more than 31%. `S` is dominated by `P`, not by
`R`.** Leg 2 is refuted, and with it Leg 3 — brief-candidate (a), *"P, not R, is what is stale
at rejection time … so calibrating R may barely move S"*, which §1 refuted, is **correct as
measured**. Since `S = HPHᵀ + R`, scaling `meas_var` by *k* scales `S` by
`1 + (k − 1)·(R/S)` — with R/S ≈ 0.19–0.30 that is roughly a **quarter** of the multiplier the
R line assumed (to first order, before `P`'s own weak dependence on `R` through the gain).
It is a weaker lever than §1 believed, not a stronger one. **This does not rescue the R line**
— §1's Leg 1 census (0.75 : 1 real-to-ghost ceiling over the entire reject population) is a
count, not a derivation, and it stands untouched. It does mean the R line was mischaracterised
as *"a maximally effective widen"* when it is in fact a weak one.

**The accept radius is ~1.8× wider than anyone in this file believed.** The brief and Leg 2
both said ~19 px. Measured median is **33.7–64.4 px**. That matters for Leg 1's reading of §5:
the four ghost rejects at **24.0, 30.3, 49.8 and 386.2 px** from the human click are, three of
them, *inside the median accept radius already*. They were not rejected for being far away in
pixels — they were rejected at moments when `P` happened to be tight, or with the innovation
pointing the wrong way. That is a different failure mode from "the radius is too small", and
it is one more reason no radius change addresses this stage.

### 5.4 K2 — M2 does not separate. KILL.

Population, exactly as §5 defined it and as reproduced in 5.1: gate rejections that stay
**lost** (the reset path's re-seeds are excluded — the shipped code already keeps those),
restricted to frames a human adjudicated. Contingency: consecutive-rejection-run-length
**1 vs ≥ 2** × **real / ghost**, where the run is defined exactly as the shipped `rej` counter
sees it (starts at `rej == 1`, broken by an acceptance or a reset).

| clip | runs of 1: real / n | runs of ≥2: real / n | frac(1) | frac(≥2) | **enrichment** | seeded null **p** |
|---|---|---|---|---|---|---|
| `am_hard_utr` | 0 / 3 | 9 / 15 | 0.00 | 0.60 | **+60.0 pp** | **0.105** |
| `yt_match40` | 2 / 5 | 4 / 8 | 0.40 | 0.50 | **+10.0 pp** | **0.589** |
| `yt_rally2` | 1 / 4 | 5 / 14 | 0.25 | 0.357 | **+10.7 pp** | **0.585** |
| **pooled (49)** | **3 / 12** | **18 / 37** | 0.25 | 0.486 | **+23.6 pp** | **0.135** |

Null control: labels permuted within the clip's lost-reject population, statistic = the same
enrichment in percentage points, **1000 draws, `random.Random(20260910)`**, p = fraction of
draws reaching or beating the observed enrichment. Identical on chain A and chain B.

**Both legs of K2 fail.**

1. **Separation.** ≥ 25 pp was required on ≥ 2 of 3 clips. It is reached on **1 of 3**.
   `yt_match40` (+10.0) and `yt_rally2` (+10.7) are less than half the bar. Pooled (+23.6) does
   not reach it either, and pooled was never the condition.
2. **The null control.** Not one clip reaches p ≤ 0.05. `am_hard_utr`'s +60.0 pp — the only
   clip that clears the separation bar — is reached by **10.5% of random label permutations**,
   because it rests on a runs-of-1 cell containing **three** rejections. Pooled p = 0.135.

**M2 is dead before any code exists**, which is the outcome §3 pre-registered for exactly this
result. Per rule 3 and §2's own warning (*"this is a fifth idea in a family with four measured
negatives"*), this is now the **fifth** measured negative in the smoother-gate family.

**Rule 10 — inspect the rejects, not what the filter kept.** The mechanism M2 rested on was
`9-solid-ghost-balls.md`'s finding that all 19 chain false locks have `run_len = 1`. Measured
here, **the ghosts at the gate do not behave like the ghosts at the end of the chain**: 19 of
the 28 pooled ghost rejects (68%) sit in runs of ≥ 2 and would be admitted by a coherence rule,
not excluded by it. The 19 chain false locks are the ghosts that SURVIVED — the same population
swap §1's Leg 1 identified in the 208–829 px argument, now measured on the run-length variable
too. **A property measured on survivors did not transfer to the gate's rejects.**

**Power, stated with the claim (T09).** The ghost counts are 9 / 7 / 12 per clip against
**53 / 24 / 26** human-marked no-ball frames — well under the 74-per-clip the product gate uses.
A ±1 ghost movement on any single clip is inside sampling noise. This does not rescue K2: the
failure is not "too few to tell", it is that two clips land at +10 pp with p ≈ 0.59, i.e.
**indistinguishable from shuffled labels**, and the third's win is driven by a 3-sample cell.

### 5.5 K3 — nobody had ever counted the resets. Here they are, and M2's prize is NOT small.

§2 rated this *"the risk most likely to end this candidate"*. **It does not.**

Method, and it is stronger than the `resets × 2 frames` proxy §3 proposed: for every reset
triggered by `rej >= reset_after`, the `reset_after − 1` **earlier** rejections in that run are
the frames the current code discards. Those exact frames are flipped to `seen` in the
`ball_seen` mask and `pipeline._build_match_from_events` is re-run over the **same fixed
hit→landing spans**, so the answer comes back in the units the bar is written in — points of
**mean `seen_frac`** — rather than in an assumed frame count.

| clip | resets total | by `rej` | by `miss` | frames discarded | base mean `seen_frac` | ceiling | **points** |
|---|---|---|---|---|---|---|---|
| `am_hard_utr` | 630 | 457 | 173 | 902 | 51.06% | 57.55% | **+6.49** |
| `yt_match40` | 384 | 246 | 138 | 479 | 54.79% | 59.71% | **+4.93** |
| `yt_rally2` | 34 | 24 | 10 | 47 | 67.96% | 71.41% | **+3.45** |

**All three clear 1.0 pt by 3.5× to 6.5×. K3 PASSES.** `am_hard_utr`'s 51.06 and
`yt_match40`'s 54.79 reproduce the published smoother-stage baselines of 51.1 and 55.0 to
within 0.05 pt, which is a third independent check on this harness. **`yt_rally2`'s
smoother-stage mean has never been published; it is 67.96% (10 shots), baselined here as §4
required.**

Read plainly: **the reset path silently discards a ceiling worth roughly 40–60% of the entire
`−11.0 / −8.1` pt cost of this stage.** That is a real, previously uncounted quantity, and it
is the most useful number this run produced. **It is a ceiling, not a prize** — it assumes
every discarded rejection is recovered for free and correctly, and K2 has just shown that run
length cannot tell which of them are real (18 of 37 are ghosts). **This does not resurrect M2**
and nothing here authorises a build.

**T23.** `yt_match40`'s calibration is known wrong, and K3 **inherits it** — hit→landing spans
come from events that depend on court geometry. `am_hard_utr` and `yt_rally2` do not, they
clear the bar independently, so the K3 verdict does not turn on `yt_match40`.

### 5.6 M1 — the falsifier fires. KILL, and the kill is itself the useful result.

§2 ranked M1 first and pre-registered: *"`coast_err` for the `"1-2"` bin, pooled over the three
TrackNet arms, must be ≤ 10.0 px median … If it is above, the exclusion rule is empirically
right, this branch dies in one command, and that is itself worth knowing."*

**First, the check §2 asked for: does an existing file already carry these numbers? Partly —
and not usably.** Nine files under `data/output/` carry `coasted_err_px_by_gap`
(`session_i_ab/coast_<clip>.json`, `chain_ab_<clip>.json`, `coherent_<clip>.json`). **Every one
of them is a BallNet arm** (`ballnet_v21.pt`, `pool_new_s0.pt`) — there is no TrackNet
coast-by-gap output in the repo. Their BallNet `"1-2"` medians are 6.7 (n=4) / 11.8 (n=4) /
5.3 (n=5), which would have *passed* the bar on a detector that is not v1's. The TrackNet
number had to be computed, and it was, by replaying the shipped ladder from the three cached
TrackNet arms and calling `tools/eval_model_filters.py`'s own `measure()` for the binning
rather than reimplementing it.

Measured against human gold clicks, distance in source pixels from each coasted emitted
position to the click, binned by the length of the coasted run it sits in:

| bin | `am_hard_utr` | `yt_match40` | `yt_rally2` | **POOLED median** | n |
|---|---|---|---|---|---|
| **`"1-2"`** | 2.9 (n=3) | 29.6 (n=6) | 19.9 (n=7) | **19.90 px** | **16** |
| `"3-5"` | 384.7 (n=1) | 86.5 (n=4) | 58.8 (n=1) | 86.55 px | 6 |
| `"6-9"` | 14.3 (n=3) | 468.5 (n=1) | 8.7 (n=21) | 14.25 px | 25 |
| `"10+"` | 624.1 (n=2) | 4.7 (n=3) | 447.6 (n=2) | 64.38 px | 7 |

**Pooled `"1-2"` median = 19.90 px against a ≤ 10.0 px bar. M1 is KILLED.** Only 5 of the 16
short-bridge frames (31%) land within the 10 px recall radius. Two of three clips fail
individually; the one that passes (`am_hard_utr`, 2.9 px) rests on **three** samples.

**What the kill establishes, and it is worth more than the branch was.** `ball.py:667–669`'s
exclusion rule — *"a forecast is a physics guess and not a measurement"* — was an **empirical
claim** that had never been tested. It is now tested, on v1's shipped detector, and it is
**right**: even the shortest bridges, bounded by accepted detections on both sides inside one
segment, are a median 19.9 px off the ball, twice the radius the project calls a hit.
**`seen_frac` is not under-counting. The −11.0 / −8.1 pts are real lost balls, not an
accounting artefact.** That closes the cheapest available escape from this stage's cost and
means any future gain here has to be earned in the tracker.

**Power (T09).** n = 16 pooled, 3 / 6 / 7 per clip. Thin, and the bar was chosen knowing that.
It does not rescue M1: the pooled median is **2× the bar**, and the two clips with the larger
samples are the two that fail (29.6 and 19.9). A larger sample would have to be dramatically
better-behaved than what is here to move a 2× miss.

### 5.7 One code-read claim of §2, now measured

§2 derived at confidence 0.85, without measurement: *"`D_smooth` (−11.0 / −8.1 pts) IS the
gate's rejection rate over span frames, minus the frames the `reset_after` re-seed path
recovers. It is not a downstream reset cascade."*

Measured — gate rejections that stay lost, as a fraction of ALL hit→landing span frames:

| clip | lost rejections in span | span frames | rate | published `D_smooth` |
|---|---|---|---|---|
| `am_hard_utr` | 858 | 8,423 | **10.19%** | −11.0 pts |
| `yt_match40` | 484 | 6,144 | **7.88%** | −8.1 pts |
| `yt_rally2` | 46 | 612 | **7.52%** | (none published) |

**Confirmed.** The rate reproduces the published cost to within ~0.8 pt on both clips that have
one, and the residual is the direction §2 predicted (re-seed recoveries and bridge effects).
`D_smooth` is the rejection rate, not a cascade. Brief-candidate (b) stays refuted.

### 5.8 What is left alive

- **M1: dead** (5.6, its own falsifier).
- **M2: dead** (5.4, K2 on both legs). Fifth measured negative in this family.
- **The R line: dead** (§1's census, unchanged) — and 5.2 adds that the premise had the sign
  backwards, while 5.3 shows the lever was weaker than §1 credited it with.
- **M3 (a) (b) (c): still DO-NOT-BUILD**, untouched by this run.
- **M4 — `suppress_false_locks`, −5.2 / −4.4 pts — is the only candidate in this file still
  standing**, and 5.6 sharpens why: with the accounting escape closed, every point of this
  stage's cost is a genuinely lost ball, and `pipeline.py:1441–1444` already records
  suppression deleting real far-court balls. Not costed here; out of this brief's scope.
- **New, and NOT a candidate — recorded so it is not re-derived.** 5.2 and 5.3 together say the
  filter's noise model is over-dispersed (median `d²` 12× below χ²₂) and that `P`, not `R`,
  supplies 70–81% of `S`. The lever that would follow is `Q` / `sigma_jerk`, and **`Q` has a
  measured negative already** (`ball.py:686–692`, false-fire 19 → 27% when loosened; tighten-only
  held flat at 19.2% and bought +1.2 pts far-court hit@10). A **tighten** cannot address the
  −11.0 / −8.1 pt coverage cost — it rejects more, not less — so it is not a coverage candidate
  and nothing is proposed on it here. It is written down because "the innovations are 12× tighter
  than the model assumes" is a fact about this filter that no file previously recorded, and
  because the next person to look at `sigma_jerk = 1.0` should see it first.

### 5.9 Provenance — exactly which files every number came from

**The path conflict §3 flagged is RESOLVED, and the evidence file was right.**
`data/output/speed_coverage/` **exists as a DIRECTORY** (11 files, e.g.
`am_hard_utr.tracknet.json`, `yt_match40.tracknet.json`). There is **no** flat
`data/output/speed_coverage_amhard_tracknet.json`. **`tools/eval_speed_coverage_chain.py`'s
docstring example is stale** — a docs-only defect, no number depends on it. Verified by `ls`
and by a Python directory walk (the harness `Glob` tool and a repo-root `grep -rl` both fail
here, T25).

| clip | ball detections (the ARM) | pose / cam-motion | human labels | frames × step | res | `res_scale` | pre-smoother locks |
|---|---|---|---|---|---|---|---|
| `am_hard_utr` | `data/output/detector_ab/am_hard_utr.tracknet.perception.json` | `data/output/am_hard_utr.perception.json` | `data/gold/am_hard_utr.labels.json` (175 ball / 53 no-ball) | 14,499 × 2 | 1920×1080 | 1.5 | 8,330 |
| `yt_match40` | `data/output/detector_ab/yt_match40.tracknet.perception.json` | `data/output/yt_match40.perception.json` | `data/gold/yt_match40.labels.json` (184 / 24) | 10,268 × 1 | 1280×720 | 1.0 | 5,974 |
| `yt_rally2` | `data/output/detector_ab/yt_rally2.tracknet.perception.json` | `data/output/detector_ab/yt_rally2.tracknet.match.perception.json` | `data/gold/yt_rally2.labels.json` (258 / 26) | 1,108 × 2 | 1280×720 | 1.0 | 788 |

All three ball arms are **TrackNet**, v1's shipped detector, from `detector_ab/` — the only
cache family that is a one-variable detector pair. All three carry the same resolved settings
(`ball_perception.py`, `weights/tracknet.pt`, `device=cuda`, `score_thresh=0.5`,
`court_gate=false`, `bgsub=true`, 2026-08-28), checked in the caches' own `provenance` blocks
rather than assumed from a preset table (T02). Pose is detector-independent (same
`yolo11m-pose.pt@1280` in every cache), which is what keeps the arm one-variable; `yt_rally2`
has no `data/output/yt_rally2.perception.json`, so its pose comes from the TrackNet **match**
cache at the same `frame_step`, asserted equal in-run.

**Smoother parameters, resolved at the call and not read from a preset table:**
`gate_chi2 = 13.8`, `meas_var = 25.0`, `sigma_jerk = 1.0`, `reset_after = 3`,
`max_gap_s = 0.4`, `bounce_reset = False`, `bounce_hypothesis = False`, `res_scale = h/720`.

**T01 — no `--frame-step 1` number is quoted as shipped.** `yt_match40`'s `step = 1` is its
NATIVE decimation (`src_fps = 29.0`, so `max(1, round(29/30)) = 1`), not an override; the other
two run at their shipped `step = 2`.

**Two chains were run through the instrumented smoother, and they are reported separately:**
chain **A** = `remove_outliers → rectify_track → suppress_false_locks` (court gate OMITTED),
which is §5's chain and is what makes the census reproduction in 5.1 a like-for-like check;
chain **B** = the full shipped ladder including `gate_ball_to_court`, which is what K3, the
span statistics and M1 are measured on (rule 5: score at the chain). **K1 and K2 are identical
on both chains** — the court gate touches 0 / 5 / 0 pre-smoother locks on these three clips,
matching §6's prediction.

**T23.** `yt_match40`'s calibration is known wrong. **K3, `in_span` and 5.7's span rates on that
clip inherit it.** **K1, K2, Leg 2's R/S and M1 do not** — they are `d²` / internal filter state
and image-space pixel distances to human clicks, neither of which passes through a homography.

**Gold-leak posture.** This pass trains nothing, fits nothing and writes no label file. Gold is
read one-way, as TEST, via `tools/_goldset.py` and `tools/eval_model_filters.py:gold()`. No
guard is bypassed. No human ground truth was edited (rule 9).

**Seeds.** The K2 null control uses `random.Random(20260910)`, 1000 draws, per clip and pooled.
The rest of the pass is deterministic; it was run twice end-to-end and produced identical
numbers.

**Artifacts.** `data/output/gate_noise_diag/` — `summary.json` (all per-clip and pooled
statistics, with the resolved-configuration provenance stamp, the script's own sha256
`e494f55e96168792` and `ball.py`'s `171932521dc3e796`), and six per-frame files
`<clip>.<chain>.rows.json`, one row per detection-bearing frame carrying `d2`, `S00`, `S11`,
`P00`, `R00`, `accepted`, `gate_tested`, `rej_ctr`, `rej_run_len`, `run_tripped_reset`,
`reset_here`, `reset_by_rej`, `seg_id`, `in_span` and `gold_label`. The instrumenting script
itself was RUN from a scratchpad outside the repo, so that no version of it could ever be
imported as shipped code; a verbatim copy is preserved next to its outputs as
`data/output/gate_noise_diag/gate_diag.py` (that directory is gitignored, like every other
cache under `data/output/`).

### 5.10 What this run does NOT establish

- **Whether a higher smoother-stage `seen_frac` produces a more accurate speed.** §4's closing
  warning stands, entirely untouched: the 0.5 gate `seen_frac` feeds is measured only weakly
  predictive (+4.96 / +3.11 against a ≥ 10-pt bar, 0 of 10 seeds), so the size of the prize
  behind the −11.0 / −8.1 pts is still not established. K3's +3.45 to +6.49 pt ceiling is a
  ceiling on a **statistic**, not on a product gain. `tools/synth_truth.py` remains the only
  rule-11-compliant instrument that could settle it, and it was not run here.
- **Whether any signal separates the gate's rejects.** Two have now failed — distance to the
  RTS-smoothed track (§5 of the readmit file) and rejection-run coherence (5.4 here). A signal
  from outside the motion model is still untested and is not covered by either negative.
- **Anything under BallNet.** All three arms are TrackNet. The BallNet coast-by-gap numbers
  quoted in 5.6 are cited only to show why they could not answer M1's falsifier.
- **`yt_rally2` at the `+smooth_forecast` stage beyond its mean.** Its 67.96% is baselined on
  **10 shots**. Any future bar on that clip must state that n.

---

## 6. Independent verification of §5 (qa)

> Verified 2026-09-10 by **qa**, independently of backend-dev. §1–§5 were **not edited,
> restructured or corrected** — this section is appended only. **No bar in §3 or §4 was
> restated.** Nothing was fixed: two defects are recorded below and left in place.
>
> `backend/swingvision/ball.py` was not opened for writing by me either; my own
> instrumentation is a second, separate source transform. Everything I ran lives in a
> scratchpad outside the repo.
>
> **What every number in this section is measured against, in one sentence each:** `d²`,
> `S00`, `S11`, `P00`, `R00` and the reset counters are the shipped Kalman filter's OWN
> internal state, read out of an instrumented copy asserted identical to the shipped
> function, and carry no accuracy claim; every `real` / `ghost` label is a **human gold
> click** in `data/gold/<clip>.labels.json` at the project's own 10.0 px recall radius;
> `seen_frac` is the tracker's own coverage over the tracker's own hit→landing spans and is
> a COVERAGE statistic, not an accuracy one; the published ladder baselines are read out of
> `data/output/speed_coverage/<clip>.tracknet.json`, the artifact
> `speed-coverage-is-chain-shaped-and-the.md` was written from.

### 6.0 Verdict table

| id | backend-dev reported | qa recomputed | verdict |
|---|---|---|---|
| **K3** frames discarded | 902 / 479 / 47 | **914 / 492 / 48** | **CONFIRMED, number CORRECTED UPWARD.** backend-dev's count is a 1.3% / 2.7% / 2.1% *under*-count; the direction is safe |
| **K3** points of `seen_frac` | +6.492 / +4.926 / +3.450 | **+6.557 / +5.142 / +3.534** | **CONFIRMED — K3 PASSES.** The ≥1.0 pt bar is cleared by 3.5× to 6.6× |
| **K3** spans held fixed? | asserted | **VERIFIED twice** — analytically from `pipeline.py`, and empirically (90→90, 86→86, 10→10 shots; span endpoint lists identical) | **CONFIRMED** |
| **K1** pooled median `d²` | 0.113 (n=291) | **0.11272 (n=291)** | **CONFIRMED** |
| **K1** the SIGN (`S` over-stated) | ~12× low | **12.30× low; 238/291 below χ²₂'s median, sign-test p = 1.9 × 10⁻²⁹** | **CONFIRMED, and it survives both alternative explanations I could test** |
| **§5.3** R/S median | 0.187 / 0.257 / 0.304 | **0.1871 / 0.2571 / 0.3036** | **CONFIRMED** |
| **§5.3** accept radius | 64.4 / 36.7 / 33.7 px | **64.41 / 36.63 / 33.71 px** | **CONFIRMED**, with a resolution caveat (6.3.5) |
| **§5.5** "reproduces the published baselines to within 0.05 pt" | claimed on 2 clips | **true on `am_hard_utr` (0.04 pt, like-for-like). NOT true on `yt_match40`** | **CORRECTED — 6.2.4. The one substantive defect.** |

**Bottom line: both headline verdicts stand.** K3 PASSES on my own numbers and by a wider
margin than reported; K1's band is missed in the direction reported, and the sign is not an
artefact. The two defects I found are in *supporting* claims, not in either verdict.

### 6.1 What "independent" means here, precisely

- **Own source transform, different insertion.** Nothing was re-derived from
  `summary.json`. My copy captures the **full counter state at the reset decision** —
  `(i, z is not None, accept, rej, miss, reset_fired, reset_by_rej)` on every frame — and I
  maintain the pending-rejection list **frame by frame in trace order**, a different
  algorithm from `gate_diag.py`'s post-hoc run reconstruction. That difference is what
  surfaced the defect in 6.2.1.
- **The shipped code is INVOKED, never re-implemented** — `B.smooth_forecast`,
  `pipeline._build_match_from_events`, `pipeline.calibrate_video`, `events.*`,
  `EMF.gold` / `EMF.index_of`. An audit that re-implements a pipeline reports a different
  pipeline; that trap has already fired in this repo.
- **`instrumented == shipped` → True on all three clips**, comparing all three returned
  lists (`out`, `coasted`, `conf`) element-wise, in my harness as in backend-dev's.
- **`ball.py` is genuinely unmodified.** Absent from `git status`; `git diff HEAD --
  backend/swingvision/ball.py` empty; sha256 prefix computed at my run time
  `171932521dc3e796`, matching the stamp in `summary.json`.
- Percentiles: backend-dev's `quant()` is **nearest-rank**; I report the standard
  **linear-interpolation** percentile beside it wherever the two differ. They differ only
  on even-n clips — the pooled n = 291 is odd and identical under both.

### 6.2 K3 — CONFIRMED, and larger than reported

#### 6.2.1 Is the discarded-frame definition right? YES — and it is undercounted

Read at `ball.py:962–970`. The reset block is:

    if rej >= reset_after or miss >= max_gap:
        x = P = None; seg += 1; rej = 0; miss = 0
        if z is not None and accept is False and rej == 0:  # re-seed on this lock

**The re-seed branch's `rej == 0` test is vacuous** — `rej` was set to `0` on the line
above, so the condition is always true and the branch reduces to
`if z is not None and accept is False`. It therefore fires on **miss**-triggered resets as
well as `rej`-triggered ones, which is very likely not what the guard was written to mean.
**It does not change the frame count**, and I verified that directly: I asserted
`used[i] is True` for every frame the branch touched, on all three clips, and the assert
held. So the reset frame's own rejected detection **is** recovered, and backend-dev's
definition — the `reset_after − 1 = 2` *earlier* rejections in the run are the discarded
ones — is the correct one. `rej` only ever increments on a frame carrying a detection and
is zeroed at every acceptance and at every reset, so a `rej`-triggered reset has **exactly
two** earlier discarded rejections behind it, never more and never fewer.

**That gives 2 × `resets_by_rej` exactly, and my count matches it exactly:**

| clip | resets total | by `rej` | by `miss` | 2 × by-`rej` | **qa discarded** | backend-dev |
|---|---|---|---|---|---|---|
| `am_hard_utr` | 630 | 457 | 173 | 914 | **914** | 902 (−12) |
| `yt_match40` | 384 | 246 | 138 | 492 | **492** | 479 (−13) |
| `yt_rally2` | 34 | 24 | 10 | 48 | **48** | 47 (−1) |

The reset counts themselves reproduce **exactly**.

> **DEFECT 1 (harness, not verdict).** `gate_diag.py` reconstructs rejection runs *after
> the fact* from the recorded `rej_ctr`, opening a new run whenever it sees `rej_ctr == 1`
> while a run is already open. But `rej_ctr` is recorded on **every** frame past the seed,
> including frames carrying **no detection**, where `rej` simply holds its previous value.
> A run of the shape `rej = 1, (no detection), (no detection), 2, 3` is therefore split
> into three runs and the first genuine rejection is orphaned out of the recover set. That
> is the whole of the 12 / 13 / 1 frame gap. **The error is one-directional — it can only
> drop frames, never add them — so K3's reported number is conservative and the PASS is
> unaffected.** Recorded, not fixed.

Two further properties I checked so the ceiling cannot double-count: every frame in my
discarded set carries a detection and has `used[i] == False` (asserted, all three clips);
and a frame with `used[i] == False` is either not emitted at all or emitted as `coasted`,
both of which are already `False` in the base `ball_seen` mask. **No discarded frame was
already being counted as seen.**

#### 6.2.2 Does the arithmetic hold? YES

Recomputed from my own discarded set through my own replay of
`pipeline._build_match_from_events`:

| clip | base mean `seen_frac` | qa ceiling | **qa points** | backend-dev points |
|---|---|---|---|---|
| `am_hard_utr` | 51.060% | 57.618% | **+6.557** | +6.492 |
| `yt_match40` | 54.785% | 59.928% | **+5.142** | +4.926 |
| `yt_rally2` | 67.963% | 71.497% | **+3.534** | +3.450 |

All three clear the pre-registered ≥ 1.0 pt by **3.5× to 6.6×**. My base means are
identical to backend-dev's to three decimals on all three clips.

#### 6.2.3 Were the hit→landing spans really held fixed? YES — verified two ways

**Analytically, from `pipeline.py`.** `ball_seen` is consumed in exactly one place —
`real_at` (`:1712`) — which is reached only from `real_fraction` (`:1722`) and directly at
`:1849`; `real_fraction` is called only at `:1730` (`real_continuation`) and `:1862`
(`seen_frac`). The span endpoints `h` / `land` are set at `:1744` / `:1753` from
`bounce_idx` and the next hit, with **no `ball_seen` dependency anywhere upstream**, and
`span_sink.append` (`:1885`) is unconditional inside the loop over `pending`. `ball_seen`
therefore cannot move a span boundary, add a shot or remove one.

**Empirically.** Base vs ceiling: **90 → 90**, **86 → 86**, **10 → 10** shots, and the full
list of `(h, land)` pairs compares **identical** on all three clips. The flip moves exactly
one thing.

> **Caveat the section states, but which deserves more weight than it is given.** This is a
> ceiling on an *accounting* flip: frames are marked seen without re-running the filter
> with those detections accepted. A real implementation would change the segment structure
> (fewer resets → longer segments → more bridged, i.e. **coasted and therefore unseen**,
> frames), so the realised number could land anywhere at or below this, including negative.
> §5.5 says the ceiling "assumes every discarded rejection is recovered for free and
> correctly"; what it does not say is that recovery would also *change the rest of the
> track*.

#### 6.2.4 Do the baselines check out? ONE YES, ONE NO — the substantive defect

Read from the published artifact `data/output/speed_coverage/<clip>.tracknet.json`, the
file `speed-coverage-is-chain-shaped-and-the.md`'s ladder table was written from:

| clip | published mean | published `n_shots` | published calibration | this run's mean | this run's `n_shots` | this run's calibration |
|---|---|---|---|---|---|---|
| `am_hard_utr` | **51.06%** | **90** | `manual-exact`, reproj 0.0, hfov 86.31° | 51.060% | **90** | `manual-exact`, reproj 0.0, hfov 86.31° |
| `yt_match40` | **54.95%** | **186** | `manual+snap`, reproj **9.112**, hfov **26.43°** | 54.785% | **86** | `manual+snap-clay`, reproj **0.011**, hfov **91.28°** |

- **`am_hard_utr` is a genuine, like-for-like reproduction** — same shot count, same
  calibration, same hfov, 0.04 pt apart. That leg of the "third independent check" holds.
- **`yt_match40` is not a reproduction at all.** The gap is 0.165 pt, not "within 0.05 pt";
  and more importantly the two means are **not the same quantity** — 86 shots here against
  186 published, because `calibrate_video` resolved a *different court* on the same clip
  from the same `data/yt_match40_pts.json`. Different homography → different events (91
  hits here vs 192 published) → a different span set. The near-agreement of 54.785 with
  54.95 is a coincidence between two different populations, not a check on the harness.

> **DEFECT 2 (a claim, and a live provenance problem).** §5.5's *"reproduce the published
> smoother-stage baselines of 51.1 and 55.0 to within 0.05 pt, which is a third independent
> check on this harness"* is **CORRECTED**: it holds on `am_hard_utr` and holds on
> `yt_match40` on neither the number nor the population. **And the underlying fact deserves
> attention independent of this run:** the same clip and the same clicked points now
> resolve to `manual+snap-clay` at 0.011 px / hfov 91.28° where a run eight days earlier
> resolved `manual+snap` at 9.112 px / hfov 26.43°. One of those two courts is wrong, the
> residual will not tell you which, and a 26° vs 91° field of view is not a rounding
> difference. Recorded, not diagnosed and not fixed — **someone has to render the corners
> (T23).**

#### 6.2.5 T23 — does the K3 verdict turn on `yt_match40`? NO, and the caveat should be stronger

`am_hard_utr` (+6.557) and `yt_rally2` (+3.534) each clear the ≥1.0 pt bar on their own, by
6.6× and 3.5×, so deleting `yt_match40` entirely does not touch the verdict. §5.5's T23
paragraph is correct as written. It is also **understated**: T23 describes `yt_match40`'s
calibration as "manual+snap, 9.1 px", which is the *published ladder's* calibration, not
the one this run used (6.2.4). Its K3 number rests on a third court, matching neither.

#### 6.2.6 `yt_rally2`'s 67.96% has never been published — CONFIRMED, and it has no cross-check

Verified by two mechanisms, as required: `ls data/output/speed_coverage/` contains ladder
artifacts for `am_hard_utr` and `yt_match40` only, in no arm for `yt_rally2`; and a
recursive `grep` for `67.9` across `docs/` returns only this file's own three mentions.
**So `yt_rally2`'s baseline is a first measurement with nothing to check it against, it
rests on 10 shots, and my 67.963% agreeing with backend-dev's 67.963% is agreement between
two runs of the same replay — a determinism check, not corroboration.** §5.10 says this; it
is repeated here because after `am_hard_utr`, `yt_rally2` is K3's only non-T23-tainted leg
and it is the one with no independent reference at all.

#### 6.2.7 The "40–60% of the stage's cost" framing

Against the published `D_smooth` of **−10.96** pt on `am_hard_utr` — the one clip where the
comparison is like-for-like — my +6.557 is **59.8%** of the stage cost, at the top of the
quoted band rather than the middle. The `yt_match40` ratio should not be quoted at all: its
numerator and denominator now come from different shot populations (6.2.4). `yt_rally2` has
no published `D_smooth`. **The claim rests on one clip, and on that clip it is right.**

### 6.3 K1 — CONFIRMED, and the sign survives every attack I could make on it

#### 6.3.1 The numbers

Population as §3 mandated, re-derived from my own run: frames the gate **accepted**, that
were **gate-tested**, whose pre-smoother detection is within **10.0 px of a human gold
click**. χ²₂ reference: median 1.3863, p90 4.6052.

| clip | n | qa median (linear) | qa median (nearest-rank) | backend-dev | qa p90 |
|---|---|---|---|---|---|
| `am_hard_utr` | 32 | **0.176** | 0.264 | 0.265 | 6.56 |
| `yt_match40` | 106 | **0.121** | 0.122 | 0.122 | 5.76 |
| `yt_rally2` | 153 | **0.104** | 0.104 | 0.104 | 2.30 |
| **pooled** | **291** | **0.11272** | 0.11272 | **0.113** | **4.776** |

**Pooled: CONFIRMED to five significant figures. 1.3863 / 0.11272 = 12.30× low.**
One small correction: `am_hard_utr`'s per-clip median is convention-dependent (n = 32 is
even) — **0.176** under the standard linear-interpolation percentile against 0.264 under
backend-dev's nearest-rank `quant()`. §5.2's "5.2× low" on that clip reads 7.9× low under
the standard definition. **The pooled headline is convention-free** (n = 291 is odd), and
it is the pooled figure that carries the verdict, so nothing moves.

#### 6.3.2 Is `d²` computed against the PRIOR? YES — the posterior explanation is ruled out at source

`ball.py:855–860`: `x = F @ x; P = F @ P @ F.T + Q * qfac[i]` executes **before**
`y = z − Hm @ x` and `S = Hm @ P @ Hm.T + R`. The update `x = x + K @ y` happens only
*inside* the accept branch, after the test. The instrumentation splits the gate line itself
(`_d2 = float(y @ np.linalg.solve(S, y))`, then `if _d2 <= gate_chi2:`), so the recorded
value is bit-for-bit the quantity the gate compares, evaluated on the propagated prior.
**There is no path by which the filter's having been updated by this detection could shrink
this frame's own innovation.** My own transform reproduces every `d²`.

#### 6.3.3 Is the median censored by the 13.8 accept cut? NO, and this is measurable

Simulation, 200,000 draws, seeded `np.random.default_rng(20260910)`: a **true** χ²₂ places
only **0.1025%** of its mass above 13.8, so censoring at 13.8 moves its median from 1.3863
to **1.3870** — a 0.05% shift. **Censoring cannot produce a 12× miss.** The uncensored
statistic §5.2 also reports (every gold-real frame carrying a detection, accepted *and*
rejected) confirms it from the data side: pooled **0.127 on n = 312**, still 10.9× low. My
per-clip uncensored medians are 1.033 / 0.131 / 0.113, matching §5.2's table exactly,
including that `am_hard_utr` alone lands inside the band once its 9 rejected reals are put
back.

#### 6.3.4 The sign, tested distribution-free

A median ratio can be moved by outliers; a sign test cannot. Fraction of gold-real accepted
frames whose `d²` falls **below** χ²₂'s median 1.3863 — 50% under the null that the noise
model is calibrated:

| clip | below / n | required to reject at p ≤ 0.05 (one-sided) | sign-test p |
|---|---|---|---|
| `am_hard_utr` | **24 / 32** | ≥ 22 / 32 | 3.5 × 10⁻³ |
| `yt_match40` | **83 / 106** | ≥ 62 / 106 | 1.9 × 10⁻⁹ |
| `yt_rally2` | **131 / 153** | ≥ 88 / 153 | 2.2 × 10⁻²⁰ |
| **pooled** | **238 / 291** | ≥ 161 / 291 | **1.9 × 10⁻²⁹** |

**The sign is established on every clip separately and is not a power artefact** (T09:
required-n quoted beside every count; even the smallest clip clears its own threshold).
§5.2's reading — innovations are far smaller than `S` predicts, so `S` is over-stated,
raising `meas_var` moves the statistic further from calibration, and the R premise dies by
the opposite sign — is **CONFIRMED**.

**One qualification §5.2 does not make, and it belongs on the claim.** The 12× is a
property of the **human-confirmed-real** subset, not of the filter's innovation
distribution as a whole. Median `d²` over **all** gate-tested frames is **1.176 / 0.429 /
0.237** (n = 8,157 / 5,834 / 777) — on `am_hard_utr` that is within 15% of χ²₂'s 1.386.
The defensible sentence is *"`S` is over-dispersed relative to real, well-localised
detections"*, not *"the innovation statistic is 12× low"* unqualified. That is still
exactly Leg 5's mixture — a tight real core the model over-covers, plus junk that inflates
the pooled statistic back toward looking calibrated — and it does not rescue the R line,
because raising `R` raises `S` further on both populations.

**Selection, stated because it runs in the same direction as the finding.** The population
is selected for detections within 10 px of a click, i.e. selection *toward* well-localised
frames. On `am_hard_utr` it is thin for a second reason: `frame_step = 2` maps only 90 of
that clip's 175 gold ball clicks onto a track index at all, of which 41 produced a
within-10 px detection and 32 were accepted and gate-tested — **n = 32 is 18% of that
clip's gold.** The other two clips are complete (184/184 and 258/258 clicks mapped).

#### 6.3.5 §5.3's R/S and the accept radius — CONFIRMED, with a resolution caveat

| clip | qa median R/S | backend-dev | qa median `S00` | qa median `P00` | `R00` | accept radius, source px | at 720p-equivalent |
|---|---|---|---|---|---|---|---|
| `am_hard_utr` (1080p) | **0.1871** | 0.187 | 300.60 | 244.35 | **56.25** | **64.41** | **42.94** |
| `yt_match40` (720p) | **0.2571** | 0.257 | 97.25 | 72.25 | 25.0 | **36.63** | 36.63 |
| `yt_rally2` (720p) | **0.3036** | 0.304 | 82.36 | 57.36 | 25.0 | **33.71** | 33.71 |

`res_scale` is handled correctly: `R00 = 56.25 = 25.0 × 1.5²` on the 1080p clip and 25.0 on
the two 720p clips, exactly as `ball.py:808–812` scales `meas_var` by `rs²`. I also
confirmed `S11 == S00` to full precision on all three clips, so "accept **radius**" is
literally right — the accept region is a circle, not an ellipse.

**Caveat on the headline.** §5.3 contrasts *"measured median is 33.7–64.4 px"* with Leg 2's
*"~19 px"*, but 64.4 px is a **1080p source-pixel** number while ~19 px was derived at 720p
with `R = 25`. Like-for-like the ratio is **42.94 / ~21 ≈ 2.0×** on `am_hard_utr` and
1.7–1.8× on the two 720p clips — the "~1.8× wider than anyone believed" conclusion is
right, but the 64.4-vs-19 comparison as printed crosses a resolution boundary, and **64.4
px must never be quoted without "@1080p" attached.**

### 6.4 The three spot-checks

- **Instrumentation identity.** `ball.py` is genuinely unmodified — absent from
  `git status`, empty `git diff HEAD`, sha256 prefix `171932521dc3e796` matching the stamp.
  The check compares **all three returned lists** element-wise
  (`got[0] == ref[0] and got[1] == ref[1] and got[2] == ref[2]`), not a summary of them,
  and it re-runs the shipped function on a fresh copy of the same input. My own independent
  transform also returns `identical == True` on all three clips, on chain B. **CONFIRMED.**
- **K2's null control.** Seeding and draw count are exactly as stated: a fresh
  `random.Random(20260910)` per clip, per chain and for the pooled statistic; **1000
  draws**; one-sided `e >= obs`; labels permuted within the clip's lost-reject population
  with the run-length assignment held fixed, so neither group can come up empty and all
  1000 draws count. I re-ran the null myself from the stored populations and reproduced
  **0.105 / 0.589 / 0.585, pooled 0.135, exactly**. Monte-Carlo standard error at p = 0.105
  on 1000 draws is ±0.010, nowhere near the 0.05 line. **CONFIRMED as stated.**
- **§5.6's M1 number, and its power honestly.** The pooled `"1-2"` bin is
  `[0.13, 2.80, 2.91, 3.50, 4.92, 7.68, 12.98, 14.41, 19.90, 25.35, 26.54, 29.62, 35.32,
  45.47, 71.10, 387.36]`, n = 16, measured as source-pixel distance from each coasted
  emitted position to a human gold click. The median is **19.90 px** under backend-dev's
  nearest-rank convention and **17.16 px** under the standard linear-interpolation
  definition — 1.7× to 2.0× the ≤ 10.0 px bar either way, so **the pre-registered KILL
  stands on either convention.** Two corrections to the surrounding prose: **6** of the 16
  land within 10 px (37.5%), not 5 (31%); and n = 16 **cannot support the inferential claim
  that follows it.** A sign test against H₀ *"the true median is exactly the 10.0 px bar"*
  gives **p = 0.45** — this sample cannot distinguish a true median of 10 px from what was
  observed, and at the observed 62.5% above-bar rate you would need **n ≥ 44** to reject at
  p ≤ 0.05. So M1 fails its own pre-registered bar on the point estimate, which is a valid
  kill because the bar was pre-registered on the median; but §5.6's stronger sentence —
  *"`ball.py:667–669`'s exclusion rule … is now tested … and it is right"* — is **not
  established at this n** and should be read as "not contradicted". The detector caveat
  §5.6 does make is load-bearing and I repeat it: these are TrackNet arms, the BallNet
  `"1-2"` medians in the same repo are 6.7 / 11.8 / 5.3, and **a number from a TrackNet arm
  may not be carried onto a BallNet default.**

### 6.5 Borderline or ambiguous — for a human, even though both verdicts pass

1. **`yt_match40`'s calibration moved between 2026-09-02 and 2026-09-10** (6.2.4): the same
   clip and the same clicked points resolved `manual+snap` / 9.112 px / hfov 26.43° then
   and `manual+snap-clay` / 0.011 px / hfov 91.28° now. Both cannot be right, the residual
   will not tell you which, and this touches every span-derived number ever measured on
   that clip. **The single thing in this audit most worth an eye.**
2. **`yt_rally2` carries K3's only non-T23-tainted second leg and has no external
   reference** (6.2.6): 10 shots, first measurement, and the only agreement so far is
   between two runs of the same replay.
3. **The K3 ceiling assumes recovery changes nothing else** (6.2.3): accepting the
   discarded detections would restructure segments and bridging, so the realised figure is
   not bounded below by anything.
4. **The vacuous `rej == 0` guard** at `ball.py:967` (6.2.1) is a no-op for K3 but is
   almost certainly not what was intended, and it makes the re-seed fire on
   `miss`-triggered resets too.
5. **`am_hard_utr`'s K1 n = 32 is 18% of that clip's gold**, an artefact of `frame_step = 2`
   halving the usable clicks (6.3.4). The sign still clears on that clip alone, but any
   future per-clip K1 claim on `am_hard_utr` must state that n.

### 6.6 What this verification did NOT check

- **K2's contingency analysis** beyond its null control — out of scope by instruction. The
  KILL verdict there is not independently re-derived here.
- **§5.7's span-rate table**, and §5.9's `0 / 5 / 0` court-gate claim, which I
  spot-confirmed from row counts (chain A 8,330 / 5,974 / 788 vs chain B 8,330 / 5,969 /
  788) but did not audit.
- **Whether any of this predicts a product gain.** §4's closing warning and §5.10 stand
  untouched: `seen_frac` is a coverage statistic, the 0.5 gate it feeds is measured only
  weakly predictive, and `tools/synth_truth.py` — the only rule-11-compliant instrument
  that could price the prize — was run neither by backend-dev nor by me.
- Nothing here was scored against a scoreboard, a HUD, a burned-in graphic or any model's
  own output. Human ground truth was read one-way for labelling only and none was edited
  (rule 9). No `--frame-step 1` number is quoted as shipped behaviour (T01): `yt_match40`'s
  `step = 1` is its native decimation at `src_fps = 29.0`.
