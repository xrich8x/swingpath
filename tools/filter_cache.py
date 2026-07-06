"""Apply the offline live-ball filter (ball.filter_live_ball) to perception
caches and write filtered copies, so eval_gold can A/B raw vs filtered against
the human gold labels WITHOUT re-running any perception.

  backend/.venv/Scripts/python.exe tools/filter_cache.py \
      --keypoints data/yt_rally2_pts.json \
      data/output/demo30.perception.json ...   -> *.live.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import court  # noqa: E402
from swingvision.ball import filter_live_ball  # noqa: E402
from swingvision.calibration import compute_homography  # noqa: E402


def homography(keypoints: str | None):
    if not keypoints:
        return None
    kp = json.loads(Path(keypoints).read_text(encoding="utf-8"))
    names = [n for n in ("near_bl_doubles", "near_br_doubles",
                         "far_bl_doubles", "far_br_doubles") if n in kp]
    if len(names) < 4:
        return None
    return compute_homography([court.LANDMARKS[n] for n in names],
                              [kp[n] for n in names])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("caches", nargs="+")
    ap.add_argument("--keypoints", default=None)
    ap.add_argument("--min-run", type=int, default=4)
    ap.add_argument("--min-net-disp-px", type=float, default=12.0)
    ap.add_argument("--play-margin-m", type=float, default=2.0)
    ap.add_argument("--suffix", default="live")
    args = ap.parse_args()

    H = homography(args.keypoints)
    print(f"homography: {'loaded' if H is not None else 'none (motion test only)'}")
    for c in args.caches:
        data = json.loads(Path(c).read_text(encoding="utf-8"))
        raw = data["ball_px"]
        filt = filter_live_ball(raw, homography=H, min_run=args.min_run,
                                min_net_disp_px=args.min_net_disp_px,
                                play_margin_m=args.play_margin_m)
        before = sum(p is not None for p in raw)
        after = sum(p is not None for p in filt)
        data["ball_px"] = filt
        data.setdefault("provenance", {})["live_ball_filter"] = {
            "min_run": args.min_run, "min_net_disp_px": args.min_net_disp_px,
            "play_margin_m": args.play_margin_m, "homography": H is not None,
            "removed": before - after,
        }
        out = Path(c).with_suffix("")   # strip .json
        out = out.with_name(out.name + f".{args.suffix}.json")
        out.write_text(json.dumps(data), encoding="utf-8")
        print(f"{Path(c).name}: {before} -> {after} locks "
              f"({before - after} removed) -> {out.name}")


if __name__ == "__main__":
    main()
