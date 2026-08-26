# Tightening the smoother gap to cut ghosting

> Evidence for the `tightening-the-smoother-gap-to-cut-ghosting` row in [docs/STATE.md](../STATE.md) (What has not worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

Pooled, 0.10 s halves ghost frames (21.5% → 11.4%, zero interpolated) but drops recall to **60.3%** — at 60 fps that is the ball drawn on 36 of every 60 frames *during a rally*. It does not remove "insane", it relocates it from dead time to mid-point, where the user is actually looking. Also: single-digit false fire is **not reachable by tuning** — pooled floor is 11.4%, because the 9 solid ghosts are the detector.
