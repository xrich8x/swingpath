# Setup Prompt

Paste this into Claude Code first to get the project installed, tested, and running.

---

You're setting up this SwingVision-clone repo (tennis only) on my machine.
Read CLAUDE.md and README.md first. Detect my operating system and use the
correct commands for it throughout.

Goal: get both halves installed, tested, and running, then tell me how to use
them. Go in order and STOP to show me the exact error and a fix if any step fails.

1. Prerequisites — check Python 3.12+, Node 18+ (20+ preferred), npm, and git
   are installed. If any is missing, tell me how to install it on my OS and stop.
   ON WINDOWS: test with `py --version`, not `python --version`. `python` is
   usually a Microsoft Store stub that prints "Python was not found" and installs
   nothing, so a check against `python` will wrongly report Python as missing.
   Use `py` for every command below, and once backend/.venv exists prefer calling
   its interpreter directly (`backend\.venv\Scripts\python.exe ...`) — that needs
   no activation and is what the rest of the repo's commands use.

2. Backend — create a virtual environment at backend/.venv, activate it, and
   install backend/requirements.txt. numpy/scipy/opencv are all the demo needs;
   ultralytics is only required later for real analysis, so don't worry if it's heavy.

3. Demo data — run: python run.py demo --out ../frontend/src/data/sample_match.json

4. Tests — run: python -m pytest tests/  and confirm the geometry and scoring
   tests pass.

5. Frontend — run npm install in frontend/, then npm run dev. Give me the local URL.

6. Verify — confirm the dashboard loads the demo match, the top-down court shows
   shot landings, and clicking a rally scrubs the ball through the point.

Constraints:
- Tennis only. Do not add any pickleball code, geometry, or scoring.
- Do not modify the geometry (homography, speed, line calls) or scoring code —
  it's already tested.
- Don't add dependencies beyond requirements.txt without asking.

When finished, give me a short summary: what's running, the dev URL, what's real
vs stubbed, and the one command to regenerate the demo data.
