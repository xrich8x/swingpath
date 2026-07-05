// Verify the JS live-call port produces the SAME calls as the Python version.
// Run:  cd mobile && node verify_live.js
// Expected (matches backend live_demo.py replay): 7 calls, 5 in / 2 out.

import fs from "fs";
import { LiveAnalyzer, computeHomography, LANDMARKS } from "./live_calls.js";

const courtPts = JSON.parse(fs.readFileSync("../data/court_pts.json", "utf-8"));
const names = Object.keys(courtPts);
const H = computeHomography(
  names.map((n) => LANDMARKS[n]),
  names.map((n) => courtPts[n])
);

const ballPx = JSON.parse(
  fs.readFileSync("../data/output/real_match.perception.json", "utf-8")
).ball_px;

const fps = 30;
const la = new LiveAnalyzer(H, { singles: true });
console.log("JS live line calls (same logic as backend/swingvision/live.py):\n");
ballPx.forEach((px, i) => {
  const c = la.push(px || null, i / fps);
  if (c) {
    const m = (c.margin_m >= 0 ? "+" : "") + c.margin_m.toFixed(2);
    console.log(`  t=${c.t_s.toFixed(2)}s  ${c.call.toUpperCase().padEnd(3)}  (${m} m from line)  at (${c.xy[0].toFixed(1)}, ${c.xy[1].toFixed(1)}) m`);
  }
});
const nin = la.calls.filter((c) => c.call === "in").length;
console.log(`\n${la.calls.length} calls (${nin} in / ${la.calls.length - nin} out)`);
