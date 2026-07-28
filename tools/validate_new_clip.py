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


def frame_size_for(kp_path, default):
    """Frame size of the clip a corners file belongs to, from data/<tag>.mp4.

    The corners are pixel coordinates, so every geometric check here is
    resolution-dependent — auditing a 1080p calibration as if it were 720p reads
    the camera ~20% too high. Falls back to `default` when the clip isn't found.
    """
    tag = Path(kp_path).name.split("_pts")[0]
    vid = REPO / "data" / f"{tag}.mp4"
    if not vid.exists():
        return default, False
    import cv2
    c = cv2.VideoCapture(str(vid))
    w, h = int(c.get(3)), int(c.get(4))
    c.release()
    return ((w, h), True) if w and h else (default, False)


MAX_FIT_PX = 10.0   # beyond this the corners are not any real camera's view
MAX_CAM_H = 15.0    # above this it is not a court-side mount


def camera_fit(kp, img_wh):
    """Fit the physical camera that produces these corners.

    courtfit.cam_fit_quad solves for position, pan, tilt, zoom and bounded roll,
    so it reads the focal off the geometry instead of assuming one. Two things
    come back that the old 70-degree assumption could not give:

      * an honest height — on am_hard_utr the assumption reads 2.1 m, the fit
        reads 1.74 m at hfov 86 deg, either side of the 2 m advice floor;
      * fit_px, the distance from the given quad to the NEAREST legal camera
        view. That residual is the real degeneracy test, and it separates the
        known files cleanly: every KNOWN GOOD calibration fits within 2.5 px
        (yt_match40 0.9, yt_rally2 1.4, yt_court 2.1) and every KNOWN BAD one is
        an order of magnitude out (doubles 54, singles 91, demo30 565). A quad
        no camera can produce has no meaningful height to check.

    Returns (height_m, fit_px, description) — height/fit_px are None if the
    solve is unavailable (needs scipy) or refuses.
    """
    try:
        from swingvision import courtfit
        fit = courtfit.cam_fit_quad({n: kp[n] for n in CORN}, calibration, court,
                                    img_wh[0], img_wh[1], allow_roll=True)
        if fit is not None:
            cam = fit[3]
            hfov = calibration.hfov_from_focal(cam[5], img_wh[0])
            roll = np.degrees(cam[6]) if len(cam) > 6 else 0.0
            return (abs(float(cam[2])), float(fit[2]),
                    f"hfov {hfov:.0f}deg roll {roll:+.1f}deg fit {fit[2]:.1f}px")
    except Exception:
        pass
    return None, None, "camera fit unavailable"


def calib_sanity(kp_path, img_wh=(1280, 720)):
    kp = json.loads(Path(kp_path).read_text(encoding="utf-8"))
    missing = [n for n in CORN if n not in kp]
    if missing:
        print(f"[calib] {Path(kp_path).name}: MISSING corners {missing}  [FAIL]")
        return "FAIL"
    H = calibration.compute_homography([court.LANDMARKS[n] for n in CORN], [kp[n] for n in CORN])
    fw, fh = img_wh
    reasons, warns = [], []
    # 1) is this quad a real camera's view at all, and how high is that camera?
    ch, fit_px, lens = camera_fit(kp, img_wh)
    if fit_px is not None and fit_px > MAX_FIT_PX:
        reasons.append(f"corners are not a physical camera view (fit residual {fit_px:.0f} px)")
    elif ch is not None and ch > MAX_CAM_H:
        reasons.append(f"camera height {ch:.1f} m (above {MAX_CAM_H:.0f} m is not a court-side mount)")
    elif ch is not None and ch < 2.0:
        # A low camera is USABLE, not broken — a phone clamped to a fence is the
        # footage this project targets. What it costs is measurable depth, so say
        # that in metres instead of failing the file.
        frac, until = calibration.reliable_court_span(H)
        warns.append(f"low camera {ch:.2f} m — measurable to court-y {until:.1f} m "
                     f"of {court.LENGTH:.1f} ({100*frac:.0f}% of depth)")
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
    verdict = "DEGENERATE" if reasons else ("LOW-CAMERA" if warns else "PASS")
    print(f"[calib] {Path(kp_path).name}: camera ~{('?' if ch is None else round(ch, 2))} m "
          f"@{fw}x{fh} ({lens}) -> {verdict}")
    for r in reasons + warns:
        print(f"[calib]     - {r}")
    return "FAIL" if reasons else ("WEAK" if warns else "PASS")


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
        # Each audited file gets ITS OWN clip's frame size where we can find it —
        # one --img-wh for a mixed 720p/1080p batch mis-measures every camera.
        wh, found = frame_size_for(f, (fw, fh))
        if not found:
            print(f"[calib] {Path(f).name}: no data/<tag>.mp4 — assuming {wh[0]}x{wh[1]}")
        results.append(calib_sanity(f, wh))
    if not results:
        ap.error("give a video, --keypoints, and/or --audit")
    print(f"\nSUMMARY: {results.count('PASS')} pass, {results.count('WEAK')} weak, "
          f"{results.count('FAIL')} fail")


if __name__ == "__main__":
    main()
