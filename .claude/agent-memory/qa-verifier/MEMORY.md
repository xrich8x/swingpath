# qa-verifier memory

Backfilled 2026-08-27 by the main session from git history, `docs/STATE.md`,
`docs/TRAPS.md` and `docs/archive/sessions/`. Everything here is sourced; anything
uncertain is marked. Covers ~2026-06-20 → 2026-08-27, all of which predates this agent
existing.

You verify; you never fix, and you never move a bar to make something pass.

---

## The gates, as currently defined

**Court precision gate — pre-registered, and it has not moved:**

> **≥12 of 20 gold clips accepted, AND zero accepted court more than 20 px from the
> human clicks** (`WRONG_PX_640 = 20.0`).

- 20 px was drawn across an **empty band** in the data: accepted clips run 3.4–13.9 px,
  refused ones 25.5–111 px. That gap is why the number is defensible.
- **The precision half is absolute.** Any change that buys recall by admitting one wrong
  court is rejected, full stop. Two changes have already died on exactly this (seed-grid
  widening, global mask replacement). A 22.4 px pair was rejected even though both were
  visibly the *same court loosely fitted* rather than a different rectangle — **the line
  does not move after the fact.**
- Court-outline IoU was tested as a principled replacement and **does not separate**
  (0.782 near-miss vs 0.714 genuinely-wrong, against the pixel metric's 11.6 px gap).
- **Secondary, reported but NOT gating:** the 10 human-calibrated references, the
  independent drop set, and shell. Do not let a secondary number carry a verdict.

**Ball measurement baseline:** 1851 ball clicks + 308 no-ball frames across 10 clips,
test-only, never trained on.

**Ball chain gates are per-experiment and pre-registered** (P1…P7 style predicates, e.g.
`bounce_hypothesis` v2 adds **P7: `wrong` must not rise on any clip**). Read the
experiment's own evidence file for its predicates — do not assume a generic gate.

## Known problem areas — expect these to fail, and report the number

- **Indoor shell courts accept 0 of 5.** Five Philippine recordings (Manila Polo Club,
  Flexi League, Hillsborough; 4K, dim indoor). Why it's hard: **the cause is not the
  surface.** The masks visibly contain the court lines; what drowns them is the
  *building* — roof trusses, strip lights, fence lattice — at 395k–1,257k mask px and
  16–40 distinct lines whose strongest members are architecture. One clip locks 7 of 8
  frames while scoring **1 vote**, i.e. it finds a different court every frame. A better
  shell-specific mask cannot fix this.
- **Refusals carry no error**, so the shell set is precision-only. The gate can
  currently only prove a change *did not break* what already works there.
- **Shell is VERIFICATION ONLY.** No threshold, constant or gate may be chosen, swept or
  adjusted against the shell recordings. If a change was tuned on shell, that is a
  finding to report, not a detail.
- **Clay works on essentially one club.** The three accepted clay clips share a house,
  windbreak and treeline. Read clay results as one venue family.
- **8 court gold frames are mislabelled** and deliberately **not** quietly edited
  (project rule 9). A failure on those is expected; say so rather than counting it as a
  regression.
- **`mpc_tuesday` repeats at 25.4 px**, above the wrong-court line. Reported, not used
  as truth.
- **Far-court numbers on `am_hard_utr` are recall, never measurement** — it fits a 1.74 m
  camera and is measurable only to court-y 7.5 m of 23.77. Same shape for `demo30`
  (1.38 m, 5.2 m measurable): do not cite its speeds.

## Known defects to check for

- **Mobile and desktop run DIFFERENT ball models.** `mobile/models/*.onnx` are exported
  from `_tracknet.py`, while `docs/STATE.md` lists **BallNet v21** as the shipped
  default detector. Any mobile result is therefore *not* a measurement of the shipped
  detector, and any desktop result is *not* a prediction of mobile behaviour. Flag this
  whenever a number crosses that boundary. **Nuance, so you don't overstate it:** at the
  field's F1@4 threshold TrackNet wins 9 of 10 gold clips, so which model is "better"
  depends on the metric — report it as an unresolved divergence, not an automatic
  regression. Audit: `docs/evidence/mobile-viability-audit.md`.
- **"Real-time on-device" is UNVERIFIED, not confirmed.** **No phone benchmark exists
  anywhere in this repo.** Every mobile speed claim — including `MOBILE.md`'s
  "real-time on a modern device is the design target" — is an expectation from model
  size and structure, never a measurement. The standing project rule is *never quote a
  phone fps.* Whenever real-time on-device comes up in a QA pass, label it **unverified**
  and say what would settle it (a run on a real handset). Do not let a desktop ONNX
  timing stand in for it — on x86 the int8 build is *slower* than fp32 (a quant-kernel
  pathology), so desktop numbers actively mislead here.

## Scoring quirks and bugs in the verification logic itself

These are documented failures of the *checking* machinery, not of the product. When a
checker and the thing it checks disagree, **the checker is a suspect too**.

- **The search-free proxy does NOT predict the product gate.** `eval/score_truth.py` is
  a screening tool, **never a gate**. Three mask arms were indistinguishable on it
  (28/30) and spanned **6/20 to 13/20** on the real gate, because the proxy asks only
  whether the criteria *recognise* a court handed to them — not what the search finds,
  nor how four downstream stages react. A pass on the proxy is not a pass.
- **The `0.18–0.31` scoring artefact — WITHDRAWN 2026-08-24.** It claimed the accept
  gate rejects the correct court on 5 of 10 clips, and it had already gone out in an
  external research brief that ranked its recommendations on the strength of it. The
  defect: it scored the human's four clicked corners **exactly**, while the gate defines
  correct as anything within 20 px@640. A court a median **5.8 px** from the clicks
  clears the gate on **9 of 10** clips (`eval/truth_neighbourhood.py`). It was measuring
  our *labelling*, not the criteria. One clip survives as a genuine scoring failure:
  `UHf0LeMU2pg`. **Do not cite 0.18–0.31.**
- **`4.50:1` — WITHDRAWN 2026-08-27.** The `bounce_hypothesis` separation ratio, from a
  two-event denominator. Re-measured at full power over all 10 gold clips it is
  **9.00:1**, which passes the >7 bar. **Do not cite 4.50:1.**
- **`1.47x` / `1.6x` — WITHDRAWN.** Rally over-split figures read off a burned-in
  scoreboard, a premise the user rejected.
- **The withdrawn-figures table is machine-read.** `.claude/hooks/withdrawn-guard.sh`
  refuses any commit where a withdrawn string appears in a live doc without a withdrawal
  marker. Point-in-time records (`docs/archive/`, `docs/REVIEW-*`, `data/output/*`) are
  skipped on purpose — they are *supposed* to still contain the old number.
- **Underpowered gates read as null results (trap T09).** The solid-ghost gate was run
  **nine times** and never once alongside its own resolution: ~14 of **74** no-ball
  frames, where sampling alone moves the count by **±3.4**. Near-elimination is
  detectable (needs 62 frames); *halving* the ghost rate needs **212** and a 30% cut
  needs **656**. So nine nulls license only "nothing has come close to eliminating it",
  never "none of these did anything". **`tools/gate_verdict.py` prints the required-n
  next to the verdict — quote it.**
- **An audit that re-derives instead of invoking (trap T15).** `audit_new_clips.py`
  drove `auto_fit_frame`/`consensus` by hand and sampled 15–85% of a clip where the
  pipeline samples 2–98%; it reported 1 of 12 calibrating when the shipped path gets
  more. The same shape was live in the user-facing `run.py check` for a whole session.
  **Predict a behaviour by invoking it, never by re-deriving it.**
- **A resolution fallback that indicted good work (trap T16).** `validate_new_clip`
  looked for video only at `data/<tag>.mp4` and fell back to "assume 1280x720", so nine
  hand-placed 1080p calibrations audited as **DEGENERATE at 15.9–56.3 px**. At the true
  resolution they read 0.3–6.5 px. **The tell was that ALL of them failed** — almost
  never what a real quality problem looks like.
- **A scorer that mis-aligns frames (trap T04).** Gold frame `f` compared against track
  index `f//step` without checking `f` was processed understated the tracker for a whole
  session and forced a retraction.
- **Stale perception caches (trap T02).** Caches are calibration- and
  settings-dependent; a whole set of published figures was withdrawn over this. The
  provenance stamp exists to catch it — check it, and re-perceive if it mismatches.
- **`--frame-step 1` is not shipped behaviour (trap T01).** It doubles `fps_eff` and
  every time-threshold's frame count. Two wrong mechanism conclusions came from quoting
  it as shipped — the second *after* the rule was written down.
- **Population identity keys on the SOURCE VIDEO, never the clip name (traps T17, and
  the 2026-08-21 correction).** 9 of the 20 court gold clips share a source video with
  the 54-recording drop set, and `am_rally32short` **is** `yt_tnxkujogch4.mp4` renamed.
  Use `eval/recordings.py`. Two published figures were corrected by this. Related: the
  gold-leak guard matches on filename, so trimming a clip renames it and silently
  defeats the guard.
- **`truth_fails` in `candidate_audit` is a union across 8 frames** — "failed at least
  once", not a rate. Do not quote it as one.
- **Scoring on a population where the decision is easy (trap T08).** Pooled line-call
  agreement reads 87–99% across camera heights from 1 m to 12 m — it cannot tell a
  worthless mount from a good one. Restricted to bounces within 0.5 m of a line it reads
  54% → 81%. **Always state the majority-class floor**: on that population, answering
  "in" every time scores **56.2%**, so a 1 m camera's 54.0% is *worse than a constant*,
  not "slightly better than chance".
- **Judge a filter by what it REJECTED, not what it kept (trap T14).** Two versions of
  the play-segment finder each reported a plausible kept-percentage while discarding real
  tennis — one threw away ten minutes of rallies while reporting 58% kept.
- **A crop is evidence about a crop (trap T18).** Four locks reviewed from 140 px tiles
  were written up as "the clip cuts to commentary"; the full frames were ordinary wide
  tennis shots with a player walking past the near corner.

## Standing rules that bind your verdicts

- **Never let a model grade its own homework.** State in one sentence what every number
  was measured against. This applies to human graders too (trap T12): the far-court
  queue's human/tracker agreement rose 42% → 75% on the same twelve gaps because a
  labeller who cannot find the ball clicks the most ball-like thing in the frame — which
  is what the detector locked onto, for the same reasons.
- **A failed gate stays failed.** Pre-registered before the run, and it does not move to
  fit the result.
- **One declared measurement exception:** figures quoting a *HUD MAE* or *HUD speed
  error* are measured against SwingVision's burned-in MPH panel and are **agreement with
  another estimator, not accuracy**. They must be labelled that way. `tools/synth_truth.py`
  is the only source of absolute accuracy here.
- **Speed is average ball speed, ~15–20% under radar** — that is drag (−21.7%), not a
  bug. Never flag it as one.
- **Bounce height is a single-camera heuristic.** Known open task, not a defect.
- **A refactor must prove it changed nothing** — re-run and diff, or pin with a test. An
  exact no-op is a legitimate, reportable result (the court refiner's resolution scaling
  shipped as 12/20 → 12/20, a correctness fix that moved no number).
