# researcher — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-10 — INNOVATION GATE / NOISE CALIBRATION

Deliverable: ONE file `docs/evidence/innovation-gate-noise-calibration.md` with FOUR
sections in order: (1) family verdict on the R-calibration line — in or out of the
barred smoother-gate family, unambiguous; (2) ranked 2-4 candidate mechanisms OUTSIDE
the family, each with mechanism / why it separates / falsifier / cost, plus a
"do not build" entry; (3) a DIAGNOSTIC that must run before any build; (4) a
PRE-REGISTERED BAR (coverage + ghost guard + per-frame-recall guard), each stated
against what it is measured on.
NO code. NO Bash (I have none). NO STATE.md edit. No subagent. Do NOT design the
implementation — that is backend-dev's run.
Return in final msg: family verdict, top mechanism, one-line diagnostic.

## STATE — ANALYSIS ESSENTIALLY COMPLETE, file being written. ~7 calls used.

### THE VERDICT I HAVE REACHED (R-calibration line = INSIDE the barred family, DEAD)

Four independent legs, none needing a new run:

1. **S ≈ R, so scaling R IS a gate_chi2 sweep.** ball.py:815-817,857,862. Q from
   `sigma_jerk=1.0` gives Q[0,0]=0.05 px²; with near-zero process noise a CA filter
   converges to least-squares so P[0,0]→small. S = Hm P Hmᵀ + R ≈ R = 25·I.
   d² ≤ 13.8 → |y| ≤ sqrt(13.8·25) = **18.6 px**, matching the brief's ~19 px.
   Scaling R by k scales S by ~k and d² by 1/k — arithmetically identical to raising
   gate_chi2 by k. There is no shape change, only radius. It is a pure WIDEN.
2. **THE CENSUS KILLS IT, and it is already measured.** smoother-gate-backward-readmit
   §3: the adjudicated LOST-rejection population is 9R/9G + 6R/7G + 6R/12G =
   **21 real / 28 ghost pooled = 0.75:1**. That is a HARD CEILING on any widen: admit
   ALL rejects and you still get 0.75:1, against the family's ~7:1 structural rate and
   the ≥3:1 pre-registered bar. Founder's "ghosts sit 208-829 px away" is the SESSION I
   CHAIN-FALSE-LOCK population, a DIFFERENT population from the gate's rejects — §5's
   table shows reject-ghosts with lock errors of 24.0 / 30.3 / 49.8 px, i.e. squarely
   inside the 35-45 px widened radius. The separation argument breaks THERE.
3. **Raising R makes staleness WORSE.** K = P Hmᵀ S⁻¹; bigger R = smaller gain = the
   filter trusts detections less = the model is slower to catch a direction change,
   which is the exact condition under which real detections get rejected.
4. **A gate-widen has been measured in THIS gate already.** Docstring ball.py:686-692,
   depth-aware Q, median reference: "half the frames get LOOSER ... lets more junk
   through the innovation gate (**false-fire 19 -> 27%**)"; tighten-only (p10) held
   false-fire flat at 19.2%. Q≠R mechanically (Q moves bandwidth+gate, R moves
   gate+gain) — DIFFERENT family — but the gate-widening HALF is shared and its one
   measured instance cost +7.7 pts of false-fire for a modest widen.

### THE CODE-READ RESULT THAT KILLS BRIEF-CANDIDATE (b)
`seen_frac` excludes coasted frames by construction, and in ball.py every ACCEPTED
detection is emitted (used[i]=True → accepted_by_seg → emit). Bridged gaps are coasted
and do not count. Therefore **D_smooth (−11.0/−8.1) IS the gate's rejection rate over
span frames, minus reset re-seeds** — not a downstream reset cascade. No run needed.
Consequence: only three routes can move coverage — (i) widen [dead], (ii) make the model
less often stale, (iii) recover rejections into a NEW segment where they are accepted.

### TOP-RANKED MECHANISM (outside the family): REJECTION-RUN COHERENCE
`rej` (ball.py:868, 965-970) counts ANY rejection toward `reset_after=3`, and on trip
re-seeds at the CURRENT frame i, discarding the earlier `reset_after-1 = 2` rejections.
Two defects, one fix, NO widen anywhere:
- a coherent run of ≥2-3 mutually-consistent rejections = a real direction change →
  re-seed RETROSPECTIVELY at the run's FIRST frame, recovering ~2 real frames per reset;
- an ISOLATED junk lock (all 19 chain false locks have **run_len = 1**, memory
  ball-negatives.md / 9-solid-ghost-balls) should not increment `rej` at all — today it
  can force a spurious reset that both EMITS the ghost as a seed (used[i]=True) and
  throws away a converged model.
Escapes the §5 confound: the coherence is fit to the REJECTIONS themselves, not to the
incumbent stale path — the barred signal was distance to the incumbent RTS track.
Falsifier: run-length × real/ghost contingency on the adjudicated rejects. If run length
does not separate, it is dead.

### GRAVITY-SEED IDEA — CHECKED AND DROPPED, do not re-derive
seed() sets a=0 with σ_a²=100 (σ=10 px/frame²). Projected gravity is ~0.44-1.1 px/frame²
at 720p (9.81/30² m/frame² × 40-100 px/m). Already inside the prior by ~10×. Buys nothing.
Also checked: seed v0=400 (σ_v=20) → after one propagation P[0,0]=25+400+25=450, S=475,
so a 40 px/frame post-hit step gives d²=3.4, passes. The seed is fine. Not the defect.

### DIAGNOSTIC I WILL PROPOSE (one run, three clips, no video decode)
One instrumented pass emitting per REJECTED frame: d², consecutive-run length, whether
the run tripped a reset, whether the frame is inside a hit→landing span, gold label if
adjudicated. Yields (a) empirical d² vs χ²₂ on gold-real frames [founder's question,
free], (b) run-length contingency [mechanism falsifier], (c) reset count = prize ceiling,
(d) share of −11.0 pts inside spans. Reuse the backward-readmit run's source-transform
instrumentation (inspect.getsource → exec), which proved identical-output on 3 clips.

### BAR DESIGN NOTE
Coverage is GAMEABLE by exactly the dead move: seen_frac counts an emitted frame without
checking accuracy, so admitting locks 24-50 px off a click RAISES seen_frac while
lowering recall. Therefore bar on MEAN seen_frac (not shot counts crossing 0.5 — that
line is measured only weakly predictive, does-seen-frac-predict-speed-error.md) AND
require recall@10px vs human clicks not to fall. yt_match40 inherits T23.

## DONE — 2026-09-10. ~11 tool calls. If restarted: the work is FINISHED, just report it.

Written: `docs/evidence/innovation-gate-noise-calibration.md` (all 4 sections, in order).
Memory updated: `.claude/agent-memory/researcher/ball-negatives.md`.
Nothing outside the allowlist written. No STATE.md edit, no code, no commit, no subagent.

REPORT LINES:
- VERDICT: R-calibration is INSIDE the barred widen family. Dead. Decisive reason = the
  reject census (21 real / 28 ghost = 0.75:1 pooled) caps ANY widen below every bar this
  family has been held to; and the founder's "ghosts at 208-829 px cannot enter" is the
  wrong population (chain survivors, not gate rejects — reject-ghosts sit at 24-50 px).
- TOP MECHANISM: are 1-2 frame interpolated bridges actually unmeasured? `seen_frac`
  excludes all coasted frames by rule; `eval_model_filters.py:201-208` already accumulates
  `coast_by_gap` ("1-2"/"3-5"/"6-9"/"10+") vs human clicks. Falsifier: `"1-2"` bin median
  > 10.0 px kills it in one command. Rank 2 = rejection-run coherence.
- DIAGNOSTIC: one instrumented pass (source-transform, ball.py untouched) recording d² for
  EVERY detection-bearing frame plus run-length/reset/span/gold-label — and compare the
  MEDIAN and p90 of d² against chi2_2 (1.386 / 4.605), NOT the 99.9th percentile the brief
  proposed, which needs >=1000 clean samples and the gold sets carry 175-258 per clip.

VERIFIED THIS RUN (do not re-verify): `tools/eval_speed_coverage_chain.py` exists (Read);
`tools/eval_model_filters.py` exists, recall = dist<=10.0 px at :199, coast_by_gap at
:201-208 (Read); `pipeline.py:1448-1460` is the ONE call site, passes only fps_eff +
res_scale. **Glob is NON-FUNCTIONAL in this session** — returned "no files found" for paths
I had just read links to. T25. Use Read on known paths only.
ARTEFACT PATH CONFLICT, unresolved and flagged in the file: eval_speed_coverage_chain.py's
docstring writes a FLAT `data/output/speed_coverage_amhard_tracknet.json`; the evidence file
cites a DIRECTORY `data/output/speed_coverage/*.json`. backend-dev must check on disk.

## LOG

- 2026-09-09 prior task DONE: docs/evidence/court-recall-what-would-actually-move-it.md.
- 2026-09-10 new task started; journal rewritten. Read the 3 evidence files + ball.py
  615-1014. Analysis above is complete enough to write the file from.
