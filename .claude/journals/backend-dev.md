# backend-dev — working journal

**READ THIS FIRST IF YOU ARE RESTARTING.** A usage limit kills an agent outright and
nothing restarts it automatically. Whatever is below is what survived.

---

## TASK — CURRENT: ARM C (Arm B is DONE + accepted by the lead, see ARCHIVE below)

**ARM C = shipped export + exactly one added argument: `nodes_to_exclude=[<final Conv>]`,
keeping the heatmap-producing convolution in fp32.** `per_channel` back at DEFAULT False
(proven inert on this graph — carrying it adds a knob that does nothing and muddies the
diff). Output `mobile/models/tracknet_ball.int8.lastconv_fp32.onnx`. Do NOT touch
`tracknet_ball.int8.onnx`. Pre-registered by the lead in `.claude/journals/lead.md`
BEFORE the brief was sent; the bar does not move.

WHY THIS ARM: the failure is AREA EROSION IN THE HEATMAP and the final Conv is what
writes the heatmap. Arm B structurally could not reach it; Arm C can.

FIRST, CHEAPLY: hash Arm C vs the shipped graph BEFORE any inference. Byte-identical =>
that is the whole answer, stop (the Arm B trap).

Identify the final Conv BY GRAPH TOPOLOGY (node feeding the output), not by guessing a
name; if more than one Conv is plausibly "final", say so and name what was excluded.

SCREEN (unchanged, necessary NOT sufficient): am_hard_utr 0147 + yt_rally2 0108/0109/0110
must ALL land within 10 px of fp32. Any one fails => REJECTED, stop, run nothing wider.
A pass only buys the right to a full run, which is the LEAD's to schedule.

ALSO REPORT (not gating): file size; whether excluding the conv changed the null/non-null
answer on those frames. If it PASSES: per-frame int8 latency on the 4 frames (fp32 conv
costs speed; the founder needs the trade stated).

REUSE the harness I built (`onnx-run-var`/`decode-var`/`blobs-var`) + existing parity
dirs. Regenerate nothing. Set BOTH BALL_PARITY_DIR and BALL_PARITY_VIDEO every call.
NOT-THIS-RUN: full 178-frame runs; yt_match40/gold_clay/gold_am/gold_shell parity dirs
(the LEAD is running those NOW — do not touch); static QDQ / calibration (2nd variable);
docs/STATE.md; any git commit. If the screen rejects, STOP — do not invent a third arm.

### ARM C STATE
FINAL CONV = **node_conv2d_17** (weights base.conv18.block.0.weight). Identified BY
TOPOLOGY: of 18 Convs it is the UNIQUE one with no other Conv downstream — path to the
graph output is Conv -> Relu -> BatchNormalization -> Reshape -> ArgMax -> heatmap. No
ambiguity (exactly 1 candidate); node_conv2d_16 still has a Conv downstream.
HASH CHECK **PASSED** (not a no-op this time): Arm C 11.36 MB vs control 10.92 MB,
+0.44 MB, sha differs. Structural check: 17 ConvInteger + **1 Conv** left in fp32, and
that Conv is node_conv2d_17. So the exclude took.
Graph: mobile/models/tracknet_ball.int8.lastconv_fp32.onnx (+ .provenance.json),
exporter mobile/export_int8_lastconv_fp32.py. Prefix for harness runs: **lc8**.

**ARM C IS REJECTED — 3 of 4 tags still fail.** Screen complete, nothing wider run.
| clip | tag | fp32 | int8 ctrl (A) | lastconv_fp32 (C) | dA | **dC** |
|---|---|---|---|---|---|---|
| am_hard_utr | 0147 | [260.93,143.60] | [313.08,191.54] | [313.25,191.58] | 70.831 | **70.989** |
| yt_rally2 | 0108 | [295.38,113.38] | [350.50,163.50] | [350.50,163.50] | 74.493 | **74.493** |
| yt_rally2 | 0109 | [295.46,112.31] | [351.62,162.62] | [351.55,162.64] | 75.393 | **75.355** |
| yt_rally2 | 0110 | [296.50,112.50] | [353.31,161.46] | [296.50,112.50] | 74.996 | **0.000** |
Only 0110 is fixed — and 0110 is the frame whose fp32 answer is itself a 2640-vs-2640
raster-scan tiebreak, so Arm C reproduced a TIE, not a robust win. 0147 got 0.16 px
WORSE. 0108 is bit-for-bit the control's answer.

BLOBS 0147 — the true blob's area was **NOT restored** (target 15):
  fp32 : true 15x220=3300 | false 13x242=3146
  A    : false 13x242=3146 | true frag 2x220=440 | 1x135=135
  C    : false 12x242=2904 | true frag **3**x220=660 | 1x135=135
 15 -> 2 -> 3. Arm C recovered ONE pixel of area. The competitor still outscores the
 true blob 4.4:1. **MECHANISTIC CONCLUSION: the area erosion does NOT originate in the
 heatmap-writing conv — it is already present in the int8 FEATURES arriving at it.**
 Keeping only the last conv in fp32 cannot undo upstream erosion. Any future mitigation
 has to act upstream (or change the decode's area sensitivity), not at the output layer.

BLOBS, other tags:
 0108: C == A exactly; true blob still DELETED outright (n_blobs 2 -> 1), false blob
       12x242=2904 unchanged from fp32. Arm C changed nothing here.
 0109: C restores the FALSE blob to fp32's exact 11x242=2662, but the true blob is still
       eroded 13->12 (2860 -> 2640) and 2640 < 2662 -> still the wrong blob. fp32's
       margin here was only 7.4%.
 0110: C reproduces fp32's blobs exactly (12x220=2640 twice) -> same scan-order tiebreak.

NOT-GATING NUMBERS (reported, not part of the bar):
 - file size 11.36 MB vs control 10.92 MB = **+0.44 MB (+4.1%)**.
 - null/non-null answer UNCHANGED on all four frames: every arm (fp32, A, C) returns a
   non-null detection on all 4. Arm C did not turn a hit into a refusal or vice versa.
 - LATENCY NOT MEASURED: the brief conditions it on a PASSING screen. Screen rejected,
   so it was not run (also keeps CPU free for the lead's concurrent 4-clip runs).

ARTIFACTS (uncommitted): mobile/export_int8_lastconv_fp32.py (new),
mobile/models/tracknet_ball.int8.lastconv_fp32.onnx + .provenance.json,
lc8_heat_<tag>.bin + blobs_lc8.json in both parity dirs. No harness change was needed —
onnx-run-var/decode-var/blobs-var from Arm B took Arm C with only env vars.
No third arm invented. STOPPED.

---

## ARCHIVED TASK (Arm B) — DONE, accepted by the lead

**Arm B of a pre-registered A/B on the int8 ball graph. ONE VARIABLE: `per_channel=True`.**

Shipped `mobile/models/tracknet_ball.int8.onnx` (from `mobile/export_tracknet.py:90`,
`quantize_dynamic(FP32, INT8, weight_type=QInt8)`, per_channel default False) FAILS the
pre-registered parity bar's condition 3.

BAR (pre-registered 2026-09-02, UNCHANGED): int8-vs-fp32, both decoded by the real
`mobile/ball_detector.js _decode()`, over 178 frames: (1) null agreement >=90%,
(2) median disagreement <=2px, (3) NO frame >10px. 1+2 pass; 3 FAILS:
  am_hard_utr 0147: fp32 [260.93,143.60] int8 [313.08,191.54] = 70.831 px
  yt_rally2 0108/0109/0110: 74.493 / 75.393 / 74.996 px (three CONSECUTIVE)

MECHANISM (already root-caused, not mine to re-derive): `_decode` scores blobs
`area*peak`. On 0147 fp32 true ball 15*220=3300 beats competitor 13*242=3146 by ~5%;
int8 fragments the true ball to area 2 + area 1 -> 440, competitor unchanged -> wrong
blob wins. yt_rally2 is the mirror (int8 GROWS the false blob).

DELIVERABLE: one screen verdict, PASS or REJECTED, with per-frame fp32-vs-ArmB
distance for all 4 tags + blob-level area*peak for at least 0147.

CHEAP SCREEN (necessary, NOT sufficient): run Arm B on ONLY those 4 frames, decode with
real JS `_decode()`. All 4 within 10px of fp32 => PASS the screen (buys a full run
later, NOT a pass of the bar). ANY fail => Arm B REJECTED, stop, run nothing wider.

DO NOT overwrite `tracknet_ball.int8.onnx` (shipped artifact + control arm).
Output name: `mobile/models/tracknet_ball.int8.perchannel.onnx`. Leave UNCOMMITTED.
NOT-THIS-RUN: full 178-frame runs, yt_match40, other extractions, the second mitigation
(final conv in higher precision), docs/STATE.md, git commit.

## STATE — where I got to

STARTED 2026-09-03. Not a restart (previous task done+committed `c01c9d1`).

Harness read and understood:
- probe `backend/ball_detector_parity_probe.py`: modes extract|compare|onnx-run|
  onnx-run-int8|compare-int8. Dispatch at line 436. `onnx_run_int8` loops ALL tags,
  resumes by skipping existing `int8_heat_<tag>.bin`.
- JS `mobile/verify_ball_detector.js`: build-decode|decode-onnx|decode-int8.
- `_decode` threshold default = 128; 8-connected BFS; score = count*peak; returns
  UNWEIGHTED centroid.
- Both take BALL_PARITY_DIR; probe also BALL_PARITY_VIDEO. SET BOTH (a mislabel already
  overwrote a real result once).

CACHE DIRS (reuse, do NOT regenerate — already hold js_input_*, onnx_heat_*, python_results.json):
  am_hard: C:\Users\richm\AppData\Local\Temp\claude\e--Claude-Outputs-Cowork-Tasks-Swing-Vision\90dad6dd-87a4-4ac2-a50e-c4dab20c69f4\scratchpad\ball_parity
  rally2 : same root ...\scratchpad\ball_parity_yt_rally2

PLAN:
 1. new file `mobile/export_int8_perchannel.py` — quantize_dynamic(FP32, OUT,
    weight_type=QInt8, per_channel=True). ONE arg differs from export_tracknet.py:90.
 2. probe: add `onnx-run-var` mode (graph from BALL_PARITY_GRAPH, out prefix from
    BALL_PARITY_PREFIX, tag filter BALL_PARITY_TAGS). Do NOT edit the int8 path.
 3. JS: add `decode-var` mode reading <prefix>_heat_<tag>.bin -> `<prefix>_xy`.
 4. run 4 tags only (~10s/frame int8, ~1 min). Another job is on CPU — no wide sweep.
 5. blob dump script for 0147: area/peak/score of every blob >=thresh 128 for fp32
    and ArmB.

### RESULTS — ARM B IS **REJECTED**. Screen run and complete.

**HEADLINE, and it is bigger than the screen: `per_channel=True` is a SILENT NO-OP for
`quantize_dynamic` on this graph.** The Arm B file is BYTE-IDENTICAL to the shipped
control (both sha256 `601bba24a8cb81af329cd598bfabd94f1bf1722cc7845cd700913c0fce896035`,
10,918,923 bytes, onnxruntime 1.27.0). Not "similar" — the same bytes.

Mechanism of the no-op, established from the installed ORT source, not guessed:
 - `quantize_dynamic` sets `mode=QuantizationMode.IntegerOps`; op types default to
   `IntegerOpsRegistry` keys, where Conv -> **`ConvInteger`**.
 - Produced graph is 18x `ConvInteger` (+ DynamicQuantizeLinear/Cast/Add/Relu/BN...).
   ALL 18 `*_weight_scale` initializers have dims `[]` = SCALAR = per-TENSOR, even
   with per_channel=True.
 - `onnxruntime/quantization/operators/conv.py`: only `QLinearConv` (static, line 153)
   and `QDQConv` (line 251) consult `is_per_channel()`. `ConvInteger` (line 17) has NO
   per-channel branch. TrackNet is 100% Conv -> per_channel touches nothing.
 => Per-channel int8 for this model is UNREACHABLE via quantize_dynamic. It needs
    static QDQ (`quantize_static`) — which needs a CALIBRATION SET, i.e. a second
    variable, so it is NOT this A/B and must not be smuggled in as one.

SCREEN, measured anyway (not assumed) through the REAL JS `_decode()`:
| clip | tag | fp32 | int8 control (A) | pc8 (B) | dA px | dB px | heatA==heatB |
|---|---|---|---|---|---|---|---|
| am_hard_utr | 0147 | [260.93,143.60] | [313.08,191.54] | [313.08,191.54] | 70.831 | **70.831** | yes |
| yt_rally2 | 0108 | [295.38,113.38] | [350.50,163.50] | [350.50,163.50] | 74.493 | **74.493** | yes |
| yt_rally2 | 0109 | [295.46,112.31] | [351.62,162.62] | [351.62,162.62] | 75.393 | **75.393** | yes |
| yt_rally2 | 0110 | [296.50,112.50] | [353.31,161.46] | [353.31,161.46] | 74.996 | **74.996** | yes |
4/4 exceed the 10 px bar => **REJECTED**. Nothing wider was run.

BLOBS (threshold 128, 8-connected, score=area*peak; guard: top blob's centroid ==
what real `_decode()` returned, TRUE on every arm/tag):
 am_hard 0147 fp32: true 15x220=3300 | false 13x242=3146     -> true wins by 4.9%
         int8 AND pc8 IDENTICAL: false 13x242=3146 | 2x220=440 | 1x135=135
         -> true ball fragments 15px -> 2+1. Briefed mechanism CONFIRMED, unfixed.
 CORRECTION to the briefed yt_rally2 mechanism ("int8 grows the FALSE blob") — it is
 mixed, and 0108 is the opposite:
  0108 fp32: true 13x242=3146 | false 12x242=2904. int8/pc8: n_blobs 2 -> **1**; the
       false blob is UNCHANGED at 12x242=2904 and the TRUE blob is DELETED OUTRIGHT.
       Same erosion mechanism as 0147, not growth.
  0109 fp32: true 13x220=2860 | false 11x242=2662. int8/pc8: false GROWS 11->13
       (=3146) and true shrinks 13->12 (=2640). Genuine mirror image.
  0110 fp32 is an EXACT TIE 12x220=2640 vs 12x220=2640, broken only by `score >
       bestScore` keeping the FIRST blob in raster scan order (true ball y=112 is
       above false y=161). int8/pc8 grow the false blob to 13x242=3146. FLAG: the
       fp32 "right answer" on 0110 is a scan-order tiebreak, so 0110 is a weak
       instance of the bar, not a strong one.

ARTIFACTS (uncommitted, as briefed):
 mobile/export_int8_perchannel.py (new), mobile/models/tracknet_ball.int8.perchannel.onnx
 + .provenance.json (resolved kwargs stamped from the SAME dict passed to the call),
 probe mode `onnx-run-var` (+58 lines, control int8 path untouched), JS modes
 `decode-var` / `blobs-var` (+115 lines). Heat dumps `pc8_heat_<tag>.bin` and
 `blobs_pc8.json` in both parity dirs.

## LOG — newest first

- 2026-09-03 New task started. Journal TASK/STATE rewritten from the completed
  speed-coverage task (that one: DONE, committed c01c9d1, NOT pushed).
- CARRIED FORWARD: `python` is a broken Store shim. Use
  `backend/.venv/Scripts/python.exe` (CPU), `backend/.venv-train/...` (CUDA).
- CARRIED FORWARD: `grep -rn` across repo root TIMES OUT (huge data dirs) — use Grep tool.
- CARRIED FORWARD: `docs/STATE.md` is CRLF on disk / LF in HEAD. `data/output/*` gitignored.
