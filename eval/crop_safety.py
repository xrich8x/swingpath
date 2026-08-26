"""eval/crop_safety.py - does the horizon crop ever delete a court line a human clicked?

The check that protects the precision record, and the reason it exists is that the
crop (B2, docs/archive/sessions/SESSION_O_shell_courts.md) is the one change in that session
whose failure mode is a WRONG COURT rather than a refusal.

THE ASYMMETRY, RESTATED SO THIS FILE STANDS ALONE
--------------------------------------------------
`movers.crop_row` zeroes the line mask above the highest point a player was ever seen
standing, on the reasoning that roof trusses, strip lights and the upper fence lattice
are all above that and the court is all below it. Getting that row too HIGH is free -
less clutter is removed, the fit is what it is today. Getting it too LOW deletes true
court lines, and a detector fed a mask with the far baseline missing does not refuse;
it finds some other quadrilateral and reports it confidently. The gate tolerates a
refusal and does not tolerate a wrong court.

So the question is not "does the crop help" - that is the gate's job. It is "can the
crop ever remove evidence a human could see", and the 20 gold clips answer it with
~315 hand-clicked frames that nobody has to trust a detector for.

PASS means: on every labelled frame of every gold clip, every clicked court keypoint
sits BELOW the crop row, with margin to spare. A single keypoint above the row on a
single frame is a fail - there is no acceptable rate here, because the failure is
silent and it corrupts every downstream number.

TWO ROWS ARE REPORTED, AND THEY ARE DIFFERENT QUESTIONS
--------------------------------------------------------
  from the recording  the operating condition: 120 frames sampled across the whole
                      source video, which is what B2 actually specifies. `y_deep` is
                      a max-statistic over depth, so more frames make it safer.
  from gold frames    the pessimistic condition: only the labelled frames, which are
                      far fewer. If the crop is safe even here it is safe in
                      practice, and clips whose source video is a YouTube stream with
                      no local file can only be checked this way.

    backend/.venv/Scripts/python.exe eval/crop_safety.py
    backend/.venv/Scripts/python.exe eval/crop_safety.py --k 1.0 --json out.json
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
sys.path.insert(0, str(REPO / "eval"))
sys.path.insert(0, str(REPO / "tools"))

GOLD = REPO / "data" / "gold"


def _gold_frames(clip):
    """[(frame_key, image)] for the labelled frames of one gold clip."""
    import cv2
    out = []
    d = GOLD / "frames" / clip
    if not d.exists():
        return out
    for p in sorted(d.glob("f*.jpg")):
        im = cv2.imread(str(p))
        if im is not None:
            out.append((p.stem, im))
    return out


def _source_frames(clip, k):
    """k frames spread across the whole SOURCE recording, or [] if it is not local."""
    try:
        from _goldset import find_video
    except Exception:
        return []
    mf = GOLD / f"{clip}.court.manifest.json"
    if not mf.exists():
        return []
    vid = str(json.loads(mf.read_text(encoding="utf-8")).get("video", "") or "")
    if not vid or vid.startswith("http"):
        return []                       # streamed: no local file to sample
    try:
        p = find_video(Path(vid).name)
    except Exception:
        p = None
    if not p or not Path(p).exists():
        return []
    from run_refs import frames_from
    return frames_from(Path(p), k)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=float, default=None,
                    help="crop margin multiplier (default: movers.CROP_K)")
    ap.add_argument("--recording-frames", type=int, default=120, dest="rk")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    import movers
    k = movers.CROP_K if a.k is None else a.k

    print(f"crop margin k={k}; 'clear' = px between the crop row and the HIGHEST "
          f"clicked keypoint.\nnegative clear = the crop would delete a court line "
          f"a human could see = FAIL.\n")
    # feet are reported for BOTH sources separately. Conflating them once made a run
    # where the recording path worked and simply proposed no crop look identical to
    # one where the recording path never ran at all.
    print(f"{'clip':22s} {'ft(rec)':>7s} {'ft(gold)':>8s} {'row(rec)':>9s} "
          f"{'row(gold)':>10s} {'top kp':>7s} {'clear':>7s}  verdict")
    print("-" * 92)

    rows, fails = [], []
    for lf in sorted(GOLD.glob("*.court.labels.json")):
        clip = lf.name.replace(".court.labels.json", "")
        labs = json.loads(lf.read_text(encoding="utf-8")).get("labels", {})
        kps = [v["keypoints"] for v in labs.values()
               if v.get("court") is True and v.get("keypoints")]
        if not kps:
            continue
        gframes = _gold_frames(clip)
        if not gframes:
            print(f"{clip:22s}  (skipped: no extracted frames)")
            continue
        h, w = gframes[0][1].shape[:2]
        top_kp = float(min(float(p[1]) for kp in kps for p in kp.values()))

        feet_g = movers.foot_points([im for _k, im in gframes])
        row_g = movers.crop_row(feet_g, h, k=k)

        src = _source_frames(clip, a.rk)
        feet_r = movers.foot_points([im for _p, im in src]) if src else []
        row_r = movers.crop_row(feet_r, h, k=k) if feet_r else None

        # the operating row is the recording one when it exists; the gold row is the
        # pessimistic fallback and the only option for streamed clips
        row = row_r if row_r is not None else row_g
        clear = None if row is None else top_kp - row
        ok = clear is None or clear > 0
        v = ("no crop" if row is None else
             "PASS" if clear > 0.05 * h else
             "PASS (tight)" if clear > 0 else "*** FAIL ***")
        if not ok:
            fails.append(clip)
        rows.append({"clip": clip, "w": w, "h": h, "frames": len(gframes),
                     "feet_rec": len(feet_r), "feet_gold": len(feet_g),
                     "src_frames": len(src), "row_rec": row_r,
                     "row_gold": row_g, "top_kp": top_kp, "clear": clear,
                     "verdict": v})
        print(f"{clip:22s} {(str(len(feet_r)) if src else 'no src'):>7s} "
              f"{len(feet_g):8d} {'none' if row_r is None else row_r:>9} "
              f"{'none' if row_g is None else row_g:>10} {top_kp:7.0f} "
              f"{'-' if clear is None else f'{clear:+.0f}':>7}  {v}", flush=True)

    print("-" * 92)
    nosrc = [r for r in rows if r["src_frames"] == 0]
    if nosrc:
        print(f"{len(nosrc)} clips have no local source video (streamed) and were "
              f"checked on gold frames only: {', '.join(r['clip'] for r in nosrc)}")
    cropped = [r for r in rows if r["clear"] is not None]
    print(f"{len(rows)} gold clips; a crop is proposed on {len(cropped)}.")
    if fails:
        print(f"\n*** {len(fails)} FAIL: {', '.join(fails)} ***")
        print("B2 CANNOT SHIP as specified. Either the margin is too small or the "
              "foot\nevidence on those clips does not bound the court at all - and "
              "'no crop' is\nalways the correct answer when it does not.")
    elif cropped:
        print(f"\nPASS on all {len(cropped)}. Tightest clearance "
              f"{min(r['clear'] for r in cropped):+.0f} px on "
              f"{min(cropped, key=lambda r: r['clear'])['clip']}.")
        print("This bounds the SAFETY of the crop only. Whether it HELPS is the "
              "gold gate's\nquestion, and it is a separate run.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
