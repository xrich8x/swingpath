"""audio_hits.py — measure the audio impact detector against the HUD (E3b).

Before audio hits are allowed anywhere near the events layer, this scores them
against the only per-stroke reference we have: SwingVision's HUD readings
(data/gold/hud_yt_rally2.json). The panel appears a beat AFTER its stroke, so a
HUD stroke counts as covered when an audio event lands in the window
[t_panel - lag_max, t_panel - lag_min].

Precision cannot be scored against the HUD (audio also hears bounces, which the
HUD does not list), so the tool reports the full event list + rate for eyeball
sanity, and coverage as the hard number.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\audio_hits.py \\
      --video ..\\data\\yt_rally2.mp4 --hud ..\\data\\gold\\hud_yt_rally2.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from swingvision import audio  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", required=True)
    ap.add_argument("--hud", default=None, help="hud_ocr.py read output to score against")
    ap.add_argument("--lag", type=float, nargs=2, default=(0.1, 1.6),
                    metavar=("MIN", "MAX"),
                    help="panel appears MIN..MAX s after its stroke")
    ap.add_argument("--k-mad", type=float, default=6.0)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    got = audio.extract_audio(args.video)
    if got is None:
        raise SystemExit("no audio track (or no ffmpeg) — nothing to measure")
    samples, sr = got
    dur = samples.size / sr
    times = audio.detect_impacts(samples, sr, k_mad=args.k_mad)
    print(f"{Path(args.video).name}: {dur:.1f}s audio @ {sr} Hz -> "
          f"{len(times)} impact events ({len(times)/max(dur,1e-9):.2f}/s)")
    print("  " + ", ".join(f"{t:.2f}" for t in times))

    result = {"video": Path(args.video).name, "sr": sr, "k_mad": args.k_mad,
              "events_s": [round(t, 3) for t in times]}

    if args.hud:
        hud = json.loads(Path(args.hud).read_text(encoding="utf-8"))
        lag_lo, lag_hi = args.lag
        covered, misses = [], []
        used: set[int] = set()
        for r in hud["shots"]:
            t_panel = r["t_start_s"]
            cands = [(i, t) for i, t in enumerate(times)
                     if i not in used and lag_lo <= t_panel - t <= lag_hi]
            if cands:
                i, t = min(cands, key=lambda it: t_panel - it[1])
                used.add(i)
                covered.append((r, t))
            else:
                misses.append(r)
        print(f"\nHUD strokes with an audio impact in the window: "
              f"{len(covered)}/{len(hud['shots'])} "
              f"({100*len(covered)/max(len(hud['shots']),1):.0f}%)  "
              f"[visual events layer managed 5/17 on this clip]")
        for r, t in covered:
            print(f"  panel@{r['t_start_s']:>6.2f}s ({r['mph']} MPH) <- audio {t:.2f}s "
                  f"(lag {r['t_start_s']-t:.2f}s)")
        for r in misses:
            print(f"  panel@{r['t_start_s']:>6.2f}s ({r['mph']} MPH) <- NO audio event")
        extra = [t for i, t in enumerate(times) if i not in used]
        print(f"unmatched audio events (bounces/echoes/other): {len(extra)}")
        result.update({
            "hud": Path(args.hud).name, "lag": [lag_lo, lag_hi],
            "hud_covered": len(covered), "hud_total": len(hud["shots"]),
            "unmatched_audio": len(extra),
        })

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
