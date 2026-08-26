"""Experiment 3a (docs/archive/HANDOFF.md §6 suspect 1): try to reproduce the archived
demo30 perception cache (968/1108 ball locks) by forcing the conditions it
was suspected to have been built under: camera hfov 70 deg (the pre-session
default, before focal self-calibration) and court-gate camera-height
threshold 4.0 m (the pre-session value, changed to 3.0 this session).

Source: yt_rally2.mp4 + the user's corner-drag calibration, same as the
canonical demo30 outputs (verified: demo30.json records yt_rally2.mp4;
2215 frames @ 60fps / frame_step 2 = 1108 processed, matching every cache).

Writes ONLY new demo30_exp_* filenames — the archived caches stay frozen.

Run from backend/ (CUDA venv for GPU, plain venv for the 3b CPU rerun):
    .venv-train\\Scripts\\python.exe exp_gate_regression.py tracknet cuda
    .venv-train\\Scripts\\python.exe exp_gate_regression.py fusion cuda
    .venv\\Scripts\\python.exe       exp_gate_regression.py tracknet cpu
"""

import json
import os
import sys

from swingvision import pipeline

VIDEO = os.path.join("..", "data", "yt_rally2.mp4")
PTS = os.path.join("..", "data", "yt_rally2_pts.json")


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else "tracknet"
    device = sys.argv[2] if len(sys.argv) > 2 else "cuda"
    out = os.path.join("..", "data", "output",
                       f"demo30_exp_{model}_{device}_hfov70_gate40.json")

    pipeline.COURT_GATE_MIN_CAM_H = 4.0  # force the pre-session threshold back

    pipeline.analyze_video(
        VIDEO,
        keypoints_path=PTS,
        out_path=out,
        pose_quality="accurate",   # matches archive + this session's fresh runs
        device=device,
        frame_step=2,              # 60fps -> 30fps, matches every demo30 cache
        camera_hfov_deg=70.0,      # force the pre-self-calibration default
        use_bgsub=True,
        ball_model=model,
    )

    cache = os.path.splitext(out)[0] + ".perception.json"
    with open(cache, "r", encoding="utf-8") as f:
        c = json.load(f)
    locks = sum(1 for p in c["ball_px"] if p)
    print(f"\n[experiment] {model}/{device} hfov=70 gate>=4.0m: "
          f"{locks}/{len(c['ball_px'])} ball locks "
          f"(archive=968, fresh tracknet cuda=781)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
