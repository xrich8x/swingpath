# Mining suppress_false_locks' rejections as hard negatives

> Evidence for the `mining-suppress-false-locks-rejections-as-hard` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**GATE FAILS, and it corrects an over-attribution.** A first estimate of 77.3% catch was withdrawn — it differenced raw against the FULL chain, crediting suppression with the tracker gates' work too. Measured in isolation on matched populations: persistence 7.5% catch / 5.7% collateral (it costs more real balls than confusers it catches — it detects things that hold still, and these move), min-segment 32.5% / **2.4%**, both 40.0% / 8.1%. Catch tops out 20 pts under the bar. **Three distinct automatic criteria have now failed** — skeleton position, racket box, trajectory plausibility — so there is no cheap automatic signal separating a swung racquet from a ball. Evidence: data/output/phase0_ball_ceiling.md
