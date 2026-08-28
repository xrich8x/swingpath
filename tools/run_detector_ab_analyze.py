"""run_detector_ab_analyze.py - the FULL pipeline, both detector arms, serially.

The ghost-ball half of the BallNet-vs-TrackNet chain A/B runs on ball-only
caches (tools/build_detector_ab_caches.py) because ghosts need no pose. The
other two product metrics do:

  event_audit      needs emitted hits/landings, which need players
  speed coverage   needs shots, which need players

so those need a real `run.py analyze`. ONE VARIABLE: --ball-model, forced
explicitly on both arms rather than left on `auto` (auto resolves to `ours` on
any calibrated clip, so leaving it would make the control arm unlabelled rather
than absent). Everything else is the shipped default: frame_step auto,
pose fast, pose_every 3, bgsub on, no far-player rescue, no far-ball tile.

ONE JOB AT A TIME - single GPU (same rule as tools/build_gold_caches.py).

    backend/.venv-train/Scripts/python.exe tools/run_detector_ab_analyze.py \
        --clips yt_rally2 gold_UHf0LeMU2pg
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from _goldset import GOLD  # noqa: E402

OUT = REPO / "data" / "output" / "detector_ab"
ARMS = {"ballnet21": "ours", "tracknet": "tracknet"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", nargs="+", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    py = REPO / "backend" / ".venv-train" / "Scripts" / "python.exe"
    log = OUT / "analyze.log"
    jobs = []
    for name in args.clips:
        c = GOLD[name]
        if not c.calib or not (REPO / c.calib).is_file():
            print(f"SKIP {name}: no calibration - speeds and calls need one")
            continue
        for arm, model in ARMS.items():
            out = OUT / f"{name}.{arm}.match.json"
            if out.is_file():
                print(f"have {out.name}")
                continue
            jobs.append((name, arm, model, c, out))

    print(f"{len(jobs)} analyze runs")
    for name, arm, *_ in jobs:
        print(f"   {name} {arm}")
    if args.dry_run or not jobs:
        return 0

    t0 = time.time()
    for i, (name, arm, model, c, out) in enumerate(jobs, 1):
        cmd = [str(py), str(REPO / "backend" / "run.py"), "analyze",
               str(REPO / c.video),
               "--keypoints", str(REPO / c.calib),
               "--out", str(out),
               "--ball-model", model,
               "--device", args.device]
        print(f"[{i}/{len(jobs)}] {name} {arm} ...", flush=True)
        started = time.time()
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(f"\n=== {name} {arm}\n" + " ".join(cmd) + "\n")
            lf.flush()
            rc = subprocess.call(cmd, cwd=str(REPO / "backend"), stdout=lf, stderr=lf)
        ok = rc == 0 and out.is_file()
        line = (f"[{i}/{len(jobs)}] {name} {arm}: "
                f"{'ok' if ok else f'FAILED rc={rc}'} in {(time.time()-started)/60:.1f} min")
        print(line, flush=True)
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(line + "\n")
    print(f"ALL DONE in {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
