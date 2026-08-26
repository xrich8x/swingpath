# Filling far-court labels by interpolating between anchors

> Evidence for the `filling-far-court-labels-by-interpolating-between` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**MEASURED NEGATIVE, and it closes a shortcut that looked free.** 89% of the 4,087 missing far-court training frames sit in bridges of ≤10 frames with a confident detection on *both* sides, so recovering them from the anchors would have cost no human time. Scored against human gold clicks (n=73 bridged positions, 3 calibrated clips): median error 5–9 px but **p90 46–95 px, max 396 px, and only 63% land within 10 px**. A label that wrong is a Gaussian on empty court — worse than no label. And accuracy is **flat across bridge length** (62 / 60 / 64% for 1-2 / 3-5 / 6-9 frames), so there is no short-gap subset to rescue. Human far-court labels are now *measured* to be required, not assumed. Evidence: data/output/farcourt_label_yield.md
