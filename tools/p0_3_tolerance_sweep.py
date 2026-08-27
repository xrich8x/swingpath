"""POST-HOC diagnostic for the P0-3 probe. Not the pre-registered number.

The pre-registered acceptance test was fixed before the runs: a detection counts
only if its own keypoint-hull box, GROWN BY 25%, contains the ball's image position
at contact. Reading the contact sheets afterwards showed that test is dominated by
how accurately the ball anchors the contact, not by whether the far player was
found: the crop arms detect a far-player-sized person 20-50 px from the anchor in
many contacts, and the strict test rejects them.

This sweeps the tolerance so that dependence is visible instead of hidden. It reads
the probe's stored per-detection records; it runs no inference and changes no
pre-registered figure. The 25% column is the pre-registered one; every other column
is post-hoc and must be labelled as such wherever it is quoted.

Distance is from the ball contact point to the NEAREST EDGE of the detection box,
in native pixels, so it is directly comparable across clips only after dividing by
the detected box height (also reported).
"""

from __future__ import annotations

import argparse
import json
import math

TOLERANCES_PX = [0, 10, 20, 30, 40, 60, 80]
TOLERANCES_REL_H = [0.0, 0.5, 1.0, 1.5, 2.0]


def _edge_dist(box, pt):
    x1, y1, x2, y2 = box
    dx = max(x1 - pt[0], 0.0, pt[0] - x2)
    dy = max(y1 - pt[1], 0.0, pt[1] - y2)
    return math.hypot(dx, dy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    all_out = {}
    for path in args.probe:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        contacts = d["contacts"]
        n = len(contacts)
        arms = list(d["arms"])
        res = {"n_far_contacts": n, "arms": {}}
        for key in arms:
            best = []
            for r in contacts:
                pt = r["ball_px_at_contact"]
                cands = [e for e in r["arms"][key]["accepted"] + r["arms"][key]["rejected"]
                         if e["small_enough"] and e["not_the_near_player"]]
                if not cands:
                    best.append(None)
                    continue
                e = min(cands, key=lambda e: _edge_dist(e["box"], pt))
                best.append((_edge_dist(e["box"], pt), e["box_h_px"], e["score"]))
            have = [b for b in best if b is not None]
            res["arms"][key] = {
                "far_sized_candidate_found_anywhere_in_crop": len(have),
                "rate_pct_any": round(100.0 * len(have) / n, 1) if n else None,
                "by_abs_px": {str(t): sum(1 for b in have if b[0] <= t) for t in TOLERANCES_PX},
                "by_rel_box_h": {str(t): sum(1 for b in have if b[0] <= t * b[1])
                                 for t in TOLERANCES_REL_H},
                "median_box_h_px": (round(sorted(b[1] for b in have)[len(have) // 2], 1)
                                    if have else None),
                "median_edge_dist_px": (round(sorted(b[0] for b in have)[len(have) // 2], 1)
                                        if have else None),
            }
        res["pre_registered_strict"] = {k: v["found"] for k, v in d["rates"].items()}
        res["note"] = ("only the pre_registered_strict block is the pre-registered "
                       "measurement; every tolerance column here is POST-HOC")
        all_out[d["video"]] = res

    print(json.dumps(all_out, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(all_out, f, indent=2)


if __name__ == "__main__":
    main()
