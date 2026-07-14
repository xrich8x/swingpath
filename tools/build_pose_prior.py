"""Learn a CAMERA-ANGLE PRIOR from the human court labels.

Amateur clips aren't shot from random angles - they cluster (behind the baseline,
a few feet up, roughly centred). Each labelled court encodes its camera setup as a
simple trapezoid in the frame; we summarise the DISTRIBUTION of those setups so the
auto-detector can (a) aim its guesses at plausible angles and (b) reject fits that
imply a physically weird camera (the wrong-nested-rectangle locks).

Per labelled frame we reduce the 4 doubles corners to 5 frame-fraction numbers:
  cx   overall horizontal centre
  yn   near-baseline height        yf   far-baseline height
  wn   near half-width             wf   far half-width
(values can exceed [0,1] - off-frame corners are normal and worth capturing.)

Output: data/court_pose_prior.json  {mean[5], cov[5][5], n, params}. The three
held-out TEST clips are excluded so the prior can be evaluated fairly.

  backend/.venv/Scripts/python.exe tools/build_pose_prior.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "data" / "gold"
DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
TEST_CLIPS = {"am_ntrp45_courtlevel", "am_rec30", "am_beginner"}
PARAMS = ["cx", "yn", "yf", "wn", "wf"]


def frame_params(c, w, h):
    """4 corners (image px) + frame size -> [cx, yn, yf, wn, wf] as fractions."""
    nbl, nbr, fbr, fbl = (np.array(c[k], float) for k in DBL)
    cx = (nbl[0] + nbr[0] + fbr[0] + fbl[0]) / 4.0 / w
    yn = (nbl[1] + nbr[1]) / 2.0 / h
    yf = (fbl[1] + fbr[1]) / 2.0 / h
    wn = (nbr[0] - nbl[0]) / 2.0 / w
    wf = (fbr[0] - fbl[0]) / 2.0 / w
    return [cx, yn, yf, wn, wf]


def main():
    rows, used = [], []
    for lab_path in sorted(GOLD.glob("*.court.labels.json")):
        clip = lab_path.name[:-len(".court.labels.json")]
        if clip in TEST_CLIPS:
            continue
        man = json.loads((GOLD / f"{clip}.court.manifest.json").read_text())
        w, h = man["width"], man["height"]
        labs = json.loads(lab_path.read_text())["labels"]
        k0 = len(rows)
        for v in labs.values():
            if v.get("court") is not True:
                continue
            kp = v.get("keypoints", {})
            if all(n in kp for n in DBL):
                rows.append(frame_params(kp, w, h))
        used.append((clip, len(rows) - k0))

    X = np.asarray(rows)
    mu = X.mean(axis=0)
    cov = np.cov(X, rowvar=False)
    # tiny ridge so the covariance is invertible / robust with limited data
    cov = cov + np.eye(5) * 1e-4
    out = {"params": PARAMS, "n": len(X), "mean": mu.tolist(), "cov": cov.tolist(),
           "excluded_test": sorted(TEST_CLIPS)}
    (REPO / "data" / "court_pose_prior.json").write_text(json.dumps(out, indent=1))

    print(f"learned camera-angle prior from {len(X)} labelled courts "
          f"({len(used)} train clips; test excluded)")
    print("            " + "  ".join(f"{p:>6s}" for p in PARAMS))
    print("mean       " + "  ".join(f"{m:6.3f}" for m in mu))
    print("std        " + "  ".join(f"{s:6.3f}" for s in np.sqrt(np.diag(cov))))
    print("-> data/court_pose_prior.json")


if __name__ == "__main__":
    main()
