# User Guide

A practical guide to running this tennis match analyzer and driving it forward
with Claude Code. Scope: tennis only.

## 1. What you have

Two halves that meet at one file, match.json:
- Backend (Python) — turns a tennis video into match.json: shots, speeds,
  bounces, line calls, rallies, and a running score.
- Frontend (React) — a dashboard that renders match.json: a top-down court with
  shot landings, stat tiles, shot-mix and line-call breakdowns, rally playback.

It runs two ways: on synthetic demo data with no AI models (instant, for trying
the dashboard), and on real footage through the full pipeline — court
auto-calibration, ball tracking (TrackNet/WASB), and player pose (YOLO-pose) are
all real and wired end to end (see §5). The forward plan lives in
[docs/sessions/](docs/sessions/).

## 2. Before you start

- Python 3.12+
- Node.js 18+ (20+ recommended) and npm
- git
- Later, for real footage: a phone/camera and a way to mount it behind the court.

Check: python --version  /  node --version

## 3. Setup (the easy way)

Open the folder in Claude Code and paste the prompt from SETUP_PROMPT.md. It
detects your OS, installs everything, runs the tests, and starts the dashboard.

## 3b. Setup (manual)

macOS / Linux:
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py demo --out ../frontend/src/data/sample_match.json
python -m pytest tests/
cd ../frontend
npm install
npm run dev                      # open the printed http://localhost:5173

Windows (PowerShell):
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py demo --out ..\frontend\src\data\sample_match.json
python -m pytest tests\
cd ..\frontend
npm install
npm run dev

If PowerShell blocks the activate script, run
Set-ExecutionPolicy -Scope Process RemoteSigned once, then retry.

## 4. Using the dashboard

- Broadcast view — empty state on demo data (no video). With a real analyzed
  clip it becomes the video + overlay.
- Court — top-down court. Nothing selected shows every shot landing (green = in,
  red = out). Click a rally to trail that point and scrub the ball.
- Statistics — shot count, rally count, average and top speed, shot mix, line-call split.
- Rallies — click any rally to focus it; click again to deselect.
- Load match (top right) — drop in any match.json you've produced.

Regenerate demo data anytime:
cd backend && python run.py demo --out ../frontend/src/data/sample_match.json

## 5. Analyzing real footage (this works now)

1. Record. Mount the camera behind a baseline, a little above the player, so both
   baselines and both alleys are visible. A FIXED camera is essential — if it
   pans/zooms, calibration breaks. A phone clamped to the back fence is fine; you
   do NOT need a TV angle. Player selection and the near/far split are computed in
   court metres from the calibration, so amateur angles work.
2. Install the ML deps once (CPU is fine; see backend/requirements-ml.txt):
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements-ml.txt
3. Calibrate. Click the court corners on the first frame:
   python calibrate.py match.mp4 --out my_court_pts.json --overlay check.png
   Open check.png — the drawn court lines should sit on the real lines. (A fixed
   camera means you calibrate once per clip.)
   Then audit it — a bad calibration breaks the overlay and ball gating with no
   error message, and some committed data/*_pts.json files are degenerate:
   python ../tools/validate_new_clip.py --audit my_court_pts.json
   The fit residual is the number that matters: under 2.5 px is good, over 10 px
   is unusable. Don't name your file court_pts.json — that one is a known-bad one.
3b. Check what your camera position is worth, BEFORE you spend an analysis run:
   python run.py check match.mp4 --keypoints my_court_pts.json
   It runs the same calibration `analyze` runs — so if it refuses here, analyze
   refuses too — and then tells you the one thing that decides whether the
   recording was worth making: what share of CLOSE line calls a mount at your
   height actually gets right. Read it against the floor it prints. Always
   answering "in" scores 56%, so a phone on a 1 m tripod (54%) is worth LESS
   than guessing; on a fence at 2.5 m it is ~68%, and at 6 m ~80%. Height is
   the biggest accuracy lever you control, and it is free.
4. Analyze. One command runs ball (TrackNet) + players (YOLO-pose), projects to
   court metres, and writes match.json:
   python run.py analyze match.mp4 --keypoints my_court_pts.json --out ../data/output/match.json
   It prints throughput (fps). Defaults are tuned for speed (~1 fps on CPU):
     --pose-quality fast|balanced|accurate   (accurate resolves a small far
        player on TV-style footage; fast is ~6x quicker and fine for most clips)
     --frame-step auto                        (auto targets ~30fps; halves work
        on 60fps phone clips)
     --full-rate                              (process EVERY frame. If you shot
        at 60fps this is the biggest accuracy gain available and it costs you
        twice the processing time: bounces land 24-35% closer to the truth, the
        ball's flight path fits more than twice as tightly, and speeds get
        noticeably nearer the radar figure. It does NOT find the ball more
        often — it measures what it finds more precisely. Nothing changes on
        30fps footage, so the flag is free to leave off there.)
     --max-frames N                           (analyze a segment, not the whole
        match — full matches are long on CPU)
   Re-runs reuse a cached perception file, so tuning the output is instant.
5. View. In the dashboard, click "Load match" (top right) and pick that
   match.json, or drop it at frontend/src/data/analyzed_match.json and use the
   "Analyzed clip" toggle.

Everything after perception — speed, line calls, scoring, stats — runs on the
real trajectories. Speed is average ball speed; bounce height is a single-camera
heuristic; vision scoring is best-effort (correct points by hand when it matters).

## 6. Driving it with Claude Code

1. claude from the repo root (it auto-reads CLAUDE.md).
2. First time on a fresh machine, paste SETUP_PROMPT.md → get it installed,
   tested, and running.
3. To build the next feature, open [docs/sessions/](docs/sessions/) and paste a
   session's kickoff prompt (e.g. `Do Session C (docs/sessions/SESSION_C_flow_polish.md)`).
   Each brief is self-contained — researched approach, step plan, and what you
   need to bring. The README in that folder lists them in the recommended order.

Keep these rules in front of the agent (they're in CLAUDE.md):
- Models go in the perception layer only.
- Never replace the geometry (homography, speed, line calls) or scoring with a
  model — it adds error to exact answers.
- match.json (schema.py) is the single source of truth for the data shape.
- Court constants in backend/.../court.py and frontend/src/lib/court.js must stay in sync.
- Before any model work, the agent must read ML_PRACTICES.md + ML_PLAYBOOK.md
  (CLAUDE.md requires it) — measure honestly, never let a model grade itself.

What's next, highest value first, is tracked in docs/sessions/: finishing the
camera story (lens + watchdog), serve analytics (done), flow polish + heatmaps,
auto-highlights, and the multi-session ball push (tracking → speed → spin).

## 7. Troubleshooting

- python: command not found → try python3; ensure Python 3.12+ on PATH.
- No module named pytest → activate the venv, then pip install -r requirements.txt.
- Dashboard blank / "failed to fetch" → regenerate sample_match.json (see §4).
- npm run dev fails on install → delete frontend/node_modules and re-run npm install on Node 18+.
- PowerShell won't activate venv → Set-ExecutionPolicy -Scope Process RemoteSigned, then retry.
- Court lines don't match the video → recalibrate; check the camera didn't move and all baselines/alleys are visible.

## 8. Project map

CLAUDE.md         agent context + doc map (auto-loaded by Claude Code)
README.md         architecture overview + quickstart
SETUP_PROMPT.md   paste-in prompt to install + run (fresh machine)
docs/sessions/    the forward plan — one researched brief per session
ML_PRACTICES.md   how to conduct ML work honestly (required before model work)
ML_PLAYBOOK.md    how to diagnose/technique the ML (required before model work)
HANDOFF.md        historical evidence log (paper trail, not current state)
backend/          Python: video -> match.json  (+ tests)
frontend/         React dashboard
data/             your videos and analysis output
