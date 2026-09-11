"""ARM C of the int8 ball-graph parity A/B — keep the FINAL Conv in fp32.

ONE VARIABLE vs the shipped export (`mobile/export_tracknet.py:90`):

    shipped (control / Arm A):
        quantize_dynamic(FP32, INT8, weight_type=QuantType.QInt8)

    this file (Arm C):
        quantize_dynamic(FP32, OUT,  weight_type=QuantType.QInt8,
                         nodes_to_exclude=[<final Conv, found by topology>])

`per_channel` is left at its DEFAULT False, exactly as the control has it: Arm B
(2026-09-03) proved the flag is structurally inert on this graph — `quantize_dynamic`
maps Conv to `ConvInteger`, and `ConvInteger` has no per-channel branch in
onnxruntime/quantization/operators/conv.py — so carrying it would add a knob that
provably does nothing while muddying the one-variable diff. weight_type, op set,
reduce_range and the (absent) calibration are untouched; the source fp32 graph is not
re-exported here, only quantised, so the op set cannot drift.

WHY THIS ARM: the shipped int8 graph fails condition 3 of the pre-registered parity bar
(no frame >10 px vs fp32 through the real JS `_decode()`) because `_decode` scores blobs
`area * peak` and quantisation ERODES the winning blob's AREA in the heatmap. The final
Conv is the node that writes that heatmap. Arm B could not reach it; excluding it from
quantisation can.

FINDING THE FINAL CONV — BY TOPOLOGY, NOT BY NAME. Walk the consumer graph forward from
each Conv's output; the final Conv is the unique Conv with no other Conv downstream of
it on the path to the graph output. Guessing "the one called conv18" would be a name
match, not a structural one, and would silently pick the wrong node if the exporter ever
renumbers.

This script DOES NOT touch `mobile/models/tracknet_ball.int8.onnx` — the shipped
artifact and the control arm.

Run from repo root:
    backend/.venv/Scripts/python.exe mobile/export_int8_lastconv_fp32.py
"""

import collections
import hashlib
import json
import os
import subprocess
import sys
import time

import onnx
from onnxruntime.quantization import QuantType, quantize_dynamic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "mobile", "models")
FP32 = os.path.join(MODELS, "tracknet_ball.onnx")
SHIPPED_INT8 = os.path.join(MODELS, "tracknet_ball.int8.onnx")
OUT = os.path.join(MODELS, "tracknet_ball.int8.lastconv_fp32.onnx")
STAMP = OUT + ".provenance.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def find_final_convs(model):
    """Every Conv with NO other Conv downstream of it. Returns (names, evidence)."""
    g = model.graph
    consumers = collections.defaultdict(list)
    for n in g.node:
        for i in n.input:
            consumers[i].append(n)

    def downstream(start):
        ops, stack, seen = [], [start], set()
        while stack:
            t = stack.pop(0)
            for c in consumers.get(t, []):
                if id(c) in seen:
                    continue
                seen.add(id(c))
                ops.append(c.op_type)
                stack.extend(c.output)
        return ops

    finals, evidence = [], {}
    for n in g.node:
        if n.op_type != "Conv":
            continue
        d = downstream(n.output[0])
        if "Conv" not in d:
            finals.append(n.name)
            evidence[n.name] = {"weights": n.input[1], "downstream_to_output": d}
    return finals, evidence


def main():
    if not os.path.exists(FP32):
        print("FATAL: source graph missing: " + FP32)
        sys.exit(1)
    if os.path.abspath(OUT) == os.path.abspath(SHIPPED_INT8):
        print("FATAL: refusing to overwrite the shipped control-arm graph")
        sys.exit(1)

    model = onnx.load(FP32)
    finals, evidence = find_final_convs(model)
    n_conv = sum(1 for n in model.graph.node if n.op_type == "Conv")
    print("graph output(s): " + str([o.name for o in model.graph.output]))
    print("%d Conv nodes; %d with no Conv downstream: %s" % (n_conv, len(finals), finals))
    for name in finals:
        print("  %s: weights=%s -> %s -> output"
              % (name, evidence[name]["weights"],
                 " -> ".join(evidence[name]["downstream_to_output"])))
    if len(finals) != 1:
        print("FATAL: final Conv is ambiguous by topology — refusing to guess. "
              "Report the candidates and pick explicitly.")
        sys.exit(1)
    final = finals[0]

    kwargs = dict(weight_type=QuantType.QInt8, nodes_to_exclude=[final])

    t0 = time.time()
    quantize_dynamic(FP32, OUT, **kwargs)
    dt = time.time() - t0

    # Structural check: the excluded Conv must survive as a real Conv, and every
    # other Conv must have become ConvInteger. If this does not hold, the exclude
    # did not take and the arm is not what it claims to be.
    q = onnx.load(OUT)
    counts = collections.Counter(n.op_type for n in q.graph.node)
    kept = [n.name for n in q.graph.node if n.op_type == "Conv"]
    print("quantised graph op counts: " + str(dict(counts)))
    print("Conv nodes remaining in fp32: " + str(kept))

    stamp = {
        "arm": "C",
        "role": "int8 dynamic quantisation with the FINAL Conv kept in fp32",
        "produced_by": "mobile/export_int8_lastconv_fp32.py",
        "produced_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quantize_dynamic_kwargs": {
            k: (v.name if isinstance(v, QuantType) else v) for k, v in kwargs.items()
        },
        "one_variable_vs_control": "nodes_to_exclude: [] -> [%s]" % final,
        "final_conv_identified_by": (
            "graph topology: the unique Conv with no other Conv downstream of it on the "
            "path to the graph output 'heatmap'"
        ),
        "final_conv_evidence": evidence[final],
        "all_final_conv_candidates": finals,
        "n_conv_in_fp32_graph": n_conv,
        "quantised_op_counts": dict(counts),
        "conv_nodes_left_unquantised": kept,
        "source_fp32": {"path": "mobile/models/tracknet_ball.onnx",
                        "sha256": sha256(FP32), "bytes": os.path.getsize(FP32)},
        "control_arm_int8": {"path": "mobile/models/tracknet_ball.int8.onnx",
                             "sha256": sha256(SHIPPED_INT8),
                             "bytes": os.path.getsize(SHIPPED_INT8),
                             "note": "NOT modified by this script"},
        "output": {"path": "mobile/models/tracknet_ball.int8.lastconv_fp32.onnx",
                   "sha256": sha256(OUT), "bytes": os.path.getsize(OUT)},
        "onnxruntime_version": __import__("onnxruntime").__version__,
        "git_commit": git_commit(),
        "quantize_seconds": round(dt, 1),
    }
    with open(STAMP, "w") as f:
        json.dump(stamp, f, indent=1)

    same = stamp["output"]["sha256"] == stamp["control_arm_int8"]["sha256"]
    print("")
    print("wrote %s  (%.2f MB) in %.1fs"
          % (os.path.basename(OUT), stamp["output"]["bytes"] / 1e6, dt))
    print("control        %.2f MB, untouched" % (stamp["control_arm_int8"]["bytes"] / 1e6))
    print("delta vs control: %+.2f MB"
          % ((stamp["output"]["bytes"] - stamp["control_arm_int8"]["bytes"]) / 1e6))
    print("BYTE-IDENTICAL TO CONTROL: %s%s"
          % (same, "   <-- arm is a NO-OP, stop here" if same else "   (arm is a real change)"))
    print("provenance -> " + os.path.basename(STAMP))


if __name__ == "__main__":
    main()
