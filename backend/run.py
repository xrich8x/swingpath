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
    """Pre-flight: grade the court setup before analyzing (SwingVision-style:
    a good, full-court setup is what makes the rest reliable).

    Two rules shape this command.

    PREDICT BY INVOKING, NEVER BY RE-DERIVING (trap 15). This used to read ONE
    frame and run detect_court_learned -> detect_court, while `analyze` runs
    `courtfit.fit_video_frames` consensus over 8 frames and only accepts >=6
    agreeing. A pre-flight on a different, weaker path can refuse a clip that
    analyzes fine, or bless one that does not — so it now calls
    `pipeline.calibrate_video`, the exact entry point analyze calls. Everything
    reported here (source, reprojection error, refusal text) is therefore what
    analyze will do, not a second opinion about it.

    QUOTE THE MEASURED ERROR, NOT THE GEOMETRIC PROXY. The old output ended at
    "elevation 0.42" — a 0-1 framing score. What actually decides whether this
    recording is worth making is `calibration.expected_call_accuracy`: the
    measured share of NEAR-THE-LINE calls a mount at this height gets right
    (54% at 1.0 m, 81% at 8 m; tools/height_curve.py, data/output/height_curve.md).
    It is quoted beside CALL_MAJORITY_FLOOR_PCT because the floor is not 50% —
    always answering "in" scores 56.2%, so a 1.0 m mount is worth LESS than a
    constant answer, which "elevation 0.42" could never say.
    """
    import cv2

    from swingvision import calibration, court, courtfit, pipeline

    cap = cv2.VideoCapture(args.video)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        print(f"could not read {args.video}")
        return 1

    print("Framing check: running the same calibration `analyze` runs...")
    try:
        _H, err, source, named = pipeline.calibrate_video(
            args.video, keypoints_path=args.keypoints)[:4]
    except ValueError as exc:
        # calibrate_video refuses with the exact overlay-tool command. analyze
        # would stop here too, so report it verbatim rather than paraphrasing.
        # ASCII only: this prints to a Windows console (cp1252), where an em-dash
        # renders as a replacement character.
        print("\nFraming check: [REFUSED] - `analyze` would stop on this clip.\n")
        print(f"  {exc}")
        return 0
    except FileNotFoundError as exc:
        print(f"\nFraming check: could not calibrate — {exc}")
        return 1

    v = courtfit.setup_verdict(frame, named, calibration, court)
    view, angle = v["view"], v["angle"]
    worst = "poor" if "poor" in (view["level"], angle["level"]) else (
        "warn" if "warn" in (view["level"], angle["level"]) else "good")
    label = {"good": "OK", "warn": "WARN", "poor": "POOR"}[worst]

    print(f"\nFraming check: [{label}]   source={source}, reprojection {err:.2f} px\n")
    print(f"  View    corners {view['corners_visible']}/4 in frame, "
          f"centred {view['centrality']:.2f}, lines {view['coverage']:.2f}")
    print(f"          {view['msg']}")

    if angle.get("height_m") is not None:
        print(f"\n  Camera  {angle['height_m']:.2f} m up, {angle['hfov_deg']:.0f} deg lens, "
              f"roll {angle['roll_deg']:+.1f} deg")
        print(f"          ~{angle['reliable_frac'] * 100:.0f}% of the court is measurable "
              f"(reliable to ~{angle['reliable_to_m']:.1f} m of {court.LENGTH:.1f} m)")

    call_pct, floor = angle.get("call_accuracy_pct"), angle.get("call_floor_pct")
    if call_pct is not None:
        print(f"\n  Calls   ~{call_pct:.0f}% of close calls correct at this mount height")
        print(f"          floor is {floor:.0f}% - that is what always answering "
              f'"in" scores')
        if call_pct <= floor + 1.0:
            print(f"          *** THIS MOUNT ADDS NOTHING: {call_pct:.0f}% vs a "
                  f"{floor:.0f}% floor. Raise the camera before recording. ***")
        else:
            print(f"          so this mount is worth ~{call_pct - floor:.0f} points "
                  f"over guessing")
        # RULE 2 (ML_PRACTICES): state what the number was measured against, in
        # one sentence. Without this the figure reads as a measurement of THIS
        # clip. It is not - it is a function of camera height alone, read off a
        # curve built from simulated flights, and the clip's own footage never
        # enters it. Only the height does, and that came from the corner fit.
        print(f"          [measured against simulated flights with a known bounce, "
              f"on calls within")
        print(f"           0.5 m of a line; 6 m setback, 100 deg lens, 720p, 30 fps, "
              f"30% dropout.")
        print(f"           A function of HEIGHT, not of this clip - real clips land "
              f"within ~3 points.")
        print(f"           tools/height_curve.py, data/output/height_curve.md]")
    else:
        print("\n  Calls   not estimated - no physical camera fits this court shape, "
              "so the height is unknown")

    print(f"\n  {angle['msg']}")
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


def _cmd_highlights(args: argparse.Namespace) -> int:
    """Cut a match into per-rally clips + an optional top-3 reel.

    Dead time is most of a phone recording, and every rally boundary is already
    in the match.json — so this is bookkeeping over data we have, not analysis.
    """
    import json

    from swingvision import highlights as hl

    with open(args.match, "r", encoding="utf-8") as f:
        match = json.load(f)

    out_dir = args.out_dir or os.path.join(
        os.path.dirname(args.match) or ".", "rallies")
    man = hl.cut_clips(args.video, match, out_dir, top_n=args.top,
                       reel=args.reel, exact=args.exact)

    made = [c for c in man["clips"] if c.get("ok")]
    print(f"wrote {len(made)} clip(s) -> {out_dir}  ({man['mode']})")
    for c in man["clips"]:
        if c.get("skipped"):
            print(f"  rally {c['rally_id']}: SKIPPED — {c['skipped']}")
        elif not c.get("ok"):
            print(f"  rally {c['rally_id']}: FAILED to cut")
    for rid in man["top"]:
        c = next(x for x in man["clips"] if x["rally_id"] == rid)
        print(f"  #{c['rank']}  {c['file']}  {c['why']}")

    # The property that matters, and it is now CHECKED rather than hoped for:
    # every clip must fully contain its rally. Cutting on a keyframe makes both
    # ends exact, so this compares real numbers, not a container offset that was
    # always ~0 and made the test pass vacuously.
    late = [c for c in made if c["start_s"] > c["rally_start_s"] + 1e-3]
    short = [c for c in made if c["end_s"] < c["rally_end_s"] - 1e-3]
    if late or short:
        if late:
            print(f"  WARNING: {len(late)} clip(s) open INSIDE the rally")
        if short:
            print(f"  WARNING: {len(short)} clip(s) end BEFORE the rally does")
    elif made:
        lead = sorted(c["lead_in_s"] for c in made)
        print(f"  verified: all {len(made)} clips contain their whole rally "
              f"(lead-in {lead[0]:.1f}-{lead[-1]:.1f}s, median "
              f"{lead[len(lead)//2]:.1f}s)")

    if man.get("reel"):
        print(f"  reel -> {os.path.join(out_dir, man['reel'])}")
    elif args.reel:
        print("  reel: not made (needs at least 2 successful clips)")
    return 0


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

    check = sub.add_parser("check", help="pre-flight: grade your court setup, and what "
                                         "your mount height costs in line-call accuracy")
    check.add_argument("video", help="input video path")
    check.add_argument("--keypoints", help="court calibration JSON (else auto-detect the court)")
    # NO --court-weights here on purpose. `analyze` has no such flag, and this
    # command's whole job is to predict `analyze`. A checkpoint override that
    # only check honoured would reintroduce exactly the divergence being fixed.
    # To point the learned tier at another checkpoint, set COURTNET_WEIGHTS —
    # both commands read it, so they stay in step.
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

    hi = sub.add_parser("highlights",
                        help="cut per-rally clips (+ optional top-3 reel) from a "
                             "video and its match.json")
    hi.add_argument("video", help="the source video the match.json was made from")
    hi.add_argument("--match", required=True, help="match.json for this video")
    hi.add_argument("--out-dir", dest="out_dir",
                    help="where to write clips (default: rallies/ next to the match)")
    hi.add_argument("--top", type=int, default=3,
                    help="how many rallies count as 'top' (default 3)")
    hi.add_argument("--reel", action="store_true",
                    help="also concat the top rallies into one highlights.mp4")
    hi.add_argument("--exact", action="store_true",
                    help="re-encode for a frame-accurate trim instead of stream "
                         "copy. 5-10x slower; only needed when the exact start "
                         "matters, since the default can only start EARLIER")
    hi.set_defaults(func=_cmd_highlights)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
