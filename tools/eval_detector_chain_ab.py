"""eval_detector_chain_ab.py - BallNet v21 vs TrackNet at the CHAIN, not the detector.

WHY. docs/STATE.md carries two DETECTOR-level verdicts that point opposite ways:
pooled hit@10 favours BallNet (60.8 vs 57.9) while F1 at the field's tau=4
favours TrackNet, which wins 9 of 10 clips. CLAUDE.md rule 5 says ball work is
scored at the CHAIN, because four detector gains in a row each cut detector error
and delivered nothing to the rendered output. mobile/models/*.onnx are TrackNet
exports while the desktop default is BallNet; this is the measurement that
settles which one a Core ML export should be spent on.

WHAT IS THE PRODUCT METRIC. The FULL row's `fires` is the ghost-ball count:
annotate.py draws a ball iff ball_px[i] is not None on this same post-
smooth_forecast track, so each fire is a frame where the rendered video paints a
ball over a human's "no ball" click. It is split solid/faded because the renderer
draws a real detection as a solid disc and an interpolated one as a faded ring -
converting solid ghosts into faded ones removes nothing, so SOLID is the number.

THE LADDER MIRRORS pipeline.analyze_video EXACTLY, remove_outliers included:

    remove_outliers -> rectify_track -> suppress_false_locks
                    -> gate_ball_to_court (calibrated clips only)
                    -> smooth_forecast

Note that tools/chain_cache.py's run_chain OMITS remove_outliers while
tools/eval_model_filters.py includes it. The shipped pipeline includes it, so
this tool does; --chain-cache-order reproduces the other one for comparison.

HOMOGRAPHY ROUTING, stated because two of the ten calibrations are compromised
(yt_match40 confirmed wrong, T23; am_hard_utr visibly skewed):
    gate_ball_to_court  H-DEPENDENT   -> ghosts/recall on the 7 calibrated clips
    far_geo             H-DEPENDENT
    ghosts/recall on gold_shell, gold_clay, gold_am   H-FREE (no calibration)
    far_px              H-FREE (top 36% of frame height)
`--no-gate` re-runs the whole comparison with gate_ball_to_court removed, which
makes every clip's ghost/recall number H-free. If the verdict is the same under
both, it does not rest on a calibration.

    backend/.venv/Scripts/python.exe tools/eval_detector_chain_ab.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

import cv2  # noqa: E402
import _goldset as gs  # noqa: E402
from swingvision import ball as B  # noqa: E402
from swingvision import calibration  # noqa: E402

AB = REPO / "data" / "output" / "detector_ab"
ARMS = ("ballnet21", "tracknet")
FAR_FRAC = 0.36
RADIUS = 10.0

#: the seven 'ours' caches reused from build_gold_caches.py - identical settings
REUSE_OURS = {"gold_shell", "gold_clay", "gold_am", "gold_UHf0LeMU2pg",
              "gold_sAjkpeRq4P4", "gold_uR5q2cSM6AY", "gold_L73ep7JHiJ4"}


def cache_for(clip: str, arm: str):
    p = AB / f"{clip}.{arm}.perception.json"
    if p.is_file():
        return p
    if arm == "ballnet21" and clip in REUSE_OURS:
        q = REPO / "data" / "output" / f"{clip}.perception.json"
        if q.is_file():
            return q
    return None


def wh_fps(video: Path):
    cap = cv2.VideoCapture(str(video))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return w, h, fps


def hfov_for(clip: str, wh) -> float:
    """The FITTED horizontal field of view. Assuming 70 deg misreads every clip
    (am_hard_utr fits 86, yt_match40 21) and the court-region gate depends on it."""
    from swingvision import court, courtfit
    c = gs.GOLD[clip]
    if not c.calib or not (REPO / c.calib).is_file():
        return 70.0
    kp = json.loads((REPO / c.calib).read_text(encoding="utf-8"))
    fit = courtfit.cam_fit_quad({n: kp[n] for n in gs.CORNERS}, calibration, court,
                                wh[0], wh[1], allow_roll=True)
    if fit is None:
        return 70.0
    return float(calibration.hfov_from_focal(fit[3][5], wh[0]))


def chain(ball_px, *, w, h, fps_eff, H, hfov, gate=True, chain_cache_order=False):
    """The shipped post-detector chain. Every stage is the pipeline's own function
    in the pipeline's own order with the pipeline's own parameters (trap T15)."""
    rs = h / 720.0
    tr = [tuple(p) if p else None for p in ball_px]
    if not chain_cache_order:
        tr = B.remove_outliers(tr, max_jump=max(w, h) * 0.06)
    tr = B.rectify_track(tr, max_speed_px=3000.0 * rs / fps_eff, resid_px=35.0 * rs)
    tr = B.suppress_false_locks(tr, fps_eff=fps_eff, res_scale=rs)
    if H is not None and gate:
        tr = B.gate_ball_to_court(tr, H, (w, h), hfov_deg=hfov)
    tr, coasted, _c = B.smooth_forecast(tr, fps_eff=fps_eff, res_scale=rs)
    return tr, coasted


def far_masks(ball, H, wh):
    px = {f for f, v in ball.items() if v[1] < FAR_FRAC * wh[1]}
    geo = set()
    if H is not None:
        for f, v in ball.items():
            try:
                if calibration.court_scale_m_per_px(H, v) > \
                        calibration.RELIABLE_SCALE_M_PER_PX:
                    geo.add(f)
            except Exception:
                pass
    return px, geo


def measure(tr, coasted, ball, noball, step, far_px, far_geo):
    n = len(tr)
    at = lambda f: (f // step) if (f % step == 0 and f // step < n) else None  # noqa: E731
    fires, fires_solid = [], []
    n_nb = 0
    for f in noball:
        i = at(f)
        if i is None:
            continue
        n_nb += 1
        if tr[i] is not None:
            fires.append(f)
            if not coasted[i]:
                fires_solid.append(f)
    hit = tot = hp = tp = hg = tg = 0
    for f, xy in ball.items():
        i = at(f)
        if i is None:
            continue
        tot += 1
        p = tr[i]
        ok = p is not None and math.dist(p, xy) <= RADIUS
        hit += ok
        if f in far_px:
            tp += 1
            hp += ok
        if f in far_geo:
            tg += 1
            hg += ok
    return {"n_ball": tot, "hit": hit, "recall": round(100 * hit / max(tot, 1), 1),
            "n_noball": n_nb, "fires": len(fires), "fires_solid": len(fires_solid),
            "fires_faded": len(fires) - len(fires_solid),
            "fire_frames_solid": sorted(fires_solid),
            "n_far_px": tp, "far_px_hit": hp,
            "far_px": round(100 * hp / max(tp, 1), 1),
            "n_far_geo": tg, "far_geo_hit": hg,
            "far_geo": None if tg == 0 else round(100 * hg / tg, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-gate", action="store_true",
                    help="drop gate_ball_to_court, making every number H-free")
    ap.add_argument("--chain-cache-order", action="store_true",
                    help="reproduce tools/chain_cache.py's ladder (no remove_outliers)")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    rows = {a: {} for a in ARMS}
    meta = {}
    for clip, c in gs.GOLD.items():
        paths = {a: cache_for(clip, a) for a in ARMS}
        if not all(paths.values()):
            print(f"skip {clip}: missing {[a for a in ARMS if not paths[a]]}")
            continue
        w, h, fps = wh_fps(REPO / c.video)
        H = gs.load_H(clip)
        hfov = hfov_for(clip, (w, h))
        ball = gs.ball_frames(clip)
        noball = gs.noball_frames(clip)
        fpx, fgeo = far_masks(ball, H, (w, h))
        meta[clip] = {"wh": [w, h], "src_fps": round(fps, 2), "hfov": round(hfov, 1),
                      "calibrated": H is not None,
                      "n_ball_labelled": len(ball), "n_noball_labelled": len(noball)}
        for a in ARMS:
            cache = json.loads(paths[a].read_text(encoding="utf-8"))
            step = int(cache.get("frame_step") or 1)
            fps_eff = fps / step
            tr, coasted = chain(cache["ball_px"], w=w, h=h, fps_eff=fps_eff,
                                H=H, hfov=hfov, gate=not args.no_gate,
                                chain_cache_order=args.chain_cache_order)
            r = measure(tr, coasted, ball, noball, step, fpx, fgeo)
            r.update(cache_path=str(paths[a].relative_to(REPO)).replace("\\", "/"),
                     frame_step=step, fps_eff=round(fps_eff, 2),
                     raw_locks=sum(p is not None for p in cache["ball_px"]),
                     provenance=cache.get("provenance"))
            rows[a][clip] = r
            meta[clip][a + "_step"] = step
        print(f"scored {clip}", flush=True)

    clips = [c for c in gs.GOLD if c in rows["ballnet21"] and c in rows["tracknet"]]
    hdr = (f"{'clip':<20}{'cal':>4}{'nb':>4}"
           f"{'solidB':>8}{'solidT':>8}{'d':>4}"
           f"{'ghostB':>8}{'ghostT':>8}{'d':>4}"
           f"{'recB':>8}{'recT':>8}{'d':>7}")
    gate_note = "gate OFF (H-free)" if args.no_gate else "gate ON (shipped)"
    order_note = "chain_cache order" if args.chain_cache_order else "shipped order"
    print(f"\nCHAIN A/B  B=BallNet v21  T=TrackNet   [{gate_note}, {order_note}]")
    print(hdr)
    print("-" * len(hdr))
    tot = {a: dict(nb=0, solid=0, fires=0, ball=0, hit=0, fpx_n=0, fpx_h=0,
                   fgeo_n=0, fgeo_h=0) for a in ARMS}
    signs = set()
    for clip in clips:
        b, t = rows["ballnet21"][clip], rows["tracknet"][clip]
        d = t["fires_solid"] - b["fires_solid"]
        signs.add((d > 0) - (d < 0))
        print(f"{clip:<20}{'Y' if meta[clip]['calibrated'] else 'n':>4}"
              f"{b['n_noball']:>4}{b['fires_solid']:>8}{t['fires_solid']:>8}{d:>+4}"
              f"{b['fires']:>8}{t['fires']:>8}{t['fires']-b['fires']:>+4}"
              f"{b['recall']:>7.1f}%{t['recall']:>7.1f}%"
              f"{t['recall']-b['recall']:>+6.1f}")
        for a in ARMS:
            r = rows[a][clip]
            tot[a]['nb'] += r['n_noball']
            tot[a]['solid'] += r['fires_solid']
            tot[a]['fires'] += r['fires']
            tot[a]['ball'] += r['n_ball']
            tot[a]['hit'] += r['hit']
            tot[a]['fpx_n'] += r['n_far_px']
            tot[a]['fpx_h'] += r['far_px_hit']
            tot[a]['fgeo_n'] += r['n_far_geo']
            tot[a]['fgeo_h'] += r['far_geo_hit']
    print("-" * len(hdr))
    B_, T_ = tot["ballnet21"], tot["tracknet"]
    rb = 100 * B_['hit'] / max(B_['ball'], 1)
    rt = 100 * T_['hit'] / max(T_['ball'], 1)
    print(f"{'POOLED':<20}{'':>4}{B_['nb']:>4}{B_['solid']:>8}{T_['solid']:>8}"
          f"{T_['solid']-B_['solid']:>+4}{B_['fires']:>8}{T_['fires']:>8}"
          f"{T_['fires']-B_['fires']:>+4}{rb:>7.1f}%{rt:>7.1f}%{rt-rb:>+6.1f}")
    print(f"\n  ball frames scored {B_['ball']} (BallNet) / {T_['ball']} (TrackNet); "
          f"no-ball frames {B_['nb']}")
    print(f"  far_px  recall  BallNet {100*B_['fpx_h']/max(B_['fpx_n'],1):.1f}%   "
          f"TrackNet {100*T_['fpx_h']/max(T_['fpx_n'],1):.1f}%   (n={B_['fpx_n']}) [H-free]")
    print(f"  far_geo recall  BallNet {100*B_['fgeo_h']/max(B_['fgeo_n'],1):.1f}%   "
          f"TrackNet {100*T_['fgeo_h']/max(T_['fgeo_n'],1):.1f}%   (n={B_['fgeo_n']}) [H-DEPENDENT]")
    if len(signs - {0}) > 1:
        print("\n  !! clips DISAGREE IN SIGN on solid ghosts - the pooled number is an "
              "average of\n     opposite effects. Read the per-clip rows.")

    sb = {(c, f) for c in clips for f in rows["ballnet21"][c]["fire_frames_solid"]}
    st = {(c, f) for c in clips for f in rows["tracknet"][c]["fire_frames_solid"]}
    if sb or st:
        both = len(sb & st)
        print(f"\n  SAME FRAMES?  {both} of {len(sb | st)} solid-ghost frames fire on "
              f"BOTH arms ({100*both/max(len(sb|st),1):.0f}% overlap)")

    if args.json_out:
        payload = {
            "tool": "eval_detector_chain_ab",
            "measured_against":
                "human gold clicks on the 10-clip gold set; hit = within 10 px of the "
                "click; a ghost = a no-ball click on which the FULL post-chain track "
                "still carries a ball (solid = the detector saw it, faded = the "
                "smoother interpolated it)",
            "arms": {"ballnet21": "ball_model=ours, weights/ballnet_v21.pt",
                     "tracknet": "ball_model=tracknet, weights/tracknet.pt"},
            "one_variable": "ball_model; every other ball_perception.py argument identical",
            "gate_ball_to_court": not args.no_gate,
            "ladder": ("chain_cache order (no remove_outliers)" if args.chain_cache_order
                       else "shipped pipeline order"),
            "meta": meta,
            "rows": rows,
            "pooled": {a: {**tot[a],
                           "recall": round(100 * tot[a]['hit'] / max(tot[a]['ball'], 1), 1),
                           "far_px": round(100 * tot[a]['fpx_h'] / max(tot[a]['fpx_n'], 1), 1),
                           "far_geo": round(100 * tot[a]['fgeo_h'] / max(tot[a]['fgeo_n'], 1), 1)}
                       for a in ARMS},
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
