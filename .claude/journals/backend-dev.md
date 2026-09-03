# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.**

---

## TASK — CURRENT (started 2026-09-04, second task of the day)

Execute lead PRE-REGISTRATION "least-squares over ALL line correspondences"
(last section of .claude/journals/lead.md).
Target: STATE joint-correspondence row — given the TRUE line-to-model assignment the
solver reconstructs a median 17.1 px@640 vs shipped 8.1 px. Test whether line-based
least squares over ALL matched lines beats the exact-4-point fit, ONE VARIABLE (fit only).
BAR: PASS <=10.0 px@640 median; FAIL >13.0 px (=> branch dies on a FIT CEILING);
INDETERMINATE 10.0-13.0. Per clip AND pooled.
MANDATORY CONTROL that gates everything: recompute the exact-4-point median in the SAME
run on the same clips/assignments. If it does not reproduce ~17.1 px -> SAY SO AND STOP.
DELIVERABLE: docs/evidence/least-squares-court-fit.md
STOP-WHEN: verdict+control written, or ~40 tool calls.
NOT-THIS-RUN: correspondence SEARCH (C6 cost, 22-of-30 kills), shipped court path,
shipping, editing docs/STATE.md, git commit.

## STATE — 2026-09-04 — TASK COMPLETE

DELIVERABLE SHIPPED: docs/evidence/least-squares-court-fit.md (full, 6 sections + a
"what this closes" + "NOT ESTABLISHED").

CONTROL PASSES: exact-4-point recomputed = 17.10 px@640, n=13, survivor SET identical to
data/output/corr_attrib.json, max per-clip |diff| = 0.00 px. Harness is faithful.

VERDICT: **FAIL** against the pre-registered bar (>13.0 px).
  exact 4-point 17.10 | LS-geom 19.80 | LS-DLT 73.50   (bar applied to the BETTER = LS-geom)
  TUNE n=8: 19.00 / 23.50 / 123.37   SHELL n=5: 6.39 / 6.79 / 73.50 — both pools fail.
  LS-geom better on 7, worse on 5, tied 1; paired Wilcoxon p=0.97 (no direction at all).
MECHANISM (the part that closes it): LS-geom lowers the line objective below the exact
  fit on 13/13 AND below the HUMAN homography on 13/13 (3.01 vs 6.44 px rms). The
  detected lines do not agree with the true court better than ~6.4 px, so the best fit to
  those lines is NOT the true court. The ceiling is the LINE EVIDENCE, one stage upstream
  of the fit. => joint-correspondence branch dies on a fit ceiling; C6 cost and the
  22-of-30 (both SEARCH problems) are no longer worth paying for.
Artifacts: eval/corr_ls_fit.py (new), data/output/corr_ls_fit.json (new).
No STATE row (lead's), no commit, no shipped-path change.

## LOG — this task

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
