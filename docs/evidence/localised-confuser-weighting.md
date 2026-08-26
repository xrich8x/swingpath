# Localised confuser weighting (Session I)

> Evidence for the `localised-confuser-weighting` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**PRODUCT GATE FAILS — pooled solid ghosts 14 → 15 (+1) at flat recall (69.2 → 69.0%).** Ninth failure at the ghost ball. **BUT THE DETECTOR IMPROVED, on 6 of 6 gold clips**: false fire 53.9 → **42.2%** pooled (−11.7 pts, 110 → 86 of 204 no-ball frames, 3.4σ) at *higher* recall (79.9 → 80.4%) and far_px (80.9 → 82.5%) — the operating point moved outward on both axes, not a precision-for-recall trade. **NOT ATTRIBUTABLE YET:** one training run per arm and the trainer had **no seed**, so the arms differ by initialisation and batch order as well as by the flag; the 6-clip sign test measures evaluation noise, not training noise. `--seed` now exists so a future pair is paired. Evidence: data/output/session_i_ab/results.md
