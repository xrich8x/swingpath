import { useState } from "react";
import { normalizeSetup, trustPolicy, STILL_WORKS } from "../lib/setup.js";

// The persistent trust surface: a chip in the topbar and a banner above the
// tabs. ONE component, rendered ABOVE <main>, so the limitation survives every
// navigation between tabs — it is not a per-tab decoration that a user can page
// away from, and it is in the DOM of every screenshot of every tab.
//
// The states, and what each one is allowed to say:
//   clear   + confirmed  "Framing verified" — court metrics stand as measured
//   clear   + provisional  framing is fine, but nobody confirmed the corners
//   limited              the notice, and every court number labelled approximate
//   overlap              the notice, and headline far-court numbers withheld
//   unknown              "not recorded" — neither verified nor limited
//
// NOTHING here hides the video, the shot list, the rallies or the corrections
// UI. That is the whole design: a low camera costs claims, not features.

const TONE_LABEL = {
  good: "Framing verified",
  provisional: "Calibration provisional",
  limited: "Limited court accuracy",
  unknown: "Setup quality not recorded",
};

export function SetupChip({ setup, onClick }) {
  const t = trustPolicy(setup);
  return (
    <button
      className={`trust-chip trust-${t.tone}`}
      onClick={onClick}
      title={t.summary}
      aria-label={`Setup quality: ${t.chip}`}
    >
      <span className="trust-dot" />
      {TONE_LABEL[t.tone]}
    </button>
  );
}

export default function SetupBanner({ setup, open, onToggle }) {
  const t = trustPolicy(setup);
  const s = normalizeSetup(setup);
  const [showHow, setShowHow] = useState(false);

  // `unknown` gets no banner unless the user opens it from the chip: an older
  // match.json is not a problem to warn about, it is simply a match whose setup
  // was never recorded, and shouting about it would train people to dismiss the
  // banner that matters.
  if (!t.showBanner && !open) return null;

  const notice = s.notice;
  return (
    <div className={`trust-banner trust-${t.tone}`} role="status">
      <div className="trust-head">
        <strong>{notice ? notice.title : TONE_LABEL[t.tone]}</strong>
        <button className="btn btn-ghost btn-sm" onClick={onToggle}>
          {open ? "Hide details" : "Details"}
        </button>
      </div>
      <p className="trust-body">{t.summary}</p>

      {open && (
        <div className="trust-details">
          <div className="trust-cols">
            <div>
              <div className="trust-sub">What still works</div>
              <ul className="trust-list">
                {STILL_WORKS.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="trust-sub">Why</div>
              <ul className="trust-list">
                {s.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="trust-facts muted">
            Framing: <code>{s.framing_status}</code> · court corners:{" "}
            <code>{s.calibration_status.replace("_", " ")}</code>
            {s.far_baseline_clearance_px_720 !== null && (
              <>
                {" "}
                · far baseline vs net tape:{" "}
                <code>
                  {s.far_baseline_clearance_px_720 > 0 ? "+" : ""}
                  {Math.round(s.far_baseline_clearance_px_720)} px
                </code>{" "}
                at 720p (positive = clear)
              </>
            )}
          </div>

          {notice && (
            <div className="trust-actions">
              {/* "Continue" is not a button that does anything — you are already
                  continuing. It is here because the copy promises it, and
                  because a notice whose only actions are corrective reads as a
                  refusal even when the words say otherwise. */}
              <span className="trust-continue">✓ {notice.actions[0]}</span>
              <button className="btn btn-sm" onClick={() => setShowHow((v) => !v)}>
                {notice.actions[1]}
              </button>
            </div>
          )}

          {showHow && (
            <div className="trust-how">
              <div className="trust-sub">Raising the camera, in order of payoff</div>
              <ol className="trust-list">
                <li>
                  Clamp the phone to the back fence (about 2.5 m) rather than
                  standing it on a tripod (about 1.5 m). This is the change that
                  moves the far baseline clear of the net tape.
                </li>
                <li>
                  Record at the highest resolution your phone offers. It is free
                  and it roughly doubles how much of the court can be measured.
                </li>
                <li>
                  Aim at the middle of the court and keep all four outer corners
                  in frame — the 0.5&times; ultrawide is fine if a fence is right
                  behind you.
                </li>
                <li>
                  Then re-check framing and set the court corners again, because
                  a calibration describes one camera position only.
                </li>
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// A small inline marker for a single court-derived value. Used by the stats and
// court views so that "approximate" is attached to the NUMBER, not parked in a
// footnote the reader has already scrolled past.
export function ApproxTag({ policy, what = "court measurement" }) {
  if (!policy.labelMetrics) return null;
  return (
    <span
      className="approx-tag"
      title={
        `This ${what} is approximate. ` +
        policy.summary +
        (policy.far_baseline_clearance_px_720 !== null
          ? ` (far baseline vs net tape: ${Math.round(
              policy.far_baseline_clearance_px_720
            )} px at 720p)`
          : "")
      }
    >
      approx
    </span>
  );
}
