"""Give an EXISTING match.json its `setup` trust block, derived from its own
calibration.

WHY THIS EXISTS, AND WHAT IT IS NOT. Every match.json written before
`backend/swingvision/setup_state.py` has no `setup` block, so it loads as
`unknown` — a true statement, but a useless one for a file that carries its own
four court corners and could therefore say something precise. This re-derives
the block from what the file already records. It is a DERIVATION, not an
annotation: the corners, the frame size and the lens coefficient all come out of
the file, and the clearance is computed by the same `setup_state.from_homography`
the pipeline calls.

    python tools/backfill_setup_state.py frontend/src/data/analyzed_match.json

Two things it will not do.

  * It will not invent a calibration status. A file with no `_provenance` stamp
    gets `provisional`, which is what trap T26 says an unattributed placement is
    worth, no matter how carefully somebody clicked it. Passing --confirmed-by
    records a real person's attestation; there is no flag that means "assume a
    human did it".
  * It will not re-run perception, re-derive stats, or touch any other key. It
    writes exactly one field.

Every backfilled state carries a reason saying it was derived after the fact from
the stored corners rather than measured during the analysis, because those are
not quite the same claim: `analyze` measures on the homography it actually used
(shape-locked, post-snap), and a file only stores the corners.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

DBL = ("near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles")


def derive(match: dict, confirmed_by: str | None = None) -> dict:
    from swingvision import calibration
    from swingvision import setup_state as ss

    cal = match.get("calibration") or {}
    corners = cal.get("corners") or {}
    vid = match.get("video") or {}
    w, h = int(vid.get("width") or 0), int(vid.get("height") or 0)

    if not all(n in corners for n in DBL) or w <= 0 or h <= 0:
        return ss.build(
            calibration_status=ss.CALIB_UNAVAILABLE,
            extra_reasons=["This match.json carries no usable court calibration, "
                           "so no court measurement could be checked."]).to_dict()

    named = {n: [float(corners[n][0]), float(corners[n][1])] for n in DBL}
    k1 = float(cal.get("lens_k1") or 0.0)
    if k1:
        # The clearance criterion models an ideal PINHOLE. On a measured lens the
        # stored corners are bent pixels, so undistort them first - the same
        # ordering analyze uses to build its metric homography.
        named = {n: [float(v) for v in
                     calibration.undistort_points([xy], k1, (w, h))[0]]
                 for n, xy in named.items()}
    H = calibration.homography_from_landmarks(named)

    reasons = ["This setup state was derived from the court corners stored in "
               "the match file, after the analysis ran."]
    if confirmed_by:
        status = ss.CALIB_USER_CONFIRMED
        reasons.append(f"The four court corners were confirmed by {confirmed_by}.")
    else:
        status = ss.CALIB_PROVISIONAL
        reasons.append("Nobody is recorded as having confirmed these corners, so "
                       "the calibration is provisional.")
    return ss.from_homography(H, (w, h), calibration_status=status,
                              extra_reasons=reasons).to_dict()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("match", nargs="+", help="match.json file(s) to backfill")
    ap.add_argument("--confirmed-by", default=None,
                    help="name the PERSON who checked these corners against the "
                         "frame. Only pass this if that actually happened - it "
                         "is the difference between 'provisional' and "
                         "'user_confirmed' everywhere downstream (trap T26)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the block that would be written and change nothing")
    args = ap.parse_args(argv)

    from swingvision import schema

    for path in args.match:
        p = Path(path)
        match = json.loads(p.read_text(encoding="utf-8"))
        block = derive(match, args.confirmed_by)
        print(f"{p.name}: framing={block['framing_status']} "
              f"calibration={block['calibration_status']} "
              f"clearance={block['far_baseline_clearance_px_720']} px@720p "
              f"verified={block['metrics_eligible']}")
        for r in block["reasons"]:
            print(f"    - {r}")
        if args.dry_run:
            continue
        match["setup"] = block
        problems = schema.validate(match)
        if problems:
            print(f"  REFUSED - the result would not validate:\n    "
                  + "\n    ".join(problems))
            return 1
        p.write_text(json.dumps(match, indent=2), encoding="utf-8")
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
