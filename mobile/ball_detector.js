// ball_detector.js — on-device ball tracking for React Native.
//
// Wraps the mobile TrackNet ONNX (tracknet_ball.int8.onnx) with onnxruntime-
// react-native. Mirrors backend/swingvision/ball.py BallDetector.detect: keeps a
// 3-frame buffer, builds the 9-channel input, runs the model, and decodes the
// heatmap to a ball pixel — then live_calls.js LiveAnalyzer does the rest.
//
//   import { InferenceSession } from "onnxruntime-react-native";
//   const session = await InferenceSession.create(modelPath);
//   const ball = new BallDetector(session);
//   const px = await ball.detect(rgbFrame);   // rgbFrame: HWC RGB Uint8, 360x640
//
// Getting `rgbFrame` is the one native piece: use react-native-vision-camera's
// frame processor to grab the pixel buffer and resize it to 640x360 (see
// MOBILE.md). Everything below is pure JS.

const IN_W = 640;
const IN_H = 360;
const HW = IN_W * IN_H;

export class BallDetector {
  constructor(session, { threshold = 128 } = {}) {
    this.session = session;
    this.threshold = threshold;
    this.buf = []; // last 3 frames as Float32Array (BGR, CHW-ready per-frame)
  }

  reset() {
    this.buf = [];
  }

  // rgbFrame: HWC RGB bytes, 360 rows x 640 cols x 3 (values 0..255).
  // Returns [x, y] in the ORIGINAL frame's pixel space, or null.
  async detect(rgbFrame, origW = IN_W, origH = IN_H) {
    this.buf.push(rgbFrame);
    if (this.buf.length > 3) this.buf.shift();
    if (this.buf.length < 3) return null;

    const input = this._buildInput(); // Float32Array(9*HW), normalized BGR CHW
    const { Tensor } = await import("onnxruntime-react-native");
    const tensor = new Tensor("float32", input, [1, 9, IN_H, IN_W]);
    const out = await this.session.run({ frames: tensor });
    const heat = out.heatmap.data; // Int (length HW): per-pixel intensity 0..255

    const px = this._decode(heat); // [x,y] in 640x360 or null
    if (!px) return null;
    return [px[0] * (origW / IN_W), px[1] * (origH / IN_H)];
  }

  // Stack cur,prev,preprev into 9-channel CHW, BGR order, /255 — exactly as the
  // PyTorch model was trained (OpenCV BGR). Camera frames are RGB, so swap R/B.
  _buildInput() {
    const input = new Float32Array(9 * HW);
    const order = [this.buf[2], this.buf[1], this.buf[0]]; // cur, prev, preprev
    for (let f = 0; f < 3; f++) {
      const frame = order[f];
      const base = f * 3;
      for (let p = 0; p < HW; p++) {
        const r = frame[p * 3], g = frame[p * 3 + 1], b = frame[p * 3 + 2];
        input[(base + 0) * HW + p] = b / 255; // B
        input[(base + 1) * HW + p] = g / 255; // G
        input[(base + 2) * HW + p] = r / 255; // R
      }
    }
    return input;
  }

  // Find the brightest blob in the heatmap and return its centroid (x,y).
  _decode(heat) {
    let max = 0, argmax = -1;
    for (let i = 0; i < heat.length; i++) {
      if (heat[i] > max) { max = heat[i]; argmax = i; }
    }
    if (max < this.threshold) return null;
    // Sub-pixel centroid over a small window around the peak.
    const cy = (argmax / IN_W) | 0, cx = argmax % IN_W;
    let sx = 0, sy = 0, sw = 0;
    for (let dy = -3; dy <= 3; dy++) {
      for (let dx = -3; dx <= 3; dx++) {
        const x = cx + dx, y = cy + dy;
        if (x < 0 || x >= IN_W || y < 0 || y >= IN_H) continue;
        const w = heat[y * IN_W + x];
        if (w >= this.threshold) { sx += x * w; sy += y * w; sw += w; }
      }
    }
    return sw > 0 ? [sx / sw, sy / sw] : [cx, cy];
  }
}
