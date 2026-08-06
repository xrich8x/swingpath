"""run.py — CLI entry point.

    python run.py demo --out ../frontend/src/data/sample_match.json
    python run.py analyze match.mp4 --keypoints my_court_pts.json --out ../data/output/match.json

`demo` writes synthetic data (no model weights). `analyze` runs the real path:
calibration is ready; the perception loop is the stubbed seam (see pipeline.py).
"""

from __future__ import annotations

import argparse
import os
import sys

from swingvision import pipeline


def _cmd_demo(args: argparse.Namespace) -> int:
    match = pipeline.write_demo_match(args.out, seed=args.seed)
    s = match.stats
    print(f"Wrote demo match -> {args.out}")
    print(
        f"  {s.shot_count} shots across {s.rally_count} rallies; "
        f"avg {s.avg_speed_kmh} km/h, top {s.top_speed_kmh} km/h"
    )
    print(f"  score: {match.score.final}  (in {len(match.score.timeline)} points)")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    if args.score_thresh is not None:
        # Env hook rather than a threaded argument: the detector is constructed
        # in several places inside the pipeline (main, far-court tile, probe) and
        # a flag that reached only some of them would produce a run that is half
        # one operating point and half another. Stamped into the cache
        # provenance, so a stale cache from another threshold is reported.
        os.environ["BALLNET_SCORE_THRESH"] = str(args.score_thresh)
    match = pipeline.analyze_video(
        args.video,
        keypoints_path=args.keypoints,
        out_path=args.out,
        pose_quality=args.pose_quality,
        pose_every=args.pose_every,
        max_frames=args.max_frames,
        frame_step=args.frame_step,
        camera_hfov_deg=args.camera_hfov,
        use_bgsub=not args.no_bgsub,
        ball_model=args.ball_model,
        annotate=args.annotate,
        doubles=args.doubles,
        far_player_rescue=args.far_player_rescue,
        far_ball_tile=args.far_ball_tile,
        device=args.device,
    )
    s = match.stats
    print(
        f"  {s.shot_count} shots, {s.rally_count} rallies; "
        f"avg {s.avg_speed_kmh} km/h, top {s.top_speed_kmh} km/h; "
        f"calls in/out = {s.line_calls['in']}/{s.line_calls['out']}"
    )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Pre-flight: grade the court framing before analyzing (SwingVision-style:
    a good, full-court setup is what makes the rest reliable)."""
    import json

    import cv2

    from swingvision import calibration

    cap = cv2.VideoCapture(args.video)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        print(f"could not read {args.video}")
        return 1

    H, src = None, ""
    if args.keypoints:
        with open(args.keypoints, "r", encoding="utf-8") as f:
            H = calibration.homography_from_landmarks(json.load(f))
        src = "your corners"
    else:
        det = (calibration.detect_court_learned(frame, weights=args.court_weights,
                                                verify=False)
               or calibration.detect_court(frame))
        if det is not None:
            H, src = det.homography, "auto-detected court"

    if H is None:
        print("Framing check: could NOT find the court automatically.")
        print("  - The whole court is probably not in view, or the lines are unclear.")
        print("  - Fix: set corners manually (--keypoints), or re-record with the full")
        print("    court in frame, camera ~5 ft up behind the baseline.")
        return 0

    r = calibration.framing_report(frame, H)
    label = {"good": "OK", "warn": "WARN", "poor": "POOR"}[r.level]
    print(f"Framing check ({src}): [{label}]  corners {r.corners_visible}/4 in frame, "
          f"centred {r.centrality:.2f}, lines {r.coverage:.2f}, elevation {r.elevation:.2f}")
    for m in r.messages:
        print(f"  - {m}")
    return 0


def _cmd_live(args: argparse.Namespace) -> int:
    import json

    from swingvision import calibration, live
    from swingvision.ball import BallDetector

    with open(args.keypoints, "r", encoding="utf-8") as f:
        H = calibration.homography_from_landmarks(json.load(f))
    bd = BallDetector(args.ball_weights, device=args.device)

    def on_call(c):
        print(f"  t={c.t_s:6.2f}s  {c.call.upper():3s}  ({c.margin_m:+.2f} m from line)  "
              f"at ({c.xy[0]:.1f}, {c.xy[1]:.1f}) m", flush=True)

    print("[live] calling lines as bounces are detected (Ctrl-C to stop)...")
    live.stream(args.video, H, lambda i, frame: bd.detect(frame),
                out_path=args.out, singles=not args.doubles, on_call=on_call)
    return 0


def _cmd_correct(args: argparse.Namespace) -> int:
    """Apply a corrections file and re-derive score + stats.

    Vision scoring is brittle by construction — a rally winner rests on a bounce a
    single camera cannot always place. This is the documented answer: let the
    person who watched the match overrule it, then recompute rather than patch.
    """
    import json

    from swingvision import corrections as corr

    with open(args.match, "r", encoding="utf-8") as f:
        match = json.load(f)
    with open(args.corrections, "r", encoding="utf-8") as f:
        blob = json.load(f)
    items = blob["corrections"] if isinstance(blob, dict) else blob

    fixed, res = corr.apply_corrections(match, items, strict=args.strict)
    d = corr.diff_summary(match, fixed)

    out = args.out or os.path.splitext(args.match)[0] + ".corrected.json"
    # Record what was applied INSIDE the output, so a corrected match.json is
    # self-describing: anyone opening it can see it was edited, and by what.
    fixed["corrections"] = res.applied
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fixed, f, indent=1)

    print(f"applied {len(res.applied)} correction(s); {len(res.skipped)} skipped")
    for s in res.skipped:
        print(f"  SKIPPED {s.get('target')} id={s.get('id')}: {s.get('reason')}")
    for a in res.applied:
        print(f"  {a['target']} id={a['id']}: {a.get('was')!r} -> {a['value']!r}")
    if d["score_changed"]:
        print(f"score: {d['final_before']}  ->  {d['final_after']}")
    else:
        print(f"score unchanged ({d['final_after']})")
    if d["line_calls_before"] != d["line_calls_after"]:
        print(f"line calls: {d['line_calls_before']} -> {d['line_calls_after']}")
    print(f"wrote {out}")
    return 0 if res.ok or not args.strict else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run.py", description="SwingVision-clone CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="write synthetic demo match.json (no weights)")
    demo.add_argument("--out", required=True, help="output match.json path")
    demo.add_argument("--seed", type=int, default=7, help="RNG seed for reproducibility")
    demo.set_defaults(func=_cmd_demo)

    analyze = sub.add_parser("analyze", help="analyze a real clip (perception stubbed)")
    analyze.add_argument("video", help="input video path")
    analyze.add_argument("--keypoints", help="manual calibration JSON {landmark: [x_px, y_px]}")
    analyze.add_argument("--out", help="output match.json path")
    analyze.add_argument("--pose-quality", default="fast",
                         choices=["fast", "balanced", "accurate"], dest="pose_quality",
                         help="pose speed/accuracy: fast (~0.4s/frame) .. accurate (small far player)")
    analyze.add_argument("--pose-every", type=int, default=3, dest="pose_every",
                         help="run pose every Nth frame (CPU budget)")
    analyze.add_argument("--max-frames", type=int, default=None, dest="max_frames",
                         help="limit source frames processed (for quick tests)")
    analyze.add_argument("--frame-step", default="auto", dest="frame_step",
                         help="process every Nth frame; 'auto' targets ~30fps")
    analyze.add_argument("--camera-hfov", type=float, default=None, dest="camera_hfov",
                         help="horizontal field of view (deg) for speed/spin; default: "
                              "self-calibrated from the court homography (phone ~70, broadcast ~28)")
    analyze.add_argument("--no-bgsub", action="store_true", dest="no_bgsub",
                         help="disable fixed-camera background-subtraction ball recovery "
                              "(use for panning/handheld footage)")
    analyze.add_argument("--device", default="cpu",
                         help="inference device for ball+pose: cpu or cuda")
    analyze.add_argument("--ball-model", default="auto", dest="ball_model",
                         choices=["auto", "tracknet", "wasb", "fusion", "ours", "all"],
                         help="ball detector: auto (default; probes the clip and picks — "
                              "tracknet suits broadcast, wasb suits amateur/720p), force "
                              "tracknet | wasb | fusion, or ours (weights/ballnet.pt, "
                              "trained on this project's own data via train_ballnet.py)")
    analyze.add_argument("--score-thresh", type=float, default=None,
                         dest="score_thresh",
                         help="ball detector accept threshold (default 0.5). Higher "
                              "is stricter: fewer false locks, less far-court recall. "
                              "Swept against human gold clicks with "
                              "tools/eval_detector_gold.py --score-thresh")
    analyze.add_argument("--annotate", action="store_true", dest="annotate",
                         help="also render an annotated overlay video (court + players + "
                              "ball + shot labels) next to the match.json")
    analyze.add_argument("--far-player-rescue", action="store_true",
                         dest="far_player_rescue",
                         help="run a second, accurate pose pass on a native-resolution "
                              "crop of the far court when the far player is missing "
                              "(they subtend ~45px and whole-frame inference loses them)")
    analyze.add_argument("--far-ball-tile", action="store_true", dest="far_ball_tile",
                         help="also run the ball detector on a native-resolution "
                              "crop of the far court (far ball is ~4px; the model "
                              "sees ~2px after downscaling). ~2x slower.")
    analyze.add_argument("--doubles", action="store_true", dest="doubles",
                         help="force doubles line calls (outer alleys). Default: "
                              "auto-detect singles vs doubles from on-court player "
                              "count. Either way, player tracking resolves two players")
    analyze.set_defaults(func=_cmd_analyze)

    check = sub.add_parser("check", help="pre-flight: grade your court framing before analyzing")
    check.add_argument("video", help="input video path")
    check.add_argument("--keypoints", help="court calibration JSON (else auto-detect the court)")
    check.add_argument("--court-weights", default="weights/court_detector.pt",
                       dest="court_weights", help="learned court model checkpoint")
    check.set_defaults(func=_cmd_check)

    live_p = sub.add_parser("live", help="stream live IN/OUT line calls from a video or webcam")
    live_p.add_argument("video", help="video path, or 0 for a webcam")
    live_p.add_argument("--keypoints", required=True, help="court calibration JSON")
    live_p.add_argument("--out", help="optional annotated output video path")
    live_p.add_argument("--ball-weights", default="weights/tracknet.pt", dest="ball_weights")
    live_p.add_argument("--device", default="cpu", help="cpu or cuda (cuda gives real-time)")
    live_p.add_argument("--doubles", action="store_true", help="call against the doubles court")
    live_p.set_defaults(func=_cmd_live)

    corr = sub.add_parser("correct",
                          help="apply human corrections to a match.json and re-derive "
                               "the score and stats")
    corr.add_argument("match", help="match.json to correct")
    corr.add_argument("--corrections", required=True,
                      help="corrections JSON (a list, or {\"corrections\": [...]}) — "
                           "the Review tab in the dashboard exports this")
    corr.add_argument("--out", help="output match.json (default: alongside, .corrected.json)")
    corr.add_argument("--strict", action="store_true",
                      help="fail on any correction that cannot be applied, instead of "
                           "reporting it")
    corr.set_defaults(func=_cmd_correct)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
