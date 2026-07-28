"""eval_detector_gold.py — raw-detector recall + false-fire on the gold clips (E5).

Isolates what a BallNet retrain changed, without the tracker's gates: for every
gold frame, run the detector on its 3-frame window and score recall (hit@10 on
ball frames), far-court recall (image y < 260), and false-fire (fires on a
no-ball frame). Point it at two weight files to compare v2.1 vs baseline.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\eval_detector_gold.py \\
      --weights weights/ballnet_v21.pt --device cuda
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

# clip -> (video, calibration or None). Only three gold clips have a calibration,
# so the geometry-based far band exists only for those; the pixel band covers all.
CLIPS = [
    ("am_hard_utr", "data/am_hard_utr.mp4", "data/am_hard_utr_pts.json"),  # 1080p gold (primary)
    ("gold_shell", "data/gold_shell.mp4", None),
    ("gold_clay", "data/gold_clay.mp4", None),
    ("gold_am", "data/gold_am.mp4", None),
    ("yt_rally2", "data/yt_rally2.mp4", "data/yt_rally2_pts.json"),
    ("yt_match40", "data/yt_match40.mp4", "data/yt_match40_pts.json"),
]
CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def load_H(pts_rel):
    if not pts_rel or not (REPO / pts_rel).exists():
        return None
    from swingvision import calibration, court
    kp = json.loads((REPO / pts_rel).read_text(encoding="utf-8"))
    return calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                          [kp[n] for n in CORN])


def score_clip(det, video, labels, radius=10.0, far_frac=0.36, H=None):
    from swingvision import calibration
    gold = {int(k): v for k, v in json.loads(Path(labels).read_text(encoding="utf-8"))["labels"].items()}
    ball = {f: v for f, v in gold.items() if v.get("ball") and not v.get("unsure")}
    noball = {f: v for f, v in gold.items() if v.get("ball") is False and not v.get("unsure")}
    cap = cv2.VideoCapture(str(video))
    # far-court band as a fraction of frame height, so 720p and 1080p are comparable
    far_y = far_frac * (cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720.0)

    def unmeasurable(v):
        """Is this click where 1 px of error costs more than RELIABLE_SCALE_M_PER_PX
        of court? The pixel band is a proxy for this; with a calibration we can ask
        directly, and the two disagree a lot on a low camera."""
        if H is None:
            return False
        try:
            return calibration.court_scale_m_per_px(H, (v["x"], v["y"])) > \
                calibration.RELIABLE_SCALE_M_PER_PX
        except Exception:
            return False

    hit = tot = fhit = ftot = fp = ftt = ghit = gtot = 0
    want = sorted(set(ball) | set(noball))
    for f in want:
        frames = []
        for j in (f - 2, f - 1, f):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, j))
            ok, im = cap.read()
            if ok:
                frames.append(im)
        if len(frames) < 3:
            continue
        det.reset()
        p = None
        for im in frames:
            p = det.detect(im)
        if f in ball:
            v = ball[f]
            tot += 1
            ok10 = p is not None and math.dist(p, (v["x"], v["y"])) <= radius
            hit += ok10
            if v["y"] < far_y:
                ftot += 1
                fhit += ok10
            if unmeasurable(v):
                gtot += 1
                ghit += ok10
        else:
            ftt += 1
            fp += p is not None
    cap.release()
    return dict(recall=100 * hit / max(tot, 1), far=100 * fhit / max(ftot, 1),
                geo=(None if gtot == 0 else 100 * ghit / gtot),
                ff=100 * fp / max(ftt, 1), n=tot, nfar=ftot, nnb=ftt, ngeo=gtot)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--weights", required=True)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    os.environ["BALLNET_WEIGHTS"] = args.weights
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=args.device)
    print(f"weights={args.weights}\n")
    print(f"{'clip':<12}{'recall':>8}{'far_px':>8}{'far_geo':>9}{'false-fire':>12}"
          f"   {'band sizes px/geo':>16}")
    print("-" * 68)
    agg = {"hit": 0, "tot": 0, "fhit": 0, "ftot": 0, "fp": 0, "ftt": 0,
           "ghit": 0, "gtot": 0}
    for tag, video, pts in CLIPS:
        labels = REPO / "data" / "gold" / f"{tag}.labels.json"
        if not labels.exists() or not (REPO / video).exists():
            continue
        r = score_clip(det, REPO / video, labels, H=load_H(pts))
        geo = "      -" if r["geo"] is None else f"{r['geo']:>6.1f}%"
        # Print how many clicks each band holds. Without it far_geo is easy to
        # misread: on a low camera the unmeasurable zone covers most of the court,
        # so far_geo stops being a "far court" sample and becomes "nearly the whole
        # clip" — which is why it can sit ABOVE the overall recall.
        span = f"{r['nfar']}/{r['ngeo']} of {r['n']}"
        print(f"{tag:<12}{r['recall']:>7.1f}%{r['far']:>7.1f}%{geo:>9}{r['ff']:>11.1f}%"
              f"   {span:>16}")
        agg["hit"] += r["recall"] / 100 * r["n"]; agg["tot"] += r["n"]
        agg["fhit"] += r["far"] / 100 * r["nfar"]; agg["ftot"] += r["nfar"]
        agg["fp"] += r["ff"] / 100 * r["nnb"]; agg["ftt"] += r["nnb"]
        if r["geo"] is not None:
            agg["ghit"] += r["geo"] / 100 * r["ngeo"]; agg["gtot"] += r["ngeo"]
    print("-" * 68)
    pooled_geo = ("      -" if agg["gtot"] == 0
                  else f"{100*agg['ghit']/agg['gtot']:>6.1f}%")
    pooled_span = f"{agg['ftot']}/{agg['gtot']} of {agg['tot']}"
    print(f"{'POOLED':<12}{100*agg['hit']/max(agg['tot'],1):>7.1f}%"
          f"{100*agg['fhit']/max(agg['ftot'],1):>7.1f}%{pooled_geo:>9}"
          f"{100*agg['fp']/max(agg['ftt'],1):>11.1f}%   {pooled_span:>16}")
    print("\nMeasured against human gold clicks (hit = within 10 px).")
    print("far_px  = top 36% of frame height. Available on every clip, comparable "
          "across resolutions; THE HEADLINE.")
    print("far_geo = where 1 px of centroid error costs more than "
          "RELIABLE_SCALE_M_PER_PX of court. Needs a calibration (3 of 6 clips).")
    print("CAREFUL: far_geo is not a synonym for 'far court'. It is 'the part of "
          "this clip we cannot measure in', and on a low camera that is most of the "
          "frame — am_hard_utr is measurable to only 32% of court depth, so its "
          "far_geo band includes easy near-court balls and reads ABOVE overall "
          "recall. Compare far_geo only between clips of similar measurable depth.")


if __name__ == "__main__":
    main()
