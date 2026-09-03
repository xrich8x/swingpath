"""How often does the fp32 ball heatmap present a CLOSE two-blob race?

WHY THIS EXISTS
---------------
The shipped int8 graph's parity failure (docs/evidence/ball-detector-parity-tracknet.md)
is not a random position error. It needs a near-tie between two blobs in the *fp32*
heatmap, which quantisation then flips by eroding the winner's AREA. So the headline
"5 failing frames in 528" has a misleading denominator: the real denominator is the
number of close races, not the number of frames.

This counts them, on fp32 heatmaps that already exist from a parity run. It runs NO
inference and loads NO model — it reads `onnx_heat_<tag>.bin` and `js_results.json`
out of one or more parity directories produced by `ball_detector_parity_probe.py`.

SCORING is the shipped decode's, not a reimplementation of convenience: threshold at
127 (so `>=128`), 8-connected components, `score = area * peak` — the same rule
`ball.py::_postprocess` and `mobile/ball_detector.js::_decode` both apply.

GUARDED. For every frame, the top-scoring blob's centroid must equal what the REAL
`_decode()` recorded in `js_results.json` for that frame. A frame failing that guard
is COUNTED AND REPORTED, never silently skipped — if guard failures are not zero,
this script is measuring something other than what the decode sees and its numbers
are void. On the six-clip 2026-09-03 run the count was 0 of 528.

THRESHOLD HONESTY — READ BEFORE QUOTING ANY NUMBER FROM THIS. `--close` defaults to
0.15 (runner-up scores >=85% of the winner). That value was chosen AFTER seeing which
frames failed; margin is `(winner - runner_up) / winner` and the widest among the five
known failures is 7.69%. It is therefore NOT independent of the result it explains,
which is why this takes the threshold as an argument. qa swept it 2026-09-03 and the
claim split in two:

  SURVIVES every threshold 0.05-0.30 - the two clips that pass the parity bar cleanly
    (yt_match40, gold_clay) contain ZERO close races. A real property of the footage.
  DOES NOT SURVIVE - "all five int8 failures are close races" holds at 0.15 but drops
    to 2 of 5 at 0.05. Do not quote "31% of close races flip" as a rate; the threshold
    was drawn around the numerator.

Pre-register the threshold before looking at which frames it catches.

USAGE
    python backend/ball_parity_margin_census.py <dir>[=<label>] [<dir>[=<label>] ...]
                                                [--close 0.15]
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np

IN_W, IN_H = 640, 360


def blobs(heat: np.ndarray) -> list[tuple[int, int, int, float, float]]:
    """(score, area, peak, cx, cy) per component, best first — the decode's own rule."""
    _, th = cv2.threshold(heat, 127, 255, cv2.THRESH_BINARY)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(th, 8)
    out = []
    for i in range(1, n):
        m = lab == i
        area = int(stats[i, cv2.CC_STAT_AREA])
        peak = int(heat[m].max())
        ys, xs = np.nonzero(m)
        out.append((area * peak, area, peak, float(xs.mean()), float(ys.mean())))
    out.sort(key=lambda b: -b[0])
    return out


def census(parity_dir: str, close: float) -> tuple[int, int, int, list[str]]:
    """(both_fire, close_races, guard_failures, close_tags) for one parity dir."""
    with open(os.path.join(parity_dir, "js_results.json")) as f:
        js = {r["tag"]: r for r in json.load(f)["results"]}
    both = races = guard_fail = 0
    tags: list[str] = []
    for tag, r in js.items():
        # Same denominator the parity bar uses: frames where BOTH graphs fire.
        if r.get("onnx_xy") is None or r.get("int8_xy") is None:
            continue
        both += 1
        heat = np.fromfile(
            os.path.join(parity_dir, f"onnx_heat_{tag}.bin"), dtype=np.uint8
        ).reshape(IN_H, IN_W)
        bl = blobs(heat)
        if not bl or abs(bl[0][3] - r["onnx_xy"][0]) > 0.01 or abs(bl[0][4] - r["onnx_xy"][1]) > 0.01:
            guard_fail += 1
            continue
        if len(bl) >= 2 and bl[1][0] >= (1.0 - close) * bl[0][0]:
            races += 1
            tags.append(tag)
    return both, races, guard_fail, tags


def main(argv: list[str]) -> int:
    close = 0.15
    dirs: list[tuple[str, str]] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--close":
            close = float(argv[i + 1]); i += 2; continue
        label = a.split("=", 1)[0]
        path = a.split("=", 1)[1] if "=" in a else a
        dirs.append((os.path.basename(path.rstrip(r"\/")) if "=" not in a else label, path))
        i += 1
    if not dirs:
        print(__doc__)
        return 1

    tot_both = tot_races = tot_guard = 0
    print(f"close-race threshold: runner-up >= {100*(1-close):.0f}% of winner\n")
    print(f"{'clip':<18}{'both-fire':<12}{'close races':<14}{'%':<9}{'guard-fail'}")
    rows = []
    for label, path in dirs:
        both, races, gf, tags = census(path, close)
        tot_both += both; tot_races += races; tot_guard += gf
        rows.append((label, tags))
        print(f"{label:<18}{both:<12}{races:<14}{100*races/max(both,1):>6.1f}%  {gf}")
    print(f"\nPOOLED: {tot_races}/{tot_both} both-fire frames = "
          f"{100*tot_races/max(tot_both,1):.1f}%   (guard failures: {tot_guard})")
    if tot_guard:
        print("!! GUARD FAILURES ARE NON-ZERO — these numbers are void, not merely noisy.")
    print("\nClose-race tags (the frames at risk):")
    for label, tags in rows:
        print(f"  {label}: {sorted(tags)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
