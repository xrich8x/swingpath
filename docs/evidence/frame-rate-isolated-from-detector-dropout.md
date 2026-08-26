# Frame rate isolated from detector dropout

> Evidence for the `frame-rate-isolated-from-detector-dropout` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

30 → 60 fps is worth **+5.8 pts** of close-call accuracy at 1.5 m, +3.2 at 3 m, +1.8 at 12 m, and cuts bounce error **24–35%** — holding at both dropout levels, so it is not dropout in disguise. For scale, a *perfect* detector buys +4.7 / +2.5 / +2.2 at the same heights: **doubling the frame rate we already have is worth about as much, and is free.** Confirmed end to end on yt_rally2 — arc reproj **148 → 91 px**, HUD speed MAE **38.9 → 33.1%** | 2026-08-07
