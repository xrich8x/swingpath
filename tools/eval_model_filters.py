"""eval_model_filters.py — measure a ball model THROUGH the shipped post-chain,
stage by stage, against the human gold labels.

The ladder here MUST mirror pipeline.analyze_video. It previously did not: its
last row was billed "FULL" while running the retired live-ball filter and running
neither gate_ball_to_court nor smooth_forecast. A ladder that does not match the
shipped code is worse than none — every conclusion drawn from it is about a
pipeline nobody runs.

  cd backend && .venv-train/Scripts/python.exe ../tools/eval_model_filters.py \
      --device cuda --weights weights/ballnet_v21.pt

Two far-court bands are reported, because they answer different questions and
only one of them is available on every clip:

  far_px   the top 36% of frame height. Geometry-blind but resolution-relative,
           so it works on the uncalibrated gold clips and keeps continuity with
           every number this project has recorded. THE HEADLINE.
  far_geo  where court_scale_m_per_px exceeds calibration.RELIABLE_SCALE_M_PER_PX,
           i.e. where 1 px of centroid error costs more than 9 cm of court. Needs
           a calibration, so it exists only on the calibrated clips — but it is
           the honest answer to "can we actually MEASURE a ball there".

The FULL row's `fires` is also the GHOST-BALL product metric (Session F step 1),
not merely a per-frame statistic. annotate.py draws a ball iff ball_px[i] is not
None on this same post-smooth_forecast track, so each fire is a frame where the
annotated video paints a ball over a human's "no ball" click. It is reported
split (N solid, M faded) because the renderer distinguishes a real detection
from an interpolated one, and a change that only converts solid ghosts to faded
ones has removed nothing. Per-frame false-fire is NOT the product — E6 part 4
raised it 19.2% -> 23.1% on yt_rally2 for zero extra phantom events — so pick on
this number and on tools/event_audit.py, never on false-fire alone.
"""
from __future__ import annotations
import argparse, json, math, os, sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import cv2
import numpy as np

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
# clip -> (video, court-pts json, gold labels json)
CLIPS = {
    "am_hard_utr": ("data/am_hard_utr.mp4", "data/am_hard_utr_pts.json",
                    "data/gold/am_hard_utr.labels.json"),
    "yt_rally2": ("data/yt_rally2.mp4", "data/yt_rally2_pts.json",
                  "data/gold/yt_rally2.labels.json"),
    "yt_match40": ("data/yt_match40.mp4", "data/yt_match40_pts.json",
                   "data/gold/yt_match40.labels.json"),
}
FAR_FRAC = 0.36


def build_calib(pts_path, wh):
    """Homography plus the FITTED lens. Assuming 70 deg misreads every clip
    (am_hard_utr is 86, yt_match40 is 21) and both the tracker's height cone and
    the court-region gate depend on it."""
    from swingvision import calibration, court, courtfit
    kp = json.load(open(REPO / pts_path))
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                       [kp[n] for n in CORN])
    hfov = 70.0
    fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court,
                                wh[0], wh[1], allow_roll=True)
    if fit is not None:
        hfov = float(calibration.hfov_from_focal(fit[3][5], wh[0]))
    return H, hfov


def gold(labels_path):
    g = {int(k): v for k, v in json.load(open(REPO / labels_path))["labels"].items()}
    ball = {f: v for f, v in g.items() if v.get("ball") and not v.get("unsure")}
    noball = [f for f, v in g.items() if v.get("ball") is False and not v.get("unsure")]
    return ball, noball


def far_masks(ball, H, wh):
    """Which gold clicks are 'far' under each definition."""
    from swingvision import calibration
    px = {f for f, v in ball.items() if v["y"] < FAR_FRAC * wh[1]}
    geo = set()
    for f, v in ball.items():
        try:
            if calibration.court_scale_m_per_px(H, (v["x"], v["y"])) > \
                    calibration.RELIABLE_SCALE_M_PER_PX:
                geo.add(f)
        except Exception:
            pass
    return px, geo


def perceive(video, weights, device, H, cam_xyz, W, Hh, fps_eff, step,
             acquire_bound_m=4.0):
    os.environ["BALLNET_WEIGHTS"] = weights
    from swingvision.ball import OurBallDetector, BallTracker
    det = OurBallDetector(device=device)
    tracker = BallTracker([det], (W, Hh), use_bgsub=False, homography=H,
                          fps=fps_eff, cam_xyz=cam_xyz,
                          acquire_bound_m=acquire_bound_m)
    cap = cv2.VideoCapture(str(video))
    ball_px = []
    idx = 0
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            ball_px.append(tracker.update(frame))
        idx += 1
    cap.release()
    print(f"  perceived {len(ball_px)} frames in {time.time()-t0:.0f}s", flush=True)
    print(f"  locks: model={tracker.n_tnet} | misses: no-detection={tracker.n_no_det}, "
          f"court-gate(acq)={tracker.n_rej_court_acq}, "
          f"court-gate(cont)={tracker.n_rej_court_cont}, "
          f"fixture={tracker.n_rej_static}, off-path={tracker.n_rej_vel}, "
          f"untracked-frames={tracker.n_untracked}", flush=True)
    return ball_px


def index_of(step, n):
    """gold frame -> position in the track, or None if that frame was never processed.

    The guard matters more than it looks. At step=2 on a 60 fps clip, HALF the gold
    frames are odd; without `f % step == 0` they get scored against the ball's
    position one source frame earlier, against a 10 px tolerance — which on a
    1080p clip is often further than the ball moves. `tools/eval_gold.py` has had
    this guard all along; this tool did not, so its recall numbers understated the
    tracker by counting a timing offset as a miss.
    """
    return lambda f: (f // step) if (f % step == 0 and f // step < n) else None


def measure(tr, ball, noball, step, tag, far_px, far_geo, coasted=None):
    at = index_of(step, len(tr))
    fires = [f for f in noball if at(f) is not None and tr[at(f)] is not None]
    n_nb = sum(1 for f in noball if at(f) is not None)
    # `fires` on the FULL row IS the ghost-ball product metric, not a proxy for it.
    # annotate.py draws a ball iff ball_px[i] is not None on this same post-
    # smooth_forecast track, so a fire here is a frame where the annotated video
    # paints a ball on top of a human's "no ball". The split matters because the
    # renderer draws the two differently — a real detection is a solid disc, an
    # interpolated one a faded ring — so a coasted false fire is the milder
    # failure, and a fix that only converts solid ghosts into faded ones has not
    # actually removed anything.
    fires_coasted = (None if coasted is None else
                     sum(1 for f in fires
                         if at(f) < len(coasted) and coasted[at(f)]))
    hit = tot = 0
    hp = tp = hg = tg = 0
    ghost = 0
    for f, v in ball.items():
        pf = at(f)
        if pf is None:
            continue                     # not a processed frame: unscoreable, not a miss
        tot += 1
        p = tr[pf]
        ok = p is not None and math.dist(p, (v["x"], v["y"])) <= 10.0
        hit += ok
        if ok and coasted is not None and pf < len(coasted) and coasted[pf]:
            ghost += 1
        if f in far_px:
            tp += 1; hp += ok
        if f in far_geo:
            tg += 1; hg += ok
    geo = "     -" if tg == 0 else f"{100*hg/tg:>5.1f}%"
    if coasted is None:
        note = ""
        fires_note = ""
    else:
        note = f"  ({ghost} of the hits interpolated)"
        fires_note = f" ({len(fires) - fires_coasted} solid, {fires_coasted} faded)"
    print(f"    {tag:<32}{100*len(fires)/max(n_nb,1):>7.1f}%"
          f"{100*hit/max(tot,1):>9.1f}%{100*hp/max(tp,1):>10.1f}%{geo:>9}"
          f"   fires={len(fires)}{fires_note}{note}")
    return {"stage": tag,
            "false_fire": round(100 * len(fires) / max(n_nb, 1), 1),
            "recall": round(100 * hit / max(tot, 1), 1),
            "far_px": round(100 * hp / max(tp, 1), 1),
            "far_geo": None if tg == 0 else round(100 * hg / tg, 1),
            "fires": len(fires), "n_scored": tot, "n_noball": n_nb,
            # None on the pre-smoother rows, matching interpolated_hits: there is
            # no coasted mask before smooth_forecast, so the split is undefined
            # rather than zero.
            "fires_coasted": fires_coasted,
            "fires_real": None if coasted is None else len(fires) - fires_coasted,
            "interpolated_hits": None if coasted is None else ghost}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", nargs="+", required=True)
    ap.add_argument("--clip", default="yt_rally2", choices=list(CLIPS))
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--acquire-bound", type=float, default=4.0,
                    help="court envelope (m) a candidate must fall inside to START a "
                         "track; continuing one uses 10 m. Measured on am_hard_utr the "
                         "4 m default can seed from only 62.9%% of real ball positions "
                         "and 0 of 13 far-court ones")
    ap.add_argument("--frame-step", type=int, default=None,
                    help="override the ~30fps decimation; 1 makes every gold frame "
                         "scoreable (2x the GPU time) and is the cross-check that the "
                         "decimated run is not hiding anything")
    ap.add_argument("--score-thresh", type=float, default=None,
                    help="detector accept threshold (default: the shipped 0.5). "
                         "Set via the env hook so it reaches every construction "
                         "site, and it IS stamped into the provenance, so a cache "
                         "cannot be reused across arms by accident")
    ap.add_argument("--json", dest="json_out",
                    help="also write the ladder as JSON (for tools/lab_server.py)")
    args = ap.parse_args()

    if args.score_thresh is not None:
        os.environ["BALLNET_SCORE_THRESH"] = str(args.score_thresh)

    from swingvision import calibration, ball as B
    video_rel, pts_rel, labels_rel = CLIPS[args.clip]
    video = REPO / video_rel
    cap = cv2.VideoCapture(str(video))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0; cap.release()
    H, hfov = build_calib(pts_rel, (W, Hh))
    step = args.frame_step or max(1, round(src_fps / 30.0))
    fps_eff = src_fps / step
    cam_xyz = calibration.camera_position_m(H, (W, Hh), hfov)
    ballg, noball = gold(labels_rel)
    far_px, far_geo = far_masks(ballg, H, (W, Hh))
    frac, until = calibration.reliable_court_span(H)
    # How much of the gold set this decimation can even see. Silently dropping half
    # the labels and calling the remainder "recall" is how the old version of this
    # tool understated the tracker.
    scoreable = sum(1 for f in ballg if f % step == 0)
    print(f"{args.clip} {W}x{Hh} @ {src_fps:.0f}fps, step={step}, fps_eff={fps_eff:.0f}, "
          f"hfov={hfov:.0f}deg, cam={None if cam_xyz is None else np.round(cam_xyz,1)}, "
          f"acquire_bound={args.acquire_bound:.0f}m")
    print(f"  measurable to court-y {until:.1f} m of 23.8 ({100*frac:.0f}% of depth); "
          f"{len(ballg)} ball / {len(noball)} no-ball; "
          f"far_px={len(far_px)}, far_geo={len(far_geo)}")
    if scoreable < len(ballg):
        print(f"  NOTE step={step} processes only {scoreable}/{len(ballg)} labelled ball "
              f"frames; the other {len(ballg)-scoreable} are SKIPPED, not counted as "
              f"misses. Use --frame-step 1 to score all of them.")
    print(f"    {'stage':<32}{'false-fire':>7}{'recall':>9}{'far_px':>10}{'far_geo':>9}\n"
          + "-" * 76)
    rows = []
    for w in args.weights:
        print(f"[{Path(w).name}]", flush=True)
        raw = perceive(video, w, args.device, H, cam_xyz, W, Hh, fps_eff, step,
                       acquire_bound_m=args.acquire_bound)
        # The ladder below mirrors pipeline.analyze_video exactly, res_scale included.
        rs = Hh / 720.0
        stages = [measure(raw, ballg, noball, step, "tracker gates only",
                          far_px, far_geo)]
        tr = B.remove_outliers(list(raw), max_jump=max(W, Hh) * 0.06)
        tr = B.rectify_track(tr, max_speed_px=3000.0 * rs / fps_eff, resid_px=35.0 * rs)
        stages.append(measure(tr, ballg, noball, step, "+ rectify", far_px, far_geo))
        tr = B.suppress_false_locks(tr, fps_eff=fps_eff, res_scale=rs)
        stages.append(measure(tr, ballg, noball, step, "+ suppress_false_locks",
                              far_px, far_geo))
        tr = B.gate_ball_to_court(tr, H, (W, Hh), hfov_deg=hfov)
        stages.append(measure(tr, ballg, noball, step, "+ court-region gate",
                              far_px, far_geo))
        tr, coasted, _conf = B.smooth_forecast(tr, fps_eff=fps_eff, res_scale=rs)
        stages.append(measure(tr, ballg, noball, step, "+ kalman smooth (FULL)",
                              far_px, far_geo, coasted=coasted))
        for s in stages:
            rows.append({"weights": Path(w).name, "clip": args.clip, **s})
    print("\nMeasured against human gold clicks; hit = within 10 px. far_px = top "
          f"{FAR_FRAC:.0%} of frame height. far_geo = court_scale_m_per_px > "
          f"{calibration.RELIABLE_SCALE_M_PER_PX} (needs calibration).")

    if args.json_out:
        payload = {
            "tool": "eval_model_filters",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            # ML_PRACTICES: state what the number was measured against, and the
            # denominator. `scoreable` matters here — a decimated run cannot see
            # every gold frame, and calling the remainder "recall" is exactly how
            # this tool understated the tracker before the alignment fix.
            "measured_against":
                f"human gold clicks on {args.clip}; hit = within 10 px. "
                f"{scoreable} of {len(ballg)} labelled ball frames scoreable at "
                f"step={step}; {len(noball)} no-ball frames",
            "clip": args.clip, "weights": args.weights, "device": args.device,
            "score_thresh": args.score_thresh,
            "frame_step": step, "fps_eff": round(fps_eff, 2),
            "resolution": f"{W}x{Hh}",
            "scoreable": scoreable, "n_ball_labelled": len(ballg),
            "n_noball": len(noball),
            "measurable_depth_m": round(until, 1),
            "rows": rows,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=1),
                                       encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
