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

// TASK 4 (coordinator follow-up, 2026-09-02): decode the real INT8 graph's
// heatmap the same way decodeOnnxPhase() decodes the fp32 one. Same real
// _decode() method, unmodified — only the heatmap's source graph differs.
function decodeInt8Phase() {
  const py = readResultsJson();
  const updates = [];
  let missing = 0;
  for (const r of py.results) {
    const { tag } = r;
    const int8HeatPath = path.join(OUT, `int8_heat_${tag}.bin`);
    if (!fs.existsSync(int8HeatPath)) { missing++; continue; }
    const bd = new BallDetector(null);
    const heatBuf = fs.readFileSync(int8HeatPath);
    const heat = new Uint8Array(heatBuf.buffer, heatBuf.byteOffset, heatBuf.length);
    if (heat.length !== HW) {
      throw new Error(`int8 heat length ${heat.length} != ${HW} for ${tag}`);
    }
    const px = bd._decode(heat); // REAL method, unmodified
    updates.push({ tag, int8_xy: px ? [px[0], px[1]] : null });
  }
  mergeJsResults(updates);
  console.log(`decode-int8: processed ${updates.length} triples (${missing} missing int8_heat files)`);
}

// ARM-B (variant) phases — 2026-09-03, backend-dev. Separate from
// decodeInt8Phase() on purpose: the int8 path is the CONTROL arm of a
// pre-registered A/B and must stay reproducible, so the treatment gets its own
// mode rather than a mutated control.
//
//   decode-var : decode <BALL_PARITY_PREFIX>_heat_<tag>.bin with the REAL,
//                unmodified _decode(), writing `<prefix>_xy` per tag.
//   blobs-var  : diagnostic dump of EVERY blob (area, peak, area*peak,
//                centroid) the decode considers, for the fp32 heatmap and the
//                variant heatmap, on the tags given. This enumerates blobs a
//                second time rather than calling _decode (which returns only
//                the winner), so it is GUARDED: the top-scoring blob's centroid
//                must equal what the real _decode() returns on the same heat,
//                and the dump records that check. If the guard ever fails the
//                dump is wrong, not the detector.
const PREFIX = process.env.BALL_PARITY_PREFIX || "var";
const TAGS = (process.env.BALL_PARITY_TAGS || "").split(",").map((t) => t.trim()).filter(Boolean);

function readHeat(file) {
  if (!fs.existsSync(file)) return null;
  const buf = fs.readFileSync(file);
  const heat = new Uint8Array(buf.buffer, buf.byteOffset, buf.length);
  if (heat.length !== HW) throw new Error(`heat length ${heat.length} != ${HW} for ${file}`);
  return heat;
}

function decodeVarPhase() {
  const py = readResultsJson();
  const updates = [];
  let missing = 0;
  for (const r of py.results) {
    const { tag } = r;
    if (TAGS.length && !TAGS.includes(tag)) continue;
    const heat = readHeat(path.join(OUT, `${PREFIX}_heat_${tag}.bin`));
    if (!heat) { missing++; continue; }
    const bd = new BallDetector(null);
    const px = bd._decode(heat); // REAL method, unmodified
    updates.push({ tag, [`${PREFIX}_xy`]: px ? [px[0], px[1]] : null });
  }
  mergeJsResults(updates);
  console.log(`decode-var[${PREFIX}]: processed ${updates.length} tags (${missing} missing ${PREFIX}_heat files)`);
}

// Blob enumeration mirroring _decode's 8-connected BFS at the SAME threshold
// instance field. Diagnostic only — see the guard note above.
function enumerateBlobs(heat, threshold) {
  const n = heat.length;
  const visited = new Uint8Array(n);
  const blobs = [];
  const stack = [];
  for (let start = 0; start < n; start++) {
    if (visited[start] || heat[start] < threshold) continue;
    let count = 0, sx = 0, sy = 0, peak = 0;
    stack.length = 0;
    stack.push(start);
    visited[start] = 1;
    while (stack.length) {
      const idx = stack.pop();
      const y = (idx / IN_W) | 0, x = idx % IN_W;
      count++; sx += x; sy += y;
      if (heat[idx] > peak) peak = heat[idx];
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = x + dx, ny = y + dy;
          if (nx < 0 || nx >= IN_W || ny < 0 || ny >= IN_H) continue;
          const nIdx = ny * IN_W + nx;
          if (visited[nIdx] || heat[nIdx] < threshold) continue;
          visited[nIdx] = 1;
          stack.push(nIdx);
        }
      }
    }
    blobs.push({ area: count, peak, score: count * peak, cx: sx / count, cy: sy / count });
  }
  blobs.sort((a, b) => b.score - a.score);
  return blobs;
}

function blobsVarPhase() {
  const bd = new BallDetector(null);
  const out = {};
  for (const tag of TAGS) {
    const sources = {
      fp32: path.join(OUT, `onnx_heat_${tag}.bin`),
      int8_control: path.join(OUT, `int8_heat_${tag}.bin`),
      [PREFIX]: path.join(OUT, `${PREFIX}_heat_${tag}.bin`),
    };
    out[tag] = {};
    for (const [name, file] of Object.entries(sources)) {
      const heat = readHeat(file);
      if (!heat) { out[tag][name] = null; continue; }
      const blobs = enumerateBlobs(heat, bd.threshold);
      const winner = bd._decode(heat); // REAL method — the guard reference
      const top = blobs[0] || null;
      const guard_ok = (winner === null && top === null) ||
        (winner !== null && top !== null &&
         Math.abs(winner[0] - top.cx) < 1e-9 && Math.abs(winner[1] - top.cy) < 1e-9);
      out[tag][name] = {
        threshold: bd.threshold,
        n_blobs: blobs.length,
        top_blobs: blobs.slice(0, 6),
        real_decode_xy: winner,
        guard_top_blob_equals_real_decode: guard_ok,
      };
    }
  }
  const p = path.join(OUT, `blobs_${PREFIX}.json`);
  fs.writeFileSync(p, JSON.stringify(out, null, 1));
  console.log(`blobs-var[${PREFIX}]: wrote ${p} for tags ${TAGS.join(",")}`);
}

const mode = process.argv[2];
if (mode === "build-decode") buildDecodePhase();
else if (mode === "decode-onnx") decodeOnnxPhase();
else if (mode === "decode-int8") decodeInt8Phase();
else if (mode === "decode-var") decodeVarPhase();
else if (mode === "blobs-var") blobsVarPhase();
else {
  console.error("usage: node verify_ball_detector.js <build-decode|decode-onnx|decode-int8|decode-var|blobs-var>");
  process.exit(1);
}
