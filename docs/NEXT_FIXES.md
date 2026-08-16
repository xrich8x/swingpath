> **COMPLETE as of 2026-08-15 — this is not an open to-do list.** Every Tier 1-3
> item below was verified done: the stale suppression figure, the hardcoded
> detector string, the "NOT yet committed" note, the README pointing at a
> degenerate calibration, and the untracked evidence .txt files.
> Kept as a record of what was fixed and why.
> **For open work read [SCOREBOARD.md](../SCOREBOARD.md).**

# Next fixes — the maintenance list

Small, bounded corrections. Distinct from
[SESSION_G_pose_proximity.md](sessions/SESSION_G_pose_proximity.md), which is the
research work. Nothing here is a test failure: **209 tests pass in 23 s** as of
2026-08-01.

Ordered by what a wrong answer costs. In a repo whose load-bearing rule is *state what
every number was measured against*, a stale number left in the code is the most
expensive kind of defect — a future session will trust it.

---

## Tier 1 — recorded numbers that are wrong

### 1.1 `pipeline.py` understates the cost of `suppress_false_locks` by 2.5×

[backend/swingvision/pipeline.py:1303](../backend/swingvision/pipeline.py#L1303) reads:

> Measured on yt_rally2 gold: no-ball false-fire 61.5% -> 15.4% at a **3.9-pt recall
> cost** — catches the persistent far-band fixture runs …

E6 part 3 superseded this. At the **shipped** frame step the same filter costs **5.4 pts
on yt_rally2 and 10.0 pts on am_hard_utr**, and the per-gate miss counters name it *the
largest recall cost in the chain*. The 61.5% → 15.4% pair predates both the E6 gate
rewrite and the retirement of the live-ball filter that used to run beside it.

**Fix:** replace with the E6 numbers, name the clip *and the frame step* each was
measured at, and cross-reference the counter table. Comment-only.

**Why it matters:** this is the single largest recall lever in the pipeline. Anyone
reading "3.9 pt" concludes it is cheap and leaves it alone.

### 1.2 `mine_hard_negatives.py` writes a provenance field it does not check

[backend/mine_hard_negatives.py](../backend/mine_hard_negatives.py) hardcodes
`"detector": "BallNet (weights/ballnet.pt)"` into every `hard_negatives.json`
regardless of which checkpoint actually loaded. The existing sets were most likely
mined while `ballnet.pt` was the default, so they are *probably* correctly attributed —
but "probably" is not provenance, and the default has since moved to `ballnet_v21.pt`.

**Fix:** report the real resolved path plus its sha256, matching the perception-cache
stamp format. **This blocks Session G Step 2** — mine again without it and the new
negatives inherit the same unverifiable label.

### 1.3 CLAUDE.md says shipped work is uncommitted

[CLAUDE.md:156](../CLAUDE.md#L156) and [CLAUDE.md:181](../CLAUDE.md#L181) both end
"NOT yet committed (branch work)". That work is on `master` and pushed. Two lines.

---

## Tier 2 — footguns that silently produce wrong output

### 2.1 The documented example points at a known-bad calibration file

[README.md:50](../README.md#L50) and the [backend/run.py](../backend/run.py) docstring
both use:

```bash
python run.py analyze match.mp4 --keypoints court_pts.json --out ../data/output/match.json
```

`data/court_pts.json` exists and is one of the five **KNOWN BAD** files — a **38 px** fit
residual, against < 2.5 px for every good one. CLAUDE.md's own Gotchas say these
"silently break the court overlay + ball gating". Copy-paste the documented command from
the repo root and you get exactly that, with no error.

**Fix:** point both examples at `data/yt_rally2_pts.json` (1.4 px) or a neutral
`your_court_pts.json` placeholder, and link the audit command next to it.

### 2.2 Good and degenerate calibration files are indistinguishable on disk

Eleven `data/*pts*.json` are committed. Six are good, five are degenerate, and nothing in
the filename or the file says which:

| Known good (< 2.5 px) | Known bad (> 10 px) |
|---|---|
| `am_hard_utr_pts` 0.7, `yt_match40_pts` 0.9, `yt_rally2_pts` 1.4, `yt_court_pts` 2.1, `court_pts_refined` 2.3, `eala_pts_auto` 3.7 | `court_pts` 38, `yt_court_pts_refined` 48, `yt_court_pts_doubles` 54, `yt_court_pts_singles` 91, **`demo30_pts` 565** |

Note the trap in the naming: `court_pts_refined` is **good** and `yt_court_pts_refined`
is **bad**, one prefix apart. And `eala_pts_auto` at 3.7 px sits in neither band —
decide whether it is usable and say so.

**Fix:** stamp each file with its audited residual and verdict, or move the bad five to
`data/bad_calibrations/`. Whichever — the check must survive someone tab-completing a
filename. `tools/validate_new_clip.py --audit` already computes the residual; this is
about persisting the answer, not recomputing it.

### 2.3 demo30 needs re-calibrating

`demo30_pts.json` is the worst of the five at **565 px**, fits a 0.2 m camera, and floors
every speed — and demo30 is the canonical dashboard clip. Re-calibrate with
`tools/court_setup_server.py`, audit with `tools/validate_new_clip.py --audit`.

Independent of the ball work, so it can go to its own session. Also listed as Session G
Step 4 — do it in whichever lands first, not both.

---

## Tier 3 — evidence hygiene

### 3.1 Nine eval-ladder results are excluded from git

`.gitignore` re-includes `!data/output/*.json` but not `*.txt`, so these 9 files
(9 KB total) are untracked:

`gold_v21_e6.txt`, `ladder_amhard_e6{,_final,_scaled}.txt`,
`ladder_amhard_s1_acq{4,10}.txt`, `tune_suppress_{amhard,amhard_s2,rally2}.txt`

`data/output/gold_v21_e6.txt` is cited **by name** in CLAUDE.md — the Session F score
sweep reproduces it "digit for digit" — so the repo cites a result it does not contain.
The gitignore's own comment says an eval scored against human gold "is a result, and a
result nobody can reproduce isn't one".

**Fix:** add `!data/output/*.txt`, commit the nine. Videos and images stay ignored.

---

## Tier 4 — portability, low priority

`.claude/launch.json`'s `court-setup` entry hardcodes `--clip am_ntrp40` and the Windows
path `backend/.venv/Scripts/python.exe`; `gold-labeler` invokes `py`. All three are
Windows-only. Harmless today — this is a single-machine project — so only worth doing if
the repo ever needs to run elsewhere.

---

## Deliberately not on this list

- **`ballnet_visweighted.pt` untracked.** Verified byte-identical (md5 `2460e181…`) to
  the tracked `ballnet.pt`. A local duplicate, not a lost training run. No action.
- **Bounce detection, speed bias, brittle vision scoring.** Bounded by single-camera
  geometry and documented as such. Not defects — the −15% speed bias in particular is
  average-vs-launch physics and must never be "corrected".
- **Speed coverage (7 of 14 shots confident).** Diagnosed as detection coverage inside
  rallies, which is exactly what Session G attacks. Not a separate fix.
- **Event metrics measurable on one clip only** (64.7% decided labels on yt_rally2 vs
  5.5% on am_hard_utr). Real limitation, but the remedy is more human labelling, which
  is a session, not a fix.

---

## Suggested order

Tier 1 is three small edits and can land in one commit — do it first, it is pure
correction of the record and 1.2 blocks Session G. Tier 3 is one gitignore line plus a
commit. Tier 2.1 is a two-line doc fix worth taking with Tier 1. Then 2.2, then 2.3 or
Session G depending on which you want to spend GPU time on.

## Verification

- `py -m pytest backend/tests/` — still 209 passing (Tiers 1–3 are comments, docs, and
  gitignore; none touch behaviour).
- After 1.2: mine one clip and confirm the provenance names the real checkpoint + hash.
- After 2.1: run the documented command verbatim from a clean shell and confirm the
  overlay is sane.
- After 2.2: `tools/validate_new_clip.py --audit data/*_pts*.json` and check the stamped
  verdict matches the recomputed residual.
