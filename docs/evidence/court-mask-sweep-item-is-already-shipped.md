# The parked court-mask-sweep item is dead: already shipped 2026-08-21

**QA verdict, 2026-09-02.** Task: determine whether `data/output/court_mask_sweep.json`
(routed variants 12/20 vs baseline 11/20, deliberately not recorded as a gate pass by
the lead pending qa's check) is a real pending gain or already shipped.

## 1. Shipped accept list vs each sweep variant's — do they match?

Independently re-ran `eval/run_eval.py --gold --all --k 8` against HEAD (`cb37352`,
2026-09-02) myself — not reusing any prior run's log. Accepted 12/20:

```
am_classB, am_college, am_fr_sud, am_grass1, am_ntrp30, am_ntrp40,
am_ntrp45_courtlevel, am_rally32short, am_rec30, am_usta40, am_usta45, am_usta60
```

`court_mask_sweep.json`'s three arms, clip for clip:

| arm | n | accept list vs shipped |
| --- | --- | --- |
| `baseline` | 11 | identical minus **`am_rally32short`** (one clip differs, one direction: shipped has it, baseline doesn't) |
| `routed_clay_chroma` | 12 | **identical, zero clips differ in either direction** |
| `routed_clay_clahe` | 12 | **identical, zero clips differ in either direction** |

Both routed variants tie the shipped accept list exactly and tie each other (same
median too: `8.101665063397835` in the JSON, `8.1` in my run — same float rounded).
The one clip that ever differs across all four lists is `am_rally32short`, present in
shipped and both routed arms, absent only from `baseline`.

## 2. My own independent gate run, both halves

Measured against `eval/run_eval.py --gold --all --k 8` (the shipped `courtfit.auto_fit_frame`
→ `courtfit.consensus` → `stacked_clay_fit` path — the same path `pipeline.calibrate_video`
Tier 1 runs), scored against the 20 gold clips' human-clicked corners
(`data/gold/*.court.labels.json`), at commit `cb37352`:

- **Accept half:** 12 of 20 accepted (gate requires ≥12) — PASS.
- **Precision half:** 0 of 12 accepted clips exceed 20 px from the human clicks; median
  8.1 px, range 1.7–13.9 px — PASS.
- Refused/vote<6 clips (not counted toward accept, not scored for precision since not
  accepted): `am_beginner` 30.1, `am_indoor_hard1` 24.9, `am_indoor_hard2` 86.0,
  `am_lk35` 66.2, `am_ntrp45w` 111.0, `am_ntrp50` 69.1, `am_usta45final` refused,
  `am_wingfield_clay` refused. These are consensus_px on frames that never accumulated
  6/8 votes, not "wrong accepted courts" — they never entered the accepted set.

This is a **second, independent confirmation** of the same 12/20, 0 wrong, 8.1 px
median that both the sweep file's routed arms and the lead's own prior
`gate_after.log` (2026-09-01) already showed — three separate runs (mine, the
predecessor's, and the commit-message's own numbers in `f41a489`) now agree exactly.

## 3. Verdict: DEAD — already shipped, no pending gain

`git show f41a489` — "Route the line mask by court surface: clay 11/20 to 12/20,
nothing lost" — 2026-08-21, is the ship commit. Its own message states:

> `routed 12/20 median 8.1 range 1.7-13.9 no wrong PASS ... gained am_rally32short,
> lost none. Re-run against the shipped call sites rather than the sweep's monkeypatch
> reproduces it exactly.`

`calibration.court_line_mask()` at current HEAD is unchanged since that commit:
`clay_line_mask()` (the CLAHE ridge, `CLAY_A_STAR = 140.0` router) for clay frames,
`line_ridge_mask()` unchanged for everything else — confirmed by reading the live
function bodies (`backend/swingvision/calibration.py:971-1030`), not by trusting the
commit message alone.

`data/output/court_mask_sweep.json`'s *current content* was written a week later by
`040df9d` ("Bank the P0 sweep results and the re-run court mask sweep [no-state]",
2026-08-28) — that commit's own message already flags this: "the new arms show 12
accepted against baseline's 11 — NOT recorded as a gate result... that is qa's verdict
to reach against the real gate, not a number to read off a sweep file." Read plainly,
this was a **re-measurement of the already-shipped router**, generated a week after
routing shipped, banked for the record — not a new candidate awaiting a decision.

**Conclusion: the parked item is DEAD.** There is no pending gain to bank. The 12/20
gate pass, the accept list, and the CLAHE-over-chroma choice are all already in
production as of `f41a489` (2026-08-21) and unchanged through current HEAD
(`cb37352`, 2026-09-02). What replaces it on the queue: nothing from this file — the
next court-mask idea has to be a genuinely new candidate, not a re-run of what
`court_line_mask()` already does. The `chroma` vs `clahe` distinction inside the sweep
file is real but immaterial to the gold gate (both arms tie there); it was decided on
the 7-clip drop set (`sAjkpeRq4P4`, 6 votes vs 5) per `f41a489`'s own message, which is
a secondary/non-gating population per the pre-registered gate.

## 4. Any variant differ from shipped AND clear both halves?

No. Both routed variants are bit-identical to shipped on the gold set (same accept
list, same median, same zero-wrong). There is nothing to report per-clip beyond what's
already the shipped state, and nothing to recommend shipping — it is already shipped.

## What every number here was measured against, one sentence each

- The 12/20 accept count and 8.1 px median/1.7–13.9 px range: `eval/run_eval.py --gold
  --all --k 8` scored against the 20 gold clips' human-clicked court corners
  (`data/gold/*.court.labels.json`) — the only ground truth in scope for this gate.
- The sweep file's `baseline`/`routed_clay_chroma`/`routed_clay_clahe` numbers: read
  directly from `data/output/court_mask_sweep.json`, itself produced by the same gold
  human-click scoring per its own commit message (`f41a489`, `040df9d`).
- The commit-message numbers in `f41a489`: quoted as historical record, not
  independently re-derived by me except where cross-checked against my own live run
  above (they match).

## Note found in passing, not investigated further

At the start of this session, `git status` showed uncommitted changes to
`.claude/hooks/agent_cap.py` (+111/-3), `.gitignore`, and a new untracked
`.claude/slots.py` — none made by me, none touched by me. Flagging since a QA verdict
should note the working tree wasn't clean when the check began; this looks like a
concurrent agent's in-progress work on the doorman/cap system, not related to the
court-mask question.
