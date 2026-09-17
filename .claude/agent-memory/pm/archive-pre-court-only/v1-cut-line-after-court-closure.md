---
name: v1-cut-line-after-court-closure
description: The v1 cut line set 2026-09-05 — manual calibration IS the setup story, court auto-detect and its 2,900-line port are cut, match scoring deferred, rally clips kept, speed-coverage parked not cut.
metadata:
  type: project
---

Set by pm 2026-09-05 in `docs/evidence/v1-resequenced-after-court-closure.md`, after court
auto-detection closed. Supersedes the court half of [[mobile-parity-first]].

**In v1:** manual 4-tap calibration with loupe; framing guidance **as a refusal, not advice**;
capture + import; TrackNet ball + pose + homography + smoother + shot detection; ball speed
labelled *average*; bounce map; per-rally clips + highlights; a resumable overnight batch job;
results UI.

**Cut, with what each buys back:**
- **Court auto-detection and the `courtfit.py`/`calibration.py` mobile port** (~2,900 lines,
  no conversion toolchain, was to become a C++/OpenCV core). Worth **~15–20 sessions** (parity
  priced 40–50 without court auto vs 55–70 with). Closed on *accuracy*: a successful port
  would not have beaten manual entry.
- **Line calls** (parked 2026-08-29 — geometry ceiling at both real mounts).
- **Match scoring** (see below). **BallNet Core ML conversion** (upgrade path).
  **Audio impact** (no compliant per-stroke reference; 0 of 88 clips usable).
  **Far-court recall labelling** (its consumer is parked).
  **The court mask sweep gate run** (orphaned — it tunes a detector v1 no longer ships).

**Two calls that will be re-proposed if not written down:**

1. **Auto-detection as a low-accuracy CONVENIENCE feature: NO.** A silently wrong court
   *inverts* numbers rather than degrading them — `yt_match40` passed a 0.9 px residual audit
   with all four corners on asphalt and a hedge, and cost two published figures. Four taps is
   not friction worth that.
2. **The speed-coverage lane is PARKED, not cut.** `seen_frac >= 0.5` is NONE ADMISSIBLE above
   a 27% coverage floor, and its replacement needs a real-footage absolute speed reference that
   does not exist (rule 11 bars the HUD). So chain work "to recover speed coverage" would move
   a statistic nobody can interpret. Unparks only when a compliant reference exists.

**Score layer SPLIT (rule 12 narrowed, not reopened):** rally *segmentation* stays — it ships,
its consumer is built, and a late boundary is a late clip, not a wrong fact. Match *scoring*
defers — one confident fact per match the user already knows, no ground truth, and its
consumers are not built (8–12 sessions from a screen even with labels). The ~3–6 h labelling
session stays on the founder queue with a **changed justification**: it is now the only way to
number **rally clip boundaries, a v1 feature currently unmeasured**.

**Pre-registered floors, written before the labels exist, and they do not move:** rally
boundaries ≥90% within **2.0 s** (below that the clip list ships but dead-time trimming does
not); match score ≥95% of games correct **plus a refusal path**, or ship no score at all.

**How to apply:** the capacity court vacated goes to (1) the phone, (2) the setup screen,
(3) **the refusal surface** — mount too low, speed not confident, ball lock refused all need
UI and none has any; it is now the largest un-owned area in v1. See
[[live-path-has-no-refusal-surface]] and [[v1-critical-path-is-founder-blocked]].

**Ranking rule this run validated:** rank founder asks by **leverage per minute on the
critical path, not by cheapness**. The §1 direct-line-click court falsifier is ~30–60 min and
ranks LAST, because its best case changes no v1 decision — the cut rests on manual calibration
already being the reference standard, not on the detector being unfixable.
