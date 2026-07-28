"""render_coast_demo.py — before/after for the arc-coast, using the SHIPPED
ball.coast_fill. LEFT = raw detections (what vanished mid-flight); RIGHT = the
ball coasting along its arc, with GUESSED frames dimmed/amber so honest.
Reuses the cached demo30 track (no GPU).

  cd backend && .venv/Scripts/python.exe ../tools/render_coast_demo.py
"""
from __future__ import annotations
import json, math, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import cv2
import numpy as np
from swingvision import ball as B

VIDEO = REPO / "data" / "demo30.mp4"
CACHE = REPO / "data" / "output" / "demo30_v21_track.json"
OUT = REPO / "data" / "output" / "demo30_smooth_final.mp4"


def draw(fr, track, i, coasted, base_color, label):
    f = fr.copy()
    for k in range(max(1, i - 12), i + 1):
        if track[k - 1] and track[k]:
            guess = coasted is not None and (coasted[k] or coasted[k - 1])
            col = (0, 190, 235) if guess else base_color      # amber trail on guesses
            cv2.line(f, (int(track[k-1][0]), int(track[k-1][1])),
                     (int(track[k][0]), int(track[k][1])), col, 2, cv2.LINE_AA)
    p = track[i]
    if p:
        guess = coasted is not None and coasted[i]
        col = (0, 190, 235) if guess else base_color
        r = 7 if guess else 9
        cv2.circle(f, (int(p[0]), int(p[1])), r, col, -1, cv2.LINE_AA)
        cv2.circle(f, (int(p[0]), int(p[1])), r + 3, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(f, (0, 0), (f.shape[1], 32), (0, 0, 0), -1)
    cv2.putText(f, label, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.62, base_color, 2)
    return f


def main():
    d = json.load(open(CACHE))
    post = [None if p is None else list(p) for p in d["post"]]
    W, Hh, fps, step = d["W"], d["H"], d["fps"], d["step"]
    fps_eff = fps / step

    # SHIPPED path: Kalman smooth+forecast is authoritative. It denoises real
    # detections and interpolates only SHORT gaps bounded by detections; it does NOT
    # extrapolate (no phantom ball in dead time, no run-off-screen). We deliberately
    # do not re-fill with coast_fill / smooth_and_fill here — that would repaint the
    # gaps it intentionally left empty.
    filled, coasted, conf = B.smooth_forecast(post, fps_eff=fps_eff)

    def jerk(track):
        acc = []
        for k in range(1, len(track) - 1):
            if track[k-1] and track[k] and track[k+1]:
                acc.append(math.hypot(track[k-1][0]-2*track[k][0]+track[k+1][0],
                                      track[k-1][1]-2*track[k][1]+track[k+1][1]))
        return float(np.mean(acc)) if acc else 0.0
    n_real = sum(p is not None for p in post)
    print(f"real detections {n_real}, visible {sum(p is not None for p in filled)}/{len(post)}; "
          f"jerkiness raw {jerk(post):.2f} -> smoothed {jerk(filled):.2f} px/frame^2")

    cap = cv2.VideoCapture(str(VIDEO))
    frames = []
    idx = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        if idx % step == 0: frames.append(f)
        idx += 1
    cap.release()

    sw, sh = int(W * 0.6), int(Hh * 0.6)
    wr = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps, (sw * 2, sh))
    for i, fr in enumerate(frames):
        a = draw(fr, post, i, None, (200, 200, 200), "BEFORE  raw detections (ball vanishes)")
        b = draw(fr, filled, i, coasted, (0, 230, 0), "AFTER  Kalman smooth+forecast (amber = guessed)")
        wr.write(np.hstack([cv2.resize(a, (sw, sh)), cv2.resize(b, (sw, sh))]))
    wr.release()
    try:
        import imageio_ffmpeg, subprocess
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        tmp = str(OUT) + ".h264.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(OUT), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, str(OUT))
        print("transcoded H.264")
    except Exception as e:
        print("h264 skip:", e)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
