# Working journal — live state

**If a session or an agent died, read this file first.** It is the durable record of what
is in flight, what is blocked, and what was decided. It is written DURING work, not after,
so a rate-limit kill or a crash leaves it usable.

**Rules for whoever writes here (lead or teammate):**
- Update it as you go, not at the end. A journal written at the end does not survive a kill.
- **NOW** and **BLOCKED** are rewritten in place — they describe the present, not history.
- **LOG** is newest-first and gets **compacted** when it passes ~40 lines: fold resolved
  entries into one line each, delete anything superseded. This file must stay short enough
  to re-read cheaply, or it stops getting read.
- Numbers here are pointers. The authority is `docs/STATE.md` + `docs/evidence/`.
- Never put a result here that belongs in STATE. This is working state, not findings.

**Last updated:** 2026-08-29, after the motion gate failed and the corner sheets were built.

---

## RESTART CHECKLIST — run this before anything else after a death

A usage limit kills a subagent outright; the session itself resumes
(`autoContinueAtUsageLimit`). The doorman does not know the agent died, because a killed
agent never fires `SubagentStop`. So the corpse keeps holding its slot, and the first
thing you try — re-dispatching the work that just died — is the thing it blocks.

1. **Read the journals.** `.claude/journals/lead.md` first, then the teammate's own.
2. **Reconcile live agents against held slots:**
   ```
   ls .claude/.agent-locks
   ```
   Compare with `ListAgents`. A lock with no matching live agent is a corpse — it frees
   itself after 30 min, or clear it now: `rm .claude/.agent-locks/<id>`.
3. **Check for parked work:** `ls .claude/.agent-queue` — refused dispatches live here and
   survive a death. The directory is gitignored, so nothing else will surface them.
4. **Then resume**, preferring the killed agent's uncommitted files over a restart.

## REPORTING RULE — founder instruction 2026-09-02

**Do not surface founder-blocked items unless the founder asks for them.** They go in
`docs/DECISIONS_PENDING.md` silently and stay there. Ending a status with "waiting on
you..." is the interrupting this rule exists to stop — the founder asked to be left to
work, and asks for the list when they want it.

Report what was DONE. Keep the queue to yourself until requested.

## RESUME AFTER A KILL — read this first, it is one paste

A usage limit kills the session outright and NOTHING restarts it — not this journal,
not a scheduled job, not a cloud agent (a cloud agent cannot see this local repo).
Resumption costs exactly one message. Paste this:

    /loop Work docs/STATE.md's Open table continuously and autonomously, and ALWAYS
    use the teammate agents for feature work — 3-live-agent project cap, one direct
    child at a time. NEVER stop to ask; append anything needing a founder decision to
    docs/DECISIONS_PENDING.md and keep going. Pre-register a bar before running
    anything, one variable per A/B, a failed bar stays failed, never score a model
    against its own output, inspect the rejects not what a filter kept. Commit to
    master, DO NOT PUSH. Keep this journal's NOW current.

Then, before doing anything else, read in this order:
  1. `docs/STATE.md` — Open table. The live record. Authority for every number.
  2. `docs/DECISIONS_PENDING.md` — what is waiting on the founder, and what was done
     instead so the blocker was not also idle time.
  3. "What has not worked" in STATE — **13 hypotheses died there this week.** Do not
     re-derive them. Each row names the number that killed it.

## NOW — what is running

**An autonomous /loop, self-paced, working `docs/STATE.md`'s Open table.** Founder
instruction 2026-09-02: *keep going, do not ask questions, record decisions for later.*
So nothing below is a request — it is a queue to hand over when asked.

**If you are a fresh context reading this after a reset: resume the loop.** Re-read
`docs/STATE.md` Open first, then `docs/DECISIONS_PENDING.md`. Do NOT re-derive the
closed branches listed in "What has not worked" — 13 hypotheses died there this week.


## PARKED — work that was started and stopped

- ~~**Court mask sweep: a possible gate pass, unclaimed.**~~ **CLOSED 2026-09-02 by qa —
  it was already shipped.** `f41a489` (2026-08-21) is the ship commit for surface routing
  and `calibration.court_line_mask` is unchanged since (qa read the live function, not the
  commit message). `court_mask_sweep.json`'s content was rewritten a week LATER by
  `040df9d` — a re-measurement of the shipped router banked for the record, not a new
  candidate. Both routed variants are bit-identical to shipped on gold; the only clip that
  ever differs is `am_rally32short`, and only because `baseline` predates the router.
  Gate re-run independently: 12/20, max 13.9 px, zero over 20. Nothing replaces it — the
  next court-mask idea has to be a genuinely new candidate.
- **Corner contact sheets for the 25 `*_pts.json` files.** BLOCKED item 3 asks the founder to
  audit calibrations by rendering corners. Rendering is the lead's job, not theirs: build a
  sheet per file with the four clicked corners drawn on a real frame, so the founder's task
  drops from "audit" to "look and say which are wrong." No tool does this today —
  `validate_new_clip.py --audit` is residual-only, which is precisely what T23 defeated.

## BLOCKED — needs the founder, nothing proceeds without it

Ranked by leverage (pm, 2026-08-29). **The v1 critical path is 100% founder-blocked** — the
two gates that decide whether an iPhone can run this (P0-0 Core ML export, P0-2 pose
affordability) both wait here, and nothing dispatchable is on that path.

1. **Re-click `yt_match40` corners** (~5 min) — unblocks P0-2, the top v1 runtime risk.
   Calibration confirmed wrong (T23). `near_br_doubles` runs off-frame and needs
   extrapolating. Sheet ready at `data/output/corner_audit/yt_match40_corners.png`.
2. **Look at `data/output/corner_audit/`** (~10 min) — 27 sheets BUILT and committed
   (`cc213d3`). Lead cannot settle two of them: on `am_hard_utr` and `sAjkpeRq4P4` the far
   corners land near the NET rather than the far baseline, and a still frame does not
   separate those at a low mount. The camera-height fit says both are fine (1.74 m, 3.33 m)
   but that is corroboration, not proof.
3. **A Mac + a physical A13.** The Core ML export itself fails on Windows — `coremltools`'
   wheel lacks the native library that writes an `mlprogram`'s weights.
4. **The TrackNet idea — or one sentence: detector-side or chain-side?** If detector-side,
   rule 6 leaves chain work open and speed coverage unparks to the front of the queue.
5. **~3-6 h point-boundary labels. DO NOT START** until researcher's protocol lands, or the
   hours get spent twice. Hardcourt + Clay only.
6. **Re-label 8 court gold frames** (~1 min). Rule 9 — recorded, never quietly fixed, so
   permanently the founder's. Lowest urgency; court is not v1-blocking.
7. ~~**Is the score layer settled in scope?**~~ **ANSWERED - not a founder question.** CLAUDE.md rule 12
   (2026-08-27) rules it IN, and that is the later ruling. Do not re-ask; the real blocker is ground truth.
8. **Is a Mac weeks or months away?** A sequencing input, not a nudge — pm would build a
   different plan for a months-long gap.

## DECIDED — binds everyone, do not reopen

- **iOS/iPadOS only, A13+**, Core ML/ANE the only inference target. **100% on-device
  forever** — a proposed network dependency is a scope violation.
- **Three live agents PROJECT-WIDE**, counting the whole tree — a teammate calling a
  teammate spends the same quota. Teammates MAY call each other. A Pro-plan QUOTA cap, not
  machine load; a one-word agent still costs ~38k. Enforced by
  `.claude/hooks/agent-cap.sh`; a refused call is PARKED verbatim, not lost, and handed
  back when a slot frees — never retry it and never shrink it to fit.
- **The rally/score layer is in scope but has no ground truth.** A compliant source is a
  prerequisite line item.
- Court auto-detection and the activity gate/trimmer are **not to be run unattended** —
  the first fires a stopping rule that closes a lane, the second needs a human to look at
  what it discarded.

- **v1 ships TRACKNET** (founder, 2026-08-29). The chain verdict was SPLIT, so this is a
  product call: fewer phantom balls beats more speed coverage, and it is the only detector
  with a Core ML path. BallNet v21 is the upgrade path, not a rejected option.
- **Line calling is PARKED** (founder, 2026-08-29). The 0.15/0.20 m refusal band is NOT
  chosen. `live.py` keeps its 0.05 m. qa's margin curve is filed in STATE, unactioned.
- **P0-3's substituted identity test is ACCEPTED** (founder, 2026-08-29).
- **P0-3 is no longer provisional** — 25 context tiles reviewed 2026-08-29. Both strict
  passes are real far-end figures; sampled rejections are real far players thrown out for
  anchor distance. The crop finds the far player.

## LOG — newest first

- **2026-09-03** — **doorman v2 installed** from `agent-team-package/swingvision-install/`
  (INSTALL.md steps 1-5). New `agent_cap.py`/`agent-cap.sh`; settings env teams flag 1->0,
  spawn depth 1, native concurrent cap 3; `Agent` removed from all five role files, replaced
  by NEEDS DISPATCH + deliver-as-you-go; CLAUDE.md dispatch section gained the run budget
  (12 / 5 h) and the DELIVERABLE/STOP-WHEN brief contract. Four gates verified by synthetic
  payload (brief reject, cap park, hand-back, budget refusal) — all logged to `doorman.log`.
  One real dispatch: SubagentStart recorded spend, SubagentStop freed the slot, no leak.
  **STEP 7 MEASURED AND IT CONTRADICTS THE PACKAGE:** identical zero-tool agent cost
  **36,836** tokens with the real 150-line CLAUDE.md vs **39,105** stubbed to 13 lines — the
  stub cost 2,269 MORE, so CLAUDE.md size is NOT what the ~38k floor is made of. Trimming it
  buys nothing on dispatch cost; run COUNT and brief scope are the only real levers.
  **NOT DONE — needs a fresh session:** check 6, the nesting test (spawn-depth 1 and the new
  role files only load at session start, so this session would report a false result).
  CLAUDE.md had to drop 4 lines to stay at its 150 cap — see the diff, nothing load-bearing
  cut. Note: `claude-md-cap.sh` (and its sibling guards) fire on EVERY write Bash command,
  not just commits — their `"if": "Bash(git commit*)"` is not honoured by this CC version.

- **2026-08-29** — **Far-player MOTION gate FAILS; the null control is CLEAN.** Nearest
  `movers.foot_points` blob to a post-hoc far-player box: **median 5.751 box-heights, 7/15**
  within 1.5, against a bar of <=1.5 on >=10/15. Random-blob control also fails (9.265, 2/15;
  0 of 1000 seeded draws pass), so the negative is a measurement, not candidate density.
  **Bimodal, not marginal** — nothing between 0.62 and 5.75: on him for 7, 173-632 px away
  for 8. Third negative in the player-foot-gate family; rule 3 closes it. All verified by the
  lead: 479 tests pass, `eval/movers.py` byte-identical, both arms re-read from the artifact.
  **A number in MY brief was wrong**: "median ~9 blobs per frame" is pre-`MAX_PLAYERS`;
  post-cap it is **median 2**. That made the control WEAKER than designed (1-in-2.5, and
  random picked the nearest blob outright on 6 of 15) — so the negative survived an easier
  test than intended, which strengthens it. Contrast rider is descriptive, no gate: the
  player's luminance offset **never reaches the court patch's own luminance spread**, colour
  is the stronger channel, and contrast does NOT separate the frames motion found from those
  it missed. Commits `7d002e0`, `be0415e`.
- **2026-08-29** — Corner audit sheets built for 27 of 29 calibrations (`cc213d3`), pm's
  top-ranked item. Reproduces T23 on sight. The **camera-height fit is the isolating screen**:
  `yt_match40` alone fits 11.3 m; everything else 1.3-3.4 m.
- **2026-08-29** — **P0-3 reviewed and STATE corrected.** Built
  `tools/p0_3_context_sheet.py` (full frame + blown-up crop, straight from the probe JSON,
  no model run, no court lines because the calibration is broken). Reviewing the 25 tiles
  **confirmed the crop finds the far player** — the two strict passes are real far-end
  figures distinct from the near-player box, and every sampled rejection is a real far
  player rejected for anchor distance, not a bad detection. **Caught a live rule-1 breach
  en route:** STATE quoted P0-3 as "15 of 25" — that is the POST-HOC relaxed criterion
  (far-sized person anywhere in the crop), while the pre-registered strict test is **2/25
  vs 0/25 control**. The evidence file labelled it correctly; STATE had dropped the label,
  and the lead repeated the unlabelled number to the founder. Row rewritten to carry both
  with their criteria. New design number: a ball-centred 192 px crop holds the far player
  only barely — **median 26.3 px from the crop edge**.
- **2026-08-28** — **pm's ranked queue is EMPTY.** Items 1, 2, 3 and 5 shipped; item 4
  (`bounce_hypothesis`) was measured and FAILED. Items 6 and 7 are the two pm ruled out for
  unattended work. Nothing further is dispatchable without a founder decision or a fresh
  sequencing pass.
- **2026-08-28** — `bounce_hypothesis` v2 **FAILED 4 of 7 bars** and does not ship (defaults
  unchanged, 468 tests pass). More valuable than the failure: it **disconfirmed its own named
  cause**. v2 removed `restitution_band` and gated tighter than v1, so the `wrong` rises
  should have gone to zero — they went 5 clips to 4. A one-variable ablation split the halves:
  removing the band is the good half, "more hypotheses" is the worse half. Reading the 17
  changed frames falsified the mechanism's core claim that a ghost fits neither hypothesis —
  the reflected hypothesis has its own false-acceptance region, covering a lock 502 px off
  track. **Correction to a claim the lead relayed:** `gate_ball_to_court` is NOT dead code —
  on gold caches it removes locks on 4 of 7 calibrated clips (`gold_sAjkpeRq4P4` -674). The
  earlier "14/14 no-op" was cache-family-specific.
- **2026-08-28** — Detector question **settled at the chain and the answer is SPLIT**, commit
  `2ead76a`. TrackNet: solid ghosts 88 -> 62 (-29.5%) for 8 hits. BallNet v21: more
  speed-confident shots, longer trails. `event_audit` underpowered. **This is now a founder
  decision**, because BallNet has no Core ML export path and TrackNet's ONNX already ships in
  `mobile/models/`.
- **2026-08-28** — **Concurrency doorman built, verified and fixed.** A cap kept only in
  CLAUDE.md could not hold, because the lead cannot see what its children spawn.
  `.claude/hooks/agent_cap.py` now counts every agent in the tree; a refused dispatch is
  parked verbatim and handed back when a slot frees. Teammates may now call each other.
  Measured: **~38k tokens is the floor for ANY agent**, so three at once is ~115k before a
  useful result; nested probe read BEFORE=1, INNER=2, AFTER=1.
  **qa passed it on nine checks and broke it on three.** The one that mattered: a read-only
  check is not a gate — counting had no side effect, so several dispatches in one message all
  saw the same free slot and all passed. Fixed with a reservation taken at approval time.
  Also fixed: sanitised agent ids colliding into one lock, and prompts truncated in the
  hand-back with no notice. Recreation guide at `master references/10`.
  **Two lead errors worth not repeating:** a `cd` leaked into a subagent's working directory
  (qa started in `master references/`, not the repo root); and Python's `write_text` silently
  rewrote seven LF files to CRLF, which the repo's own CLAUDE.md cap hook caught.

- **2026-08-28** — Detector comparison killed by usage limit. **Lesson: nothing restarts a
  dead subagent.** `autoContinueAtUsageLimit` resumes the SESSION; a subagent that hits the
  limit is killed outright and no mechanism polls for it. The failure notification IS the
  restart trigger — treat it as one, do not just report it.
- **2026-08-28** — Audio screen: **0 bail-outs of 88 clips, 0 of 62 Shell.** The feared
  correlated audio/vision failure on echo-heavy indoor courts did not occur. Two findings:
  the binding threshold is level-dependent (58-65% of candidates discarded on quiet indoor
  venues vs 17-25% outdoors — same class as the unscaled 720p constants), and
  `impact_envelope`'s rolling median is O(n·win) with a **13.5 GB peak allocation** on a
  28-min clip, never hit because nobody has run it on a full match. Committed `cae1dcc`.
- **2026-08-28** — Refusal band measured (qa). Both real mounts at/below the floor within
  10 cm; clear it from ~20 cm. `live.py`'s shipped `line_margin_m = 0.05` sits inside the
  unreliable zone. **qa correctly refused to write to the codebase** — its charter forbids
  it and my brief wrongly asked. Its findings still need filing by the lead.
- **2026-08-28** — P0-3 rebuilt. Crop finds the far player where full frame does not
  (0/25 control vs 15/25 crop192@640), and the mechanism is **upscale factor**, peaking at
  ~100-140 px of player in the tensor — a transferable design number. Found en route that
  `yt_match40`'s calibration is fabricated, which **withdrew P0-2's yt_match40 column**.
  Commits `10ed80f`, `8454e7e`.
- **2026-08-27** — P0-2 FAILED its gate: pose downscaling destroys the far player
  (11.0% → 0.1% → 0.0%). Closed full-frame downscaling as a way to afford pose on an A13.
- **Two lead errors worth not repeating:** sent execution work to `researcher`, which has
  no `Bash` by design; and claimed an agent was running without calling `ListAgents`.
  Match the task to the agent's `tools:` first, and verify state before asserting it.

---

## PRE-REGISTRATION — int8 ball-graph parity, Lane 1. Written 2026-09-03 BEFORE any run

Written before `yt_match40`'s int8 pass finished, before any new clip was extracted, and
before any mitigation graph existed. A failed bar stays failed.

**The bar is UNCHANGED from 2026-09-02.** It is not being re-derived or re-tuned; it is
being applied to more clips and to a candidate fix. Per comparison (one clip, its full
178-frame span, int8-through-JS-decode vs fp32-through-JS-decode):

1. null/non-null agreement **>= 90%**
2. median position disagreement when both fire **<= 2 px**
3. **no single frame > 10 px**

### (b) Cross-clip rate — pre-registered definitions

- **Clip set, fixed now, before any of them is run:** the 6 gold clips
  `am_hard_utr`, `yt_rally2`, `yt_match40`, `gold_clay`, `gold_am`, `gold_shell`.
  Chosen for surface spread (Hardcourt 3 / Shell 2 / Clay 1) and because they are the
  gold registry's own members - not selected on any int8 result. Same 180-source-frame
  span (0-179) for every clip, the probe's existing default. **No clip is dropped after
  the fact**, including one that yields few both-fire frames; a low-n clip is reported
  with its n, not excluded.
- **Reported rate = failing frames / both-fire frames, pooled across the 6 clips**, plus
  the per-clip numerator/denominator, plus **clips failing condition 3 / clips run**.
- **A "failing frame" is one with disagreement > 10 px** - the same threshold as
  condition 3, not a new one.
- No pass/fail attaches to the rate itself. It is a characterisation; the pass/fail is
  condition 3 per clip.

### (c) Mitigation — pre-registered, ONE variable

Shipped graph = `quantize_dynamic(fp32, weight_type=QInt8)`, `per_channel` defaulting
to False. **Arm B changes exactly one argument: `per_channel=True`.** Nothing else -
same source fp32 graph, same weight type, same op set, same export script path.

- **Cheap SCREEN first (a necessary condition, not the bar):** run Arm B on the 4 known
  failing frames only - `am_hard_utr` 0147, `yt_rally2` 0108/0109/0110. All 4 must come
  within 10 px of fp32. **If any of the 4 still fails, Arm B is REJECTED and no full run
  is paid for.** A screen that passes proves nothing on its own - it only buys the right
  to run the full bar.
- **The bar, if the screen passes:** conditions 1-3 above on the FULL 178 frames of
  **both** currently-failing clips (`am_hard_utr`, `yt_rally2`). Arm B ships only if
  condition 3 passes on both. Passing on one is a failure.
- **Reported, not gating** (named now so it cannot be quietly dropped later): the
  null-mismatch count per clip (shipped int8: 8 on `am_hard_utr`, 2 on `yt_rally2`) and
  the file size. A fix that buys condition 3 by losing detections is a trade to state,
  not a win.
- If Arm B is rejected, the second named mitigation (final conv kept in higher
  precision) is the next candidate and gets this same screen-then-bar treatment. Only
  one mitigation is required by the task; a second is only run if time allows.

### What would make this whole lane wrong
The probe substitutes desktop `onnxruntime` CPU for `onnxruntime-react-native`. Every
number here is quantisation effect measured through that substitution. It stays true.

### Arm B REJECTED, and Arm C pre-registered. 2026-09-03, BEFORE Arm C ran

**Arm B (`per_channel=True`) is REJECTED — and the reason is not that it lost.** The graph
it produced is **byte-identical to the shipped control** (same sha256, same 10,918,923
bytes). `quantize_dynamic` forces `QuantizationMode.IntegerOps`, mapping Conv to
`ConvInteger`, and ORT's `ConvInteger` operator class has **no per-channel branch at all** -
only `QLinearConv` (static) and `QDQConv` consult `is_per_channel()`. TrackNet is 18 Convs
and nothing else quantisable, so the flag touched zero weights; all 18 `*_weight_scale`
initializers came out scalar. 4/4 screen frames failed at exactly the control's distances.
**Per-channel int8 for this graph is unreachable through `quantize_dynamic`** - reaching it
needs static QDQ plus a calibration set, which is a second variable and therefore a
different experiment, not this one.

**Arm C, pre-registered now, before it is built or run. ONE variable versus the shipped
export:** `nodes_to_exclude=[<the final Conv>]`, keeping the heatmap-producing convolution
in fp32. Everything else identical - same source fp32 graph, same `QuantType.QInt8`, same
op set, `per_channel` back at its default False (Arm B proved it inert here, so carrying it
would add a knob that provably does nothing while muddying the diff).

Rationale against the named mechanism: the failure is **area erosion in the heatmap**, and
the final Conv is what writes the heatmap. Arm B could not touch it. Arm C can.

Same treatment as Arm B, unchanged:
- **SCREEN** (necessary, not sufficient): the 4 known-failing frames - `am_hard_utr` 0147,
  `yt_rally2` 0108/0109/0110 - all within 10 px of fp32. Any failure REJECTS Arm C with no
  full run paid for.
- **BAR** if the screen passes: conditions 1-3 on the FULL 178 frames of BOTH failing
  clips. Passing one clip is a failure.
- **Reported, not gating:** null-mismatch count, file size (excluding a conv gives back
  size), and per-frame latency.

**One correction to the mechanism as previously written, from Arm B's blob dump.** STATE
records `yt_rally2` as "the mirror image - int8 grows the false blob". That is true of
0109 only. **0108 is the same erosion as 0147** (the true blob is deleted outright; the
false one is unchanged), and **0110's fp32 answer is an exact 2640-vs-2640 tie** resolved
only by raster scan order - a weak instance of the bar, and worth naming before anyone
counts it as a strong one.

### RESULTS AS THEY LAND (written during, not after)

- **Arm B `per_channel=True`: REJECTED** - byte-identical graph, 4/4 screen frames fail. See above.
- **Arm C `nodes_to_exclude=[final Conv]`: REJECTED** - a real change (11.36 MB vs 10.92,
  17 ConvInteger + 1 fp32 Conv) but 3 of 4 screen frames still fail. 0147 got 0.16 px
  WORSE; 0108 bit-identical to the control; only 0110 passed and 0110 is the tie-break
  frame flagged as the weak instance. Blob dump on 0147: the true blob's area went
  **15 -> 2 (control) -> 3 (Arm C)** against a target of 15. **The negative localises the
  fault: erosion is already present in the int8 features ARRIVING at the final conv, so
  output-layer precision is the wrong lever.** Both named mitigations are now spent.
- **`yt_match40` full 178: PASSES all three bars.** null agreement 170/178 (95.5%),
  both-fire 93, median **0.000 px**, max **1.362 px**, 8 null mismatches. First clip to
  pass. Its failing-frame count is **0 of 93**.
- **`gold_clay` full 178: PASSES all three bars.** 175/178 (98.3%) null agreement,
  both-fire 77, median 0.000 px, max **0.960 px**, 3 null mismatches. **0 of 77** failing.
- **`gold_am` full 178: PASSES.** 173/178, both-fire 67, median 0.137, max **0.688 px**, 5 null mm. 0 of 67.
- **`gold_shell` full 178: FAILS, and it is the WORST outlier yet - 185.066 px** (tag 0097).
  177/178 null agreement, both-fire 89, median 0.000, 1 null mm. **1 of 89.**
  Blob dump on 0097 - the same mechanism, doing BOTH things at once:
  fp32 true 13x220=2860 vs false 11x242=2662 (margin 7.4%); int8 erodes the true blob
  13->10 (2200) AND grows the false one 11->12 (2904). False wins by 32%.

**CROSS-CLIP RATE, 6 clips, all pre-registered before any ran:**
`5 failing frames / 528 both-fire frames = 0.95%`, and **3 of 6 clips FAIL condition 3.**
Per clip (>10px / both-fire): am_hard_utr 1/53, yt_rally2 3/149, yt_match40 0/93,
gold_clay 0/77, gold_am 0/67, gold_shell 1/89.

**The rate has a much better denominator, and it makes the failure PREDICTABLE.**
`margin_census.py` (scratchpad; guarded - the top blob's centroid must equal what the real
`_decode()` returned, 0 guard failures in 528 frames) counts fp32 frames where the
runner-up blob scores >=85% of the winner:

| clip | both-fire | close races | % |
|---|---|---|---|
| am_hard_utr | 53 | 4 | 7.5% |
| yt_rally2 | 149 | 9 | 6.0% |
| yt_match40 | 93 | **0** | 0.0% |
| gold_clay | 77 | **0** | 0.0% |
| gold_am | 67 | 1 | 1.5% |
| gold_shell | 89 | 2 | 2.2% |
| **pooled** | **528** | **16** | **3.0%** |

**All 5 failures are inside those 16 frames, and the two clips that pass cleanly have
ZERO close races.** So the honest rate is not 0.95% of frames - it is **5 of 16 close
races (31%)**, and the close-race rate is what varies by clip. The 0.15 threshold was
chosen AFTER seeing the failures (widest failing fp32 margin 7.4%, plus headroom), so it
is NOT independent of them - qa is checking whether the zero-on-passing-clips result
survives other thresholds. Until that lands, treat the split as suggestive, not measured.

**Derived candidate, NOT measured, NOT proposed as done:** the close race is visible in the
fp32 heatmap at decode time, so a decode that REFUSES when the margin is under threshold
converts a confident wrong lock into a null the smoother already handles. Cost, computable
from the table: it refuses 16 frames to prevent 5 wrong locks - **11 of those 16 refusals
are frames int8 currently gets RIGHT**. Rule 5 says score it at the CHAIN or not at all.

**LANE 1 CLOSED 2026-09-03, commit `28ead70` (committed to master, NOT pushed).** All three
asks done: `yt_match40` finished (PASS), cross-clip rate exists (5/528, 3 of 6 clips fail),
both named mitigations measured to rejection. qa verified independently and corrected the
close-race framing; corrections are in the evidence file, not just here. The one thing left
is a product call and it is in `docs/DECISIONS_PENDING.md` item 0 - **do not surface it
unless the founder asks** (reporting rule, 2026-09-02).

Next candidate if this lane reopens: a per-layer activation diff to find where the erosion
first appears. Arm C proved the final conv is not it. That is a new experiment and needs its
own pre-registration.

---

## PRE-REGISTRATION — smoother innovation gate: is a BACKWARD-pass re-admit separating?
Written 2026-09-03 BEFORE anything ran, before the code was read in detail.

**Target:** the speed-coverage row - `smooth_forecast` costs **-11.0 / -8.1 pts** under
TrackNet and is the largest single-stage cost. Mechanism already measured: its innovation
gate deletes **14-17% of surviving REAL detections** in every arm.

**Why a new attempt is allowed at all.** Rule 3 - every dead smoother idea in STATE changed
what the FORWARD gate admits (`max_gap_s` both directions, `reset_after`, the `blocked`
mask, `bounce_reset`, `bounce_hypothesis` v1/v2). The evidence file states the requirement
outright: *a third attempt needs a mechanism that SEPARATES real from false, not one that
admits more of both.* The smoother is **non-causal** (Kalman + RTS, offline by design), so
the backward pass holds information the forward gate did not have when it rejected. Nothing
in STATE has tested whether that information separates. This is a NEW question, not a
re-proposal.

**MEASURE THE SEPARATION BEFORE BUILDING ANY FIX.** No fix is authorised by this
pre-registration - only the measurement of whether the signal has power.

The population: detections the forward innovation gate REJECTS. Each is adjudicated
**against human gold clicks** (1851 clicks / 308 no-ball frames, TEST-only) - real if within
the gold tolerance of a click, ghost otherwise. Never against the smoother's own output;
that would be a model grading its own homework.

The signal: each rejected detection's distance to the FINAL RTS-smoothed trajectory.

- **PASS (the signal separates, worth building):** the two distributions separate at
  **>= 3:1** real-to-ghost at the best single threshold - i.e. some cut re-admits >=3 real
  detections per ghost re-admitted - on **>= 2 of 3** clips, AND a **shuffled-label null
  control** (same distances, labels permuted, seeded, 1000 draws) passes at under 5%.
  3:1 is chosen against the project's own precedent: `bounce_hypothesis` was allowed to
  claim separation at 9:1 but its product gate still failed, and the ~7:1 structural
  exchange rate is the number this project keeps hitting. A mechanism below 3:1 cannot
  survive a product gate, so measuring further would be wasted.
- **FAIL:** anything else. **A failed bar stays failed and this branch closes** - it would
  be the third measured negative in the smoother-gate family, and rule 3 then bars a fourth.
- The null control is MANDATORY, not optional. Without it a positive is uninterpretable.

**NOT authorised by this:** changing `smooth_forecast`, shipping anything, or quoting a
coverage gain. A separating signal earns a build brief and a product gate, nothing more.
