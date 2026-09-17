# Platform, runtime & on-device — CLOSED

**Things tried here that did NOT work, and the number that killed each one.**

Read this before proposing anything in this area. Hard rule 3: **do not re-propose these.** Nine
distinct ideas in this project have been re-proposed at least once, each costing a run to re-kill.

**The code is gone, not lost.** Where a row names a deleted file, recover it with:

```bash
git log --diff-filter=D --oneline -- <path>     # find the commit that removed it
git show <sha>^:<path>                          # print the file as it last existed
```

A row here is a verdict. The mechanism and the war story live in `docs/evidence/`.

| What was tried | What we did | The result that killed it | Deleted code | Evidence |
|---|---|---|---|---|
| **The ONNX / React-Native mobile port** | Exported TrackNet to ONNX int8 with argmax in-graph; ported the call logic to JS; verified bit-parity two ways | **SHELVED to `v2/mobile/`, not deleted - wrong RUNTIME, not wrong code.** The product is iPhone-only on the Neural Engine; ONNX + onnxruntime-react-native + NNAPI targets neither. **What it proved is worth keeping: the line-call brain ported to another language bit-identically, first pass.** That is the evidence the Swift port is cheap | `v2/mobile/` | [live-call-parity-verified-without-video](../../../../evidence/live-call-parity-verified-without-video.md) |
| **Per-channel int8 (`per_channel=True`) for the ball graph** | Re-quantize per channel | **REJECTED - it is a silent NO-OP, not a loss.** Byte-identical graph (same sha256, same 10,918,923 bytes): `quantize_dynamic` forces `IntegerOps` -> `ConvInteger`, which has no per-channel branch | `v2/mobile/export_int8_perchannel.py` | [int8-parity-qa-verification](../../../../evidence/int8-parity-qa-verification.md) |
| **Keeping the FINAL conv in fp32 to stop blob erosion** | `nodes_to_exclude` on the last conv | **REJECTED** - 3 of 4 screen frames still fail. A genuine graph change (+0.44 MB), so a real negative: true blob area **15 -> 2 -> 3** against a target of 15 | `v2/mobile/export_int8_lastconv_fp32.py` | [int8-parity-qa-verification](../../../../evidence/int8-parity-qa-verification.md) |
| **A precision boundary above where int8 erosion 'first appears'** | Per-layer activation diff over 36 shared tensors | **The premise is FALSE.** Relative L2 rises through the encoder, peaks at the bottleneck and falls through the decoder - **identically on passing and failing frames** | - | - |
| **Downscaling the pose INPUT to afford it on an A13 (P0-2)** | Compare far-player detection at 1280 / 640 / 384 | **NOT ESTABLISHED - the `yt_match40` column is WITHDRAWN.** That clip's calibration is wrong (T23), so the pipeline labelled the NEAR player FAR | `tools/p0_3_crop_probe.py and the P0-3 family` | [pose-downscale-far-player](../../../../evidence/pose-downscale-far-player.md) |
| **Exporting Core ML on Windows** | `coremltools` on the Windows wheel | `RuntimeError: BlobWriter not loaded` - the Windows wheel is pure Python. **Linux works and bills at 1x instead of macOS's 10x** | - | [coreml-export-on-linux](../../../../evidence/coreml-export-on-linux.md) |
