"""Video-free-style parity probe: mobile/ball_detector.js (ONNX TrackNet port) vs
backend/swingvision/ball.py BallDetector (PyTorch TrackNet, the reference).

Mirrors the technique used for live_calls.js parity (see
docs/evidence/live-call-parity-verified-without-video.md): drive the REAL
production code on each side on IDENTICAL inputs and diff outputs, rather than
re-deriving either implementation.

Two things are checked, both against REAL frames from a gold clip (no synthetic
inputs, no mocked ONNX runtime):

  1. INPUT TENSOR PARITY — does ball_detector.js's `_buildInput()` (channel
     packing / BGR swap / normalisation) produce the same 9x360x640 float32
     tensor Python's BallDetector.detect() builds, given the same 3 raw frames?
  2. DECODE PARITY — does ball_detector.js's `_decode()` (argmax + windowed
     centroid) agree with ball.py's `_postprocess()` (connected-component
     region + area*peak scoring) on the SAME real heatmap?
  3. FULL PIPELINE — JS's _buildInput -> the real bundled ONNX graph
     (mobile/models/tracknet_ball.onnx, fp32) -> JS's _decode, compared to
     Python's real end-to-end detect() (PyTorch model + real _postprocess) on
     the same frame triples.

This script does the PYTHON side (extraction + Python detection + dumps for
Node to consume) and, in --compare mode, the final comparison once Node has
produced its outputs. Python is the reference throughout: nothing here edits
ball.py, and no comparison result is used to change ball.py — only
mobile/ball_detector.js may move.

Usage:
  backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py extract
  node mobile/verify_ball_detector.js   (writes js outputs into the same dir)
  backend/.venv/Scripts/python.exe backend/ball_detector_parity_probe.py compare
"""
import json
import os
import sys

import cv2
import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from swingvision.ball import BallDetector  # noqa: E402

VIDEO = os.path.join(ROOT, "data", "incoming", "Hardcourt", "am_hard_utr.mp4")
WEIGHTS = os.path.join(ROOT, "backend", "weights", "tracknet.pt")
ONNX_FP32 = os.path.join(ROOT, "mobile", "models", "tracknet_ball.onnx")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
    "BALL_PARITY_DIR",
    r"C:\Users\richm\AppData\Local\Temp\claude\e--Claude-Outputs-Cowork-Tasks-Swing-Vision"
    r"\90dad6dd-87a4-4ac2-a50e-c4dab20c69f4\scratchpad\ball_parity",
)
IN_W, IN_H = 640, 360

# Frame span: source frames 0..179 (contiguous, real decode, no frame_step
# skipping) — covers array idx 5-13 and 32-44 of the cached
# am_hard_utr.tracknet.perception.json (frame_step=2, so source frames
# 10-26 and 64-88) where TrackNet is already known to fire on this exact clip,
# plus the frames around/between them (including detector misses, which is
# also part of a fair parity read — not cherry-picking only successes).
N_FRAMES = 180


def extract():
    os.makedirs(OUT, exist_ok=True)
    cap = cv2.VideoCapture(VIDEO)
    if not cap.isOpened():
        print(f"FATAL: could not open {VIDEO}")
        sys.exit(1)
    frames = []
    for _ in range(N_FRAMES):
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.resize(f, (IN_W, IN_H)))  # BGR, uint8, 640x360
    cap.release()
    print(f"decoded {len(frames)} real frames from {VIDEO}")
    if len(frames) < 3:
        print("FATAL: not enough frames")
        sys.exit(1)

    bd = BallDetector(WEIGHTS, device="cpu")
    results = []
    for i in range(2, len(frames)):
        cur, prev, preprev = frames[i], frames[i - 1], frames[i - 2]
        # Mirrors ball.py BallDetector.detect() lines 1092-1105 EXACTLY (same
        # resize-noop since frames are already 640x360, same concat order,
        # same normalisation, same rollaxis) so we can capture the
        # intermediate input tensor and feature_map that detect() computes
        # internally but does not return. bd.model / bd._postprocess below
        # are the REAL, unmodified production objects — nothing here
        # reimplements decode logic.
        imgs = np.concatenate([cur, prev, preprev], axis=2).astype(np.float32) / 255.0
        py_input = np.rollaxis(imgs, 2, 0)[None]  # (1,9,360,640) float32
        inp = torch.from_numpy(py_input).float().to(bd.device)
        with torch.no_grad():
            out = bd.model(inp)
        feature_map = out.argmax(dim=1).detach().cpu().numpy()[0]  # (360*640,) uint-ish
        cx, cy = bd._postprocess(feature_map)  # REAL production decode

        # Dump the 3 raw frames as RGB (camera convention) for JS to consume,
        # and the heat/input tensors for cross-language comparison.
        tag = f"{i:04d}"
        for name, fr in (("cur", cur), ("prev", prev), ("preprev", preprev)):
            rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            rgb.astype(np.uint8).tofile(os.path.join(OUT, f"frame_{tag}_{name}.rgb"))
        py_input.astype(np.float32).tofile(os.path.join(OUT, f"input_{tag}.bin"))
        feature_map.astype(np.uint8).tofile(os.path.join(OUT, f"heat_{tag}.bin"))
        results.append({
            "i": i, "tag": tag,
            "py_xy": [cx, cy] if cx is not None else None,
        })

    with open(os.path.join(OUT, "python_results.json"), "w") as f:
        json.dump({
            "video": VIDEO, "n_triples": len(results), "in_w": IN_W, "in_h": IN_H,
            "results": results,
        }, f, indent=1)
    n_det = sum(1 for r in results if r["py_xy"] is not None)
    print(f"wrote {len(results)} triples to {OUT}; python detected ball in {n_det}/{len(results)}")


def compare():
    with open(os.path.join(OUT, "python_results.json")) as f:
        py = json.load(f)
    js_path = os.path.join(OUT, "js_results.json")
    if not os.path.exists(js_path):
        print(f"FATAL: {js_path} missing — run mobile/verify_ball_detector.js first")
        sys.exit(1)
    with open(js_path) as f:
        js = json.load(f)
    js_by_tag = {r["tag"]: r for r in js["results"]}

    # --- 1. Input tensor parity ---
    tensor_diffs = []
    for r in py["results"][:20]:  # sample; these are large files
        tag = r["tag"]
        jf = os.path.join(OUT, f"js_input_{tag}.bin")
        if not os.path.exists(jf):
            continue
        py_t = np.fromfile(os.path.join(OUT, f"input_{tag}.bin"), dtype=np.float32)
        js_t = np.fromfile(jf, dtype=np.float32)
        if py_t.shape != js_t.shape:
            tensor_diffs.append((tag, "SHAPE MISMATCH", py_t.shape, js_t.shape))
            continue
        tensor_diffs.append((tag, float(np.max(np.abs(py_t - js_t)))))
    print("\n=== 1. INPUT TENSOR PARITY (sample of", len(tensor_diffs), "triples) ===")
    for d in tensor_diffs[:5]:
        print(" ", d)
    numeric = [d[1] for d in tensor_diffs if isinstance(d[1], float)]
    if numeric:
        print(f"  max abs diff across sample: {max(numeric):.8f}  (bar: <1e-5)")
        print(f"  PASS" if max(numeric) < 1e-5 else "  FAIL")

    # --- 2. Decode-only parity (same heat array fed to both _postprocess and _decode) ---
    decode_agree_null = 0
    decode_agree_pos = 0
    decode_both_nonnull = 0
    decode_total = 0
    decode_pos_diffs = []
    mismatches = []
    for r in py["results"]:
        tag = r["tag"]
        jr = js_by_tag.get(tag)
        if jr is None or "decode_xy" not in jr:
            continue
        decode_total += 1
        py_xy = r["py_xy"]
        js_xy = jr["decode_xy"]
        py_null = py_xy is None
        js_null = js_xy is None
        if py_null == js_null:
            decode_agree_null += 1
        if not py_null and not js_null:
            decode_both_nonnull += 1
            dx = py_xy[0] - js_xy[0]
            dy = py_xy[1] - js_xy[1]
            dist = (dx * dx + dy * dy) ** 0.5
            decode_pos_diffs.append(dist)
            if dist <= 5.0:
                decode_agree_pos += 1
            else:
                mismatches.append((tag, py_xy, js_xy, dist))
        elif py_null != js_null:
            mismatches.append((tag, py_xy, js_xy, "NULL MISMATCH"))

    print(f"\n=== 2. DECODE PARITY (identical real heatmap fed to both) — {decode_total} frames ===")
    print(f"  null/non-null agreement: {decode_agree_null}/{decode_total} "
          f"({100*decode_agree_null/max(decode_total,1):.1f}%)  (bar: >=90%)")
    if decode_both_nonnull:
        print(f"  position agreement (<=5px) when both fire: {decode_agree_pos}/{decode_both_nonnull} "
              f"({100*decode_agree_pos/decode_both_nonnull:.1f}%)  (bar: >=80%)")
        print(f"  position diff distribution: min={min(decode_pos_diffs):.2f} "
              f"median={sorted(decode_pos_diffs)[len(decode_pos_diffs)//2]:.2f} "
              f"max={max(decode_pos_diffs):.2f} px")
    print(f"  mismatches ({len(mismatches)} shown up to 15):")
    for m in mismatches[:15]:
        print("   ", m)

    bar1_pass = decode_total > 0 and decode_agree_null / decode_total >= 0.90
    bar2_pass = decode_both_nonnull == 0 or decode_agree_pos / decode_both_nonnull >= 0.80
    print(f"  DECODE BAR: null-agreement {'PASS' if bar1_pass else 'FAIL'}, "
          f"position-agreement {'PASS' if bar2_pass else 'FAIL'}")

    # --- 3. Full pipeline parity (JS buildInput -> real ONNX -> JS decode, vs Python end-to-end) ---
    fp_total = fp_agree_null = fp_agree_pos = fp_both = 0
    fp_pos_diffs = []
    fp_mismatches = []
    for r in py["results"]:
        tag = r["tag"]
        jr = js_by_tag.get(tag)
        if jr is None or "onnx_xy" not in jr:
            continue
        fp_total += 1
        py_xy = r["py_xy"]
        js_xy = jr["onnx_xy"]
        py_null = py_xy is None
        js_null = js_xy is None
        if py_null == js_null:
            fp_agree_null += 1
        if not py_null and not js_null:
            fp_both += 1
            dist = ((py_xy[0]-js_xy[0])**2 + (py_xy[1]-js_xy[1])**2) ** 0.5
            fp_pos_diffs.append(dist)
            if dist <= 5.0:
                fp_agree_pos += 1
            else:
                fp_mismatches.append((tag, py_xy, js_xy, dist))
        elif py_null != js_null:
            fp_mismatches.append((tag, py_xy, js_xy, "NULL MISMATCH"))

    print(f"\n=== 3. FULL PIPELINE PARITY (JS buildInput -> real ONNX fp32 -> JS decode) — {fp_total} frames ===")
    if fp_total:
        print(f"  null/non-null agreement: {fp_agree_null}/{fp_total} ({100*fp_agree_null/fp_total:.1f}%)")
        if fp_both:
            print(f"  position agreement (<=5px): {fp_agree_pos}/{fp_both} ({100*fp_agree_pos/fp_both:.1f}%)")
            print(f"  position diff distribution: min={min(fp_pos_diffs):.2f} "
                  f"median={sorted(fp_pos_diffs)[len(fp_pos_diffs)//2]:.2f} max={max(fp_pos_diffs):.2f} px")
        print(f"  mismatches ({len(fp_mismatches)} shown up to 15):")
        for m in fp_mismatches[:15]:
            print("   ", m)
    else:
        print("  (no onnx_xy entries found — Node ONNX step not run)")

    summary = {
        "input_tensor_max_abs_diff": max(numeric) if numeric else None,
        "decode_parity": {
            "total": decode_total, "null_agree": decode_agree_null,
            "both_nonnull": decode_both_nonnull, "pos_agree_5px": decode_agree_pos,
            "pos_diffs_px": decode_pos_diffs,
        },
        "full_pipeline_parity": {
            "total": fp_total, "null_agree": fp_agree_null,
            "both_nonnull": fp_both, "pos_agree_5px": fp_agree_pos,
            "pos_diffs_px": fp_pos_diffs,
        },
    }
    summary_path = os.path.join(ROOT, "data", "output", "ball_detector_parity_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=1)
    print(f"\nwrote summary to {summary_path}")


def onnx_run():
    """Run the REAL bundled fp32 ONNX graph on JS's own _buildInput() tensors
    (js_input_{tag}.bin, produced by `node verify_ball_detector.js build-decode`)
    and dump the resulting heatmap for JS to decode with its REAL _decode().
    This exercises the actual .onnx file mobile ships — the same graph
    onnxruntime-react-native would load — just via onnxruntime (Python) since
    no RN/onnxruntime-node runtime is installed in this environment (offline,
    nothing installed to fake it). Named explicitly as the one part of the
    chain this cannot exercise: the RN engine binding itself.
    """
    import onnxruntime as ort

    sess = ort.InferenceSession(ONNX_FP32, providers=["CPUExecutionProvider"])
    with open(os.path.join(OUT, "python_results.json")) as f:
        py = json.load(f)
    n = 0
    for r in py["results"]:
        tag = r["tag"]
        jf = os.path.join(OUT, f"js_input_{tag}.bin")
        if not os.path.exists(jf):
            continue
        js_input = np.fromfile(jf, dtype=np.float32).reshape(1, 9, IN_H, IN_W)
        heat = sess.run(None, {"frames": js_input})[0][0]  # (HW,) int-ish
        heat.astype(np.uint8).tofile(os.path.join(OUT, f"onnx_heat_{tag}.bin"))
        n += 1
    print(f"onnx_run: ran real ONNX graph on {n} JS-built input tensors")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("extract", "compare", "onnx-run"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "extract":
        extract()
    elif sys.argv[1] == "onnx-run":
        onnx_run()
    else:
        compare()
