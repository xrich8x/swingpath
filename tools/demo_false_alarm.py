"""demo_false_alarm.py — SEE the false-alarm fix on a NON-gold clip (demo30).

Runs the ball path twice and renders them side by side:
  LEFT  OLD  = baseline detector (ballnet.pt) + old post (rectify + live-ball filter)
  RIGHT NEW  = v2.1 detector + new post (rectify + suppress_false_locks, no live)
Both use demo30's calibration (court gate on). No labels here — the point is the
eyeball test: does the NEW trail stop locking the HUD / net posts / fixtures while
still following the real ball. Also dumps frames where the two disagree most.

  cd backend && .venv-train/Scripts/python.exe ../tools/demo_false_alarm.py --device cuda
"""
from __future__ import annotations
import argparse, json, math, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import cv2
import numpy as np

VIDEO = REPO / "data" / "demo30.mp4"
PTS = REPO / "data" / "demo30_pts.json"
OUT = REPO / "data" / "output" / "demo30_false_alarm.mp4"
CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def perceive(weights, device, H, cam_xyz, W, Hh, fps_eff):
    os.environ["BALLNET_WEIGHTS"] = weights
    from swingvision.ball import OurBallDetector, BallTracker
    tr = BallTracker([OurBallDetector(device=device)], (W, Hh), use_bgsub=False,
                     homography=H, fps=fps_eff, cam_xyz=cam_xyz)
    cap = cv2.VideoCapture(str(VIDEO))
    frames, locks = [], []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
        locks.append(tr.update(f))
    cap.release()
    return frames, locks


def to_h264(path):
    """cv2's mp4v codec won't play in browsers / most Windows players. Transcode
    in place to H.264 with the ffmpeg binary imageio_ffmpeg bundles (no system
    ffmpeg needed)."""
    try:
        import imageio_ffmpeg, subprocess
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        tmp = str(path) + ".h264.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(path),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                        "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, str(path))
        print(f"  transcoded to H.264 (browser-playable)")
    except Exception as e:
        print(f"  (H.264 transcode skipped: {e})")


def draw(frame, track, i, color, label, n_locks):
    f = frame.copy()
    for k in range(max(1, i - 10), i + 1):
        a, b = track[k - 1], track[k]
        if a is not None and b is not None:
            cv2.line(f, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), color, 2, cv2.LINE_AA)
    p = track[i]
    if p is not None:
        cv2.circle(f, (int(p[0]), int(p[1])), 9, color, -1, cv2.LINE_AA)
        cv2.circle(f, (int(p[0]), int(p[1])), 12, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(f, (0, 0), (f.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(f, label, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.putText(f, f"locks:{n_locks}", (f.shape[1] - 150, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    from swingvision import calibration, court, ball as B
    kp = json.load(open(PTS))
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN], [kp[n] for n in CORN])
    cap = cv2.VideoCapture(str(VIDEO))
    W = int(cap.get(3)); Hh = int(cap.get(4)); fps = cap.get(5) or 30.0; cap.release()
    step = max(1, round(fps / 30.0)); fps_eff = fps / step
    cam_xyz = calibration.camera_position_m(H, (W, Hh), 70.0)

    print("[old] perceiving baseline (ballnet.pt)...", flush=True)
    frames, old_locks = perceive("weights/ballnet.pt", args.device, H, cam_xyz, W, Hh, fps_eff)
    print("[new] perceiving v2.1 (ballnet_v21.pt)...", flush=True)
    _, new_locks = perceive("weights/ballnet_v21.pt", args.device, H, cam_xyz, W, Hh, fps_eff)

    # OLD post: rectify + live-ball filter ; NEW post: rectify + suppress
    old = B.remove_outliers(list(old_locks), max_jump=max(W, Hh) * 0.06)
    old = B.rectify_track(old, max_speed_px=3000.0 / fps_eff, resid_px=35.0)
    old = B.filter_live_ball(old, homography=H)
    new = B.remove_outliers(list(new_locks), max_jump=max(W, Hh) * 0.06)
    new = B.rectify_track(new, max_speed_px=3000.0 / fps_eff, resid_px=35.0)
    new = B.suppress_false_locks(new, fps_eff=fps_eff)

    n_old = sum(p is not None for p in old); n_new = sum(p is not None for p in new)
    print(f"OLD kept {n_old} locks, NEW kept {n_new} locks over {len(frames)} frames")

    scale = 0.75
    sw, sh = int(W * scale), int(Hh * scale)
    writer = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps, (sw * 2, sh))
    diffs = []
    for i, fr in enumerate(frames):
        lo = draw(fr, old, i, (80, 80, 255), "OLD  baseline + live filter", n_old)
        rt = draw(fr, new, i, (0, 230, 0), "NEW  v2.1 + suppressor", n_new)
        combo = np.hstack([cv2.resize(lo, (sw, sh)), cv2.resize(rt, (sw, sh))])
        writer.write(combo)
        # a frame where OLD locked something NEW dropped (a suppressed false alarm)
        if old[i] is not None and new[i] is None:
            diffs.append((i, old[i]))
    writer.release()
    to_h264(OUT)
    print(f"wrote {OUT}")
    # export a few example 'OLD locked, NEW dropped' full-res frames
    picks = diffs[:: max(1, len(diffs) // 4)][:4] if diffs else []
    for i, p in picks:
        f = draw(frames[i], old, i, (80, 80, 255), f"OLD locked here (frame {i})", n_old)
        cv2.imwrite(str(REPO / f"data/output/demo30_olddrop_{i:04d}.png"), f)
    print(f"{len(diffs)} frames where OLD kept a lock NEW dropped; examples: {[i for i,_ in picks]}")


if __name__ == "__main__":
    main()
