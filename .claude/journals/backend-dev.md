# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK - CURRENT (started 2026-09-04, THIRD task of the day)

Lead PRE-REG "an int8-COMPUTABLE refusal signal" (last section of .claude/journals/lead.md).
Q: does ANY int8-graph-computable quantity flag its own bad frames? Candidates named before
looking: winner absolute AREA, winner PEAK, BLOB COUNT, winner AREA x PEAK.
BAR: PASS = some single quantity, some threshold, catches >=4/5 bad at <=5% collateral on
the 523 correctly-decoded both-fire frames. Both halves. FAIL = anything else => int8 cannot
police itself.
MANDATORY: (1) seeded 1000-draw null; (2) SELECTION-ADJUSTED null - each draw searches the
SAME candidate x threshold grid. REPORT PRECISION too (fp32 passed at 31% = risk gate).
Power: n=5 bad, effective ~3. PASS is a SCREEN not a ship.
DELIVERABLE: section "Can int8 police itself?" appended to
docs/evidence/top2-margin-refusal-signal.md
STOP-WHEN: candidates + both nulls measured & written, or ~35 tool calls.
NOT-THIS-RUN: decode/shipped changes, shipping, 4th precision arm, re-running int8 inference,
editing docs/STATE.md, git commit.

## STATE - 2026-09-04 - IN PROGRESS

Reusing scratchpad/top2_margin.py + top2_null.py (this session scratchpad, both intact).
Plan: new script int8_self.py -> extract int8 blob features (area1,peak1,k8,score1) with the
SAME decode guard (top blob centroid == int8_xy in js_results.json), exhaustive threshold
sweep both directions, then nulls A (fixed t) + B (selection-adjusted over the FULL grid
actually searched, incl. both directions).

## LOG - previous task (least-squares court fit, COMPLETE)

- CARRIED FORWARD: `python` is a broken Store shim. Use backend/.venv/Scripts/python.exe
- CARRIED FORWARD: `grep -rn` across repo ROOT times out (it walks .venv) — grep with an
  explicit dir list (eval/ tools/ backend/swingvision/ docs/) is fast.
- CARRIED FORWARD: Grep/Glob TOOLS have returned false "no matches" this session; bash grep.
- CARRIED FORWARD: long markdown via heredoc FAILS; use the Write tool for long docs.
- CARRIED FORWARD: bash /tmp is NOT visible to Windows python.exe — use scratchpad abs path.
- eval/ is OUTSIDE the mobile audit scope (desktop harness) — fine to edit for measurement.
- Harness written: eval/corr_ls_fit.py. CONTROL REPRODUCES PER-CLIP EXACTLY vs
  data/output/corr_attrib.json (am_classB 5.57, am_usta45 12.88, CYqapSq5llo 50.49,
  hillsborough_p02 4.51). Trustworthy.
- v1 objective was BROKEN: point-on-line using the world segment ENDPOINTS blows up when
  an endpoint projects near/behind the horizon — rms under the TRUE homography was 204 px
  on hillsborough_p02. An objective the truth does not minimise cannot test anything.
  FIX: reverse the direction — project the MODEL line into the image (l_i = H^-T l_w,
  always finite) and measure distance from sample points on the FRAME-CLIPPED DETECTED
  line. Depth-safe, and uses evidence only where the line was actually seen.
  Acceptance test for the objective itself: rms_truth must be a few px, not 200.
- CYqapSq5llo has 2/2 matched lines so LS == exact by construction (50.49 both). Internal
  control that the two arms share the same assignment.
- Full run: 40 clips, 11 s, 13 survivors. Numbers in STATE above.
- TASK COMPLETE 2026-09-04.

## LOG - this task (int8 self-policing)

- Prior task COMPLETE: LS court fit FAIL 19.80 px, ceiling is the LINE EVIDENCE. Shipped.
- fp32 rows already on disk: scratchpad/top2_rows.json (has m32/k32/top1/area1/peak1 for fp32
  only). int8 features NOT in it -> re-extract from int8_heat_*.bin (cheap, no model).
- EXTRACTION DONE. 528 both-fire, 5 bad, int8 guard failures 0. Files:
  scratchpad/int8_self.py, int8_self_null.py, int8_self_rows.json.
- RESULT: area1 / peak1 / score1 all FAIL flat (0 catch at <=5% collat). Bad frames sit AT
  the median of every one: area1 12-13 (med 12), peak1 242 (= the MAX and the mode), score1
  2904-3146 (med 2904). "Small winner" is REFUTED.
- k8 <= 1 (the PRE-REGISTERED mechanistic direction) FAILS hardest: 1/5 at 95.2% collateral,
  because ~94% of both-fire frames have exactly one blob.
- k8 >= 2 (OPPOSITE direction) PASSES: 4/5, 25/523 = 4.78% collat, precision 13.8%.
  Misses yt_rally2/0108 - exactly the frame the pre-reg named as the single-blob case.
- CORRECTION to sec 3.2 of the doc: the earlier "int8 margin FAILS at every threshold" used
  the fp32-inherited grid that STOPS AT 0.30. Wider sweep: m8<=0.90 catches 4/5 at 3.82%
  collat, precision 16.7% -> PASSES. m8<=0.99 is EXACTLY k8>=2. Same mechanism: a runner-up
  EXISTS, not that the race is close.
- NULLS all separate: A exact hypergeom 3.6e-5 (k8) / 1.6e-5 (m8<=0.90), perm p=0.0000;
  B selection-adjusted 108-rule grid p=0.0000; B' extended 148-rule grid p=0.0000;
  C cluster-preserving fixed-rule p=0.0010 (max 4 in 1000), C' extended p=0.0000.
- CONFOUND to report: k8>=2 rate is 11.3%/10.7% on the two clips holding the failures vs
  1.1-3.4% on the other four. Null C prices per-clip counts and still separates.
- NEXT: write sections 8-15 into docs/evidence/top2-margin-refusal-signal.md.
