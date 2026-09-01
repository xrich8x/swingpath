# The doubles-alley live-call bug: fixed, and the fix is exercised (2026-09-02)

## What the bug actually did, in call terms

`mobile/live_calls.js`'s `_detectBounce` computed the IN/OUT verdict with
`isInSingles(x, y, this.lineMargin)` **unconditionally**, ignoring
`this.singles`. Two lines below, `_distanceInside` (which produces the
displayed `margin_m`) DID branch correctly on `this.singles`. So in doubles
mode, for a ball that bounced in the doubles alley (inside the doubles
sideline, outside the singles sideline — a real, common doubles shot):

- the call shown on screen was **OUT** (tested against the narrower singles
  box), while
- the displayed margin was **positive** ("+0.50 m inside") — because that
  number came from the correctly-doubles-aware `_distanceInside`.

A self-contradictory call on screen, and the wrong verdict for doubles
scoring: the alley is legally IN in doubles. `backend/swingvision/live.py`
was never wrong — its `in_bounds = is_in_singles(...) if self.singles else
is_in_doubles(...)` ternary was correct from the start; the JS port dropped
the ternary during translation. `mobile/live_calls.js` also had no
`isInDoubles` function at all — only `isInSingles` was ever exported, which
is a large part of how this survived: there was no doubles-bounds check to
even accidentally call.

This was never exercised by any existing test: `verify_live.js`
([[video-free-parity-checks]]) only ever constructs `LiveAnalyzer({singles:
true})`, and the one real cached ball track it replays produced 7 IN / 0 OUT
— no OUT call at all, let alone a doubles one.

## The fix

`mobile/live_calls.js`:
- Added `isInDoubles(x, y, margin)`, a direct mirror of
  `court.is_in_doubles` (was missing entirely).
- `_detectBounce`'s `inBounds` now branches on `this.singles`, mirroring
  `live.py`'s ternary exactly:
  `this.singles ? isInSingles(x, y, this.lineMargin) : isInDoubles(x, y, this.lineMargin)`.

No change to `backend/swingvision/live.py` — see "Is Python itself correct"
below for why not.

## How the fix is exercised (this is the part that matters)

The parity check from the prior task ([[video-free-parity-checks]]) cannot
see this bug: its only cached ball track is singles-only and produces zero
OUT calls. A fix that leaves the doubles branch untested is the same
unexercised code with different contents. So a second, PARITY-labelled
(not accuracy-labelled) check was built:

**`mobile/doubles_alley_parity_cases.json`** — 21 synthetic COURT-PLANE
POSITIONS (not a real ball trajectory; no invented ground truth), chosen to
straddle every boundary that matters: court centre; both doubles alleys at
the exact sideline, ~3mm inside the margined boundary, and ~3mm outside it
(the asymmetric case the bug breaks — IN in doubles, OUT in singles);
fully outside the doubles court on both sides; the near/far baseline
(shared by both court widths) at ~3mm inside/outside its margined boundary.
`expected_singles`/`expected_doubles` per case were **hand-computed from the
raw court constants** (`X_LEFT_SINGLES=1.37`, `X_RIGHT_SINGLES=9.60`,
`X_LEFT_DOUBLES=0`, `X_RIGHT_DOUBLES=10.97`, `Y` 0..23.77, margin pinned at
0.05 m in the file rather than trusting each side's own default) —
independently of running either implementation, so this is not two
implementations grading each other.

Each case is driven through the FULL bounce-detection state machine (not
`isInSingles`/`isInDoubles` in isolation, which were each already correct
individually — the bug was in the wiring around them): a minimal 4-point
synthetic trajectory with segment speeds `[9, 1, 9]` produces one clean
local-minimum bounce exactly at the target position, using an **identity
homography** (pushed "pixel" coordinates equal court metres directly — no
camera, no calibration file, explicitly a synthetic geometry probe).

- **`backend/live_doubles_alley_probe.py`** runs all 21 cases × 2 modes (42
  checks) through `live.LiveAnalyzer`, asserts Python's own actual call
  against the hand-computed expected (a check on Python, not of it — see
  below), and writes `data/output/live_doubles_alley_python.json`.
- **`mobile/verify_live_doubles.js`** runs the same 42 checks through the
  JS port, asserts against the hand-computed expected AND against Python's
  recorded actuals (call + margin within 0.001 m, matching the earlier
  parity bar), and exits non-zero on any divergence.

**Both pass, 42/42, on every case in both modes**, including all seven
alley-type asymmetric cases (`left_alley`, `right_alley`,
`on_doubles_sideline_exact`, and the four ~3mm-from-margin alley variants) —
the exact case the bug broke.

**Regression check that the test is not vacuous:** re-run with the fix
reverted (`git stash` on `live_calls.js` alone), `verify_live_doubles.js`
correctly FAILS 7/42, every failure a doubles-mode alley case, every one
flagged `DIVERGES FROM PYTHON` — confirming the new test actually exercises
the fixed line rather than passing regardless of it.

## Is Python (`live.py`) itself correct? Checked, not assumed.

`live_doubles_alley_probe.py` compares Python's own output against the
hand-computed expected independently — it does not assume `live.py` is
right and only check JS against it. **Result: 42/42 match, no findings.**
`live.py`'s singles/doubles ternary and its `_distance_inside` branch were
both already correct; only the JS port had drifted. Had Python disagreed
with the hand-computed expectation anywhere, that would have been reported
as a finding against the reference itself (per the binding constraint: two
implementations agreeing on a wrong answer is not parity worth having) —
it did not happen here.

## What this still does not cover

- **A real doubles ball trajectory.** These are synthetic boundary
  positions, deliberately not presented as accuracy evidence. There is no
  human-labelled doubles ball track in this repo to test against; inventing
  one and presenting it as ground truth was explicitly ruled out.
- **The live path's serve-box gap** (unrelated, previously noted): `live.py`
  never reaches `analytics.is_in`, so a deep serve is called IN regardless
  of the serve boxes. Still open.
- **Any margin/timing precision beyond 0.001 m / the fixed synthetic
  trajectory shape.** The `[9, 1, 9]` speed profile and `dt=1` spacing were
  chosen for a clean, unambiguous bounce fire — not to probe the bounce-
  detection threshold itself (`min_speed_drop`, `min_call_gap_s`), which
  remains covered only by whatever the original `verify_live.js` track
  happens to exercise.

## Files

- `mobile/live_calls.js` — `isInDoubles` added, `_detectBounce` fixed
- `mobile/doubles_alley_parity_cases.json` — the 21 pre-registered cases
- `backend/live_doubles_alley_probe.py` — Python-side driver
- `mobile/verify_live_doubles.js` — JS-side driver + comparison
- `data/output/live_doubles_alley_python.json` — Python's raw output
