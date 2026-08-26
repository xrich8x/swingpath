# Whether more data is what actually caused it

> Evidence for the `whether-more-data-is-what-actually-caused` row in [docs/STATE.md](../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**n = 1 training run per arm.** `--seed 0` on both fixes initialisation and seeds the shuffle, which is a real improvement on Session I's unseeded pair, but the datasets differ in size so batch composition and augmentation draws still differ, and the 9-of-10 per-clip sign test measures *evaluation* noise. Also: each arm's checkpoint is its own best epoch on its **own** validation split (A epoch 6, B epoch 12), and B's val contains the new venues. A `--seed 1` replication of arm B (~1h52m) would size the run-to-run floor; the effect is 4.1σ against evaluation noise, so the question is whether training noise is anywhere near 5 pts.
