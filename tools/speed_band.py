"""speed_band.py — calibrate (and sanity-check) the reported speed uncertainty.

The dashboard suppresses a speed unless `speed_confident`, and on a low camera
that is never true, so it shows 0.0 km/h while holding usable numbers. To show a
number honestly we need to say what it is worth. This measures that against the
only independent speed reference we have: SwingVision's burned-in HUD.

    backend/.venv/Scripts/python.exe tools/speed_band.py \\
        --match data/output/rally2_dash.json \\
        --hud data/gold/hud_yt_rally2.json \\
        --keypoints data/yt_rally2_pts.json

It also tests whether each confidence signal actually PREDICTS error, which is the
question that decides between one global band and a graded one. Read the caveat at
the bottom of the output before quoting anything from here: the HUD is itself a
single-camera estimate, not radar, and there are only 17 strokes on one clip.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import calibration, court  # noqa: E402

CORN = ("near_bl_doubles", "near_br_doubles", "far_bl_doubles", "far_br_doubles")


def load_H(pts_path):
    kp = json.loads(Path(pts_path).read_text(encoding="utf-8"))
    return calibration.compute_homography([court.LANDMARKS[n] for n in CORN],
                                          [kp[n] for n in CORN])


def scale_at_court(H, xy):
    try:
        p = calibration.court_to_image(H, [xy])[0]
        return calibration.court_scale_m_per_px(H, p)
    except Exception:
        return None


def summarise(tag, rows):
    if not rows:
        print(f"{tag:<36} n=0")
        return
    errs = [r["err"] for r in rows]
    print(f"{tag:<36} n={len(rows):<3} median|err| {st.median(map(abs, errs)):5.1f}%"
          f"  MAE {st.mean(map(abs, errs)):5.1f}%  bias {st.mean(errs):+6.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--match", required=True)
    ap.add_argument("--hud", required=True)
    ap.add_argument("--keypoints", required=True)
    ap.add_argument("--window-s", type=float, default=1.2,
                    help="max |t_hit - HUD t_start| to call it the same stroke")
    args = ap.parse_args()

    H = load_H(REPO / args.keypoints)
    match = json.loads((REPO / args.match).read_text(encoding="utf-8"))
    hud = json.loads((REPO / args.hud).read_text(encoding="utf-8"))

    rows = []
    for s in match["shots"]:
        best = None
        for r in hud["shots"]:
            d = abs(r["t_start_s"] - s["t_hit_s"])
            if d < args.window_s and (best is None or d < best[0]):
                best = (d, r["kmh"])
        if best is None or not s.get("speed_kmh"):
            continue
        a = scale_at_court(H, s["hit_xy"])
        b = scale_at_court(H, s["bounce_xy"])
        if a is None or b is None:
            continue
        rows.append({
            "type": s["type"], "scale": max(a, b), "ours": s["speed_kmh"],
            "hud": best[1], "err": 100.0 * (s["speed_kmh"] - best[1]) / best[1],
            "src": s.get("speed_source", "?"),
            "conf": bool(s.get("speed_confident", True)),
        })
    rows.sort(key=lambda r: r["scale"])

    print(f"matched {len(rows)} of {len(hud['shots'])} HUD strokes "
          f"({len(match['shots'])} shots in the match)\n")
    print(f"{'type':<10}{'src':>9}{'conf':>6}{'max m/px':>10}{'ours':>8}{'HUD':>8}{'err%':>9}")
    for r in rows:
        print(f"{r['type']:<10}{r['src']:>9}{('yes' if r['conf'] else 'no'):>6}"
              f"{r['scale']:>10.3f}{r['ours']:>8.1f}{r['hud']:>8.1f}{r['err']:>+9.1f}")
    print()

    ground = [r for r in rows if r["type"] != "serve"]
    summarise("ALL matched", rows)
    summarise("groundstrokes only (no serve)", ground)
    print()
    # THE question this tool exists to answer: is what we PUBLISH better than what
    # we hide? If the confident set is not better, the confidence rule is decoration.
    summarise("speed_confident (the headline avg/top)", [r for r in rows if r["conf"]])
    summarise("suppressed", [r for r in rows if not r["conf"]])
    print()
    # Does the gate that suppresses everything actually predict accuracy?
    thr = calibration.RELIABLE_SCALE_M_PER_PX
    summarise(f"scale_ok PASS (max <= {thr})", [r for r in rows if r["scale"] <= thr])
    summarise(f"scale_ok FAIL (max >  {thr})", [r for r in rows if r["scale"] > thr])
    print()
    print("Reference: SwingVision's burned-in HUD — itself a single-camera estimate, "
          "NOT radar, on ONE clip. Treat as directional.")
    print("Our number is the AVERAGE ball speed over the flight; a racquet-speed "
          "readout is legitimately higher (CLAUDE.md: ~15-20% under radar), so a "
          "negative bias of that size is expected physics, not a calibration error.")


if __name__ == "__main__":
    main()
