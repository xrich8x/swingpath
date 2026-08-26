# SwingVision Clone

A single-camera tennis match analyzer, built as a learning project. Point a
camera at a court, record a match, and the pipeline turns the video into a
match.json of shots, speeds, bounces, line calls and a running score. A React
dashboard renders it: a top-down court with shot landings, per-shot stats, and
rally-by-rally playback.

Offline-first by design — you record, then process. That avoids the hardest part
of the real SwingVision (real-time on-device inference) while keeping everything
that makes it useful.

## Architecture: three kinds of work

You learn what you can't compute, and compute what you can.
- Perception (ML): court keypoints, player pose, ball tracking, shot type —
  learned models, inference from messy pixels
- Geometry (math): homography, ball->court projection, shot speed, line calls —
  exact closed-form math; ML here only adds error
- Logic (rules): scoring, rally segmentation, highlights — deterministic state machines

The seam between backend and frontend is match.json (backend/swingvision/schema.py).
Either side can change freely as long as that contract holds.

video -> calibrate -> perceive -> detect events -> measure -> score -> match.json -> dashboard
         (geometry)   (ML)        (geometry)        (geometry)  (logic)

## Quickstart (synthetic data, no model weights)

**Full instructions, including Windows, are in [USER_GUIDE.md](USER_GUIDE.md) §3.**
This is the short version.

macOS / Linux:

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py demo --out ../frontend/src/data/sample_match.json
cd ../frontend && npm install && npm run dev

Windows (PowerShell) — use `py`, not `python`:

cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py run.py demo --out ..\frontend\src\data\sample_match.json
cd ..\frontend; npm install; npm run dev

> **On Windows `python` is usually a Microsoft Store stub** that prints "Python was
> not found" and installs nothing. Use `py` to create the venv. Afterwards the most
> reliable way to run anything is the venv's interpreter directly —
> `backend\.venv\Scripts\python.exe run.py ...` — which is what every command in
> CLAUDE.md and the tools uses, and it needs no activation.

## Analyzing a real clip (the real pipeline is wired end to end)

> Commands below are written `python ...`. **On Windows use `py`**, or call the venv
> interpreter directly (`backend\.venv\Scripts\python.exe ...`) — see the Quickstart note.

Install the ML deps once (see backend/requirements-ml.txt — CPU torch is fine):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-ml.txt

Then:
1. Calibrate — click the court corners with calibrate.py and pass --keypoints
   (reliable on any angle), or rely on auto-detect. overlay.py draws the court
   back on the frame so you can confirm it's right.
2. Analyze — one command runs ball (TrackNet) + players (YOLO-pose), projects to
   court metres, and writes match.json:
python run.py analyze match.mp4 --keypoints my_court_pts.json --out ../data/output/match.json

   On 60 fps footage add `--full-rate` to process every frame: bounces land 24-35%
   closer to truth and the flight fits more than twice as tightly, at 2x the
   processing time. It is a no-op on 30 fps clips.

   Audit any calibration before you trust it — some committed `data/*_pts.json` are
   degenerate and break the overlay + ball gating silently:
   `python ../tools/validate_new_clip.py --audit my_court_pts.json` (good is < 2.5 px).
2b. Pre-flight — before spending an analysis run, find out what the camera position
   is worth:
python run.py check match.mp4 --keypoints my_court_pts.json

   It runs the SAME calibration `analyze` runs (so a refusal here is a refusal
   there) and prints the measured share of CLOSE line calls a mount at that height
   gets right, beside the floor that answering "in" every time scores (56%). A 1 m
   tripod reads 54% — worse than guessing; a fence at 2.5 m ~68%. Height is the
   largest accuracy lever available and it is free.
3. View — load that match.json in the dashboard (Load match, top right).
4. Cut the rallies (optional) — every point becomes its own playable clip, plus a
   top-3 reel, so the dead time between points disappears:
python run.py highlights match.mp4 --match ../data/output/match.json --out-dir ../frontend/public/rallies --reel

   Cutting is a stream copy, so it is I/O-bound rather than a re-encode. Clips get
   2 s of lead-in because a rally starts at the first CONTACT — without it every
   clip opens mid-swing. Drop them in frontend/public/rallies/ and the Rallies tab
   grows a Play button per point.

Camera placement matters more than the models (a fixed camera + good calibration
dominate accuracy). Mount it behind a baseline, a little above the player, so both
baselines and both alleys are visible and it does NOT move during the point.
Player selection and the near/far split are derived from the homography in court
metres, so amateur angles (a phone on a fence) work, not just a TV camera.

Note: speed is average ball speed; single-camera bounce/height is a heuristic.

## Layout

backend/swingvision/
  court.py         court constants + landmarks (geometry)
  calibration.py   classical court detection (ML seam) + homography solve (geometry)
  overlay.py       draw the court line set back onto frames (calibration proof)
  pose.py          player pose — real (YOLO-pose)
  ball.py          ball tracking — real (TrackNet/WASB) + trajectory smoothing (physics)
  courtfit.py      line-fit court auto-calibration + physical shape lock + watchdog
  events.py        hits, bounces, rallies, shot type
  analytics.py     shot speed + line calls (geometry)
  scoring.py       tennis scoring state machine (logic)
  corrections.py   apply human corrections, then re-derive score + stats (logic)
  highlights.py    rank rallies + cut per-rally clips and a reel (logic)
  pipeline.py      orchestrator + synthetic demo + calibrate_video
  schema.py        the match.json contract
backend/run.py       CLI: demo | analyze | check | live | correct | highlights
backend/calibrate.py manual click-to-calibrate tool
backend/tests/       geometry + scoring + detection tests
frontend/src/        components, lib/court.js, data/sample_match.json
tools/               dev + ML tooling, not part of the analyzer. Notably:
  lab_server.py        the Lab — add a clip, label it, train, score, in a browser
                       (`py tools/lab_server.py`); enforces gold/train separation
  court_setup_server.py  place the court corners on a clip (browser)
  validate_new_clip.py   audit a calibration; --stamp records the verdict in it

## Tests

cd backend && python -m pytest tests/

## Build order

1. Calibration + court overlay — validates the geometry foundation.
2. Ball tracking — the riskiest piece; de-risk early.
3. Pose + hit detection — forehand/backhand classification.
4. Analytics — speed, bounces, line calls (mostly done).
5. Scoring + dashboard polish + a manual-correction UI (all done).
6. Per-rally clips and a highlights reel (done).
7. (Stretch) real-time / mobile.

## Honest limitations

- Ball tracking through motion blur and occlusion is the make-or-break part;
  expect trajectory gaps you interpolate.
- Speed is average ball speed and reads ~15-20% under a radar gun.
- Bounce detection from a single camera has no true height, so it's a court-speed
  heuristic — a second camera or a learned bounce model improves it.
- Scoring from vision alone is brittle (the real app gets points wrong too) —
  which is structural, not a bug to fix with a better detector. The answer is the
  Review tab: overrule a winner, call or stroke, and the score and stats are
  replayed from the corrected facts by the same code the pipeline uses.

Accuracy is bounded by calibration quality and a fixed camera far more than by
any single model choice.

## Docs

- **CLAUDE.md** — architecture, hard rules, current status (start here to work on it).
- **[docs/STATE.md](docs/STATE.md)** — the stack, the method, and what has and hasn't
  worked, in flat lists. Kept live; updated alongside the work.
- **[docs/STATE.md](docs/STATE.md)** — the current state of play: what is shipped, what is open,
  and what has been measured and ruled out.
- **ML_PRACTICES.md** / **ML_PLAYBOOK.md** — required reading before any model work
  (discipline + technique). **docs/archive/HANDOFF.md** — historical evidence log.
- **USER_GUIDE.md** — running it and driving it with Claude Code, in plain language.
