# Per-rally clips + highlights reel (run.py highlights)

> Evidence for the `per-rally-clips-highlights-reel` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

the last unbuilt product feature. Dead time disappears: every rally becomes a playable clip, ranked deterministically (shot count → top *confident* speed → duration), with a top-3 reel. ffmpeg **stream copy**, so cutting is I/O-bound rather than a 5–10× re-encode. The manifest records requested vs actual start, so "a clip never opens mid-rally" is **checked**, not asserted | 2026-08-08
