# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

**Write here DURING the work, after every meaningful step** — a finding, a decision, a
command whose result you would not want to re-derive. You can only write when you call a
tool, so you cannot stream your thinking: the goal is that a kill loses ONE step, not the
whole run. Rewrite TASK/STATE in place; append to LOG; compact LOG when it passes ~30 lines.

This is transient working state. Durable learnings go in `.claude/agent-memory/backend-dev/`, and
findings go in `docs/STATE.md` + `docs/evidence/`.

---

## TASK — what I was asked to do

**Run `bounce_hypothesis` v2 against its pre-registered gate**
(`docs/evidence/bounce-hypothesis-v2-gate.md`, written 2026-08-27 before any code).
pm queue item 4. Items 1,2,3,5 done. The detector A/B above is FINISHED (2ead76a) — do
not redo it.

v1 at full power (10 clips, 1658 clicks, 272 no-ball): P1 PASS 47.0->48.1 (+18),
P4 PASS 9.00:1 (>7 bar), P5 PASS. FAILS P2 (ghosts rise on 5/10) and P6 (replication).
Named defect: `wrong` rises on ball frames (+5 on gold_UHf0LeMU2pg) => reflected state
accepted at the WRONG POSITION, a loosening hiding in `restitution_band`'s y-variance
inflation (`Sb[1,1] += (band*vy_prev)**2` dominates R at large vy; x-gate stays tight,
so right-x/wrong-y passes).

**v2 = replace the band with a discrete set of restitution hypotheses (0.6/0.75/0.9)
each tested at the UNMODIFIED S.** Gate doc says this is preferable to bounding the
inflation. MUST NOT touch gate_chi2, reset_after, max_gap_s, suppress_false_locks (T10).

**Gate = all 6 bars of ball-chain-gate.md PLUS P7: `wrong` must not rise on any clip.**
Run over all 10 cached clips with `tools/eval_chain_gate.py`.

Discipline: failed gate stays failed, no retuning. `4.50:1` is WITHDRAWN — never cite
(hook refuses the commit). Off by default unless every criterion passes. State which
metrics route through the homography. Update docs/STATE.md same commit.

## STATE — where I got to

Read v1 evidence, v2 gate, ball.py `smooth_forecast`, eval_chain_gate.py,
test_bounce_hypothesis.py. Next: reproduce v1's 10-clip table as the baseline before
changing any code.

## LOG — newest first

- 2026-08-29 **ENV: `python` is a broken Store shim. Use `backend/.venv/Scripts/python.exe`.**
  That venv is numpy 2.5.0 / cv2 4.13.0 / torch 2.12.1+**cpu**, cuda False. The chain gate
  runs off CACHED perception (`data/output/*.perception.json`) so **no GPU is needed** for
  this whole task — it is CPU-only. Do not queue GPU jobs for it.
- 2026-08-29 Started item 4. Code facts: v1 branch is in `smooth_forecast`, ball.py ~862.
  De-propagates the prior (vy_prev = x[4]-ay, y_prev = x[3]-vy_prev-0.5ay), reflects,
  re-propagates, gates with `Sb = S.copy(); Sb[1,1] += (band*vy_prev)**2`. On accept:
  `seed(z)`, carry reflected vx/vy, `seg += 1`, accept=True, rej=miss=0.
  `tools/eval_chain_gate.py` prints P1/P2/P4/P5 and the per-clip `wrong` delta column
  (so P7 is readable from it). **P3 (seen_frac shot counts) and P6 are NOT printed** —
  P6 is a judgement over the per-clip rows; P3 needs a separate route. Resolve P3.
  Existing tests: backend/tests/test_bounce_hypothesis.py, 6 tests, incl.
  `test_off_is_byte_identical_to_shipped_default` and `test_flag_is_not_inert`.

- 2026-08-28 **COMMITTED 2ead76a** (previous item, detector A/B). CRLF trap: docs/STATE.md
  is CRLF on disk / LF in HEAD (autocrlf). Normalise the WHOLE file after editing, not
  just the inserted row. `data/output/*` is gitignored — evidence JSONs need `git add -f`.
- 2026-08-28 Detector verdict: SPLIT, does not favour a switch. Export TrackNet first.

- 2026-08-29 **BASELINE REPRODUCES v1 EXACTLY.** `eval_chain_gate.py --bounce-hypothesis`
  over 10 clips reprinted the committed correction table row-for-row: pooled 1658 ball /
  272 no-ball, hits 779->797 (+18), wrong +7, ghosts 86->88 (+2), 9.00:1, rises on 5/10.
  Runtime ~2 min, CPU. So the harness is deterministic and any v2 delta is real.
  NOTE the `wrong` OFF column differs from the 3-clip v1 doc (285 pooled here) — that is
  just the larger clip set, not a discrepancy.

- 2026-08-29 **v2 IMPLEMENTED + REFACTOR PROVED NEUTRAL.** Added
  `restitution_set: Optional[Sequence[float]] = None` to `smooth_forecast`. None =>
  v1 exactly (single `restitution`, `Sb[1,1] += (band*vy_prev)**2`). Non-empty => v2:
  each e tested at the **UNMODIFIED S**, lowest-chi2 passing candidate wins, no
  inflation at all. Wired `--restitution-set` through tools/chain_cache.py and
  tools/eval_chain_gate.py; added P6-input and **P7** lines to the gate report.
  PROOF OF NEUTRALITY: 47 tests pass (test_bounce_hypothesis + test_ball), and the v1
  arm re-run reprints the identical table (779->797, wrong +7, 86->88, 9.00:1).
  New P7 readout on **v1**: pooled wrong 285 -> 292 (+7), rises on **5 of 10** —
  gold_shell +2, gold_clay +1, gold_am +1, gold_UHf0LeMU2pg +5, gold_uR5q2cSM6AY +3.
  So v1 fails P7 on 5 clips, not just the one the gate doc named.
  CAUTION: my P6 line prints only the -2.0 pt recall floor (0 of 10 on v1) — that is
  an INPUT, not the verdict. v1's P6 fail was a judgement at -1.8 pts, inside the
  floor. Relabelled the line so it cannot be misread as "P6 passes".

- 2026-08-29 **### V2 RESULT — THE GATE FAILS. P7 FAILS, P2 FAILS. ###**
  `eval_chain_gate.py --bounce-hypothesis --restitution-set 0.6,0.75,0.9`, 10 clips,
  1658 clicks, 272 no-ball. **Numbers are final — do not re-run to "check".**
    P1 recall  47.0 -> 48.1% (+18/1658)          **PASS**
    P2 ghosts  86 -> 88 (+2), rises on **5 of 10**  **FAIL**
    P4 separation 18 hits / 2 ghosts = 9.00:1     **PASS**
    P5 power   272 no-ball frames                 **PASS**
    P6 replication                                **FAIL** (P2 rises on 5; recall flat
       on 3 clips while +5 on am_hard_utr; per-clip recall floor itself 0 of 10)
    P7 wrong   285 -> 291 (+6), rises on **4 of 10**  **FAIL**
       gold_shell +2, gold_clay +1, gold_UHf0LeMU2pg +3, gold_uR5q2cSM6AY +3
  v2 vs v1 per-clip: gold_UHf0LeMU2pg **-3 hits/+5 wrong -> 0 hits/+3 wrong** (the
  named clip is HALF fixed), gold_am +1 wrong -> 0, gold_L73ep7JHiJ4 +6 -> +4 hits,
  yt_rally2 +1 -> 0 hits. Pooled hits IDENTICAL (+18), ghosts IDENTICAL (+2, same 5).
  **=> THE GATE DOC'S NAMED MECHANISM IS DISCONFIRMED.** v2's y-gate is STRICTLY
  TIGHTER than v1's (unmodified S vs band-inflated S), so if `restitution_band` were
  the cause of the mislocalisation, removing it should have zeroed the `wrong` rises.
  It removed ONE clip of five and 1 of 7 pooled. The mislocalisation is NOT the band.
  **STOPPING RULE DOES NOT FIRE.** Its antecedent is "if v2 FIXES the `wrong`
  regression and P2 still fails". The regression is reduced, not fixed, so the
  condition is not met. Say this explicitly — do not fire it by vibes.

- 2026-08-29 **ABLATION (one variable): single e=0.75 at UNMODIFIED S** — i.e. band
  removed, extra hypotheses NOT added. `--restitution-set 0.75`.
    hits **+21** (v1 +18, v2 +18), wrong **+5** (v1 +7, v2 +6), ghosts +2 / 5 of 10
    (identical in all three), separation **10.50:1**, P7 rises on **5 of 10**.
  TWO findings:
  (a) **Removing the band is the GOOD half; adding 0.6/0.9 is NET HARMFUL** — the extra
      hypotheses cost 3 hits and add 1 wrong vs band-removal alone. "More hypotheses"
      does not help; the gate doc's preferred form is the worse of the two.
  (b) **THE `wrong` RISE IS NOT GATE LOOSENESS.** The single-e/unmodified-S arm is
      STRICTLY TIGHTER than v1 in y and identical in x, and it reproduces the SAME 5
      clips rising, ghosts +2 on the SAME 5. Gate tightness is not the lever.
  HYPOTHESIS FOR THE REAL MECHANISM (verify, do not assert): on accept the branch does
  `x, P = seed(z)`, so the emitted position IS THE RAW DETECTION z, unsmoothed. Every
  acceptance converts "no output" into "raw detector output", and raw output has ~5px
  noise plus tails — some land inside the 10px scoring radius (hit), some outside
  (wrong). That predicts hits and wrong rise TOGETHER from one cause, which is exactly
  what all three arms show (+21/+5, +18/+7, +18/+6). NEXT: confirm on gold_UHf0LeMU2pg
  that the added-wrong frames are bounce-branch acceptances emitting z verbatim.

- 2026-08-29 **`seed(z)` HYPOTHESIS DISCONFIRMED — 0/17 changed frames emitted the raw
  detection verbatim.** The emitted value is RTS-smoothed. But the diagnostic names TWO
  REAL mechanisms (scratchpad diag_wrong.py, 3 clips, 17 changed frames):
  **(1) GHOST ADMISSION ON BALL FRAMES (miss -> wrong).** At every such frame the RAW
  detection was ALREADY far off: gold_shell f226 d_raw=**502.2**, uR5q2cSM6AY f1162
  d_raw=76.0, f882 49.3, UHf0LeMU2pg f1534 40.3, f852 20.2. The reflected hypothesis
  ADMITTED them at the UNMODIFIED S. **This falsifies the mechanism's core design claim**
  ("all 19 chain false locks sit 208-829 px off the track, so a ghost fits NEITHER
  hypothesis"): reflecting vy moves the predicted position far enough that a 502 px-off
  lock fits the REFLECTED model. The second hypothesis has its own false-acceptance
  region. These score `wrong` not `fp` only because a human happened to label a ball
  present on that frame — same object as a ghost.
  **(2) SEGMENT-RESTART DEGRADATION (hit -> wrong).** A well-localised frame gets pushed
  out past 10 px because the branch inserted a segment boundary nearby and the RTS pass
  now smooths a different set together: gold_shell f2146 d_raw=**0.7**, d_off=1.5 ->
  d_on=**11.3**; uR5q2cSM6AY f624 d_raw=5.1, d_off=**0.9** -> d_on=**13.4**.
  NEITHER is the `restitution_band`. Power caveat: 17 frames / 3 clips — characterise,
  do not quantify. The 502 px case is not sampling noise.

- 2026-08-29 **P3 MEASURED, AND IT FAILS.** Re-derived `real_fraction` (a closure, not
  importable) and VALIDATED IT BY REPRODUCTION: OFF arm reprints part 3's committed
  smoother-stage counts EXACTLY — am_hard_utr **69**/120, yt_match40 **124**/196.
    am_hard_utr 69 -> v1 72 / **v2 73** / e=.75 72   BAR >=77  **FAIL, short by 4**
    yt_match40 124 -> v1 127 / **v2 127** / e=.75 127 BAR >=132 **FAIL, short by 5**
  Spans taken from committed match.json `t_hit_s`/`bounce_t_s`, held IDENTICAL across
  arms. Script: scratchpad/p3_seenfrac.py.

- 2026-08-29 **CORRECTION TO A BELIEF I WAS CARRYING — the court gate is NOT dead code.**
  On the GOLD caches it removes locks on **4 of 7** calibrated clips:
  gold_sAjkpeRq4P4 **-674**, gold_uR5q2cSM6AY -43, gold_L73ep7JHiJ4 -30, yt_match40 -5;
  no-op only on am_hard_utr, yt_rally2, gold_UHf0LeMU2pg. My previous item's "0 locks
  removed, 14/14" was measured on the **detector_ab caches (different ball models)** and
  does NOT generalise. Fix agent-memory.
  H-ROUTING VERDICT: the gate runs BEFORE the smoother and the flag only touches the
  smoother, so both arms get byte-identical gate output => **the A/B DELTAS are H-clean**.
  The absolute LEVELS on those 4 clips are H-shaped, and yt_match40's H is confirmed
  wrong (T23). P3 is worse: its hit->landing SPANS come from match.json, i.e. from the
  pipeline's H-dependent bounce detection, so P3's WINDOW POPULATION is H-dependent on
  both clips (yt_match40 broken, am_hard_utr skewed right) even though its delta is not.

- 2026-08-29 **WRITE-UP DONE, 468 tests pass.** ball.py docstring carries the full
  verdict + both named mechanisms; evidence file appended (250 lines); STATE updated:
  new v2 FAIL row + "reflected hypothesis has its own false-acceptance region" +
  "more hypotheses is the WORSE half" + "gate_ball_to_court is NOT dead code";
  retired the Open pre-registration row; corrected the "ball-chain NOT closed" row's
  reasoning. Tests: 13 in test_bounce_hypothesis.py.
  **CAUGHT A VACUOUS TEST BEFORE SHIPPING IT.** My first strict-tightness test passed
  on 40/40 seeded fixtures — but v1 and v2 were EQUAL on all 40, so it proved nothing.
  Swept vy 18-42 x dy 6-44 (100 combos): still 0 binding cases. Reason: a detection the
  bounce branch rejects is often re-seeded a frame later by the ordinary `reset_after`
  path, so EMITTED-FRAME COUNT IS A POOR PROXY FOR BRANCH ACCEPTANCE. Replaced it with
  a test that PINS that negative (do not tune this mechanism on the fixture), and
  verified it is sensitive: 6/12 differ if the set uses a wrong e.
  REMAINING: commit (CRLF-normalise STATE), update agent-memory.
