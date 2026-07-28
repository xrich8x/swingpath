"""coast_fill_probe.py — diagnose mid-flight ball-track gaps on a non-gold clip
and compare three fills: raw locks, current LINEAR interpolation, and an arc-aware
COAST (local image-space parabola x(t),y(t)). Physics, not ML: mid-flight the ball
is ballistic, so a degree-2 fit through the surrounding locks follows the real arc
where a straight line floats.

Perceives once (GPU), caches the track to json, then all analysis/render is CPU.

  cd backend && .venv-train/Scripts/python.exe ../tools/coast_fill_probe.py --device cuda
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
TRACK_CACHE = REPO / "data" / "output" / "demo30_v21_track.json"
CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def perceive_and_cache(device):
    from swingvision import calibration, court, ball as B
    kp = json.load(open(PTS))
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN], [kp[n] for n in CORN])
    cap = cv2.VideoCapture(str(VIDEO))
    W = int(cap.get(3)); Hh = int(cap.get(4)); fps = cap.get(5) or 30.0
    step = max(1, round(fps / 30.0)); fps_eff = fps / step
    cam_xyz = calibration.camera_position_m(H, (W, Hh), 70.0)
    os.environ["BALLNET_WEIGHTS"] = "weights/ballnet_v21.pt"
    from swingvision.ball import OurBallDetector, BallTracker
    tr = BallTracker([OurBallDetector(device=device)], (W, Hh), use_bgsub=False,
                     homography=H, fps=fps_eff, cam_xyz=cam_xyz)
    locks = []
    idx = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if idx % step == 0:
            locks.append(tr.update(f))
        idx += 1
    cap.release()
    post = B.remove_outliers(list(locks), max_jump=max(W, Hh) * 0.06)
    post = B.rectify_track(post, max_speed_px=3000.0 / fps_eff, resid_px=35.0)
    post = B.suppress_false_locks(post, fps_eff=fps_eff)
    json.dump({"post": [None if p is None else [float(p[0]), float(p[1])] for p in post],
               "W": W, "H": Hh, "fps": fps, "step": step}, open(TRACK_CACHE, "w"))
    print(f"cached {TRACK_CACHE.name}: {sum(p is not None for p in post)} locks / {len(post)} frames")
    return post


def gaps(track):
    """interior None-runs bounded by a lock on each side -> list of (start,end,len)."""
    out, n = [], len(track)
    i = 0
    while i < n:
        if track[i] is not None:
            j = i + 1
            while j < n and track[j] is None:
                j += 1
            if j < n and j - i - 1 > 0:      # gap (i, j) has j-i-1 missing frames
                out.append((i, j, j - i - 1))
            i = j
        else:
            i += 1
    return out


def linear_fill(track):
    out = [None if p is None else list(p) for p in track]
    for a, b, L in gaps(track):
        for k in range(a + 1, b):
            t = (k - a) / (b - a)
            out[k] = [track[a][0] + t * (track[b][0] - track[a][0]),
                      track[a][1] + t * (track[b][1] - track[a][1])]
    return out


def coast_fill(track, win=4, max_gap=30):
    """arc-aware: fit x(t),y(t) as degree-2 through up to `win` locks each side of
    the gap and evaluate across it. Falls back to linear if too few anchors or the
    velocity reverses across the gap (a hit — the arc changes, don't coast through)."""
    out = [None if p is None else list(p) for p in track]
    n = len(track)
    for a, b, L in gaps(track):
        if L > max_gap:
            continue
        left = [k for k in range(max(0, a - win + 1), a + 1) if track[k] is not None]
        right = [k for k in range(b, min(n, b + win)) if track[k] is not None]
        pre_v = (track[a][0] - track[left[0]][0]) if len(left) >= 2 else 0.0
        post_v = (track[right[-1]][0] - track[b][0]) if len(right) >= 2 else pre_v
        anchors = left + right
        if len(anchors) < 3 or (pre_v * post_v < 0 and abs(pre_v) > 2):
            for k in range(a + 1, b):        # hit or too few points -> linear
                t = (k - a) / (b - a)
                out[k] = [track[a][0] + t * (track[b][0] - track[a][0]),
                          track[a][1] + t * (track[b][1] - track[a][1])]
            continue
        ts = np.array(anchors, float)
        px = np.polyfit(ts, [track[k][0] for k in anchors], 2)
        py = np.polyfit(ts, [track[k][1] for k in anchors], 2)
        for k in range(a + 1, b):
            out[k] = [float(np.polyval(px, k)), float(np.polyval(py, k))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--use-cache", action="store_true")
    args = ap.parse_args()
    if args.use_cache and TRACK_CACHE.exists():
        d = json.load(open(TRACK_CACHE))
        post = [None if p is None else p for p in d["post"]]
        W, Hh, fps, step = d["W"], d["H"], d["fps"], d["step"]
    else:
        post = perceive_and_cache(args.device)
        d = json.load(open(TRACK_CACHE)); W, Hh, fps, step = d["W"], d["H"], d["fps"], d["step"]

    gg = gaps(post)
    lens = [L for _, _, L in gg]
    print(f"\n{len(gg)} interior gaps; missing-frame lengths: "
          f"min={min(lens) if lens else 0} median={int(np.median(lens)) if lens else 0} "
          f"max={max(lens) if lens else 0}")
    from collections import Counter
    buckets = Counter("1-2" if L <= 2 else "3-6" if L <= 6 else "7-15" if L <= 15 else "16+"
                      for L in lens)
    for k in ("1-2", "3-6", "7-15", "16+"):
        print(f"  gap {k:>5} frames: {buckets.get(k,0)}")
    print(f"total missing frames bridged: {sum(lens)}")

    lin = linear_fill(post)
    coa = coast_fill(post)
    # how far linear and coast disagree inside gaps (px) — where the arc matters
    dev = [math.dist(lin[k], coa[k]) for a, b, L in gg for k in range(a + 1, b)
           if lin[k] and coa[k]]
    if dev:
        print(f"\nlinear vs arc-coast disagreement inside gaps: "
              f"median={np.median(dev):.1f}px  p90={np.percentile(dev,90):.1f}px  max={max(dev):.1f}px")

    # render raw | linear | coast, three panels
    cap = cv2.VideoCapture(str(VIDEO))
    frames = []
    idx = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        if idx % step == 0: frames.append(f)
        idx += 1
    cap.release()

    def panel(fr, track, i, color, label, is_gap):
        f = fr.copy()
        for k in range(max(1, i - 12), i + 1):
            if track[k - 1] and track[k]:
                cv2.line(f, (int(track[k-1][0]), int(track[k-1][1])),
                         (int(track[k][0]), int(track[k][1])), color, 2, cv2.LINE_AA)
        p = track[i]
        if p:
            c = (0, 220, 255) if is_gap else color   # amber when this point is filled
            cv2.circle(f, (int(p[0]), int(p[1])), 9, c, -1, cv2.LINE_AA)
            cv2.circle(f, (int(p[0]), int(p[1])), 12, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.rectangle(f, (0, 0), (f.shape[1], 30), (0, 0, 0), -1)
        cv2.putText(f, label, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return f

    gapset = set(k for a, b, L in gg for k in range(a + 1, b))
    sw, sh = int(W * 0.5), int(Hh * 0.5)
    out_mp4 = REPO / "data" / "output" / "demo30_coast.mp4"
    wr = cv2.VideoWriter(str(out_mp4), cv2.VideoWriter_fourcc(*"mp4v"), fps, (sw * 3, sh))
    for i, fr in enumerate(frames):
        a = panel(fr, post, i, (200, 200, 200), "RAW detections (gaps)", False)
        b = panel(fr, lin, i, (80, 80, 255), "LINEAR fill (current)", i in gapset)
        c = panel(fr, coa, i, (0, 230, 0), "ARC coast (proposed)", i in gapset)
        wr.write(np.hstack([cv2.resize(a, (sw, sh)), cv2.resize(b, (sw, sh)), cv2.resize(c, (sw, sh))]))
    wr.release()
    try:
        import imageio_ffmpeg, subprocess
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        tmp = str(out_mp4) + ".h264.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(out_mp4), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, str(out_mp4))
    except Exception as e:
        print("h264 skip:", e)
    print(f"wrote {out_mp4} (amber dot = a filled/coasted frame)")


if __name__ == "__main__":
    main()
