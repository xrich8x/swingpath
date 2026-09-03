"""ARM B of the int8 ball-graph parity A/B — per-channel dynamic quantisation.

ONE VARIABLE vs the shipped export (`mobile/export_tracknet.py:90`):

    shipped (control / Arm A):
        quantize_dynamic(FP32, INT8, weight_type=QuantType.QInt8)
        # per_channel defaults to False

    this file (Arm B):
        quantize_dynamic(FP32, OUT,  weight_type=QuantType.QInt8, per_channel=True)

Same source fp32 graph, same weight type, same op set (the op set is a property of
`tracknet_ball.onnx`, which is NOT re-exported here — this script only quantises the
existing file, so the op set cannot drift), same (absent) calibration: dynamic
quantisation has none. `reduce_range` is left at its default, untouched.

WHY: the shipped int8 graph fails condition 3 of the pre-registered parity bar
(no single frame >10 px vs fp32 through the real JS `_decode()`). Root cause on
am_hard_utr tag 0147: `_decode` scores blobs `area * peak`; per-tensor quantisation
erodes the winning blob's AREA (15 px -> 2+1 px), flipping a ~5% margin against a
competing blob. Per-channel scales are the standard mitigation for exactly this —
a single outlier channel no longer sets the scale for the whole weight tensor.

This script DOES NOT touch `mobile/models/tracknet_ball.int8.onnx`. That file is the
shipped artifact and the control arm of the A/B; overwriting it would destroy the
comparison. Output is a sibling.

Run from repo root:
    backend/.venv/Scripts/python.exe mobile/export_int8_perchannel.py
"""

import hashlib
import json
import os
import subprocess
import sys
import time

from onnxruntime.quantization import QuantType, quantize_dynamic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "mobile", "models")
FP32 = os.path.join(MODELS, "tracknet_ball.onnx")
SHIPPED_INT8 = os.path.join(MODELS, "tracknet_ball.int8.onnx")
OUT = os.path.join(MODELS, "tracknet_ball.int8.perchannel.onnx")
STAMP = OUT + ".provenance.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def main():
    if not os.path.exists(FP32):
        print(f"FATAL: source graph missing: {FP32}")
        sys.exit(1)
    if os.path.abspath(OUT) == os.path.abspath(SHIPPED_INT8):
        print("FATAL: refusing to overwrite the shipped control-arm graph")
        sys.exit(1)

    # The RESOLVED kwargs, built once and both PASSED to quantize_dynamic and
    # STAMPED — so the provenance record cannot drift from the call that made
    # the file (a static preset table stamped next to a different call is how a
    # cache outlives its settings).
    kwargs = dict(weight_type=QuantType.QInt8, per_channel=True)

    t0 = time.time()
    quantize_dynamic(FP32, OUT, **kwargs)
    dt = time.time() - t0

    stamp = {
        "arm": "B",
        "role": "per-channel dynamic int8 sibling of the shipped ball graph",
        "produced_by": "mobile/export_int8_perchannel.py",
        "produced_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quantize_dynamic_kwargs": {
            k: (v.name if isinstance(v, QuantType) else v) for k, v in kwargs.items()
        },
        "one_variable_vs_control": "per_channel: False -> True",
        "source_fp32": {
            "path": os.path.relpath(FP32, ROOT).replace("\\", "/"),
            "sha256": sha256(FP32),
            "bytes": os.path.getsize(FP32),
        },
        "control_arm_int8": {
            "path": os.path.relpath(SHIPPED_INT8, ROOT).replace("\\", "/"),
            "sha256": sha256(SHIPPED_INT8) if os.path.exists(SHIPPED_INT8) else None,
            "bytes": os.path.getsize(SHIPPED_INT8) if os.path.exists(SHIPPED_INT8) else None,
            "note": "NOT modified by this script",
        },
        "output": {
            "path": os.path.relpath(OUT, ROOT).replace("\\", "/"),
            "sha256": sha256(OUT),
            "bytes": os.path.getsize(OUT),
        },
        "onnxruntime_version": __import__("onnxruntime").__version__,
        "git_commit": git_commit(),
        "quantize_seconds": round(dt, 1),
    }
    with open(STAMP, "w") as f:
        json.dump(stamp, f, indent=1)

    print(f"wrote {os.path.basename(OUT)}  ({stamp['output']['bytes']/1e6:.1f} MB) in {dt:.1f}s")
    print(f"control {os.path.basename(SHIPPED_INT8)}  "
          f"({(stamp['control_arm_int8']['bytes'] or 0)/1e6:.1f} MB) untouched, "
          f"sha {str(stamp['control_arm_int8']['sha256'])[:12]}")
    print(f"provenance -> {os.path.basename(STAMP)}")


if __name__ == "__main__":
    main()
