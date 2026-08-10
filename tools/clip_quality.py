"""clip_quality.py — rank training clips by how much BALL there is to see.

WHY NOT JUST LOOK AT THE RESOLUTION
-----------------------------------
"1080p" is a container label, not a measurement. A YouTube re-upload of a 480p
recording is still 1080p in its header, and this project's whole far-court
problem is a shortage of pixels ON THE BALL — so the number that decides whether
a clip is worth keeping is how many real, sharp pixels the ball occupies, not
what the file claims.

Four measurements, and the last two are the ones that matter:

  bitrate        MB per minute. Cheap proxy for how hard the encoder squeezed;
                 a heavily compressed frame loses the small high-contrast blobs
                 first, which is exactly the ball.
  detail         residual after halving the frame and scaling it back up,
                 normalised by the frame's own contrast. A genuinely sharp clip
                 keeps detail the half-resolution copy cannot reproduce; an
                 UPSCALED one has almost none, whatever its header says.
  ball_px        median apparent ball diameter in SOURCE pixels, far court only,
                 measured at the tracker's own label positions.
  ball_contrast  median |ball - local background| in grey levels there.

Measured on the gold set for calibration: the far ball carries MORE contrast
than the near ball (99 vs 88 grey levels over 1201 human clicks), so contrast is
rarely the thing that fails.

READ `--at-human-clicks` BEFORE ACTING ON THE DEFAULT TABLE
-----------------------------------------------------------
The default mode measures the ball at the TRACKER's label positions, and on
these clips roughly half of those are false locks on a wall, a hedge or a
spectator. It therefore reports the size of whatever the tracker found, which
is why it comes out ANTI-correlated with whether a human could find the ball:
`nQan0M5JDM8` scores the largest "ball" in the pool (17.3 px) at a contrast of
37, which is a big soft blob, not a ball.

`--at-human-clicks` re-measures at positions a human actually clicked in the
far-court label queues. That is the only clean version, and its verdict is
blunt: **none of these numbers predicts whether the ball was findable.** The
smallest ball in the pool (TilAFMPc0yg, 3.7 px) was found on 88% of frames; the
sharpest clip (ewqSn18xdsY) has the highest unsure rate. Do not delete footage
on this table.

A CONFOUND TO AVOID IN THIS TABLE, because it was walked into once
------------------------------------------------------------------
`ball_px_at_net` reads lower on the two 1080p clips (3.11, 3.14) than on some
720p ones (3.69, 4.10), which looks like "higher resolution delivers a smaller
ball". It is not. The ball subtends a fixed FRACTION of the frame, so a source
of any width scaled to 512 yields the same pixels: 11.7 px at 1920 wide and
7.8 px at 1280 wide are the same ball. What the column actually ranks is how
tightly each camera FRAMED the court — 11.7/1920 = 0.61% of frame width against
9.2/1280 = 0.72%.

So resolution is NEUTRAL at the network input, matching the standing measurement
that recording at 1080p or 4K "currently buys nothing" (data/output/
phase0_ball_ceiling.md). Framing is not neutral: filling the frame with the
court is worth real ball pixels, and it is free.

    py tools/clip_quality.py --dir data/train_clips
    py tools/clip_quality.py --at-human-clicks

Reports only. It never deletes anything — the clips are gitignored, have no
off-machine copy, and both data/ball_dataset and every far-court human label
reference them by name and frame number.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAR_FRAC = 0.36           # the project's resolution-comparable far_px band
IN_W, IN_H = 512, 288     # BallNet's input; the 512x288 the ball is resized to


def probe(video: Path, n_detail: int = 24):
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dets, sharp = [], []
    for i in np.linspace(0.1 * total, 0.9 * total, n_detail).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, im = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
        half = cv2.resize(g, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        back = cv2.resize(half, (W, H), interpolation=cv2.INTER_CUBIC)
        # Normalise by the frame's own contrast: a dark night clip is not
        # "softer" than a bright one, it just has less range to work with.
        dets.append(float(np.abs(g - back).mean() / max(g.std(), 1e-3)))
        sharp.append(float(cv2.Laplacian(g, cv2.CV_32F).var()))
    cap.release()
    if not dets:
        return None
    mb = video.stat().st_size / 1e6
    mins = (total / fps) / 60.0 if fps else 0.0
    return {"video": video.name, "w": W, "h": H, "fps": round(fps, 1),
            "minutes": round(mins, 1), "mb": round(mb, 1),
            "mb_per_min": round(mb / mins, 1) if mins else None,
            "detail": round(st.median(dets), 4),
            "laplacian": round(st.median(sharp), 1)}


def ball_stats(video: Path, dataset_dir: Path, clips_root: Path, n: int = 90):
    """Far-court ball diameter and contrast, in SOURCE pixels, at the tracker's
    own label positions. Pseudo-labels include false locks, so these are medians
    over many samples rather than per-frame truth."""
    import cv2
    import numpy as np
    import sys

    sys.path.insert(0, str(REPO / "tools"))
    from select_farcourt_labels import source_map, source_frame

    lp = dataset_dir / "labels.json"
    if not lp.is_file():
        return {}
    sm = source_map(dataset_dir, clips_root)
    if sm is None:
        return {}
    _vid, ws, starts, step, (W, H) = sm
    L = {int(k): v for k, v in (json.loads(lp.read_text(encoding="utf-8"))
                                .get("labels") or {}).items()}
    far = [(k, v) for k, v in L.items() if v[1] < FAR_FRAC * IN_H]
    if not far:
        return {}
    far.sort()
    take = far[:: max(1, len(far) // n)][:n]
    cap = cv2.VideoCapture(str(video))
    dia, con = [], []
    sx, sy = W / IN_W, H / IN_H
    for k, (bx, by) in take:
        cap.set(cv2.CAP_PROP_POS_FRAMES, source_frame(k, ws, starts, step))
        ok, im = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(float)
        x, y = int(bx * sx), int(by * sy)
        if not (14 <= x < g.shape[1] - 14 and 14 <= y < g.shape[0] - 14):
            continue
        peak = g[y - 1:y + 2, x - 1:x + 2].max()
        ring = np.concatenate([g[y - 12:y + 13, x - 12:x - 6].ravel(),
                               g[y - 12:y + 13, x + 7:x + 13].ravel()])
        bg = float(np.median(ring))
        c = abs(peak - bg)
        if c < 8:                       # a lock on flat background: not a ball
            continue
        w = g[y - 9:y + 10, x - 9:x + 10]
        npx = int((np.abs(w - bg) >= c * 0.5).sum())
        dia.append(2 * (max(npx, 1) / np.pi) ** 0.5)
        con.append(c)
    cap.release()
    if not dia:
        return {}
    return {"far_n": len(dia), "ball_px": round(st.median(dia), 1),
            "ball_contrast": round(st.median(con), 1),
            "ball_px_at_net": round(st.median(dia) * IN_W / max(1, W), 2)}


def _patch_stats(g, x, y):
    """(apparent diameter px, |ball - local background|) at one position."""
    import numpy as np

    if not (14 <= x < g.shape[1] - 14 and 14 <= y < g.shape[0] - 14):
        return None
    peak = g[y - 1:y + 2, x - 1:x + 2].max()
    ring = np.concatenate([g[y - 12:y + 13, x - 12:x - 6].ravel(),
                           g[y - 12:y + 13, x + 7:x + 13].ravel()])
    bg = float(np.median(ring))
    c = abs(peak - bg)
    w = g[y - 9:y + 10, x - 9:x + 10]
    n = int((np.abs(w - bg) >= c * 0.5).sum())
    return 2 * (max(n, 1) / np.pi) ** 0.5, c


def at_human_clicks(labels_dir: Path, clips_root: Path):
    """Ball size and contrast at positions a HUMAN clicked, per source clip.

    The queue frames are the source frames at native resolution, so this reads
    them straight off disk — no seeking, no rescaling, and no tracker involved.
    """
    import cv2
    import numpy as np

    per: dict = {}
    for man_p in sorted(labels_dir.glob("*.manifest.json")):
        man = json.loads(man_p.read_text(encoding="utf-8"))
        lab_p = man_p.with_name(man_p.name.replace(".manifest.", ".labels."))
        if not lab_p.is_file():
            continue
        lab = json.loads(lab_p.read_text(encoding="utf-8")).get("labels") or {}
        for r in man["frames"]:
            v = lab.get(str(r["frame"])) or {}
            if v.get("x") is None or v.get("unsure") or not r.get("video"):
                continue
            p = labels_dir / "frames" / man["clip"] / f"f{r['frame']:05d}.jpg"
            im = cv2.imread(str(p))
            if im is None:
                continue
            s = _patch_stats(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(float),
                             int(v["x"]), int(v["y"]))
            if s:
                per.setdefault(r["video"], []).append((s[0], s[1], im.shape[1]))
    out = {}
    for vid, rows in per.items():
        d = [r[0] for r in rows]
        out[vid] = {"human_n": len(rows), "human_ball_px": round(st.median(d), 1),
                    "human_contrast": round(st.median([r[1] for r in rows]), 1),
                    "human_ball_px_at_net": round(st.median(d) * IN_W / rows[0][2], 2)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=str(REPO / "data/train_clips"))
    ap.add_argument("--dataset", default=str(REPO / "data/ball_dataset"))
    ap.add_argument("--labels", default=str(REPO / "data/labels"))
    ap.add_argument("--at-human-clicks", action="store_true",
                    help="THE CLEAN VERSION. Measure at positions a human "
                         "clicked instead of at the tracker's locks, half of "
                         "which are not balls")
    ap.add_argument("--json", default=str(REPO / "data/output/clip_quality.json"))
    args = ap.parse_args()

    if args.at_human_clicks:
        got = at_human_clicks(Path(args.labels), Path(args.dir))
        hdr = f"{'clip':<18}{'n':>4}{'ball px':>9}{'at net':>8}{'contrast':>10}"
        print("measured at HUMAN clicks in the far-court label queues\n")
        print(hdr); print("-" * len(hdr))
        for vid, r in sorted(got.items(), key=lambda kv: kv[1]["human_ball_px_at_net"]):
            print(f"{Path(vid).stem:<18}{r['human_n']:>4}{r['human_ball_px']:>9.1f}"
                  f"{r['human_ball_px_at_net']:>8.2f}{r['human_contrast']:>10.1f}")
        Path(args.json).with_name("clip_quality_human.json").write_text(
            json.dumps(got, indent=1), encoding="utf-8")
        print("\nNone of these columns predicts whether the ball was findable — "
              "see this file's docstring. Do not delete footage on them.")
        return

    root, ds = Path(args.dir), Path(args.dataset)
    rows = []
    for v in sorted(root.glob("*.mp4")):
        r = probe(v)
        if r is None:
            print(f"{v.name}: unreadable")
            continue
        d = ds / f"yt_{v.stem}"
        r.update(ball_stats(v, d, root) if d.is_dir() else {})
        rows.append(r)
        print(".", end="", flush=True)
    print()

    hdr = (f"{'clip':<18}{'res':>10}{'fps':>6}{'MB/min':>8}{'detail':>8}"
           f"{'far n':>7}{'ball px':>9}{'at net':>8}{'contrast':>10}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: r.get("ball_px") or 0):
        print(f"{Path(r['video']).stem:<18}{r['w']}x{r['h']:<5}{r['fps']:>6}"
              f"{r['mb_per_min'] or 0:>8.1f}{r['detail']:>8.3f}"
              f"{r.get('far_n', 0):>7}{r.get('ball_px', 0):>9.1f}"
              f"{r.get('ball_px_at_net', 0):>8.2f}{r.get('ball_contrast', 0):>10.1f}")
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nwrote {args.json}")
    print("Reports only — nothing is deleted. These files are gitignored and "
          "have no off-machine copy.")


if __name__ == "__main__":
    main()
