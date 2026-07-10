"""Score the court detector against the human COURT gold labels.

The court analogue of eval_gold.py. For each clip you have court-labeled with
gold_label_server.py (the "Court quality" page), this runs the pipeline's court
detector (calibration.detect_court_keypoints — the learned CourtNet when a
checkpoint is present, else the classical detector) on the same frames and
compares its 14 keypoints to your clicks.

Reported per clip and overall, on USABLE frames (you marked a court):
  detect%    the detector returned a court at all (didn't refuse / fail)
  kp_err     median pixel error over all 14 keypoints, on detected frames
  corner_err median pixel error over the 4 baseline corners (the shape)
  within%    fraction of keypoints within --tol px of the human click
  court_IoU  overlap of the detected doubles-court polygon with the human one
             (1.0 = identical outline, 0 = no overlap) - the headline "is the
             court right" number

And on frames you marked NOT USABLE (court absent/occluded):
  false%     the detector nonetheless returned a court (a confidently-wrong
             overlay - what the white-paint self-check should prevent)

Errors are in the frame's own pixels; amateur clips here are 640x360, so ~6 px
is ~1% of the width. Usage (repo root, backend venv for torch/cv2):

  backend/.venv/Scripts/python.exe tools/eval_court.py am_rec30 am_ntrp45_courtlevel
  backend/.venv/Scripts/python.exe tools/eval_court.py --all --tol 8 --markdown court_scores.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

GOLD = REPO / "data" / "gold"
CORNER_NAMES = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def poly_area(poly: list[tuple[float, float]]) -> float:
    """Shoelace area of a polygon."""
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def clip_polygon(subject: list, clipper: list) -> list:
    """Sutherland-Hodgman: intersect convex subject with convex clipper."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def isect(p1, p2, a, b):
        x1, y1 = p1; x2, y2 = p2; x3, y3 = a; x4, y4 = b
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            return p2
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    # ensure clipper is counter-clockwise (inside() assumes it)
    if poly_signed_area(clipper) < 0:
        clipper = clipper[::-1]
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        for j in range(len(inp)):
            cur, prv = inp[j], inp[j - 1]
            if inside(cur, a, b):
                if not inside(prv, a, b):
                    out.append(isect(prv, cur, a, b))
                out.append(cur)
            elif inside(prv, a, b):
                out.append(isect(prv, cur, a, b))
        if not out:
            return []
    return out


def poly_signed_area(poly: list) -> float:
    a = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def quad_iou(a: list, b: list) -> float:
    inter = clip_polygon(a, b)
    if len(inter) < 3:
        return 0.0
    ai = poly_area(inter)
    return ai / (poly_area(a) + poly_area(b) - ai + 1e-9)


def dist(p, q) -> float:
    return ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5


_WEIGHTS = str(REPO / "backend" / "weights" / "court_detector.pt")


def _detect(calibration, img, learned: bool, kw: dict):
    """Return the 14-keypoint dict from the chosen detector, or None."""
    if learned:
        det = calibration.detect_court_learned(img, weights=_WEIGHTS)
        return det.keypoints if det is not None else None
    return calibration.detect_court_keypoints(img, **kw)


def score_clip(clip: str, tol: float, min_conf: float | None,
               learned: bool = False) -> dict | None:
    man_path = GOLD / f"{clip}.court.manifest.json"
    lab_path = GOLD / f"{clip}.court.labels.json"
    if not man_path.exists():
        print(f"  {clip}: no court manifest, skip"); return None
    if not lab_path.exists():
        print(f"  {clip}: no labels yet, skip"); return None

    import cv2
    from swingvision import calibration

    man = load(man_path)
    labels = load(lab_path)["labels"]
    frames_dir = GOLD / "frames" / clip

    usable = {k: v for k, v in labels.items() if v.get("court") is True}
    unusable = [k for k, v in labels.items() if v.get("court") is False]

    kp_errs, corner_errs, ious = [], [], []
    within = tot_kp = detected = 0
    false_court = 0

    kw = {} if min_conf is None else {"min_confidence": min_conf}

    for key, lab in usable.items():
        img = cv2.imread(str(frames_dir / f"f{int(key):05d}.jpg"))
        if img is None:
            continue
        pred = _detect(calibration, img, learned, kw)
        if pred is None:
            continue
        detected += 1
        gk = lab["keypoints"]
        for name, gxy in gk.items():
            if name in pred:
                e = dist(pred[name], gxy)
                kp_errs.append(e); tot_kp += 1
                if e <= tol:
                    within += 1
        corner_errs += [dist(pred[n], gk[n]) for n in CORNER_NAMES if n in pred and n in gk]
        if all(n in pred for n in CORNER_NAMES):
            ious.append(quad_iou([tuple(pred[n]) for n in CORNER_NAMES],
                                 [tuple(gk[n]) for n in CORNER_NAMES]))

    for key in unusable:
        img = cv2.imread(str(frames_dir / f"f{int(key):05d}.jpg"))
        if img is None:
            continue
        if _detect(calibration, img, learned, kw) is not None:
            false_court += 1

    return {
        "clip": clip,
        "usable": len(usable),
        "detected": detected,
        "detect_pct": 100 * detected / len(usable) if usable else 0.0,
        "kp_err": median(kp_errs) if kp_errs else None,
        "corner_err": median(corner_errs) if corner_errs else None,
        "within_pct": 100 * within / tot_kp if tot_kp else 0.0,
        "iou": median(ious) if ious else None,
        "unusable": len(unusable),
        "false_pct": 100 * false_court / len(unusable) if unusable else None,
    }


def fmt(x, s="{:.1f}"):
    return "  -  " if x is None else s.format(x)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="*", help="clip ids (default: --all)")
    ap.add_argument("--all", action="store_true", help="every *.court.labels.json in data/gold")
    ap.add_argument("--tol", type=float, default=8.0, help="within-tolerance px (default 8)")
    ap.add_argument("--min-confidence", type=float, default=None,
                    help="override the detector confidence gate")
    ap.add_argument("--learned", action="store_true",
                    help="test the learned CourtNet (detect_court_learned) instead "
                         "of the classical detector")
    ap.add_argument("--markdown", default=None)
    args = ap.parse_args()

    clips = args.clips
    if args.all or not clips:
        clips = sorted(p.name[:-len(".court.labels.json")]
                       for p in GOLD.glob("*.court.labels.json"))
    if not clips:
        raise SystemExit("no court-labeled clips found (label some first, then re-run)")

    rows = [r for c in clips
            if (r := score_clip(c, args.tol, args.min_confidence, args.learned))]
    if not rows:
        raise SystemExit("no scorable clips (need at least one with labels)")

    hdr = (f"{'clip':22s} {'usable':>6s} {'detect%':>7s} {'kp_err':>7s} "
           f"{'corner':>7s} {'within%':>7s} {'court_IoU':>9s} {'false%':>7s}")
    lines = [hdr, "-" * len(hdr)]
    for r in rows:
        lines.append(
            f"{r['clip']:22s} {r['usable']:6d} {fmt(r['detect_pct']):>7s} "
            f"{fmt(r['kp_err']):>7s} {fmt(r['corner_err']):>7s} "
            f"{fmt(r['within_pct']):>7s} {fmt(r['iou'],'{:.3f}'):>9s} "
            f"{fmt(r['false_pct']):>7s}")
    out = "\n".join(lines)
    print(out)
    print(f"\ntol={args.tol}px  |  detect%/within%/IoU higher=better  |  "
          f"kp_err/corner/false% lower=better")

    if args.markdown:
        Path(args.markdown).write_text("```\n" + out + "\n```\n", encoding="utf-8")
        print(f"\nwrote {args.markdown}")


if __name__ == "__main__":
    main()
