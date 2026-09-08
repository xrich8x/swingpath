# qa — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — 2026-09-09: CANDIDATE PROPOSAL RECALL (court only)

Question: on what fraction of gold clips does a court candidate within the accept
tolerance (WRONG_PX_640 = 20.0 px @640) EVER appear — regardless of whether the vote
accepts it? Separates "the search never found it" from "it found it and lost the vote".
GATES backend-dev's CNN-global/classical-local reorder. Message backend-dev with the
headline as soon as I have it.

DELIVERABLE: docs/evidence/candidate-proposal-recall.md
STOP-WHEN: audit run + verdict written, or ~40 tool calls.
Instrument: eval/candidate_audit.py (exists, marked UNRUN as of 2026-08-24).

## PRE-REGISTERED BAR — written BEFORE any result was seen (this is the whole point)

Let R = (# gold clips where >=1 per-frame lock lands <= 20.0 px @640 from the human
court) / (# gold clips audited).

- **VOTING BINDS** if R >= 0.80. The search reaches the right answer on nearly every
  clip; the loss is downstream (scoring/agreement/accept-conjunction). A CNN global
  localiser would then be replacing a stage that is already working -> external
  document's premise COLLAPSES.
- **SEARCH BINDS** if R <= 0.60. On >=40% of clips no correct candidate is ever
  produced, so no downstream gate/score/vote change can recover them -> external
  document's premise HOLDS, rebuild justified.
- **MIXED / INDETERMINATE** for 0.60 < R < 0.80. Say so; do not round either way.

Secondary, also pre-registered:
- HEADROOM H = (# clips with >=1 good candidate) - 12 (clips the shipped gate already
  accepts). H >= 4 clips => materially recoverable recall exists downstream.
- SHELL (indoor, historically 0/5 accepted): search binds on shell if shell recall
  <= 1/5; voting binds on shell if >= 4/5; between = mixed.
- MOUNT HEIGHT mechanism (net tape overlapping far baseline below ~2.0-2.2 m) is
  CONFIRMED as a distinct mechanism only if recall drops by >= 40 percentage points
  across the 2.0-2.2 m boundary AND the low group has >= 3 clips. Otherwise: not
  established, report the numbers only.

A failed bar stays failed. I will not read the threshold off the results.

## KNOWN CAVEAT TO STATE UP FRONT (identified from source before running)
`audit()` calls `cf.auto_fit_frame` per frame, which returns ONE winner per frame,
already past the per-frame accept conjunction. So what this instrument measures is
**per-frame ACCEPTED-LOCK recall across k frames**, which is a LOWER BOUND on true
proposal-stage recall (raw quad candidates before scoring are strictly a superset).
=> a HIGH R is strong evidence for "voting binds". A LOW R is weaker evidence for
"search binds" — it could still be the per-frame accept rule killing a proposed
candidate. The script's `truth_would_pass` / `truth_fails` columns address exactly
that second half (would the accept rule take the human court if handed it), so I
must report BOTH.

## LOG
- 2026-09-09: read journal + memory; read eval/candidate_audit.py in full (339 lines,
  docstring says UNRUN, no number in repo produced by it yet). Bar pre-registered above.
- 2026-09-09: POOL = run_refs.references() -> 20 clips, all with `_exact:true` human
  clicks + a `_audit` stamp carrying camera_height_m. Surfaces by data/incoming folder:
  Hardcourt 8, Clay 2, Shell 10 (= 5 shell RECORDINGS x2 points each: flexi_franz,
  flexi_joy, hillsborough, mpc_mixed, mpc_tuesday -> this is the "0 of 5" shell set).
  Heights <2.0m: 12 clips; >=2.0m: 8 clips. HoHxFSX_gLk_s1/s2 share a source.
- 2026-09-09: audit running (~10min+ for 12/20; 4K shell clips are slow). INTERIM
  best_err@640: A7vXlWIlyrI 5.3(reached x1), am_hard_utr 7.5(x8), CYqapSq5llo 5.2(x5),
  e8T34KoJzOw_s2 6.7(x3), flexi_franz_p01 8.8(x3), flexi_franz_p07 6.6(x2),
  flexi_joy_p01 40.8(x0), flexi_joy_p07 40.8(x0), hillsborough_p02 37.2(x0),
  hillsborough_p08 27.6(x0), HoHxFSX_gLk_s1 60.5(x0), HoHxFSX_gLk_s2 23.1(x0).
  => 6/12 so far reached. NOTE the near-misses: HoHxFSX_gLk_s2 23.1 and
  hillsborough_p08 27.6 sit just outside 20px; flexi_franz DOES reach truth on shell,
  which already contradicts a blanket "shell search never finds the court".
- 2026-09-09: AUDIT COMPLETE, 20/20 clips. HEADLINE: proposal recall 8/20 = 40%.
  Pre-registered bar said <=0.60 => **SEARCH BINDS**. Shell 2/10 clips = 1/5
  recordings (exactly ON my pre-registered <=1/5 shell line => borderline search-binds,
  said so). Mount height <2.0m 4/12=33.3% vs >=2.0m 4/8=50.0%, gap 16.7pp vs a
  pre-registered 40pp bar => mechanism NOT ESTABLISHED (and confounded: 8 of 12
  sub-2m clips are shell). Second half: truth_would_pass 9/20; blockers g>=.33 x11,
  struct x4, verify x4, suffic x3; selects_against_truth on 9 clips. Verdict: BOTH
  stages fail; search binds on 12 clips, accept rule refuses truth on 11.
- 2026-09-09: CAVEAT found in the instrument: truth_would_pass is a UNION over 8
  frames of any failing term, scored on the EXACT human clicks -> harsh; proven
  distorted because 5 of the 8 clips where a good lock WAS produced are marked
  "truth would not pass". Reported 9/20 as a FLOOR. Did not edit the script (not mine).
- 2026-09-09: DELIVERABLE WRITTEN: docs/evidence/candidate-proposal-recall.md with the
  headline for backend-dev at the very top. NO SendMessage tool exists in my toolset
  (2nd consecutive run a brief claimed it); used the file as the channel.
- 2026-09-09: CONFLICT: docs/STATE.md:196 (researcher) says it waits on "qa's SHELL
  proposal recall, which decides it" yet already declares DIAGNOSIS CONTRADICTED with
  "generated 7/10, reachable 31/38, recognised 9/10, lost at the vote". My shell
  number is 2/10 / 1/5 and points the OTHER way. Next: reconcile units by reading
  researcher's evidence file (read-only, not editing it).
- 2026-09-09: MAJOR RECONCILIATION, corrects my own draft.
  (a) candidate_audit.py docstring "UNRUN" is STALE: Session O ran it on SHELL on
      2026-08-24 -> data/output/court_scoring_diagnosis.md §10 + docs/evidence/
      indoor-shell-courts.md. Prior shell: 3/10 reached, 4 locks-no-truth, 3 no-lock.
      MINE: 2/10 reached, 5 locks-no-truth, 3 no-lock. Same direction, ONE CLIP LOWER
      -> report as drift/possible small regression; cannot name the clip from the
      archived summary (no per-clip table), and 2 within-frame margins flipped sign.
      Candidate cause worth someone's eye: 4a33635 scaled refiner reach 55 -> 55*w/640,
      validated as "no-op on the gate" -- but shell is 3840x2160 (6x) and is NOT in
      the gate pool, so a shell-only effect would be invisible to that validation.
  (b) MY 9/20 truth_would_pass IS THE WITHDRAWN-FIGURE ARTIFACT. §10 records the
      already-existing correct instrument: the neighbourhood sweep at a median 4.9 px
      from the clicks clears the 0.33 accept gate on **19 of 20** references (only
      UHf0LeMU2pg fails). So the criteria do NOT bind. RETRACT my "both stages are
      broken" framing -> SEARCH BINDS, cleanly, and this AGREES with Session O's
      "the search is decisively the bottleneck".
  (c) researcher's row is NOT in conflict: its own §3.4 pre-states the narrowing
      condition ("if shell proposal recall is near zero while pooled is 70%, the doc
      is right about shell") and says it could not obtain the number. My shell number
      TRIGGERS that condition. Also its pooled 7/10 is the 10 ORIGINAL calibrated
      clips (docs/evidence/court-detection-frames-that-each-find-the.md), a DIFFERENT
      population from my 20 -> 7/10 and my 8/20 are not the same quantity.
  (d) mpc_tuesday's two human labels disagree by 25.4 px (above the wrong-court line)
      -> not usable as truth; shell recall on the 4 trustworthy recordings = 1/4.
- 2026-09-09: DELIVERABLE FINALISED docs/evidence/candidate-proposal-recall.md (7 sections,
  headline for backend-dev at top, §4 retraction of my own "both stages broken" draft in
  place, §6 researcher reconciliation, decisions-for-lead list). Memory written:
  .claude/agent-memory/qa/court-proposal-recall-search-binds.md + MEMORY.md index line.
  Did NOT write docs/DECISIONS_PENDING.md (not on my allowlist) — decisions are in §5 of
  the evidence file and in my report instead.
## TASK STATE: COMPLETE. Nothing outstanding.
