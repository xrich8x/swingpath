"""compare_match_products.py - diff two match.json files on the outputs a USER sees.

Written for the BallNet-v21-vs-TrackNet chain A/B, but it is detector-agnostic:
hand it any two match.json produced by runs that differ in ONE variable.

WHAT IT REPORTS, and why each is a chain-level number rather than a detector one:

  shots / rallies        what the timeline renders. A detector change reaches
                         these only through events.detect_hits.
  speed coverage         share of shots the product is willing to print a speed
                         for. `speed_confident` is set in pipeline.py from
                         real_fraction(hit, landing) >= 0.5 + a tracked landing,
                         so it is a direct function of how much of the FLIGHT the
                         detector actually held - the closest thing this project
                         has to "did the detector do its job where it mattered".
                         `speed_source == "physics"` is the stricter version: a
                         bounce-anchored arc fit that survived validation.
  line calls             in/out/uncertain, and call_confident.
  ball_track points      how many track points the rally view draws.

HOMOGRAPHY ROUTING. Everything on this page except the raw shot/rally counts
runs through the homography: speeds are a path integral in court metres, line
calls are a ground-plane test, and ball_track is projected. On a clip whose
calibration is wrong these numbers are still a valid A/B (both arms share the
same wrong H) but they are NOT an accuracy statement.

    py tools/compare_match_products.py a.json b.json --labels ballnet21 tracknet
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarise(m: dict) -> dict:
    shots = m.get("shots", [])
    rallies = m.get("rallies", [])
    st = m.get("stats", {})
    n = len(shots)
    conf = [s for s in shots if s.get("speed_confident", True) and s.get("speed_kmh", 0) > 0]
    phys = [s for s in shots if s.get("speed_source") == "physics"]
    nonzero = [s for s in shots if s.get("speed_kmh", 0) > 0]
    calls_conf = [s for s in shots if s.get("call_confident", True)]
    track_pts = sum(len(r.get("ball_track", [])) for r in rallies)
    return {
        "shots": n,
        "rallies": len(rallies),
        "shots_with_speed": len(nonzero),
        "speed_confident": len(conf),
        "speed_confident_pct": round(100 * len(conf) / max(n, 1), 1),
        "speed_physics": len(phys),
        "speed_physics_pct": round(100 * len(phys) / max(n, 1), 1),
        "call_confident": len(calls_conf),
        "call_confident_pct": round(100 * len(calls_conf) / max(n, 1), 1),
        "avg_speed_kmh": st.get("avg_speed_kmh"),
        "top_speed_kmh": st.get("top_speed_kmh"),
        "speed_estimated": st.get("speed_estimated"),
        "line_calls": st.get("line_calls"),
        "ball_track_points": track_pts,
        "shot_mix": st.get("shot_mix"),
    }


FIELDS = ["shots", "rallies", "shots_with_speed", "speed_confident",
          "speed_confident_pct", "speed_physics", "speed_physics_pct",
          "call_confident", "call_confident_pct", "avg_speed_kmh",
          "top_speed_kmh", "ball_track_points"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("matches", nargs="+", help="match.json files, in label order")
    ap.add_argument("--labels", nargs="+", required=True)
    ap.add_argument("--clip", default=None)
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()
    if len(args.matches) != len(args.labels):
        raise SystemExit("one --label per match.json")

    summ = {}
    for lab, p in zip(args.labels, args.matches):
        summ[lab] = summarise(json.loads(Path(p).read_text(encoding="utf-8")))
        summ[lab]["file"] = Path(p).name

    w = max(len(f) for f in FIELDS) + 2
    print(f"\n{args.clip or ''}")
    print(f"{'metric':<{w}}" + "".join(f"{lab:>16}" for lab in args.labels)
          + f"{'delta':>10}")
    print("-" * (w + 16 * len(args.labels) + 10))
    for f in FIELDS:
        vals = [summ[lab].get(f) for lab in args.labels]
        d = ""
        if len(vals) == 2 and all(isinstance(v, (int, float)) for v in vals):
            d = f"{vals[1] - vals[0]:+.1f}"
        print(f"{f:<{w}}" + "".join(f"{('-' if v is None else v):>16}" for v in vals)
              + f"{d:>10}")
    for lab in args.labels:
        print(f"  {lab}: line_calls={summ[lab]['line_calls']} "
              f"speed_estimated={summ[lab]['speed_estimated']}")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(
            {"tool": "compare_match_products", "clip": args.clip,
             "measured_against": "nothing - this is an A/B between two runs of the "
                                 "same pipeline, not an accuracy measurement. Every "
                                 "row except shots/rallies routes through the "
                                 "homography.",
             "arms": summ}, indent=1), encoding="utf-8")
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
