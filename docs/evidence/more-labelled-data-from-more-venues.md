# More labelled data, from more venues

> Evidence for the `more-labelled-data-from-more-venues` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**+57% training frames (26,293 → 41,390) across 8 new venues buys +5.6 pts pooled detector recall** on the ten-clip benchmark (74.8 → **80.4%**, 4.1σ), far_px +6.5 (73.3 → 79.8%), far_geo +5.6. Recall is up on **9 of 10 clips, flat on 1, down on none**. It is generalisation rather than domain-matching: on the **legacy six alone** — venues sharing nothing with the new footage — recall goes 77.0 → **82.2%** (3.1σ), the highest ever recorded on that 1,201-frame set (shipped `ballnet_v21` reads 69.4%). Both arms `--seed 0`, one variable. **RECALL ONLY: false fire did not move** (57.1 → 53.9%, **0.8σ** on 308 no-ball frames; +0.5 pts on the legacy six). Not yet shipped and not yet a product number — see Open. Evidence: data/output/pool_ab.md | 2026-08-13
