"""eval/run_refs.py - MEASURED court error on clips with a human-placed calibration.

eval/frames has no ground truth, so eval/run_eval.py --drop can only say "it
locked", never "it locked to the right place". This closes that gap on the subset
where a human already placed the corners by hand.

WHAT COUNTS AS A REFERENCE HERE. Only `data/<clip>_pts.json` carrying
`"_exact": true`. That flag is pipeline.calibrate_video's own definition - "the
overlay tool's shape-lock-OFF save: the user DELIBERATELY placed these corners" -
so it is a human placement, not a detector output. `data/eala_pts_auto.json` is
excluded by name and by rule: scoring the detector against a court the detector
produced is self-grading, which ML_PRACTICES forbids. Files with neither marker
are excluded as provenance-unclear rather than assumed human.

WHY IT RE-EXTRACTS. eval/collect_frames.py groups a recording's files together
(a trim and its source are the same court), but a calibration belongs to ONE FILE
at ONE resolution. Comparing a fit made on the 1080p source against corners
clicked on a 720p trim would be measuring the resize. So each reference is paired
with the single file whose stem matches its own name, and frames come from there.

The error is the mean distance between the four doubles corners as projected by
the human's homography and by the consensus fit, in that file's own pixels. Two
corners are usually OFF-FRAME on a low mount - that is fine and is the point:
they are projected, not detected.

    backend/.venv/Scripts/python.exe eval/run_refs.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

from swingvision.courtfit import DBL  # noqa: E402

# Where to look for the one file a reference belongs to, most-specific first.
SEARCH = ["data", "data/train_clips", "data/gold_clips", "data/amateur_clips",
          "data/highlights", "data/incoming"]

ACCEPT_VOTES, ACCEPT_K = 6, 8


def references() -> list[tuple[str, Path, Path]]:
    """[(clip, pts_path, video_path)] for every human-placed calibration whose
    video can be identified unambiguously by stem."""
    out = []
    for p in sorted((REPO / "data").glob("*_pts*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("_exact"):
            continue                      # not a deliberate human placement
        stem = p.stem[:-4] if p.stem.endswith("_pts") else p.stem
        vid = None
        for pool in SEARCH:
            c = REPO / pool / f"{stem}.mp4"
            if c.exists():
                vid = c
                break
        if vid is not None:
            out.append((stem, p, vid))
    return out


def frames_from(video: Path, k: int):
    import cv2

    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total > 0:
        lo, hi = int(0.05 * total), int(0.95 * total)
        for pos in np.linspace(lo, hi, k).round().astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(pos))
            ok, img = cap.read()
            if ok:
                frames.append((int(pos), img))
    cap.release()
    return frames


def score(clip, pts_path, video, k):
    import cv2  # noqa: F401
    from swingvision import calibration, court, courtfit

    ref = json.loads(pts_path.read_text(encoding="utf-8"))
    named = {kk: v for kk, v in ref.items() if not kk.startswith("_")}
    if not all(n in named for n in DBL):
        return None
    frames = frames_from(video, k)
    if not frames:
        return None
    h, w = frames[0][1].shape[:2]

    fits = [courtfit.auto_fit_frame(im, calibration, court) for _p, im in frames]
    pts, votes = courtfit.consensus(fits)
    tag = "vote" if pts is not None else None
    if pts is None and len(frames) >= 6:
        pts = courtfit.stacked_clay_fit(frames, calibration, court)
        tag = "stack" if pts is not None else None
    accepted = pts is not None and tag == "vote" and votes >= ACCEPT_VOTES

    err = None
    if pts is not None:
        Href = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [named[n] for n in DBL])
        Hfit = calibration.compute_homography(
            [court.LANDMARKS[n] for n in DBL], [pts[n] for n in DBL])
        err = float(np.mean([
            np.hypot(*(calibration.court_to_image(Href, [court.LANDMARKS[n]])[0]
                       - calibration.court_to_image(Hfit, [court.LANDMARKS[n]])[0]))
            for n in DBL]))
    return {"clip": clip, "w": w, "h": h, "votes": votes, "tag": tag,
            "accepted": accepted, "err": err, "locked": sum(1 for f in fits if f),
            "frames": len(frames), "audit": ref.get("_audit", {}).get("verdict", "?")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=ACCEPT_K)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    refs = references()
    print(f"{len(refs)} human-placed calibrations with an identifiable video\n")
    print(f"{'clip':22s} {'res':>10s} {'audit':>11s} {'lock':>5s} {'votes':>5s} "
          f"{'result':>9s} {'err_px':>7s} {'err@640':>8s}")
    print("-" * 84)
    rows = []
    for clip, pts_path, vid in refs:
        r = score(clip, pts_path, vid, a.k)
        if r is None:
            print(f"{clip:22s}  (skipped: no frames or incomplete corners)")
            continue
        rows.append(r)
        # normalise to the gold set's 640-wide frames so the number is comparable
        # to the 3.4-13.9 px accepted band in data/output/court_consensus_bar.md
        e640 = None if r["err"] is None else r["err"] * 640.0 / r["w"]
        res = ("ACCEPTED" if r["accepted"] else "stk" if r["tag"] == "stack"
               else f"vote<{ACCEPT_VOTES}" if r["tag"] == "vote" else "refused")
        err_s = "-" if r["err"] is None else f"{r['err']:.1f}"
        e640_s = "-" if e640 is None else f"{e640:.1f}"
        print(f"{r['clip']:22s} {r['w']}x{r['h']:<5d} {r['audit']:>11s} "
              f"{r['locked']:>2d}/{r['frames']:<2d} {r['votes']:5d} {res:>9s} "
              f"{err_s:>7s} {e640_s:>8s}")
    acc = [r for r in rows if r["accepted"] and r["err"] is not None]
    if acc:
        e = [r["err"] * 640.0 / r["w"] for r in acc]
        print("-" * 84)
        print(f"ACCEPTED {len(acc)}/{len(rows)} with a reference.  "
              f"err@640 median {np.median(e):.1f} px, range {min(e):.1f}-{max(e):.1f}")
        print("The gold set's accepted band is 3.4-13.9 px at 640 wide "
              "(data/output/court_consensus_bar.md); >20 px there has always been a wrong court.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
