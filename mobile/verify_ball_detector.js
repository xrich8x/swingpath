// verify_ball_detector.js — parity harness for ball_detector.js (the ONNX
// TrackNet port) vs backend/swingvision/ball.py BallDetector (the reference).
//
// Companion to backend/ball_detector_parity_probe.py. Runs the REAL, unmodified
// _buildInput() and _decode() methods from ./ball_detector.js against real
// frames extracted from a gold clip by the Python side — no synthetic input,
// no reimplementation of the port's logic here.
//
// ball_detector.js only imports onnxruntime-react-native dynamically INSIDE
// detect(); _buildInput()/_decode() have no runtime dependency, so this runs
// under plain Node with no onnxruntime package installed (none is available
// in this environment/offline — see docs/evidence/
// ball-detector-parity-tracknet.md for what that does and does not verify).
// The real ONNX graph (mobile/models/tracknet_ball.onnx) IS exercised, but via
// Python's onnxruntime running the tensor this script builds (see phase
// "decode-onnx" below and the probe's onnx_run) — the onnxruntime-react-native
// engine binding itself is the one thing this cannot exercise on this machine.
//
// Two phases, run in this order (see backend/ball_detector_parity_probe.py
// docstring for the full pipeline):
//   node mobile/verify_ball_detector.js build-decode   (after `... extract`)
//   node mobile/verify_ball_detector.js decode-onnx     (after `... onnx-run`)

import fs from "node:fs";
import path from "node:path";
import { BallDetector } from "./ball_detector.js";

const OUT = process.env.BALL_PARITY_DIR ||
  "C:\\Users\\richm\\AppData\\Local\\Temp\\claude\\e--Claude-Outputs-Cowork-Tasks-Swing-Vision" +
  "\\90dad6dd-87a4-4ac2-a50e-c4dab20c69f4\\scratchpad\\ball_parity";
const IN_W = 640, IN_H = 360, HW = IN_W * IN_H;

function loadRgb(tag, name) {
  const p = path.join(OUT, `frame_${tag}_${name}.rgb`);
  const buf = fs.readFileSync(p);
  return new Uint8Array(buf.buffer, buf.byteOffset, buf.length); // HWC RGB uint8
}

function readResultsJson() {
  return JSON.parse(fs.readFileSync(path.join(OUT, "python_results.json"), "utf8"));
}

function writeJsResults(results) {
  fs.writeFileSync(
    path.join(OUT, "js_results.json"),
    JSON.stringify({ results }, null, 1)
  );
}

function mergeJsResults(updates) {
  const p = path.join(OUT, "js_results.json");
  let existing = { results: [] };
  if (fs.existsSync(p)) existing = JSON.parse(fs.readFileSync(p, "utf8"));
  const byTag = new Map(existing.results.map((r) => [r.tag, r]));
  for (const u of updates) {
    const cur = byTag.get(u.tag) || { tag: u.tag };
    byTag.set(u.tag, { ...cur, ...u });
  }
  writeJsResults([...byTag.values()]);
}

function buildDecodePhase() {
  const py = readResultsJson();
  const updates = [];
  for (const r of py.results) {
    const { tag } = r;
    const curFile = path.join(OUT, `frame_${tag}_cur.rgb`);
    if (!fs.existsSync(curFile)) continue;
    const cur = loadRgb(tag, "cur");
    const prev = loadRgb(tag, "prev");
    const preprev = loadRgb(tag, "preprev");

    // Reproduce the REAL deque state BallDetector.detect() would have at this
    // call: buf[0]=oldest(preprev), buf[1]=prev, buf[2]=newest(cur). A fresh
    // instance per triple is equivalent to the sliding window's content
    // (maxlen=3 deque has no memory beyond the last 3 frames), same technique
    // used for the doubles-alley parity cases (isolated per-case construction
    // rather than replicated streaming state).
    const bd = new BallDetector(null);
    bd.buf = [preprev, prev, cur];

    const input = bd._buildInput(); // Float32Array(9*HW) — REAL method, unmodified
    fs.writeFileSync(path.join(OUT, `js_input_${tag}.bin`), Buffer.from(input.buffer));

    // Decode-only isolation: feed Python's REAL heatmap (from the PyTorch
    // model, dumped by the probe) into JS's REAL _decode(), no ONNX/runtime
    // involved — isolates the decode ALGORITHM difference from any model or
    // runtime-engine difference.
    const heatPath = path.join(OUT, `heat_${tag}.bin`);
    let decode_xy = null;
    if (fs.existsSync(heatPath)) {
      const heatBuf = fs.readFileSync(heatPath);
      const heat = new Uint8Array(heatBuf.buffer, heatBuf.byteOffset, heatBuf.length);
      if (heat.length !== HW) {
        throw new Error(`heat length ${heat.length} != ${HW} for ${tag}`);
      }
      const px = bd._decode(heat); // REAL method, unmodified
      decode_xy = px ? [px[0], px[1]] : null;
    }
    updates.push({ tag, decode_xy });
  }
  mergeJsResults(updates);
  console.log(`build-decode: processed ${updates.length} triples`);
}

function decodeOnnxPhase() {
  const py = readResultsJson();
  const updates = [];
  let missing = 0;
  for (const r of py.results) {
    const { tag } = r;
    const onnxHeatPath = path.join(OUT, `onnx_heat_${tag}.bin`);
    if (!fs.existsSync(onnxHeatPath)) { missing++; continue; }
    const bd = new BallDetector(null);
    const heatBuf = fs.readFileSync(onnxHeatPath);
    const heat = new Uint8Array(heatBuf.buffer, heatBuf.byteOffset, heatBuf.length);
    if (heat.length !== HW) {
      throw new Error(`onnx heat length ${heat.length} != ${HW} for ${tag}`);
    }
    const px = bd._decode(heat); // REAL method, unmodified — the same decode used in detect()
    updates.push({ tag, onnx_xy: px ? [px[0], px[1]] : null });
  }
  mergeJsResults(updates);
  console.log(`decode-onnx: processed ${updates.length} triples (${missing} missing onnx_heat files)`);
}

const mode = process.argv[2];
if (mode === "build-decode") buildDecodePhase();
else if (mode === "decode-onnx") decodeOnnxPhase();
else {
  console.error("usage: node verify_ball_detector.js <build-decode|decode-onnx>");
  process.exit(1);
}
