// live_calls.js — the line-call brain, ported to JavaScript for on-device use.
//
// This is the same logic as backend/swingvision/live.py + calibration.py, in
// pure JS (no dependencies), so a React Native app can run it on every frame
// after the on-device ball model returns a pixel position. Court constants
// mirror backend/swingvision/court.py and frontend/src/lib/court.js.
//
// Flow on the phone:  camera frame -> ONNX ball model -> [x,y] px
//                     -> analyzer.push([x,y], t) -> {call:"in"|"out", ...} | null

export const COURT = {
  LENGTH: 23.77,
  DOUBLES_WIDTH: 10.97,
  SINGLES_WIDTH: 8.23,
  NET_Y: 23.77 / 2,
  X_LEFT_DOUBLES: 0,
  X_LEFT_SINGLES: (10.97 - 8.23) / 2, // 1.37
  X_RIGHT_SINGLES: 10.97 - (10.97 - 8.23) / 2, // 9.60
  X_RIGHT_DOUBLES: 10.97,
  Y_NEAR_BASELINE: 0,
  Y_FAR_BASELINE: 23.77,
};

// Canonical court coords of the 14 named landmarks (mirror court.LANDMARKS).
export const LANDMARKS = {
  near_bl_doubles: [0, 0],
  near_br_doubles: [10.97, 0],
  far_bl_doubles: [0, 23.77],
  far_br_doubles: [10.97, 23.77],
  near_bl_singles: [1.37, 0],
  near_br_singles: [9.6, 0],
  far_bl_singles: [1.37, 23.77],
  far_br_singles: [9.6, 23.77],
};

// --- linear algebra (just enough) -------------------------------------------

// Solve A x = b for an n x n system by Gaussian elimination with partial pivot.
function solveLinear(A, b) {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let col = 0; col < n; col++) {
    let piv = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[piv][col])) piv = r;
    [M[col], M[piv]] = [M[piv], M[col]];
    const d = M[col][col];
    for (let j = col; j <= n; j++) M[col][j] /= d;
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = M[r][col];
      for (let j = col; j <= n; j++) M[r][j] -= f * M[col][j];
    }
  }
  return M.map((row) => row[n]);
}

// Homography from >=4 court<->image correspondences (exact 4-point DLT).
// courtPts/imagePts: arrays of [x,y]. Returns a 3x3 row-major matrix.
export function computeHomography(courtPts, imagePts) {
  const A = [];
  const b = [];
  for (let i = 0; i < courtPts.length; i++) {
    const [x, y] = courtPts[i];
    const [u, v] = imagePts[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]);
    b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]);
    b.push(v);
  }
  const h = solveLinear(A, b); // h33 fixed to 1
  return [
    [h[0], h[1], h[2]],
    [h[3], h[4], h[5]],
    [h[6], h[7], 1],
  ];
}

function invert3x3(m) {
  const [a, b, c] = m[0], [d, e, f] = m[1], [g, h, i] = m[2];
  const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B + c * C;
  return [
    [A / det, -(b * i - c * h) / det, (b * f - c * e) / det],
    [B / det, (a * i - c * g) / det, -(a * f - c * d) / det],
    [C / det, -(a * h - b * g) / det, (a * e - b * d) / det],
  ];
}

function applyH(H, [x, y]) {
  const u = H[0][0] * x + H[0][1] * y + H[0][2];
  const v = H[1][0] * x + H[1][1] * y + H[1][2];
  const w = H[2][0] * x + H[2][1] * y + H[2][2];
  return [u / w, v / w];
}

export function isInSingles(x, y, margin = 0) {
  return (
    x >= COURT.X_LEFT_SINGLES - margin && x <= COURT.X_RIGHT_SINGLES + margin &&
    y >= COURT.Y_NEAR_BASELINE - margin && y <= COURT.Y_FAR_BASELINE + margin
  );
}

// Mirror of court.is_in_doubles. Added 2026-09-02 alongside the _detectBounce fix
// below -- it did not exist before, which is exactly how the bug survived: there
// was no doubles-bounds check to call.
export function isInDoubles(x, y, margin = 0) {
  return (
    x >= COURT.X_LEFT_DOUBLES - margin && x <= COURT.X_RIGHT_DOUBLES + margin &&
    y >= COURT.Y_NEAR_BASELINE - margin && y <= COURT.Y_FAR_BASELINE + margin
  );
}

// --- the live analyzer (mirror of live.LiveAnalyzer) ------------------------

export class LiveAnalyzer {
  // `homography` maps court metres -> image px (the calibration result).
  constructor(homography, opts = {}) {
    this.Hinv = invert3x3(homography); // image px -> court metres
    this.singles = opts.singles ?? true;
    this.lineMargin = opts.lineMargin ?? 0.05;
    this.minSpeedDrop = opts.minSpeedDrop ?? 0.6;
    this.minCallGap = opts.minCallGap ?? 0.5;
    this.valid = [];   // [t, x_m, y_m]
    this.seg = [];     // court-plane speeds between consecutive valid points
    this.lastCallT = -1e9;
    this.calls = [];
  }

  // ballPx: [x,y] in image pixels, or null for a missed frame. t: seconds.
  push(ballPx, t) {
    if (!ballPx) return null;
    const [x, y] = applyH(this.Hinv, ballPx);
    this.valid.push([t, x, y]);
    const n = this.valid.length;
    if (n >= 2) this.seg.push(this._speed(this.valid[n - 2], this.valid[n - 1]));
    return this._detectBounce();
  }

  _speed(a, b) {
    const dt = b[0] - a[0];
    if (dt <= 0) return 0;
    return Math.hypot(b[1] - a[1], b[2] - a[2]) / dt;
  }

  _detectBounce() {
    const m = this.seg.length;
    if (m < 3) return null;
    const [sPrev, sCand, sNext] = [this.seg[m - 3], this.seg[m - 2], this.seg[m - 1]];
    const isMin = sCand < sPrev && sCand < sNext;
    const isDip = sCand < this.minSpeedDrop * Math.max(sPrev, sNext, 1e-9);
    if (!(isMin && isDip)) return null;
    const [t, x, y] = this.valid[this.valid.length - 2];
    if (t - this.lastCallT < this.minCallGap) return null;
    this.lastCallT = t;
    // FIXED 2026-09-02 (was: unconditionally isInSingles regardless of this.singles).
    // Mirror of live.py's `court.is_in_singles(...) if self.singles else
    // court.is_in_doubles(...)`. The bug: in doubles mode the alley (inside doubles,
    // outside singles) was called OUT while _distanceInside (below, always correct)
    // reported a positive inside margin -- a self-contradictory call, and the wrong
    // one for doubles scoring. See mobile/doubles_alley_parity_cases.json +
    // mobile/verify_live_doubles.js for the parity test that exercises this branch.
    const inBounds = this.singles
      ? isInSingles(x, y, this.lineMargin)
      : isInDoubles(x, y, this.lineMargin);
    const margin = this._distanceInside(x, y);
    const call = { t_s: +t.toFixed(2), xy: [+x.toFixed(3), +y.toFixed(3)], call: inBounds ? "in" : "out", margin_m: +margin.toFixed(3) };
    this.calls.push(call);
    return call;
  }

  _distanceInside(x, y) {
    const xl = this.singles ? COURT.X_LEFT_SINGLES : COURT.X_LEFT_DOUBLES;
    const xr = this.singles ? COURT.X_RIGHT_SINGLES : COURT.X_RIGHT_DOUBLES;
    return Math.min(x - xl, xr - x, y - COURT.Y_NEAR_BASELINE, COURT.Y_FAR_BASELINE - y);
  }
}
