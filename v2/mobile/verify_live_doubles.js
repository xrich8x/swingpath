// verify_live_doubles.js — PARITY test for the singles/doubles branch fix at
// live_calls.js:145 (was: `isInSingles` called unconditionally regardless of
// `this.singles`, so a doubles-mode alley ball was called OUT with a positive
// "inside" margin on screen -- self-contradictory, and wrong for doubles
// scoring; see the comment above `_detectBounce`'s `inBounds` line).
//
// This is a PARITY test, not an accuracy test: doubles_alley_parity_cases.json
// holds SYNTHETIC court-plane positions (no camera, no real ball trajectory,
// no invented ground truth) chosen to straddle every X/Y boundary that
// matters, with expected_singles/expected_doubles HAND-COMPUTED from the raw
// court constants -- independently of both implementations. Python
// (backend/swingvision/live.py) is the reference; this only asserts the JS
// port agrees with it AND with the hand-computed expectation.
//
// Each case is turned into a minimal 4-point synthetic trajectory (identity
// homography, so pushed "pixel" coords equal court metres directly) that
// produces exactly one bounce call at the target position -- the same
// push()/_detectBounce() code path a real bounce takes, so it actually
// exercises the fixed line rather than testing isInSingles/isInDoubles in
// isolation (which were each already correct; the bug was in the wiring).
//
// Run:  cd backend && python live_doubles_alley_probe.py   (writes the Python
//       reference to data/output/live_doubles_alley_python.json)
//       cd mobile && node verify_live_doubles.js

import fs from "fs";
import { LiveAnalyzer } from "./live_calls.js";

const IDENTITY_H = [
  [1, 0, 0],
  [0, 1, 0],
  [0, 0, 1],
];

function runCase(x0, y0, singles, margin) {
  const la = new LiveAnalyzer(IDENTITY_H, { singles, lineMargin: margin });
  const pts = [
    [x0 - 10, y0],
    [x0 - 1, y0],
    [x0, y0],
    [x0 + 9, y0],
  ];
  pts.forEach((p, i) => la.push(p, i));
  if (la.calls.length !== 1) {
    throw new Error(`expected exactly 1 bounce call for (${x0},${y0}) singles=${singles}, got ${la.calls.length}`);
  }
  const c = la.calls[0];
  return { call: c.call, margin_m: c.margin_m, xy: c.xy };
}

const spec = JSON.parse(fs.readFileSync("./doubles_alley_parity_cases.json", "utf-8"));
const margin = spec.line_margin_m;
const cases = spec.cases;

let pyRef = null;
try {
  pyRef = JSON.parse(fs.readFileSync("../data/output/live_doubles_alley_python.json", "utf-8"));
} catch {
  console.log("NOTE: no Python reference found at ../data/output/live_doubles_alley_python.json");
  console.log("      (run: cd backend && python live_doubles_alley_probe.py). Checking against");
  console.log("      the hand-computed expectation only -- NOT a parity check without it.\n");
}
const pyByName = pyRef ? Object.fromEntries(pyRef.results.map((r) => [r.name, r])) : null;

console.log(`[verify_live_doubles] JS port -- ${cases.length} cases x 2 modes, margin=${margin} m\n`);

let nFail = 0;
let nParityFail = 0;
for (const c of cases) {
  for (const mode of ["singles", "doubles"]) {
    const singles = mode === "singles";
    const { call, margin_m } = runCase(c.x, c.y, singles, margin);
    const expected = c[`expected_${mode}`];
    const okExpected = call === expected;
    if (!okExpected) nFail++;

    let parityNote = "";
    if (pyByName) {
      const pyCall = pyByName[c.name][`${mode}_call`];
      const pyMargin = pyByName[c.name][`${mode}_margin_m`];
      const parityOk = call === pyCall && Math.abs(margin_m - pyMargin) <= 0.001;
      if (!parityOk) {
        nParityFail++;
        parityNote = `  DIVERGES FROM PYTHON (py=${pyCall} ${pyMargin.toFixed(3)}m)`;
      }
    }

    console.log(
      `  ${c.name.padEnd(34)} ${mode.padEnd(8)} expected=${expected.padEnd(3)} got=${call.padEnd(3)} ` +
      `margin=${margin_m >= 0 ? "+" : ""}${margin_m.toFixed(3)}m  ${okExpected ? "OK" : "MISMATCH"}${parityNote}`
    );
  }
}

console.log(`\n${cases.length * 2 - nFail}/${cases.length * 2} match the hand-computed expectation.`);
if (pyByName) {
  console.log(`${cases.length * 2 - nParityFail}/${cases.length * 2} match the Python reference (live_doubles_alley_probe.py) within 0.001 m.`);
}

if (nFail > 0 || nParityFail > 0 || !pyByName) {
  console.error(
    `\nFAIL: ${nFail} case(s) diverge from the hand-computed expectation, ` +
    `${nParityFail} diverge from Python` +
    (pyByName ? "." : ", and no Python reference was found to compare against.")
  );
  process.exit(1);
}
console.log("\nPASS -- JS matches both the hand-computed expectation and the Python reference in singles AND doubles mode.");
