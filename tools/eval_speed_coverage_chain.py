"""eval_speed_coverage_chain.py — per-stage SPEED-COVERAGE attribution.

The metric is the one that actually gates a reported speed:

    seen_frac = real_fraction(hit, landing)      # pipeline.py, inside
    speed_confident requires seen_frac >= 0.5    # _build_match_from_events

`data/output/post_bounce_chain.md` part 3 attributes the loss of that number to
each chain stage, but there was no tool: it was a one-off, and `real_fraction`
is a closure inside `_build_match_from_events`. This is the tool.

WHAT IT DOES, and the two design decisions that make the attribution honest:

1. **The spans are FIXED.** `hit_idx` / `bounce_idx` / `track` are computed ONCE,
   from the FULL shipped chain, exactly as `pipeline.analyze_video` does. Every
   stage is then scored over those same spans by handing
   `_build_match_from_events` a different `ball_seen` mask. If the spans moved
   per stage the table would be comparing different shot populations and the
   per-stage deltas would mean nothing. The shot COUNT is therefore identical on
   every row, which is also true of the published table (120 / 196).

2. **The stages are INVOKED, not re-derived** (trap T15). The order below is
   copied from `pipeline.analyze_video`'s ball section and must stay that way:

       remove_outliers -> rectify_track -> suppress_false_locks
       -> gate_ball_to_court -> smooth_forecast

   and `seen` is `p is not None` before the smoother, `p is not None and not
   coasted[i]` after it — a coasted frame is DRAWN but was not SEEN.

WHAT EACH NUMBER IS MEASURED AGAINST: `seen_frac` is measured on the tracker's
own output over spans the tracker's own events defined. It is a COVERAGE
statistic, not an accuracy one, and nothing here is evidence that a seen frame
was on the ball. Recall/ghost claims for these same detectors live in
`tools/eval_model_filters.py`, which scores against human gold clicks.

  backend/.venv/Scripts/python.exe tools/eval_speed_coverage_chain.py \
      --clip am_hard_utr \
      --ball-cache data/output/detector_ab/am_hard_utr.tracknet.perception.json \
      --label tracknet --json data/output/speed_coverage_amhard_tracknet.json

`--pose-cache` defaults to the clip's standard perception cache: pose, camera
motion and the player court tracks are DETECTOR-INDEPENDENT, so sharing them
across the two arms is what keeps the A/B to one variable. The ball track is the
only thing that comes from `--ball-cache`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

sys.path.insert(0, str(REPO / "tools"))

import _goldset as gs  # noqa: E402  — the registry resolves videos by BASENAME
import cv2  # noqa: E402

STAGES = ("raw", "rectify", "suppress", "gate", "smooth")
STAGE_LABEL = {
    "raw": "raw (tracker out)",
    "rectify": "+ rectify_track",
    "suppress": "+ suppress_false_locks",
    "gate": "+ gate_ball_to_court",
    "smooth": "+ smooth_forecast",
}

# clip -> (video, keypoints json, default pose/perception cache)
CLIPS = {
    name: (gs.find_video(f"{name}.mp4"), f"data/{name}_pts.json",
           f"data/output/{name}.perception.json")
    for name in ("am_hard_utr", "yt_match40")
}


def _as_xy(p):
    return None if p is None else (float(p[0]), float(p[1]))


def build_stage_tracks(ball_px, *, fps_eff, width, height, H, hfov):
    """The shipped chain, stage by stage. Returns {stage: (track, coasted)}.

    Mirrors pipeline.analyze_video exactly, `remove_outliers` included — it runs
    immediately before `rectify_track` there and is folded into that row here,
    the same grouping tools/eval_model_filters.py uses.
    """
    from swingvision import ball as ball_mod

    res_scale = height / 720.0
    out = {}
    raw = [_as_xy(p) for p in ball_px]
    out["raw"] = (list(raw), [False] * len(raw))

    tr = ball_mod.remove_outliers(list(raw), max_jump=max(width, height) * 0.06)
    tr = ball_mod.rectify_track(tr, max_speed_px=3000.0 * res_scale / fps_eff,
                                resid_px=35.0 * res_scale)
    out["rectify"] = (list(tr), [False] * len(tr))

    tr = ball_mod.suppress_false_locks(tr, fps_eff=fps_eff, res_scale=res_scale)
    out["suppress"] = (list(tr), [False] * len(tr))

    if H is not None:
        tr = ball_mod.gate_ball_to_court(tr, H, (width, height), hfov_deg=hfov)
    out["gate"] = (list(tr), [False] * len(tr))

    tr, coasted, _conf = ball_mod.smooth_forecast(tr, fps_eff=fps_eff,
                                                  res_scale=res_scale)
    out["smooth"] = (list(tr), list(coasted))
    return out


def seen_mask(track, coasted):
    """`ball_seen` — the image-space "the detector actually had the ball here".

    Same definition as pipeline.analyze_video: a coasted frame is a physics
    guess, not a measurement, so it is drawn but not seen.
    """
    return [p is not None and not coasted[i] for i, p in enumerate(track)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", required=True, choices=list(CLIPS))
    ap.add_argument("--ball-cache", required=True,
                    help="perception cache supplying ball_px (the ARM)")
    ap.add_argument("--pose-cache", default=None,
                    help="perception cache supplying pose / cam_motion / player "
                         "court tracks (detector-independent; defaults to the "
                         "clip's standard cache)")
    ap.add_argument("--label", required=True,
                    help="arm name, stamped into the artifact (e.g. tracknet)")
    ap.add_argument("--spans-from", default=None,
                    help="ball cache whose FULL chain defines the hit->landing "
                         "spans, when that should NOT be --ball-cache. Cross-check "
                         "only: pointing both arms at ONE span source removes the "
                         "shot-population difference between detectors, so the "
                         "per-stage deltas are compared on identical shots. The "
                         "primary measurement leaves this unset, because the "
                         "shipped product scores each detector on the shots that "
                         "detector's own events produced.")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    from swingvision import calibration, events, pipeline
    from swingvision import ball as ball_mod
    from swingvision.ball import smooth_and_fill

    video_rel, pts_rel, pose_default = CLIPS[args.clip]
    video = str(REPO / video_rel)
    ball_cache = json.loads(Path(args.ball_cache).read_text(encoding="utf-8"))
    pose_path = args.pose_cache or str(REPO / pose_default)
    pose_cache = json.loads(Path(pose_path).read_text(encoding="utf-8"))

    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    step = int(ball_cache.get("frame_step") or 1)
    pose_step = int(pose_cache.get("frame_step") or 1)
    if step != pose_step:
        raise SystemExit(f"frame_step mismatch: ball={step} pose={pose_step}. The "
                         f"two caches index different frames; refusing to pair them.")
    fps_eff = fps / step

    # Calibration EXACTLY as the pipeline gets it. Two traps ride on this: the
    # court-region gate takes a much tighter fallback rung when hfov is None (a
    # cache-provenance artefact, not the shipped behaviour), and res_scale.
    H, err, source, named_corners, cam_hfov_deg, lens_k1, H_und = \
        pipeline.calibrate_video(video, str(REPO / pts_rel), None)
    camera_hfov_deg = None
    if cam_hfov_deg is not None:
        camera_hfov_deg = float(cam_hfov_deg)
    if camera_hfov_deg is None:
        f_est = (calibration.focal_from_homography(H, (width, height))
                 if H is not None else None)
        camera_hfov_deg = (calibration.hfov_from_focal(f_est, width) if f_est
                           else 70.0)
    H_metric = H_und if lens_k1 else H

    ball_raw = ball_cache["ball_px"]
    near_court = pose_cache["near_court"]
    far_court = pose_cache["far_court"]
    near_kpts = pose_cache["near_kpts"]
    far_kpts = pose_cache["far_kpts"]
    cam_motion = pose_cache.get("cam_motion") or []
    n = len(ball_raw)
    if len(near_kpts) != n:
        raise SystemExit(f"frame-count mismatch: ball={n} pose={len(near_kpts)}")

    near_court, near_kpts = pipeline._reject_static_player(near_court, near_kpts, "near")
    far_court, far_kpts = pipeline._reject_static_player(far_court, far_kpts, "far")

    cam_inv = [np.linalg.inv(pipeline._cam_row_to_A(row)) for row in cam_motion]

    def unwarp(px, i):
        if not cam_inv or i >= len(cam_inv):
            return px
        q = cam_inv[i] @ np.array([px[0], px[1], 1.0])
        return (q[0] / q[2], q[1] / q[2])

    def und(px):
        if not lens_k1 or px is None:
            return px
        q = calibration.undistort_points([px], lens_k1, (width, height))[0]
        return (float(q[0]), float(q[1]))

    print(f"{args.clip} [{args.label}] {width}x{height} @ {fps:.0f}fps step={step} "
          f"fps_eff={fps_eff:.1f} hfov={camera_hfov_deg:.1f} lens_k1={lens_k1} "
          f"frames={n}", flush=True)
    print(f"  ball  <- {Path(args.ball_cache).name}  "
          f"({sum(p is not None for p in ball_raw)} raw locks)")
    print(f"  pose  <- {Path(pose_path).name}", flush=True)

    stage_tracks = build_stage_tracks(ball_raw, fps_eff=fps_eff, width=width,
                                      height=height, H=H, hfov=camera_hfov_deg)

    # --- the FULL chain defines the spans, once ---------------------------------
    span_tracks = stage_tracks
    if args.spans_from:
        sp_cache = json.loads(Path(args.spans_from).read_text(encoding="utf-8"))
        if len(sp_cache["ball_px"]) != n:
            raise SystemExit("--spans-from cache has a different frame count")
        span_tracks = build_stage_tracks(sp_cache["ball_px"], fps_eff=fps_eff,
                                         width=width, height=height, H=H,
                                         hfov=camera_hfov_deg)
        print(f"  spans <- {Path(args.spans_from).name} (CROSS-CHECK: the shot "
              f"population comes from a different detector than the stages)",
              flush=True)
    ball_px, ball_coasted = span_tracks["smooth"]
    RUNOFF_M = 2.5
    ball_court_raw, ball_conf = [], []
    for i, px in enumerate(ball_px):
        if px is None:
            ball_court_raw.append(None); ball_conf.append(None); continue
        p0 = und(unwarp(px, i))
        x, y = calibration.image_to_court(H_metric, [p0])[0]
        from swingvision import court as court_mod
        if (-RUNOFF_M <= x <= court_mod.DOUBLES_WIDTH + RUNOFF_M
                and -RUNOFF_M <= y <= court_mod.LENGTH + RUNOFF_M):
            ball_court_raw.append([float(x), float(y)])
            ball_conf.append(calibration.court_scale_m_per_px(H_metric, p0))
        else:
            ball_court_raw.append(None); ball_conf.append(None)
    ball_valid = [p is not None for p in ball_px]
    ball_court_raw = ball_mod.cap_court_jumps(ball_court_raw, max_step_m=84.0 / fps_eff)
    smoothed = smooth_and_fill(ball_court_raw, window=7, polyorder=2)
    track = [(i / fps_eff, float(smoothed[i, 0]), float(smoothed[i, 1]))
             for i in range(n)]

    ball_gap = events.ball_player_gap(ball_px, near_kpts, far_kpts, n)
    if np.isfinite(ball_gap).sum() >= 0.15 * n:
        hit_idx = sorted(events.detect_hits_hybrid(ball_gap, track))
        hit_idx = events.drop_midflight_hits(hit_idx, track)
        bounce_idx = sorted(events.detect_bounces_between_hits(
            ball_px, hit_idx, n, track=track))
        events_src = "gap+between"
    else:
        hit_idx = sorted(events.detect_hits(track, angle_thresh_deg=70, min_gap_s=0.3))
        bounce_idx = sorted(events.detect_bounces(track, min_speed_drop=0.55))
        events_src = "angle+speedmin (no pose)"
    hit_idx = events.drop_events_without_ball(hit_idx, ball_valid)
    bounce_idx = events.drop_events_without_ball(bounce_idx, ball_valid)
    if not hit_idx:
        hit_idx = [0]
    print(f"  events: {len(hit_idx)} hits, {len(bounce_idx)} bounces [{events_src}]",
          flush=True)

    # --- score every stage over those FIXED spans -------------------------------
    rows, prev_mean, n_shots = [], None, None
    print(f"\n    {'stage':<26}{'mean seen_frac':>15}{'delta':>8}"
          f"{'shots>=50%':>12}{'delta':>8}")
    print("-" * 71)
    prev_pass = None
    for st in STAGES:
        tr, co = stage_tracks[st]
        sink = []
        pipeline._build_match_from_events(
            track, hit_idx, bounce_idx, near_court, far_court, fps_eff,
            width, height, video, None, ball_conf, near_kpts, far_kpts, H_metric,
            singles=True, lens_k1=lens_k1, ball_coasted=ball_coasted,
            ball_seen=seen_mask(tr, co), span_sink=sink,
        )
        if n_shots is None:
            n_shots = len(sink)
        elif len(sink) != n_shots:
            raise SystemExit(f"shot population moved between stages "
                             f"({n_shots} -> {len(sink)}); the spans are not fixed "
                             f"and the attribution is meaningless")
        fr = [s["seen_frac"] for s in sink]
        mean = 100.0 * sum(fr) / max(len(fr), 1)
        npass = sum(1 for v in fr if v >= 0.5)
        d_mean = None if prev_mean is None else mean - prev_mean
        d_pass = None if prev_pass is None else npass - prev_pass
        print(f"    {STAGE_LABEL[st]:<26}{mean:>14.1f}%"
              f"{'' if d_mean is None else f'{d_mean:>+8.1f}'}"
              f"{npass:>12}"
              f"{'' if d_pass is None else f'{d_pass:>+8d}'}")
        rows.append({"stage": st, "label": STAGE_LABEL[st],
                     "mean_seen_frac_pct": round(mean, 2),
                     "delta_pts": None if d_mean is None else round(d_mean, 2),
                     "shots_ge_50pct": npass,
                     "delta_shots": d_pass,
                     "n_shots": len(sink),
                     "locks": sum(p is not None for p in tr),
                     "seen_frames": sum(seen_mask(tr, co))})
        prev_mean, prev_pass = mean, npass

    if args.json_out:
        payload = {
            "tool": "eval_speed_coverage_chain",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "measured_against":
                "the tracker's own post-chain output over hit->landing spans fixed "
                "by the FULL shipped chain's events; seen_frac is a COVERAGE "
                "statistic, not accuracy — no human gold label is involved and no "
                "claim here is that a seen frame was on the ball",
            "clip": args.clip, "arm": args.label,
            "spans_from": str(args.spans_from) if args.spans_from else None,
            "ball_cache": str(args.ball_cache), "pose_cache": str(pose_path),
            # RESOLVED configuration, not a preset table.
            "ball_cache_provenance": ball_cache.get("provenance"),
            "pose_cache_provenance": pose_cache.get("provenance"),
            "resolution": f"{width}x{height}", "src_fps": round(fps, 3),
            "frame_step": step, "fps_eff": round(fps_eff, 3),
            "res_scale": round(height / 720.0, 4),
            "camera_hfov_deg": round(float(camera_hfov_deg), 2),
            "lens_k1": float(lens_k1), "calibration_source": source,
            "reproj_err_px": None if err is None else round(float(err), 3),
            "frames": n, "n_shots": n_shots,
            "n_hits": len(hit_idx), "n_bounces": len(bounce_idx),
            "events_src": events_src,
            "rows": rows,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
