"""Select a stratified set of frames for human gold-labeling (HANDOFF §8 fix 1.4).

Builds the frame list for the browser labeling tool (gold_label_server.py).
Selection is stratified, not random — five buckets:

  serve     frames around each rally start (serve contact windows)
  near      mid-rally, ball on the camera-near half (court y < net)
  far       mid-rally, ball on the far half — the decisive bucket for the
            demo30 archive-vs-fresh question (HANDOFF §10)
  disagree  frames where the archived cache and a fresh run disagree
            (one locks and the other doesn't, or locks >10 px apart)
  noball    frames likely to contain no ball in play, plus distractor frames
            where some track sits on a static fixture (HUD box, logo, net post)

Assignment priority when a frame qualifies for several buckets:
serve > disagree > noball > near/far. Each frame lands in exactly one bucket.

Outputs (under --out, default data/gold/):
  <clip>.manifest.json          frame list + buckets + provenance (committed)
  frames/<clip>/f<NNNNN>.jpg    extracted frames for the browser tool (gitignored;
                                regenerable from the video with --extract-only)

Degrades gracefully for future clips: no --match json -> no serve bucket;
fewer than 2 caches -> no disagree bucket. With NO caches at all the
stratification signals don't exist, so selection is plain UNIFORM over the
whole clip (single bucket "uniform") — statistically the cleanest option for
a generalization test set; per-region analysis happens post-hoc from the
human's clicks. Run from the repo root with the backend venv python:

  backend/.venv/Scripts/python.exe tools/select_gold_frames.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import court  # noqa: E402
from swingvision.calibration import compute_homography, image_to_court  # noqa: E402

# Session-1 static-junk definition (HANDOFF §10): a lock that moves less than
# STATIC_STEP_PX per frame for at least STATIC_MIN_RUN consecutive locked
# frames is a fixture (HUD label, logo, net post), never a ball.
STATIC_STEP_PX = 3.0
STATIC_MIN_RUN = 5
DISAGREE_PX = 10.0


def load_cache(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "ball_px" not in data or "frame_step" not in data:
        raise SystemExit(f"{path} does not look like a perception cache")
    return data


def static_flags(ball_px: list) -> list[bool]:
    """Flag locks that sit in a static run (Session-1 junk filter)."""
    n = len(ball_px)
    flags = [False] * n
    run: list[int] = []  # indices of the current low-motion locked run
    for i in range(n):
        cur, prev = ball_px[i], ball_px[i - 1] if i else None
        if cur is not None and prev is not None:
            step = math.dist(cur, prev)
            if step < STATIC_STEP_PX:
                if not run:
                    run = [i - 1]
                run.append(i)
                continue
        if len(run) >= STATIC_MIN_RUN:
            for j in run:
                flags[j] = True
        run = []
    if len(run) >= STATIC_MIN_RUN:
        for j in run:
            flags[j] = True
    return flags


def spread(candidates: list[int], quota: int) -> list[int]:
    """Pick up to quota items evenly spaced across a sorted candidate list."""
    if len(candidates) <= quota:
        return list(candidates)
    idx = np.linspace(0, len(candidates) - 1, quota).round().astype(int)
    return [candidates[i] for i in sorted(set(idx.tolist()))]


def streak_sample(candidates: list[int], quota: int, gap: int = 2) -> list[int]:
    """Sample round-robin across contiguous streaks so every disagreement
    episode is represented, not just the longest one."""
    streaks: list[list[int]] = []
    for c in sorted(candidates):
        if streaks and c - streaks[-1][-1] <= gap:
            streaks[-1].append(c)
        else:
            streaks.append([c])
    # take the middle of each streak first, then widen
    picked: list[int] = []
    offset = 0
    while len(picked) < quota:
        added = False
        for s in streaks:
            mid = len(s) // 2
            for k in (mid + offset, mid - offset) if offset else (mid,):
                if 0 <= k < len(s) and s[k] not in picked:
                    picked.append(s[k])
                    added = True
                    break
            if len(picked) >= quota:
                break
        if not added:
            break
        offset += 1
    return sorted(picked)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", default="data/yt_rally2.mp4")
    ap.add_argument("--clip", default="yt_rally2")
    ap.add_argument("--keypoints", default="data/yt_rally2_pts.json",
                    help="corner calibration json (for the near/far split); optional")
    ap.add_argument("--match", default="data/output/demo30.json",
                    help="match json whose rally starts define serve windows; optional")
    ap.add_argument("--caches", nargs="*", default=[
        "data/output/demo30.perception.json",            # archive (968)
        "data/output/demo30_staticgate_fusion.perception.json",
        "data/output/demo30_staticgate_tracknet.perception.json",
        "data/output/demo30b.perception.json",           # ballnet-only
    ], help="perception caches; first = reference for the disagree bucket")
    ap.add_argument("--target", type=int, default=250)
    ap.add_argument("--out", default="data/gold")
    ap.add_argument("--extract-only", action="store_true",
                    help="re-extract JPEGs for an existing manifest (after re-clone)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    out_dir = REPO / args.out
    frames_dir = out_dir / "frames" / args.clip
    manifest_path = out_dir / f"{args.clip}.manifest.json"
    video_path = REPO / args.video

    if args.extract_only:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        extract(video_path, frames_dir, [f["frame"] for f in manifest["frames"]])
        print(f"re-extracted {len(manifest['frames'])} frames -> {frames_dir}")
        return

    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video_path}")
    n_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    caches = [load_cache(REPO / c) for c in args.caches]
    if caches:
        step = caches[0]["frame_step"]
        for c, p in zip(caches, args.caches):
            if c["frame_step"] != step:
                raise SystemExit(f"frame_step mismatch: {p} has {c['frame_step']}, "
                                 f"expected {step} — caches must align")
        n_idx = min(len(c["ball_px"]) for c in caches)
        tracks = [c["ball_px"][:n_idx] for c in caches]
        stat = [static_flags(t) for t in tracks]
    else:
        # no caches: index every video frame (perception on ~30fps footage
        # uses frame_step 1, so future caches will align frame-for-frame)
        step, n_idx, tracks, stat = 1, n_video, [], []

    # Homography for the near/far split (image -> court metres, same math as
    # the pipeline). Optional: without it near/far falls back to image-y median.
    H = None
    if args.keypoints:
        try:
            with open(REPO / args.keypoints, encoding="utf-8") as f:
                kpts = json.load(f)
            names = [n for n in ("near_bl_doubles", "near_br_doubles",
                                 "far_bl_doubles", "far_br_doubles") if n in kpts]
            if len(names) >= 4:
                H = compute_homography([court.LANDMARKS[n] for n in names],
                                       [kpts[n] for n in names])
        except FileNotFoundError:
            pass

    # --- per-cache-index signals -------------------------------------------
    n_live = []      # count of non-static locks at idx
    consensus = []   # median position of non-static locks (or None)
    any_static = []  # some track is fixture-locked here (distractor frame)
    for i in range(n_idx):
        pts = [t[i] for t, s in zip(tracks, stat) if t[i] is not None and not s[i]]
        n_live.append(len(pts))
        consensus.append(np.median(np.array(pts), axis=0).tolist() if pts else None)
        any_static.append(any(t[i] is not None and s[i] for t, s in zip(tracks, stat)))

    # --- bucket candidates (cache indices) ---------------------------------
    if not tracks:
        buckets = {"uniform": spread(list(range(n_idx)), args.target)}
        write_outputs(args, manifest_path, frames_dir, video_path, buckets,
                      step, n_video, fps, width, height)
        return

    quota = args.target // 5
    taken: set[int] = set()

    def claim(cands: list[int], quota: int, sampler=spread) -> list[int]:
        picked = sampler(sorted(set(cands) - taken), quota)
        taken.update(picked)
        return picked

    buckets: dict[str, list[int]] = {}

    # (a) serve windows around each rally start
    serve_cands: list[int] = []
    if args.match:
        try:
            with open(REPO / args.match, encoding="utf-8") as f:
                match = json.load(f)
            for r in match.get("rallies", []):
                lo = int((r["start_s"] - 0.3) * fps / step)
                hi = int((r["start_s"] + 0.8) * fps / step)
                serve_cands += [i for i in range(max(lo, 0), min(hi, n_idx))]
        except FileNotFoundError:
            pass
    buckets["serve"] = claim(serve_cands, quota)

    # (d) archive-vs-fresh disagreements (reference cache vs every other)
    dis_cands: list[int] = []
    if len(tracks) >= 2:
        ref = tracks[0]
        for other in tracks[1:3]:  # vs the fresh fusion + fresh tracknet runs
            for i in range(n_idx):
                a, b = ref[i], other[i]
                if (a is None) != (b is None):
                    dis_cands.append(i)
                elif a is not None and math.dist(a, b) > DISAGREE_PX:
                    dis_cands.append(i)
    buckets["disagree"] = claim(dis_cands, quota, streak_sample)

    # (e) no-ball / distractor frames: half quiet (no live track anywhere),
    # half fixture-locked (a tracker is glued to HUD/logo/net post there)
    quiet = [i for i in range(n_idx) if n_live[i] == 0 and not any_static[i]]
    distract = [i for i in range(n_idx) if any_static[i]]
    picked_e = claim(distract, quota // 2, streak_sample)
    picked_e += claim(quiet, quota - len(picked_e))
    buckets["noball"] = sorted(picked_e)

    # (b)/(c) mid-rally near/far, split at the net line in court metres
    near_cands, far_cands = [], []
    ys = [c[1] for c in consensus if c is not None]
    y_split = float(np.median(ys)) if ys else height / 2
    for i in range(n_idx):
        if n_live[i] >= 2 and consensus[i] is not None:
            if H is not None:
                cy = image_to_court(H, [consensus[i]])[0][1]
                is_far = cy > court.NET_Y
            else:
                is_far = consensus[i][1] < y_split  # far = higher in image
            (far_cands if is_far else near_cands).append(i)
    buckets["near"] = claim(near_cands, quota)
    buckets["far"] = claim(far_cands, quota)

    # top up shortfalls from the biggest remaining pools
    total = sum(len(v) for v in buckets.values())
    if total < args.target:
        extra = claim(near_cands + far_cands + dis_cands, args.target - total)
        for i in extra:
            if H is not None and consensus[i] is not None:
                cy = image_to_court(H, [consensus[i]])[0][1]
                buckets["far" if cy > court.NET_Y else "near"].append(i)
            else:
                buckets["near"].append(i)

    write_outputs(args, manifest_path, frames_dir, video_path, buckets,
                  step, n_video, fps, width, height)


def write_outputs(args, manifest_path: Path, frames_dir: Path,
                  video_path: Path, buckets: dict[str, list[int]],
                  step: int, n_video: int, fps: float,
                  width: int, height: int) -> None:
    frames = sorted(
        ({"frame": i * step, "bucket": name}
         for name, idxs in buckets.items() for i in idxs),
        key=lambda r: r["frame"],
    )

    sha1 = hashlib.sha1()
    with open(video_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha1.update(chunk)

    manifest = {
        "clip": args.clip,
        "video": args.video,
        "video_sha1": sha1.hexdigest(),
        "width": width, "height": height, "fps": fps,
        "video_frames": n_video,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": {
            "target": args.target, "frame_step": step,
            "static_step_px": STATIC_STEP_PX, "static_min_run": STATIC_MIN_RUN,
            "disagree_px": DISAGREE_PX,
            "caches": args.caches, "match": args.match,
            "keypoints": args.keypoints,
        },
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "frames": frames,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    extract(video_path, frames_dir, [r["frame"] for r in frames])

    print(f"wrote {manifest_path}")
    print(f"extracted {len(frames)} frames -> {frames_dir}")
    for k, v in manifest["bucket_counts"].items():
        print(f"  {k:9s} {v}")


def extract(video_path: Path, frames_dir: Path, frame_numbers: list[int]) -> None:
    """Single sequential decode pass — exact frames, no codec seek drift."""
    import cv2

    wanted = set(frame_numbers)
    frames_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    i, done = 0, 0
    while done < len(wanted):
        ok, frame = cap.read()
        if not ok:
            break
        if i in wanted:
            cv2.imwrite(str(frames_dir / f"f{i:05d}.jpg"), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            done += 1
        i += 1
    cap.release()
    if done < len(wanted):
        raise SystemExit(f"video ended early: got {done}/{len(wanted)} frames")


if __name__ == "__main__":
    main()
