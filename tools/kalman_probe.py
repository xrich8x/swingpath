"""kalman_probe.py — smoothing + forecasting of the ball via a constant-acceleration
Kalman filter + RTS smoother (image space), prototyped on the cached demo30 track.

Why this replaces per-gap polyfit coasting: one physics model governs the WHOLE
track, so (a) noisy detections are denoised, (b) gaps are forecast by the same
ballistic model with no kink where a fill meets a detection, (c) outlier locks are
gated out by innovation, (d) covariance gives a per-frame confidence that grows the
longer the ball is unseen. Hits/bounces (sharp direction change) are handled by a
reset: sustained gated detections => the model is stale => start a new segment; the
RTS smoother never bridges across a reset, so corners stay sharp.

  cd backend && .venv/Scripts/python.exe ../tools/kalman_probe.py [--r 9 --jerk 2]
"""
from __future__ import annotations
import argparse, json, math, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import cv2
import numpy as np

VIDEO = REPO / "data" / "demo30.mp4"
CACHE = REPO / "data" / "output" / "demo30_v21_track.json"
OUT = REPO / "data" / "output" / "demo30_kalman.mp4"


def ca_block():
    # constant-acceleration transition for one axis, dt=1: p+=v+a/2, v+=a
    return np.array([[1, 1, 0.5], [0, 1, 1], [0, 0, 1]], float)


def q_block(sj):
    # continuous white-noise-jerk process noise, dt=1
    return (sj ** 2) * np.array([[1/20, 1/8, 1/6], [1/8, 1/3, 1/2], [1/6, 1/2, 1]], float)


def kalman_rts(meas, r=9.0, jerk=2.0, gate=13.8, reset_after=3, max_forecast=25):
    """meas: list of (x,y)|None. Returns (smoothed[(x,y)|None], coasted[bool], conf[0..1])."""
    n = len(meas)
    F = np.zeros((6, 6)); F[:3, :3] = ca_block(); F[3:, 3:] = ca_block()
    Q = np.zeros((6, 6)); Q[:3, :3] = q_block(jerk); Q[3:, 3:] = q_block(jerk)
    H = np.zeros((2, 6)); H[0, 0] = 1; H[1, 3] = 1
    R = np.eye(2) * r

    # forward pass, tracking segments (reset at sustained rejection / long gap)
    seg_id = [-1] * n
    xf = [None] * n; Pf = [None] * n         # filtered (posterior)
    xp = [None] * n; Pp = [None] * n         # predicted (prior)
    used = [False] * n                        # measurement accepted this frame
    x = None; P = None; seg = 0; miss = 0; rej = 0

    def init(z):
        s = np.array([z[0], 0, 0, z[1], 0, 0], float)
        C = np.diag([r, 400, 100, r, 400, 100]).astype(float)
        return s, C

    for i in range(n):
        if x is None:
            if meas[i] is not None:
                x, P = init(meas[i]); xp[i], Pp[i] = x.copy(), P.copy()
                xf[i], Pf[i] = x.copy(), P.copy(); used[i] = True; seg_id[i] = seg
            continue
        x = F @ x; P = F @ P @ F.T + Q
        xp[i], Pp[i] = x.copy(), P.copy()
        z = meas[i]
        accept = False
        if z is not None:
            y = np.array([z[0], z[1]]) - H @ x
            S = H @ P @ H.T + R
            d2 = float(y @ np.linalg.solve(S, y))
            if d2 <= gate:
                K = P @ H.T @ np.linalg.inv(S)
                x = x + K @ y; P = (np.eye(6) - K @ H) @ P
                accept = True; rej = 0; miss = 0
            else:
                rej += 1
        if not accept:
            miss += 1
        used[i] = accept
        xf[i], Pf[i] = x.copy(), P.copy(); seg_id[i] = seg
        # reset conditions: too many rejects (a hit) or too long unseen (stale)
        if (rej >= reset_after) or (miss >= max_forecast):
            x = None; P = None; seg += 1; rej = 0; miss = 0
            if z is not None:                 # re-seed a fresh segment on this lock
                x, P = init(z); xp[i], Pp[i] = x.copy(), P.copy()
                xf[i], Pf[i] = x.copy(), P.copy(); used[i] = True; seg_id[i] = seg

    # RTS backward smoother, per segment
    xs = [None if xf[i] is None else xf[i].copy() for i in range(n)]
    Ps = [None if Pf[i] is None else Pf[i].copy() for i in range(n)]
    for i in range(n - 2, -1, -1):
        if xf[i] is None or xs[i + 1] is None or seg_id[i] != seg_id[i + 1]:
            continue
        C = Pf[i] @ F.T @ np.linalg.inv(Pp[i + 1])
        xs[i] = xf[i] + C @ (xs[i + 1] - xp[i + 1])
        Ps[i] = Pf[i] + C @ (Ps[i + 1] - Pp[i + 1]) @ C.T

    out = [None] * n; coasted = [False] * n; conf = [0.0] * n
    for i in range(n):
        if xs[i] is None:
            continue
        out[i] = [float(xs[i][0]), float(xs[i][3])]
        coasted[i] = not used[i]
        pos_var = Ps[i][0, 0] + Ps[i][3, 3] if Ps[i] is not None else 0.0
        conf[i] = float(1.0 / (1.0 + pos_var / (4 * r)))   # ~1 at a measurement, decays in gaps
    return out, coasted, conf


def draw(fr, track, i, coasted, conf, base, label):
    f = fr.copy()
    for k in range(max(1, i - 14), i + 1):
        if track[k - 1] and track[k]:
            guess = coasted is not None and (coasted[k] or coasted[k - 1])
            col = (0, 190, 235) if guess else base
            cv2.line(f, (int(track[k-1][0]), int(track[k-1][1])),
                     (int(track[k][0]), int(track[k][1])), col, 2, cv2.LINE_AA)
    p = track[i]
    if p:
        guess = coasted is not None and coasted[i]
        col = (0, 190, 235) if guess else base
        cv2.circle(f, (int(p[0]), int(p[1])), 8, col, -1, cv2.LINE_AA)
        cv2.circle(f, (int(p[0]), int(p[1])), 11, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(f, (0, 0), (f.shape[1], 30), (0, 0, 0), -1)
    cv2.putText(f, label, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, base, 2)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r", type=float, default=9.0)
    ap.add_argument("--jerk", type=float, default=2.0)
    args = ap.parse_args()
    d = json.load(open(CACHE))
    post = [None if p is None else list(p) for p in d["post"]]
    W, Hh, fps, step = d["W"], d["H"], d["fps"], d["step"]

    sm, coasted, conf = kalman_rts(post, r=args.r, jerk=args.jerk)
    nvis = sum(p is not None for p in sm)
    # smoothing magnitude at measured frames (how far the smoother moved a detection)
    moved = [math.dist(sm[i], post[i]) for i in range(len(post))
             if post[i] is not None and sm[i] is not None]
    print(f"r={args.r} jerk={args.jerk}: visible {nvis}/{len(post)}, "
          f"guessed {sum(coasted)}; smoother moved detections median "
          f"{np.median(moved):.1f}px p90 {np.percentile(moved,90):.1f}px")

    cap = cv2.VideoCapture(str(VIDEO)); frames = []; idx = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        if idx % step == 0: frames.append(f)
        idx += 1
    cap.release()
    sw, sh = int(W * 0.6), int(Hh * 0.6)
    wr = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps, (sw * 2, sh))
    for i, fr in enumerate(frames):
        a = draw(fr, post, i, None, None, (200, 200, 200), "BEFORE  raw detections")
        b = draw(fr, sm, i, coasted, conf, (0, 230, 0), "AFTER  Kalman smooth+forecast (amber=guessed)")
        wr.write(np.hstack([cv2.resize(a, (sw, sh)), cv2.resize(b, (sw, sh))]))
    wr.release()
    try:
        import imageio_ffmpeg, subprocess
        ff = imageio_ffmpeg.get_ffmpeg_exe(); tmp = str(OUT) + ".h264.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(OUT), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, str(OUT))
    except Exception as e:
        print("h264 skip:", e)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
