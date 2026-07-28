"""validate_new_clip.py — intake gate for a clip + its court calibration, run
BEFORE it costs any labeling time (refresh-plan steps 0 and 2).

Two checks:
  0) RESOLUTION gate — is the clip genuinely higher-res than the current 720p pool?
     A 720p re-download is a no-op (the far ball stays ~2-4 px); 1080p/4K is the win.
  2) CALIBRATION sanity — does the corners file give a NON-degenerate homography?
     camera height 2-15 m, near baseline BELOW the far baseline in-frame, corners not
     left/right swapped, and every court line projects as one contiguous in-frame run
     (no horizon crossing). The degenerate data/yt_court_pts_doubles.json failed all
     of these and silently broke the court overlay + ball gating all session.

  # gate a new clip (+ optional calibration)
  cd backend && ../backend/.venv/Scripts/python.exe ../tools/validate_new_clip.py \
      ../data/<clip>.mp4 --keypoints ../data/<clip>_pts.json

  # audit existing calibration files (no video needed for the corners geometry check)
  ../backend/.venv/Scripts/python.exe ../tools/validate_new_clip.py --audit ../data/*_pts.json
"""
from __future__ import annotations
import argparse, glob, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
import numpy as np
from swingvision import calibration, court, overlay

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def resolution_gate(video):
    import cv2
    c = cv2.VideoCapture(str(video))
    w, h, fps, n = int(c.get(3)), int(c.get(4)), c.get(5) or 0, int(c.get(7))
    c.release()
    tier = "HIGH (>=1080p)" if h >= 1080 else ("720p — NO-OP vs current pool" if h >= 700
                                               else "LOW (<720p)")
    verdict = "PASS" if h >= 1080 else ("WEAK" if h >= 700 else "FAIL")
    print(f"[resolution] {w}x{h} @{fps:.0f}fps, {n} frames ({n/max(fps,1):.0f}s) -> {tier}  [{verdict}]")
    print(f"[resolution]   far-ball pixels scale ~{h/720:.1f}x vs the current 720p pool")
    return verdict


def calib_sanity(kp_path, img_wh=(1280, 720)):
    kp = json.loads(Path(kp_path).read_text(encoding="utf-8"))
    missing = [n for n in CORN if n not in kp]
    if missing:
        print(f"[calib] {Path(kp_path).name}: MISSING corners {missing}  [FAIL]")
        return "FAIL"
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN], [kp[n] for n in CORN])
    fw, fh = img_wh
    reasons = []
    # 1) camera height sane
    ch = calibration.camera_height_m(H, img_wh, 70.0)
    if ch is None or not (2.0 <= ch <= 15.0):
        reasons.append(f"camera height {ch if ch is None else round(ch,1)} m (want 2-15)")
    # 2) orientation: near baseline lower in frame than far; near-left left of near-right
    nbl = calibration.court_to_image(H, [court.LANDMARKS["near_bl_doubles"]])[0]
    nbr = calibration.court_to_image(H, [court.LANDMARKS["near_br_doubles"]])[0]
    fbl = calibration.court_to_image(H, [court.LANDMARKS["far_bl_doubles"]])[0]
    if not (nbl[1] > fbl[1]):
        reasons.append(f"near baseline not below far in frame (near y={nbl[1]:.0f}, far y={fbl[1]:.0f})")
    if not (nbl[0] < nbr[0]):
        reasons.append(f"near corners left/right swapped (bl x={nbl[0]:.0f} >= br x={nbr[0]:.0f})")
    # 3) every court line projects as ONE contiguous in-frame run (no horizon crossing)
    bad = 0
    for a, b in court.LINES:
        runs = overlay._project_court_line(H, a, b, (fw, fh))
        if len(runs) != 1:
            bad += 1
    if bad:
        reasons.append(f"{bad}/{len(court.LINES)} court lines cross the horizon / go off-frame")
    ok = not reasons
    print(f"[calib] {Path(kp_path).name}: camera ~{('?' if ch is None else round(ch,1))} m "
          f"-> {'PASS' if ok else 'DEGENERATE'}")
    for r in reasons:
        print(f"[calib]     - {r}")
    return "PASS" if ok else "FAIL"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", nargs="?", help="clip to resolution-gate")
    ap.add_argument("--keypoints", help="court corners JSON to sanity-check")
    ap.add_argument("--audit", nargs="*", help="calibration files to audit (geometry only)")
    ap.add_argument("--img-wh", default="1280x720", help="frame size for the calib geometry check")
    args = ap.parse_args()
    fw, fh = (int(v) for v in args.img_wh.lower().split("x"))

    results = []
    if args.video:
        results.append(resolution_gate(args.video))
        if args.keypoints:
            import cv2
            c = cv2.VideoCapture(str(args.video)); fw, fh = int(c.get(3)), int(c.get(4)); c.release()
    if args.keypoints:
        results.append(calib_sanity(args.keypoints, (fw, fh)))
    for f in (args.audit or []):
        results.append(calib_sanity(f, (fw, fh)))
    if not results:
        ap.error("give a video, --keypoints, and/or --audit")
    print(f"\nSUMMARY: {results.count('PASS')} pass, {results.count('WEAK')} weak, "
          f"{results.count('FAIL')} fail")


if __name__ == "__main__":
    main()
