// Verify the JS live-call port produces the SAME calls as the Python version.
// Run:  cd mobile && node verify_live.js
//
// VERIFIED 2026-09-02 (see .claude/journals/frontend-dev.md and
// backend/live_replay_novideo.py for the full derivation):
//   Expected: 7 calls, 7 in / 0 out.
// `backend/live_demo.py replay` cannot run -- data/tennis_sample.mp4 is not in
// the repo -- so this is NOT that replay. Instead, `live.LiveAnalyzer.push_position`
// (backend/swingvision/live.py) is a pure function of (ball_px, t_s): no frame, no
// cv2, no renderer. `backend/live_replay_novideo.py` drives it directly over the
// SAME cached track this file uses (data/output/real_match.perception.json's
// ball_px, cross-checked to have exactly as many entries as tennis_sample.mp4 has
// frames: 4.1s * 30fps = 123 == len(ball_px), from data/output/real_match.json).
// Run it yourself:
//   cd backend && .venv/Scripts/python.exe live_replay_novideo.py \
//     --keypoints ../data/court_pts_refined.json \
//     --cache ../data/output/real_match.perception.json \
//     --match-json ../data/output/real_match.json --fps 30.0
// Its output matches this file's, call-for-call, to 3 decimal places on t_s, xy
// and margin_m, and on the in/out verdict. Python is the reference; this is
// agreement WITH it, not a claim this file's logic is independently correct.
//
// CALIBRATION: this harness reads court_pts_refined.json, NOT court_pts.json.
// court_pts.json is stamped `_audit.verdict: "DEGENERATE"` (38.1px fit residual --
// validate_new_clip.py's own gate rejects it as not a physical camera view).
// Commit 20a672e ("Make a degenerate calibration announce itself...") states
// explicitly that court_pts.json and court_pts_refined.json are two calibrations
// of the SAME clip (tennis_sample.mp4) and that live_demo.py's docstring was
// updated to name court_pts_refined.json "the good version of the same clip".
// Reading court_pts.json here was a harness bug (wrong file), not a genuine
// ambiguity -- fixed 2026-09-02.

import fs from "fs";
import { LiveAnalyzer, computeHomography, LANDMARKS } from "./live_calls.js";

const courtPts = JSON.parse(fs.readFileSync("../data/court_pts_refined.json", "utf-8"));
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
    const m = (c.margin_m >= 0 ? "+" : "") + c.margin_m.toFixed(3);
    console.log(`  t=${c.t_s.toFixed(2)}s  ${c.call.toUpperCase().padEnd(3)}  (${m} m from line)  at (${c.xy[0].toFixed(3)}, ${c.xy[1].toFixed(3)}) m`);
  }
});
const nin = la.calls.filter((c) => c.call === "in").length;
console.log(`\n${la.calls.length} calls (${nin} in / ${la.calls.length - nin} out)`);

// Regression gate: fail loudly (non-zero exit) on ANY drift from the verified
// reference above, rather than just printing a number a human has to compare.
const EXPECTED = { n: 7, nIn: 7 };
if (la.calls.length !== EXPECTED.n || nin !== EXPECTED.nIn) {
  console.error(
    `\nFAIL: expected ${EXPECTED.n} calls (${EXPECTED.nIn} in / ${EXPECTED.n - EXPECTED.nIn} out), ` +
    `got ${la.calls.length} (${nin} in / ${la.calls.length - nin} out). ` +
    `This is a DIVERGENCE from the Python reference (backend/live_replay_novideo.py) ` +
    `-- do not silence this by editing EXPECTED without re-running the Python side.`
  );
  process.exit(1);
}
console.log("PASS -- matches the Python reference (backend/live_replay_novideo.py).");
