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

## Feature workflow — do not skip, do not auto-chain

**Announce every subagent by name before you invoke it**, say what you are asking it
for, and label its output with that name when you show me. Never run one silently, and
never present its work as your own. For any new feature or significant change:

1. **pm-agent** → spec. STOP. Show me and wait for my express approval.
2. **researcher-agent** with the approved spec, **in its own new chat session** — do
   not run it as a subagent burning the planning session's context. Hand it the
   approved spec and nothing else it would have to re-derive. STOP. Show me the
   findings and wait again, under the same approval rule.
3. Implement, **in its own new chat session**, handed the approved spec and the
   approved findings — using the test loop rules already in this file.
4. **qa-verifier** → independent check, **in its own new chat session**, separate from
   the implementation session. STOP. Show me its report. Do not mark the feature
   complete yourself, and do not let the coder's own claim of success stand in for
   this. On FAIL, fix and re-verify from this step — never skip re-verification.
5. Done only when qa-verifier reports PASS **and** I expressly approve that report.

**Why separate sessions:** each stage's context is the approved output of the one
before it, not the full history of how it was reached. Running all four in one session
accumulates tokens no later stage needs — the researcher does not need the PM
back-and-forth, the coder does not need the research dead ends, and QA should read the
diff fresh, not inherit the coder's framing of what it did.

**What counts as approval:** a clear, standalone "ok" / "okay" / "approved" / "go" /
"yes" / "sounds good" / "lgtm". Anything else — a question, a challenge, a request for
changes, an alternative to consider, or an approval that still raises one concern — is
NOT APPROVED. The whole thing waits: answer or revise, then stop and wait again. Never
infer approval from silence, from a topic change, or from me moving on to something
else. If you are unsure whether I approved, ask me directly rather than proceeding.
