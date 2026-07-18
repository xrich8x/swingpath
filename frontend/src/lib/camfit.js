// Physical-camera shape lock, in the browser.
//
// A hand-dragged 4-corner court has 8 degrees of freedom, but a real camera
// looking at a regulation court has ~6 (position, pan, tilt, zoom; phones sit
// level so roll~0). fitCamToQuad projects any 4-corner placement onto the
// closest legal camera view - the same maths as backend courtfit.cam_fit_quad
// (closed-form seed from the quad's own geometry + Nelder-Mead polish), so the
// dashboard's Court Setup behaves exactly like the Python overlay tool.
//
// Corner order everywhere here: [near_bl, near_br, far_br, far_bl] (doubles).

import { LENGTH, DOUBLES_WIDTH } from "./court.js";

const DBL_COURT = [
  [0, 0],
  [DOUBLES_WIDTH, 0],
  [DOUBLES_WIDTH, LENGTH],
  [0, LENGTH],
];

// Project the 4 doubles corners through camera p = [Cx, Cy, Cz, yaw, pitch, f].
export function camCorners(p, w, h) {
  const [Cx, Cy, Cz, yaw, pitch, f] = p;
  const sy = Math.sin(yaw), cy = Math.cos(yaw);
  const st = Math.sin(pitch), ct = Math.cos(pitch);
  const fwd = [sy * ct, cy * ct, -st];
  const right = [cy, -sy, 0];
  const up = [sy * st, cy * st, ct];
  const out = [];
  for (const [X, Y] of DBL_COURT) {
    const d = [X - Cx, Y - Cy, -Cz];
    const z = d[0] * fwd[0] + d[1] * fwd[1] + d[2] * fwd[2];
    if (z < 0.5) return null;
    out.push([
      w / 2 + (f * (d[0] * right[0] + d[1] * right[1] + d[2] * right[2])) / z,
      h / 2 - (f * (d[0] * up[0] + d[1] * up[1] + d[2] * up[2])) / z,
    ]);
  }
  return out;
}

// Closed-form camera guess from the quad itself: distance from the near/far
// width ratio, focal from the pinhole relation, height from vertical extent.
// Covers everything from a phone at the fence to a broadcast telephoto.
function seedFromQuad(q) {
  const [nbl, nbr, fbr, fbl] = q;
  const wn = Math.hypot(nbr[0] - nbl[0], nbr[1] - nbl[1]);
  const wf = Math.hypot(fbr[0] - fbl[0], fbr[1] - fbl[1]);
  if (wf <= 1 || wn <= wf) return null;
  const r = wf / wn;
  const Dn = (r * LENGTH) / (1 - r);
  if (Dn < 1 || Dn > 200) return null;
  const f = (wn * Dn) / DOUBLES_WIDTH;
  const dy = Math.max((nbl[1] + nbr[1]) / 2 - (fbl[1] + fbr[1]) / 2, 1);
  let Cz = dy / (f * (1 / Dn - 1 / (Dn + LENGTH)));
  Cz = Math.min(Math.max(Cz, 0.5), 60);
  const pitch = Math.atan2(Cz, Dn + LENGTH / 2);
  return [DOUBLES_WIDTH / 2, -Dn, Cz, 0, pitch, f];
}

// Minimal Nelder-Mead (6-dim is all we need).
function nelderMead(fn, x0, maxIter = 1200) {
  const n = x0.length;
  let simplex = [x0.slice()];
  for (let i = 0; i < n; i++) {
    const p = x0.slice();
    p[i] += p[i] !== 0 ? 0.05 * Math.abs(p[i]) : 0.1;
    simplex.push(p);
  }
  let vals = simplex.map(fn);
  const alpha = 1, gamma = 2, rho = 0.5, sigma = 0.5;
  for (let it = 0; it < maxIter; it++) {
    const order = vals.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]).map((t) => t[1]);
    simplex = order.map((i) => simplex[i]);
    vals = order.map((i) => vals[i]);
    if (Math.abs(vals[n] - vals[0]) < 1e-3) break;
    const cen = new Array(n).fill(0);
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++) cen[j] += simplex[i][j] / n;
    const worst = simplex[n];
    const refl = cen.map((c, j) => c + alpha * (c - worst[j]));
    const fr = fn(refl);
    if (fr < vals[0]) {
      const exp = cen.map((c, j) => c + gamma * (refl[j] - c));
      const fe = fn(exp);
      if (fe < fr) { simplex[n] = exp; vals[n] = fe; }
      else { simplex[n] = refl; vals[n] = fr; }
    } else if (fr < vals[n - 1]) {
      simplex[n] = refl; vals[n] = fr;
    } else {
      const con = cen.map((c, j) => c + rho * (worst[j] - c));
      const fc = fn(con);
      if (fc < vals[n]) { simplex[n] = con; vals[n] = fc; }
      else {
        for (let i = 1; i <= n; i++) {
          simplex[i] = simplex[0].map((s, j) => s + sigma * (simplex[i][j] - s));
          vals[i] = fn(simplex[i]);
        }
      }
    }
  }
  const best = vals.indexOf(Math.min(...vals));
  return { x: simplex[best], f: vals[best] };
}

// quad: [[x,y] x4] in [near_bl, near_br, far_br, far_bl] order.
// Returns { corners, fitPx, params } (closest legal camera view) or null.
export function fitCamToQuad(quad, w, h) {
  const cost = (p) => {
    const c = camCorners(p, w, h);
    if (!c) return 1e6;
    let s = 0;
    for (let i = 0; i < 4; i++) s += Math.hypot(c[i][0] - quad[i][0], c[i][1] - quad[i][1]);
    return s / 4;
  };
  const fGuess = w * 0.9;
  const starts = [
    [DOUBLES_WIDTH / 2, -6, 4, 0, 0.25, fGuess],
    [DOUBLES_WIDTH / 2, -3, 1.6, 0, 0.1, fGuess],
    [DOUBLES_WIDTH / 2, -12, 8, 0, 0.35, fGuess],
    [DOUBLES_WIDTH / 2, -6, 4, 0, 0.25, w * 1.4],
  ];
  const seed = seedFromQuad(quad);
  if (seed) starts.unshift(seed);

  let best = null;
  for (const x0 of starts) {
    const r = nelderMead(cost, x0);
    if (Number.isFinite(r.f) && r.f < 1e5 && (!best || r.f < best.f)) best = r;
  }
  if (!best) return null;
  const r2 = nelderMead(cost, best.x);          // fresh-simplex restart
  if (r2.f < best.f) best = r2;
  const corners = camCorners(best.x, w, h);
  if (!corners) return null;
  return { corners, fitPx: best.f, params: best.x };
}
