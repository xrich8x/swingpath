"""Build any MISSING gold perception cache, sequentially, on the GPU.

WHY THIS EXISTS. Seven of the ten gold clips have no perception cache, so every
chain measurement in this project has been made on the three that do — 74
no-ball frames out of the 308 the gold set actually holds. That is what left the
`bounce_hypothesis` verdict resting on a denominator of two ghost frames
(docs/evidence/bounce-hypothesis.md). The caches are the fix, and they are
reusable: every future chain or detector A/B inherits the extra power.

ONE JOB AT A TIME is not a preference. There is a single RTX 5060 Ti; two
concurrent runs would OOM or halve each other and make every timing a lie — the
same rule tools/lab_jobs.py enforces.

SETTINGS ARE PINNED to the three existing caches so the ten are comparable
rather than a device-and-threshold confound (ML_PRACTICES: argmax can flip
near-threshold decisions between devices): --device cuda, --ball-model ours, the
shipped ballnet.pt, and score-thresh at its default. frame_step follows the
project's own rule — 2 above 45 fps so fps_eff lands near TrackNet's 30, else 1.

Paths come from tools/_goldset.py rather than being restated here. Three of the
seven do NOT follow the `gold_<name>.mp4` pattern (the registry knows; a
hand-written list did not), which is trap T17's shape: a check or a job keyed on
a guessed name breaks the moment the pipeline gains a renaming step.

  backend/.venv-train/Scripts/python.exe tools/build_gold_caches.py [--dry-run]
"""

from __future__ import annotations

import argparse
import glob
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from _goldset import GOLD  # noqa: E402

import cv2  # noqa: E402


def clips():
    return GOLD if isinstance(GOLD, (list, tuple)) else list(GOLD.values())


def resolve(video: str) -> Path | None:
    hits = glob.glob(str(REPO / "data" / "**" / Path(video).name), recursive=True)
    return Path(hits[0]) if hits else None


def probe(path: Path):
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return n, fps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    py = REPO / "backend" / ".venv-train" / "Scripts" / "python.exe"
    log = REPO / "data" / "output" / "goldcache_build.log"
    todo = []

    for c in clips():
        if glob.glob(str(REPO / "data" / "output" / f"{c.name}*.perception.json")):
            continue
        vid = resolve(c.video)
        if vid is None:
            print(f"SKIP {c.name}: video not found ({c.video})")
            continue
        n, fps = probe(vid)
        step = 2 if fps > 45 else 1
        todo.append((c.name, vid, step, n // step))

    total = sum(t[3] for t in todo)
    print(f"{len(todo)} caches to build, {total:,} frames to perceive")
    for name, vid, step, proc in todo:
        print(f"   {name:20} step={step}  {proc:>7,} frames  {vid.name}")
    if args.dry_run or not todo:
        return 0

    with open(log, "w", encoding="utf-8") as lf:
        lf.write(f"gold cache build, {len(todo)} clips, {total:,} frames\n")

    t0 = time.time()
    for i, (name, vid, step, proc) in enumerate(todo, 1):
        out = REPO / "data" / "output" / f"{name}.perception.json"
        print(f"[{i}/{len(todo)}] {name} ...", flush=True)
        cmd = [str(py), str(REPO / "tools" / "ball_perception.py"),
               "--video", str(vid), "--out", str(out),
               "--ball-model", "ours", "--device", args.device,
               "--frame-step", str(step)]
        started = time.time()
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(f"\n=== {name} step={step} frames={proc}\n")
            lf.flush()
            rc = subprocess.call(cmd, cwd=str(REPO / "backend"), stdout=lf, stderr=lf)
        dt = time.time() - started
        status = "ok" if rc == 0 and out.exists() else f"FAILED rc={rc}"
        line = f"[{i}/{len(todo)}] {name}: {status} in {dt/60:.1f} min"
        print(line, flush=True)
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(line + "\n")

    print(f"ALL DONE in {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
