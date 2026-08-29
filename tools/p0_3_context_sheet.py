"""Render P0-3's far-end contacts so a HUMAN can answer one question:
is the detected box on the FAR player, or on something else?

The existing sheet (`p0_3_crop_probe.py::_sheets`) shows only the 192 px window
around the ball, upscaled. That is the right view for judging box quality and the
wrong one for judging near-vs-far: with no court context you cannot tell which end
of the court you are looking at, and near-vs-far is exactly what killed the first
P0-3 probe (it detected the NEAR player and reported the far one).

So each contact gets TWO panels side by side:
  left   the whole frame, so you can see where in the court the crop sits
  right  that crop blown up, so you can see whether it is a person at all

**No court lines are drawn.** `yt_match40`'s calibration is confirmed wrong (T23) -
all four clicked corners are off any court line. Drawing it would hand the reader a
near/far cue derived from the very thing that is broken. Near/far here is judged by
eye: the far player is the one beyond the net, high in the frame.

Reads the probe's own JSON - no model runs, nothing is re-measured.

Run from the repo root:
  ./backend/.venv/Scripts/python.exe tools/p0_3_context_sheet.py \
      --probe data/output/p0_3_probe_yt_match40.json \
      --video data/incoming/Hardcourt/yt_match40.mp4 \
      --arm crop192@640_x \
      --out data/output/p0_3_context_yt_match40.png
"""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

FULL_W = 640          # left panel width; frame is 1280x720 -> 640x360
DETAIL = 360          # right panel is DETAIL x DETAIL
PAD = 6
LABEL_H = 46

GREEN = (0, 220, 0)
RED = (0, 0, 255)
MAGENTA = (255, 0, 255)
YELLOW = (0, 215, 255)
WHITE = (255, 255, 255)
GREY = (130, 130, 130)


def _read_frames(video, wanted):
    """Sequential decode only: grab() through, retrieve() at the wanted frames."""
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")
    want = sorted(set(wanted))
    out, i, k = {}, 0, 0
    while k < len(want):
        if not cap.grab():
            break
        if i == want[k]:
            ok, fr = cap.retrieve()
            if ok:
                out[i] = fr
            k += 1
        i += 1
    cap.release()
    return out


def _panel(frame, rec, arm, crop_px):
    bx, by = rec["ball_px_at_contact"]
    h = crop_px // 2
    cx0, cy0, cx1, cy1 = int(bx - h), int(by - h), int(bx + h), int(by + h)
    a = rec["arms"][arm]

    # ---- left: whole frame, downscaled ----
    full = frame.copy()
    nb = rec.get("near_player_box_full_frame")
    if nb:
        cv2.rectangle(full, (int(nb[0]), int(nb[1])), (int(nb[2]), int(nb[3])), YELLOW, 2)
        cv2.putText(full, "near player (control)", (int(nb[0]), max(12, int(nb[1]) - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, YELLOW, 1, cv2.LINE_AA)
    cv2.rectangle(full, (cx0, cy0), (cx1, cy1), WHITE, 2)
    for e in a["rejected"]:
        x1, y1, x2, y2 = e["box"]
        cv2.rectangle(full, (int(x1), int(y1)), (int(x2), int(y2)), RED, 2)
    for e in a["accepted"]:
        x1, y1, x2, y2 = e["box"]
        cv2.rectangle(full, (int(x1), int(y1)), (int(x2), int(y2)), GREEN, 2)
    cv2.drawMarker(full, (int(bx), int(by)), MAGENTA, cv2.MARKER_TILTED_CROSS, 22, 2)
    sc = FULL_W / float(full.shape[1])
    left = cv2.resize(full, (FULL_W, int(full.shape[0] * sc)), interpolation=cv2.INTER_AREA)

    # ---- right: the crop window, blown up ----
    vx1, vy1 = max(0, cx0 - 24), max(0, cy0 - 24)
    vx2, vy2 = min(frame.shape[1], cx1 + 24), min(frame.shape[0], cy1 + 24)
    sub = frame[vy1:vy2, vx1:vx2].copy()
    if sub.size == 0:
        sub = np.zeros((16, 16, 3), np.uint8)
    z = DETAIL / float(max(sub.shape[:2]))
    sub = cv2.resize(sub, (max(1, int(sub.shape[1] * z)), max(1, int(sub.shape[0] * z))),
                     interpolation=cv2.INTER_NEAREST)
    for e in a["rejected"] + a["accepted"]:
        x1, y1, x2, y2 = e["box"]
        col = GREEN if e in a["accepted"] else RED
        cv2.rectangle(sub, (int((x1 - vx1) * z), int((y1 - vy1) * z)),
                      (int((x2 - vx1) * z), int((y2 - vy1) * z)), col, 2)
    cv2.drawMarker(sub, (int((bx - vx1) * z), int((by - vy1) * z)), MAGENTA,
                   cv2.MARKER_TILTED_CROSS, 20, 2)
    right = np.zeros((DETAIL, DETAIL, 3), np.uint8)
    right[:min(DETAIL, sub.shape[0]), :min(DETAIL, sub.shape[1])] = sub[:DETAIL, :DETAIL]

    body_h = max(left.shape[0], right.shape[0])
    body = np.zeros((body_h, FULL_W + PAD + DETAIL, 3), np.uint8)
    body[:left.shape[0], :FULL_W] = left
    body[:right.shape[0], FULL_W + PAD:] = right

    # ---- label ----
    lab = np.zeros((LABEL_H, body.shape[1], 3), np.uint8)
    verdict = "PASSES the strict test" if a["found"] else "fails the strict test"
    vcol = GREEN if a["found"] else RED
    ndet = len(a["accepted"]) + len(a["rejected"])
    cv2.putText(lab, f"shot #{rec['shot_id']}  frame {rec['source_frame']}  "
                     f"t={rec['t_hit_s']:.2f}s   {ndet} detection(s) in crop", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, WHITE, 1, cv2.LINE_AA)
    why = []
    for e in a["rejected"]:
        r = []
        if not e.get("contains_contact"):
            r.append("box misses the ball anchor")
        if not e.get("small_enough"):
            r.append("too tall to be the far player")
        if not e.get("not_the_near_player"):
            r.append(f"overlaps near player (IoU {e.get('iou_with_near_player', 0):.2f})")
        why.append("; ".join(r) or "rejected")
    if not ndet:
        txt = "no detection at all inside the crop"
        vcol = GREY
    else:
        txt = verdict + (f"   -   {why[0]}" if why else "")
    cv2.putText(lab, txt[:150], (8, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.46, vcol, 1, cv2.LINE_AA)
    return np.vstack([lab, body])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--arm", default="crop192@640_x")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=2)
    args = ap.parse_args()

    d = json.load(open(args.probe, encoding="utf-8"))
    if args.arm not in d["rates"]:
        raise SystemExit(f"arm {args.arm} not in {list(d['rates'])}")
    crop_px = int(args.arm.split("@")[0].replace("crop", ""))
    recs = d["contacts"]
    frames = _read_frames(args.video, [r["source_frame"] for r in recs])
    print(f"[ctx] decoded {len(frames)} of {len(recs)} wanted frames")

    tiles = [_panel(frames[r["source_frame"]], r, args.arm, crop_px)
             for r in recs if r["source_frame"] in frames]
    if not tiles:
        raise SystemExit("no tiles")

    tw = max(t.shape[1] for t in tiles)
    th = max(t.shape[0] for t in tiles)
    norm = []
    for t in tiles:
        c = np.zeros((th, tw, 3), np.uint8)
        c[:t.shape[0], :t.shape[1]] = t
        cv2.rectangle(c, (0, 0), (tw - 1, th - 1), GREY, 1)
        norm.append(c)

    rows = []
    for i in range(0, len(norm), args.cols):
        row = norm[i:i + args.cols]
        while len(row) < args.cols:
            row.append(np.zeros_like(norm[0]))
        rows.append(np.hstack(row))
    sheet = np.vstack(rows)

    n = d["population"]["far_contacts_evaluated"]
    r = d["rates"][args.arm]
    ctrl = d["rates"]["control_full@1280"]
    head = np.zeros((104, sheet.shape[1], 3), np.uint8)
    lines = [
        (f"P0-3 context sheet   {d['video']}   arm = {args.arm}   "
         f"n = {n} far-end contacts", WHITE),
        (f"STRICT (pre-registered) test: this arm {r['found']}/{n}   |   "
         f"full-frame control {ctrl['found']}/{n}", WHITE),
        ("LEFT = whole frame (where in the court).  RIGHT = the crop, blown up "
         "(is it a person?).  No court lines drawn: this clip's calibration is wrong.", GREY),
        ("magenta X = ball at contact  |  white box = the crop window  |  "
         "yellow = near player  |  GREEN = passed strict  |  RED = detected, rejected", WHITE),
    ]
    for i, (t, col) in enumerate(lines):
        cv2.putText(head, t, (8, 20 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1, cv2.LINE_AA)

    cv2.imwrite(args.out, np.vstack([head, sheet]))
    print(f"[ctx] -> {args.out}  ({len(norm)} tiles, {sheet.shape[1]}x{sheet.shape[0] + 104})")


if __name__ == "__main__":
    main()
