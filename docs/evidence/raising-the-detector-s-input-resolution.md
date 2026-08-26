# Raising the detector's input resolution

> Evidence for the `raising-the-detector-s-input-resolution` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**Gate B FAILS on both clips.** At the detector it looks like a large free win — 512x288 → 640x360 is **+8.2 pts far_px**, with operating points that dominate the shipped one outright (same precision for +5.4 recall, or same recall for −14.2 false-fire). End to end the shipped setting **dominates every variant**: the chain was already removing those false fires, so the precision gain is absorbed and the recall gain arrives as extra SOLID ghosts (5→7 on yt_rally2, 1→5 on am_hard_utr). E3f's "per-frame recall is not the bottleneck" still stands. Evidence: data/output/phase0_ball_ceiling.md
