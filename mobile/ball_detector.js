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

  // Decode exactly like ball.py's BallDetector._postprocess: threshold the
  // heatmap, find every 8-connected blob, score each by area*peak (not just
  // the brightest pixel), and return the UNWEIGHTED centroid of the winning
  // blob. This matters: a scene can have two separate bright blobs (the ball
  // plus a false response elsewhere, e.g. a court line or a player's kit) —
  // picking by global-argmax-then-small-window (the old approach here) can
  // lock onto a single hot pixel in the WRONG blob while a larger, more
  // coherent blob a few dozen px away is the real ball. Measured on real
  // frames (docs/evidence/ball-detector-parity-tracknet.md): this happened on
  // 4/61 real TrackNet detections in a 178-frame span of am_hard_utr.mp4,
  // with errors up to 238px — small in count, but a CONFIDENT wrong lock with
  // no refusal signal, which is exactly the failure mode this product design
  // refuses elsewhere. cv2.connectedComponentsWithStats(binm, connectivity=8)
  // is the Python reference; this is a plain BFS flood-fill equivalent.
  _decode(heat) {
    const n = heat.length;
    const visited = new Uint8Array(n);
    let best = null, bestScore = 0;
    const stack = [];
    for (let start = 0; start < n; start++) {
      if (visited[start] || heat[start] < this.threshold) continue;
      let count = 0, sx = 0, sy = 0, peak = 0;
      stack.length = 0;
      stack.push(start);
      visited[start] = 1;
      while (stack.length) {
        const idx = stack.pop();
        const y = (idx / IN_W) | 0, x = idx % IN_W;
        count++;
        sx += x;
        sy += y;
        if (heat[idx] > peak) peak = heat[idx];
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || nx >= IN_W || ny < 0 || ny >= IN_H) continue;
            const nIdx = ny * IN_W + nx;
            if (visited[nIdx] || heat[nIdx] < this.threshold) continue;
            visited[nIdx] = 1;
            stack.push(nIdx);
          }
        }
      }
      const score = count * peak;
      if (score > bestScore) {
        bestScore = score;
        best = [sx / count, sy / count];
      }
    }
    return best;
  }
}
