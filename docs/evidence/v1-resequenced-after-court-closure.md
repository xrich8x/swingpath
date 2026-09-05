# v1, re-sequenced after the court closure

> **DELIVERABLE:** a re-sequencing of v1 against three closures of 2026-09-03..05 — court
> auto-detection closed, the `seen_frac` speed gate unrescuable, the int8 ball graph's ship
> choice reduced to int8-vs-fp32 on an unmeasured A13. Written by pm, 2026-09-05. **Nothing
> here re-derives a measurement**; every number is cited from the row that owns it.
>
> Sections: (1) what v1 is · (2) the cut line · (3) the founder-time queue, ranked ·
> (4) the dispatchable queue, in order · (5) the hardware dead-ends · then the single next
> dispatch.

---

## 0. The one-paragraph version

Court auto-detection closing does not shrink v1 — it **finishes** v1's setup story and frees
the largest single engineering item on the board (a ~2,900-line classical-CV port with no
conversion toolchain). What is left unfinished in v1 is not perception, it is **the phone**:
no part of this pipeline has ever run on an iPhone, and three separate decisions dead-end on
that. Meanwhile the item my own memory records as the hardest blocker — "Core ML export needs
a Mac" — **is stale**: the export runs on a GitHub-hosted `macos-14` runner, the workflow is
already on `origin/master`, its one defect is fixed, and the push bar that blocked it was
lifted 2026-09-04. Nobody has pressed the button. That is the next dispatch.

The cut this run makes: **match scoring leaves v1** (rally clips stay), line calling stays
parked, and the court research lane is closed rather than re-aimed.

---

## 1. What v1 is, given court auto-detection is out

### 1.1 The setup story, end to end, as the user experiences it

1. **Mount.** Phone on a fence clamp or tripod behind the baseline. The app shows a live
   framing guide and a **mount grade** — the port of `run.py check`'s height guidance, which
   already reaches the user on desktop (STATE, *What has worked*).
2. **Calibrate.** The user taps the four court corners on a frozen frame with a magnifier
   loupe. That is the calibration. No auto-detect button, no "detecting court…" spinner, no
   failure state to recover from.
3. **Record or import.** Capture in-app, or pick an existing video.
4. **Analyse.** A long-running on-device job. Not real-time, not interactive — a resumable
   batch pass the user starts and walks away from.
5. **Review.** Shot list with types and speeds, bounce map, per-rally clips, a highlights
   reel.

**Is that coherent? Yes — and it is better than the version with auto-detection in it.**
Three reasons, none of them consolation:

- Manual calibration is not the fallback that survived; it is **the reference standard the
  auto-detector spent six measured branches failing to reproduce**. Every court number this
  project reports — the 8.1 px shipped fit, the 54/69/81% close-call curve by mount height —
  is downstream of a human-clicked court.
- The platform change works *for* it. Tap-and-drag with a loupe on a touchscreen is a better
  corner-picking interface than a desktop mouse. This is the one subsystem where going mobile
  improves the manual path.
- It deletes an entire class of user-facing failure. An auto-detector that is wrong 8 times
  in 20 (and 5 in 5 indoors) does not save the user four taps; it costs them four taps *plus*
  a wrong-court recovery they have no way to diagnose.

**The product tradeoff researcher left open in §4 of the closure — "should we ship
auto-detection as a convenience even at lower accuracy?" — I am answering NO, for v1 and for
v1.x.** A silently wrong court is the exact failure class this project's accuracy floors
exist to prevent: it does not degrade a number, it inverts one. `yt_match40` is the standing
proof — a calibration that passes a 0.9 px residual audit while all four corners sit on
asphalt and a hedge, which made the pipeline call the near player far and cost two published
figures. Four taps is not the friction worth risking that for.

### 1.2 Where the setup story is still broken

Four things, named plainly, in order of how much they hurt:

1. **The user can hold the phone at a height that makes the app lie, and nothing stops
   them.** At the two measured real mounts (1.38 m, 1.74 m) close calls run **54.0% at 1.0 m
   against a 56.2% majority-class floor** — worse than answering "in" every time — reaching
   ~69% at 3 m and ~81% at 8 m. The height guidance *exists* and *reaches the user*, but it
   is advice. v1 needs it to be a **refusal**: below a stated mount height, the app declines
   to produce the numbers that height cannot support, rather than producing worse ones. That
   is a build item, and it is on the frontend lane below.
2. **Speed ships behind a gate nobody can validate.** `seen_frac >= 0.5` gates every speed
   shown (`pipeline.py:1873`) and is **NONE ADMISSIBLE for any coverage floor above 27%**;
   the replacement needs a real-footage absolute speed reference that does not exist and that
   rule 11 bars the HUD from supplying. **Call: ship the gate unchanged and stop denominating
   anything in it** (§2).
3. **The ball graph can lock confidently onto the wrong thing about once per 100 frames**,
   in runs long enough to survive the smoother. Ship choice is int8-vs-fp32 and both turn on
   an A13 fps nobody has measured (§5).
4. **Nothing has ever run on a phone.** No fps, no thermal behaviour, no battery figure, no
   evidence that a 60–90 minute match is analysable at all on an A13. On desktop CPU the
   arithmetic is ball 0.7 s + pose 0.4 s ≈ 1.1 s/frame — a 10-minute clip is ~5.5 hours. The
   honest bar was never "fps", it is **sustained throughput at thermal steady state,
   resumable, overnight** — and it is unmeasured.

Items 1–3 are things we can decide today. Item 4 is a purchase (§5).

---

## 2. The cut line

### 2.1 In v1

| In | Why it survives |
|---|---|
| Manual 4-tap calibration + loupe | It **is** the setup story now. |
| Framing guidance **as a refusal**, not advice | The mount-height curve is a measured accuracy ceiling; advice does not enforce a ceiling. |
| Capture + import | No product without it. |
| TrackNet ball, pose, homography, smoother, shot detection | The shipped perception chain; founder ruled TrackNet for v1 (2026-08-29). |
| Ball speed, labelled **average ball speed** | Ships today, ~15–20% under radar by drag (−21.7%). Never "fixed" to match TV. |
| Bounce location map | Ships today. |
| Per-rally clips + highlights reel | Ships today (`run.py highlights`, ffmpeg stream copy). See §2.3 — this is the half of rule 12 that stays. |
| Resumable overnight batch job | The unit-of-analysis question is a product decision and this is the answer. |
| Results UI | No product without it. |

### 2.2 Out of v1 — each with what it costs to cut and what it buys back

| Cut | Why | Buys back |
|---|---|---|
| **Court auto-detection, and the `courtfit.py`/`calibration.py` mobile port** | Closed on accuracy, not cost: the line detector's ~6.4 px disagreement with truth is the same order as the ~5.8 px human click neighbourhood, so a *successful* port would not have shipped something better than manual entry. Six measured branches. | **The largest single item on the board.** ~2,900 lines with no conversion toolchain, which was going to become a shared C++/OpenCV core — a genuine engineering project, not a port. Memory priced parity **~40–50 sessions without court auto vs ~55–70 with**: this cut is worth roughly **15–20 sessions**. |
| **Line calls / in-out** | Already parked by founder decision 2026-08-29. The geometry ceiling at both real mounts is at or below the majority-class floor within 0.10 m of a line. `live.py`'s shipped `line_margin_m = 0.05` sits inside the unreliable zone. | The live-call lane (largely ported and now parity-verified) stays as *infrastructure*, not a v1 feature. No further spend. |
| **Match SCORING — sets, games, point-by-point score** | See §2.3. | ~8–12 sessions of consumer UI (score view, mobile correction UI) that cannot be specified until an accuracy floor exists. |
| **BallNet v21 Core ML conversion** | Upgrade path, explicitly. v1 ships TrackNet. | ~3–5 sessions. |
| **Audio impact detection** | Screened, not measured: `detect_impacts` self-declares useless on 0 of 88 clips, and no compliant per-stroke reference exists. The iOS port additionally needs a streaming order statistic (Accelerate has no rolling median). Infrastructure for a feature with no measured value. | ~4–6 sessions. |
| **Far-court recall labelling** (4,087 frames, 4–5 h of founder clicking) | Its consumer is line calling, which is parked. | 4–5 h of the scarcest resource in the project. |
| **The `seen_frac` replacement measurement** (DECISIONS_PENDING option 2) | It cannot be closed. The §7 pre-registration needs a real-footage absolute speed reference; rule 11 bars the HUD; `synth_truth` is not real footage. Running it produces another INDETERMINATE. | ~2–3 sessions. **Take option 1 (leave it), plus one consequence, below.** |
| **The court mask sweep's qa gate run** (DECISIONS_PENDING item 4) | Now orphaned: it tunes the classical detector v1 no longer ships. Nothing consumes the result. | A qa run. |
| **Top-2 margin refusal as a shipped detector** | It is a *screen* at 14–31% precision on an effective n≈3. Not a threshold to adopt. | Not a cut of the *measurement* — see §4, item 2, which is the one thing that could still make it pay. |

**The consequence of leaving the speed gate alone, stated because it is three steps out:**
"speed coverage" stops being a v1 target. The best-measured open item in the project — *37
shots lose their speed to the chain; `smooth_forecast` costs −11.0/−8.1 pts under TrackNet* —
is a count of shots under a bar that has been shown not to predict speed error. **Fixing that
chain cost would move a statistic we cannot interpret.** So the speed-coverage lane is
**parked, not cut**: it unparks the day a compliant real-footage speed reference exists, and
not before. Anyone proposing chain work "to recover speed coverage" should be shown this
paragraph.

### 2.3 The score/rally layer — split it, do not carry it whole

**Call: rally SEGMENTATION stays in v1. Match SCORING leaves v1.**

They have been carried as one item since rule 12 put them back in scope on 2026-08-27, and
they have opposite risk profiles:

- **Rally segmentation degrades gracefully.** A boundary half a second late produces a clip
  that starts half a second late. The user sees it, shrugs, and the product still works. It
  already ships, it already has its consumer built (the clip list and highlights reel), and
  it is the *only* thing in this family with a v1 consumer.
- **A match score does not degrade gracefully.** It is one confident fact per match, and the
  user already knows the true answer. A wrong score is the trust-destroying class this
  project's accuracy floors exist for — and today the layer "has no ground truth of any kind"
  and reports which rule split it (`yt_rally2`: 5 timeout / 0 tennis-rule). Its consumers —
  a score view, a mobile correction UI — are **not built**. So even with labels in hand,
  scoring is 8–12 sessions from a screen, and we would be building the UI before we knew
  whether the number is good enough to display.

**The labelling session is still worth doing, and its justification changes.** It is not
"score-layer ground truth" any more; it is **the only way to put a number on a v1 feature** —
are the timeout-rule clip boundaries any good? That reframing is what keeps 3–6 h of founder
time on the list after scoring is deferred.

**Accuracy floors, pre-registered now, before the labels exist (rule 2):**

- **Rally clip boundaries (v1):** ≥90% of detected point boundaries within **2.0 s** of the
  human label, on the labelled set. Rationale for 2.0 s: the protocol's own self-agreement
  bar is a 1.0 s median disagreement, so a tolerance at the algorithm level must sit above
  the label's own noise. Below 90%, the clip list still ships — a clip is a clip — but
  **dead-time trimming does not**, because a trim that cuts a rally's first shot is a
  destroyed clip, not a shorter one.
- **Match score (v1.x, gating whether it is ever displayed):** ≥95% of games correctly
  scored on the labelled set, **and** a refusal path — the app says "score unavailable for
  this stretch" rather than guessing. Below 95%, ship no score at all.

These are written before the experiment and do not move.

### 2.4 What should take the capacity court work is vacating

Court has absorbed the largest share of this project's measured effort: six auto-detection
branches, a joint-correspondence solver, a least-squares fitter, a mask sweep, a verify gate
audit. It is closed. That capacity goes, in this order, to:

1. **The phone.** Export, run, measure, make the batch job survive an overnight run. This is
   the only lane where an unknown can still kill v1.
2. **The setup screen.** Manual calibration went from fallback to product; it deserves the
   polish budget the auto-detector was consuming.
3. **The refusal surface.** My own memory records that the live path has *no* refusal surface
   — no confidence band, no false-lock suppression, no serve boxes. Every honest thing in
   §1.2 (mount too low, speed not confident, ball lock refused) is a refusal, and none of
   them has a UI. This is now the largest un-owned area in v1.

**It does not go to a seventh court branch, and it does not go to a learned segmentation
net.** Rule 3.

---

## 3. The founder-time queue, ranked by what it unblocks per founder-minute

Ranked by **leverage per founder-minute on the v1 critical path** — not by cheapness, and not
by how interesting the question is. Two items that are cheap rank low here precisely because
their best-case outcome changes no v1 decision.

| # | Ask | Time | What it unblocks | Leverage |
|---|---|---|---|---|
| **0** | **Buy one used A13-or-newer iPhone.** Not on any existing list; the largest omission on the board. | ~15 min + money | Every item in §5. Three v1 decisions dead-end here and nowhere else. | **Highest in the project.** An iPhone 11 or SE 2nd gen secondhand is the cheapest unblock available and it retires an entire dead-end class. |
| **1** | **Re-click `yt_match40`'s four corners.** Sheet is already rendered at `data/output/corner_audit/yt_match40_corners.png`. | ~5 min | P0-2 (pose downscale — the top v1 *runtime* risk), the two withdrawn figures (`11.0% @1280`, `8.8 m mount`), the whole `yt_match40` shot list, and the far-end player/ball work whose gate needs a valid homography and is currently *not dispatchable* without it. | Best minutes-to-unblock ratio of any non-purchase item. |
| **2** | **Review `data/output/corner_audit/` — 27 rendered sheets.** Two the lead cannot settle: on `am_hard_utr` and `sAjkpeRq4P4` the far corners land near the NET rather than the far baseline, and a still frame cannot separate those at a low mount. | ~10 min | Confidence in *every* court-derived number. `yt_match40` proves a residual audit passes a grossly wrong court (T23); a second undetected one silently corrupts more numbers. | High. This is insurance against re-running T23 with nobody noticing. |
| **3** | **Re-label the 8 mislabelled court gold frames** in the Lab. Rule 9 — recorded, deliberately never quietly fixed. | ~1 min | Correctness of the denominator in the ≥12-of-20 court precision gate. | Highest per-minute in absolute terms; low absolute value. **Bundle with #2** — same sitting, same tool. |
| **4** | **~3–6 h point-boundary labelling**, per the now-written and costed protocol (~5.6 h worst case, hard-stop 4.5 h, the cut already made in the document). | 3–6 h | **Re-justified by §2.3:** not score-layer truth any more — the only way to put a number on **rally clip boundaries, a v1 feature that is currently unmeasured**. Score is deferred, so the v1.x score floor is a secondary benefit, not the case. | Medium. Big time cost for one v1 number plus a deferred feature — but it is the only compliant truth source that exists, and 4 of the 9 eligible files are already ball gold under the same basename, so the leak guard must be in place before a single label is written. |
| **5** | **Click points *along* the four outer court lines** on a handful of gold frames — the §1 falsifier for the court closure. | ~30–60 min | **Nothing on the v1 path.** Its three outcomes are: detector is fine (court stays closed), detector matches the measured gap (court stays closed), detector is >10 px off (reopens a research branch we are not funding for v1 anyway). | **Lowest, and deliberately so.** It is cheap, it is genuinely the single measurement that would falsify the closure's premise, and **its best case changes no v1 decision** — because the cut in §2.2 rests on manual calibration already being the reference standard, not on the detector being unfixable. Do it after v1 ships, or never. Ranking a cheap item last is the point of ranking by leverage rather than cost. |

**Sequencing note for the lead:** #1, #2 and #3 are one ~16-minute sitting and should be
asked as one batched update with the artefacts already built, per the standing rule that a
founder ask is a scarce batched resource. #0 is a purchase with a lead time, so it goes in the
same update and its clock starts running while machine work continues.

---

## 4. Dispatchable right now, without the founder, in order

The lead runs one agent at a time. This is the queue, head first.

1. **backend-dev — trigger the Core ML export (P0-0) and land the artefacts.**
   `.github/workflows/coreml-export.yml` is verified present: `workflow_dispatch`, pinned
   `macos-14` (Apple Silicon), installs `coremltools` on real macOS where the compiled
   `libmilstoragepython`/`libcoremlpython` exist, runs `tools/export_coreml_p0.py`, uploads
   `ios/coreml_export/` with **14-day retention**. The push bar that blocked it was **lifted
   2026-09-04**, and the defect that would have failed the job (a hard-coded
   `backend/yolo11m-pose.pt` that `.gitignore` excludes from a fresh CI checkout) is fixed.
   **Brief must include: push `master` first** — `workflow_dispatch` only appears for the
   version of the workflow on the default branch, and the export-script fix must be on
   `origin/master` or the job exports the ball model and dies at the pose step, which is the
   whole reason the job exists. **Retrieve the artefact within 14 days or it evaporates.**
   *Why head of queue:* it is minutes of work, it is on the critical path, it converts "no
   part of this pipeline has ever been Core ML" into a solved problem, and **it retires the
   "we need a Mac" blocker my own memory still records as procurement.**

2. **backend-dev — measure the downstream cost of a refused frame, on both graphs.**
   DECISIONS_PENDING names this as explicitly unmeasured: refusing ~5% of both-fire frames
   (fp32 `margin <= 0.10`: 5/5 caught, 2.1% collateral; int8 `blob_count >= 2` / `margin <=
   0.90`: 4/5 caught, 3.8–4.8% collateral) has an unknown cost to the rendered chain.
   *Why #2:* this is **the only lever that can dissolve an A13 dependency without an A13.**
   If the smoother absorbs a refused frame at no cost, then int8's 1-in-100 confident wrong
   lock is defensible with a refusal in front of it, and the int8-vs-fp32 decision stops
   waiting on an fps number. If it costs recall, we have learned the price of the safety net
   before buying it. Ride along: promote `top2_margin.py` / `top2_null.py` out of the
   ephemeral scratchpad into `tools/` so the evidence file is reproducible.
   *Not a detector claim.* n = 5, effective ≈ 3. This measures a cost, not a gate.

3. **frontend-dev — the setup screen: 4-tap calibration with loupe, framing guidance, and a
   mount-height REFUSAL.** This is now the entire setup story and it is on every user's path.
   The refusal is the load-bearing half and the part that does not exist anywhere yet: below a
   stated mount height the app declines to produce the outputs that height cannot support,
   rather than producing worse ones. Manual 4-corner tap is already pure JS, so this is UI
   and policy, not new geometry.

4. **frontend-dev / backend-dev — the resumable overnight batch job shell, instrumented.**
   `BGProcessingTask`, OS-scheduled and killable, realistically overnight-on-charger; the
   phone starts the job **hot** from recording, so never benchmark cold. Build the throughput
   instrumentation *now*, into the shell, so that the moment an A13 exists a sustained-
   throughput number lands in one run instead of a build-then-measure round trip.

5. **researcher — the rally-boundary scoring harness, specified against the protocol, no
   labels required yet.** Pure paper: how the timeout rule's boundaries will be scored against
   `data/gold/<clip>.points.json` at the pre-registered ≥90%-within-2.0 s bar, and the
   `assert_no_point_boundary_gold_leak` guard keyed on basename (T17) — which must be in place
   **before** the founder writes a single label, because 4 of the 9 eligible raw files are
   already ball gold under the same basename.

6. **qa — re-verify mobile parity after items 1–2 land.** Independent numbers, as always.

**Explicitly NOT dispatched, so it is not mistaken for forgotten:** the court mask sweep gate
run (orphaned by §2.2), the `seen_frac` §7 replacement (unrunnable — no compliant reference),
far-court recall labelling (consumer is parked), any seventh court branch (rule 3).

---

## 5. The A13 / Mac dependency — what can and cannot finish without hardware

### 5.1 The Mac dependency is dead. Retire it.

My own agent memory (`v1-critical-path-is-founder-blocked`) records P0-0 as "needs a Mac.
Procurement, not minutes." **That is stale.** The export runs on a GitHub-hosted `macos-14`
runner, the workflow is on `origin/master`, the push bar was lifted 2026-09-04 and the one
defect is fixed. It is a button press. I am updating that memory in this run.

### 5.2 What genuinely needs a physical A13-or-newer iPhone

Not a Mac, not a Simulator, not a cloud macOS VM with no phone attached:

1. **Sustained throughput at thermal steady state.** The honest bar for this product. Desktop
   arithmetic (ball 0.7 + pose 0.4 ≈ 1.1 s/frame; a 10-min clip ≈ 5.5 h) says a 60–90 minute
   match needs roughly an order of magnitude more than desktop CPU. Whether an A13's ANE
   supplies that is the single largest open unknown in v1, and this project has a standing
   rule against quoting an unmeasured fps.
2. **The int8-vs-fp32 ship decision.** fp32 is 43.0 MB against 10.9 — 4× — and nobody can say
   whether it is affordable. Option 2 in §4 can *narrow* this but not close it.
3. **P0-2, pose affordability.** Split cleanly in two: the **accuracy** half is unblocked by
   five minutes of founder corner-clicking (§3 #1); the **cost** half needs the device.
4. **Thermal and battery behaviour of an overnight job**, and whether iOS's scheduler actually
   runs it to completion.

### 5.3 How much of v1 finishes without the device

**Almost all of the building; none of the three go/no-go calls.** Buildable today, at full
speed, with zero hardware: the Core ML artefacts, the whole app shell, capture and import, the
calibration screen, the refusal surface, the results UI, the batch job and its instrumentation,
the rally-boundary harness, and every parity check qa runs. That is the bulk of the remaining
~40–50 sessions.

What cannot finish: (a) is it fast enough to be a product, (b) int8 or fp32, (c) does an
overnight job survive. **All three are one purchase away, and none of them is a research
problem.** That asymmetry is the whole argument for §3 item 0: we are about to spend tens of
sessions building against three unknowns that a secondhand iPhone 11 retires in an afternoon.

**The consequence three steps out, stated because nobody will catch it otherwise:** if the
device arrives late and throughput comes back *bad*, the fix is not optimisation — it is a
product cut (analyse a set, not a match; downscale pose; drop a stage), and that cut is
cheaper to make at session 15 than at session 45. **The device is not a verification step at
the end. It is a scoping input, and it is late already.**

---

## THE SINGLE NEXT DISPATCH

**backend-dev — push `master`, then trigger `.github/workflows/coreml-export.yml`
(`workflow_dispatch`, `macos-14`) and retrieve the `coreml-export` artefact.**

One deliverable: the Core ML artefacts from `ios/coreml_export/`, in the repo or recorded as
having failed and why. It is minutes of work, it is on the critical path, the two things that
blocked it (a standing push bar, a hard-coded checkpoint path) are both resolved, **the
artefact expires in 14 days**, and it converts the project's oldest hardware blocker from
procurement into a solved problem. Nothing else in the queue is both this cheap and this far
upstream.

---

## NOT ESTABLISHED THIS RUN

- **Session prices in §2.2 are pm estimates**, not measured — the ~15–20 sessions freed by the
  court cut is arithmetic from the 40–50 vs 55–70 parity range in agent memory, not a
  bottom-up plan.
- **The two accuracy floors in §2.3 are pre-registered, not validated.** They are written
  before the labels exist, which is the point; they will be tested, not tuned.
- **Whether `origin/master` already carries the `export_coreml_p0.py` fix.** The brief in §4
  item 1 assumes it may not and says push first; the dispatched agent should verify rather
  than assume.

