"""eval_model_filters.py — measure a ball model THROUGH the full shipped post-
chain (tracker gates -> remove_outliers -> rectify -> suppress_false_locks ->
live-ball filter) on the yt_rally2 gold labels. Isolates how much detector
precision (baseline vs a hard-negative model) buys once the deterministic
false-lock suppressors are in place. GPU: one tracker pass per model.

  cd backend && .venv-train/Scripts/python.exe ../tools/eval_model_filters.py \
      --device cuda --weights weights/ballnet.pt weights/ballnet_v21.pt
"""
from __future__ import annotations
import argparse, json, math, os, sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import cv2
import numpy as np

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
# clip -> (video, court-pts json, gold labels json)
CLIPS = {
    "yt_rally2": ("data/yt_rally2.mp4", "data/yt_rally2_pts.json",
                  "data/gold/yt_rally2.labels.json"),
    "yt_match40": ("data/yt_match40.mp4", "data/yt_match40_pts.json",
                   "data/gold/yt_match40.labels.json"),
}


def build_calib(pts_path):
    from swingvision import calibration, court
    kp = json.load(open(REPO / pts_path))
    return calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                          [kp[n] for n in CORN])


def gold(labels_path):
    g = {int(k): v for k, v in json.load(open(REPO/labels_path))["labels"].items()}
    ball = {f: v for f, v in g.items() if v.get("ball") and not v.get("unsure")}
    noball = [f for f, v in g.items() if v.get("ball") is False and not v.get("unsure")]
    return ball, noball


def perceive(video, weights, device, H, cam_xyz, W, Hh, fps_eff, step):
    os.environ["BALLNET_WEIGHTS"] = weights
    from swingvision.ball import OurBallDetector, BallTracker
    det = OurBallDetector(device=device)
    tracker = BallTracker([det], (W, Hh), use_bgsub=False, homography=H,
                          fps=fps_eff, cam_xyz=cam_xyz)
    cap = cv2.VideoCapture(str(video))
    ball_px = []
    idx = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            ball_px.append(tracker.update(frame))
        idx += 1
    cap.release()
    print(f"  perceived {len(ball_px)} frames in {time.time()-t0:.0f}s", flush=True)
    return ball_px


def measure(tr, ball, noball, step, tag):
    fires = [f for f in noball if (f//step) < len(tr) and tr[f//step] is not None]
    hit = fh = ft = 0
    for f, v in ball.items():
        pf = f//step; p = tr[pf] if pf < len(tr) else None
        ok = p is not None and math.dist(p, (v["x"], v["y"])) <= 10.0
        hit += ok
        if v["y"] < 260.0:
            ft += 1; fh += ok
    print(f"    {tag:<34}{100*len(fires)/len(noball):>7.1f}%{100*hit/len(ball):>9.1f}%"
          f"{100*fh/max(ft,1):>10.1f}%   fires={len(fires)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", nargs="+", required=True)
    ap.add_argument("--clip", default="yt_rally2", choices=list(CLIPS))
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    from swingvision import calibration, ball as B
    video_rel, pts_rel, labels_rel = CLIPS[args.clip]
    video = REPO / video_rel
    H = build_calib(pts_rel)
    cap = cv2.VideoCapture(str(video))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0; cap.release()
    step = max(1, round(src_fps / 30.0))
    fps_eff = src_fps / step
    cam_xyz = calibration.camera_position_m(H, (W, Hh), 70.0)
    ballg, noball = gold(labels_rel)
    print(f"{args.clip} {W}x{Hh} @ {src_fps:.0f}fps, step={step}, fps_eff={fps_eff:.0f}, "
          f"cam={None if cam_xyz is None else np.round(cam_xyz,1)}  "
          f"({len(ballg)} ball / {len(noball)} no-ball)")
    print(f"    {'stage':<34}{'false-fire':>7}{'recall':>9}{'far-rec':>10}\n" + "-"*62)
    for w in args.weights:
        print(f"[{Path(w).name}]", flush=True)
        raw = perceive(video, w, args.device, H, cam_xyz, W, Hh, fps_eff, step)
        measure(raw, ballg, noball, step, "tracker gates only")
        tr = B.remove_outliers(list(raw), max_jump=max(W, Hh)*0.06)
        tr = B.rectify_track(tr, max_speed_px=3000.0/fps_eff, resid_px=35.0)
        measure(tr, ballg, noball, step, "+ rectify")
        tr2 = B.suppress_false_locks(tr, fps_eff=fps_eff)
        measure(tr2, ballg, noball, step, "+ suppress_false_locks")
        tr3 = B.filter_live_ball(tr2, homography=H)
        measure(tr3, ballg, noball, step, "+ live-ball filter (FULL)")


if __name__ == "__main__":
    main()
