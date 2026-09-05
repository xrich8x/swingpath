"""Render every calibration's CLICKED CORNERS onto a real frame, so a human can
audit them by looking instead of by reading a residual.

This exists because of trap T23. `data/yt_match40_pts.json` is stamped PASS at a
**0.9 px** fit residual with all four clicked corners off any court line. A residual
only asks whether four points form a plausible court; four points on a plausible
trapezoid in the wrong place fit perfectly. The pipeline then put the net line
35-75 px low and labelled the NEAR player FAR, and P0-2 published that mislabel as
an 11.0% far-player detection rate.

So: `validate_new_clip.py --audit` is a screen, not a verdict. The verdict is the
frame. This tool renders it.

What is drawn, and deliberately what is not:
  * the four clicked corners, each labelled by name, as a cross plus a ring
  * the quad they form, edge by edge
  * NOTHING derived from the homography - no projected court model, no net line.
    A projected court is a *consequence* of the clicks. Drawing it invites the
    reader to check the clicks against the thing the clicks produced, which is
    circular, and is close to how T23 survived a written gate in the first place.
    The reader's job is only: does each corner sit on the court line it is named
    for? That is answerable from paint and clicks alone.

Corners off-frame are normal on a low wide mount (`am_hard_utr` clicks x=-41 and
x=2090 on a 1920-wide frame) and are reported in the caption rather than drawn, so
their absence is never read as a missing click.

Run from the repo root:
  ./backend/.venv/Scripts/python.exe tools/render_corner_audit.py
  ./backend/.venv/Scripts/python.exe tools/render_corner_audit.py --pts data/yt_match40_pts.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import cv2
import numpy as np

import net_anchor_check

REPO = pathlib.Path(__file__).resolve().parents[1]

CORNERS = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
COL = {
    "near_bl_doubles": (80, 255, 80),
    "near_br_doubles": (80, 255, 255),
    "far_br_doubles": (255, 160, 80),
    "far_bl_doubles": (255, 80, 255),
}
WHITE = (255, 255, 255)
GREY = (140, 140, 140)
RED = (0, 0, 255)
AMBER = (0, 190, 255)


def find_video(tag):
    """Same recursive search validate_new_clip.py uses - a hard-coded directory
    list has broken twice here when data/ was reorganised."""
    cands = [REPO / "data" / f"{tag}.mp4"]
    for sub in ("incoming", "train_clips", "gold_clips", "amateur_clips", "gold"):
        d = REPO / "data" / sub
        if d.is_dir():
            cands += sorted(d.rglob(f"{tag}.mp4"))
    for v in cands:
        if v.exists():
            return v
    return None


def grab_frame(video, index=0):
    """Sequential decode, no seeking."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    fr = None
    for i in range(index + 1):
        ok, f = cap.read()
        if not ok:
            break
        fr = f
    cap.release()
    return fr


def render(pts_path, frame_index, out_dir):
    tag = pts_path.stem.replace("_pts", "")
    blob = json.loads(pts_path.read_text(encoding="utf-8"))
    kp = {k: blob[k] for k in CORNERS if k in blob}
    if len(kp) < 4:
        return {"tag": tag, "status": "SKIP", "note": f"only {len(kp)}/4 named corners"}

    video = find_video(tag)
    if video is None:
        return {"tag": tag, "status": "NO VIDEO", "note": "no matching .mp4 found"}
    frame = grab_frame(video, frame_index)
    if frame is None:
        return {"tag": tag, "status": "NO FRAME", "note": f"cannot decode {video.name}"}

    h, w = frame.shape[:2]
    img = frame.copy()
    audit = blob.get("_audit", {})
    stamped_wh = audit.get("img_wh")
    # A calibration clicked at one resolution and rendered at another lands
    # nowhere. This is the exact failure the auditor's own comments describe.
    sx = sy = 1.0
    if stamped_wh and (stamped_wh[0] != w or stamped_wh[1] != h):
        sx, sy = w / float(stamped_wh[0]), h / float(stamped_wh[1])

    off = []
    P = {}
    for name in CORNERS:
        x, y = kp[name][0] * sx, kp[name][1] * sy
        P[name] = (x, y)
        if not (0 <= x < w and 0 <= y < h):
            off.append(name)

    for a, b in zip(CORNERS, CORNERS[1:] + CORNERS[:1]):
        cv2.line(img, tuple(np.int32(P[a])), tuple(np.int32(P[b])), WHITE, 2, cv2.LINE_AA)
    for name in CORNERS:
        x, y = np.int32(P[name])
        if 0 <= x < w and 0 <= y < h:
            cv2.drawMarker(img, (x, y), COL[name], cv2.MARKER_CROSS, 34, 2)
            cv2.circle(img, (x, y), 15, COL[name], 2, cv2.LINE_AA)
            cv2.putText(img, name.replace("_doubles", ""), (x + 19, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, COL[name], 2, cv2.LINE_AA)

    scale = 1280.0 / w
    if abs(scale - 1.0) > 0.01:
        img = cv2.resize(img, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

    cap_h = 118
    cap = np.zeros((cap_h, img.shape[1], 3), np.uint8)
    verdict = audit.get("verdict", "not stamped")
    resid = audit.get("fit_residual_px")
    camh = audit.get("camera_height_m")
    vcol = AMBER if verdict != "PASS" else GREY
    rows = [
        (f"{tag}   {video.name}   frame {frame_index}   {w}x{h}", WHITE),
        (f"stamped: {verdict}"
         + (f"   residual {resid} px" if resid is not None else "")
         + (f"   camera {camh} m" if camh is not None else "")
         + ("   [clicked at %dx%d, RESCALED to render]" % tuple(stamped_wh)
            if sx != 1.0 or sy != 1.0 else ""), vcol),
        ("THE RESIDUAL IS NOT THE VERDICT (T23). Ask only: does each corner sit on "
         "the court line it is named for?", GREY),
        (("off-frame, not drawn: " + ", ".join(n.replace("_doubles", "") for n in off)
          + "  (normal on a low wide mount)") if off else
         "all four corners are inside the frame", AMBER if off else GREY),
    ]
    for i, (t, c) in enumerate(rows):
        cv2.putText(cap, t, (8, 22 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, c, 1, cv2.LINE_AA)

    out = out_dir / f"{tag}_corners.png"
    cv2.imwrite(str(out), np.vstack([cap, img]))
    flag = "CHECK" if (camh is not None and camh > 6.0) else "ok"
    return {"tag": tag, "status": "rendered", "out": out.name, "verdict": verdict,
            "residual_px": resid, "camera_h_m": camh, "off_frame": off, "flag": flag}


def render_net_anchors(pts_path, frame_index, out_dir):
    """The NET-ANCHOR check, rendered to its OWN image.

    Deliberately a separate PNG from the corner sheet above. The corner sheet's
    entire value is that it shows evidence and clicks and nothing derived from
    them; mixing a projection into it would re-create the confusion it exists to
    prevent. This image is the complementary question: given those clicks, does
    the NET land on the net? See tools/net_anchor_check.py for why that is not
    circular and what the two pre-registered bars are.
    """
    tag = pts_path.stem.replace("_pts", "")
    blob = json.loads(pts_path.read_text(encoding="utf-8"))
    kp = {k: blob[k] for k in CORNERS if k in blob}
    if len(kp) < 4:
        return {"tag": tag, "status": "SKIP", "note": f"only {len(kp)}/4 named corners"}
    video = find_video(tag)
    if video is None:
        return {"tag": tag, "status": "NO VIDEO", "note": "no matching .mp4 found"}
    frame = grab_frame(video, frame_index)
    if frame is None:
        return {"tag": tag, "status": "NO FRAME", "note": f"cannot decode {video.name}"}

    h, w = frame.shape[:2]
    audit = blob.get("_audit", {})
    stamped_wh = audit.get("img_wh")
    sx = sy = 1.0
    if stamped_wh and (stamped_wh[0] != w or stamped_wh[1] != h):
        sx, sy = w / float(stamped_wh[0]), h / float(stamped_wh[1])
    kp = {n: (kp[n][0] * sx, kp[n][1] * sy) for n in CORNERS}

    hfov = net_anchor_check.hfov_for(kp, w, h)
    meas, geo = net_anchor_check.measure(frame, kp, (w, h), hfov)
    rows = [
        (f"{tag}   {video.name}   frame {frame_index}   {w}x{h}   "
         + (f"hfov {hfov:.0f}deg (fitted)" if hfov else "hfov UNKNOWN"), WHITE),
        (f"stamped {audit.get('verdict', 'not stamped')} at "
         f"{audit.get('fit_residual_px')} px, camera {audit.get('camera_height_m')} m"
         f"   |   band_ratio {meas['band_ratio']}   best {meas['ratio_best']} at "
         f"dy {meas['dy_best']}   net {meas['net_px_height']} px", GREY),
        (f"rows: horizon {meas['horizon_row']}   net GROUND {meas['net_ground_row']}   "
         f"net TAPE {meas['net_tape_row']}   (tape = horizon + (ground-horizon)*(H-0.914)/H)",
         GREY),
        ("NET AND POSTS ARE NOT FITTED POINTS. Ask only: does the YELLOW tape line lie "
         "along the real white tape, and do the red sticks stand on the real posts?", GREY),
        ("Do NOT read the GREEN ground line against the tape - that is the apples-to-"
         "oranges error; the tape is 0.914 m up and MUST image higher.", AMBER),
    ]
    out = out_dir / f"{tag}_netanchor.png"
    cv2.imwrite(str(out), net_anchor_check.draw(frame, geo, meas, rows))
    return {"tag": tag, "status": "rendered", "out": out.name,
            "verdict": audit.get("verdict"),
            "residual_px": audit.get("fit_residual_px"),
            "camera_h_m": audit.get("camera_height_m"),
            "hfov_deg": None if hfov is None else round(hfov, 1),
            **meas, "flag": "FLAG" if meas["flags"] else "ok"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pts", nargs="*", default=None)
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--out-dir", default="data/output/corner_audit")
    ap.add_argument("--net-anchors", action="store_true",
                    help="render the NET-ANCHOR check instead: the net line and "
                         "both net posts, none of which is one of the four fitted "
                         "corners, drawn over the frame and measured")
    args = ap.parse_args()

    files = ([pathlib.Path(p) for p in args.pts] if args.pts
             else sorted((REPO / "data").rglob("*_pts.json")))
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    fn = render_net_anchors if args.net_anchors else render
    rows = []
    for f in files:
        try:
            rows.append(fn(f, args.frame, out_dir))
        except Exception as e:                       # noqa: BLE001
            rows.append({"tag": f.stem, "status": "ERROR", "note": repr(e)[:110]})
        r = rows[-1]
        note = (f"ratio {r.get('band_ratio')} dy {r.get('dy_best')} {r.get('flag')}"
                if args.net_anchors and r["status"] == "rendered"
                else r.get("verdict", r.get("note", "")))
        print(f"  {r['tag']:28s} {r['status']:9s} {note}")

    if args.net_anchors:
        done = [r for r in rows if r["status"] == "rendered"]
        flagged = [r for r in done if r["flag"] == "FLAG"]
        print(f"\n[net] {len(done)} rendered of {len(files)} -> {out_dir}")
        print(f"[net] {len(flagged)} FLAGGED by the pre-registered bars "
              f"(band_ratio < {net_anchor_check.BAR_BAND_RATIO}, or |dy| > "
              f"{net_anchor_check.BAR_DY_FRAC} x net px height):")
        for r in flagged:
            print(f"      {r['tag']:28s} ratio {r['band_ratio']} -> {r['ratio_best']} "
                  f"at dy {r['dy_best']}  netpx {r['net_px_height']}  "
                  f"stamped {r['verdict']} @ {r['residual_px']} px")
        print("[net] A BAR IS A TRIAGE ORDER, NOT A VERDICT - open the PNG (T23).")
        (out_dir / "net_index.json").write_text(json.dumps(rows, indent=2),
                                                encoding="utf-8")
        return 0

    done = [r for r in rows if r["status"] == "rendered"]
    tall = [r for r in done if r["flag"] == "CHECK"]
    print(f"\n[corners] {len(done)} rendered of {len(files)} -> {out_dir}")
    if tall:
        # An implausible camera height was the ONE real signal the T23 audit gave
        # and it was ignored, so surface it here rather than leaving it in a field.
        print("[corners] implausibly TALL camera for a court-side mount - look at "
              "these first:")
        for r in tall:
            print(f"          {r['tag']:28s} {r['camera_h_m']} m   "
                  f"stamped {r['verdict']} at {r['residual_px']} px")
    (out_dir / "index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
