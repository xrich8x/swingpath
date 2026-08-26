# Mining whole-frame hard negatives at all

> Evidence for the `mining-whole-frame-hard-negatives-at-all` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Gate C fails, and it names the root cause.** Purity depends on the base rate, and the training clips are **88.5% ball-present** (they are extracted rally clips). Enrichment: persistence 1.4x, min-segment 6.0x, both 3.7x — against a 10x bar. At the real base rate a mined pool is **43.7% pure at best**, i.e. over half real-ball frames. Every route has died on the same fact: dead-time frames are pure but hold no confusers, and confuser-rich frames are frames with tennis being played. **The whole-frame negative format asks about the FRAME when the useful question is the LOCATION.**
