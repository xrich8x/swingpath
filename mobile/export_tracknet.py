"""Export TrackNet (the ball model) to a MOBILE-optimised ONNX:

  - argmax is baked into the graph, so the runtime returns a small (360x640) int
    heatmap (~1 MB) instead of the raw 256x360x640 logits (~236 MB). That single
    change is what makes on-device decode feasible.
  - verified bit-identical to the PyTorch decode, quantised to int8, benchmarked.

Run from repo root:  backend/.venv/Scripts/python.exe mobile/export_tracknet.py
"""

import os
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort
import torch
import torch.nn as nn
from onnxruntime.quantization import QuantType, quantize_dynamic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from swingvision._tracknet import BallTrackerNet
from swingvision.ball import BallDetector

MODELS = os.path.join(ROOT, "mobile", "models")
WEIGHTS = os.path.join(ROOT, "backend", "weights", "tracknet.pt")
FP32 = os.path.join(MODELS, "tracknet_ball.onnx")
INT8 = os.path.join(MODELS, "tracknet_ball.int8.onnx")
VIDEO = os.path.join(ROOT, "data", "tennis_sample.mp4")
W, H = 640, 360


class MobileTrackNet(nn.Module):
    """TrackNet + in-graph argmax -> compact (B, H*W) int heatmap for the phone."""

    def __init__(self, base):
        super().__init__()
        self.base = base

    def forward(self, x):
        logits = self.base(x)            # (B, 256, H*W)
        return logits.argmax(dim=1)      # (B, H*W) int


base = BallTrackerNet(out_channels=256)
base.load_state_dict(torch.load(WEIGHTS, map_location="cpu"))
model = MobileTrackNet(base).eval()

# --- export ---
torch.onnx.export(
    model, torch.randn(1, 9, H, W), FP32,
    input_names=["frames"], output_names=["heatmap"], opset_version=17,
)
# Re-save with weights embedded (single self-contained file for mobile bundling).
import onnx
onnx.save_model(onnx.load(FP32), FP32, save_as_external_data=False)
print(f"exported {os.path.basename(FP32)}  ({os.path.getsize(FP32)/1e6:.1f} MB)")

# --- real inputs ---
cap = cv2.VideoCapture(VIDEO)
frames = []
while len(frames) < 14:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(cv2.resize(f, (W, H)))
cap.release()
inps = [
    np.rollaxis(np.concatenate([frames[i], frames[i - 1], frames[i - 2]], 2).astype(np.float32) / 255.0, 2, 0)[None]
    for i in range(2, len(frames))
]
bd = BallDetector(WEIGHTS)

# --- verify parity (decoded ball position, PyTorch vs ONNX) ---
sess32 = ort.InferenceSession(FP32, providers=["CPUExecutionProvider"])
def torch_heat(x):
    with torch.no_grad():
        return model(torch.from_numpy(x)).numpy()[0]
errs = []
for x in inps:
    pt = bd._postprocess(torch_heat(x))
    po = bd._postprocess(sess32.run(None, {"frames": x})[0][0])
    if pt[0] is not None and po[0] is not None:
        errs.append(((pt[0] - po[0]) ** 2 + (pt[1] - po[1]) ** 2) ** 0.5)
print(f"fp32 ONNX vs PyTorch ball decode: {np.mean(errs) if errs else 0:.3f}px")

# --- quantize int8 ---
quantize_dynamic(FP32, INT8, weight_type=QuantType.QInt8)
sess8 = ort.InferenceSession(INT8, providers=["CPUExecutionProvider"])
e8 = []
for x in inps:
    p32 = bd._postprocess(sess32.run(None, {"frames": x})[0][0])
    p8 = bd._postprocess(sess8.run(None, {"frames": x})[0][0])
    if p32[0] is not None and p8[0] is not None:
        e8.append(((p32[0] - p8[0]) ** 2 + (p32[1] - p8[1]) ** 2) ** 0.5)
print(f"int8 vs fp32 ball decode: {np.mean(e8) if e8 else 0:.3f}px  ({os.path.getsize(INT8)/1e6:.1f} MB)")

# --- benchmark ---
def bench(fn, n=15):
    fn(inps[0])
    t = time.time()
    for _ in range(n):
        fn(inps[0])
    return (time.time() - t) / n * 1000
ms_t = bench(torch_heat)
ms_32 = bench(lambda x: sess32.run(None, {"frames": x}))
ms_8 = bench(lambda x: sess8.run(None, {"frames": x}))
out_floats = 256 * H * W
print(f"\noutput tensor: in-graph argmax {H*W:,} ints (~{H*W*4/1e6:.1f}MB) vs raw {out_floats:,} floats (~{out_floats*4/1e6:.0f}MB)")
print(f"latency/frame (desktop CPU): PyTorch {ms_t:.0f}ms | ONNX fp32 {ms_32:.0f}ms | ONNX int8 {ms_8:.0f}ms")
print(f"model size: PyTorch {os.path.getsize(WEIGHTS)/1e6:.0f}MB | ONNX int8 {os.path.getsize(INT8)/1e6:.0f}MB")
