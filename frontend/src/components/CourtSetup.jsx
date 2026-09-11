import { useEffect, useMemo, useRef, useState } from "react";
import { LINES, NET_LINE, LENGTH, DOUBLES_WIDTH } from "../lib/court.js";
import { computeHomography, applyHomography } from "../lib/homography.js";
import { fitCamToQuad } from "../lib/camfit.js";
import { callVerdict } from "../lib/calls.js";
import {
  FAR_BASELINE_QUESTION,
  framingHintFromHeight,
  noticeFor,
  FRAMING_OVERLAP,
  FRAMING_UNKNOWN,
} from "../lib/setup.js";

// SwingVision-style court setup: a fixed camera is calibrated ONCE by dragging
// the four court corners onto the real corners. Coarse placement is by drag;
// fine placement (esp. on a phone) is by the on-screen nudge pad / arrow keys,
// with a magnifier loupe so you can see exactly where the corner lands.
// "Shape lock" keeps the court a real camera's view of a regulation court while
// you steer (corners re-solve together); turn it off to place corners exactly
// (wide lenses bend the real lines away from any rigid view).

const PAD = 90; // draggable margin around the frame so edge corners are reachable
const ZOOM = 3.5;
const LOUPE_R = 120;

// PLAIN LANGUAGE, not landmark keys. A normal player has never heard of a
// "doubles corner"; they can see the far end of the court and the tramline they
// are standing next to. Each corner therefore carries a `plain` name and a
// `where` sentence that describes the physical spot to click, and the confirm
// step names them one at a time.
const CORNERS = [
  { key: "far_bl_doubles", court: [0, LENGTH], label: "far-left", at: [0.34, 0.35],
    plain: "Far end, left corner",
    where: "The far end of the court, on YOUR left - the outermost corner, where the back line meets the outside tramline." },
  { key: "far_br_doubles", court: [DOUBLES_WIDTH, LENGTH], label: "far-right", at: [0.66, 0.35],
    plain: "Far end, right corner",
    where: "The far end of the court, on YOUR right - again the outermost corner, outside the tramline." },
  { key: "near_bl_doubles", court: [0, 0], label: "near-left", at: [0.16, 0.86],
    plain: "Near end, left corner",
    where: "The near end, on your left. If a corner is off the edge of the frame, zoom out and grab the frame again." },
  { key: "near_br_doubles", court: [DOUBLES_WIDTH, 0], label: "near-right", at: [0.84, 0.86],
    plain: "Near end, right corner",
    where: "The near end, on your right. All four outer corners must be visible before you confirm." },
];
// camfit's fixed corner order
const DBL_ORDER = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"];
const defaultCorners = (w, h) =>
  Object.fromEntries(CORNERS.map((c) => [c.key, [w * c.at[0], h * c.at[1]]]));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

export default function CourtSetup({ match }) {
  const svgRef = useRef(null);
  const fileRef = useRef(null);
  const nudgeTimer = useRef(null);
  const [frame, setFrame] = useState({ src: "/court_setup_frame.jpg", w: 1280, h: 720 });
  const [pts, setPts] = useState(() => defaultCorners(1280, 720));
  const [drag, setDrag] = useState(null);
  const [selected, setSelected] = useState("near_br_doubles");
  const [step, setStep] = useState(1);
  const [lockShape, setLockShape] = useState(true);
  const [note, setNote] = useState("");
  // Mount grade, recomputed off the current corners (see the effect below).
  const [mount, setMount] = useState(null);
  const mountTimer = useRef(null);
  // --- the guided flow -------------------------------------------------------
  // FEATURE 1: the framing question, asked BEFORE any calibration exists. There
  // is no honest automatic answer at that moment - the clearance criterion needs
  // a homography - so the person holding the phone is asked, and the answer is
  // recorded as an ANSWER rather than laundered into a measurement.
  const [farBaseline, setFarBaseline] = useState(null);   // true | false | null
  // FEATURE 2: nothing is saved as confirmed until the user has ticked all four
  // corners by their plain-language names, one at a time. `_exact` used to be
  // read as "a human placed these" and never meant it (trap T26); this does.
  const [confirmed, setConfirmed] = useState({});
  const [reviewing, setReviewing] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);

  // Seed the corners from the ANALYZED match's own calibration when it carries
  // one (match.calibration.corners — written by run.py analyze), else from the
  // static /court_setup_seed.json. The user then only fine-tunes.
  useEffect(() => {
    const cal = match?.calibration?.corners;
    if (cal && CORNERS.every((c) => Array.isArray(cal[c.key]))) {
      setPts(Object.fromEntries(CORNERS.map((c) => [c.key, [...cal[c.key]]])));
      setNote("Loaded this match's calibration — adjust if needed, then save.");
      return;
    }
    fetch("/court_setup_seed.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((seed) => {
        if (seed && CORNERS.every((c) => Array.isArray(seed[c.key]))) {
          setPts(Object.fromEntries(CORNERS.map((c) => [c.key, [...seed[c.key]]])));
        }
      })
      .catch(() => {});
  }, [match]);

  // Project the current 4 corners onto the closest LEGAL camera view of a
  // regulation court (the shape lock). Returns the locked pts (or the input).
  function lockedPts(s) {
    const quad = DBL_ORDER.map((k) => s[k]);
    const fit = fitCamToQuad(quad, frame.w, frame.h);
    if (!fit) return s;
    const out = { ...s };
    DBL_ORDER.forEach((k, i) => (out[k] = [fit.corners[i][0], fit.corners[i][1]]));
    if (fit.fitPx > 3) {
      setNote(`Shape locked to a real camera view (adjusted ~${fit.fitPx.toFixed(0)}px). ` +
              "Untick Shape lock to place corners exactly.");
    }
    return out;
  }
  function resolveShape() {
    if (lockShape) setPts((s) => lockedPts(s));
  }

  const H = useMemo(
    () => computeHomography(CORNERS.map((c) => c.court), CORNERS.map((c) => pts[c.key])),
    [pts]
  );
  const lines = useMemo(
    () => (H ? LINES.map(([a, b]) => [applyHomography(H, a), applyHomography(H, b)]) : []),
    [H]
  );
  const net = H ? [applyHomography(H, NET_LINE[0]), applyHomography(H, NET_LINE[1])] : null;

  // WHAT THIS MOUNT COSTS IN LINE CALLS — the measured half of "mount it higher".
  // fitCamToQuad already solves the physical camera for the shape lock, and its
  // params carry the height (Cz), so the grade is free: no extra fitting, just
  // reading the number the lock already computed. Debounced because the fit is
  // a Nelder-Mead polish from 5 starts and the corners move on every drag frame.
  useEffect(() => {
    clearTimeout(mountTimer.current);
    mountTimer.current = setTimeout(() => {
      const fit = fitCamToQuad(DBL_ORDER.map((k) => pts[k]), frame.w, frame.h);
      if (!fit) {
        setMount(null);           // no real camera sees this shape - say nothing
        return;
      }
      const heightM = Math.abs(fit.params[2]);
      setMount({ heightM, fitPx: fit.fitPx, ...callVerdict(heightM) });
    }, 250);
    return () => clearTimeout(mountTimer.current);
  }, [pts, frame.w, frame.h]);

  // ANY change to a corner un-confirms every corner. A confirmation is a claim
  // about a specific placement, and carrying it across an edit is precisely how a
  // stale attestation ends up in a file (trap T26 is that failure one stage up).
  function invalidateConfirmation() {
    setConfirmed((c) => (Object.keys(c).length ? {} : c));
    setReviewing(false);
  }

  function nudge(dx, dy) {
    if (!selected) return;
    invalidateConfirmation();
    setPts((s) => ({
      ...s,
      [selected]: [
        clamp(s[selected][0] + dx, -PAD, frame.w + PAD),
        clamp(s[selected][1] + dy, -PAD, frame.h + PAD),
      ],
    }));
    // With the lock on, re-solve the rigid court shortly after the last nudge
    // (not per click - 1px fine-tuning would fight an instant re-solve).
    if (lockShape) {
      clearTimeout(nudgeTimer.current);
      nudgeTimer.current = setTimeout(resolveShape, 600);
    }
  }

  // Keyboard arrows (desktop): nudge the selected corner; Shift = x10.
  useEffect(() => {
    const onKey = (e) => {
      if (!selected) return;
      const k = e.key;
      const s = e.shiftKey ? 10 : 1;
      const map = { ArrowLeft: [-s, 0], ArrowRight: [s, 0], ArrowUp: [0, -s], ArrowDown: [0, s] };
      if (map[k]) {
        e.preventDefault();
        nudge(...map[k]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected, frame.w, frame.h]);

  function toImg(e) {
    const svg = svgRef.current;
    const p = svg.createSVGPoint();
    p.x = e.clientX;
    p.y = e.clientY;
    const l = p.matrixTransform(svg.getScreenCTM().inverse());
    return [l.x, l.y];
  }
  function onMove(e) {
    if (!drag) return;
    invalidateConfirmation();
    const [x, y] = toImg(e);
    setPts((s) => ({ ...s, [drag]: [clamp(x, -PAD, frame.w + PAD), clamp(y, -PAD, frame.h + PAD)] }));
  }
  function loadFrame(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setFrame({ src: url, w: img.naturalWidth, h: img.naturalHeight });
      setPts(defaultCorners(img.naturalWidth, img.naturalHeight));
      invalidateConfirmation();
    };
    img.src = url;
    e.target.value = "";
  }
  // Pull a frame straight from the analyzed video, so the court is adjusted on
  // the actual footage without exporting a screenshot first.
  function grabVideoFrame() {
    const v = document.createElement("video");
    v.muted = true;
    v.preload = "auto";
    v.src = "/analyzed.mp4";
    v.addEventListener("loadeddata", () => {
      v.currentTime = Math.min(2, (v.duration || 4) / 2);
    });
    v.addEventListener("seeked", () => {
      const c = document.createElement("canvas");
      c.width = v.videoWidth;
      c.height = v.videoHeight;
      c.getContext("2d").drawImage(v, 0, 0);
      setFrame({ src: c.toDataURL("image/jpeg", 0.92), w: v.videoWidth, h: v.videoHeight });
      setNote("Frame grabbed from the analyzed video.");
    });
    v.addEventListener("error", () => setNote("No analyzed video found — load a frame instead."));
  }
  const allConfirmed = CORNERS.every((c) => confirmed[c.key]);

  function download() {
    // With the lock on, export the LOCKED shape (a real camera's court). With it
    // off, export the exact points with the _exact marker - the analyzer then
    // skips its own snap + shape lock and treats your placement as final.
    //
    // NEVER SILENTLY MOVE A CONFIRMED POINT. When the shape lock would shift the
    // corners the user just confirmed, the confirmation is dropped and the file
    // says so, rather than shipping an attestation about points that are no
    // longer the ones the person looked at.
    const src = lockShape ? lockedPts(pts) : pts;
    const named = {};
    let movedPx = 0;
    for (const c of CORNERS) {
      named[c.key] = [Math.round(src[c.key][0]), Math.round(src[c.key][1])];
      movedPx = Math.max(
        movedPx,
        Math.hypot(src[c.key][0] - pts[c.key][0], src[c.key][1] - pts[c.key][1])
      );
    }
    if (!lockShape) named._exact = true;
    if (lockShape) setPts(src);

    const stillConfirmed = allConfirmed && movedPx <= 1.0;
    // PROVENANCE IS PART OF THE LABEL (trap T26). What is recorded here is what
    // actually happened - who confirmed what, on which frame, and how far the
    // solver then moved it - not an inference about it. `placed_by` stays the
    // honest "unattributed": a browser cannot tell a person's mouse from a
    // script's synthetic event, and only `confirmed_by_user`, which requires the
    // four named ticks in this UI, upgrades a calibration downstream.
    named._provenance = {
      placed_by: "unattributed",
      tool: "frontend Court Setup",
      shape_lock: lockShape,
      moved_px: Number(movedPx.toFixed(2)),
      confirmed_by_user: stillConfirmed,
      confirmed_corners: stillConfirmed ? CORNERS.map((c) => c.key) : [],
      confirmed_on_frame: frame.src.startsWith("data:") ? "video frame grab" : frame.src,
      frame_wh: [frame.w, frame.h],
      // FEATURE 1's answer, travelling with the calibration so `run.py analyze`
      // can carry it into match.json even for a clip whose far baseline is out
      // of frame entirely and therefore has no measurable clearance.
      far_baseline_visible: farBaseline,
      saved_at: new Date().toISOString(),
    };
    if (allConfirmed && !stillConfirmed) {
      setConfirmed({});
      setNote(
        `Shape lock moved a confirmed corner by ${movedPx.toFixed(0)}px, so the ` +
          "confirmation was dropped - check the corners again and re-confirm."
      );
    }
    const blob = new Blob([JSON.stringify(named, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "court_pts.json";
    a.click();
  }

  const vb = `${-PAD} ${-PAD} ${frame.w + 2 * PAD} ${frame.h + 2 * PAD}`;
  const sel = selected ? pts[selected] : null;
  // Loupe sits in the quadrant opposite the selected corner so it never hides it.
  const loupe = sel
    ? { cx: sel[0] < frame.w / 2 ? frame.w * 0.74 : frame.w * 0.26,
        cy: sel[1] < frame.h / 2 ? frame.h * 0.74 : frame.h * 0.26 }
    : null;
  const selLabel = CORNERS.find((c) => c.key === selected)?.label;

  const hint = mount ? framingHintFromHeight(mount.heightM) : null;
  const framingNotice =
    farBaseline === false ? noticeFor(FRAMING_OVERLAP) : null;

  return (
    <div className="setup">
      <div className="setup-help">
        <h3>Set up the court (do this once per camera position)</h3>
        <p>
          <strong>Drag</strong> the four court corners onto the real corners, then <strong>fine-tune</strong>{" "}
          the selected corner with the arrows below (or keyboard arrows). The magnifier shows exactly
          where it lands. Load your own frame to try it on your footage.
        </p>
      </div>

      {/* STEP 1 - the framing question. Asked before anything is measured,
          because that is the only moment a low camera can still be fixed, and
          because no honest automatic answer exists yet: the clearance criterion
          needs a homography that does not exist until the corners are placed. */}
      <div className="setup-step">
        <div className="setup-step-num">1</div>
        <div className="setup-step-body">
          <div className="setup-step-title">{FAR_BASELINE_QUESTION}</div>
          <p className="muted">
            Look at the far end of the court. If the far baseline is hidden behind
            the top of the net, speed, bounce positions and line calls on the far
            half will be unreliable — but you can still record and review the
            match either way.
          </p>
          <div className="setup-answers">
            {[
              { v: true, label: "Yes - I can see it below the net" },
              { v: false, label: "No - the net covers it" },
              { v: null, label: "Not sure" },
            ].map((o) => (
              <button
                key={String(o.v)}
                className={`chip ${farBaseline === o.v ? "chip-on" : ""}`}
                onClick={() => setFarBaseline(o.v)}
              >
                {o.label}
              </button>
            ))}
          </div>
          {framingNotice && (
            <div className="trust-banner trust-limited" style={{ marginTop: 12 }}>
              <div className="trust-head">
                <strong>{framingNotice.title}</strong>
              </div>
              <p className="trust-body">{framingNotice.body}</p>
              <div className="trust-actions">
                <span className="trust-continue">✓ {framingNotice.actions[0]}</span>
                <span className="muted">
                  Keep going — the corners below still get set, and the match is
                  still analyzed. It will simply be marked as having limited court
                  accuracy.
                </span>
              </div>
            </div>
          )}
          {hint?.text && (
            <p className="muted" style={{ marginTop: 10 }}>
              <strong>
                {hint.hint === FRAMING_UNKNOWN ? "Indication: " : "Indication: "}
              </strong>
              {hint.text}
            </p>
          )}
        </div>
      </div>

      <svg
        ref={svgRef}
        viewBox={vb}
        className="setup-svg"
        onPointerMove={onMove}
        onPointerUp={() => { if (drag) resolveShape(); setDrag(null); }}
        onPointerLeave={() => { if (drag) resolveShape(); setDrag(null); }}
      >
        <defs>
          <clipPath id="loupeClip">
            {loupe && <circle cx={loupe.cx} cy={loupe.cy} r={LOUPE_R} />}
          </clipPath>
        </defs>

        <rect x={-PAD} y={-PAD} width={frame.w + 2 * PAD} height={frame.h + 2 * PAD} className="setup-bg" />
        <image href={frame.src} x="0" y="0" width={frame.w} height={frame.h} />
        {/* The RAW frame must be inspectable. An overlay drawn over the paint is
            exactly what made trap T23 invisible for months: `yt_match40` stamped
            PASS at 0.9 px with all four clicks on asphalt, and no residual could
            have said so. Toggling the overlay off is how a person checks the
            clicks against the actual lines. */}
        {showOverlay && lines.map(([a, b], i) => (
          <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="setup-line" />
        ))}
        {showOverlay && net && (
          <line x1={net[0][0]} y1={net[0][1]} x2={net[1][0]} y2={net[1][1]} className="setup-net" />
        )}
        {CORNERS.map((c) => (
          <g key={c.key}>
            <circle
              cx={pts[c.key][0]}
              cy={pts[c.key][1]}
              r="15"
              className={`setup-handle ${drag === c.key ? "dragging" : ""} ${selected === c.key ? "selected" : ""} ${confirmed[c.key] ? "confirmed" : ""}`}
              onPointerDown={(e) => {
                setDrag(c.key);
                setSelected(c.key);
                try {
                  e.target.setPointerCapture(e.pointerId);
                } catch {
                  /* synthetic/edge pointers — drag still works via state */
                }
              }}
            />
            <text x={pts[c.key][0]} y={pts[c.key][1] - 22} className="setup-handle-label">
              {confirmed[c.key] ? "✓ " : ""}{c.plain}
            </text>
          </g>
        ))}

        {/* Magnifier loupe, centred on the selected corner */}
        {loupe && sel && (
          <g>
            <g clipPath="url(#loupeClip)">
              <rect x={loupe.cx - LOUPE_R} y={loupe.cy - LOUPE_R} width={LOUPE_R * 2} height={LOUPE_R * 2} className="setup-bg" />
              <image
                href={frame.src}
                x={loupe.cx - sel[0] * ZOOM}
                y={loupe.cy - sel[1] * ZOOM}
                width={frame.w * ZOOM}
                height={frame.h * ZOOM}
              />
            </g>
            <circle cx={loupe.cx} cy={loupe.cy} r={LOUPE_R} className="loupe-ring" />
            <line x1={loupe.cx - 18} y1={loupe.cy} x2={loupe.cx + 18} y2={loupe.cy} className="loupe-cross" />
            <line x1={loupe.cx} y1={loupe.cy - 18} x2={loupe.cx} y2={loupe.cy + 18} className="loupe-cross" />
          </g>
        )}
      </svg>

      <div className="setup-controls">
        <div className="nudge">
          <div className="nudge-title">
            Fine-tune: <strong>{selLabel}</strong>
            {sel && <span className="muted"> ({Math.round(sel[0])}, {Math.round(sel[1])})</span>}
          </div>
          <div className="nudge-pad">
            <button className="nudge-btn up" onClick={() => nudge(0, -step)} aria-label="up">▲</button>
            <button className="nudge-btn left" onClick={() => nudge(-step, 0)} aria-label="left">◀</button>
            <button className="nudge-btn step" onClick={() => setStep((s) => (s === 1 ? 10 : 1))}>
              {step}px
            </button>
            <button className="nudge-btn right" onClick={() => nudge(step, 0)} aria-label="right">▶</button>
            <button className="nudge-btn down" onClick={() => nudge(0, step)} aria-label="down">▼</button>
          </div>
          <div className="nudge-pick">
            {CORNERS.map((c) => (
              <button
                key={c.key}
                className={`chip ${selected === c.key ? "chip-on" : ""}`}
                onClick={() => setSelected(c.key)}
                title={c.where}
              >
                {c.plain}
              </button>
            ))}
          </div>
          {selected && (
            <p className="muted" style={{ marginTop: 8 }}>
              {CORNERS.find((c) => c.key === selected)?.where}
            </p>
          )}
        </div>

        <div className={`mount-grade mount-${mount?.level || "unknown"}`}>
          <div className="mount-title">This camera position</div>
          {mount ? (
            <>
              <div className="mount-figure">
                <strong>{mount.pct.toFixed(0)}%</strong>
                <span className="muted"> of close calls correct</span>
              </div>
              <div className="mount-detail">
                Camera ~{mount.heightM.toFixed(1)} m up. Always answering &ldquo;in&rdquo;
                scores {mount.floor.toFixed(0)}%, so this mount is worth{" "}
                <strong>{mount.gain > 0 ? `+${mount.gain.toFixed(0)}` : mount.gain.toFixed(0)} points</strong>{" "}
                over guessing.
              </div>
              {mount.level === "poor" && (
                <div className="mount-note">
                  At this height close calls carry no information — raise the camera
                  before you record. Clamping the phone to the fence (~2.5 m) instead of
                  a standing tripod takes this to ~68%.
                </div>
              )}
              {mount.level === "warn" && (
                <div className="mount-note">
                  Only just above the floor. Every metre higher is worth real accuracy:
                  ~69% at 3 m, ~80% at 6 m.
                </div>
              )}
            </>
          ) : (
            <div className="mount-detail muted">
              No real camera view fits these corners yet — place all four on the court
              corners to see what this mount is worth.
            </div>
          )}
          <div className="mount-src muted">
            Measured on simulated flights with a known bounce, on calls within 0.5 m of a
            line. Guidance, not a promise.
          </div>
        </div>

        {/* STEP 2 - confirm the four corners, one at a time, by their plain
            names. This is the ONLY thing that produces `confirmed_by_user`
            downstream, and it is what separates `user_confirmed` from
            `provisional` in every match this calibration goes on to produce. */}
        <div className="setup-confirm">
          <div className="setup-step-title">
            2. Check each corner on the frame, then tick it
          </div>
          <p className="muted">
            Turn the overlay off to see the real lines, zoom in with the
            magnifier, and make sure the handle sits on the actual corner of the
            paint — not near it, and not on a line behind the court.
          </p>
          <label className="setup-toggle">
            <input
              type="checkbox"
              checked={!showOverlay}
              onChange={(e) => setShowOverlay(!e.target.checked)}
            />
            Hide the overlay (show the raw camera frame)
          </label>
          <ul className="confirm-list">
            {CORNERS.map((c) => (
              <li key={c.key} className={confirmed[c.key] ? "confirmed" : ""}>
                <label>
                  <input
                    type="checkbox"
                    checked={Boolean(confirmed[c.key])}
                    onChange={(e) => {
                      setSelected(c.key);
                      setConfirmed((s0) => ({ ...s0, [c.key]: e.target.checked }));
                    }}
                  />
                  <span className="confirm-name">{c.plain}</span>
                  <span className="muted confirm-where">{c.where}</span>
                </label>
              </li>
            ))}
          </ul>
          <div className="confirm-state">
            {allConfirmed ? (
              <span className="confirm-ok">
                ✓ All four corners confirmed — saving will record this as a
                user-confirmed calibration.
              </span>
            ) : (
              <span className="muted">
                {CORNERS.filter((c) => confirmed[c.key]).length} of 4 confirmed.
                You can still save without confirming — the calibration is then
                recorded as <strong>provisional</strong>, and court measurements
                are not presented as verified.
              </span>
            )}
          </div>
          <button className="btn" onClick={() => setReviewing((v) => !v)}>
            {reviewing ? "Close review" : "Review before saving"}
          </button>
          {reviewing && (
            <div className="setup-review">
              <div className="setup-step-title">What will be saved</div>
              <ul className="trust-list">
                <li>
                  Frame: {frame.w}&times;{frame.h}
                  {frame.src.startsWith("data:") ? " (grabbed from the video)" : ` (${frame.src})`}
                </li>
                {CORNERS.map((c) => (
                  <li key={c.key}>
                    {confirmed[c.key] ? "✓" : "·"} {c.plain}: (
                    {Math.round(pts[c.key][0])}, {Math.round(pts[c.key][1])})
                  </li>
                ))}
                <li>
                  Far baseline visible below the net:{" "}
                  <strong>
                    {farBaseline === true ? "yes" : farBaseline === false ? "no" : "not answered"}
                  </strong>
                </li>
                <li>
                  Shape lock: <strong>{lockShape ? "on" : "off"}</strong>
                  {lockShape
                    ? " — corners may be moved onto the nearest real camera view. If that moves a confirmed corner, the confirmation is dropped."
                    : " — your points are saved exactly as placed."}
                </li>
                <li>
                  Calibration will be recorded as{" "}
                  <strong>{allConfirmed ? "user-confirmed" : "provisional"}</strong>.
                </li>
              </ul>
            </div>
          )}
        </div>

        <div className="setup-actions">
          <button className="btn" onClick={grabVideoFrame}>Use video frame</button>
          <button className="btn" onClick={() => fileRef.current?.click()}>Load frame</button>
          <input ref={fileRef} type="file" accept="image/*" onChange={loadFrame} hidden />
          <button
            className="btn btn-ghost"
            onClick={() => {
              setPts(defaultCorners(frame.w, frame.h));
              invalidateConfirmation();
            }}
          >
            Reset corners
          </button>
          <label
            className="muted"
            style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}
            title="ON: the court always stays a shape a real camera could see (corners re-solve together). OFF: place each corner exactly - use when a wide lens bends the real lines."
          >
            <input
              type="checkbox"
              checked={lockShape}
              onChange={(e) => {
                setLockShape(e.target.checked);
                if (e.target.checked) setPts((s) => lockedPts(s));
                else setNote("Shape lock OFF — corners stay exactly where you put them; save keeps your exact points.");
              }}
            />
            Shape lock
          </label>
          <button className="btn btn-primary" onClick={download}>
            {allConfirmed ? "Save confirmed calibration" : "Save as provisional"}
          </button>
          <span className="muted setup-note">
            {note || <>Saves <code>court_pts.json</code> → <code>run.py analyze --keypoints</code>.</>}
          </span>
        </div>
      </div>
    </div>
  );
}
