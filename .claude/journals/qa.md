# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-10: AUDIT §5 of docs/evidence/innovation-gate-noise-calibration.md

backend-dev built a diagnostic harness AND graded its own output with it (rule 1 shape,
one stage removed). Independent check of TWO claims.

**K3** (the only PASSED verdict, no independent cross-check): reset path silently
discards 902/479/47 frames on am_hard_utr / yt_match40 / yt_rally2, worth
+6.49/+4.93/+3.45 pts of mean seen_frac. Resets 630/384/34, rej-triggered 457/246/24.
Baselines 51.06/54.79/67.96 (first two claimed to reproduce published 51.1/55.0).
CHECK: (a) is "discarded" definition right — read ball.py reset block ~962-970, and the
re-seed branch `if z is not None and accept is False and rej == 0:` right AFTER rej=0;
(b) recompute pts from raw rows independently of summary.json; confirm hit->landing
spans held FIXED; (c) yt_rally2 67.96 has never been published — say so;
(d) T23: yt_match40 calibration known wrong — verdict must not turn on that clip.

**K1**: median d^2 on gold-confirmed real ACCEPTED frames pooled 0.113 (n=291; per clip
0.265/0.122/0.104) vs chi2_2 median 1.386 => ~12x LOW => S over-stated / over-dispersed.
§5.3: R/S median 0.187/0.257/0.304 => P dominates S not R, refuting §1 Leg 2 (R 70-85%
of S), true accept radius 64.4 px @1080p not ~19 px.
CHECK: recompute medians+p90 from raw rows; population = gold-confirmed REAL ACCEPTED;
d^2 captured BEFORE comparison (not censored at 13.8); THE SIGN is load-bearing — is
d^2 vs the PRIOR or a posterior?; accept-radius arithmetic + res_scale (meas_var,
sigma_jerk scaled at ball.py ~808-812) — say which resolution.

SPOT-CHECKS (cheap, no deep dive): instrumented==shipped identity (git-clean ball.py +
does it compare all 3 lists); K2 null control seed random.Random(20260910), 1000 draws,
p=0.105/0.589/0.585 — seeding+draw count as stated?; §5.6 M1 TrackNet "1-2" coast bin
median 19.90 px n=16 — state power honestly (T09).

DELIVERABLE: APPEND ONE section `## 6. Independent verification of §5 (qa)` to
docs/evidence/innovation-gate-noise-calibration.md. Do NOT restructure §1-§5.
STOP-WHEN: that section exists with a K3 + K1 verdict. Then stop. No fixes, no STATE.md,
no commit, no subagent.

BINDING: rule 1 (say what each number is measured against); T09 (required-n; clips carry
only 53/24/26 no-ball frames); T02 (cache provenance); T01 (never quote --frame-step 1);
NOT authorised to restate any bar in §3/§4.

## STATE
- ball.py NOT in git status => unmodified vs HEAD. (spot-check 1, half done)
- Untracked: docs/evidence/innovation-gate-noise-calibration.md,
  .claude/agent-memory/backend-dev/smoother-noise-model-is-over-dispersed.md

## LOG
- 2026-09-10: journal written, task recorded. Next: read the evidence file §1/§3/§5.
- 2026-09-10: read §1/§3/§4/§5 in full + ball.py 780-1015 + gate_diag.py (all 581 lines).
  SOURCE FINDINGS BEFORE RUNNING ANYTHING:
  (a) d2 IS captured against the PRIOR and BEFORE the comparison — gate_diag inserts
      `_d2 = float(y @ solve(S,y))` then `if _d2 <= gate_chi2`. x/P are the propagated
      prior (x = F@x; P = FPF'+Q happen above). K1's sign has no posterior explanation.
  (b) identity check compares ALL THREE returned lists (got[0..2] == ref[0..2]). OK.
  (c) THE RE-SEED BRANCH's `rej == 0` is VACUOUS — rej was set to 0 on the line above.
      Branch fires whenever z is not None and accept is False, for BOTH rej- and
      miss-triggered resets. Behaviourally: the reset frame's own rejected detection IS
      recovered, so "reset_after-1 = 2 earlier frames discarded" is the right definition.
  (d) gate_diag's `quant()` is NEAREST-RANK, not linear-interpolation. Matters only on
      even-n clips (am_hard_utr n=32: 0.265 nearest vs 0.176 linear). Pooled n=291 odd
      -> identical either way.
  (e) DEFECT: gate_diag reconstructs rejection RUNS post-hoc from rej_ctr, and a run
      containing no-detection frames (rej_ctr repeats at 1) gets SPLIT, orphaning the
      first rejection. Undercounts discarded frames. Predicted 914/492/48 vs its 902/479/47.
  (f) SPANS ARE FIXED BY CONSTRUCTION: pipeline.py real_at/ball_seen is consumed ONLY at
      :1862 (seen_frac) and :1849/:1851 (real_landing), both AFTER h/land are set (:1744/
      :1753 from bounces/next_hit) and span_sink.append (:1885) is unconditional.
- 2026-09-10: MY INDEPENDENT RUN (scratchpad/qa_verify.py, own source transform, own
  frame-by-frame pending-list counter, full pipeline replay) — all numbers confirmed:
  instrumented==shipped True on all 3. Discarded 914/492/48 (= exactly 2 x resets_by_rej
  457/246/24) vs backend-dev 902/479/47 -> defect (e) CONFIRMED, undercount 12/13/1.
  K3 points MINE +6.557/+5.142/+3.534 vs theirs +6.492/+4.926/+3.450. Base means
  51.060/54.785/67.963 reproduce theirs EXACTLY. shots 90->90, 86->86, 10->10 and
  spans_identical=True on all 3 -> spans held fixed, confirmed empirically too.
  K1 pooled median 0.11272 (n=291) vs their 0.113 CONFIRMED; ratio 12.30x low.
  CENSORING RULED OUT: a true chi2_2 censored at 13.8 has median 1.387 (0.10% of mass
  above 13.8) -> censoring cannot move a median 12x.
  R/S 0.187/0.257/0.304 CONFIRMED; radius 64.41/36.63/33.71 px @source, am_hard is
  1080p so 42.94 px @720p-equiv (the ~19 px it is compared to is a 720p figure).
  NUANCE TO REPORT: d2 over ALL gate-tested frames is 1.176/0.429/0.237 (am_hard within
  15% of chi2_2's 1.386) — the 12x is a property of the GOLD-REAL subset.
  Raw: scratchpad/qa_verify.json
- 2026-09-10: SIGN TEST (distribution-free, the strongest K1 evidence): 24/32, 83/106,
  131/153, pooled 238/291 below chi2_2's median; required-n 22/32, 62/106, 88/153, 161/291;
  pooled p=1.9e-29. Sign CONFIRMED on every clip separately, not a power artifact.
  M1 POWER: 6/16 within 10px (not 5/16 as §5.6 says); median 19.90 nearest-rank / 17.16
  linear; sign test vs H0(median=10) p=0.45, need n>=44 at the observed 62.5% rate ->
  the KILL is valid (pre-registered point estimate) but "the exclusion rule is right" is
  NOT established at n=16.
  K2 NULL reproduced exactly from the stored populations: 0.105/0.589/0.585, pooled 0.135.
  Seeding + 1000 draws + one-sided >= all as stated.
- 2026-09-10: DEFECT 2, the big one. Published ladder artifact
  data/output/speed_coverage/yt_match40.tracknet.json says mean 54.95 over **186 shots**,
  calib manual+snap reproj 9.112 hfov 26.43. THIS run: 54.785 over **86 shots**, calib
  manual+snap-CLAY reproj 0.011 hfov 91.28, 91 hits vs 192. SAME clip, SAME pts file,
  different court. So §5.5's "reproduces the published baselines to within 0.05 pt" is
  false on yt_match40 both on the number (0.165 pt) and on the population. am_hard_utr IS
  a genuine like-for-like reproduction (51.060 vs 51.06, 90 vs 90 shots, same calib).
  yt_rally2 has NO ladder artifact -> "never published" confirmed by ls + grep.
- 2026-09-10: DELIVERABLE WRITTEN. Section `## 6. Independent verification of §5 (qa)`
  appended to docs/evidence/innovation-gate-noise-calibration.md (line 873, file 869->1240
  lines; §1-§5 untouched, append-only via python 'a' mode after asserting the header was
  absent). git status confirms ONLY .claude/journals/qa.md + that evidence file are mine.
  Memory written: .claude/agent-memory/qa/gate-noise-diag-k1-k3-verified.md + index line.
## TASK STATE: COMPLETE. Nothing outstanding.
