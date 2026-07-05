"""Demo the live line-call path.

  # Replay a cached ball track (instant, no inference) — proves the live calling:
  python live_demo.py replay --video ../data/tennis_sample.mp4 \
      --keypoints ../data/court_pts.json --cache ../data/output/real_match.perception.json

  # True streaming (runs TrackNet per frame, ~1.4fps on CPU) — same as `run.py live`:
  python live_demo.py stream --video ../data/tennis_sample.mp4 \
      --keypoints ../data/court_pts.json
"""

from __future__ import annotations

import argparse
import json

from swingvision import calibration, live


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["replay", "stream"])
    ap.add_argument("--video", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--cache", help="perception.json with ball_px (replay mode)")
    ap.add_argument("--out", default="../data/output/live_calls.mp4")
    args = ap.parse_args()

    with open(args.keypoints, "r", encoding="utf-8") as f:
        H = calibration.homography_from_landmarks(json.load(f))

    if args.mode == "replay":
        ball_px = json.load(open(args.cache))["ball_px"]
        source = lambda i, frame: (tuple(ball_px[i]) if i < len(ball_px) and ball_px[i] else None)
    else:
        from swingvision.ball import BallDetector
        bd = BallDetector("weights/tracknet.pt")
        source = lambda i, frame: bd.detect(frame)

    def on_call(c):
        print(f"  t={c.t_s:6.2f}s  {c.call.upper():3s}  ({c.margin_m:+.2f} m from line)  "
              f"at ({c.xy[0]:.1f}, {c.xy[1]:.1f}) m", flush=True)

    print(f"[live] {args.mode} — calling lines as bounces are detected:\n")
    live.stream(args.video, H, source, out_path=args.out, on_call=on_call)
    print(f"annotated video -> {args.out}")


if __name__ == "__main__":
    main()
