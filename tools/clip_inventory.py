"""clip_inventory.py — fps/resolution/duration of every clip we own.

Session E's first guardrail: "a number without its frame rate is not a result."
This prints the table that lets any later measurement name its fps.

  cd backend && .venv\\Scripts\\python.exe ..\\tools\\clip_inventory.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]


def probe(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"clip": str(path), "error": "cannot open"}
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return {
        "clip": str(path.relative_to(REPO)).replace("\\", "/"),
        "w": w, "h": h,
        "fps": round(fps, 3),
        "frames": n,
        "seconds": round(n / fps, 1) if fps else None,
        "mb": round(path.stat().st_size / 1e6, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--roots", nargs="*", default=["data", "data/train_clips",
                                                  "data/amateur_clips"])
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    rows = []
    for root in args.roots:
        d = REPO / root
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.mp4")):
            rows.append(probe(f))

    rows.sort(key=lambda r: (-(r.get("fps") or 0), r["clip"]))
    print(f"{'clip':<48} {'res':>11} {'fps':>7} {'frames':>7} {'sec':>7}")
    print("-" * 84)
    for r in rows:
        if "error" in r:
            print(f"{r['clip']:<48} {r['error']}")
            continue
        print(f"{r['clip']:<48} {r['w']}x{r['h']:<6} {r['fps']:>7.2f} "
              f"{r['frames']:>7} {r['seconds'] or 0:>7.1f}")

    by_fps: dict[int, int] = {}
    for r in rows:
        if "fps" in r and r["fps"]:
            by_fps[round(r["fps"])] = by_fps.get(round(r["fps"]), 0) + 1
    print("\nclips per fps bucket:", dict(sorted(by_fps.items(), reverse=True)))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
