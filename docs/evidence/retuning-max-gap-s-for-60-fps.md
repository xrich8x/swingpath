# Retuning max_gap_s for 60 fps

> Evidence for the `retuning-max-gap-s-for-60-fps` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

**GATE FAILS on replication.** 0.60 looks like a clean knee on yt_rally2 (ghost flat at 8 from 0.20–0.60, recall +1.9) and passes the gate there — then on am_hard_utr it costs **+5.6 pts false-fire and +3 ghosts for +0.5 recall**, with no flat region at all. 0.4 stays, and full-rate 60 fps therefore needs **no** rate-dependent gap policy.
