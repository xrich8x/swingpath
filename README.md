# Swing Vision — automatic, live 3D court mapping (iPhone, on-device)

**This repository is currently working on ONE feature: the court.** From a single fixed iPhone camera,
the app finds a tennis court automatically, places every line (doubles alley included) as a 3D court
with a solved camera, infers lines that are out of view from the regulation dimensions, and keeps
tracking the court when the phone moves. Everything runs on the phone.

Everything else this repo once did — ball tracking, line calls, physics, players, scoring, highlights —
is archived in `docs/archive/2026-09-17-pre-court-only/` (the old README is there too).

## Where to start

- `CLAUDE.md` — orientation and rules.
- `docs/SPEC.md` — what the court feature must do.
- `docs/STATE.md` — what has been measured so far.

## Court tools

```bash
# Windows: backend\.venv\Scripts\python.exe
python tools/court_setup_server.py --video clip.mp4            # court overlay setup tool
python run.py check <video> --keypoints pts.json               # grade a mount / calibration (from backend/)
python ../tools/court_map_ceiling.py --n 400 --seed 0          # C1 court-model test (from backend/)
python -m pytest tests/                                        # from backend/
```
