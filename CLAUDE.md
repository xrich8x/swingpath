# CLAUDE.md

Orientation for Claude Code. Read this file; read the others **only when the table
below sends you there.**

<!-- MAINTAINER NOTE: auto-loaded every session; every line costs context on every
     turn. Hard cap: 150 lines. Findings, numbers and session entries do NOT go here
     — see the doc map. Block HTML comments are stripped before this reaches context. -->

## What this is

A single-camera **tennis** match analyzer. Backend turns a video into `match.json`
(shots, speeds, bounces, line calls, score); a React frontend renders it.
**Offline-first**: record, then process. No real-time requirement. `schema.py` is the
only contract between the halves — either side may change freely as long as it holds.

## The one principle: learn what you can't compute, compute what you can

Every stage is one of three kinds. The boundary IS the architecture.

- **Perception (ML)** — court keypoints, player pose, ball tracking, shot type
- **Geometry (math)** — homography, projection, shot speed, line calls. Closed-form.
- **Logic (rules)** — scoring, rally segmentation, highlights. Deterministic.

Do NOT "ML-ify" geometry or logic. It adds error to exact answers.

## Doc map — read the ONE that matches your task

| Task | Read | Do not read |
| --- | --- | --- |
| Anything at all | this file | — |
| About to propose a change | `docs/STATE.md` **first** — the verdict table | evidence files |
| A row in STATE looks wrong or you need the detail | that row's evidence file | all of them |
| Any model work (create/train/tune/evaluate) | `ML_PRACTICES.md` — **required** | PLAYBOOK unless diagnosing |
| Diagnosing a model weakness | `ML_PLAYBOOK.md` §for that area | other §s |
| About to repeat a process mistake | `docs/TRAPS.md` | — |
| Running or driving the tool | `README.md` / `USER_GUIDE.md` | — |
| Working ON a subsystem (live calls, the Lab, mobile, CPU perf) | `docs/modules.md` | unless you are in that code |
| Historical context, "why is it like this" | `docs/session_log.md`, `docs/archive/` | routinely — these are cold storage |

**`docs/STATE.md` is the only live record of state.** If another doc disagrees with
it, that doc is wrong. This file is orientation, not status.

## Hard rules

1. **Never let a model grade its own homework.** Score only against independent
   human/gold labels. State in one sentence what every number was measured against.
2. **Pre-register the gate before running the experiment.** A failed gate stays
   failed; do not move the bar to fit the result.
3. **Check `docs/STATE.md` "What has not worked" before proposing anything.** Nine
   distinct ideas in there were re-proposed at least once.
4. **Ball/court gold is TEST-only, one-way, enforced.** `assert_no_gold_leak`,
   `assert_no_court_gold_leak`, `assert_no_swingvision_leak`. A discipline enforced
   on one model is not enforced on the project — check each new model for its guard.
5. **Score ball work at the CHAIN, not the detector.** Four detector gains (input
   resolution, `score_thresh`, localised weighting, +57% data) each cut detector
   error substantially and delivered nothing to the rendered output. Justify the
   next ball idea by a chain-level mechanism or do not run it.
6. **Ball-DETECTOR work is closed** by the Session L stopping rule. Chain work is open.
7. **One variable per A/B, seeded.** `--seed` on both arms; `recipe_stamp` on every
   checkpoint.
8. **A refactor must prove it changed nothing.** Re-run and diff, or pin with a test.
9. **Never quietly edit human ground truth.** Mislabels get recorded, not fixed.
10. **Always inspect the rejects**, not what a filter kept.
11. **Truth comes from the GAME, not the VIDEO.** Court, ball, players, bounces,
    physics — never a scoreboard, HUD or graphic burned into the frame. That is
    somebody's data entry *about* the game: barred as a training target, a
    ground-truth reference AND a tuning signal. Independence is not truth — a
    diligently-kept WRONG board is perfectly self-consistent, and nothing leaning on
    an overlay generalises to the user's own phone clip. Compliant references: human
    clicks, `tools/synth_truth.py`, geometry we derive. **One live exception, flagged
    not hidden:** `tools/hud_ocr.py` reads SwingVision's MPH panel — a "HUD MAE" is
    *agreement with another estimator, not accuracy*. Label it so; add no new ones.
12. **The rally / score layer is BACK IN SCOPE** — user ruling 2026-08-27, superseding
    the 2026-08-20 ruling that closed it. The product needs match scoring (sets,
    games), point-by-point clip segmentation and dead-time trimming. **Reopening
    scope does not create ground truth.** That layer still has none, and rule 11 bars
    the easy source — a burned-in scoreboard stays barred. A compliant source (human
    -labelled point boundaries, or boundaries derived from bounces and physics) is a
    prerequisite for any number here, not a detail. `stats.score_validation_note`
    stays until a measured number replaces it.

## Commands

```bash
# Backend (Python 3.12). On Windows use `py`, or backend\.venv\Scripts\python.exe
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py demo --out ../frontend/src/data/sample_match.json   # synthetic, no weights
python run.py check <video> --keypoints pts.json                  # pre-flight: grade the mount
python run.py analyze <video> --keypoints pts.json --out out.json # full pipeline
python -m pytest tests/
cd ../frontend && npm install && npm run dev
```

`run.py`: `demo | analyze | check | live | correct | highlights`.
`tools/lab_server.py` is the Lab (label/train/score in a browser). Not part of the
analyzer — it never imports `swingvision` and deleting it leaves the product intact.

## Conventions

- `schema.py` is the single source of truth for `match.json`. Don't fork the format.
- Court constants: `backend/swingvision/court.py` → `frontend/src/lib/court.js`;
  call-accuracy table → `calls.js`. Both enforced by `tests/test_js_mirror_parity.py`.
- One module per pipeline stage; independently testable.
- Metres for all real-world measurement; km/h for speeds.
- Every pixel threshold scales by `frame_height/720` — except `static_radius_px`,
  which measurement says should not.
- Add a test for any new geometry or logic.
- No new dependencies for what stdlib/numpy/scipy already do.

## Which doc moves with which change

| You changed | Update | Enforced by |
| --- | --- | --- |
| Any code (`backend/`, `tools/`, `frontend/src/`, `mobile/`, `ball_physics/`) | **`docs/STATE.md`** — the number it moved, or the negative and why | `.claude/hooks/state-guard.sh` (`[no-state]` opts out) |
| `run.py`'s argument parser | `README.md` / `USER_GUIDE.md` / `SETUP_PROMPT.md` — whichever now lies | `.claude/hooks/docs-guard.sh` (`[no-docs]` opts out) |
| `schema.py` | `README.md` layout note + the frontend that reads it | judgement |
| `court.py` constants or `calibration.py`'s call table | the JS mirrors | `test_js_mirror_parity.py` |
| A model, weight file, or runtime | `docs/STATE.md` "The stack" | judgement |
| A process mistake hit **twice** | `docs/TRAPS.md` — **append a new ID, never renumber** | judgement |

A STATE entry is **one line**: what changed, the number, the evidence path. Prose goes
in the evidence file — if your row needs a paragraph, you are writing in the wrong file.

## Gotchas that bite every session

- **Speed is average ball speed**, ~15–20% under radar. That is drag (−21.7%),
  confirmed against synthetic truth. Never "fix" it to match TV.
- **A low mount is not a style choice, it is measured accuracy.** Close calls:
  54.0% at 1.0 m, ~69% at 3 m, ~81% at 8 m, against a **56.2% majority-class
  floor** — so 1 m is worse than answering "in" every time. Quote that, not
  `reliable_court_span`, which is a geometric bound and reads far kinder.
- **Audit every calibration before trusting it.** Some committed `data/*_pts.json` are
  degenerate and silently break the overlay + ball gating. `tools/validate_new_clip.py
  --audit <files>` — good is < 2.5 px fit residual. Known-good/bad: `docs/calibration.md`.
- **`am_hard_utr` (primary 1080p gold) fits a 1.74 m camera** and is measurable
  only to court-y 7.5 m of 23.77. It does not reach the net. Any far-court number
  on that clip is detection recall, NOT a measurement.
- **`demo30` is 0.5 px but low (1.38 m)** — measures 5.2 m of 23.77. Never cite its speeds.
- **Bounce height is a single-camera heuristic.** Known open task, not a bug.
- **Don't fan out to parallel agents.** The bottleneck is one GPU and one gold set.
  Two multi-agent runs burned ~971k tokens for zero results.

## The team — `tennis-team`

Five teammates in `.claude/agents/`, all on opus, each with memory in
`.claude/agent-memory/<name>/`. **Announce a teammate by name before invoking it** and
label its output with that name — never present its work as your own.

| Teammate | Owns | Writes code |
| --- | --- | --- |
| **pm** | Scope and sequencing across the team; the cut line; accuracy floors | no |
| **researcher** | ML/CV for court, player, ball and shot detection; on-device iOS inference | no |
| **backend-dev** | On-device logic: inference pipeline, the four detections, match storage, porting `backend/swingvision/` | yes |
| **frontend-dev** | The iPhone app: UI/UX, camera capture, calling the pipeline, rendering results | yes |
| **qa** | Independent verification of both layers. Runs gates, reports numbers, **never fixes** | no |

**They coordinate and move independently — no approval gate between phases.** pm sequences
the work; it does not have to sign off each step. qa reports; it does not block by fiat.

**Two constraints bind every teammate.** **iOS/iPadOS only, A13+** (iPhone 11, SE 2nd gen,
2020 iPad Pro and up), Core ML/ANE the only inference target — settled, not reopened. And
**100% on-device, forever**: no server, no cloud, no API fallback. A proposed network
dependency is a scope violation, not an optimisation.

**Folder boundary.** Every teammate works only inside this project folder — never reads,
writes or navigates outside it, never installs anything globally, never touches system or
account settings. `tools:` in each agent file is what actually enforces this: pm,
researcher and qa have no write access, and only backend-dev and frontend-dev can edit.
