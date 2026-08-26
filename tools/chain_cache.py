"""Run the SHIPPED post-detector chain over a perception cache and write the
result as a new cache, so eval_gold can A/B a chain change against human gold
labels WITHOUT re-running perception.

Same pattern as tools/filter_cache.py, and the same reason: a chain experiment
that re-derives the stages instead of calling them measures something the
product does not do (trap T15). Every stage below is the SAME function, in the
SAME order, with the SAME parameters as pipeline.analyze_video's ball section:

    rectify_track -> suppress_false_locks -> gate_ball_to_court -> smooth_forecast

`--stop-after` writes the track as it stands at the end of a named stage, which
is how the per-stage attribution table is produced. `--bounce-hypothesis` turns
on the fourth smoother attempt (docs/evidence/ball-chain-gate.md).

  backend/.venv/Scripts/python.exe tools/chain_cache.py \
      --keypoints data/am_hard_utr_pts.json \
      --out data/output/am_hard_utr.chain.json \
      data/output/am_hard_utr.perception.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import ball as ball_mod          # noqa: E402
from swingvision import court  # noqa: E402
from swingvision.calibration import compute_homography  # noqa: E402

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")
STAGES = ("raw", "rectify", "suppress", "gate", "smooth")


def homography(keypoints: str | None):
    if not keypoints:
        return None
    kp = json.loads(Path(keypoints).read_text(encoding="utf-8"))
    names = [n for n in CORNERS if n in kp]
    if len(names) < 4:
        return None
    return compute_homography([court.LANDMARKS[n] for n in names],
                              [kp[n] for n in names])


def run_chain(ball_px, *, fps_eff, width, height, H, hfov, stop_after="smooth",
              bounce_hypothesis=False):
    """Invoke the shipped stages. Returns (track, coasted, per_stage_counts)."""
    res_scale = height / 720.0
    counts = {"raw": sum(p is not None for p in ball_px)}
    coasted = [False] * len(ball_px)

    if stop_after == "raw":
        return ball_px, coasted, counts

    ball_px = ball_mod.rectify_track(
        ball_px,
        max_speed_px=3000.0 * res_scale / fps_eff,
        resid_px=35.0 * res_scale,
    )
    counts["rectify"] = sum(p is not None for p in ball_px)
    if stop_after == "rectify":
        return ball_px, coasted, counts

    ball_px = ball_mod.suppress_false_locks(ball_px, fps_eff=fps_eff,
                                            res_scale=res_scale)
    counts["suppress"] = sum(p is not None for p in ball_px)
    if stop_after == "suppress":
        return ball_px, coasted, counts

    if H is not None:
        ball_px = ball_mod.gate_ball_to_court(ball_px, H, (width, height),
                                              hfov_deg=hfov)
    counts["gate"] = sum(p is not None for p in ball_px)
    if stop_after == "gate":
        return ball_px, coasted, counts

    ball_px, coasted, _conf = ball_mod.smooth_forecast(
        ball_px, fps_eff=fps_eff, res_scale=res_scale,
        bounce_hypothesis=bounce_hypothesis,
    )
    counts["smooth"] = sum(p is not None for p in ball_px)
    # A coasted frame is DRAWN but was not SEEN. real_fraction counts seen, so
    # the two must never be conflated (pipeline.py makes the same distinction).
    counts["smooth_seen"] = sum(
        1 for i, p in enumerate(ball_px) if p is not None and not coasted[i]
    )
    return ball_px, coasted, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("caches", nargs="+")
    ap.add_argument("--keypoints", default=None)
    ap.add_argument("--out", default=None,
                    help="output cache path (single input only)")
    ap.add_argument("--suffix", default=".chain",
                    help="used when --out is absent")
    ap.add_argument("--stop-after", default="smooth", choices=STAGES)
    ap.add_argument("--bounce-hypothesis", action="store_true")
    ap.add_argument("--fps", type=float, default=None,
                    help="source fps; fps_eff = fps / frame_step")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--seen-only", action="store_true",
                    help="write only frames the detector actually SAW (drop "
                         "coasted fills), which is what a recall number needs")
    args = ap.parse_args()

    H = homography(args.keypoints)

    for path in args.caches:
        cache = json.loads(Path(path).read_text(encoding="utf-8"))
        prov = cache.get("provenance") or {}
        step = int(cache.get("frame_step") or 1)
        fps_src = args.fps
        fps_eff = fps_src / step
        # NO SILENT DEFAULT. res_scale is height/720 and every pixel threshold
        # in the chain scales by it, so guessing 1080p on a 720p clip runs the
        # whole chain 1.5x too loose and the run looks fine (trap T16: a default
        # that cannot tell "not found" from "found and fine"). The caches do not
        # record resolution, so it must be passed.
        width = args.width or prov.get("width")
        height = args.height or prov.get("height")
        if not width or not height:
            raise SystemExit(
                f"{path}: --width/--height are required (the cache does not record "
                f"them, and res_scale=height/720 changes every threshold in the chain)")
        width, height = int(width), int(height)
        if not args.fps:
            raise SystemExit(
                f"{path}: --fps is required (source fps; fps_eff = fps/frame_step). "
                f"Never let it default - it sets every time threshold's frame count.")
        hfov = prov.get("camera_hfov_deg")

        track, coasted, counts = run_chain(
            list(cache["ball_px"]),
            fps_eff=fps_eff, width=width, height=height, H=H, hfov=hfov,
            stop_after=args.stop_after,
            bounce_hypothesis=args.bounce_hypothesis,
        )

        if args.seen_only:
            track = [None if coasted[i] else p for i, p in enumerate(track)]

        cache["ball_px"] = track
        cache.setdefault("provenance", {})["chain"] = {
            "stop_after": args.stop_after,
            "bounce_hypothesis": bool(args.bounce_hypothesis),
            "seen_only": bool(args.seen_only),
            "fps_eff": fps_eff,
            "res_scale": height / 720.0,
            "homography": H is not None,
            "counts": counts,
        }
        out = Path(args.out) if args.out else Path(path).with_suffix(
            args.suffix + ".json")
        out.write_text(json.dumps(cache), encoding="utf-8")
        stages = "  ".join(f"{k}={v}" for k, v in counts.items())
        print(f"{Path(path).name}  ->  {out.name}")
        print(f"   {stages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
