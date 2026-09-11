# Research brief — tennis court detection fails on indoor shell courts

**Question in one line:** how do you pick the ~8 court lines out of a frame where an
indoor building supplies 20–40 stronger straight lines, when the court lines are already
in the edge mask?

This brief is self-contained. It states what was measured, what has already been tried
and failed (please do not re-propose those), and what an answer has to satisfy.

---

## 1. The system

Single-camera amateur tennis analyser. Court detection produces a homography from the
image to a top-down court plane in metres; everything downstream (shot speed, line calls,
player position) is closed-form geometry on top of it, so a wrong court silently corrupts
every number.

The detector is **classical, not learned**:

1. **Line mask** — a ridge filter: a pixel is "line" if it is `tau` grey levels brighter
   than pixels at ±(line half-width) horizontally **or** vertically, with a low-saturation
   test to keep white paint and drop coloured edges.
2. **Distinct lines** — probabilistic Hough on the mask, segments of one painted line
   merged into a single infinite line in `(theta, rho)` normal form.
3. **Candidate courts** — a court is parameterised by 5 numbers (centre-x, near/far
   baseline y, near/far half-width), seeded from a coarse grid, a camera-pose prior
   learned from labelled courts, and synthetic low-camera poses.
4. **Scoring** — project the whole regulation court and measure agreement `g` with the
   mask (distance transform + local ridge-orientation match), plus a **structural** test:
   each of the 8 regulation lines must claim its **own distinct** real line.
5. **Physical gate** — the winner is re-fitted as a real 6-DOF camera view; if no camera
   can produce that quad, the result is refused.
6. **Accept rule** — fit 8 frames independently, accept only if **≥6 agree**. Below that
   it refuses and a human sets the court by hand in ~30 s.

**The accept rule has never accepted a wrong court** on the 20-clip hand-labelled gold
set. Accepted courts land 3.4–13.9 px from human clicks (at 640 px wide); refused ones
land 25.5–111 px. That precision record is the thing any change must not spend.

Current state: **12 of 20** gold clips auto-accept; **19 of 54** recordings repo-wide.

---

## 2. The failure

Five new recordings of **indoor shell courts** (Philippines — Manila Polo Club, Flexi
League, Hillsborough). Shell is a packed dirt/crushed-shell surface: pale sandy brown,
non-uniform, dusty, with faded white lines. 4K, 30 fps, 20–39 min each, cut into 58 short
clips at serve boundaries.

```
recording       frames  locked  votes   result
flexi_joy            6       3      1   refused
mpc_mixed            8       3      1   refused
flexi_franz          8       7      1   refused
mpc_tuesday          8       0      0   refused
hillsborough         6       2      1   refused
```

**0 of 5.** Note `flexi_franz`: the detector locks a court on **7 of 8 frames** and
scores **1 vote** — it fires every time and finds a *different* court each time. That is
not blindness, it is instability.

---

## 3. What the evidence says the cause is

**The court lines are already in the mask.** Rendering the mask for each failing frame
shows baselines, service lines, sidelines and centre line all clearly traced. The problem
is everything else in the mask:

- roof trusses and purlins
- ceiling strip-lights
- mesh/lattice fence walls behind the baselines
- railings, chairs, balcony edges

Mask sizes are **395,000–1,257,000 pixels**; the Hough stage returns **16–40 distinct
lines**, and the longest, straightest, highest-contrast ones are architecture, not paint.
The structural test then has 8 court lines competing for the wrong candidates.

This is a **known failure family** in this codebase, not a new one. It was first
characterised on an indoor hard court (`am_ntrp45w`) where the detector confidently
produced a court **111 px wrong** on 8 of 8 frames, collapsing the whole 23.77 m court
onto a dark curtain band near the horizon. The five shell venues are that same failure
in force.

**Therefore: this is not a surface problem and a better shell-specific mask cannot fix
it.** The mask is not what is failing.

---

## 4. Already tried and MEASURED — do not re-propose these

Each was built, run against the gold set under a pre-registered gate, and rejected.

| Idea | Result |
|---|---|
| **Widen the seed grid** to cover real court geometry (measured: all 30 human-labelled courts fall outside the shipped far-width range) | Reaches courts the old grid could not, and **gets every one of them wrong** — 26 px and 78 px errors. Failed the gate. |
| **Global mask replacement** — CLAHE local contrast, Lab a\*/b\* chroma fusion, both | Fixes clay, **breaks hard courts**. 13/20 with two wrong courts, or 9/20 and 6/20 by losing clips that already worked. All three failed the gate. |
| **Surface routing to the existing hue-agnostic clay mask** | Bit-identical to baseline. The pipeline already falls back to it. |
| **Broadcast-pose seeding** (27 synthetic 6–18 m long-lens poses) | No change on any clip. |
| **"The court is too small in the frame"** — cropped toward the court and upscaled ×1.18 → ×2.50 | No change; one clip got *worse* as its corners cropped out. |
| **Camera-angle selection** — human-picked top-down-only frames on broadcast | No change, 0 of 6. |

**One thing did work and shipped:** routing the mask by surface (clay gets a
CLAHE/no-saturation-gate mask, everything else untouched). 11/20 → 12/20, nothing lost,
zero wrong courts. It helps clay and does nothing for the indoor-clutter case.

> **⚠ CORRECTION 2026-08-24, after this brief was sent.** The paragraph below is
> **withdrawn**. It scored the criteria at the human's four clicked corners exactly,
> but the gate defines "correct" as anything within **20 px at 640 wide**. Sweeping
> that neighbourhood (`eval/truth_neighbourhood.py`), a court a median **5.8 px** from
> the clicks clears the 0.33 gate on **9 of 10** clips, not 5, and has a positive
> margin on 9 of 10. The criteria do recognise the correct court; they were handed a
> mis-registered version of it. Only `UHf0LeMU2pg` survives as a genuine scoring
> failure. **Any recommendation that ranked "the scoring function is mis-specified"
> on the strength of this paragraph should be re-weighted accordingly.**

~~Also relevant: a search-free diagnostic that scores the criteria **at the human-placed
court** shows that on 5 of 10 hand-calibrated clips the true court scores **0.18–0.31
against a 0.33 accept gate** — the criteria reject the correct answer even when handed
it.~~ And on broadcast frames the agreement score's **global maximum over the entire
parameter space sits on a wrong court**, so no amount of better searching helps there.

---

## 5. Constraints on any answer

- **Precision is non-negotiable.** The gate is: ≥12 of 20 gold clips accepted **and zero
  accepted court more than 20 px from the human clicks**. A change that buys recall by
  admitting a wrong court is rejected. Two changes already died on exactly this.
- **Classical CV preferred.** Python 3.14, OpenCV 4.13, NumPy, SciPy, **CPU-only** for
  inference. New heavy dependencies or a trained model need justification.
- **Offline**, so compute per clip is cheap — currently ~1.8 s/frame, 8 frames per clip.
- **Geometry stays closed-form.** Homography, projection and line calls are exact maths
  and must not be replaced by a learned estimator. Only *perception* may be learned.
- **Refusal is an acceptable output.** Falling back to a 30-second manual court is far
  better than a confident wrong one.
- The learned path already exists as a fallback (a 14-keypoint heatmap CNN, the
  `yastrebksv/TennisCourtDetector` architecture) and scores **20.2% detect on a clean
  held-out split** — it is the weaker path on this footage, not a rescue.

---

## 6. The questions

**Q1 — Ground-plane line selection.** The court is on the ground; trusses and lights are
above the horizon. Is there an established method to rank or filter detected lines by
"could this line lie on the ground plane" *before* a homography is known? Vanishing-point
constraints, horizon estimation from a partial fit, iterative
estimate-horizon-then-reselect schemes — what actually works when the ground plane is
what you are trying to estimate?

**Q2 — Vanishing points as a filter.** Court lines share two vanishing points. So do roof
trusses and fence lattice in a rectilinear building, and often *nearly the same ones*,
because the building is aligned with the court. Is there published work separating
coplanar ground lines from parallel-but-elevated structure in a single image? Does the
distinction survive when both families share a vanishing point?

**Q3 — Which SOTA method handles cluttered indoor venues?** Known landscape: 14-keypoint
heatmap CNNs are the de-facto standard, ML6's study found MAE loss and a fully-conv head
help and that predicting just 4 outer corners is about as good as 16. What is **not**
known here is how any published method performs on *cluttered indoor amateur* footage
specifically. Are there benchmarks or reported results on indoor club courts with visible
roof structure, rather than broadcast or outdoor footage?

**Q4 — Robust model fitting under a high outlier fraction.** With 16–40 candidate lines of
which ~8 are court and the rest are structurally similar architecture, is plain RANSAC
over line correspondences the right tool, or do methods designed for high structured-outlier
regimes (MAGSAC++, PROSAC with a principled sampling prior, graph/clustering-based
grouping) materially change the outcome? Specifically: outliers here are *not* random —
they are long, straight, high-contrast, and share vanishing points with the inliers.

**Q5 — Is the scoring function the real problem?** The measured fact that a correct court
scores below the accept threshold on half of the hardest clips, and that a wrong court can
be the global maximum, suggests the agreement measure itself is mis-specified rather than
under-searched. What scoring formulations are used in the literature for
project-the-model-and-measure-agreement, and are any robust to a mask dominated by
non-model structure? Is a **relative** criterion (best vs next-best, or vs a
random-hypothesis baseline) established practice?

**Q6 — Cheap wins worth knowing about.** Temporal accumulation across frames (the court is
static, the players and lighting are not), background/clean-plate estimation, or
multi-frame line-evidence stacking. A crude version of the last already exists here as a
clay rescue. Is there better prior art?

---

## 7. What exists to test an answer against

- **20 hand-labelled gold clips** — 14 clicked court keypoints per frame, ~315 frames,
  never trained on, with a published per-clip scorecard.
- **10 further clips** with a human-placed 4-corner calibration.
- **62 recordings** repo-wide by surface: 9 clay, ~38 hard, 6+5 shell, 4 grass.
- A search-free harness that scores any change at the known-true court in ~3 min, and a
  full gate run in ~4 min.

**The honest gap:** the shell evidence is 5 recordings and the clay evidence is
essentially one club. Anything that appears to work needs checking on more venues before
it is believed.
