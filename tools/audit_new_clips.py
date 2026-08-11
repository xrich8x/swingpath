"""audit_new_clips.py — what is each clip actually worth, before anyone labels it.

WHY THIS EXISTS
---------------
A clip's value to this project is not how it looks. It is three measurements,
and the most important one is invisible to the eye:

  camera height   The biggest measured lever in the repo. On close line calls a
                  1.0 m mount scores 54% against a 56.2% majority-class floor —
                  worse than answering "in" every time — rising to ~81% by 8 m
                  (calibration.expected_call_accuracy, data/output/height_curve.md).
                  You cannot judge this from a thumbnail.
  framing         How much of the frame the court fills, which sets how many
                  pixels land on the ball. The existing pool spans 0.29% to 1.45%
                  of frame width on the ball itself — a 5x range that is free.
  overlays        Burned-in scoreboards and watermarks. One of them is a literal
                  yellow tennis ball, and the first far-court labelling pilot put
                  5 of 36 clicks inside a scoreboard.

Resolution is deliberately NOT in the list. It cancels at the network input: the
ball subtends a fixed fraction of the frame, so 1080p and 720p deliver the same
pixels once both are scaled to the detector's 512-wide input. Recording higher
"currently buys nothing" (data/output/phase0_ball_ceiling.md), and a table that
ranked clips by resolution would be ranking them by nothing.

    py tools/audit_new_clips.py --clips data/train_clips/A7vXlWIlyrI.mp4
    py tools/audit_new_clips.py --new          # everything from play_segments.json

Auto-calibration REFUSES on roughly half of amateur footage, by measurement —
11 of 20 gold clips succeed, and no wrong court has ever been auto-accepted.
A refusal here is not a bad clip, it is a clip needing ~30 s in
tools/court_setup_server.py. The two outcomes are reported separately.

THE 6-VOTE BAR IS LOAD-BEARING, AND THIS TOOL NEARLY BROKE IT
--------------------------------------------------------------
`consensus()` returns a court and a vote count, and it will happily return a
court agreed by 2 frames of 8. Session H part 2 measured what those are worth:
every clip at **>=6 votes** lands 3.4-13.9 px from the human corners, every clip
at **<=5 votes** lands 25.5-111.0 px, and there is nothing in the gap. The one
5-vote clip in the gold set is wrong by 68.7 px.

The first run of this tool reported a confident "4.35 m, close calls 74%" for a
clip whose consensus was **2 of 8**. A camera height is derived from the corners,
so a wrong court gives a wrong height that looks exactly like a right one — and
the project's standing claim that no wrong court has ever been auto-accepted
survives only because that bar is enforced everywhere. It is enforced here too:
below ACCEPT_VOTES nothing is reported but the vote count.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "tools"))

K_FRAMES = 8            # the consensus bar is 6 of 8, measured (Session H part 2)
ACCEPT_VOTES = 6        # below this a fit lands 25-111 px out. Not a tunable.


def calibrate(video: Path, k: int = K_FRAMES):
    """(named corners, votes, tag) — EXACTLY what the pipeline would decide.

    Calls `pipeline._sample_calib_frames` + `courtfit.fit_video_frames`, the
    shipped Tier-1 path, rather than driving `auto_fit_frame`/`consensus` here.
    A first version did re-implement it and got 1 of 12 clips where the pipeline
    gets more, because it sampled 15-85% instead of 2-98% and skipped the
    clay/shell evidence stack that `fit_video_frames` falls back to. An audit
    that predicts something other than what the product will do is worse than no
    audit — it would have sent a clip to manual calibration that calibrates
    itself, and vice versa.
    """
    from swingvision import calibration, court, courtfit, pipeline

    frames = pipeline._sample_calib_frames(str(video), k=k)
    if not frames:
        return None, 0, None
    return courtfit.fit_video_frames(frames, calibration, court)


def geometry(video: Path, named):
    """Camera height, lens, and what that height costs in close-call accuracy."""
    import cv2
    import numpy as np
    from swingvision import calibration, court
    from swingvision.courtfit import setup_verdict

    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(0.5 * total))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return {}
    v = setup_verdict(frame, named, calibration, court)
    ang, view = v.get("angle", {}), v.get("view", {})
    h = ang.get("height_m")
    out = {"height_m": None if h is None else round(float(h), 2),
           "hfov_deg": ang.get("hfov_deg"), "roll_deg": ang.get("roll_deg"),
           "reliable_frac": ang.get("reliable_frac"),
           "reliable_to_m": ang.get("reliable_to_m"),
           "coverage": view.get("coverage"), "centrality": view.get("centrality"),
           "view_level": view.get("level"), "angle_level": ang.get("level")}
    if h:
        out["close_call_pct"] = round(calibration.expected_call_accuracy(float(h)), 1)
        out["beats_guessing"] = out["close_call_pct"] > calibration.CALL_MAJORITY_FLOOR_PCT
    # Court framing: the share of the frame the court quad covers. More court in
    # frame is more pixels on the ball, and it costs nothing to ask for.
    pts = np.array([named[c] for c in
                    ("near_bl_doubles", "near_br_doubles",
                     "far_br_doubles", "far_bl_doubles")], np.float32)
    area = 0.5 * abs(float(np.dot(pts[:, 0], np.roll(pts[:, 1], -1))
                           - np.dot(pts[:, 1], np.roll(pts[:, 0], -1))))
    out["court_frac"] = round(area / (frame.shape[0] * frame.shape[1]), 4)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--clips", nargs="*", default=[])
    ap.add_argument("--new", action="store_true",
                    help="every clip named in data/output/play_segments.json")
    ap.add_argument("--k", type=int, default=K_FRAMES)
    ap.add_argument("--accept-votes", type=int, default=ACCEPT_VOTES,
                    help="frames that must agree before a court is trusted. "
                         "6 of 8 is MEASURED, not tuned - see the docstring")
    ap.add_argument("--json", default=str(REPO / "data/output/new_clip_audit.json"))
    args = ap.parse_args()

    vids = [Path(c) for c in args.clips]
    if args.new:
        rep = json.loads((REPO / "data/output/play_segments.json")
                         .read_text(encoding="utf-8"))["clips"]
        for yid, r in rep.items():
            n = len(r["segments"])
            for k in range(1, n + 1):
                p = REPO / "data/train_clips" / (
                    f"{yid}.mp4" if n == 1 else f"{yid}_s{k}.mp4")
                if p.is_file():
                    vids.append(p)
    if not vids:
        raise SystemExit("nothing to audit: pass --clips or --new")

    import mask_hud

    rows = []
    for v in vids:
        named, votes, tag = calibrate(v, args.k)
        # Enforce the bar HERE, not at the call site: a court agreed by 2 of 8
        # frames yields a camera height that reads exactly like a good one.
        # Same condition the pipeline applies (tag must be 'vote' too - a
        # clay 'stack' rescue is a single fit, so its vote count means
        # something different and is not comparable to the bar).
        accepted = (named is not None and tag == "vote"
                    and votes >= args.accept_votes)
        row = {"clip": v.stem, "votes": int(votes), "tag": tag,
               "calibrated": accepted, "accept_votes": args.accept_votes}
        if accepted:
            row.update(geometry(v, named))
            row["corners"] = {k: [round(float(x), 1) for x in p]
                              for k, p in named.items()}
        try:
            boxes, _plate, _agree, wh = mask_hud.detect(str(v), 40)
            row["overlay_boxes"] = len(boxes)
            row["overlay_frac"] = round(
                sum(b["w"] * b["h"] for b in boxes) / float(wh[0] * wh[1]), 4)
        except Exception as e:                       # a probe must not stop an audit
            row["overlay_boxes"], row["overlay_error"] = None, str(e)[:80]
        rows.append(row)
        print(f"  {v.stem:<22} votes {votes}/{args.k}  "
              f"{'height %.2f m' % row['height_m'] if row.get('height_m') else 'REFUSED'}"
              f"   auto-overlay {row.get('overlay_boxes')}")

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(
        {"tool": "audit_new_clips.py", "created": time.strftime("%Y-%m-%d %H:%M:%S"),
         "k_frames": args.k, "clips": rows}, indent=1), encoding="utf-8")

    ok = [r for r in rows if r.get("height_m")]
    print(f"\n{len(ok)} of {len(rows)} auto-calibrated. "
          f"A refusal is a 30-second job in tools/court_setup_server.py, "
          f"not a bad clip.")
    if ok:
        hdr = (f"{'clip':<22}{'height':>8}{'close call':>12}{'measurable':>12}"
               f"{'court %':>9}{'auto-ovl':>9}")
        print("\n" + hdr); print("-" * len(hdr))
        for r in sorted(ok, key=lambda r: -r["height_m"]):
            rf = r.get("reliable_frac")
            print(f"{r['clip']:<22}{r['height_m']:>7.2f}m"
                  f"{r['close_call_pct']:>11.1f}%"
                  f"{(rf * 100 if rf else 0):>11.0f}%"
                  f"{r['court_frac'] * 100:>8.1f}%"
                  f"{r.get('overlay_boxes', 0):>9}")
        print(f"\nclose call = share of near-the-line bounces called right at that "
              f"height; anything at or below "
              f"{__import__('swingvision.calibration', fromlist=['x']).CALL_MAJORITY_FLOOR_PCT}"
              f"% is no better than always saying IN")
    print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
