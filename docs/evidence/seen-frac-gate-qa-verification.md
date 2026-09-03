# QA verification — does `seen_frac >= 0.5` predict speed error?

Verifying `docs/evidence/does-seen-frac-predict-speed-error.md` (backend-dev, 2026-09-03,
commit `79c381d`), against the pre-registration at the end of `.claude/journals/lead.md`.
QA is measurement-only: nothing here changes the `0.5` constant, no replacement threshold
is proposed, nothing is committed to `tools/`, `docs/STATE.md` is not touched.

**Method note, load-bearing for everything below:** backend-dev's actual harness
(`scratchpad/seen_frac_vs_error.py`) lives in *that agent's own session temp directory*,
which is outside this project folder and was not accessible to me. I could not run their
literal script. Instead I **independently rebuilt** the harness from the evidence file's
own §2/§3 description — same shipped code paths (`tools/synth_truth.simulate`/`truth_of`,
`swingvision.ball.smooth_forecast`/`cap_court_jumps`/`smooth_and_fill`,
`calibration.image_to_court`/`homography_from_landmarks`, `analytics.shot_speed_kmh`,
`tools/height_curve.hfov_of`), same three clips, same per-flight `dropout ~ U(0.05,0.80)`
design. Scripts: `scratchpad/positive_control.py` and `scratchpad/full_check.py` (this
session's scratchpad, not committed, not promoted to `tools/`, per the brief).

## VERDICT

**The headline stands, with one caveat that narrows but does not void it.** G is refused
in every population I tested too (0 of 3 clips reach 1.5x in any arm I ran). The
classifier-shape numbers (accept-precision ≈ base rate, refused-but-accurate ≈39% of
refused, court-coverage as the real correlate) reproduce closely in an independently-built
harness. The positive control (check 1) shows the harness is **not blind by construction**
— it does respond to an injected true correlation — but the response is **modest and
camera-dependent**, which is a real, additional limitation the evidence file does not
fully state. The specific 2-decimal-place band-ratio numbers in the file's §4 (1.35/0.86/
0.76, 1.11/1.21/0.97) are **less reproducible than their precision implies** — my rebuild
gets a materially different set (see check 2) while agreeing on the qualitative shape and
on G refusing everywhere. Recommend treating §4's precise ratios as indicative, not exact,
and the INDETERMINATE verdict itself as the right conservative call.

---

## 1. Positive control — is the harness capable of detecting a true `seen_frac` effect?

**CONFIRMED, with a caveat.** Two arms, same marginal `dropout ~ U(0.05,0.80)` draw:
`random` (assigned independently per flight, replicating the evidence file's design) vs
`correlated` (same values, reassigned by rank so the highest dropout lands on the highest
simulated apex height, `max_z` — a real error-driving quantity per backend-dev's own §6
finding, not an invented one). The injection worked: seen_frac~max_z correlation moved
from near-zero under `random` to **-0.86 to -0.87** under `correlated`, on all three
clips.

| clip | arm | n | seen_frac~max_z corr | [0.35,.50) n/med% | [.50,.65) n/med% | **ratio** |
| --- | --- | --- | --- | --- | --- | --- |
| yt_rally2 | random | 351 | -0.17 | 62 / 73.5 | 65 / 46.4 | **1.58** |
| yt_rally2 | correlated | 393 | -0.86 | 85 / 87.9 | 84 / 49.9 | **1.76** |
| am_hard_utr | random | 310 | -0.08 | 53 / 90.5 | 59 / 100.0 | **0.91** |
| am_hard_utr | correlated | 335 | -0.86 | 56 / 100.0 | 80 / 100.0 | **1.00** |
| yt_court | random | 338 | -0.13 | 59 / 90.9 | 62 / 86.9 | **1.05** |
| yt_court | correlated | 368 | -0.87 | 72 / 100.0 | 83 / 87.5 | **1.14** |

All three clips move **in the expected direction** (ratio up) once dropout is deliberately
tied to a real error-driver. **This answers the core worry directly: the negative/
indeterminate finding is not an artefact of a generator that can never show an effect by
construction.** The harness has a pulse.

**But the pulse is weak and camera-dependent, and that is itself a finding worth stating
plainly.** Even under an extreme injected correlation (rho ≈ -0.86), 2 of 3 clips
(`am_hard_utr`, `yt_court`) stay at or barely above 1.0-1.14x — nowhere near 1.5x. Only
`yt_rally2` clears 1.5x, and it already did so in the *random* arm (1.58) before any
injection. Rendering the raw numbers shows why: on `am_hard_utr`/`yt_court` under
`correlated`, both bands' medians sit at or near a **99.999...% ceiling** — once
court-coverage collapses (the mechanism §6 identifies: a high, dropout-heavy flight's
z=0 projection falls outside the runoff box, `smooth_and_fill` bridges flat, the path
integral collapses toward zero, signed error saturates near -100%), the estimate is
already maximally wrong on *both sides* of the 0.35-0.65 band, so a median-based
comparison at that exact window has nowhere further to move on those two camera
geometries. That is a genuine, camera-dependent ceiling on this test's sensitivity, in
addition to the causal-vs-correlational gap backend-dev already disclosed in §"NOT
ESTABLISHED": **a real but weak `seen_frac` effect in the wild could plausibly go
undetected by this exact band window on a low/narrow-hfov mount, even though the harness
is demonstrably not blind in general.**

**Reproducibility gap, disclosed rather than hidden:** my `random`-arm numbers
(1.58 / 0.91 / 1.05) do not match backend-dev's reported primary-population numbers
(1.35 / 0.86 / 0.76) — same qualitative shape (yt_rally2 highest, the other two near or
under 1) but different magnitudes. This is expected given I could not run their literal
script (different RNG sequencing, N=500-800/clip here vs 1200 there, and unavoidable small
implementation differences in exactly how the per-frame arrays are assembled) — it is not
evidence either harness is wrong, but it means the underlying measurement is **more
implementation-sensitive than the file's two-decimal precision suggests.** See check 2.

**Read this as: the positive control PASSES (the harness is not void), but with a
caveat serious enough that a human should see the raw ceiling-saturated rows before
trusting the exact ratio values in §4 to the digit.**

## 2. The population switch

**(a) `pipeline.py:1762` — CORRECTED, minor.** The line-level citation is slightly
imprecise. `speed < MIN_SPEED_KMH` (5.0) is dropped at **line 1759**; `speed > 250.0` is
dropped at **line 1761-1762**, and — not stated in the evidence file — **only for
non-serves** (`if not is_serve and (disp < 0.8 or speed > 250.0): continue`). Serves of
any speed pass this filter (though they can never satisfy `speed_confident` anyway, since
that gate separately requires `not p["is_serve"]`). The harness does not appear to model
serve/non-serve as a distinct population, so applying the `>250` cut universally is a
reasonable simplification, but the citation "pipeline.py:1762 drops speed<5 or speed>250"
conflates two lines and omits the serve conditionality. This does not change the
substance of Arm A/B.

**(b) Both sets of ratios — reproduced qualitatively, NOT numerically.** My own re-run of
the unrestricted (primary) population gives 1.58 / 0.91 / 1.05 (random arm above) against
their reported 1.35 / 0.86 / 0.76. My re-run of the shipped-shot-restricted population
(`5 < est < 250`, analogous to their Arm A/B) gives:

| clip | armB n1/med1 | armB n2/med2 | ratio (mine) | ratio (reported) |
| --- | --- | --- | --- | --- |
| yt_rally2 | 81 / 38.6 | 95 / 32.7 | **1.18** | 1.11 |
| am_hard_utr | 38 / 49.9 | 54 / 34.1 | **1.46** | 1.21 |
| yt_court | 55 / 55.7 | 66 / 29.4 | **1.89** | 0.97 |

`yt_rally2` and `am_hard_utr` land in the same ballpark and direction as reported.
`yt_court` **flips**: their number reads as "no effect" (0.97, essentially N), mine reads
as the single clip closest to G in either harness (1.89, clears 1.5x on its own — though
it is still only 1 of 3 clips, so G still fails by the pre-registration's own ">=2 of 3"
requirement). I cannot determine, without their literal script, which implementation
detail causes the gap — this is genuinely **borderline and a human/researcher should look
at it** rather than take either set of ratios at face value. What I can say confidently:
**in every rebuild I ran (primary, Arm-B-style restriction, and both positive-control
arms), G is refused (never >=2 of 3 clips at >=1.5x)** — that part of the headline is
robust across two independent implementations even though the finer ratio digits are not.

**(c) Reporting I rather than N — CONFIRMED as the correct, conservative call.** The two
populations disagree (unrestricted leans N-ish, restricted does not), and reporting the
weaker/less favorable reading when two legitimate populations disagree is the right
application of the pre-registration's own "I: anything between, including a split across
clips" language, and consistent with the project rule against moving a bar to fit a result.

**(d) Was any OTHER population choice made after seeing results? — YES, disclosed.**
Arms A, B, and C (the shipped-shot filter, the gate's own `<=160` conjunct, and the
`max_z<=1.5m` ground-shot restriction) were all constructed **after** the primary
(as-drawn) population produced its result — the evidence file says so directly ("Omitting
those filters was an oversight in fidelity, not a design choice"). This is disclosed, not
hidden, and framed as a correctness fix rather than a result-shopping exercise, which is
the right framing — but it is still a post-hoc population choice, and it is worth stating
plainly rather than only implicitly: **the population that produced verdict I was chosen
after seeing verdict N.**

## 3. The reject characterisation and the classifier numbers

**CONFIRMED — close numeric match on an independently-built harness with different code,
RNG, and N.** Pooling my own `random`-arm re-run across all 3 clips (N=800/clip, n=1636
usable primary / 1079 shipped-shot-restricted):

| | primary (mine) | primary (reported) | armB (mine) | armB (reported) |
| --- | --- | --- | --- | --- |
| accept-precision | **0.500** | 0.500 | **0.501** | 0.500 |
| base rate | **0.469** | 0.467/0.472 | **0.473** | 0.472 |
| refused-but-accurate, % of refused | **39.3%** | 38.1% | **39.6%** | 39.1% |
| med abs% of refused-but-accurate | **21.2** | 18.8 | **12.5** | 11.8 |
| med abs% accepted (their "accurate" threshold) | 72.5 | 46.9 | 29.9 | 24.7 |

The load-bearing claim — **accept-precision equal to the base rate** — reproduces almost
exactly (0.500/0.469 and 0.501/0.473 here vs 0.500/0.472 reported), on a harness I built
independently from the prose description alone. The refused-but-accurate share of refused
(≈39% both ways) also reproduces closely. The absolute error medians differ somewhat
(21.2 vs 18.8, 72.5 vs 46.9) — consistent with the same implementation-sensitivity noted
in check 2 — but the **shape** of the finding (the gate is at chance as a classifier) is
confirmed, not just asserted. I did not attempt to recompute the exact 173/639 counts
(different N and usable-flight yield make raw counts incomparable across harnesses); the
**fractions and precision numbers**, which are what the "worthless bar" claim rests on,
are what I checked and they hold up.

## 4. The court-coverage rival — real, but partly definitional

**Spearman -0.749 (reported) vs -0.098 (reported for `seen_frac`) — CONFIRMED in shape.**
My independent numbers: court-coverage vs abs% error **-0.820** (primary) / **-0.543**
(armB) vs `seen_frac` vs abs% **-0.079** (primary) / **-0.085** (armB). Same direction,
same enormous gap between the two predictors, on a rebuild that computes court-coverage
as "fraction of the flight span surviving the runoff-box test and `cap_court_jumps`" —
matching the evidence file's own description of the mechanism.

**Scepticism requested, and it is warranted: court-coverage is partly definitional, not
a wholly independent rival predictor.** Building the harness myself makes the mechanism
visible directly: `analytics.shot_speed_kmh` sums pairwise distances over exactly the
points that survive `cap_court_jumps`/`smooth_and_fill` — i.e., over the court-coverage
set. When that set is small, `smooth_and_fill` interpolates flat across a mostly-empty
span and the path-length integral collapses toward near-zero, which is *why* the
correlated positive-control run (check 1) saturates near a -100% signed-error ceiling.
Court-coverage is not measuring "was this a hard shot" independently of how the estimate
is computed — it is close to measuring "how many points fed the very calculation being
scored," which will correlate with error under almost any detector, by construction of
the estimator. That does not make the finding wrong (it is real, reproducible, and useful
context on why `seen_frac` is the wrong quantity), but it means court-coverage is a
weaker *candidate replacement gate* than a rho of -0.75/-0.82 makes it look, precisely
because part of that correlation is mechanical rather than diagnostic. The evidence
file's own §7 already declines to propose it as a replacement and requires the same
held-out sweep before any adoption — that caution is correct, and this check adds the
reason it is necessary: a naive read of "-0.749 vs -0.098, obviously better" would be
overclaiming what a definitionally-entangled correlate can promise on unseen data.

## 5. Scope honesty

**CONFIRMED clean.** Grepped the evidence file directly:
- No replacement threshold is named anywhere; §7 explicitly says "Not authorised:
  changing `0.5`, proposing any specific replacement value."
- `yt_match40` appears only in the EXCLUDED list with the T23 rationale (four clicks off
  every court line) — no number attributed to it anywhere in the file.
- `demo30` appears only in the EXCLUDED list, citing `docs/STATE.md`'s "speeds never
  citable" rule — no number attributed to it.
- `HUD` appears exactly twice, both to say it is barred as a reference, never used as one.
- Clips used: `yt_rally2` (1.4 px), `am_hard_utr` (0.7 px), `yt_court` (2.1 px) —
  **residuals independently confirmed against `docs/calibration.md`**: "KNOWN GOOD (<2.5
  px): yt_match40_pts 0.9, yt_rally2_pts 1.4, yt_court_pts 2.1" and "`am_hard_utr` fits a
  1.74 m camera (hfov 86 deg, 0.7 px — good corners...)" — exact match to all three
  figures quoted in the evidence file.

## NOT ESTABLISHED THIS RUN

- **Whether my rebuild or backend-dev's original harness is "more correct"** where the two
  disagree on band-ratio digits (check 2b) — I do not have their literal script (it lives
  in a different agent session's temp directory, outside this project folder) to diff
  against mine line for line. Flagged as borderline for a human/researcher to inspect the
  raw per-flight rows on `yt_court` specifically, where the two implementations disagree
  in direction, not just magnitude.
- **A clean, mechanism-decoupled statistical-power check** (e.g., directly injecting an
  artificial dependency of estimated error on `seen_frac`, bypassing the court-coverage
  confound entirely) was not run, for budget reasons — it would isolate "is n~150-200/band
  enough to see a clean 1.5x median separation" from "does this specific mechanism (max_z
  -> court-coverage) saturate before the band comparison can see it," which check 1 above
  conflates somewhat. The rank-correlation design used instead is a fair, disclosed
  approximation but not the cleanest possible positive control.
- **The exact 173/639 raw counts** from the evidence file were not independently
  recomputed (different N/usable-yield make raw counts across two different harnesses
  not directly comparable); only the fractions and precision/base-rate numbers they imply
  were checked, and those held up closely.

## Scripts (not committed, not promoted — QA scratchpad only)

`scratchpad/positive_control.py` (band-ratio + positive control, both arms) and
`scratchpad/full_check.py` (pooled classifier/reject-table numbers), run under
`backend/.venv-train/Scripts/python.exe`, in this session's temp scratchpad directory.
