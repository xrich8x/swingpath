"""eval_detector_gold.py — raw-detector recall + false-fire on the gold clips (E5).

Isolates what a BallNet retrain changed, without the tracker's gates: for every
gold frame, run the detector on its 3-frame window and score recall (hit@10 on
ball frames), far-court recall (image y < 260), and false-fire (fires on a
no-ball frame). Point it at two weight files to compare v2.1 vs baseline.

  cd backend && .venv-train\\Scripts\\python.exe ..\\tools\\eval_detector_gold.py \\
      --weights weights/ballnet_v21.pt --device cuda

SWEEPING THE SCORE THRESHOLD COSTS ONE PASS, NOT ONE PASS PER THRESHOLD
----------------------------------------------------------------------
`--score-thresh` takes several values and the extra ones are free.
OurBallDetector.detect() picks the heatmap peak by argmax and only THEN compares
it to score_thresh, so the peak's POSITION does not depend on the threshold —
recording the peak value once per window makes every threshold an in-memory
comparison. This is exact, not an approximation: the sweep is pinned against a
real per-threshold pass by backend/tests/test_score_thresh.py.

That matters because 0.5 is an INHERITED default. It is hardcoded in four places
in ball.py, was reachable from no tool or CLI, and had never been swept in this
project's history.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
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


def probe_clip(det, video, labels):
    """One GPU pass: the heatmap peak and its position for every gold window.

    Returns {frame: (pt, score)}. `pt` is the argmax location, which is
    threshold-independent, so every threshold can be scored from this dict.
    """
    gold = {int(k): v for k, v in json.loads(Path(labels).read_text(encoding="utf-8"))["labels"].items()}
    want = sorted(f for f, v in gold.items()
                  if not v.get("unsure") and v.get("ball") is not None)
    cap = cv2.VideoCapture(str(video))
    out = {}
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
        for im in frames:
            det.detect(im)
        out[f] = (det.last_pt, det.last_score)
    cap.release()
    return out


def score_probe(probe, labels, thresh, radius=10.0, far_frac=0.36, H=None,
                frame_h=720.0):
    """Score one threshold against a probe dict. No GPU, no video."""
    from swingvision import calibration
    gold = {int(k): v for k, v in json.loads(Path(labels).read_text(encoding="utf-8"))["labels"].items()}
    ball = {f: v for f, v in gold.items() if v.get("ball") and not v.get("unsure")}
    noball = {f: v for f, v in gold.items() if v.get("ball") is False and not v.get("unsure")}
    far_y = far_frac * frame_h

    def unmeasurable(v):
        if H is None:
            return False
        try:
            return calibration.court_scale_m_per_px(H, (v["x"], v["y"])) > \
                calibration.RELIABLE_SCALE_M_PER_PX
        except Exception:
            return False

    hit = tot = fhit = ftot = fp = ftt = ghit = gtot = 0
    for f, (pt, score) in probe.items():
        p = pt if (pt is not None and score >= thresh) else None
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
        elif f in noball:
            ftt += 1
            fp += p is not None
    return dict(recall=100 * hit / max(tot, 1), far=100 * fhit / max(ftot, 1),
                geo=(None if gtot == 0 else 100 * ghit / gtot),
                ff=100 * fp / max(ftt, 1), n=tot, nfar=ftot, nnb=ftt, ngeo=gtot)


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


def sweep_weights(weights, device, thresholds, rows):
    """One probe pass per checkpoint; every threshold scored from it."""
    os.environ["BALLNET_WEIGHTS"] = weights
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=device)
    print(f"weights={weights}   thresholds={thresholds}\n")
    probes = {}
    for tag, video, pts in CLIPS:
        labels = REPO / "data" / "gold" / f"{tag}.labels.json"
        if not labels.exists() or not (REPO / video).exists():
            continue
        cap = cv2.VideoCapture(str(REPO / video))
        fh = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720.0
        cap.release()
        t0 = time.time()
        probes[tag] = (probe_clip(det, REPO / video, labels), labels,
                       load_H(pts), fh)
        print(f"  probed {tag} ({len(probes[tag][0])} windows) "
              f"in {time.time()-t0:.0f}s", flush=True)

    print(f"\n{'thresh':<8}{'clip':<12}{'recall':>8}{'far_px':>8}{'far_geo':>9}"
          f"{'false-fire':>12}{'composite':>11}")
    print("-" * 68)
    best = None
    for th in thresholds:
        agg = {"hit": 0, "tot": 0, "fhit": 0, "ftot": 0, "fp": 0, "ftt": 0,
               "ghit": 0, "gtot": 0}
        for tag, (probe, labels, H, fh) in probes.items():
            r = score_probe(probe, labels, th, H=H, frame_h=fh)
            geo = "      -" if r["geo"] is None else f"{r['geo']:>6.1f}%"
            print(f"{th:<8.2f}{tag:<12}{r['recall']:>7.1f}%{r['far']:>7.1f}%{geo:>9}"
                  f"{r['ff']:>11.1f}%{r['recall']-r['ff']:>10.1f}")
            rows.append({"weights": os.path.basename(weights), "clip": tag,
                         "score_thresh": th,
                         "recall": round(r["recall"], 1),
                         "far_px": round(r["far"], 1),
                         "far_geo": None if r["geo"] is None else round(r["geo"], 1),
                         "false_fire": round(r["ff"], 1),
                         "composite": round(r["recall"] - r["ff"], 1),
                         "n_ball": r["n"], "n_far": r["nfar"],
                         "n_geo": r["ngeo"], "n_noball": r["nnb"]})
            agg["hit"] += r["recall"] / 100 * r["n"]; agg["tot"] += r["n"]
            agg["fhit"] += r["far"] / 100 * r["nfar"]; agg["ftot"] += r["nfar"]
            agg["fp"] += r["ff"] / 100 * r["nnb"]; agg["ftt"] += r["nnb"]
            if r["geo"] is not None:
                agg["ghit"] += r["geo"] / 100 * r["ngeo"]; agg["gtot"] += r["ngeo"]
        pr = 100 * agg["hit"] / max(agg["tot"], 1)
        pf = 100 * agg["fp"] / max(agg["ftt"], 1)
        pgeo = ("      -" if agg["gtot"] == 0
                else f"{100*agg['ghit']/agg['gtot']:>6.1f}%")
        print(f"{th:<8.2f}{'POOLED':<12}{pr:>7.1f}%"
              f"{100*agg['fhit']/max(agg['ftot'],1):>7.1f}%{pgeo:>9}{pf:>11.1f}%"
              f"{pr-pf:>10.1f}")
        rows.append({"weights": os.path.basename(weights), "clip": "POOLED",
                     "score_thresh": th, "recall": round(pr, 1),
                     "far_px": round(100 * agg["fhit"] / max(agg["ftot"], 1), 1),
                     "far_geo": (None if agg["gtot"] == 0
                                 else round(100 * agg["ghit"] / agg["gtot"], 1)),
                     "false_fire": round(pf, 1),
                     "composite": round(pr - pf, 1),
                     "n_ball": agg["tot"], "n_far": agg["ftot"],
                     "n_geo": agg["gtot"], "n_noball": agg["ftt"]})
        if best is None or pr - pf > best[1]:
            best = (th, pr - pf)
        print("-" * 68)
    print(f"best pooled composite (recall - false-fire): {best[1]:.1f} at "
          f"score_thresh={best[0]}")
    print("Composite is a SHORTLISTING device, not the pick. Session F picks on "
          "the product metric: the ghost-ball count from eval_model_filters and "
          "tools/event_audit.py. A raw-detector composite cannot see whether a "
          "lock ever became a drawn ball or an event.")


def score_weights(weights, device, rows):
    """Print the table for one checkpoint and append its rows to `rows`."""
    os.environ["BALLNET_WEIGHTS"] = weights
    from swingvision.ball import OurBallDetector
    det = OurBallDetector(device=device)
    print(f"weights={weights}\n")
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
        rows.append({"weights": os.path.basename(weights), "clip": tag,
                     "recall": round(r["recall"], 1),
                     "far_px": round(r["far"], 1),
                     "far_geo": None if r["geo"] is None else round(r["geo"], 1),
                     "false_fire": round(r["ff"], 1),
                     "n_ball": r["n"], "n_far": r["nfar"],
                     "n_geo": r["ngeo"], "n_noball": r["nnb"]})
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
    rows.append({"weights": os.path.basename(weights), "clip": "POOLED",
                 "recall": round(100 * agg["hit"] / max(agg["tot"], 1), 1),
                 "far_px": round(100 * agg["fhit"] / max(agg["ftot"], 1), 1),
                 "far_geo": (None if agg["gtot"] == 0
                             else round(100 * agg["ghit"] / agg["gtot"], 1)),
                 "false_fire": round(100 * agg["fp"] / max(agg["ftt"], 1), 1),
                 "n_ball": agg["tot"], "n_far": agg["ftot"],
                 "n_geo": agg["gtot"], "n_noball": agg["ftt"]})
    print()
    return agg


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--weights", required=True, nargs="+",
                    help="one or more checkpoints; each is scored on every clip")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--score-thresh", type=float, nargs="+", default=None,
                    help="detector accept threshold(s). Several are FREE - the "
                         "peak position is threshold-independent, so one probe "
                         "pass scores them all. Omit to use the shipped default")
    ap.add_argument("--json", dest="json_out",
                    help="also write the table as JSON (for tools/lab_server.py)")
    args = ap.parse_args()

    rows = []
    for w in args.weights:
        if args.score_thresh:
            sweep_weights(w, args.device, args.score_thresh, rows)
        else:
            score_weights(w, args.device, rows)

    if args.json_out:
        pooled = next((r for r in rows if r["clip"] == "POOLED"), {})
        payload = {
            "tool": "eval_detector_gold",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            # ML_PRACTICES: every number states what it was measured against.
            "measured_against":
                f"human gold clicks on {len({r['clip'] for r in rows}) - 1} clips; "
                f"hit = detector peak within 10 px of the click "
                f"({pooled.get('n_ball', 0)} ball frames, "
                f"{pooled.get('n_noball', 0)} no-ball frames)",
            "weights": args.weights,
            "device": args.device,
            "rows": rows,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=1),
                                       encoding="utf-8")
        print(f"wrote {args.json_out}")

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
