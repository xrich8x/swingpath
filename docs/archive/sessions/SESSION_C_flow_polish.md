> **STATUS: STATUS UNCONFIRMED** — stamped 2026-08-15 during doc cleanup.
> Parts of this (refuse->overlay handoff, setup tool) appear shipped, but no Results section was ever filled in. Verify before re-running.
> This file is the PRE-REGISTERED BRIEF, kept for its gate and reasoning.
> For what actually happened and the current state of play, read
> [SCOREBOARD.md](../../../SCOREBOARD.md) — not this file.

# Session C — Flow polish + camera events in UI + player heatmap

**Kickoff prompt:** `Do Session C (docs/archive/sessions/SESSION_C_flow_polish.md)`
**User brings:** nothing.

## Goal
Close the loose UX ends so a video goes from zero → analyzed without touching a
terminal twice, and surface information we already compute but don't show.

## Scope (three small items, mostly internal engineering — no external research
needed beyond what's cited; the heatmap reuses the proven in-repo approach)
1. **Refuse → overlay handoff.** `run.py analyze` currently prints the
   court_setup_server command when auto-calibration refuses. Add
   `--setup-on-refuse` (default ON for interactive terminals): launch the
   overlay tool automatically with `--video <clip> --out <clip>.court.json`,
   and print the exact re-run command on save. Keep the plain refusal for
   scripted/CI use (`--no-setup-on-refuse`).
2. **Camera events in the dashboard.** `match.calibration.events` already
   records `{frame, kind: reacquired|lost}` from the watchdog. Show them:
   markers on the Broadcast scrubber + a plain-language banner ("camera moved
   around 1:23 — court re-acquired" / "…could not re-acquire, check this
   section"). Data exists; this is pure frontend.
3. **Player-position heatmap.** The shot-landing heatmap (frontend/src/lib/
   heatmap.js, Gaussian-splat → grid → ramp) is done and looks good — REUSE it.
   Missing piece is data: export per-frame `near_court`/`far_court` player
   positions (already in the perception cache) into match.json as a downsampled
   track (~2 Hz is plenty; keep file size sane), then render a second heat
   layer per player with the existing splatter. Additive schema change only.

## Plan
1. Backend: schema additive field `player_tracks` (2 Hz downsample, court
   metres); pipeline writes it; size check on a real match.json (<200KB added).
2. Frontend: heat layer toggle (Player A / Player B / shots) in Court.jsx.
3. Backend: `--setup-on-refuse` wiring (subprocess launch, reuse the ValueError
   path); dashboard event markers.
4. Verify each in the browser (read_page/live interaction; screenshots of this
   app are broken in the pane — verify via DOM + render offline proof images).
5. Commit + push per item.

## Definition of done
- A refused video opens the overlay tool by itself; saving prints the re-run line
- Camera events visible on the analyzed clip's timeline (test with the clip that
  has events, or inject a synthetic event into a match.json copy for the demo)
- Player heatmaps render for both players on a real analyzed clip
- Tests pass; pushed

## Guardrails
- Schema changes ADDITIVE only (schema.py is the single source of truth).
- Downsample tracks — do not dump 30 Hz positions into match.json.

## Results (fill in during the session)
- _pending_
