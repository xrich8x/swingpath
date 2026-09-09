# Calibrations as they stood before the 2026-09-09 re-audit

Copies, not moves. The live files are untouched. These exist so that if any calibration is
re-placed, the placement it replaced survives as a record rather than being quietly
overwritten — `CLAUDE.md` rule 9: *mislabels get recorded, not fixed*.

This directory is a **subdirectory on purpose**. `eval/run_refs.py:132` globs
`data/*_pts*.json` **non-recursively**, so nothing here can ever be picked up as a
reference and scored against.

## Provenance of these files, and why they are suspect

Most were placed during a seven-commit agent calibration session on 2026-08-11/12 in which a
Claude agent placed the corners **and was the sole verifier of its own placement** — see
`docs/TRAPS.md` T26 and `docs/evidence/calibration-provenance.md`. None carries a
`_provenance` block, because the field did not exist until 2026-09-09.

## The founder's verdicts, judged across all 8 evaluation frames

Judged 2026-09-09 with the earlier frame-0 verdict hidden, after the discovery that every
original sheet had been rendered on frame 0 — often a title card or a different camera setup
from the frame the corners were placed against.

| clip | verdict | note |
| --- | --- | --- |
| `HoHxFSX_gLk_s1` | misplaced | multi-shot: 3 cut frames of 8, M_win 101.9 px@640 |
| `HoHxFSX_gLk_s2` | misplaced | multi-shot: 2 cut frames of 8, M_win 81.2 px@640. Was marked *correct* on the frame-0 sheet — a false exoneration qa predicted in advance |
| `HoHxFSX_gLk_s3` | misplaced | contains two different venues. Not `_exact`, so outside the scoring pool |
| `bump_ntrp30` | misplaced | clean cut at frame 508. Untracked, and in a subdirectory the pool glob never scans |
| `A7vXlWIlyrI` | mixed | monochrome intro frame at a different zoom |
| `CYqapSq5llo` | mixed | |
| `UHf0LeMU2pg` | mixed | |
| `uR5q2cSM6AY` | mixed | |
| `bump_ntrp30b` | mixed | was marked *correct* on the frame-0 sheet — the second predicted false exoneration |
| `sAjkpeRq4P4` | **holds** | falsely accused by the frame-0 sheet; placement is sound. The lead's own spot-check had wrongly confirmed the accusation |

## Status

**No calibration has been re-placed.** All four "misplaced" clips are multi-shot, so a single
set of four corners cannot describe them, and re-placing on one frame would reproduce the
defect the review just exposed. The open question — whether each clip contains one camera
setup covering at least 6 of its 8 sampled frames, the project's own `ACCEPT_VOTES` bar — is
measured in `docs/evidence/clip-shot-map.md`. The outcome is a drop-or-restrict decision for
the founder, not a labelling session.
