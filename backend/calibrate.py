"""calibrate.py — manual court calibration.

Open the first frame of a video, click the court landmarks in the order printed,
and save the clicked pixel positions to a JSON file:

    python calibrate.py match.mp4 --out court_pts.json

Output is {landmark: [x_px, y_px]} for names in court.LANDMARKS — exactly what
`run.py analyze --keypoints` expects. The homography solve is the existing,
tested calibration.compute_homography; this tool only collects the clicks.

Controls: left-click to place the next landmark · u = undo · s = save & quit ·
ESC = quit without saving. You can skip a hidden landmark with the SPACE key
(min 4 needed for a solve).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from swingvision import calibration, court


def _first_frame(video_path: str):
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"could not open video: {video_path!r}")
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("could not read the first frame")
    return frame


def collect_clicks(frame, names: list[str]):
    """Interactive click collection. Returns {name: [x, y]} for placed points."""
    import cv2

    points: dict[str, list[float]] = {}
    order = list(names)
    idx = {"i": 0}
    base = frame.copy()

    def redraw():
        img = base.copy()
        for n, (x, y) in points.items():
            cv2.circle(img, (int(x), int(y)), 5, (40, 120, 255), -1, cv2.LINE_AA)
            cv2.putText(img, n, (int(x) + 6, int(y) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (40, 120, 255), 1, cv2.LINE_AA)
        if idx["i"] < len(order):
            cv2.putText(img, f"click: {order[idx['i']]}", (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 255, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(img, "all placed - press 's' to save", (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 255, 60), 2, cv2.LINE_AA)
        cv2.imshow("calibrate", img)

    def on_mouse(event, x, y, flags, _):
        if event == cv2.EVENT_LBUTTONDOWN and idx["i"] < len(order):
            points[order[idx["i"]]] = [float(x), float(y)]
            idx["i"] += 1
            redraw()

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_mouse)
    redraw()
    while True:
        key = cv2.waitKey(20) & 0xFF
        if key == 27:                       # ESC -> abort
            cv2.destroyAllWindows()
            return None
        if key in (ord("s"), 13):           # s / Enter -> done
            break
        if key == ord("u") and idx["i"] > 0:  # undo
            idx["i"] -= 1
            points.pop(order[idx["i"]], None)
            redraw()
        if key == ord(" ") and idx["i"] < len(order):  # skip a hidden landmark
            idx["i"] += 1
            redraw()
    cv2.destroyAllWindows()
    return points


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manual court calibration")
    parser.add_argument("video", help="input video path")
    parser.add_argument("--out", required=True, help="output keypoints JSON path")
    parser.add_argument("--overlay", help="optional path to write an overlay preview PNG")
    args = parser.parse_args(argv)

    print("Landmarks to click, in order:")
    for n in court.landmark_names():
        print(f"  - {n}  (court {court.LANDMARKS[n]})")

    frame = _first_frame(args.video)
    points = collect_clicks(frame, court.landmark_names())
    if not points:
        print("aborted; nothing saved.", file=sys.stderr)
        return 1
    if len(points) < 4:
        print(f"need >=4 points, got {len(points)}.", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(points, f, indent=2)

    H = calibration.homography_from_landmarks(points)
    err = calibration.reprojection_error(
        H, [court.LANDMARKS[n] for n in points], [points[n] for n in points]
    )
    print(f"saved {len(points)} points -> {args.out}")
    print(f"reprojection error = {err:.2f} px")

    if args.overlay:
        from swingvision import overlay

        overlay.render_overlay_image(frame, H, args.overlay)
        print(f"overlay preview -> {args.overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
