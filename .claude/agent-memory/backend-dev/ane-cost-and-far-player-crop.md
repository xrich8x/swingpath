---
name: ane-cost-and-far-player-crop
description: Measured ANE cost facts (pose dominates, int8 buys nothing pre-A17) and the P0-3 result that upscale factor, not crop size, is the far-player lever
metadata:
  type: project
---

- **The ANE inverts the desktop cost ordering.** On desktop CPU pose (~0.4 s/frame) was
  cheaper than ball (~0.7 s/frame). On an A13 Neural Engine, `yolo11m-pose@1280` is
  roughly 25× the ball model, because ANE cost tracks FLOPs. Estimated, not measured on a
  phone — no phone benchmark exists in this repo.
- **int8 buys no compute speedup on an A13.** int8×int8 ANE compute begins at A17 Pro;
  earlier silicon stores int8 weights and dequantises to fp16. It buys download size and
  memory bandwidth. Plan on fp16.
- **[measured 2026-08-28] The far player needs ~100–140 px in the model INPUT TENSOR, and
  the lever is the UPSCALE FACTOR, not the crop size.** On `yt_match40` the far player is
  ~30–34 px native. Full frame @1280 (1.0×) finds them at **0 of 25** far-end contacts.
  A 192 px crop fed at 640 (3.33× → ~110 px) finds them at **15 of 25**; a 320 px crop at
  1280 (4.0× → ~135 px) at 13 of 25. Below ~90 px nothing; at 6.67× (~203 px) it falls
  back to 6. **Crop size 192 and 320 both work** if the ratio is right — do not
  re-derive this as a crop-size question. PROVISIONAL until a human reads the contact
  sheets (`data/output/p0_3_sheet_yt_match40_crop192at640_x.png`).
- **[measured 2026-08-28] The cheapest good arm is also the best.** `crop192@640` beats
  `crop192@1280` at a quarter the cost. Nothing argues for a bigger input tensor.
- **P0-2 (full-frame pose downscaling) is NOT ESTABLISHED, not a closed negative.** Its
  `yt_match40` column is withdrawn — see [[calibration-trap-check-corners-first]].
  Surviving evidence is `am_hard_utr` 1.0 → 0.0 → 0.0, which never had headroom to
  measure a 2-pt gate.

**How to apply:** pose scheduling is the binding runtime decision. Run pose on fewer
frames, never at lower resolution.

Related: [[ios-architecture-rules]], [[data-limits-far-end-contacts]].
