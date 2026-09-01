---
name: doubles-alley-bug-fixed
description: mobile/live_calls.js's isInSingles-called-unconditionally bug is fixed and exercised (2026-09-02) — the general lesson on proving a fix actually runs the code it claims to fix.
metadata:
  type: project
---

Fixed 2026-09-02 (`docs/evidence/doubles-alley-live-call-bug-fixed-and-exercised.md`,
`.claude/journals/frontend-dev.md` that date). `mobile/live_calls.js`'s
`_detectBounce` called `isInSingles(...)` unconditionally regardless of `this.singles`
— in doubles mode an alley ball was called OUT with a positive "inside" margin shown
on screen. `isInDoubles` didn't exist in the JS port at all before this fix. `live.py`
was already correct; only the port had drifted during translation.

**The lesson that generalizes, not just the bug:** the existing parity check
([[video-free-parity-checks]]) was singles-only and produced zero OUT calls, so it
could not see this bug — and a coordinator explicitly called out that fixing the code
without extending the test would leave "the same untested code with different
contents." The fix that shipped includes a new parity mechanism
(`mobile/doubles_alley_parity_cases.json` + `backend/live_doubles_alley_probe.py` +
`mobile/verify_live_doubles.js`) that drives the FULL bounce-detection state machine
(not the boundary functions in isolation — the bug was in the wiring around them, and
a unit test of `isInSingles`/`isInDoubles` alone would have passed both before and
after the fix) with synthetic court positions at 21 pre-registered boundary cases,
in both singles and doubles mode. It was sanity-checked non-vacuous by reverting the
fix and confirming the test then fails exactly the alley cases.

**How to apply next time a coordinator hands back "you found it, now fix it":**
1. Before writing the fix, identify exactly which code path is untested and why the
   existing check can't see the bug (here: singles-only input, zero OUT calls).
2. Build a test that exercises the SPECIFIC branch through the real call path, not a
   narrower unit test of a helper function that happens to already be correct.
3. Prove the new test is not vacuous — revert the fix, confirm the test fails, redo
   the fix, confirm it passes.
4. If constructing synthetic input (no real ground truth available), label it as a
   PARITY check explicitly, not an accuracy claim, and pre-register the expected
   values independently of both implementations before running either one.
