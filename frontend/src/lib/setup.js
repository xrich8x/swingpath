// What this camera setup can honestly claim — the browser's copy.
//
// MIRROR of backend/swingvision/setup_state.py. Same rule as court.js and
// calls.js: the Python file is the source of truth, this is the copy the browser
// reads, and the two must be kept in sync. The user-facing STRINGS below are
// pinned character-for-character by backend/tests/test_setup_copy_parity.py —
// they are a product contract, not decoration, and a limitation that is worded
// one way in the CLI and another way in the dashboard is a limitation nobody
// trusts. Change one, change both, in the same commit.
//
// THE THREE AXES (see the Python module for the full argument):
//   framing_status      clear | limited | overlap | unknown — is the far
//                       baseline separable from the net tape? GEOMETRY.
//   calibration_status  user_confirmed | provisional | unavailable — did a
//                       person confirm the four corners? PROVENANCE.
//   metrics_eligible    may court-derived numbers be shown as VERIFIED? Only
//                       when both of the above are good. Re-derived here, never
//                       trusted from the file.
//
// NOT A GATE. Nothing here hides the video, the shot list, the rally clips, the
// highlights or the corrections UI. `metrics_eligible: false` means "do not
// render this as a verified fact" — never "do not show" and never "do not use".

export const FRAMING_CLEAR = "clear";
export const FRAMING_LIMITED = "limited";
export const FRAMING_OVERLAP = "overlap";
export const FRAMING_UNKNOWN = "unknown";
const FRAMING_STATUSES = [FRAMING_CLEAR, FRAMING_LIMITED, FRAMING_OVERLAP, FRAMING_UNKNOWN];

export const CALIB_USER_CONFIRMED = "user_confirmed";
export const CALIB_PROVISIONAL = "provisional";
export const CALIB_UNAVAILABLE = "unavailable";
const CALIBRATION_STATUSES = [CALIB_USER_CONFIRMED, CALIB_PROVISIONAL, CALIB_UNAVAILABLE];

// --- the exact user-facing copy (mirrored verbatim from Python) -------------
export const LOW_CAMERA_TITLE = "Camera is a little low for precise court measurements";
export const LOW_CAMERA_BODY =
  "You can continue recording. Video review, rally clips, highlights, and " +
  "manual corrections will still work. For more reliable speed, bounce " +
  "locations, and line calls, raise the phone until the far baseline is " +
  "clearly visible below the net.";
export const OVERLAP_TITLE = "The net hides the far baseline";
export const OVERLAP_BODY =
  "You can still record and review this match. Court measurements may be less " +
  "reliable, especially on the far half. Raising the phone gives better results.";
export const FRAMING_ACTIONS = [
  "Continue with this setup",
  "Show me how to improve it",
  "Re-check framing",
];
export const CLEAR_SUMMARY =
  "Framing verified: the far baseline is clearly separated from the net tape, " +
  "so the court can be measured normally.";
export const UNKNOWN_SUMMARY =
  "Setup quality was not recorded for this match, so we cannot say how " +
  "reliable the court measurements are.";
export const FAR_BASELINE_QUESTION =
  "Looking at the far end of the court: can you see the far baseline as a " +
  "separate line BELOW the top of the net?";

export function noticeFor(framingStatus) {
  if (framingStatus === FRAMING_LIMITED)
    return { title: LOW_CAMERA_TITLE, body: LOW_CAMERA_BODY, actions: [...FRAMING_ACTIONS] };
  if (framingStatus === FRAMING_OVERLAP)
    return { title: OVERLAP_TITLE, body: OVERLAP_BODY, actions: [...FRAMING_ACTIONS] };
  return null;
}

// Mirror of setup_state.normalize: a match.json with no `setup` block, a partial
// one, or one carrying a status this build does not know, all load as a
// well-formed `unknown`. An old match must open; an unreadable trust state
// degrades to "we do not know", never to "verified".
export function normalizeSetup(raw) {
  const d = raw && typeof raw === "object" ? raw : {};
  const framing = FRAMING_STATUSES.includes(d.framing_status)
    ? d.framing_status
    : FRAMING_UNKNOWN;
  const calibration = CALIBRATION_STATUSES.includes(d.calibration_status)
    ? d.calibration_status
    : CALIB_UNAVAILABLE;
  const px = Number.isFinite(Number(d.far_baseline_clearance_px_720))
    ? Number(d.far_baseline_clearance_px_720)
    : null;
  let reasons = Array.isArray(d.reasons) ? d.reasons.map(String) : [];
  if (framing === FRAMING_UNKNOWN && reasons.length === 0) reasons = [UNKNOWN_SUMMARY];
  return {
    framing_status: framing,
    far_baseline_clearance_px_720: px,
    calibration_status: calibration,
    // Re-derived, never trusted from the file: a hand-edited match.json must not
    // be able to assert its numbers are verified when its own axes say not.
    metrics_eligible: framing === FRAMING_CLEAR && calibration === CALIB_USER_CONFIRMED,
    reasons,
    far_baseline_user_answer:
      d.far_baseline_user_answer === true || d.far_baseline_user_answer === false
        ? d.far_baseline_user_answer
        : null,
    notice: noticeFor(framing),
  };
}

// Mirror of setup_state.summary_line — the text on the persistent status chip.
export function summaryLine(setup) {
  const s = normalizeSetup(setup);
  if (s.framing_status === FRAMING_CLEAR)
    return s.metrics_eligible ? "Framing clear" : "Framing clear - court corners not confirmed";
  if (s.framing_status === FRAMING_LIMITED) return "Limited court accuracy";
  if (s.framing_status === FRAMING_OVERLAP)
    return "Limited court accuracy - net hides the far baseline";
  return "Setup quality not recorded";
}

// --- what the RESULTS UI does with it ---------------------------------------
// One place decides how each state renders, so the Court tab, the Statistics
// tab and the topbar cannot drift into three different opinions about the same
// match. This is presentation policy; the Python side owns the state itself.
//
//   tone           which chip/banner style to use
//   showBanner     is a persistent limitation banner required?
//   labelMetrics   must court-derived values carry an "approximate" label?
//   suppressHeadline  prefer an explicit unavailable state over a
//                  precise-looking number with a tiny disclaimer. TRUE ONLY FOR
//                  `overlap`, where the far court is not in the image at all.
//                  On `limited` the numbers stay, labelled — deleting a usable
//                  figure is its own kind of dishonesty.
export function trustPolicy(setup) {
  const s = normalizeSetup(setup);
  const base = { ...s, chip: summaryLine(s) };
  switch (s.framing_status) {
    case FRAMING_CLEAR:
      return {
        ...base,
        tone: s.metrics_eligible ? "good" : "provisional",
        showBanner: !s.metrics_eligible,
        labelMetrics: !s.metrics_eligible,
        suppressHeadline: false,
        summary: s.metrics_eligible
          ? CLEAR_SUMMARY
          : CLEAR_SUMMARY +
            " The four court corners have not been confirmed by a person, so this calibration is still provisional.",
      };
    case FRAMING_LIMITED:
      return {
        ...base,
        tone: "limited",
        showBanner: true,
        labelMetrics: true,
        suppressHeadline: false,
        summary: LOW_CAMERA_BODY,
      };
    case FRAMING_OVERLAP:
      return {
        ...base,
        tone: "limited",
        showBanner: true,
        labelMetrics: true,
        suppressHeadline: true,
        summary: OVERLAP_BODY,
      };
    default:
      return {
        ...base,
        tone: "unknown",
        showBanner: false,
        labelMetrics: false,
        suppressHeadline: false,
        summary: UNKNOWN_SUMMARY,
      };
  }
}

// --- the setup-time HINT, and why it is only a hint --------------------------
// The exact criterion is `calibration.net_tape_clearance` in Python: it projects
// the top of the net tape and the far baseline and compares their rows, with the
// lens self-calibrated from the homography. It is not reimplemented here. A rule
// with two implementations eventually has two meanings (trap T21), and the whole
// point of the criterion is that there is one number everybody quotes.
//
// What the browser DOES have is the physical camera the shape lock already fits,
// which yields the mount HEIGHT — and height is the quantity the margin actually
// tracks: Spearman(camera height, clearance) = +0.937 over 28 real calibrations,
// against +0.189 for the far/near width ratio that `min_elevation` uses. So a
// height band is a legitimate INDICATION and a dishonest MEASUREMENT, and this
// function is named, typed and worded as the former.
//
// The bands come from the derivation, not from this file: the geometric
// crossover sits at 1.98–2.21 m (median 2.06) and the comfortable +10 px band
// starts at 2.28–2.98 m (median 2.55), over standoff 2–5 m and lens 65–100°.
// Because those are RANGES, a height between them is reported as "cannot say" —
// which is the honest answer for a single number standing in for three.
export const CROSSOVER_LOW_M = 1.98;
export const CROSSOVER_HIGH_M = 2.98;

export function framingHintFromHeight(heightM) {
  const z = Number(heightM);
  if (!Number.isFinite(z)) return { hint: FRAMING_UNKNOWN, text: null };
  if (z < CROSSOVER_LOW_M)
    return {
      hint: FRAMING_OVERLAP,
      text:
        `The court corners you placed imply a camera about ${z.toFixed(1)} m up. ` +
        `Below about ${CROSSOVER_LOW_M} m the net tape projects over the far baseline ` +
        `in every standoff and lens combination that was checked, so the two lines ` +
        `cannot be told apart. This is an indication from the fitted camera; the exact ` +
        `margin is measured by \`run.py check\`.`,
    };
  if (z > CROSSOVER_HIGH_M)
    return {
      hint: FRAMING_CLEAR,
      text:
        `The court corners you placed imply a camera about ${z.toFixed(1)} m up, ` +
        `above the ${CROSSOVER_HIGH_M} m where the far baseline clears the net tape ` +
        `comfortably in every combination checked.`,
    };
  return {
    hint: FRAMING_UNKNOWN,
    text:
      `The court corners you placed imply a camera about ${z.toFixed(1)} m up, ` +
      `inside the ${CROSSOVER_LOW_M}–${CROSSOVER_HIGH_M} m band where the answer ` +
      `depends on how far back you are standing and how wide your lens is. Your own ` +
      `answer above is the better guide here, and \`run.py check\` measures it exactly.`,
  };
}

// The short "why you can still use this" list, shown wherever the banner is.
// Deliberately concrete: a user told "limited accuracy" and nothing else assumes
// the whole app is broken.
export const STILL_WORKS = [
  "Video review and the annotated overlay",
  "Rally clips and highlights",
  "Shot list and shot types",
  "Manual corrections",
];
