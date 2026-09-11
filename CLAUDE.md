# CLAUDE.md

Orientation for Claude Code. Read this file; read the others **only when the doc map sends you there.**

## What this is

A single-camera **tennis** analyzer for iPhone. **v1 is an ENGINE, not a feature list** — a metric
3D reconstruction of court and ball. In/out, landing position and speed are its *outputs*, and fall
out of it rather than being built separately.

**The three v1 capabilities** (founder brief 2026-09-11):

1. **3D spatial court mapping** — map the full court, *including lines the camera cannot see*, from
   visible markers plus the universal regulation dimensions. Known geometry substitutes for sight.
2. **3D trajectory & physics tracking** — the ball's continuous 3D arc from velocity, spin, launch
   angle and gravity, so the track survives loss of line-of-sight instead of breaking at it.
3. **Bounce point triangulation** — find the frame where the downward arc reverses, and intersect it
   with the ground plane to place a landing the camera never directly observed.

**Target: the call is INSTANT** — budget **one frame at 60 fps = 16.7 ms** end-to-end, emitted on the
bounce frame (`docs/SPEC.md` §8). Capture floor **60 fps and 1080p, both hard**: below 60 fps, refuse
to attempt bounce detection. Fence-mount or tripod only. **iPhone only, A13+, Neural Engine —
hardware acceleration is a v1 tool, not a v2 upgrade.** 100% on-device forever; a proposed network
dependency is a scope violation, not an optimisation. `schema.py` is the only backend/frontend contract.

**`docs/SPEC.md` is the LOCKED v1 target spec.** Every bar in it is pre-registered under rule 2 and
does not move to fit a result. The headline: **10 cm landing accuracy on ≥90% of near-line contested
calls**, bounce timing within **±1 frame 90% of the time**, and an **abstention** path — refusing a
call when 1σ uncertainty exceeds 10 cm is correct behaviour, not failure.

**The founding premise, unmeasured:** these work from one camera *regardless of mount height*. Every
height-dependent number here was measured on the 2D ground-projection estimator — the very method a
physics-anchored 3D fit replaces — so those numbers do not transfer. Monocular 3D is unevaluated.

## The one principle: learn what you can't compute, compute what you can

Every stage is one of three kinds. The boundary IS the architecture.

- **Perception (ML)** — court keypoints, ball detection
- **Geometry (math)** — homography, 6-DOF camera, ballistic fits, ground-plane intersection, line calls
- **Logic (rules)** — deterministic bookkeeping

Do NOT "ML-ify" geometry or logic. It adds error to exact answers.

## Scope — decided 2026-09-11, do not silently widen

| | What |
| --- | --- |
| **IN v1** | live 3D court mapping + drift recalibration · ball detection/tracking · drag+Magnus trajectory · bounce by vertical-velocity sign reversal · in/out incl. **doubles alley (required)** · abstention when 1σ > 10 cm |
| **DEFERRED to v2** — built or specced, out of scope | **ALL pose** (`pose.py`, the 187 MB YOLO weights, Apple Vision — SPEC §9 tossed) · **occlusion prediction and proxy spin** (SPEC §6 tossed) · `events.classify_shot` · shot **speed** as a shown number · spin RPM · stereo depth · handheld · let/net-cord · multi-ball |
| **CUT** — do not rebuild | match scoring, sets/games (`scoring.py`) · highlights + rally clips (`highlights.py`) · manual corrections (`corrections.py`) · the ONNX / React-Native port (`mobile/`) — wrong runtime |

**Deferred is not dead** — do not delete it, do not build on it. **v1 uses NO pose of any kind.**
`SPEC.md` §6 and §9 are struck through rather than deleted: their bars were reasoned, and the ±15%
fence in §9 is what stops body language becoming evidence. Restore them verbatim if they return.

**What v1 outputs, end to end:** where the ball bounced, whether it was in or out, and a REFUSAL when
it cannot tell. Nothing else. With §6 gone every occluded bounce is a refusal, so SPEC's ≤5% refusal
target is provisional — the honest rate may be far higher, and that is a finding, not a failure.

## Hard rules

1. **Never let a model grade its own homework.** Score only against independent human/gold labels.
   State in one sentence what every number was measured against.
2. **Pre-register the gate before running the experiment.** A failed gate stays failed.
3. **Check the CLOSED record before proposing anything.** Nine distinct ideas have been re-proposed
   at least once. See the doc map.
4. **Ball/court gold is TEST-only, one-way, enforced.** `assert_no_gold_leak`,
   `assert_no_court_gold_leak`, `assert_no_swingvision_leak`. Check each new model for its guard.
5. **Score ball work at the CHAIN, not the detector.** Four detector gains each cut detector error
   substantially and delivered nothing to the rendered output.
6. **Ball-DETECTOR work is closed** by the Session L stopping rule. Chain work is open.
7. **A single camera does not OBSERVE depth — it IMPOSES it.** 3D is recovered only by assuming a
   ballistic arc with known `g` and anchoring on the ground plane or known court dimensions. Every 3D
   number must name what pinned it. A reprojection residual does not certify an arc (a 23.8x span
   error passes), and a single amateur-mount arc's apparent-`g` fit is worth only ±15-25%.
8. **One variable per A/B, seeded.** `--seed` on both arms; `recipe_stamp` on every checkpoint.
9. **A refactor must prove it changed nothing.** Re-run and diff, or pin with a test.
10. **Never quietly edit human ground truth.** Mislabels get recorded, not fixed.
11. **Always inspect the rejects**, not what a filter kept.
12. **Truth comes from the GAME, not the VIDEO.** Court, ball, physics — never a scoreboard, HUD or
    burned-in graphic. That is somebody's data entry *about* the game: barred as training target,
    ground-truth reference AND tuning signal. A diligently-kept WRONG board is self-consistent, and
    nothing leaning on an overlay generalises to a phone clip. Compliant: human clicks,
    `tools/synth_truth.py`, geometry we derive. The one live exception, `tools/hud_ocr.py`, is
    **capped and being retired** — add no new ones.

## Known blockers

- **Monocular 3D has never been measured.** The bar now exists (10 cm, `SPEC.md` §3) and
  `tools/synth_truth.py` already generates known 3D trajectories, so the rig exists. **This is the
  first thing to do** — no design decision downstream is safe until there is a number.
- **Three gold sets in SPEC.md do not exist yet:** near-line contested calls (§7), bounce timing
  (§7), and the occlusion set (§6 cannot ship without it). Each needs human labelling.
- **No number has ever come from a phone.** The Core ML export ran green on Linux and the iOS latency
  harness compiled green, both 2026-09-10; the `.ipa` and `.mlpackage` exist as CI artifacts. The last
  mile is sideloading, blocked on Apple ID login on Windows (Sideloadly -22410). **Do not re-open that
  line without the founder.**
- **INSTANT is ~60x away on paper and unmeasured in fact.** 0.7-1.1 s/frame on CPU against a 16.7 ms
  budget. Nothing here has ever run on the ANE. Dropping §6/§9 leaves ball + court + physics only —
  exactly `live.py`'s design, which is v1's starting point.
- **Everything ball-related is blocked behind the indoor-shell court issue** (`SPEC.md` §10): ball
  targets do not apply until a working court model exists on that surface.
- **`run.py live` is broken out of the box** — it defaults to `weights/tracknet.pt`, deleted in the
  2026-09-11 weights cleanup along with `court_detector.pt` and `wasb_tennis_best.pth.tar`. All three
  are upstream downloads and re-obtainable; nothing in-house was lost.
- **Court auto-detection is closed for v1.** Manual four-corner setup is the product answer, not a
  fallback. Capability 1 above is the route back in, and it is a different mechanism.

## Commands

```bash
# Backend (Python 3.12). Windows: backend\.venv\Scripts\python.exe (CPU), .venv-train (CUDA).
python run.py demo --out ../frontend/src/data/sample_match.json   # synthetic, no weights
python run.py check <video> --keypoints pts.json                  # pre-flight: grade the mount
python run.py analyze <video> --keypoints pts.json --out out.json # full pipeline
python run.py live <video> --keypoints pts.json                   # streaming calls — v1's seed
python -m pytest tests/ && cd ../frontend && npm install && npm run dev
```

`run.py correct` and `run.py highlights` still exist and are **out of scope** — pending removal.
`tools/court_setup_server.py` is the manual calibration tool and is load-bearing. `tools/lab_server.py`
is the label/train workbench — deleting it leaves the product intact.

## Conventions

- `schema.py` is the single source of truth for `match.json`. Don't fork the format.
- Court constants: `backend/swingvision/court.py` -> `frontend/src/lib/court.js`; call-accuracy table
  -> `calls.js`. Both enforced by `tests/test_js_mirror_parity.py`.
- One module per pipeline stage; independently testable. Add a test for any new geometry or logic.
- Metres for all real-world measurement; km/h for speeds.
- Every pixel threshold scales by `frame_height/720` — except `static_radius_px` (measured).
- No new dependencies for what stdlib/numpy/scipy already do.

## Doc map — read the ONE that matches your task

| Task | Read |
| --- | --- |
| What v1 must hit, and what is deferred | **`docs/SPEC.md`** — the locked bars |
| About to propose a change | `docs/STATE.md` — the verdict tables, **first** |
| About to propose something that may already be dead | that pillar's `docs/<court\|ball\|measure\|data\|platform>/CLOSED.md` |
| A row looks wrong, or you need the mechanism | that row's file in `docs/evidence/` — one, not all |
| Any model work (create/train/tune/evaluate) | `ML_PRACTICES.md` — **required** |
| Diagnosing a model weakness | `ML_PLAYBOOK.md` §for that area |
| About to repeat a process mistake | `docs/TRAPS.md` |
| Running the tool | `README.md` / `USER_GUIDE.md` |
| Working ON a subsystem | `docs/modules.md` |
| Why is it like this | `docs/session_log.md`, `docs/archive/` — cold storage, not routine |

**`docs/STATE.md` is the only live record of state.** If another doc disagrees, that doc is wrong.
A STATE entry is **one line**: what changed, the number, the evidence path.

## Which doc moves with which change

| You changed | Update | Enforced by |
| --- | --- | --- |
| Any code | **`docs/STATE.md`** — the number it moved, or the negative and why | `.claude/hooks/state-guard.sh` (`[no-state]` opts out) |
| `run.py`'s argument parser | `README.md` / `USER_GUIDE.md` / `SETUP_PROMPT.md` | `.claude/hooks/docs-guard.sh` (`[no-docs]` opts out) |
| `court.py` constants or the call table | the JS mirrors | `test_js_mirror_parity.py` |
| A process mistake hit **twice** | `docs/TRAPS.md` — append a new ID, never renumber | judgement |
| This file | keep it under **150 non-blank lines** | `.claude/hooks/claude-md-cap.sh` |

## The team — `tennis-team`

Five teammates in `.claude/agents/`, memory in `.claude/agent-memory/<name>/`. **Announce a teammate
by name before invoking it** and label its output — never present its work as your own.

| Teammate | Owns | Writes code |
| --- | --- | --- |
| **pm** | Scope, sequencing, the cut line, accuracy floors | no |
| **researcher** | ML/CV for court and ball; on-device iOS inference | no |
| **backend-dev** | On-device logic: inference pipeline, 3D geometry, porting `backend/swingvision/` | yes |
| **frontend-dev** | The iPhone app: UI, camera capture, calling the pipeline, rendering results | yes |
| **qa** | Independent verification. Runs gates, reports numbers, **never fixes** | no |

**THREE LIVE AGENTS PROJECT-WIDE** — `.claude/hooks/agent-cap.sh` counts the whole tree, so a teammate
calling a teammate spends the same quota. **A refusal is PARKED, not lost.** The lead holds **one**
direct child at a time, one task per brief. A surprising RESULT goes to `researcher` first, then `pm`.

**A task needs a human when** only an eye can invalidate it, or it fires a stopping rule, is
irreversible, is a product decision, needs absent hardware, or would edit ground truth (rule 10).
**Batch paused tasks into ONE update.**

**`.claude/journals/` — one per agent plus `lead.md`, written DURING work, not after.** Read yours
FIRST on restart. **A KILL IS NOT A PAUSE — resume without asking.** Only the founder pauses, via
`lead.md`'s `RUN-STATE:`; they alone clear it, and a stale PAUSED line stops the next session too.
