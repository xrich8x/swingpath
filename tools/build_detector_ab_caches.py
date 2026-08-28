"""Build the perception caches for the BallNet-v21-vs-TrackNet CHAIN A/B.

ONE VARIABLE. Both arms run tools/ball_perception.py with byte-identical
arguments except --ball-model, on the same 10 gold clips, at the same frame_step
(the project rule: 2 above 45 fps so fps_eff lands near TrackNet's 30, else 1),
same device, same score threshold, same bgsub, court gate OFF in the tracker.

Court gate OFF is deliberate and it is the same choice tools/build_gold_caches.py
made for the seven caches this reuses: the tracker's court gate is homography-
dependent, and two of the ten clips have a calibration that is known or suspected
wrong. The SHIPPED post-chain still applies gate_ball_to_court downstream where a
calibration exists (tools/chain_cache.run_chain), so the gate is measured - it is
just not allowed to change what the detector was even offered.

REUSE, not rebuild, where the provenance stamp already matches: the seven
gold_* caches were built by build_gold_caches.py under exactly these settings
(ballnet_v21.pt, cuda, score_thresh 0.5, court_gate False). Only the three
clips whose only 'ours' cache came from the full pipeline (different settings:
pose exclude boxes + tracker court gate) are rebuilt.

    backend/.venv-train/Scripts/python.exe tools/build_detector_ab_caches.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from _goldset import GOLD  # noqa: E402
import cv2  # noqa: E402

OUT = REPO / "data" / "output" / "detector_ab"
ARMS = {"ballnet21": "ours", "tracknet": "tracknet"}

#: 'ours' caches already built by build_gold_caches.py under identical settings.
#: Verified stamp: tool=ball_perception.py, ballnet_v21.pt, cuda, thresh 0.5,
#: court_gate False. Anything not listed here is rebuilt.
REUSE_OURS = {
    "gold_shell", "gold_clay", "gold_am",
    "gold_UHf0LeMU2pg", "gold_sAjkpeRq4P4", "gold_uR5q2cSM6AY", "gold_L73ep7JHiJ4",
}


def step_for(fps: float) -> int:
    return 2 if fps > 45 else 1


def probe(p: Path):
    cap = cv2.VideoCapture(str(p))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return n, fps


def cache_path(clip: str, arm: str) -> Path:
    return OUT / f"{clip}.{arm}.perception.json"


def plan():
    jobs = []
    for c in GOLD.values():
        vid = REPO / c.video
        if not vid.is_file():
            print(f"SKIP {c.name}: video missing")
            continue
        n, fps = probe(vid)
        st = step_for(fps)
        for arm, model in ARMS.items():
            if arm == "ballnet21" and c.name in REUSE_OURS:
                continue
            out = cache_path(c.name, arm)
            if out.is_file():
                continue
            jobs.append((c.name, arm, model, vid, st, n // st))
    # cheapest first: early signal, and the 29-minute clay clip last
    jobs.sort(key=lambda j: j[5])
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    jobs = plan()
    total = sum(j[5] for j in jobs)
    print(f"{len(jobs)} caches to build, {total:,} frames to perceive")
    for name, arm, model, vid, st, proc in jobs:
        print(f"   {name:<20} {arm:<10} step={st}  {proc:>7,} frames")
    if args.dry_run or not jobs:
        return 0

    py = REPO / "backend" / ".venv-train" / "Scripts" / "python.exe"
    log = OUT / "build.log"
    t0 = time.time()
    for i, (name, arm, model, vid, st, proc) in enumerate(jobs, 1):
        out = cache_path(name, arm)
        cmd = [str(py), str(REPO / "tools" / "ball_perception.py"),
               "--video", str(vid), "--out", str(out),
               "--ball-model", model, "--device", args.device,
               "--frame-step", str(st),
               "--tracknet-weights", "weights/tracknet.pt",
               "--ballnet-weights", "weights/ballnet_v21.pt"]
        print(f"[{i}/{len(jobs)}] {name} {arm} ({proc:,} frames) ...", flush=True)
        started = time.time()
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(f"\n=== {name} {arm} step={st} frames={proc}\n")
            lf.write(" ".join(cmd) + "\n")
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
