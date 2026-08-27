# pm-agent memory

## Index

- [Parity before features](parity-before-features.md) — USER RULE: recreate the existing product on mobile first; do not let port-readiness drive product sequencing
- [iOS-only, and no desktop product](ios-only-no-desktop-product.md) — two rulings that reshape everything: Python is a lab; target is iOS/iPadOS A13+, Android companion-only
- [Sensor-assisted court](sensor-assisted-court.md) — IMU/intrinsics/ARKit collapse the search; REBUILD not port; blocked on a sensor gold set that does not exist
- [Score layer reopened, still no ground truth](score-layer-reopened-no-ground-truth.md) — 2026-08-20 closure superseded; stroke type is an unmeasured pose heuristic
- [Mobile plan](mobile-parity-first.md) — pose binds runtime, court binds sessions, ball is fine; order and session costs
- [Line-call numbers assume a perfect bounce detector](line-call-numbers-assume-perfect-bounce.md) — 95.9% and the 54/69/81% height curve are geometry ceilings, not end-to-end accuracy
- [The live path has no refusal surface](live-path-has-no-refusal-surface.md) — no confidence band, no false-lock suppression, no serve boxes; a serve long is called IN
- [SUPERSEDED: live-calls-first v1](mobile-v1-scope-live-calls.md) — rejected 2026-08-27; records why the non-causality argument was wrong

---

Backfilled 2026-08-27 by the main session from git history, `docs/STATE.md`,
`docs/TRAPS.md`, `docs/archive/sessions/` and `docs/archive/resolved/`. Everything here
is sourced; anything uncertain is marked so. This covers roughly 2026-06-20 → 2026-08-27,
all of which predates this agent existing.

---

## Product decisions already made

- **The rally / score layer is OUT OF SCOPE.** User ruling, 2026-08-20
  (`archive/resolved/rally-segmentation-score.md`). Not an open problem, not a backlog
  item. No work on point boundaries, rally segmentation, the `gap_s` override, or the
  second-bounce rule. `scoring.py` / `corrections.py` stay in place — the corrections
  replay depends on them, and `stats.score_validation_note` is what stops the UI
  presenting a scoreline as a measurement. **Do not re-scope this.**
- **Truth comes from the GAME, not the VIDEO.** User rule, established 2026-08-19 after
  a burned-in-scoreboard ground-truth tool was built and then rejected on its premise
  and reverted (`afffb5a`). A scoreboard/HUD is somebody's data entry *about* the game:
  barred as training target, ground-truth reference AND tuning signal. One flagged
  exception: `tools/hud_ocr.py` reads SwingVision's MPH panel, and those figures are
  *agreement with another estimator, not accuracy*. Add no new ones.
- **60 fps shipped opt-in as `--full-rate`**, not as default (decided 2026-08-15).
  Buys +5.8 pts close-call accuracy at 1.5 m and arc reproj 148 → 91 px, costs **2×
  perception time**. The cost is why it is opt-in.
- **Refusal is the designed fallback, not an error state.** Court auto-detection is
  fragile; the shipped answer for a clip it cannot read is the ~30-second manual court
  via the setup tool, plus camera guidance. This was chosen deliberately over accepting
  a low-confidence court.
- **Manual-correction UI ships and edits FACTS only** — score is replayed through the
  one state machine; re-applying a correction is a no-op.
- **Stats refuse rather than invent.** `distance_run_m` used to show a confident 0.0 m
  for a player the system never saw. It now returns None below a ≥50% coverage bar,
  never 0.0, and refuses outright in doubles.

## Constraints already established — treat as given, not as open questions

- **CPU-only shipped inference**, ~0.7–1.1 s/frame. Offline-first by design: record,
  then process. There is **no real-time requirement**. Training is one RTX 5060 Ti,
  **single GPU, one job at a time** (enforced by `lab_jobs.py`).
- **Geometry stays closed-form and is a hard architectural boundary.** Homography,
  projection, shot speed, line calls are never learned. Only perception may be ML.
- **The court precision gate: ≥12 of 20 gold clips accepted, AND zero accepted court
  more than 20 px from the human clicks** (`WRONG_PX_640 = 20.0`). Pre-registered, and
  it has not moved. **Any change that buys recall by admitting one wrong court is
  rejected** — two changes have already died on exactly that.
- **Target footage is amateur phone video**, fence or tripod, 720p–1080p, 30–60 fps,
  often a low mount. Measured mounts: **1.38 m** and **1.74 m**.
- **A low camera is a measured accuracy ceiling, not a style preference.** Close calls
  run 54.0% at 1.0 m → ~69% at 3 m → ~81% at 8 m against a **56.2% majority-class
  floor** — so a 1 m mount is *worse than answering "in" every time*. Quote that, never
  `reliable_court_span`, which is a geometric bound and reads far kinder.
- **Speed is average ball speed, ~15–20% under radar.** That is drag (−21.7%), confirmed
  against synthetic truth. Never "fix" it to match TV numbers.
- **Ball-DETECTOR work is closed** (Session L stopping rule). **Ball-CHAIN work is
  open** — and as of 2026-08-27 explicitly *not* closed: the stopping rule did not fire.
- **Score ball work at the CHAIN, not the detector.** Four separate detector gains
  (input resolution, `score_thresh`, localised weighting, +57% data) each cut detector
  error and delivered **nothing** to the rendered output. Four for four.
- **Don't fan out to parallel agents** (trap T07). One GPU, one gold set. Two multi-agent
  runs burned ~971k tokens for zero results.

## Previously proposed and rejected — with the reason

Product/scope-level rejections. The technical A/B negatives live in researcher-agent's
memory and in `docs/STATE.md` "What has not worked" (currently ~50 rows — check it before
proposing anything).

| Proposal | Why it was rejected |
|---|---|
| Burned-in scoreboard as ground truth for points/rallies | Built, then **rejected on the premise** and reverted. It is data entry, not the court. Do not rebuild. |
| Rally-segmentation / score accuracy work | Closed by user ruling 2026-08-20 as out of scope. That layer has **no ground truth of any kind**. |
| Improving CourtNet for auto-calibration | Wrong target — CourtNet is Tier 2 at 20.2% held-out detect; `courtfit` consensus is Tier 1 and beats it. |
| Widening the court seed grid for recall | Reaches courts the old grid could not and **gets every one of them wrong** (26 px, 78 px). Would have been the first wrong court ever accepted on the gold set. |
| Global mask replacement (CLAHE / Lab chroma) | Fixes clay, **breaks hard courts**. All three arms failed the gate. |
| A refuse-only player-plausibility gate as the shell fix | A gate can only remove candidates; it **cannot produce an acceptance**. Measured: converts zero clips, and its statistic's sign is backwards (it rewards a court for being large). |
| Making the accept rule "≥6 of surviving frames" | This is where the precision cost actually sits — it lowers the evidence bar. Must never ship in the same change as the gate feeding it. Moot on current evidence: nothing for it to convert. |
| Lowering the court consensus bar 6/8 → 5/8 | Gate fails — the one 5-vote clip is wrong by 68.7 px. |
| Fine-tuning the 14-keypoint CNN on hand-annotated shell frames | Not rejected, **deferred**: a real option at real cost (~300–600 labelled frames), explicitly not to start before the geometric tree is exhausted. |

## Open, waiting on a product call rather than on engineering

- **Far-court recall** needs ~4,087 human-labelled frames, **4–5 hours of clicking**.
  Automating the selection is a measured dead end. This is a "is it worth the human
  time" call, not a research question.
- **8 court gold frames are mislabelled.** A minute of human re-labelling. Deliberately
  *not* quietly edited (project rule 9).
- **Off-machine backup** — second disk verified 2026-08-17; off-machine still open.
- **Phone app shell** — app development, not ML. See the risk below.

## Known risks

- **The clay evidence is one club.** The three accepted clay clips share a house,
  windbreak and treeline. Read it as one venue family, not five venues. Clay from
  unrelated venues is the single thing that would move this from "works on one club" to
  "works on clay".
- **Shell is 0 of 5** and the target population is dim indoor, not the bright pale courts
  the earlier "shell already works" claim rested on. That claim is **withdrawn**.
- **Never quote a phone fps.** None has ever been measured.

- Known risk (flagged 2026-08-27): early codebase may have been built
  assuming a PC/desktop environment rather than on-device mobile.
  See audit findings for specifics. Every future feature spec must
  explicitly confirm mobile/on-device feasibility, not assume
  desktop-era architecture still applies.

  *Main-session note, 2026-08-27: the audit was run the same day and now exists —
  **`docs/evidence/mobile-viability-audit.md`**, with a row in `docs/STATE.md`. Read it
  before scoping any mobile feature. Its verdict: the port is **split**, not uniform —
  live line calls are a straightforward port and largely done, the offline analyzer is a
  significant rebuild (non-causal Kalman+RTS smoothing, whole-video passes, ~2,900 lines
  of classical CV with no conversion toolchain). The concern was directionally right but
  narrower than feared: no Windows paths, no GUI calls, and every OpenCV symbol used
  exists in the mobile builds. What the repo already corroborated before the audit:
  `docs/modules.md` records that the shipped stack is CPU-first Python/OpenCV, that
  int8 is **slower** than fp32 on x86 desktop (a quant-kernel pathology; the
  quantisation is for mobile CoreML/NNAPI), and that the app shell has **never been
  benchmarked on a real phone**. `docs/STATE.md` carries the same warning: "No phone fps
  has ever been measured, so do not quote one." The classical court CV is the harder
  port — it has no conversion toolchain and would become a shared C++ core.*
