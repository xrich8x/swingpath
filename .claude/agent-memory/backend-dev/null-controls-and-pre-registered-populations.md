---
name: null-controls-and-pre-registered-populations
description: Executing someone else's pre-registered gate — why a FAILING null control is the valuable outcome, and how a population described two ways resolves to two different sets
metadata:
  type: feedback
---

Lessons from executing the far-player MOTION gate (2026-08-29, FAILED). These are about
*running a gate someone else wrote*, which is a different job from designing one.

- **A null control that FAILS is what makes a failed gate worth anything.** The motion
  gate's whole design worry was candidate density: with several blobs per frame, "some
  blob is close" is nearly free. Random failed decisively (median 9.265 box-heights,
  2/15, 0.0% of 1,000 seeded draws pass), so the real arm's 5.751 / 7-of-15 is a genuine
  measurement of the hypothesis rather than an artefact. **Report the control's number
  even when the real arm failed** — without it the negative is ambiguous and someone will
  re-propose the idea claiming the test was rigged.
  **Why:** the gate author pre-committed to "if the random control clears the bar about as
  often, the real arm has proved nothing regardless of its own number."
  **How to apply:** run the control on every identity/localisation gate, seed it, and
  additionally report a many-seed repeat so nobody can dismiss the single draw as luck.

- **A pre-registered POPULATION can be described two ways that resolve to different sets.
  Record the discrepancy; do not silently pick.** The gate said "the **15** of 25 contacts
  … within **1.5 box-heights**". In `p0_3_tolerance_sweep.json` those are different: 15 is
  `far_sized_candidate_found_anywhere_in_crop`, and `by_rel_box_h["1.5"]` is 14. Resolve
  it by which number the BAR depends on (the bar read ">=10 of 15", so 15 is load-bearing)
  and report the other reading alongside so the verdict cannot hinge on the choice.
  **How to apply:** before running, reproduce the population count from its own source
  script and check it equals the number in the prose. If it does not, that is a finding.

- **Reproduce the selection rule from the script that produced the published figure, not
  from the prose.** The 15/25 came from `tools/p0_3_tolerance_sweep.py`; its filter
  (`small_enough and not_the_near_player`) and its nearest-by-box-EDGE distance were
  copied verbatim, and a test asserts the two `_edge_dist` implementations agree on 200
  seeded boxes. Same species as [[traps-this-project-paid-for]]'s stale-docstring entry.

- **`movers.py`'s "median ~9 blobs per frame" is PRE-`MAX_PLAYERS`.** After the cap, on
  the 15 `yt_match40` far-end contact frames, it is a **median of 2** (min 1, max 4, mean
  2.53) from ~68 foot points per 31-frame window. Quoting 9 as the post-filter field size
  overstates how hard the null control is by ~4x. Both facts are true; say which one.

- **A bimodal failure is a different finding from a marginal one, and it must be said.**
  Nearest-blob distances were 0.21-0.62 on 7 contacts and 5.75-25.16 on 8 — nothing in
  between. "Close but not close enough" would invite a tweak; "right, or looking at the
  other half of the court" does not. Print the sorted values.

- **A rider with no pre-registered bar ships as characterisation and concludes nothing.**
  Far-player contrast had never been measured, so there was nothing to pre-register;
  inventing a bar after seeing |dL| median 5.96 would be a rule-2 violation. Label it, give
  the distribution, and stop. (Measured: colour separates better than brightness — dChroma
  median 11.71 with a floor of 6.04, while |dL| bottoms out at 0.11 and never reaches the
  surround's own SD of L*.)

Related: [[traps-this-project-paid-for]], [[data-limits-far-end-contacts]],
[[calibration-trap-check-corners-first]].
