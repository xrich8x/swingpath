"""Summarise tools/audio_impact_screen.py's output, by surface and by venue.

THIS IS A FEASIBILITY SCREEN, NOT AN ACCURACY MEASUREMENT.

Indoor SHELL is always reported as its own line and is never pooled with the
other surfaces — it is the venue where court detection is 0 of 5, so a
correlated audio failure there is the whole point of the screen.

Usage: py tools/audio_impact_screen_report.py [--screen ...] [--loudness ...]
"""
from __future__ import annotations

import argparse
import json
import statistics as st


def venue_of(surface: str, fname: str) -> str:
    if surface != "Shell":
        return surface
    for p in ("flexi_franz", "flexi_joy", "mpc_mixed", "mpc_tuesday", "hillsborough"):
        if fname.startswith(p):
            return f"Shell/{p} (founder-recorded)"
    return "Shell/other (YouTube pulls)"


def agg(rows, key):
    vals = [r[key] for r in rows if key in r and r[key] is not None]
    if not vals:
        return None
    return {"n": len(vals), "median": round(st.median(vals), 3),
            "min": round(min(vals), 3), "max": round(max(vals), 3)}


def line(name, rows):
    ok = [r for r in rows if "n_events_raw" in r]
    bailed = [r for r in ok if r.get("bailed_out")]
    err = [r for r in rows if "error" in r]
    rate = agg(ok, "events_per_s")
    con = agg(ok, "event_contrast_over_local_floor_median")
    gap = agg(ok, "gap_median_s")
    dur = sum(r.get("duration_s", 0) for r in ok)
    return {
        "group": name, "clips": len(rows), "decoded": len(ok), "decode_failed": len(err),
        "bailed_out": len(bailed),
        "audio_minutes": round(dur / 60.0, 1),
        "events_per_s": rate, "contrast_over_local_floor": con,
        "inter_event_gap_s": gap,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", default="data/output/audio_impact_screen.json")
    ap.add_argument("--loudness", default="data/output/audio_loudness.json")
    args = ap.parse_args()
    d = json.load(open(args.screen))
    clips = d["clips"]

    try:
        loud = {r["file"]: r for r in json.load(open(args.loudness))["clips"]}
    except OSError:
        loud = {}

    print("THIS IS A FEASIBILITY SCREEN, NOT AN ACCURACY MEASUREMENT.")
    print("Measured against: nothing. Every number below is a property of the "
          "detector's own output on the clip's own audio. No recall or precision "
          "figure is produced, because the only per-stroke reference in this repo "
          "is SwingVision's burned-in HUD, which rule 11 bars.\n")

    groups = {}
    for r in clips:
        groups.setdefault(venue_of(r["surface"], r["file"]), []).append(r)

    order = sorted(groups, key=lambda g: (not g.startswith("Shell"), g))
    hdr = (f"{'group':34s} {'clips':>5s} {'min':>6s} {'bail':>5s} "
           f"{'ev/s med':>9s} {'ev/s rng':>13s} {'contrast med':>12s} {'gap med':>8s}")
    print(hdr)
    print("-" * len(hdr))
    rows_out = []
    for g in order:
        s = line(g, groups[g])
        rows_out.append(s)
        r, c, gp = s["events_per_s"], s["contrast_over_local_floor"], s["inter_event_gap_s"]
        rng = f"{r['min']:.2f}-{r['max']:.2f}" if r else "-"
        print(f"{g:34s} {s['decoded']:5d} {s['audio_minutes']:6.1f} {s['bailed_out']:5d} "
              f"{(r['median'] if r else 0):9.2f} {rng:>13s} "
              f"{(c['median'] if c else 0):12.2f} {(gp['median'] if gp else 0):8.3f}")

    print("\nSHELL IS REPORTED SEPARATELY AND IS NOT POOLED WITH ANY OTHER SURFACE.\n")

    bail = [r for r in clips if r.get("bailed_out")]
    print(f"bail-outs (detector self-declares useless, returns []): {len(bail)} of "
          f"{len([r for r in clips if 'n_events_raw' in r])} decoded")
    for r in bail:
        print(f"  {r['surface']}/{r['file']}: {r['events_per_s']}/s over "
              f"{r['duration_s']}s")

    fails = [r for r in clips if "error" in r]
    print(f"\ndecode failures (census said audio=true): {len(fails)}")
    for r in fails:
        print(f"  {r['surface']}/{r['file']}: {r['error']}")

    if loud:
        print("\nlevel check (a stream can exist and be silence):")
        quiet = [(f, v) for f, v in loud.items() if v.get("rms_dbfs", 0) < -60]
        print(f"  clips below -60 dBFS RMS: {len(quiet)}")
        for f, v in quiet[:20]:
            print(f"    {f}: rms={v['rms_dbfs']} peak={v['peak_dbfs']}")

    v = d.get("verifications", [])
    if v:
        print(f"\nparity: {sum(1 for x in v if x['match'])}/{len(v)} sampled clips "
              f"reproduce shipped detect_impacts exactly")
    print(f"\nprovenance: {json.dumps(d['provenance']['resolved_config'])}")
    print(f"audio.py sha256[:16]={d['provenance']['audio_py_sha256']} "
          f"commit={d['provenance']['commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
