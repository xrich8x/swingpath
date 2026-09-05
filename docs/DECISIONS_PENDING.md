# Decisions waiting on the founder

## FOUNDER RULING 2026-09-04: "I said yes to all." Everything below is APPROVED.

Given in the affirmative to the whole list, without conditions. Recorded here because a
blanket approval that is not written down decays into "did they mean that one too?".

**What it settles, item by item:**

- **Item 0, the int8 ship call.** The three options were mutually exclusive, so a blanket
  yes cannot select among them. Read as authorising **the only one that is work rather than
  a hardware-gated ship decision: option 3, fund the third mitigation** — a per-layer
  activation diff to find where the quantisation erosion first appears, then a precision
  boundary above it. Options 1 and 2 both turn on an A13 fps number nobody has measured, so
  neither can be executed today whatever the answer. **This also settles the rule-6
  ambiguity the item flagged, in favour of proceeding:** it is a deployment-precision
  question, not detector accuracy, and the founder said yes.
- **Item 1, the push bar: LIFTED.** Standing instruction of 2026-08-24 is withdrawn.
  Pushes to `origin/master` (the private `xrich8x/swingpath` backup) are authorised, which
  also unblocks the `workflow_dispatch` Core ML export.
- **Item 0b, Shell/Grass footage.** Approved in the only sense available: those two surfaces
  stay unmeasured on the score layer until continuous footage is recorded. No labelling
  hours are spent trying to work around a recording gap.
- **Item 3, the carried-over list.** Approved, but **five of its seven need human hands**
  (re-clicking `yt_match40`'s corners, reviewing the corner sheets, ~3-6 h of point-boundary
  labelling, re-labelling 8 court gold frames). Approval does not perform them; they move
  from "awaiting a decision" to "awaiting the founder's time", and the protocol for the
  labelling session is now written and costed.
- **Item 4** was never blocked and is unaffected.

**Nothing above overrides a safety rule.** Rule 9 still bars quietly editing human ground
truth, and rule 11 still bars the HUD as a reference; a yes to the queue is not a yes to
those, and neither was asked for.

---

**Do not interrupt to ask these, and do not volunteer them in status reports either.**
Founder instruction 2026-09-02, tightened the same day: keep working, record what needs a
decision, and hand the list over ONLY when the founder asks for it. Mentioning a blocker
unprompted — even as a closing line — is the interruption this file exists to prevent.

Newest first. Each entry says what is blocked, what it costs to unblock, and what
was done instead so the blocker is not also idle time.

---

## −1. Buy one used A13-or-newer iPhone. This is the largest unblock available and it is on no list.

**Raised by pm 2026-09-05 while re-sequencing v1** (`docs/evidence/v1-resequenced-after-court-closure.md` §5).

Three v1 decisions dead-end on physical hardware and **nowhere else**: sustained throughput at
thermal steady state (the honest bar for whether a 60–90 min match is analysable at all), the
int8-vs-fp32 ship call, and the cost half of P0-2 pose affordability. A cloud macOS runner does
not help — it is a VM with no phone attached, and a Simulator number is not a device number.

**The Mac half of this blocker is now DEAD** and should stop being quoted: the Core ML export
runs on a GitHub-hosted `macos-14` runner, the workflow is on `origin/master`, the push bar was
lifted 2026-09-04 and the one defect is fixed. What remains is an iPhone, not a Mac.

**Cost to unblock: one secondhand iPhone 11 or SE 2nd gen.** Why it is urgent rather than a
verification step at the end: if throughput comes back bad, the fix is a **product cut**
(analyse a set not a match; downscale pose; drop a stage), and that cut is far cheaper at
session 15 than at session 45. We are otherwise about to build tens of sessions against three
unknowns an afternoon of testing would retire.

**Done instead, so the blocker is not idle time:** the whole build lane is dispatchable without
it — see §4 of the same file for the ordered queue.

---

## −0.5. Match SCORING is being DEFERRED out of v1; rally clips stay. Confirm or overturn.

**pm call 2026-09-05**, recorded because rule 12 put the score layer back in scope on
2026-08-27 and this narrows it. Full reasoning in
`docs/evidence/v1-resequenced-after-court-closure.md` §2.3.

**Rally segmentation stays in v1** — it ships today, its consumer (clip list, highlights reel)
is built, and a late boundary produces a slightly late clip, not a wrong fact. **Match scoring
leaves v1** — it is one confident fact per match that the user already knows the true answer
to, it has no ground truth of any kind today, and its consumers (a score view, a mobile
correction UI) are **not built**, so it is 8–12 sessions from a screen even with labels in hand.

**The ~3–6 h labelling session is still on the founder queue, with a changed justification:** it
is now the only way to put a number on **rally clip boundaries, a v1 feature that is currently
unmeasured**. The score floor becomes a secondary benefit.

**Two accuracy floors pre-registered before the labels exist (rule 2), and they do not move:**
- Rally clip boundaries (v1): **≥90% of boundaries within 2.0 s** of the human label. Below
  that, the clip list still ships but **dead-time trimming does not**.
- Match score (v1.x, gating whether it is ever displayed): **≥95% of games correctly scored**,
  plus a refusal path. Below that, ship no score at all.

**Cost to overturn: one sentence.** If the founder wants scoring in v1, the queue absorbs
8–12 sessions of consumer UI built before its accuracy floor is known.

---

## 0. The shipped int8 ball graph fails its parity bar on half the gold clips — ship it, or not?

> **UPDATE 2026-09-04 — option 3 was authorised, run, and is MEASURED OUT.** The per-layer
> activation diff refuted its own premise: the failing frame carries the **same** quantisation
> noise as frames that decode correctly (peak rel L2 0.282 vs 0.281 / 0.261; within 4% across
> the encoder, 35% *quieter* at the output). There is no layer where erosion "first appears",
> so there is no precision boundary to install. **The choice is now genuinely between options
> 1 and 2 only**, and both still turn on an unmeasured A13 fps.
>
> **But the finding reframes both:** int8 is not the disease. The exposure is the fp32 model's
> own ~5% top-2 blob margin, which ordinary noise flips — so **fp32 is one bad frame from the
> same error** and option 2 buys less safety than it appears to. The cheap fix this points at
> is a **top-2 margin refusal signal**, which is chain-side, protects both graphs, and directly
> attacks the failure's defining property (a confident wrong lock with no refusal signal).
> That is not a fourth precision arm and rule 6 does not close it.
>
> **MEASURED 2026-09-04, and it complicates option 1.** The margin refusal PASSES its screen on **fp32** (5/5 caught, 2.1% collateral, null p<=0.001) but **FAILS on int8 at every threshold**: on the frames int8 gets wrong its own margin is *wide* - up to 1.00 with no runner-up - because quantisation resolved the race instead of leaving it close. **AMENDED 2026-09-04 - that fp32-only claim is WITHDRAWN as too strong.** It was searched on a threshold grid stopping at t<=0.30, and one bad frame's int8 margin is 0.86. On a wider sweep **int8 CAN police itself**: `blob count >= 2` (equivalently `margin_int8 <= 0.90`) catches **4 of 5** failures at **<5% collateral**, surviving a selection-adjusted and a cluster-preserving null. What this removes is one *absolute* argument against int8. What replaces it is a *quantitative* one: fp32's is a **closeness** test catching **5/5 at 31% precision**; int8's is a **presence** test catching **4/5 at 14-17%** - about half as precise and 80% as complete - and the failure it misses is the single-blob collapse (`yt_rally2/0108`), the one it would most want to catch. **This does NOT settle option 1 vs option 2** and must not be used as if it did: 5 events, effective count ~3. Neither rule is a threshold to adopt, and the downstream cost of refusing ~5% of both-fire frames has **not been measured on either graph**.
>
> **AMENDED 2026-09-04 (same day, backend-dev, second run — the sentence above is too strong).** "FAILS on int8 at every threshold" was searched on the grid inherited from the fp32 sweep, which **stops at t = 0.30**; one bad frame's int8 margin is 0.86 and sits above it. On a wider grid **int8 CAN police itself**: `margin_int8 <= 0.90` catches **4 of 5** at **3.82%** collateral, and the equivalent int8-only rule `blob_count >= 2` catches **4 of 5** at **4.78%**. Both survive a seeded null (exact hypergeometric 1.6e-5 / 3.6e-5), a **selection-adjusted** null over the full 148-rule grid actually searched (p = 0.0000) and a **cluster-preserving** null (p = 0.0010). **So "shipping int8 forfeits the cheap safety net" is withdrawn.** What replaces it is quantitative, not absolute: int8's self-policing is a *presence* test (is there a runner-up blob at all) with **14-17% precision catching 4 of 5**, against fp32's *closeness* test at **31% precision catching 5 of 5** — about half as precise, and it misses exactly the frame where quantisation merged the ball and its confuser into one blob. n = 5, effective ~3; a screen, not a ship. Evidence: `docs/evidence/top2-margin-refusal-signal.md` §8-15.


**Status: measured out. Not blocked on anything technical — this is a product call.**

Six gold clips, 178 contiguous frames each, the shipped `tracknet_ball.int8.onnx` against
the fp32 reference, both through the real mobile decode. **5 of 9 informative clips fail** the pre-registered
no-frame-over-10px condition — widened to the full 10-clip gold set on 2026-09-05, up from 3 of 6. Worst frames: 185.1, 162.5, 75.4 (three consecutive), 70.8, 38.6 px.
Pooled **7 bad frames in 772** where both graphs fire = **0.91%**, essentially unchanged from
the 6-clip 0.95%, so the rate is now stable rather than provisional. **`sAjkpeRq4P4` is
excluded from the denominator: it has ZERO both-fire frames, so its "pass" is vacuous and
counting it would flatter the result.**
Aggregates are excellent everywhere and always were: medians 0.000–0.163 px, null agreement
95.5–99.4%. The failure is a confident wrong lock with no refusal signal, not a wobble.

**Both named mitigations are spent, and neither is a near miss.** `per_channel=True`
produces a byte-identical graph (ORT's `ConvInteger` has no per-channel path at all).
Keeping the final conv in fp32 is a real change that still fails 3 of 4 test frames, and
its failure localises the fault upstream of the output layer — so a third attempt is a
per-layer investigation, not a flag.

**The three options, with what each costs:**

1. **Ship int8 as-is.** ~1 wrong lock per 100 both-fire frames, and on `yt_rally2` they
   came in a 3-frame run, which is long enough to survive the smoother's innovation gate
   rather than be rejected as an outlier. 10.9 MB.
2. **Ship fp32 instead.** 43.0 MB versus 10.9 — **4x** — and no on-device fps has ever been
   measured on an A13, so nobody can say today whether fp32 is affordable there. That
   measurement is itself blocked on absent hardware (see the Mac/A13 item).
3. **Fund a third mitigation.** A per-layer activation diff to find where the erosion first
   appears, then a precision boundary above it. Real work, no guarantee, and it is
   detector-side — which rule 6's stopping rule may or may not cover, since this is a
   deployment-precision question rather than a detector-accuracy one. **That ambiguity is
   itself worth one sentence from the founder.**

**Cost to unblock: one sentence.** Nothing else in the lane is waiting on it.

**Done instead, so the blocker was not idle time:** `yt_match40`'s abandoned pass finished,
three new clips added (the rate exists now and did not before), both mitigations built and
measured to rejection, the mechanism confirmed on every reject inspected, and qa
independently recomputed the pooled numbers and corrected the close-race explanation.

---

## 0b. Shell and Grass have NO eligible footage for point-boundary ground truth

**Status: not blocking anything today. Recorded so it is not discovered later as a surprise.**

The point-boundary protocol priced 9 eligible raw files — **7 Hardcourt, 2 Clay, 0 Shell,
0 Grass**. The queued labelling session only ever targeted Hardcourt + Clay, so nothing
stalls. But it means the score layer will be measurable on two surfaces and **unmeasured on
the other two, indefinitely**, and Shell is the project's largest footage folder (64 clips).

This is a **recording gap, not a protocol gap** — no labelling instruction can fix it.

**Becomes a decision only if Shell or Grass point-boundary numbers are ever wanted.** Then:
record new continuous match footage on those surfaces, or accept they stay unmeasured on
this layer. Cost to unblock: a decision, plus filming if the answer is the first one.

Source: §3 of `docs/evidence/point-boundary-label-protocol.md`.

---

## 0c. The cheapest founder task in the queue: click along court LINES, not corners

**Status: not blocking. It is the single falsifier for a conclusion just reached, and it costs
minutes rather than hours.**

Court auto-detection was closed for v1 on 2026-09-05 on the grounds that the line detector's
~6.4 px disagreement with truth is **near-irreducible** — the same order as human corner-click
noise (~5.8 px). That conclusion is falsifiable by one measurement nobody has made: click a few
points **along** each court line (not the four corners) on a handful of existing gold frames,
so the detector can be scored against direct line truth instead of a corner-derived homography.

- **> 10 px** — the detector carries real, fixable bias. The closure is wrong and a narrow,
  differently-scoped reopening is justified.
- **~5–7 px** — the ceiling is corroborated and the closure stands.

Every court branch this project has funded rests on the assumption this tests. It is the
highest-leverage founder minute available and it is not hours of work.

---

## 1. A push is required before the Core ML export can ever run — and pushes are barred

**Status: the job is ready and cannot be triggered.**

`.github/workflows/coreml-export.yml` already exists, is already on `origin/master`,
and is `workflow_dispatch` (manual) — deliberately, to dodge the 24-hour minimum
lease AWS and Scaleway both charge for any macOS instance under Apple's EULA.

So the Core ML export was **never blocked on hardware**. It is blocked on:
- a standing instruction from 2026-08-24: *"Do not push anything until I say so"*,
  never lifted; and
- **a defect that would have made it fail anyway**, now fixed (below).

**Cost to unblock: one sentence lifting the push bar.** GitHub-hosted `macos-14`
minutes bill at 10x on a private repo, but this job is minutes.

**Found and fixed while it was blocked:** `tools/export_coreml_p0.py` hard-coded
`backend/yolo11m-pose.pt`, which is **not in the repo** — `.gitignore`'s `*.pt`
excludes it and only `ballnet*.pt` is excepted. A CI runner checks out a fresh tree,
so the job would have exported the ball model and then failed at the pose step, which
is the whole reason the job exists. Now falls back to the bare name so ultralytics
fetches the stock checkpoint; a local run still prefers the file on disk.

**Still genuinely hardware-blocked, and not by the same thing:** on-device fps on an
A13. A cloud Mac is a VM with no iPhone attached, and a Simulator number is not a
device number. This project has a standing rule against quoting an unmeasured fps.

---

## 2. ~~`data/tennis_sample.mp4` is missing~~ — RESOLVED 2026-09-02, no video needed

**Closed by frontend-dev.** The ambiguity was not a missing asset, it was a bad
calibration plus a stale harness input, and git history settled it.

`data/court_pts.json` carries its own `_audit` stamp reading **`verdict:
"DEGENERATE"`, 38.1 px residual** — the project's calibration gate already rejects
that file. The harness was reading it. Commit `20a672e` states directly that
`court_pts_refined.json` is "the good version of the same clip". So the
6in/1out-vs-7in/0out question had an answer on disk the whole time.

Parity is now **verified without the video**: `backend/live_replay_novideo.py` drives
`live.push_position` over the cached track directly (it is a pure function; only
`live.stream()` touches cv2), and Python and the JS port agree on **7 calls, 7 in /
0 out with every t_s, xy and margin_m matching to 0.000 m** against a pre-registered
0.001 m tolerance. `verify_live.js` is now a real regression gate that exits
non-zero on drift.

**One premise remains unverified and is recorded as such:** the cached track's
123 frames at 30.0 fps comes from `real_match.json`'s recorded metadata, not from
re-measuring the absent video. Restoring `tennis_sample.mp4` would close that, and
would also exercise the decode path and the doubles branch, neither of which this
check touches.

## 3. Carried over from the pre-existing BLOCKED list (lead journal, 2026-08-29)

Unchanged and still founder-only. Ranked there by leverage:

1. **Re-click `yt_match40` corners** (~5 min) — unblocks P0-2, the top v1 runtime
   risk. Sheet ready at `data/output/corner_audit/yt_match40_corners.png`.
2. **Look at `data/output/corner_audit/`** (~10 min) — 27 sheets built. Two the lead
   cannot settle: on `am_hard_utr` and `sAjkpeRq4P4` the far corners land near the
   NET rather than the far baseline, and a still frame cannot separate those at a low
   mount.
3. **TrackNet: detector-side or chain-side?** One sentence. If detector-side, rule 6
   leaves chain work open and speed coverage unparks to the front of the queue.
4. **~3-6 h of point-boundary labels — DO NOT START** until the researcher's protocol
   lands, or the hours get spent twice.
5. **Re-label 8 court gold frames** (~1 min). Rule 9 — recorded, never quietly fixed.
6. **Is the score layer settled in scope?** It flipped out 2026-08-20, back in
   2026-08-27.
7. **Is a Mac weeks or months away?** A sequencing input — pm would build a different
   plan for a months-long gap.

---

## 4. Dispatchable without the founder — listed so it is not mistaken for blocked

- **Court mask sweep needs a qa gate run.** `data/output/court_mask_sweep.json` shows
  12 accepted vs baseline 11, deliberately NOT claimed: the gate is >=12 of 20 AND
  zero accepted court beyond 20 px, and an accept count alone cannot clear it.

## The speed-confidence bar `seen_frac >= 0.5` has not been shown to predict speed error

Raised by backend-dev 2026-09-03. Evidence:
`docs/evidence/does-seen-frac-predict-speed-error.md` (verdict INDETERMINATE; the
"gate predicts error" bar G is refuted in all four populations tested; as a classifier of
accuracy the gate's accept-precision is 0.500 against a 0.472 base rate).

**The decision, which is a product/sequencing call and not mine:** the whole speed-coverage
target ("37 shots lose their speed to the chain") is a count of shots under this bar. Three
options, none taken:

1. **Leave it.** The bar is unvalidated but not shown harmful; coverage work continues to
   be scored against it as today.
2. **Run the §7 replacement pre-registration** (held-out clips, swept not point-picked,
   >=10-point precision margin over base rate, plus a real-footage confirmation arm). This
   is a fresh measurement run, not a code change.
3. **Re-scope the coverage target** so it is stated against something measured — §6 finds
   court-coverage fraction carries rho -0.749 against speed error where `seen_frac` carries
   -0.098. That is a candidate, explicitly NOT a proposal, and it must face the same
   held-out swept bar before anything is swapped.

No threshold has been changed and no replacement value has been named; the
pre-registration forbids picking one from this data.

---

## `seen_frac` gate — one addition after qa verification (backend-dev, 2026-09-03)

The INDETERMINATE verdict and the options above are unchanged. One fact found while
reconciling qa's rebuild changes what a re-run would have to look like, and it is a founder
call whether to spend the run:

**The adjacent-band ratio the test was pre-registered on is not a stable estimator.** Across
seeds 0-9 it has sd 0.17-0.45 per clip and bootstrap 95% CIs 0.69-2.47 wide that all contain
1.0 (`docs/evidence/does-seen-frac-predict-speed-error.md` §8.3). Under the
shipped-fidelity configuration (`--runoff-m 2.5`, which the original harness got wrong at
4.0) the "gate predicts error" bar would have **passed on 4 of 10 reseeds**. That does not
establish the bar and no threshold is being moved — it means the experiment as designed
cannot decide the question at this sample size, which reinforces INDETERMINATE.

The decision: **option 2 above (run the §7 replacement pre-registration) is still the right
next step, but it must not reuse the ratio-of-medians estimator.** §7 already specifies
accept-precision vs base rate with a >= 10-point margin, which the positive control shows is
sensitive enough to detect an effect the band ratio misses entirely (+14.8 pts vs a band
ratio that moved 1.046 -> 1.142). No change to §7 is needed; this is a note that its choice
of metric was the load-bearing one, and that any future test which reverts to a band ratio
should be refused.

Tooling is no longer a blocker: `tools/seen_frac_speed_error.py` reproduces both prior
implementations exactly and carries `--arm correlated` as the positive control.

---

## Top-2 margin refusal signal: promote the analysis scripts? (backend-dev, 2026-09-04)

`docs/evidence/top2-margin-refusal-signal.md` is reproducible only from two scripts that
currently live in an ephemeral agent scratchpad (`top2_margin.py`, `top2_null.py`), because
promoting them to `tools/` would be a code change and this run was barred from touching
`docs/STATE.md`. They are small and load no model. **Decision needed:** promote them
alongside `backend/ball_parity_margin_census.py` in a run that is allowed a STATE row, or
accept the evidence file as a frozen result. Until then the numbers are re-derivable only
by rewriting the scripts.

**Related, and larger:** the PASS in that file is a *screen*. Section 6.2 shows the margin
identifies the population at risk but does not predict which member flips (at an exact
`area x peak` tie the decode is correct 3 times in 4), and section 5 shows it is blind to
dropout. Whether a refusal that discards ~2 correct answers per error avoided is worth
taking is a **product decision about downstream handling of a refused frame**, not a
measurement — it is not answered by this run and should not be assumed.

## Net-anchor check: two calibrations need a human eye (backend-dev, 2026-09-05)

`tools/render_corner_audit.py --net-anchors` now renders the net TAPE (z=0.914 m)
and both net POSTS over frame 0 of every calibration. The quantitative half
(`band_ratio`) FAILED its pre-registered bars and was not replaced, so two files
cannot be settled by machine:

- `data/output/corner_audit/am_hard_utr_netanchor.png`
- `data/output/corner_audit/sAjkpeRq4P4_netanchor.png`

**Question for the founder:** does the yellow TAPE line lie along the real white
net tape, and do the red sticks stand on the real net posts, in those two images?
Nothing else in the repo can answer it — the corner sheets passed both, and the
texture instrument that would decide them is the one that failed.

Do NOT read the GREEN ground line against the tape: the tape is 0.914 m up and
must image higher. That comparison is what produced the withdrawn "yt_match40 is
still wrong" claim. See `docs/evidence/net-anchor-calibration-check.md` sec 1.

---

## Two frames only an eye can settle — the net-tape height check, 2026-09-05

`tools/net_tape_height.py` measured the white net tape automatically on 15 of 27
calibrations and compared the implied camera height with the fitted one. The
pre-registered bar came out **AGREE** (13/15 within 10%, directions 8+/7-, median
+0.3%) — see `docs/evidence/net-tape-camera-height-consistency.md`. Two clips are
outside it and neither can be closed by machine.

- **`sAjkpeRq4P4`** — **which row is the white tape, 407 or 438?** qa's hand
  brightness profile (`net-anchor-qa-verification.md` sec 3) puts it at 406-409;
  this run's matched filter locks at 437.8, within 0.3 px of where the calibration
  projects it. The two independent measurements of the same object are ~30 px
  apart. At 407 this clip is -33% (worst in the corpus); at 438 it is +5.4%
  (passing). Frame: `data/output/corner_audit/sAjkpeRq4P4_netanchor.png`.
- **`L73ep7JHiJ4`** — **is the bright band 21 px ABOVE the projected tape the real
  net tape, or something else** (a fence rail, a wall line, the far court edge)?
  Strong, tight, repeatable response (z 11.6, ranges agree to 2.0 px) on a clip
  where a pixel is only 1.2% of height, so this is a genuine geometric
  disagreement, not measurement noise. Implied height 2.245 m vs fitted 2.888 m.
  Frame: `data/output/corner_audit/L73ep7JHiJ4_netanchor.png`.

Same caution as the entry above: do NOT read the GREEN ground line against the
tape; the tape is 0.914 m up and must image higher.

**Not blocking anything.** The verdict is AGREE with or without these two, and no
fitted height is being changed either way. What they buy is knowing whether the
residual few-percent spread is net sag or calibration.

---

## Net-post detector: FAILED its bar. Two eye-checks, and one keep-or-cut call. 2026-09-05 (backend-dev)

The net post was ranked the #1 next off-plane calibration reference
(`independent-calibration-references.md`). It is built, swept over the corpus, and it
**FAILS its pre-registered bar: 3 of 11 confident clips within 10% of the fitted
height, against a 2/3 bar.** The tape scores 13/15 on the same corpus with the same
constants. Full write-up: `docs/evidence/net-post-detector.md`. Nothing was gated,
nothing was rejected, no fitted height changed.

**Only an eye can settle these two**, and they are the mechanism behind the whole
failure — I inferred it from numbers alone and flagged it as inferred:

- **`bump_ntrp30`** — **is there a horizontal fence rail behind BOTH net posts?**
  Both posts locked their "top" at `h' ~ 3.46` m above the net line, agreeing with each
  other to 1.5 px, and produced a confident −69.1% camera height. A rail spanning both
  posts at one height is the parsimonious explanation, and if it is right then the
  two-post cross-check (P5) is confounded by exactly the confuser it was built to catch —
  which is a structural objection to the post as an instrument, not a tuning problem.
  Frame: `data/output/corner_audit/bump_ntrp30_netanchor.png`.
- **`UHf0LeMU2pg`** — **same question**: both posts locked at `h' ~ 1.97` m, agreeing to
  2.1 px, giving a confident −45.8%. Frame:
  `data/output/corner_audit/UHf0LeMU2pg_netanchor.png`.

**And one product call that is not mine.** `tools/net_post_height.py` and the
`render_corner_audit.py --net-anchors --post-height` flag are shipped but OFF by default
and documented as a failed diagnostic. **Keep them as a negative result others can
re-run and extend, or cut them?** I kept them because a priced negative is cheaper to
re-read than to rebuild, and because the `%/px` pricing in the tool is reusable by any
future off-plane candidate. Cutting is defensible too.

**Not blocking anything.** The tape remains the only working off-plane reference and is
unchanged. Do NOT show a post-implied height to a user: on this corpus it would have
told someone their 3.73 m camera was at 1.16 m.

---

## The net-occlusion crossover: one product call and one 15-minute ask. 2026-09-05 (pm)

Full reasoning: `docs/evidence/low-mount-implications.md`. Two items, one a decision and
one a task; **neither blocks any dispatchable work today.**

**THE PRODUCT CALL — recommend approve.** Below the ~2.0–2.2 m crossover, does v1
(a) **warn but never block capture**, (b) still ship the shot list, rally clips, dead-time
trim and highlights, and (c) **withhold ball speed, the bounce map and distance run**
rather than caveating them? My recommendation is yes to all three. The reasoning is that a
recording refused courtside is a match lost forever, so capture must never block; while a
speed that leaves the app in a screenshot carries no caveat with it, so a metric number
must be withheld rather than warned. It requires one bit — *framing verified* — stored on
the **match record**, not in view state, which makes it a `schema.py` question. **No new
autonomous calibration gate is proposed**; net posts, fitted hfov, gravity/arc and every
ground-plane statistic are already measured out in STATE.

**THE ASK — ~15 minutes, and it is now the highest-leverage founder item on the board.**
**Record one 2-minute clip from above 2.5 m at the court you actually play on**, using
whatever elevation you can find (fence clamp, tripod on a bench, balcony, raised path), and
note what you had to do to get up there. Two reasons it outranks everything else:

- **This project owns no confirmed metric footage.** The four named mounts are 1.36–1.74 m,
  all below the crossover. Every future speed or bounce measurement needs a clip above it.
- **It is the falsifier for v1's whole setup story.** If a phone cannot get above ~2.2 m at
  a real court with ordinary gear, then the framing requirement is unshippable and v1's
  answer changes to **cut speed and the bounce map entirely** and ship the shot-and-rally
  product. That is a smaller but coherent v1, and it is far cheaper to choose at session 15
  than at session 45.

**Two queue changes this finding makes, recorded so nobody re-asks:**

- **`am_hard_utr`'s corner sheet is DELETED from the eye-check queue.** At 1.74 m it is
  below the crossover and therefore **un-confirmable from a still frame in principle** —
  asking a human to settle it asks for something the geometry says cannot be done. It stands
  on two independent corroborations instead (net-tape height −3.7%, net-anchor internally
  consistent to 0.4 px).
- **`sAjkpeRq4P4` is PROMOTED and is now a ~2-minute ask.** At 3.33 m it is *above* the
  crossover, so the information is in the image and an eye can settle it — and qa measured
  it as the worse of the two (tape offset ~29–31 px *and* ground offset ~22–25 px, same
  direction) despite the automated bar reading it clean. Answerable and probably wrong.

**Unaffected, stated so no session is spent re-screening for it:** the ~3–6 h
point-boundary labelling. A point boundary is a **time, not a place** — it consumes no
homography, so mount height is irrelevant and low-mount clips are fine labelling material.

---

## The live setup criterion is shipped — three calls it hands back (backend-dev, 2026-09-05)

`calibration.net_tape_clearance` now measures, in pixels, whether the far baseline is clear
of the net tape, and `run.py check` prints it. Full evidence and the per-clip sweep:
`docs/evidence/live-setup-criterion.md`. Three things it raises and does not decide.

- **Should `min_elevation = 0.28` be DELETED from `framing_report`?** The derivation says the
  crossover corresponds to a far/near width ratio of **~0.12**, not 0.28, and that 0.28 implies
  a camera **8.5–10.0 m up** — a broadcast tower, while the message it prints advises a 2.5 m
  fence clamp that could never satisfy it. Worse, the ratio does not measure what it claims:
  **Spearman(ratio, clearance) = +0.189** against **Spearman(camera height, clearance) =
  +0.937** over 28 calibrations, and the ratios of "poor" and "good" clips overlap completely.
  I **left 0.28 untouched** — deleting a shipped check is a behaviour change and not this
  run's call — but on this evidence no value of it is defensible. Removal is a one-line change
  plus the two `test_selfcheck` framing tests.
- **What does the app say to a user who cannot reach 2.5 m?** 16 of 28 existing calibrations
  (57%) are below the crossover, all 16 of them phone-height mounts. The criterion tells them
  to clamp to a fence. If no fence exists, there is currently no second answer, and "record
  anyway, results unverifiable" is a product decision rather than a geometric one.
- **One eye-check, cheap and specific.** The criterion locates the *geometric* crossover, not
  the *perceptual* one. Nobody has looked at a frame from a clip near **+5 px** (e.g.
  `mpc_tuesday_p01`, 2.79 m) to confirm the two lines are actually distinguishable there. If
  they are not, the good band belongs higher than +10 px — and that would be a finding, not a
  reason to retune. Rule: the bands stay as pre-registered until an eye says otherwise.
