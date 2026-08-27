"""Render the P0-3 contact POPULATION so a human can check it before any A/B runs.

The first P0-3 probe died of an unchecked population (193 of 196 contacts called
"far" on a real match). This renders each candidate contact as a full frame with:
  white       the court lines projected through the calibration
  yellow      the NET line (the near/far boundary)
  cyan poly   the ball's raw image track over +/- WINDOW processed frames
  magenta X   the ball at the contact frame
  red X       where the GROUND-projected hit_xy lands (the old, broken criterion)
Label carries the ball-derived end call and both image-y slopes.

Sequential decode only (`grab`/`retrieve`), no random seeking.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from swingvision import calibration, court                      # noqa: E402
from swingvision.pipeline import calibrate_video                 # noqa: E402
from p0_3_population import WINDOW, classify_contacts, load      # noqa: E402

TILE_W = 640
COLS = 3


def _draw_court(img, H, scale, color=(255, 255, 255)):
    for (a, b) in court.LINES:
        pa, pb = calibration.court_to_image(H, [a, b])
        cv2.line(img, (int(pa[0] * scale), int(pa[1] * scale)),
                 (int(pb[0] * scale), int(pb[1] * scale)), color, 1, cv2.LINE_AA)
    na, nb = calibration.court_to_image(H, [(0.0, court.NET_Y),
                                            (court.DOUBLES_WIDTH, court.NET_Y)])
    cv2.line(img, (int(na[0] * scale), int(na[1] * scale)),
             (int(nb[0] * scale), int(nb[1] * scale)), (0, 255, 255), 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--perception", default=None)
    ap.add_argument("--video", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--end", default="far", choices=["far", "near", "undecided", "all"])
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()

    match, perception = load(args.match, args.perception)
    recs = classify_contacts(match, perception)
    ball_px = perception["ball_px"]
    frame_step = int(perception.get("frame_step", 1))
    H, err, src, _named, hfov, k1, _Hund = calibrate_video(args.video, args.keypoints, None)
    print(f"[calib] residual {err:.2f}px source={src} hfov={hfov} k1={k1}")

    sel = [r for r in recs if args.end == "all" or r["end"] == args.end]
    sel = [r for r in sel if r.get("ball_px_at_contact")]
    if not sel:
        print("no contacts of that class")
        return
    step = max(1, len(sel) // args.n)
    sel = sel[::step][: args.n]
    wanted = {r["source_frame"]: r for r in sel}

    cap = cv2.VideoCapture(args.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    Hh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = TILE_W / float(W)
    tiles = []
    idx = 0
    remaining = set(wanted)
    while remaining:
        ok = cap.grab()
        if not ok:
            break
        if idx in remaining:
            ok, frame = cap.retrieve()
            remaining.discard(idx)
            if ok:
                r = wanted[idx]
                img = cv2.resize(frame, (TILE_W, int(Hh * scale)))
                _draw_court(img, H, scale)
                pi = r["processed_index"]
                pts = [(int(ball_px[j][0] * scale), int(ball_px[j][1] * scale))
                       for j in range(max(0, pi - WINDOW), min(len(ball_px), pi + WINDOW + 1))
                       if ball_px[j] is not None]
                for a, b in zip(pts, pts[1:]):
                    cv2.line(img, a, b, (255, 255, 0), 1, cv2.LINE_AA)
                for p in pts:
                    cv2.circle(img, p, 2, (255, 255, 0), -1)
                bx, by = r["ball_px_at_contact"]
                cv2.drawMarker(img, (int(bx * scale), int(by * scale)),
                               (255, 0, 255), cv2.MARKER_TILTED_CROSS, 22, 2)
                if r.get("hit_xy_court"):
                    gp = calibration.court_to_image(H, [r["hit_xy_court"]])[0]
                    cv2.drawMarker(img, (int(gp[0] * scale), int(gp[1] * scale)),
                                   (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
                cv2.putText(img, f"#{r['shot_id']} {r['end']} f{idx} t={r['t_hit_s']:.1f}s "
                                 f"pre{r.get('slope_pre_px_per_frame')} post{r.get('slope_post_px_per_frame')}",
                            (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1, cv2.LINE_AA)
                tiles.append(img)
        idx += 1
    cap.release()

    if not tiles:
        print("no tiles")
        return
    rows = []
    for i in range(0, len(tiles), COLS):
        row = tiles[i:i + COLS]
        while len(row) < COLS:
            row.append(np.zeros_like(tiles[0]))
        rows.append(np.hstack(row))
    sheet = np.vstack(rows)
    legend = np.zeros((30, sheet.shape[1], 3), np.uint8)
    cv2.putText(legend, "yellow=NET  cyan=ball track +/-5f  magentaX=ball at contact  "
                        "redX=ground-projected hit_xy (old criterion)",
                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(args.out, np.vstack([legend, sheet]))
    print(f"wrote {args.out} ({len(tiles)} tiles)")


if __name__ == "__main__":
    main()
