"""court_contact_sheet.py — draw every committed calibration on its own clip.

WHY
---
The court numbers in this repo (detect%, kp_err, court_IoU) say how close the
lines land to a human's clicks. They do not let you SEE whether a court is right,
and a calibration can be numerically plausible and visibly wrong - which is the
whole reason `_audit` verdicts exist. This renders each committed
`data/*_pts*.json` onto a real frame of its own clip so the overlay can be judged
by eye.

Reads the same path the pipeline does: `calibration.compute_homography` from the
four doubles corners, then `overlay.draw_court`. No new geometry.

    py tools/court_contact_sheet.py --out data/output/court_sheet
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

CORNERS = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def find_video(pts: Path) -> Path | None:
    stem = pts.name
    for suf in ("_pts.json", "_pts_auto.json", "_pts_refined.json", ".json"):
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
            break
    for cand in (REPO / "data" / f"{stem}.mp4",
                 REPO / "data" / "gold_clips" / f"{stem}.mp4",
                 REPO / "data" / "train_clips" / f"{stem}.mp4"):
        if cand.exists():
            return cand
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="data/output/court_sheet")
    ap.add_argument("--frame", type=int, default=None,
                    help="frame index to draw on (default: 10%% into the clip, "
                         "which avoids black leader frames)")
    ap.add_argument("--width", type=int, default=640, help="tile width in px")
    args = ap.parse_args()

    import cv2
    from swingvision import calibration, court, overlay

    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = []

    for pts in sorted((REPO / "data").glob("*_pts*.json")):
        video = find_video(pts)
        kp = json.loads(pts.read_text(encoding="utf-8"))
        audit = kp.get("_audit", {}) or {}
        verdict = audit.get("verdict", "?")
        resid = audit.get("fit_residual_px")
        cam_h = audit.get("camera_height_m")
        if video is None:
            rows.append({"name": pts.stem, "video": None, "verdict": verdict,
                         "resid": resid, "cam_h": cam_h, "img": None,
                         "note": "no video in repo - cannot render"})
            continue
        if not all(n in kp for n in CORNERS):
            rows.append({"name": pts.stem, "video": video.name, "verdict": verdict,
                         "resid": resid, "cam_h": cam_h, "img": None,
                         "note": "missing one of the four doubles corners"})
            continue

        cap = cv2.VideoCapture(str(video))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        idx = args.frame if args.frame is not None else max(0, int(n * 0.10))
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            rows.append({"name": pts.stem, "video": video.name, "verdict": verdict,
                         "resid": resid, "cam_h": cam_h, "img": None,
                         "note": f"could not read frame {idx}"})
            continue

        H = calibration.compute_homography(
            [court.LANDMARKS[c] for c in CORNERS], [kp[c] for c in CORNERS])
        overlay.draw_court(frame, H)

        h, w = frame.shape[:2]
        scale = args.width / float(w)
        tile = cv2.resize(frame, (args.width, int(h * scale)))
        name = f"{pts.stem}.jpg"
        cv2.imwrite(str(out / name), tile, [cv2.IMWRITE_JPEG_QUALITY, 82])
        rows.append({"name": pts.stem, "video": video.name, "verdict": verdict,
                     "resid": resid, "cam_h": cam_h, "img": name,
                     "note": f"frame {idx} of {n}", "wh": f"{w}x{h}"})
        print(f"  drew {pts.stem:<28} {verdict:<12} -> {name}")

    (out / "index.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    drew = sum(1 for r in rows if r["img"])
    print(f"\n{drew} of {len(rows)} calibrations rendered -> {out}")


if __name__ == "__main__":
    main()
