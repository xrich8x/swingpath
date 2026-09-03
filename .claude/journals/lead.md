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
Nothing below is a request — it is a queue to hand over when asked.

**Live child: `researcher`** — the point-boundary label protocol
(`docs/evidence/point-boundary-label-protocol.md`). It unblocks 3-6 h of queued founder
labelling that is explicitly gated on it, and the score layer is v1 scope per CLAUDE.md
rule 12. One direct child at a time; dispatch the next on its return.

**Closed this session (2026-09-03):**
- Lane 1, int8 ball graph — `28ead70`. 3 of 6 clips fail; both named mitigations rejected.
  The remainder is a product call, in DECISIONS_PENDING item 0. Do not surface it unasked.
- Smoother-gate backward-pass re-admit — `1fbcb6f`. FAIL, 0 of 3 clips, null p=0.526.
  **Third negative in that family; rule 3 now bars a fourth, cross-detector variant included.**

**Queue, re-sorted after the smoother negative** (the negative deleted the obvious follow-up,
which is the point of re-sorting on every return):
1. `suppress_false_locks` is now the largest ATTACKABLE speed-coverage cost (-5.2 / -4.4)
   — the smoother is bigger but its gate family is closed.
2. Court search problem (STATE rows: right court / wrong width, indoor shell, AGREE_PX on 4K)
   — all three are downstream of the same unsolved search.
3. Off-machine backup — still open; note pushes are barred, so this needs a non-push route.

**If you are a fresh context reading this after a reset: resume the loop.** Re-read
`docs/STATE.md` Open first, then `docs/DECISIONS_PENDING.md`. Do NOT re-derive the closed
branches in "What has not worked" — 16 hypotheses have died there now.


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

## PRE-REGISTRATIONS — 2026-09-03. Full text is in git, not here

Compacted per this file's own rule (*numbers here are pointers; the authority is
`docs/STATE.md` + `docs/evidence/`*). Each bar was written and **committed before** its
result, which is the point of recording them; the commit named is the one that first
carried the text, and `git show <commit>:.claude/journals/lead.md` prints it in full.

| Pre-registration | Written in | Result | Verdict |
|---|---|---|---|
| int8 ball-graph parity — 6-clip set, rate definition, Arms B and C | `28ead70` | `28ead70` | 3 of 6 clips FAIL; both mitigations rejected |
| Smoother gate — backward-pass re-admit separation, >=3:1 + null control | `1fbcb6f` | `1fbcb6f` | **FAIL** 0 of 3; branch closed, rule 3 bars a fourth |
| `seen_frac >= 0.5` — does the gate predict speed error, G/N/I + n floor | `79c381d` | `6013653` | INDETERMINATE; G refuted everywhere; gate at chance |

**The one process lesson from these three, worth keeping in front of me:** on the int8
lane I picked a threshold *after* seeing which frames failed, and qa showed it collapsed
under a sweep. Both later briefs forbade naming a threshold from the data that revealed the
problem, and both agents complied. Keep that clause in every threshold brief.

---

## RATE-LIMIT KILL 2026-09-03 ~23:45 — and what the lead did instead

The `Definitive seen_frac gate numbers` run was **killed by a session limit before it did any
work** (its whole output was "I'll start by reading my journal"). Session limit resets 19:40
Asia/Manila. Locks checked and were already clear — no corpse to reap this time.

**Do not re-dispatch that brief while the limit holds**; a re-dispatch dies the same way and
spends a run for nothing. The lead is running the work directly instead: the harness is now a
committed tool (`tools/seen_frac_speed_error.py`, `cf556a5`) with clips, seed and arm as
arguments, so this particular task no longer needs an agent at all. That is a side benefit of
having promoted it out of the scratchpad an hour earlier.

**PARKED, verbatim, so it survives:** multi-seed classifier margin (accept-precision minus
base rate) on the FAITHFUL 2.5 m config, both arms, against the **>=10-point bar already
pre-registered in the evidence file's own section 7** — not a bar chosen after seeing the
number. Plus the restated reject characterisation, and an explicit supersedes-list naming
every number the 4.0 m defect invalidated.

Seed 0, faithful config, already in hand: accept-precision **0.500** vs base rate **0.467**
(unrestricted) and **0.500** vs **0.466** (shipped-shot) — a margin of **+3.3 / +3.4 points**
against a >=10 bar. One seed is not evidence, which is the whole lesson of the run before
this; 10 seeds x 2 arms are running now.

---

## PRE-REGISTRATION — the §7 held-out replacement-bar sweep. 2026-09-04, BEFORE it runs

Executing the pre-registration in §7 of `does-seen-frac-predict-speed-error.md`. Two things
§7 could not have known, both settled here BEFORE any sweep runs.

**1. §7's own named candidate clips are the two WORST available, and are rejected.** It named
`court_pts_refined` and `eala_pts_auto`. Their audit stamps fit camera heights of **12.28 m**
and **8.89 m**. That is the exact signature that exposed `yt_match40` - stamped PASS at 0.9 px
while grossly wrong, and STATE records the camera-height fit as *"the one screen that isolates
it"* (every sane clip fits 1.3-3.4 m). Using either would repeat T23 knowingly. **Rejected on
that ground, before seeing any result they would produce.**

**Held-out clips used instead** - all `_audit` verdict PASS, residual <=1.4 px, camera height
in the plausible court-side band, `img_wh` read from the actual clip (not assumed, which
`yt_court` is), and none used in the burned experiment:

| clip | residual | camera h | resolution |
|---|---|---|---|
| `L73ep7JHiJ4` | 0.7 px | 2.89 m | 1920x1080 |
| `mpc_tuesday_p01` | 0.9 px | 2.79 m | 3840x2160 |
| `flexi_franz_p01` | 0.2 px | 2.50 m | 3840x2160 |
| `tc8CGFxyRE8` | 1.4 px | 2.00 m | 1920x1080 |

Four distinct venues, exceeding §7's minimum of 3. `mpc_tuesday_p07` (0.5 px, 2.81 m) is
available as a fifth but is **the same venue as p01**, so it is not independent and is not
counted toward the >=3-of-N tally. Excluded and why: `sAjkpeRq4P4` (PASS 2.8 px but its corner
sheet is one of the two the lead could not settle), `uR5q2cSM6AY` (PASS but 9.3 px).

**2. The accuracy label must be FIXED across the sweep, and currently is not.**
`classifier_table` defines "accurate" as `<= median abs% error of the ACCEPTED set`. That is
defensible at a single fixed threshold - it scores the gate against the population it creates -
but it makes a **sweep meaningless**, because the label moves with every candidate `t` and
precisions at different `t` are then not comparable.

**For the sweep, and only the sweep, "accurate" is `<= the median abs% error of the WHOLE
clip population`, computed once, independent of `t`.** Base rate is then ~0.50 by
construction and identical at every step, so the >=10-point margin means the same thing
everywhere on the curve. The single-point table keeps its existing definition unchanged; the
two are reported separately and never mixed.

**Bar, unchanged from §7:** a replacement `t` is admissible only if on **>= 3 of the 4
held-out clips** (a) accept-precision at `t` beats the fixed base rate by **>= 10 points**,
and (b) both neighbours `t +/- 0.05` are within 3 points of `t`'s precision - the plateau
test. Sweep [0.20, 0.90] step 0.05, FULL curve reported.

**Multi-seed or it does not count.** >= 5 seeds; a `t` admissible on a single seed is not
admissible. This file's own instability finding is the reason.

**Court-coverage faces the identical sweep, as §7 requires** - named, not adopted, and with
its partly-mechanical confound restated at the point of reporting.

**Nothing ships from this.** An admissible `t` earns a real-footage confirmation arm (§7 item
4), which no compliant reference currently supports.
