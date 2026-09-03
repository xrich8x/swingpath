# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — CURRENT (started 2026-09-03): smoother backward-pass re-admit SEPARATION measurement

MEASUREMENT ONLY. Do NOT modify `smooth_forecast`, do not build a re-admit, ship nothing.
Bar pre-registered at the END of `.claude/journals/lead.md`. PASS = >=3:1 real:ghost at the
best single threshold on >=2 of 3 clips AND shuffled-label null under 5% (1000 draws, seeded).
DELIVERABLE: `docs/evidence/smoother-gate-backward-readmit-separation.md`.
STOP-WHEN: verdict written with null control, or ~40 tool calls.

## STATE — where I got to

RULE 3 CHECKED: dead smoother ideas in STATE are max_gap_s, reset_after, `blocked` mask,
bounce_reset, bounce_hypothesis v1/v2. NO backward-pass re-admit. Not a re-proposal.

**STEP 1 ANSWERED — the premise is ALIVE.** Gate = `backend/swingvision/ball.py:863`,
`float(y @ np.linalg.solve(S, y)) <= gate_chi2`, y = z - Hm@x_prior (2-vector px),
S = Hm P Hm' + R, R = I*meas_var*res_scale^2, gate_chi2=13.8 (chi2_2 ~99.9%).
Rejection = `else` at :868 (`rej += 1`, no update); `used[i]=accept=False` at :963.
RTS pass :972-981 recurses only over xf/xs/Pp — never re-reads positions[i], never touches
`used[]`. Emission :1010 keys off used[i]. => backward pass does NOT re-admit. Open question.

STEP 2 plan: instrument by SOURCE TRANSFORM in scratchpad (exec a copy of smooth_forecast
with recording lines inserted), NOT by editing backend/. Verify (out,coasted,conf) identical.

Reuse `tools/eval_speed_coverage_chain.py` build_stage_tracks() = shipped pre-smoother chain
(remove_outliers -> rectify_track -> suppress_false_locks -> gate_ball_to_court -> smoother),
res_scale = height/720.
DECISION: run WITHOUT gate_ball_to_court so NO homography is touched (yt_match40 H is T23-
broken). STATE records the court gate retains 100% of human-labelled ball frames on all 7
clips => dropping it cannot remove a REAL detection from the rejected population, only leave
extra GHOSTS => conservative, makes separation HARDER.

CLIPS: am_hard_utr, yt_match40, yt_rally2 — all three have
`data/output/detector_ab/<clip>.tracknet.perception.json` AND `data/gold/<clip>.labels.json`.

## LOG — newest first


- 2026-09-03 New task started. Journal TASK/STATE rewritten from the completed
  speed-coverage task (that one: DONE, committed c01c9d1, NOT pushed).
- CARRIED FORWARD: `python` is a broken Store shim. Use
  `backend/.venv/Scripts/python.exe` (CPU), `backend/.venv-train/...` (CUDA).
- CARRIED FORWARD: `grep -rn` across repo root TIMES OUT (huge data dirs) — use Grep tool.
- CARRIED FORWARD: `docs/STATE.md` is CRLF on disk / LF in HEAD. `data/output/*` gitignored.

- 2026-09-03 STEP1 done (see STATE): backward pass does NOT re-admit -> premise alive.
  STEP2: instrumented smooth_forecast by SOURCE TRANSFORM in
  scratchpad/reject_separation.py (2 textual inserts: chi2 recording at the gate line,
  xs/used/seg_id export before the return). Identity vs shipped fn asserted in-run.
  KEY CODE FACT: a gate rejection that trips `rej >= reset_after` is RE-SEEDED at
  ball.py:968-970 (`used[i]=True`) — so the LOST population is
  {chi2>13.8} MINUS {re-seeded}. Both counts reported.
  Deliverable skeleton written to docs/evidence/smoother-gate-backward-readmit-separation.md.
  Run is SLOW (>10 min, backgrounded id b3go90t13) — smoother runs twice per clip
  (instrumented + shipped identity check) over up to 14,499 frames.
- 2026-09-03 **VERDICT WRITTEN: FAIL, branch closed.** docs/evidence/
  smoother-gate-backward-readmit-separation.md is complete (all 7 sections + NOT ESTABLISHED).
  0 of 3 clips reach 3:1 (bar needed 2 of 3); best ratios 1.14 / 2.00 / 0.56, pooled 0.93:1.
  Null control p = 1.000 / 0.526 / 1.000 / 1.000 pooled — observed separation is AT CHANCE.
  Mechanism: the nearest reject to the RTS track is a GHOST on 2 of 3 clips, because ghosts
  that continue the stale motion sit ON the smoothed path, while a real detection is rejected
  precisely when the model is stale and xs[i] is smoothed off that SAME stale model
  (RTS blocked at segment boundaries). Same evidence as the forward gate -> confounded.
  TRAP WORTH REMEMBERING: `while not (REPO/"backend").is_dir(): REPO = REPO.parent` spins
  FOREVER from a scratchpad path (drive root .parent == itself). Burned ~25 min and 4 hung
  python procs. Hardcode REPO in scratchpad scripts.
  Second gotcha: smooth_forecast has TWO `return out, coasted, conf` (the n==0 early return);
  match on chr(10)+"    return ..." to hit the real one.
  Artifacts (scratchpad, uncommitted): reject_separation.py, reject_sep.json.
  NOT DONE: docs/STATE.md untouched (NOT-THIS-RUN), no commit.
