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

## 0. The shipped int8 ball graph fails its parity bar on half the gold clips — ship it, or not?

**Status: measured out. Not blocked on anything technical — this is a product call.**

Six gold clips, 178 contiguous frames each, the shipped `tracknet_ball.int8.onnx` against
the fp32 reference, both through the real mobile decode. **3 of 6 clips fail** the
pre-registered no-frame-over-10px condition: 70.8 px, 75.4 px (three consecutive frames)
and **185.1 px**. Pooled **5 bad frames in 528** where both graphs fire — call it 1 in 100.
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
