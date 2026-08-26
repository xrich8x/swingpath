# am_hard_utr finally has a perception cache

> Evidence for the `am-hard-utr-finally-has-a-perception` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**The clip that kills smoother tunings could never be used to test them.** The last two — `max_gap_s` at 60 fps and `reset_after` — both turned on this clip and neither could be measured on it, because no cache existed and a fresh pass was a multi-hour run nobody had spent. Built on **cuda** with thresh 0.5 to match the device and settings of the yt_match40 / yt_rally2 caches, so the three are comparable rather than a device confound (ML_PRACTICES: argmax can flip near-threshold decisions between devices): 14,499 frames at `frame_step 2`, hfov 86.3, 10,840 locks, 120 shots / 79 rallies. **It immediately earned its keep** — it is the clip that showed the post-bounce diagnosis is a smaller lever on amateur footage than on yt_match40 (see the `bounce_reset` row). Any future chain change can now be replicated on all three calibrated clips instead of two. | 2026-08-15
