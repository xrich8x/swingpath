// Verify the JS live-call port produces the SAME calls as the Python version.
// Run:  cd mobile && node verify_live.js
// Expected (matches backend live_demo.py replay): 7 calls, 5 in / 2 out.
// NOTE 2026-09-02: this expectation is currently UNVERIFIABLE. The Python
// reference (`live_demo.py replay --video ../data/tennis_sample.mp4`) cannot run --
// that sample video is not in the repo -- so nothing can say whether 5in/2out is
// still right, nor which calibration it was recorded against. This harness reads
// court_pts.json and produces 6in/1out; pointed at court_pts_refined.json (what
// live_demo.py names) it produces 7in/0out. Do NOT "fix" the port against either
// number until the reference can be re-run. Restoring tennis_sample.mp4 is the
// unblocker.

import fs from "fs";
import { LiveAnalyzer, computeHomography, LANDMARKS } from "./live_calls.js";

const courtPts = JSON.parse(fs.readFileSync("../data/court_pts.json", "utf-8"));
// Drop the `_`-prefixed metadata keys, mirroring pipeline.py's
//   named = {k: v for k, v in raw.items() if not k.startswith("_")}
// A calibration file is not just landmarks: the Court Setup tool stamps `_exact`
// when the user placed corners with shape-lock off, and validate_new_clip.py
// stamps `_audit` with the camera verdict. Python has always stripped them; this
// port did not, so once calibrations started carrying an audit stamp
// `LANDMARKS["_audit"]` came back undefined and this harness died on
// "undefined is not iterable" -- taking the ONLY parity check the mobile
// live-call port has with it, silently.
const names = Object.keys(courtPts).filter((k) => !k.startsWith("_"));
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
