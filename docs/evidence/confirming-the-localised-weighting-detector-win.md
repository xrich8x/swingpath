# Confirming the localised-weighting detector win

> Evidence for the `confirming-the-localised-weighting-detector-win` row in [docs/STATE.md](../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**~2h20m of GPU, and it is now well-motivated** — the pooled false-fire effect recorded in the **Localised confuser weighting** row (What has not worked) is large enough to confirm or kill cleanly. Re-run the pair with the new `--seed 0` on both arms so the flag is the only difference, plus a third arm at `--seed 1 --hard-weight 1.0` (~1h10m) to measure how far two *identical* recipes drift — without that floor a paired difference still cannot be sized. Do NOT spend the ~12h on a 40-epoch pair until this comes back.
