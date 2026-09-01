"""live_replay_novideo.py — drive the Python live-call reference with NO video.

`live_demo.py replay` still requires `--video` even though the ball positions
come from a cache, because it hands the frame loop to `live.stream()`, which
opens the video with cv2.VideoCapture just to (a) learn fps and iterate frame
indices and (b) draw an annotated output video. Neither of those needs pixels:
`LiveAnalyzer.push_position(ball_px, t_s)` (backend/swingvision/live.py) is a
pure function of a ball pixel and a timestamp — no frame, no cv2, no renderer.
This script calls it directly, replicating stream()'s loop body only:

    for i, ball_px_i in enumerate(cached_ball_px):
        call = analyzer.push_position(ball_px_i, i / fps)

That is a faithful re-implementation of the reference, not a new algorithm —
compare line-for-line against `live.stream()` and `live_demo.py`'s replay
lambda. It is only valid when the cached track's length already equals the
source video's frame count, so this script CHECKS that against fps/duration
in the match.json sidecar rather than assuming it; see --match-json.

This exists because data/tennis_sample.mp4 is not in the repo, so
`live_demo.py replay` cannot run at all. This script is how the Python
reference gets exercised without it. It changes no behaviour in live.py.

Usage:
    python live_replay_novideo.py \
        --keypoints ../data/court_pts_refined.json \
        --cache ../data/output/real_match.perception.json \
        --match-json ../data/output/real_match.json \
        --fps 30.0 --singles
"""

from __future__ import annotations

import argparse
import json

from swingvision import calibration, live


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keypoints", required=True, help="calibration JSON (named landmark px)")
    ap.add_argument("--cache", required=True, help="perception.json with ball_px")
    ap.add_argument("--match-json", default=None,
                    help="optional match.json to CROSS-CHECK len(ball_px) against "
                         "video.duration_s * video.fps before trusting the frame count")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--singles", action="store_true", default=True)
    ap.add_argument("--json-out", default=None, help="write the call list as JSON")
    args = ap.parse_args()

    with open(args.keypoints, "r", encoding="utf-8") as f:
        H = calibration.homography_from_landmarks(json.load(f))

    ball_px = json.load(open(args.cache, encoding="utf-8"))["ball_px"]

    if args.match_json:
        mj = json.load(open(args.match_json, encoding="utf-8"))
        v = mj.get("video", {})
        expected = round(v.get("duration_s", 0.0) * v.get("fps", 0.0))
        if expected != len(ball_px):
            raise SystemExit(
                f"REFUSING: ball_px has {len(ball_px)} entries but "
                f"{args.match_json} implies {expected} frames "
                f"(duration_s={v.get('duration_s')} * fps={v.get('fps')}) — "
                f"the no-video frame-count assumption does not hold here."
            )
        if v.get("fps") and abs(v["fps"] - args.fps) > 1e-9:
            raise SystemExit(
                f"REFUSING: --fps {args.fps} != {args.match_json}'s video.fps "
                f"{v['fps']}; pass --fps {v['fps']}"
            )
        print(f"[cross-check] {args.match_json}: video.fps={v.get('fps')} "
              f"duration_s={v.get('duration_s')} -> {expected} frames "
              f"== len(ball_px)={len(ball_px)}. OK.")

    la = live.LiveAnalyzer(H, singles=args.singles)
    for i, px in enumerate(ball_px):
        pos = tuple(px) if px else None
        la.push_position(pos, i / args.fps)

    n_in = sum(c.call == "in" for c in la.calls)
    print(f"\n[live_replay_novideo] Python reference — {len(la.calls)} calls "
          f"({n_in} in / {len(la.calls) - n_in} out)\n")
    for c in la.calls:
        print(f"  t={c.t_s:6.2f}s  {c.call.upper():3s}  ({c.margin_m:+.3f} m from line)  "
              f"at ({c.xy[0]:.3f}, {c.xy[1]:.3f}) m")

    if args.json_out:
        out = [
            {"t_s": c.t_s, "xy": c.xy, "call": c.call, "margin_m": c.margin_m}
            for c in la.calls
        ]
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
