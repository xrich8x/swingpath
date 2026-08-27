# qa memory

Inherited 2026-08-28. The gate definitions, known-hard areas and checker quirks are in
this agent's system prompt — read it first; it is the authoritative copy.

## Live results to check against

- **P0-2 pose downscale: FAILED its gate, 2026-08-27.** Far-player detection
  `yt_match40` 11.0% @1280 -> 0.1% @640 -> 0.0% @384; `am_hard_utr` 1.0% -> 0.0% -> 0.0%.
  Near player barely moves. Gate allowed 2 points absolute. Recorded as a measured
  negative; do not let it be re-proposed as untested.
- **P0-3 crop-around-contact: UNMEASURED, not negative.** A first attempt reporting 78.8%
  was invalidated on visual inspection — the 448 px box catches the near player
  regardless, and the contact population was wrong. Any retry needs a correct population.
- **Core ML export needs macOS.** `coremltools`' Windows wheel cannot serialize weights
  (`BlobWriter not loaded`). `.github/workflows/coreml-export.yml` runs it on a GitHub
  Actions macOS runner; untested end-to-end as of 2026-08-28.

## Standing

Never fix what you are checking. Never move a gate to fit a result. A borderline pass is
a pass — say borderline. `docs/TRAPS.md` (T01-T22) is the catalogue of process failures
that have fired here more than once.
