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

## −1. ~~Buy one used A13-or-newer iPhone~~ — **RESOLVED 2026-09-09: the founder has an iPhone 17.**

> **The device obstacle is closed. The decisions are NOT yet measurable, and this item's own
> framing was wrong.** An iPhone 17 is far above the A13 floor, so the hardware half is done. But
> the three decisions — sustained throughput at thermal steady state, the int8-vs-fp32 ship call,
> and the cost half of P0-2 pose affordability — do **not** dead-end on hardware "and nowhere
> else", as this item claimed. **There is no iOS app to install.** No `.xcodeproj`,
> `.xcworkspace`, `Package.swift` or `Info.plist` exists anywhere in the repo; `mobile/` is
> JavaScript and Python (ONNX models, JS detector/live-call ports, export scripts), and
> `coreml-export.yml` produces **model artifacts**, not an installable app.
>
> **Corrected chain:** (1) export Core ML models — unblocked, runs in CI, no Mac needed;
> (2) **an iOS harness that loads those models and times them — DOES NOT EXIST and is the real
> blocker**; (3) install on the iPhone 17 — needs (2). A harness can be authored on Windows and
> **built** on the same GitHub-hosted `macos-14` runner, then sideloaded from Windows
> (AltStore/Sideloadly, free Apple ID = 7-day re-sign) or shipped via TestFlight with a paid
> developer account. So no Mac purchase is implied — but a build-and-install lane and the harness
> itself are unwritten work, not an afternoon of testing.
>
> **Recorded because the lead got this wrong:** it read this item's "dead-end on physical hardware
> and nowhere else" and relayed "the three decisions are now measurable" to the founder without
> checking whether an app existed. Third instance today of trusting a document's claim over the
> repo — see T24. Original text below; its *reasoning* stands, its *scope* did not.

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

## 0d. FOUNDER DIRECTION 2026-09-06: court setup should be PROACTIVE, SwingVision-style

**Founder, before sleeping:** *"court detection needs to be a little proactive, so can use
SwingVision as a sample wherein they ask the user to set up the court and then the green
outlines just snap to the lines for tennis."*

Recorded as a direction, not a question. **Two facts the morning needs before acting on it, so
a run is not spent rediscovering them:**

**1. The tool already exists and already does this.** `tools/court_setup_server.py` describes
itself as *"the SwingVision-style ADJUSTABLE OVERLAY calibration tool"* — it auto-detects and
snaps at startup (`--no-auto` opts out), draws an adjustable overlay, and has a temporal
clean-plate. It is what the founder re-clicked `yt_match40` in today. So the direction may be
**"make the existing snap better / more visible"** rather than "build this" — worth one
sentence from the founder to disambiguate, because those are very different runs.

**2. SNAPPING ONTO DETECTED LINES IS A MEASURED FAILURE HERE, and it made things WORSE, not
just no better.** From `docs/STATE.md` "What has not worked":

> median distance from truth: seed **9.8** → refiner **8.4** → **snap 70.5**

Snap took a near-correct court **8.4 px** from truth and pushed it to **70.5 px**. The refiner
helps; the snap actively destroys. STATE records the diagnosis: it needs **joint line-to-model
assignment**, and that was then built and measured on 2026-08-29 — it fails three ways, and on
2026-09-04 the whole branch died on a **fit ceiling**: the detected lines themselves disagree
with the true court by ~6.4 px rms, which is the same order as human click noise (~5.8 px).

**So "snap to the lines" cannot be made to work by trying harder at snapping** — the lines it
would snap to are not accurate enough to snap to. That is measured, not assumed, and rule 3
bars re-proposing it in that form.

**What is NOT barred, and is probably what the founder actually wants:** the *interaction* —
the overlay appearing already roughly placed, moving as a whole, guiding the user — rather than
the *algorithm* of snapping to detected lines. Today's live setup criterion
(`net_tape_clearance`) is exactly that kind of proactive guidance and it is real: it runs on
every preview frame, needs no image content, and tells the user **where to stand** before any
calibration exists.

**Cost to unblock: one sentence** — is the ask (a) make the existing overlay's auto-place and
drag feel better, (b) something new, or (c) the live guidance already built today?

---

## 1. ~~A push is required before the Core ML export can ever run — and pushes are barred~~ — **UNBLOCKED 2026-09-09**

**Status: the job is ready and CAN NOW BE TRIGGERED. Nobody has triggered it yet.**

> The founder lifted the push bar on 2026-09-09 ("ok to push") and three commits went to
> `origin/master` the same day. Both halves of this blocker are therefore gone: the Mac half was
> already dead (the export runs on a GitHub-hosted `macos-14` runner, not local hardware — this
> heading's "pushes are barred" had also been stale since 2026-09-04 per item −1, and the lead
> repeated it to the founder before checking), and the push bar is now lifted in fact.
> **The remaining action is one manual `workflow_dispatch` trigger.** The on-device fps half is
> separately unblocked by item −1.

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

## Composite calibration score — 2026-09-06 (backend-dev)

Evidence: `docs/evidence/composite-calibration-score.md`. Code `backend/swingvision/calib_score.py`.
The composite FAILS the pre-registered bar (held-out 57% detection vs 80%) but MEETS the
false-flag budget (1 of 9, and `eala_auto` scores 0.0). It is wired to nothing.

1. **EYE-CHECK, human required: `flexi_franz_p07`.** It is the single held-out false flag,
   fired by a fitted lens of 59.5 deg — 0.5 deg below the 60 deg floor — while its sibling
   `flexi_franz_p01` (same camera, same mount, re-clicked) fits 60.5 deg and passes. Measured
   re-click hfov scatter on one mount is up to 29.2 deg, so the "<= 1 false flag" half of the
   bar is met by luck, not margin. Only a human looking at the frame can say whether p07 is a
   marginal click or a rule error.
2. **UNEXPLAINED: `demo30`'s net tape reads +80%** against its own fitted camera height, while
   every other held-out clip reads within 8%. Not chased this run. It is half a vote so it
   changed no verdict, but an 80% off-plane disagreement on a believed-correct calibration is
   either a real clip problem or a tape-measurement failure mode nobody has named.
3. **PRODUCT CALL: should the score be surfaced at all, and where?** It is a reason string for
   the human confirming setup, not a gate, and it is currently called from nothing. Options:
   (a) print the reasons in `run.py check`'s Setup block, (b) stamp them into `_audit`,
   (c) leave it dormant. Anything that makes it refuse footage is a founder decision.
4. **THE REAL ASK: commission human mis-clicks as ground truth.** The composite scores 0.0 on
   the ONE confirmed-wrong calibration (`yt_match40_pts.json.bak-2026-09-05`) because a wrong
   court clicked on asphalt fits a 10.8 m / 20.9 deg camera, which is within 2 m and 4 deg of
   the real Wimbledon broadcast clip. The synthetic corruption class does not cover the
   failure mode that actually happened. A dozen deliberately mis-clicked, labelled
   calibrations would be worth more than another five corruption families.

## 2026-09-09 - backend-dev - CourtNet as the court GLOBAL proposer: flag built, bar FAILED
The CNN-global -> classical-local ordering flip is implemented behind
`auto_fit_frame(..., proposer="courtnet")`, default UNCHANGED. It FAILS the
pre-registered bar: gold 12/20 -> 2/20 accepted; references 2/20 -> 0/20; 3 of 160
frames locked vs 89; shell 0 of 80 frames. Mechanism: the UPSTREAM checkpoint emits
NO proposal on the failing clips (2-3 of 14 keypoints clear 0.40; 4 are needed for a
homography). Evidence: docs/evidence/cnn-global-classical-local.md.
FOUNDER DECISIONS NEEDED:
1. Keep the flag (recommended - it costs nothing and the follow-up needs it) or revert?
2. The live follow-up is whether a CourtNet TRAINED ON AMATEUR LOW-MOUNT FOOTAGE
   proposes at all on shell. `courtnet_ft.pt` cannot answer it: 17 of 20 gold clips
   were in its training pool, so measuring it on gold is self-grading. This needs a
   leak-clean train/test split and a retrain - both out of this run's scope. Approve?
3. SendMessage was asserted to work in two briefs and does NOT exist in the subagent
   toolset. Agent-to-agent findings are being relayed by hand.

---

## 2026-09-10 — The innovation-gate brief meets a measured ceiling. Recorded, not asked.

**The founder's brief:** *"Attack the innovation gate."* Correctly aimed — `smooth_forecast`
is the largest single speed-coverage cost (**-11.0 / -8.1 pts** under TrackNet) and it is a
STAGE property, since the gate deletes **14-17% of surviving real detections in every arm**.

**What the desk work found, before anything was run.** The gate's own reject population has
already been adjudicated against human clicks, in
`docs/evidence/smoother-gate-backward-readmit-separation.md` §3: **21 real / 28 ghost, 0.75 : 1
pooled** over three clips. That is a **ceiling on every re-admission route at once** — admit
every rejection the gate has ever made, by any mechanism, at any threshold, and the exchange
rate cannot exceed 0.75 : 1, against a family bar of >=3:1 and a structural rate of ~7:1.
The lead's own proposed line (that `meas_var = 25.0` was never calibrated, and a chi2 gate at
13.8 claiming a 0.1% false-reject rate while measuring 14-17% must have an understated R) was
put to `researcher` to confirm **or refute**, and was **refuted**: with `Q[0,0] = 0.05 px2`
against `R = 25 px2`, `S ~ (1.2-1.4) x R`, so scaling `meas_var` is arithmetically a
`gate_chi2` sweep in different units — a widen, drawing from that same 0.75:1 pool. The one
supporting fact the brief leaned on (Session I's ghosts at 208-829 px) describes chain
SURVIVORS; the gate's own reject-ghosts sit at **24.0, 30.3, 49.8 and 386.2 px**, three of four
inside the radius the widen would have opened.

**No founder decision is required and none is requested.** The brief is being executed, on the
two routes that are outside the barred family and that leave the accept radius untouched:

- **M1** — whether 1-2 frame interpolated bridges are actually unmeasured. `seen_frac` excludes
  every coasted frame on an *empirical* claim ("a forecast is not a measurement") that has never
  been tested, and `tools/eval_model_filters.py:201-208` already computes the number that tests
  it. Changes no filter behaviour at all.
- **M2** — rejection-run coherence. `rej` counts every rejection alike and the reset re-seeds at
  the current frame, discarding two. All 19 chain false locks have `run_len = 1`, so a coherence
  requirement excludes ghosts by their own measured signature rather than by a chosen threshold.

**Three things the founder may want to overrule later, recorded so they are not silently
assumed:**

1. **`meas_var` / `gate_chi2` have never been swept, and that question is now closed by
   argument rather than by measurement.** No sweep exists anywhere in STATE's 78 "has not
   worked" rows. The diagnostic below measures the noise model's bulk calibration anyway, as a
   free by-product, so the argument gets one chance to be wrong.
2. **The size of the prize behind -11.0 / -8.1 pts is still not established.** `seen_frac >= 0.5`
   is measured only weakly predictive of speed accuracy (+4.96 / +3.11 against a >=10-pt bar,
   0 of 10 seeds). Nothing in this repo shows a higher smoother-stage `seen_frac` yields a more
   accurate speed. Establishing that needs `tools/synth_truth.py` — the one rule-11-compliant
   speed reference — and is a separate run nobody has funded.
3. **The evidence points at `suppress_false_locks`, which this brief does not cover.** It costs
   -5.2 / -4.4 pts, and `pipeline.py:1441-1444` records that the gaps it opens are mostly gaps
   where it deleted a REAL far-court ball. A lock deleted there never reaches the gate at all.
   Out of scope here; named so it is not lost.

### Addendum, same day — the brief is EXECUTED and CLOSED, and one thing needs the founder's eye

**All three candidates are measured dead** against kill conditions pre-registered before anything
ran. `docs/evidence/innovation-gate-noise-calibration.md` §5 (backend-dev) and §6 (qa) carry the
numbers; the three negatives are rows in `docs/STATE.md`.

**The answer to "attack the innovation gate", in one line: the gate is not too tight — it is
already ~12x LOOSER than its own nominal design point, and what it rejects is genuinely
inconsistent with the motion model.** Median `d2` on gold-confirmed real accepted frames is
**0.113 against chi2_2's 1.386** (qa: 0.11272, sign test p = 1.9e-29). The -11.0 / -8.1 pt cost is
not a mis-set threshold; it is what a single constant-acceleration model costs when the ball
changes direction. Both of the lead's supporting arguments were wrong — the separation argument by
population swap (now TRAPS **T27**) and the "R dominates S" derivation by measurement (`R/S` is
0.187-0.304; **P** dominates).

**ONE ITEM NEEDS A HUMAN EYE — recorded, not fixed (rule 9), and not an interruption.**
`yt_match40` resolved to a **different court in two runs off the same `_pts.json`**: the published
ladder stamps `manual+snap`, reproj 9.112, hfov 26.43 deg, 186 shots; the 2026-09-10 run stamps
`manual+snap-clay`, reproj **0.011**, hfov **91.28 deg**, 86 shots. This is the clip T23 already
flagged as miscalibrated, so the snap has two wrong courts to choose between — and **reproj cannot
tell them apart; the 0.011 px fit is the better-looking of the two.** It joins the existing
"re-click `yt_match40`'s corners" item rather than adding a new demand on the founder's time.

**What is left of the -11.0 / -8.1 pts, and it is not nothing:** the reset path discards a
**ceiling worth ~40-60% of the whole stage cost** (+6.56 / +5.14 / +3.53 pts, qa-verified). It is a
ceiling nothing known can collect — that population is ~19 real / 18 ghost and M2 measured that run
length cannot separate them. **The next real target on this row is `suppress_false_locks`**
(-5.2 / -4.4 pts), whose own pipeline comment records it deleting real far-court balls. Not started;
it is a different stage and a different brief.

---

## 2026-09-10 — PRE-REGISTRATION: the HUMAN-GUIDED two-line calibration (NOT BUILT)

**Status: a protocol, not a result. No code, no number, and no product UI until the founder
approves it.** Written before anything is run, because rule 2 says the gate is pre-registered
and rule 3 says check "what has not worked" first — and checking it changed this proposal
substantially.

**Where the question came from.** The founder's note (2026-09-10): SwingVision is described as
doing *"3D spatial court mapping — automatically maps the full court layout, including hidden
or blocked lines, using visible markers and standard universal court dimensions."* And the
product brief's Feature 5: *can a user identify the near baseline and the actual GROUND-PLANE
net line, allowing geometry to predict the hidden far-court corners accurately enough for
metric output?*

**A competitor's marketing copy is a reason to ask, never evidence about the answer.** Nobody
outside that company has measured their far-court error, and rule 11's logic applies: another
product's claim about a court is not the court.

### This is NOT unexplored — most of it is already measured, and half of it already FAILED

`docs/STATE.md` → **"The camera SOLVES from the near baseline + net alone - the far line is
never needed"** (2026-09-06), evidence `evidence/net-baseline-solve-without-far-line.md`. That
row IS this idea, derived from the founder's earlier "how stretched it looks" proposal. What it
established, so none of it is re-run:

- **The geometry is exact and the system is DETERMINED.** Near baseline and net line sit at a
  known 11.885 m separation with the same known 10.97 m width: four observables (two rows, two
  widths) against four unknowns (standoff, focal, horizon, height). Synthetic solve-back is
  **0.0000 m**. Fed TRUTH observables on all 40 real clips it reproduces the human far-baseline
  row to **0.007 px median / 0.75 px max**, through real distortion, roll and off-centre
  principal points. **So "known dimensions can place what the camera cannot see" is not in
  doubt. It is proven.**
- **The AUTOMATIC version FAILED the very gate the brief names.** End-to-end from detected
  lines: far-baseline ROW error 3.99 px median (inside 8.1), but far **CORNER 17.4 px @640**
  against the **8.1 px** bar. The row would have passed; the corner is the shipped metric.
- **The cause is isolated and it is DETECTION, not geometry.** Near-baseline ROW detects to
  0.83 px, but near-baseline WIDTH to **12.44 px** and width at the net to **44.63 px** — a
  width is the separation of two intersections with *oblique* sidelines, where a sub-degree
  angle error levers into tens of pixels.
- **Availability binds harder than precision.** Right doubles sideline found on **18/40** clips,
  net ground line on **24/40**, and all four lines coexisting on only **10/40**.
- **The net TAPE is not the net ground line, and the error is sized.** Tape is found on 38/40
  clips against the ground line's 24/40, sitting **15–47 px above it**; substituting tape for
  ground puts the far baseline **32 px** out on every clip. This is exactly the brief's own
  constraint, and it is not a caution — it is a measurement.

**So rule 3 bars re-proposing the automatic form.** "Detect two lines instead of four" has been
run and missed the bar for a named, isolated reason.

### What IS open, and it is precisely the brief's wording

The evidence file's own closing line: *"it composes with a human placing two lines rather than
four — it does not remove the human."* Every failure above is a DETECTION failure, and the
control shows the geometry is exact when the observables are right. **So the open question is
whether a PERSON can supply those observables well enough**, on a low mount, where they are
being asked for the two best-resolved lines in the image instead of four corners two of which
they cannot see. That is a question about human placement precision, and this project has never
measured it.

### Pre-registered gate (verbatim from the brief; not to be moved afterwards)

- median far-corner error **<= 8.1 px at 640p**
- p90 **<= 20 px**
- **no plausible-looking but grossly wrong calibration**

**The third criterion is load-bearing and needs its own instrument.** A residual proves nothing
(T23: `yt_match40` stamped PASS at 0.9 px with all four corners on asphalt), so "grossly wrong"
is adjudicated by **rendering the predicted corners on the frame**, reviewed by a human who is
not the agent that produced them (T26). Pre-registered definition: a predicted far corner more
than **40 px at 640p** from the human-labelled one, or any prediction a reviewer marks off the
paint, is gross — and **one gross failure in the held-out set fails the gate outright**,
whatever the median says.

**Pre-registered secondary, because the first run must be able to say WHY it failed:** report
human placement error on the two input lines separately as ROW and WIDTH. If width error lands
near the detector's 12.44 px, the human-guided version fails for the same reason the automatic
one did, and that is a stopping result rather than a tuning opportunity.

### Method constraints — all of them existing project rules

- **The elevated net tape is never the ground-plane net line.** 0.914 m at the centre strap,
  1.07 m at the posts, measured at 32 px of far-baseline error if substituted. The user must be
  asked for **where the net meets the ground**, and the UI must make that distinction
  unmissable — a person asked for "the net line" will click the tape, which is the bright one.
- **Held-out court labels only** (`data/gold/court_split.json`, `assert_no_court_gold_leak`),
  and the pool must exclude the batch T26 indicts: `3399d58` / `ac94aab` supplied 9 of the 20
  scoring clips at a ~73% wrong-rate. **Establishing a clean held-out pool is a prerequisite,
  not a step inside this experiment.**
- **The human placements must be commissioned as ground truth, with provenance in the file** —
  who placed them, by what method, who verified. An agent placing them and then scoring them is
  T26 exactly.
- One variable, seeded. The control is the shipped four-corner calibration on the same clips.
- No new ML model. A learned far-corner regressor is a different proposal and stays barred until
  this one has a number.

**If it fails, it is retired, not retuned.** Five dead autonomous gates on this project share
one feature: a second attempt at a bar they had already missed.

### One thing from that row is worth taking NOW, and it is not calibration

**Camera HEIGHT from the two-line solve survives a 40% standoff error** (1.64->1.62, 2.11->1.95,
2.88->2.92 m). The evidence file's own conclusion is that *"if this solve has a use it is
mount-height estimation for the setup criterion, not calibration."* That is directly useful to
the framing guidance shipped today: it would give a live preview an honest mount height with no
calibration at all, which is the one quantity the clearance criterion actually tracks (Spearman
+0.937 against the width ratio's +0.189). **Cheap, separable, and it does not need this gate.**
Offered as its own small piece of work, not folded into the above.

**What the founder is asked for:** (a) approve or amend the protocol, (b) approve the clean
held-out pool and the commissioned human two-line placements as prerequisites, and (c) say
whether the mount-height by-product should be picked up separately. **Nothing is blocked
meanwhile** — the shipped Court Setup & Trust flow does not depend on any of it. A low-camera
user can record, review and correct today, and is told plainly what their numbers are worth.

---

## 2026-09-12 — P4: FOUR contradictions inside a LOCKED spec. No code; a written ruling.

**Asked for by the founder's own queue (P4, ~20 min). This is not an unprompted blocker.**
The queue named three. A fourth turned up while verifying the first, it is the one with real
build consequences, and it is listed last. `backend-dev` cannot start P7 (the Swift live path)
until (i), (ii) and (iv) resolve. All four were introduced or exposed by the 2026-09-11 rewrite.

### (i) §8 vs §4 — as written, §8 is unsatisfiable by §4's own method

§8: the call is emitted **"on the bounce frame itself"**, budget **16.7 ms**.
§4: a bounce **IS** a vertical-velocity **sign reversal**.

A sign reversal cannot be observed on the bounce frame. `vz` is a finite difference of two
positions, so seeing `vz` go negative -> positive needs **two post-bounce detections** to form
one post-bounce velocity, and **three** to reject a noise flip. At 60 fps with a *perfect*
detector that is **33.3 ms (k=2) to 50.0 ms (k=3)** before any compute.

**It is worse than frames, and this is the part to notice: the floor is in DETECTIONS, not
frames.** `live.py:69` returns early on a missed frame (`if ball_px is None: return None` —
"gap; bounce logic uses valid points only"), so dropout stretches the wait. At the 30% dropout
the synthetic rig uses as our detector's real rate, k=2 detections costs **~2.9 frames expected
(~48 ms)** and the tail is real: **P(>4 frames) = 8.4%, P(>6 frames) = 1.1%** (negative binomial,
p=0.7). So the worst-case call is several times the mean, which is exactly what a latency bar has
to be stated against.

**Second, separate defect: 16.7 ms/frame is a THROUGHPUT number and §8 uses it to state a
LATENCY requirement.** Throughput is the rate the per-frame path must sustain to avoid falling
behind. Latency is capture + compute + k/fps + emit. They are different quantities and a
pipeline can hit one while badly missing the other.

- **What the shipped code actually does, for reference:** `live.py:85-97` is **1 valid detection**
  of latency, not zero — it attributes the bounce to `_valid[-2]` and emits on the arrival of
  `_valid[-1]`, with the true bounce lying somewhere inside the candidate segment (so ±1 frame of
  attribution quantisation on top).
- **RECOMMENDED RULING:** §8 splits into two numbered bars. **Throughput: 16.7 ms/frame on the
  ANE** (unchanged, P6 costs it). **Latency: bounce + k detections + compute, with k=2 or 3 named
  in the spec**, giving a floor of ~33-50 ms at 60 fps, stated as detections-not-frames so
  dropout is visible. "INSTANT" stays the product word; it stops being a number.
- **WHAT NEEDS YOUR CALL:** the value of k (2 = faster and noisier, 3 = the robust choice), and
  whether a ~50 ms call still counts as INSTANT for the product. It is under one-twentieth of a
  second and well inside human reaction time, so I believe it does — but that is a product call.

### (ii) §1 vs the closed court path — the drift CHECK survives, the RECOVERY half has no mechanism

§1 mandates a **"full court re-solve every 10 s"** and holds calls until an **8-frame vote
(>=6/8)** passes. Court AUTO-detection is CLOSED for v1 and v1's court is a **manual four-tap**.
There is nothing to re-solve *with*: the vote and the re-solve are both properties of the search
that v1 does not run.

The optical-flow **drift check** (§1's first bullet, 4-8 tracked intersections, 15 px sustained
3 frames) is unaffected — it needs no search, only tracking.

- **RECOMMENDED RULING:** when tracked corners drift past tolerance, v1 **REFUSES and asks the
  user to re-tap.** Strike the forced 10 s re-solve and the 8-frame vote from §1 as v1 text; keep
  them struck-not-deleted for v2, the way §6 and §9 are kept.
- **This is a real UX consequence and it is why it is a ruling and not an implementation detail:**
  a bumped tripod mid-rally ends the automatic calling until the user intervenes. The alternative —
  calling on a drifted court — is the failure mode the 10 cm bar exists to prevent.
- **Carried from the old journal queue rather than re-derived:** the right companion is **calibrate
  LAST** (four-tap on a frame captured *after* the phone is placed and untouched) plus an **IMU
  stillness gate** (CoreMotion, on-device, zero inference). The measured reason it must be the IMU:
  **motionless tripods disagree with themselves about the court by more than a wrong-court
  distance**, so camera movement cannot be detected by watching the court fit wobble.

### (iii) §10's indoor-shell blocker is VOID for v1 — and the evidence is better than "probably"

**Two independent arguments, and SPEC already contains the first one.**

1. **By SPEC's own corrected attribution.** §10's final paragraph, corrected 2026-09-11, says the
   shell failure is a **SEARCH/proposal** problem: "on 12 of 20 clips the shipped search never once
   produces a correct court across 8 sampled frames (recall 8/20 = 40%)". **v1 never runs the
   search.** A blocker attributed to a mechanism v1 does not execute cannot block v1.
2. **Constructively — manual taps on shell courts already exist and were checked by an
   independent method.** `7c8b8af` (2026-08-26) committed **ten** shell calibrations across five
   venues, all `_exact`, fit residuals **0.0-2.5 px — the best band in the repo**, implied camera
   height reproducing **to 0.02 m** across two independent labels of the same venue.

**THE HONEST LIMITS, because the raw count flatters it and I got this wrong on first reading:**
- **`_audit: PASS` and "valid ground truth" are DIFFERENT AXES.** Four of the ten stamp PASS, but
  `mpc_tuesday_p01`/`p07` (2.79 / 2.81 m) are **explicitly excluded as ground truth by their own
  commit** — their two independent labels disagree by **25.4 px@640**, above the 20 px line that
  separates a right court from a wrong one. They pass the *camera* audit while being invalid as
  *truth*. So the usable count is **8 of 10**, and at a spec-relevant mount height it is **2** —
  `flexi_franz_p01`/`p07`, 2.50 / 2.51 m, which are two labels of **one venue**, not two venues.
- The other six valid ones sit at **1.36-1.64 m**, below the height where 10 cm is plausible at all.
- All ten are 3840x2160; **frame rate unknown** — P3 will say whether any meets the 60 fps floor.
- **T23 applies:** what carries these files is the *repeatability between two independent labels*,
  not the low residual. A residual certifies nothing.

- **RECOMMENDED RULING:** strike §10's "Ball-calling targets do not apply until that blocker
  clears". Replace the blocker with the accurate, narrower statement: **shell is unblocked for
  manual-tap v1; shell AUTO-detection stays closed and is v2.** Cost: zero. This dissolves the
  largest stated blocker in the project.
- **Do NOT let it be read as more than it is:** one shell venue at >=2.5 m is not a validated
  surface split. §7 asks for hard/clay/shell, and P5's court visit is what supplies that.

### (iv) NOT ON YOUR LIST, and it is the one that changes a build: live.py's bounce detector is NOT §4's method

P7 says "port `live.py`'s design". **`live.py` does not implement SPEC §4.** Its own docstring,
lines 14-16: *"a bounce is a local minimum of the ball's court-plane speed. Single-camera bounces
have no true height, so this is a court-speed heuristic."*

§4 says: **"Method: vertical-velocity sign reversal. NOT nearest-frame-to-court-plane."** A
court-plane speed minimum is not sign reversal, and it is *further* from §4 than the method §4
names as the thing to avoid — it has **no height channel at all**. It is a third method.

**This matters because the evidence for P7 being cheap is evidence about the wrong thing.**
`v2/mobile/live_calls.js` is a verified bit-parity port of `live.py` — confirmed: it carries the
same `seg` court-plane-speed structure (`live_calls.js:124-139`). So the parity result is real,
and it says **a port is cheap**. It says nothing about porting §4's method, which does not exist
in any language here yet. **A port proves faithfulness, never accuracy** — and here it would
faithfully reproduce a detector v1's own spec forbids.

- **RECOMMENDED RULING:** P7 ports live.py's **STRUCTURE** — streaming API, court from the manual
  tap, gap handling, call gating, refusal path — and **replaces the bounce stage** with §4's
  sign reversal on the 3D fit that P1 is building. `live.py`'s court-speed heuristic becomes the
  **control arm** for the new detector, not the thing shipped.
- **CONSEQUENCE FOR SEQUENCING, and it strengthens the existing order:** §4's method needs a
  **height channel**, which is exactly what P1 is measuring. If P1 fires its bar C kill, there is
  no §4-compliant bounce detector to port and P7 has nothing to build. **P7 stays last.**

**WHAT I DID INSTEAD OF WAITING:** P1 is in flight with backend-dev; the four items above were
verified from the code and the git record rather than asked about; and `ios/README.md`'s false
"nothing here has been built or run" sentence is corrected.

---

## 2026-09-12 — WITHDRAWALS. Four founder asks above are dead or reclassified. Nothing to decide.

**This section takes work OFF the founder's plate. It asks for nothing.** Each item above was
written before the 2026-09-11 scope lock and survives in this file as apparently shovel-ready.
Reading it as live would spend founder hours on a cut layer, so each is settled here explicitly
rather than left to decay.

### WITHDRAWN — the point-boundary labelling session (3-6 hours of founder time). DEAD.

**The single largest founder ask in this file, and it is now for nothing.** It exists to give the
**score layer** ground truth. **Match scoring, sets and games were CUT from v1** (CLAUDE.md's
scope table; `scoring.py` named as cut). A gold set for a layer that does not ship is not a
deferred task, it is a task with no consumer.

- `docs/evidence/point-boundary-label-protocol.md` **stays on disk**, complete and costed — the
  protocol was good work and re-deriving it if scoring returns in v2 would be waste. Deferred is
  not dead; **this ask is dead, the artefact is not.**
- **Do not pick this up as "ready and unblocked" because STATE says so.** That STATE row predates
  the scope lock and is corrected in the same pass as P3's row.
- **Where those 3-6 hours should go instead: P2, the occlusion census, ~45 minutes.** With SPEC §6
  tossed, every occluded bounce is a refusal, so the refusal rate is a property of the FOOTAGE and
  it decides whether v1 is a product at all. The queue is explicit that the eye-hour goes there.

### MOOT — item 0b, "Shell and Grass have no eligible footage for point-boundary ground truth"

It is a true observation about a layer that no longer ships, so there is nothing left to decide.
**Its underlying fact got worse and moved somewhere that matters**: P3's capture-floor census
(2026-09-12) finds **Shell 0 and Grass 0 clips** meeting v1's 60 fps + 1080p floor — all 58 4K
shell clips are 30 fps. So the recording gap 0b identified on the score layer is now a recording
gap on the **engine**, and it is answered by P5's court visit rather than by a labelling decision.

### RECLASSIFIED TO v2 — item 0c, "click along court LINES, not corners"

**Still sound, still unmeasured, and no longer on any v1 path.** It falsifies the claim that the
line detector's ~6.4 px disagreement with truth is near-irreducible — but that closure only binds
**court AUTO-detection**, which is closed for v1 (v1's court is a manual four-tap, so v1 never
runs the search). The measurement cannot move a v1 number.

Keep the pre-registered bands exactly as written (>10 px = the closure is wrong; ~5-7 px = it
stands) so it is not re-derived if auto-detection reopens in v2. **Not a founder minute today.**

### STILL LIVE, AND ALREADY THE v1 ANSWER — item 0d, PROACTIVE court setup

Founder direction 2026-09-06: *"ask the user to set up the court and then the green outlines just
snap to the lines."* **That is v1's court, exactly.** It is the one item in the court thread the
scope lock did not kill — because it was never the auto-detection search. `docs/court/CLOSED.md`
and the v2 parking apply to the SEARCH; a four-tap that snaps is the product answer.

It needs no ruling now — it becomes P4(ii)'s companion (the refuse-and-re-tap drift behaviour) and
frontend work once P1 and P6 report. Recorded here so the scope lock is not misread as having
killed it along with the rest of the pillar.

---

## 2026-09-15 — P5-scope: THE CAMERA IS BLIND IN ONE AXIS. What v1 claims, and what it outputs.

**pm. This is the FIFTH question on this file and the biggest.** It does not duplicate the
2026-09-12 **P4** entry above (four contradictions *inside* the locked spec — §8 vs §4, §1 vs the
closed court path, §10's shell blocker, and live.py's bounce method). **P4 asks whether the spec is
self-consistent. This asks whether its central bar is achievable at all, and what the product is if
it is not.** P4's four rulings are still needed and are unaffected by this one, with a single
interaction noted in §6 below.

**Everything here is downstream of two measurements, neither of which is mine:**
`docs/evidence/monocular-3d-ceiling.md` (**P1**, `backend-dev` built and ran it, the lead recomputed
every headline) and `docs/evidence/monocular-3d-routes.md` (**researcher**, plus the lead's **R1**
run at the end of that file). **I did not measure anything.** Below, every claim is tagged
**[MEASURED]** (someone else's number, with the file), **[PM-ARITHMETIC]** (mine, closed-form,
re-derivable in three lines — if the arithmetic is wrong the conclusion goes with it), or
**[PRODUCT JUDGEMENT]** (mine, and yours to overrule).

**Bar A is FAILED at 6.1% and stays failed (hard rule 2). Nothing in this entry re-opens it**, and
nothing here proposes pose, occlusion prediction, stereo, a second camera in the product path, court
auto-detection, or ball-detector work — P1 independently re-kills the detector and pose routes on
measurement. I have checked `docs/measure/CLOSED.md`, `docs/ball/CLOSED.md` and
`docs/platform/CLOSED.md`; **nothing in any of them touches optical framing or a per-line error
metric**, which are the two new things below.

---

### 0. The one-paragraph version

**[MEASURED]** The estimator is not inaccurate. It is accurate in two dimensions and blind in the
third: median error **5.4 cm** perpendicular to the camera ray and **1.28 m** along it, a factor of
**23.5**, confirmed across five mount heights and predicted to within 4% by closed-form geometry
before it was run. **[PRODUCT JUDGEMENT]** A spec that states one accuracy number for all calls is
therefore measuring something that does not exist. **My recommendation is to split §3 by the
direction of the line being called, to change the error metric from a scalar distance to the error
perpendicular to that line, and to stop v1 outputting a landing coordinate at all** — v1 emits a
line, a signed margin, an uncertainty on that margin, or a refusal. The bounce map is cut.

---

### 1. QUESTION 1 — what does v1 CLAIM? A per-LINE floor, not a per-direction one.

**[MEASURED]** R1 decomposes the error two ways. In court axes: lateral `|Δx|` **0.101 m** vs
down-court `|Δy|` **1.270 m**. About the camera ray: tangential **0.054 m** vs radial **1.280 m**.

**[PRODUCT JUDGEMENT] Neither of those is the bar's frame, and this is the correction I most want
you to read.** The camera-ray frame (radial/tangential) is the right frame for the *mechanism* — it
is where the physics lives. The product does not speak in camera rays; it speaks in **lines**. And
the only error that can change a call is the component **perpendicular to the line being called**.
An error of a metre *along* a sideline changes no call. An error of 3 cm *across* it changes a call
at a 2 cm margin. **So the honest metric is per-line perpendicular error, and nobody has ever
computed it.**

Those two frames coincide only on the court's centreline, and here is what the difference costs:

> **[PM-ARITHMETIC] The far corner leaks the blind axis into the sideline.** The camera sits on the
> centreline, 6 m behind the near baseline. A far *doubles* corner is 5.485 m across and 29.77 m
> down-ray, so the camera ray there sits **10.44°** off the court's long axis. That puts
> `sin(10.44°) = 0.181` of the blind-axis error **across the sideline**: `0.181 × 1.28 m ≈ **23 cm**`
> median, against the pooled court-frame lateral median of **10.1 cm**.

**The sideline is not uniformly safe. It is roughly 2x worse exactly at the far corner — which is
where contested calls actually happen.** This is arithmetic, not a measurement, and §7 below
pre-registers the free re-read that confirms or refutes it.

#### What I would put in §3 — the SHAPE. I am not proposing a number.

I am deliberately **not** offering a relaxed rate, because I would be picking it after seeing the
result, which is the thing rule 2 exists to prevent. What I am proposing is that §3 stops being one
bar and becomes four, and that **the surviving number does not move**:

- **§3.0 — the metric changes.** Accuracy is measured **perpendicular to the line being called**
  (equivalently: the error in the signed margin), not as `dist(true_landing, est_landing)`. **This
  is not a relaxation** — for a baseline call it selects the *harder* of the two components.
- **§3.1 — lines that RUN DOWN-COURT** (both singles sidelines, both doubles sidelines, the centre
  service line). **Bar unchanged: ≥90% within 10 cm, perpendicular.** **[MEASURED]** It is expected
  to fail today — the nearest proxy is a lateral-only rate of **49.9%**, and even at *zero* pixel
  noise **83.9%**. **Keep the bar and let it fail.** A failed bar with a known mechanism is worth
  more than a passed bar chosen to be passable.
- **§3.2 — lines that RUN ACROSS COURT** (both baselines, both service lines). **No accuracy bar is
  offered for v1.** **[MEASURED]** In the 18-24 m band the down-court ≤10 cm rate is **4.1%**. These
  calls depend on the axis a single camera does not observe. v1 refuses them, or does not offer
  them. Whether they ever return is decided by P5's real footage and by the capture spec, **not** by
  an estimator result.
- **§3.3 — abstention becomes directional.** §3 today refuses when a scalar 1σ exceeds 10 cm. There
  is no scalar to take a 1σ of. Refuse when **the 1σ of the perpendicular error exceeds the
  estimated margin** — the decision-relevant test.
- **§3.4 — the ≤5% refusal target is WITHDRAWN,** with no replacement number. See §4.

**The hazard in this, named because you should hold me to it:** *narrowing what a bar applies to is
a way of moving a bar.* Three reasons it is not that here, and if you do not accept all three you
should reject the split: (i) the direction split was derived from closed-form geometry
**independently of the result** and reproduced P1's measured failure boundary — 9.54 m predicted vs
9.85 m measured, **4%**; (ii) R1's ratio test was **pre-registered in a 5-20 band before it ran** and
came back 12.6; (iii) **the number 10 cm does not move, and the 90% does not move.** Only the
population each applies to changes, on a mechanism established before the split was proposed.

---

### 2. QUESTION 3 — what v1 outputs, end to end. **This is the biggest change and I lead with it.**

CLAUDE.md today: *"where the ball bounced, whether it was in or out, and a refusal when it cannot
tell."*

**[PRODUCT JUDGEMENT] My call: cut "where the ball bounced". v1 outputs a CALL, never a
COORDINATE.**

> **Proposed replacement line:** *What v1 outputs, end to end: for a bounce near a line, which line,
> which side of it, by what margin, with an uncertainty on that margin — or a refusal. It does not
> output a landing position, and it does not draw one.*

**Why, and it is a trust argument, not an accuracy one.** A landing coordinate is a claim in two
dimensions. We can honestly make a claim in one. If we render a dot on a court map, that dot will
sit **over a metre** from where the ball actually landed while the *call attached to it is correct*.
The user does not see two numbers with two error bars; they see a dot in the wrong place next to the
word IN, and they conclude the app is broken. **The dot destroys the trust that the call earns.**
That is the failure mode I am avoiding, and it is worse than being wrong — it is being visibly wrong
about the thing we did not measure, in a way that discredits the thing we did.

**And it kills the obvious compromise before someone proposes it.** "Show the margin, and also show
where along the line it landed" does not work: for a sideline call the margin is the *well-measured*
axis and the position *along* the line is the *blind* one. **[PM-ARITHMETIC]** There is no view that
places the bounce in space that is not mostly guess.

**What this buys, beyond honesty.** SPEC §3's abstention clause becomes implementable for the first
time — "1σ > 10 cm" has no referent once the error is anisotropic, but "1σ of the margin > the
margin" is a well-posed test with a covariance behind it (researcher's R2 is exactly that object,
and it is unmeasured).

**What this costs, and I will not soften it.** Refusing when uncertainty exceeds margin means
**the calls we refuse are precisely the near-line contested ones** — which is the population SPEC §7
validates against. So §7's *validation set* and §3's *abstention rule* select for opposite things.
**That is a fifth spec contradiction**, of a different kind from P4's four: it is invisible until you
accept the blind axis, and it needs the same written ruling. It does not change P4's four.

---

### 3. QUESTION 2 — the three shapes, ranked, plus two researcher did not name

**Ranked by what they cost against what they buy, and I have priced each in sessions.**

**RANK 1 — (a) Keep 10 cm; refuse by geometry and covariance; and DECLARE the coverage region up
front.** The variant matters more than the shape. Researcher's (a) refuses *per call*; I want the
callable region **drawn for the user at setup, before they record**, from the four-tap calibration
alone. **[PRODUCT JUDGEMENT]** Those are the same mechanism and two completely different promises:
a declared region is a promise we keep, a per-call refusal is a promise we break unpredictably and
silently. "Your camera cannot resolve that end of the court from here — move it back or up" is a
sentence a user can act on. A call that just never arrives is not.
- **Cost: ~5 sessions** (geometric map ~1; covariance measurement ~1 and wiring ~1; setup-time
  coverage overlay and the call card ~2). Most of it is work the setup flow needs regardless.
- **What it does not buy:** the far half of the court. Under a 1080p / 3 m mount that is everything
  past ~9.5 m from the near baseline. **[MEASURED]** That boundary is P1's own measured good-fit
  median of 9.85 m.

**RANK 2 — (c) The margin-based call.** I do **not** rank this as an alternative; **it is the
output change in §2 and it should be folded into (a), not chosen against it.** A depth-dependent
*accuracy bar* I would reject — it is a sliding number with no natural value and it will be tuned.
A *margin* test has a natural value (the margin itself) and cannot be tuned.
- **Cost: net NEGATIVE.** It removes the bounce-map view rather than adding anything. ~1 session for
  the call card.

**RANK 3 — (b) Move the capture spec — but only one of its three variants is worth pricing.**
- **(b1) Wide-angle, full court, higher and further back.** **[MEASURED, researcher]** A 6 m mount
  with 12.6 m of setback, or 4K with ~5.5 m. **[PRODUCT JUDGEMENT] Reject.** This project already
  owns the answer: **all four of our confirmed mounts are 1.36-1.74 m**, and the standing top ask —
  record *one* clip above 2.5 m — has been open for ten days. A spec that requires 6 m and 12.6 m of
  clear space behind the baseline is not a spec an amateur satisfies; it is a spec that means we
  ship to nobody. It also collides head-on with CLAUDE.md's founding premise, and **[MEASURED]** bar
  D passed that premise *only because every height failed equally*.
- **(b2) Telephoto, far half only — the one variant with a feasible band, and it is mine, so check
  it.** Researcher held the field of view at the full-court framing, where `f ≤ 175·S` binds. **That
  framing requirement is a scope decision, not a physical one.**
  > **[PM-ARITHMETIC]** If the camera frames only the **far** half-court, the binding width is
  > 10.97 m at 29.77 m, so `hfov ≤ 20.9°` and `f ≤ 5209 px` at 1920 wide. The requirement is
  > `f·h ≥ 8862`, i.e. `f ≥ 2954` at h = 3 m. **A feasible band exists** (hfov 21-36°) — unlike the
  > full-court configuration, which has **no solution at any setback**. At bar A's 2 px the
  > requirement doubles to 17,724, so `f ≥ 5908` exceeds the 5209 cap at 3 m and the mount must rise
  > to **h ≥ 3.4 m**.
  **So: marginal, not impossible.** That is a genuinely different status from (b1) and it is the
  only reason (b) is still on this page. **Three things it costs, all of which must be stated
  together:** (i) the near half of the court is out of frame entirely, so you call one end at a time;
  (ii) fewer observations of the arc, which **[PRODUCT JUDGEMENT]** may make P1's conditioning
  problem *worse* rather than better — this must be measured, not assumed; (iii) **a device
  consequence three steps out: the iPhone SE 2nd and 3rd generation have no telephoto camera at
  all.** An optical-tele capture spec narrows the supported device list below our stated A13 floor.
  The 4K-digital-crop alternative runs on any device but re-raises researcher's R7 caveat — whether
  detector noise scales with resolution is a **detector measurement, closed by rule 6** — so it is
  undecidable here, and saying so is the right answer rather than guessing.
  - **Cost to decide: ~0.5 session** (one seeded rig configuration — it is a camera config, not an
    estimator change), plus P5 capturing the framing (see §5, marginal cost ≈ 0 at the visit).
- **(b3) Side mount — pre-killed, because someone will propose it.** Turning the camera to the side
  makes the blind axis run *across* the court, which would make baselines callable and sidelines
  blind.
  > **[PM-ARITHMETIC]** Camera 6 m outside the sideline, level with the net: the worst point (the
  > opposite far corner) is 20.7 m away instead of 29.8 m — but framing 23.77 m of court length from
  > 6 m of setback needs `hfov ≈ 126°`, so `f ≈ 489 px` and `f·h = 1467` at 3 m. That gives **29 cm
  > per pixel** against the end-mount's **36 cm**.
  **~20% better, and it only swaps which lines are blind.** Not a rescue. Recorded so no session is
  spent rediscovering it.

**RANK 4 — (d), which researcher did not name: cut the line-call output and ship the engine as
something else.** I am not recommending it and I do not think we are there. It belongs on the list
because it is the honest floor if §4's kill condition fires, and because naming it now is cheaper
than discovering it at session 45.

---

### 4. QUESTION 4 — the refusal rate. Withdraw ≤5% NOW. Do not wait for P2, and do not replace it.

**[MEASURED] ≤5% is not merely provisional, it is arithmetically unreachable, and that conclusion
does not need P2.** Under a truthful abstention rule, refusals on across-court lines approach 100%
at the current capture spec (4.1% within 10 cm in the 18-24 m band), and on down-court lines run
near half (49.9%). No occlusion census is required to see that.

**P2 measures a different and ADDITIVE source.** Occlusion refusals and geometry refusals compound:
`total ≈ 1 − (1−r_occlusion)(1−r_geometry)`. **[PM-ARITHMETIC]** P2 can only raise the floor, never
lower it — so P2 is still worth its ~45 minutes, but it is **not a precondition for withdrawing
≤5%**, and holding the withdrawal for it would leave a number in a locked spec that we already know
is impossible.

**[PRODUCT JUDGEMENT] I will not name a replacement target, and I think naming one now would be
dishonest** — it would be picked after the result. What I will pre-register instead is a **kill
condition**, which *can* be fixed before the data:

> **PROPOSED PRE-REGISTRATION (needs your approval to become binding):** measured on P5's real
> footage, within the **declared coverage region**, if more than **one in three** near-line calls is
> refused, v1's line-call output is **cut** rather than tuned. Reasoning, and it is a judgement:
> a user who is refused a third of the time stops asking, and an app that is silent when it matters
> is worse than an app that does not claim the feature.

And the reporting shape, which I *would* fix now: **refusal rate is reported per line class and per
court region, never pooled.** A pooled 40% hides "5% near, 95% far", and that single pooled number
is how a product ships a promise it cannot keep.

---

### 5. QUESTION 5 — does R1 change what P5's court visit must capture? **Yes, in four ways.**

I will brief P5 itself separately. These are the **requirement deltas only**, and every one of them
costs near-zero extra at the visit but cannot be recovered afterwards.

1. **The marks must be placed at KNOWN OFFSETS FROM LINES, not just at known positions.** P5 as
   written asks for "≥30 landing points known to ≤3 cm". If the output becomes a margin (§2), the
   truth set must contain balls at known margins — tape-measured marks at, say, ±2, ±5, ±10, ±20 cm
   from each line type. Positions alone cannot validate a margin claim.
2. **Matched pairs across the two directions, at matched ranges.** Marks on **sidelines** (the
   well-measured axis) and on **baselines and service lines** (the blind axis) at the *same*
   down-court distances, so per-direction error can actually be separated. Without pairing, one
   pooled number comes back and we are exactly where we started.
3. **≥30 points is now too few.** It was sized for one pooled bar. Split by two line directions and
   at least two range bands and it is ~7 per cell. **[PRODUCT JUDGEMENT] The bar should rise to ≥30
   per direction class** — raising a bar is safe, and a visit that comes back unable to separate the
   two axes has not answered the question that made it top of the queue.
4. **Capture the same marks under two framings and at two mount heights.** The second framing is
   (b2)'s telephoto far-half view; the second height (e.g. ~2.5 m and ~3.5 m) tests the predicted
   `1/h` scaling **on real footage**, which is currently synthetic-only. **[PRODUCT JUDGEMENT] This
   is the highest-value addition on this list.** It converts one visit into the falsifier for the
   entire geometric diagnosis, and a court visit has days of lead time — a second visit to collect a
   variable we could have recorded on the first is the expensive mistake here.

**Also carry in, unchanged:** the mount height and setback must be **tape-measured and written
down**, not estimated — every conclusion in this entry is `D²/(f·h)` and `h` is the lever.

---

### 6. What this costs, and what does not get built

**Cut from v1, and this is the something-else that the yes above is a no to:**
- **The bounce map / landing dot / shot-placement heatmap.** Not deferred as a nice-to-have —
  **cut on measurement**, because we cannot place a bounce in two dimensions.
- **The far half of the court**, under shape (a), at the current capture spec.
- **Across-court line calls** (baselines, service lines) get no v1 accuracy claim.

**Sessions:** ~0.5 for the free re-read in §7; ~5 for shape (a) built; ~0.5 to decide (b2); and
shape (c) is a net saving. **The re-read is the only thing that should start before your ruling.**

**Interaction with P4, stated so the two rulings are not made in conflict:** P4(iv) rules that P7
replaces `live.py`'s bounce stage with §4's sign reversal *on the 3D fit P1 was building*. **[MEASURED]**
P1's bar B failed that timing badly (29.5% within ±1 frame against 90%, and biased **+3.66 frames
late**). §2's margin output does not need a landing coordinate, but it still needs a *bounce frame*,
so P4(iv) and this entry both depend on a bounce detector whose timing is currently failing its bar.
**P7 still stays last.** Nothing here changes P4's four recommended rulings.

**ON-DEVICE CATCH:** nothing in this entry adds a network dependency, and I checked each item
specifically. The coverage map is closed-form geometry evaluated **once at calibration** — zero
per-frame cost. The margin covariance is a small matrix inverse per arc, CPU-side, microseconds.
**The two real on-device risks are both pre-existing and both unmeasured:** (i) **[MEASURED,
researcher]** `fit_arc`'s per-arc latency on an A13 has never been measured against the 16.7 ms
throughput budget, and no number in this repo covers it; (ii) shape (b2)'s 4K-crop variant raises a
sustained-capture thermal question that **no number in this project has ever come from a phone** to
answer. Neither is created by this ruling; both are made more load-bearing by it.

---

### 7. The one thing that should run before you rule — pre-registered here, BEFORE it runs

**A per-line perpendicular decomposition of the error already on disk.** Same class as R1: a re-read
of `data/output/mono3d_ceiling/*.json`, **zero new compute, no refitting**. Project each flight's
error onto the **normal of the nearest line**, and report the ≤10 cm rate and p90 per line type and
per range band.

**PRE-REGISTERED PREDICTION, written before the run, testing §1's obliquity arithmetic:**
- **PASS (my arithmetic holds):** in the far-corner band (bounce >18 m down-court, lateral offset
  >4 m from the centreline), the median **sideline-perpendicular** error is **≥ 2x** the pooled
  court-frame lateral median of 0.101 m.
- **REFUTED:** it comes back near **1x**. Then the sideline is uniformly safe, my far-corner leak is
  wrong, and shape (a) gets **better**, not worse — a good outcome I would be happy to be handed.
- **Either way the §3 SHAPE recommendation stands**, because it rests on R1's measured 23.5x
  anisotropy, not on my obliquity term.

> **RUN 2026-09-15 (lead). RESULT: PASS at 3.58x** against the >=2.0x bar — the far-corner leak is
> real and larger than predicted. The gradient is monotonic in off-axis angle (median `|Δx|`
> **0.049 m on the centreline -> 0.348 m at the doubles sideline**, <=10 cm rate **72.9% -> 20.0%**)
> and a two-term quadrature model accounts for it to 5-13% with nothing fitted. **Consequence: the
> sideline-first shape buys LESS coverage than the pooled 49.9% suggests, and a per-line bar must
> also be per-REGION.** Full result: `docs/evidence/monocular-3d-routes.md`, section "R1b".

**Caveat carried into every line above, and it is the reason to rule on shape now and numbers
later: nothing here has touched real footage.** P1 and R1 are synthetic; the noise is i.i.d.
Gaussian where a real detector's error is correlated and heavy-tailed; and **[MEASURED]** the flight
population is *uniform* rather than a tennis distribution, which over-represents exactly the
fast/lofted/far flights that fail — **so 6.1% may be pessimistic by an unknown amount.**
**[PRODUCT JUDGEMENT]** The split that matters: **the anisotropy is geometric and will survive real
noise; the rates (49.9%, 83.9%, 6.1%) are properties of the noise model and the flight population
and will move.** Rule on the shape today. Let P5 set the numbers.

---

### WHAT YOU ARE ASKED FOR — five sentences, and the definition of done, written before the work

1. **Split §3 by line direction, with the metric changed to perpendicular error** — yes or no?
   (§1. The 10 cm and the 90% do not move.)
2. **Does v1 output a margin-and-call, with no landing coordinate and no bounce map** — yes or no?
   (§2. This is the one with the largest build consequence.)
3. **Is a DECLARED half-court coverage region an acceptable v1** — yes or no? (§3, rank 1.)
4. **Confirm ≤5% refusal is withdrawn with no replacement, and approve or amend the one-in-three
   kill condition.** (§4.)
5. **Approve P5 capturing two framings, two mount heights, and line-referenced marks** — yes or no?
   (§5. This one has lead time and cannot be added later.)

**Definition of done for this item:** the five answers above are written into this file; CLAUDE.md's
"what v1 outputs, end to end" line is updated by the lead to match answer 2; and P5's brief is
rewritten against answers 1, 2 and 5 **before the visit is scheduled**. **No SPEC edit is made by
anyone but you** — SPEC is LOCKED and I have written options, not an amendment.

**WHAT WAS DONE INSTEAD OF WAITING:** P1 and R1 both ran and landed; researcher's seven routes are
written and ranked with pre-registered bars; and the §7 re-read above needs no ruling and no
compute, so it can start today whatever you decide.

---

## 2026-09-16 — Two court-truth items from P8 C2. One labelling ask, one edit to rule on.

**1. An unrecorded edit to court gold (rule 10).** Agent commit `2e49f38` (2026-09-06), whose message
is about the composite calibration score, also re-saved `data/gold/am_beginner.court.labels.json` —
all four corners of frame 3904 moved, by up to 27 px — and added 15 labelled frames to
`data/gold/am_usta45final.court.labels.json` (+1,312 / -97 lines). **Nothing records who made the
edits or why.** It may be your own labelling session swept into an agent's commit, or an agent
editing gold. It touches the 12/20 court gate. **Nothing has been reverted.** Needed from you: were
those your edits? If yes, they stand and get recorded as such; if not, the gate is re-scored on the
pre-edit files.

**2. C2 needs clicks that don't exist yet.** The court gold's non-corner landmarks are computed by the
labelling tool from your four corner clicks, so they cannot test the four-tap court model — that
would grade it against its own output. A real C2 needs **you to click the T's and service-line
junctions directly, with no court overlay shown, on ~20 gold frames** (a new tool mode and a
pre-registered bar first; not yet built). **Lower priority than the court visit**: C1 already showed
human clicks are ~200x too coarse to settle the question, and only the visit's tape marks can measure
the court model in metres. It would still catch lens distortion or non-regulation courts on real
footage.

---

## 2026-09-16 — FOUNDER RULING: the app makes a call even when the ball is blocked.

Founder: "the idea is for the app to still make a call even though it is blocked" — and not to pivot
away from that instruction. **This settles the direction of the P5-scope entry above: its narrowing
options (per-line bars that drop across-court lines, a call without a coordinate) are NOT adopted.**
They stay on file as analysis only. SPEC §6 (calling through occlusion) returns to scope; its formal
restoration waits on researcher's SwingVision report, because §6's contact detector relies on pose,
which §9 still excludes — that one question will come back to the founder with the research.

---

## 2026-09-17 — Two court items from researcher's court-precision routes

**1. SPEC §1's drift trigger is far too loose for the court v1 needs.** Researcher: "SPEC §1's
15 px drift trigger is ~5 m at the far baseline at 1080p/3 m; a sub-5 cm court needs a per-line
re-fit tolerance of ~0.1 px on far lines" (lead-checked: 15 px x ~0.37 m/px ~ 5.5 m). Researcher
also found the phone's motion sensor cannot see drift that small (~0.01° of tilt) and recommends
BOTH an IMU bump trigger and a periodic image re-fit of the court. This bears on your pending P4(ii)
ruling (refuse-and-re-tap vs recover) and would change §1's number. Needed: a ruling, after CP1
reports on whether the re-fit reaches that precision.

**2. The court visit should add long tape strips at the far end.** A 10 cm fiducial square 30 m
away is only ~0.27 px tall on screen, too small to check the far baseline. Researcher proposes long
strips laid down-court near the far baseline, plus measuring the court's real dimensions, paint
widths and surface height at the far baseline on the day. This is an amendment to
`docs/CAPTURE_PROTOCOL.md` (pm owns it). Needed: your OK before pm changes the protocol.

---

## 2026-09-17 — FOUNDER ANSWERS to the court items. Recorded, applied where they decide something.

1. **The 2026-09-06 gold edits (commit `2e49f38`) were the founder's.** They stand, unchanged. The
   STATE row that flagged them is updated. No re-score.
2. **Far-end tape strips for the court visit: "can do but not in person".** Read as: approved in
   principle, but the founder cannot do an in-person court session. The protocol amendment waits
   until a visit is possible (pm owns it).
3. **Court visit: "can not do yet".** So **no metric real-court truth is available for now.** Court
   work proceeds on synthetic truth (C1, CP1) and must look for real-footage checks that need no one
   at a court.
4. **Phone movement: "must continue, its essentially live court tracking".** P4(ii) is RULED:
   **track and re-fit, never refuse.** Applied to SPEC §1 (ruling block added, original bullets
   kept) and to CLAUDE.md. This overturns the lead's refuse-and-re-tap recommendation.
5. **Indoor shell: "yes".** P4(iii) is RULED: the §10 blocker is void for v1. Applied to SPEC §10 and
   CLAUDE.md.

---

## 2026-09-17 — FOUNDER RULING: automatic court detection (ML), not taps.

Verbatim: "dont use finger level accuracy - I keep saying that it must be the machine learning the 3d space and determining the far and close lines and assuming where the end points are if they are not visible similar to swing vision".

Applied to CLAUDE.md, SPEC §1, STATE and `docs/court/CLOSED.md` (annotated, not deleted). This settles the 2026-09-09 open item "a CourtNet trained on AMATEUR low-mount footage, on a leak-clean split — founder call": the founder has made that call in favour of an automatic, learned court. Carried forward from C1, and it applies to ML exactly as to taps: any method that pins the court from four corner points needs ~0.1 px corners for the far lines, so the automatic system must fit the WHOLE painted lines (what CP1 tests).

