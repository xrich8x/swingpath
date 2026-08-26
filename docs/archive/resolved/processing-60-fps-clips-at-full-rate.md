# Processing 60 fps clips at full rate — DECIDED 2026-08-15: shipped opt-in as --full-rate

> Evidence for the `processing-60-fps-clips-at-full-rate` row in [docs/STATE.md](../../STATE.md) (Open).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

The product call was made rather than measured further, because the measurement was already complete: `max_gap_s = 0.4` is correct at 60 fps on both native-60fps gold clips, so no re-tune was needed. 60 fps wins the MEASUREMENT — arc reprojection, HUD speed error, bounce error and close-call accuracy all improve, with the figures owned by the **Frame rate isolated from detector dropout** row in What has worked (read them there, not from a copy here) and is a wash-to-negative on DETECTION (yt_rally2 recall +2.7, far_geo −1.7, false-fire +7.7), at 2× perception cost. **Opt-in, not default** — the default stays `auto` until a full match has been run end to end at full rate. See "What has worked".
