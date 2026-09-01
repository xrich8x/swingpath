"""live_doubles_alley_probe.py — drive live.LiveAnalyzer's singles/doubles branch
with synthetic, pre-registered boundary cases.

This is a PARITY / geometry probe, not an accuracy test: the positions are
synthetic court-plane points chosen to straddle every X/Y boundary that
matters (centre court, both doubles alleys, fully outside doubles, every line
to within a few millimetres of the margined boundary), not a real ball
trajectory with human ground truth. See mobile/doubles_alley_parity_cases.json
for the case list and the hand-computed expected in/out per case (computed
independently of this script, from the raw court constants).

Why drive the full bounce state machine instead of calling
`court.is_in_singles`/`is_in_doubles` directly: the mobile JS port's bug
(mobile/live_calls.js, fixed 2026-09-02) was in the WIRING inside
`_detectBounce` — `isInSingles` was called unconditionally regardless of
`this.singles` — not in `isInSingles`/`isInDoubles` themselves, which were
each individually correct. A unit test of the boundary functions alone would
not have caught it. So each case is turned into a minimal 4-point synthetic
trajectory (identity homography, so pushed "pixel" coords equal court metres
directly — no camera, no calibration file) that produces exactly one bounce
call at the target position, and the ACTUAL call is read off LiveAnalyzer.calls
— the same code path `push_position` -> `_detect_bounce` that a real bounce
takes.

Trajectory construction, per case (x0, y0):
    p0=(x0-10, y0) t=0   p1=(x0-1, y0) t=1   p2=(x0, y0) t=2   p3=(x0+9, y0) t=3
    segment speeds: 9, 1, 9 -> a clean local-min dip (is_min AND is_dip at the
    default min_speed_drop=0.6), bounce reported at _valid[-2] = p2 = (x0, y0)
    exactly. A fresh LiveAnalyzer per case+mode sidesteps min_call_gap_s.

Usage:
    cd backend && .venv/Scripts/python.exe live_doubles_alley_probe.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from swingvision import live

CASES_PATH = Path(__file__).resolve().parent.parent / "mobile" / "doubles_alley_parity_cases.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "output" / "live_doubles_alley_python.json"

IDENTITY_H = np.eye(3)


def run_case(x0: float, y0: float, singles: bool, margin: float):
    la = live.LiveAnalyzer(IDENTITY_H, singles=singles, line_margin_m=margin)
    pts = [(x0 - 10.0, y0), (x0 - 1.0, y0), (x0, y0), (x0 + 9.0, y0)]
    call = None
    for i, (x, y) in enumerate(pts):
        call = la.push_position((x, y), float(i))
    assert len(la.calls) == 1, f"expected exactly 1 bounce call, got {len(la.calls)}"
    c = la.calls[0]
    return c.call, c.margin_m, c.xy


def main() -> int:
    spec = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    margin = spec["line_margin_m"]
    cases = spec["cases"]

    results = []
    findings = []  # Python disagreeing with the hand-computed expected -- a FINDING, not silently fixed
    n_fail = 0
    print(f"[live_doubles_alley_probe] Python reference -- {len(cases)} cases x 2 modes, margin={margin} m\n")
    for c in cases:
        row = {"name": c["name"], "x": c["x"], "y": c["y"]}
        for mode, singles in (("singles", True), ("doubles", False)):
            call, margin_m, xy = run_case(c["x"], c["y"], singles, margin)
            expected = c[f"expected_{mode}"]
            row[f"{mode}_call"] = call
            row[f"{mode}_margin_m"] = margin_m
            row[f"{mode}_xy"] = xy
            ok = call == expected
            if not ok:
                n_fail += 1
                findings.append(
                    f"PYTHON DISAGREES WITH HAND-COMPUTED EXPECTED: case={c['name']!r} mode={mode} "
                    f"x={c['x']} y={c['y']} expected={expected} got={call} margin_m={margin_m:+.3f}"
                )
            print(f"  {c['name']:34s} {mode:8s} expected={expected:3s} got={call:3s} "
                  f"margin={margin_m:+.3f}m  {'OK' if ok else 'MISMATCH'}")
        results.append(row)

    print(f"\n{len(cases) * 2 - n_fail}/{len(cases) * 2} match the hand-computed expectation.")
    if findings:
        print("\nFINDINGS (Python live.py itself disagrees with the pre-registered expectation --")
        print("reporting, NOT silently reconciling; live.py is the reference and moves only on")
        print("a deliberate, separately-reviewed change):")
        for f in findings:
            print(f"  - {f}")
    else:
        print("\nNo findings: live.py's singles/doubles branch matches the hand-computed")
        print("expectation on every case. It was already correct (the JS port had drifted from it).")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"line_margin_m": margin, "results": results}, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT_PATH}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
