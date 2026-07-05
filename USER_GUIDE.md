# User Guide

A practical guide to running this tennis match analyzer and driving it forward
with Claude Code. Scope: tennis only.

## 1. What you have

Two halves that meet at one file, match.json:
- Backend (Python) — turns a tennis video into match.json: shots, speeds,
  bounces, line calls, rallies, and a running score.
- Frontend (React) — a dashboard that renders match.json: a top-down court with
  shot landings, stat tiles, shot-mix and line-call breakdowns, rally playback.

It runs today on synthetic demo data with no AI models. The parts that read real
video (court keypoints, player pose, ball tracking) are stubbed with the plug-in
points marked, so you add models when you're ready.

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
   python calibrate.py match.mp4 --out court_pts.json --overlay check.png
   Open check.png — the drawn court lines should sit on the real lines. (A fixed
   camera means you calibrate once per clip.)
4. Analyze. One command runs ball (TrackNet) + players (YOLO-pose), projects to
   court metres, and writes match.json:
   python run.py analyze match.mp4 --keypoints court_pts.json --out ../data/output/match.json
   It prints throughput (fps). Defaults are tuned for speed (~1 fps on CPU):
     --pose-quality fast|balanced|accurate   (accurate resolves a small far
        player on TV-style footage; fast is ~6x quicker and fine for most clips)
     --frame-step auto                        (auto targets ~30fps; halves work
        on 60fps phone clips)
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
2. Paste SETUP_PROMPT.md → get it running and verified.
3. Paste the Phase 1 block from PROMPT.md → first real feature (calibration + overlay).
4. Use the phase blocks in PROMPT.md for each next milestone.

Keep these rules in front of the agent (they're in CLAUDE.md):
- Models go in the perception layer only.
- Never replace the geometry (homography, speed, line calls) or scoring with a
  model — it adds error to exact answers.
- match.json (schema.py) is the single source of truth for the data shape.
- Court constants in backend/.../court.py and frontend/src/lib/court.js must stay in sync.
- One verifiable milestone per phase, with acceptance criteria. Run the tests after changes.

Good first features to ask for after Phase 1 (highest value first):
- A scoring-correction UI — confirm/fix points after a match. Closes the biggest
  real-world accuracy gap.
- A video export pipeline — trim dead time and render a highlights clip with the
  score/stats overlaid. The most-loved feature in this category.
- Movement & placement analytics — player-coverage heatmaps and shot-depth
  metrics from the pose data.

## 7. Troubleshooting

- python: command not found → try python3; ensure Python 3.12+ on PATH.
- No module named pytest → activate the venv, then pip install -r requirements.txt.
- Dashboard blank / "failed to fetch" → regenerate sample_match.json (see §4).
- npm run dev fails on install → delete frontend/node_modules and re-run npm install on Node 18+.
- PowerShell won't activate venv → Set-ExecutionPolicy -Scope Process RemoteSigned, then retry.
- Court lines don't match the video → recalibrate; check the camera didn't move and all baselines/alleys are visible.

## 8. Project map

CLAUDE.md         agent context (auto-loaded by Claude Code)
SETUP_PROMPT.md   paste-in prompt to install + run
PROMPT.md         paste-in prompts for each build phase
README.md         architecture overview
backend/          Python: video -> match.json  (+ tests)
frontend/         React dashboard
data/             your videos and analysis output
