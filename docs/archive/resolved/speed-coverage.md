# Speed coverage — and it is CHAIN work, not detector work (superseded by the row above)

> Evidence for the `speed-coverage` row in [docs/STATE.md](../../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

On yt_match40, **speed is not trusted for 95 of 196 shots (48%)**, the largest named reason being losing the ball *after* it lands, which closes the hit→landing span a path integral needs. **MEASURED 2026-08-15, and it settles the scoping question**: of those 95, **77 (81%) had the detector firing past the bounce and the chain discarded it**; only **18 (19%)** had a silent detector. Over ALL 196 shots the detector is present past the bounce on **90%**. (`ball_px` from the committed perception cache is the tracker's output BEFORE `suppress_false_locks` and before the Kalman, so this is exactly the "existed vs survived" split.) So this is **open chain work**, NOT the detector work the Session L stopping rule closed — and it shares a root cause with the dead second-bounce rule below. The −15% bias is average-vs-launch physics and must **never** be corrected away.
