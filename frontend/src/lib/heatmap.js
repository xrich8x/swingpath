// Shot-placement density heatmap over the court (court-metre points -> grid cells).
// Gaussian-splat each landing into a grid, normalize, return drawable cells.
import { DOUBLES_WIDTH, LENGTH } from "./court.js";

export function heatCells(points, { cols = 22, rows = 48, sigma = 1.4, floor = 0.05 } = {}) {
  const cw = DOUBLES_WIDTH / cols;
  const ch = LENGTH / rows;
  const grid = new Float64Array(cols * rows);
  let max = 0;
  const inv2s2 = 1 / (2 * sigma * sigma);
  for (let r = 0; r < rows; r++) {
    const cy = (r + 0.5) * ch;
    for (let c = 0; c < cols; c++) {
      const cx = (c + 0.5) * cw;
      let v = 0;
      for (const p of points) {
        const dx = p[0] - cx;
        const dy = p[1] - cy;
        v += Math.exp(-(dx * dx + dy * dy) * inv2s2);
      }
      grid[r * cols + c] = v;
      if (v > max) max = v;
    }
  }
  const cells = [];
  if (max <= 0) return cells;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const intensity = grid[r * cols + c] / max;
      if (intensity >= floor) {
        cells.push({ x0: c * cw, y0: r * ch, w: cw, h: ch, intensity });
      }
    }
  }
  return cells;
}

// Cool -> hot colour ramp (blue, cyan, green, amber, red).
export function heatColor(t) {
  const stops = [
    [40, 90, 180],
    [40, 170, 180],
    [90, 200, 90],
    [240, 200, 60],
    [230, 70, 50],
  ];
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = stops[i];
  const b = stops[Math.min(i + 1, stops.length - 1)];
  const ch = (k) => Math.round(a[k] + (b[k] - a[k]) * f);
  return `rgb(${ch(0)}, ${ch(1)}, ${ch(2)})`;
}
