"""Video probe for the Lab — the one bit of intake that needs OpenCV.

tools/lab_server.py is deliberately stdlib-only so it starts under a bare `py`
with no venv. Reading a video's dimensions and pulling a preview frame needs
cv2, so the Lab shells out to this script with the CPU venv's interpreter
instead of importing cv2 itself. Keeping the dependency on this side of a
subprocess boundary is what lets the labelling and training UI run even when the
venv is broken or missing.

Prints ONE JSON object to stdout. Errors are JSON too ({"error": ...}), so the
caller never has to parse a traceback.

  <venv>/python tools/lab_probe.py probe data/clip.mp4
  <venv>/python tools/lab_probe.py frame data/clip.mp4 500 out.jpg
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def sha1_of(path: Path, chunk: int = 1 << 20) -> str:
    """Match the video_sha1 the gold manifests already carry."""
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def probe(video: Path) -> dict:
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"error": f"cannot open {video}"}
    info = {
        "video": str(video.relative_to(REPO)) if video.is_relative_to(REPO)
                 else str(video),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": round(float(cap.get(cv2.CAP_PROP_FPS)), 4),
        "video_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "size_mb": round(video.stat().st_size / 1e6, 1),
    }
    cap.release()
    info["video_sha1"] = sha1_of(video)
    info["duration_s"] = (round(info["video_frames"] / info["fps"], 1)
                          if info["fps"] > 0 else None)
    return info


def grab(video: Path, index: int, out: Path) -> dict:
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"error": f"cannot open {video}"}
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if index < 0:                      # negative = fraction through the clip
        index = max(0, total // 3)
    cap.set(cv2.CAP_PROP_POS_FRAMES, min(index, max(0, total - 1)))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return {"error": f"could not read frame {index} of {video}"}
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), frame):
        return {"error": f"could not write {out}"}
    return {"ok": True, "frame": index, "path": str(out),
            "width": int(frame.shape[1]), "height": int(frame.shape[0])}


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"error": "usage: lab_probe.py probe|frame ..."}))
        raise SystemExit(2)
    try:
        if args[0] == "probe":
            print(json.dumps(probe(Path(args[1]).resolve())))
        elif args[0] == "frame":
            print(json.dumps(grab(Path(args[1]).resolve(), int(args[2]),
                                  Path(args[3]).resolve())))
        else:
            print(json.dumps({"error": f"unknown command {args[0]!r}"}))
            raise SystemExit(2)
    except ImportError as exc:
        print(json.dumps({"error": f"OpenCV missing in this interpreter: {exc}"}))
        raise SystemExit(1)
    except Exception as exc:                       # noqa: BLE001 - JSON contract
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
