"""Validate a court calibration on a new clip — the sanity gate for the overlay tool.

After you set a court with tools/court_setup_server.py (Save writes a
{landmark: [x_px, y_px]} JSON), run this to confirm the saved court is a real
camera's view of a regulation court on THIS clip, before you trust it downstream:

    backend/.venv/Scripts/python.exe tools/validate_new_clip.py \
        --keypoints court_pts.json --video clip.mp4

It reports three things, all measured (no ML):

  1. CAMERA HEIGHT — fit the physical camera (position, pan, tilt, zoom, bounded
     roll) that produces the saved corners and read its height above the court.
     A usable single-camera setup sits ~2-15 m up (a phone on a ~5 ft/1.5 m mount
     behind the baseline is ~2-3 m; stands/broadcast go higher). Outside that the
     calibration is almost certainly wrong (a court-level or impossible pose).
  2. NO HORIZON CROSSING — the projective denominator of H must keep one sign
     across the whole court (+ a margin). If it flips, part of the court projects
     through the horizon/behind the camera: the overlay tears apart and speeds /
     line calls there are meaningless.
  3. OVERLAY — draws overlay.draw_court on a mid-frame so you can SEE the fit sit
     on the paint (the Phase-1 acceptance check). Written next to --out.

Exit code 0 = all checks pass, 1 = something failed (details printed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]

# A single-camera tennis setup lives in this height band (metres above the court
# plane). Below ~2 m is court-level (the far half crushes to a few pixel rows;
# see calibration.framing_report); above ~15 m is not a realistic amateur mount.
MIN_CAM_H, MAX_CAM_H = 2.0, 15.0


def load_frame(args):
    """First/middle frame, mirroring court_setup_server.load_frame."""
    import cv2

    if args.frame:
        img = cv2.imread(args.frame)
        if img is None:
            raise SystemExit(f"cannot read image: {args.frame}")
        return img
    if args.clip:
        d = REPO / "data" / "gold" / "frames" / args.clip
        jpgs = sorted(d.glob("*.jpg"))
        if not jpgs:
            raise SystemExit(f"no frames in {d}")
        return cv2.imread(str(jpgs[len(jpgs) // 2]))
    if args.video:
        cap = cv2.VideoCapture(args.video)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if n > 1:
            cap.set(cv2.CAP_PROP_POS_FRAMES, n // 2)   # a mid-frame (rally, not intro)
        ok, im = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"cannot read {args.video}")
        return im
    raise SystemExit("pass --keypoints and one of --clip / --frame / --video")


def horizon_crosses(H, court) -> bool:
    """Does the court (+ a margin) project across the horizon under H?

    H maps court (X, Y, 1) -> image (u, v, w); the image point is (u/w, v/w).
    Everything in front of the camera shares one sign of w, and w = 0 is exactly
    the horizon preimage. So if w changes sign anywhere over the court rectangle
    plus a margin, the overlay straddles the horizon."""
    import numpy as np

    xs = np.linspace(-2.0, court.DOUBLES_WIDTH + 2.0, 12)
    ys = np.linspace(-2.0, court.LENGTH + 2.0, 24)
    XX, YY = np.meshgrid(xs, ys)
    w = H[2, 0] * XX + H[2, 1] * YY + H[2, 2]
    return not (bool((w > 0).all()) or bool((w < 0).all()))


def main() -> int:
    import numpy as np

    from swingvision import calibration, court, courtfit, overlay

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keypoints", required=True,
                    help="the {landmark: [x, y]} JSON that Save wrote")
    ap.add_argument("--clip", help="gold clip id (uses a middle frame)")
    ap.add_argument("--frame", help="path to a single image")
    ap.add_argument("--video", help="path to a video (uses a middle frame)")
    ap.add_argument("--out", default="court_overlay.png",
                    help="where the overlay PNG is written")
    args = ap.parse_args()

    raw = json.loads(Path(args.keypoints).read_text(encoding="utf-8"))
    exact = bool(raw.pop("_exact", False))
    named = {k: [float(v[0]), float(v[1])] for k, v in raw.items()
             if not k.startswith("_") and k in court.LANDMARKS}
    missing = [n for n in DBL if n not in named]
    if missing:
        print(f"FAIL: keypoints JSON is missing doubles corner(s): {missing}")
        return 1

    frame = load_frame(args)
    h, w = frame.shape[:2]
    quad = {n: named[n] for n in DBL}
    H = calibration.homography_from_landmarks(quad)

    print(f"clip frame {w}x{h}   corners {'(exact / shape-lock OFF)' if exact else ''}")
    ok = True

    # --- physical camera fit: height, hfov, roll (bounded roll = trusted path) ---
    fit = courtfit.cam_fit_quad(quad, calibration, court, w, h, allow_roll=True)
    if fit is None:
        print("FAIL: no real camera pose reproduces these corners "
              "(non-physical court shape). Re-place the corners in the overlay tool.")
        return 1   # nothing else is meaningful without a camera
    _Hc, _corners, fit_px, cam = fit
    Cz, focal, roll = abs(cam[2]), cam[5], cam[6] if len(cam) > 6 else 0.0
    hfov = calibration.hfov_from_focal(focal, w)
    h_ok = MIN_CAM_H <= Cz <= MAX_CAM_H
    ok &= h_ok
    print(f"[{'PASS' if h_ok else 'FAIL'}] camera height {Cz:5.2f} m "
          f"(want {MIN_CAM_H:g}-{MAX_CAM_H:g} m)   "
          f"hfov {hfov:.0f}deg  roll {np.degrees(roll):+.1f}deg  "
          f"physical-fit residual {fit_px:.1f}px")

    # --- horizon crossing ---
    horizon = horizon_crosses(H, court)
    ok &= not horizon
    print(f"[{'FAIL' if horizon else 'PASS'}] horizon crossing: "
          f"{'court straddles the horizon (overlay will tear)' if horizon else 'none'}")

    # --- paint coverage (does the overlay actually sit on the lines) ---
    cov_white, vis = calibration.court_line_coverage(frame, H)
    cov_clay = calibration.court_line_coverage(
        frame, H, mask_fn=lambda f: courtfit._clay_mask(f, calibration))[0]
    cov = max(cov_white, cov_clay)
    cov_ok = cov >= 0.40
    ok &= cov_ok
    print(f"[{'PASS' if cov_ok else 'WARN'}] line coverage {cov:.2f} "
          f"(white {cov_white:.2f} / clay {cov_clay:.2f}), "
          f"visible {vis:.2f}   [<0.40 = overlay is off the paint or worn clay]")

    # --- overlay render (the eyeball check) ---
    out = str(Path(args.out).resolve())
    overlay.render_overlay_image(frame, H, out, thickness=max(2, w // 640))
    print(f"overlay written -> {out}")

    print("\n" + ("VALID: all checks passed." if ok else
                  "INVALID: fix the flagged item(s) in the overlay tool, then re-validate."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
