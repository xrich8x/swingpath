"""eval/proposer_ab.py - the court GLOBAL-PROPOSAL A/B: classical vs CourtNet.

ONE VARIABLE. Arm A is the shipped ordering (classical-global `autodetect` ->
classical-local `snap_to_lines` -> 6-DOF `lock_quad`). Arm B flips stage one only
(CourtNet-global -> the SAME snap -> the SAME lock). The consensus vote, the
accept rule (tag=="vote" and votes>=6), the frame count and the error metric are
`run_refs`'s, untouched, and both arms are scored on the SAME DECODED FRAMES so a
seek difference cannot masquerade as a detector difference.

WHAT IT IS SCORED AGAINST: the human-placed `_exact` corners in data/<clip>_pts.json,
via run_refs.references() - human clicks, never a detector output.

WEIGHTS. Arm B forces `court_detector.pt`, the UPSTREAM released checkpoint, through
the COURTNET_WEIGHTS hook. Without the hook `detect_court_learned` silently prefers
`courtnet_ft.pt` - our fine-tune, whose training pool contained 17 of these 20 gold
clips. Scoring against that would be self-grading. The RESOLVED path is stamped.

    backend/.venv/Scripts/python.exe eval/proposer_ab.py --out eval/out/proposer_ab.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "eval"))

# Force the upstream checkpoint BEFORE the model global is populated.
os.environ.setdefault(
    "COURTNET_WEIGHTS", str(REPO / "backend" / "weights" / "court_detector.pt"))

import run_refs  # noqa: E402
from swingvision import calibration, court, courtfit  # noqa: E402
from swingvision.courtfit import DBL  # noqa: E402

WRONG_PX_640 = 20.0          # the shipped empty-band number (eval/candidate_audit.py)
ACCEPT_VOTES = run_refs.ACCEPT_VOTES
LOW_MOUNT_M = 2.2            # below this the net tape overlaps the far baseline


def _err_at_640(named_ref, pts, w):
    Href = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [named_ref[n] for n in DBL])
    Hfit = calibration.compute_homography(
        [court.LANDMARKS[n] for n in DBL], [pts[n] for n in DBL])
    err = float(np.mean([
        np.hypot(*(calibration.court_to_image(Href, [court.LANDMARKS[n]])[0]
                   - calibration.court_to_image(Hfit, [court.LANDMARKS[n]])[0]))
        for n in DBL]))
    return err, err * 640.0 / float(w)


def _mount_height_m(named_ref, w, h):
    """Camera height implied by the HUMAN corners (courtfit's own 6-DOF fit)."""
    try:
        quad = {k: [float(named_ref[k][0]), float(named_ref[k][1])] for k in DBL}
        fit = courtfit.cam_fit_quad(quad, calibration, court, w, h, allow_roll=True)
        if fit is None:
            return None
        return round(abs(float(fit[3][2])), 2)
    except Exception:
        return None


def _arm(frames, proposer, named_ref, w):
    t0 = time.time()
    fits = [courtfit.auto_fit_frame(im, calibration, court, proposer=proposer)
            for _p, im in frames]
    pts, votes = courtfit.consensus(fits)
    tag = "vote" if pts is not None else None
    if pts is None and len(frames) >= 6:
        pts = courtfit.stacked_clay_fit(frames, calibration, court)
        tag = "stack" if pts is not None else None
    accepted = pts is not None and tag == "vote" and votes >= ACCEPT_VOTES
    err = err640 = None
    if pts is not None:
        err, err640 = _err_at_640(named_ref, pts, w)
    return {"proposer": proposer, "locked": sum(1 for f in fits if f),
            "votes": int(votes), "tag": tag, "accepted": bool(accepted),
            "err_px": None if err is None else round(err, 2),
            "err_640": None if err640 is None else round(err640, 2),
            "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=run_refs.ACCEPT_K)
    ap.add_argument("--out", default=str(REPO / "eval" / "out" / "proposer_ab.json"))
    ap.add_argument("--only", default=None, help="comma-separated clip stems")
    a = ap.parse_args()

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "?"
    stamp = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": commit,
        "k_frames": a.k,
        "accept_votes": ACCEPT_VOTES,
        "wrong_px_640": WRONG_PX_640,
        # the RESOLVED configuration, not the request
        "courtnet_weights_resolved": courtfit.resolved_courtnet_weights(),
        "proposer_default_resolved": courtfit.resolved_proposer(),
        "reference": "human _exact clicks via run_refs.references()",
    }
    print(json.dumps(stamp, indent=2))

    refs = run_refs.references()
    if a.only:
        keep = set(a.only.split(","))
        refs = [r for r in refs if r[0] in keep]
    rows = []
    for clip, pts_path, vid in refs:
        ref = json.loads(pts_path.read_text(encoding="utf-8"))
        named = {kk: v for kk, v in ref.items() if not kk.startswith("_")}
        if not all(n in named for n in DBL):
            print(f"{clip}: SKIP (incomplete human corners)"); continue
        frames = run_refs.frames_from(vid, a.k)
        if not frames:
            print(f"{clip}: SKIP (no frames)"); continue
        h, w = frames[0][1].shape[:2]
        row = {"clip": clip, "surface": vid.parent.name, "w": w, "h": h,
               "mount_m": _mount_height_m(named, w, h),
               "audit": ref.get("_audit", {}).get("verdict", "?")}
        for p in ("classical", "courtnet"):
            row[p] = _arm(frames, p, named, w)
        rows.append(row)
        print(f"{clip:22s} {row['surface']:10s} mount={row['mount_m']} "
              f"A: acc={row['classical']['accepted']} v={row['classical']['votes']} "
              f"e640={row['classical']['err_640']} | "
              f"B: acc={row['courtnet']['accepted']} v={row['courtnet']['votes']} "
              f"e640={row['courtnet']['err_640']}", flush=True)

    out = {"stamp": stamp, "rows": rows}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {a.out}  ({len(rows)} clips)")

    for p in ("classical", "courtnet"):
        acc = [r for r in rows if r[p]["accepted"]]
        bad = [r for r in acc if (r[p]["err_640"] or 0) > WRONG_PX_640]
        print(f"{p:10s} accepted {len(acc)}/{len(rows)}  wrong-accepted {len(bad)}")


if __name__ == "__main__":
    main()
