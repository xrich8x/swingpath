---
name: int8-per-channel-is-a-noop-for-conv
description: two rejected int8 mitigations for the ball graph — per_channel is a silent no-op under quantize_dynamic, and keeping the final Conv in fp32 barely moves it because the blob erosion starts upstream
metadata:
  type: project
---

`onnxruntime.quantization.quantize_dynamic(..., per_channel=True)` is a **silent no-op**
on `mobile/models/tracknet_ball.onnx`. Measured 2026-09-03 (ORT 1.27.0): the output is
**byte-identical** to the shipped per-tensor graph — same sha256
`601bba24a8cb…`, same 10,918,923 bytes.

**Why:** `quantize_dynamic` forces `QuantizationMode.IntegerOps`, so Conv maps to
**`ConvInteger`** via `IntegerOpsRegistry`. In
`onnxruntime/quantization/operators/conv.py` only `QLinearConv` (static) and `QDQConv`
consult `is_per_channel()`; the `ConvInteger` class has no per-channel branch at all.
TrackNet is 18 Convs and nothing else quantisable, so the flag touches zero weights —
confirmed directly: all 18 `*_weight_scale` initializers have dims `[]` (scalar).

**How to apply:** never propose "just turn on per_channel" as an int8 accuracy fix for a
conv-only graph under dynamic quantisation, and never accept a quantised artifact as a
distinct A/B arm without diffing its hash against the control first — this arm looked
like a one-variable change and was in fact no change. Reaching per-channel for this model
requires `quantize_static` with QDQ, which drags in a calibration set: that is a SECOND
variable and a different experiment, not a retune of this one. Related:
[[ball-detector-choice-is-split]], [[traps-this-project-paid-for]].

**Arm C (2026-09-03) also REJECTED, and it localises the fault.** Keeping the final Conv
in fp32 (`nodes_to_exclude=[node_conv2d_17]`, the unique Conv with no Conv downstream of
the `heatmap` output) is a REAL change — 17 ConvInteger + 1 fp32 Conv, +0.44 MB — but on
am_hard_utr 0147 the true blob's area goes 15 (fp32) -> 2 (control) -> **3** (Arm C).
One pixel recovered. So **the area erosion does not originate in the heatmap-writing
convolution; it is already in the int8 features arriving at it.** Output-layer precision
is the wrong lever. 3 of the 4 screen frames still fail; the one that "passed" (yt_rally2
0110) is a 2640-vs-2640 raster-scan tiebreak that Arm C merely reproduced.

Standing context: the shipped int8 ball graph fails condition 3 of the 2026-09-02 parity
bar (no frame >10 px vs fp32 through the real JS `_decode()`) on am_hard_utr 0147 and
yt_rally2 0108/0109/0110, because `_decode` scores blobs `area*peak` and quantisation
erodes (0147, 0108) or inflates (0109, 0110) blob AREA, flipping close two-blob margins.
Peaks barely move; area is the lever.
