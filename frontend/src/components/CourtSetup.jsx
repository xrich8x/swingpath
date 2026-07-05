import { useEffect, useMemo, useRef, useState } from "react";
import { LINES, NET_LINE, LENGTH, DOUBLES_WIDTH } from "../lib/court.js";
import { computeHomography, applyHomography } from "../lib/homography.js";

// SwingVision-style court setup: a fixed camera is calibrated ONCE by dragging
// the four court corners onto the real corners. Coarse placement is by drag;
// fine placement (esp. on a phone) is by the on-screen nudge pad / arrow keys,
// with a magnifier loupe so you can see exactly where the corner lands.

const PAD = 90; // draggable margin around the frame so edge corners are reachable
const ZOOM = 3.5;
const LOUPE_R = 120;

const CORNERS = [
  { key: "far_bl_doubles", court: [0, LENGTH], label: "far-left", at: [0.34, 0.35] },
  { key: "far_br_doubles", court: [DOUBLES_WIDTH, LENGTH], label: "far-right", at: [0.66, 0.35] },
  { key: "near_bl_doubles", court: [0, 0], label: "near-left", at: [0.16, 0.86] },
  { key: "near_br_doubles", court: [DOUBLES_WIDTH, 0], label: "near-right", at: [0.84, 0.86] },
];
const defaultCorners = (w, h) =>
  Object.fromEntries(CORNERS.map((c) => [c.key, [w * c.at[0], h * c.at[1]]]));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

export default function CourtSetup() {
  const svgRef = useRef(null);
  const fileRef = useRef(null);
  const [frame, setFrame] = useState({ src: "/court_setup_frame.jpg", w: 1280, h: 720 });
  const [pts, setPts] = useState(() => defaultCorners(1280, 720));
  const [drag, setDrag] = useState(null);
  const [selected, setSelected] = useState("near_br_doubles");
  const [step, setStep] = useState(1);

  // Seed the corners from /court_setup_seed.json when the backend published a
  // best-guess calibration for the default frame — the user then only fine-tunes.
  useEffect(() => {
    fetch("/court_setup_seed.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((seed) => {
        if (seed && CORNERS.every((c) => Array.isArray(seed[c.key]))) {
          setPts(Object.fromEntries(CORNERS.map((c) => [c.key, [...seed[c.key]]])));
        }
      })
      .catch(() => {});
  }, []);

  const H = useMemo(
    () => computeHomography(CORNERS.map((c) => c.court), CORNERS.map((c) => pts[c.key])),
    [pts]
  );
  const lines = useMemo(
    () => (H ? LINES.map(([a, b]) => [applyHomography(H, a), applyHomography(H, b)]) : []),
    [H]
  );
  const net = H ? [applyHomography(H, NET_LINE[0]), applyHomography(H, NET_LINE[1])] : null;

  function nudge(dx, dy) {
    if (!selected) return;
    setPts((s) => ({
      ...s,
      [selected]: [
        clamp(s[selected][0] + dx, -PAD, frame.w + PAD),
        clamp(s[selected][1] + dy, -PAD, frame.h + PAD),
      ],
    }));
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
    };
    img.src = url;
    e.target.value = "";
  }
  function download() {
    const named = {};
    for (const c of CORNERS) named[c.key] = [Math.round(pts[c.key][0]), Math.round(pts[c.key][1])];
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

      <svg
        ref={svgRef}
        viewBox={vb}
        className="setup-svg"
        onPointerMove={onMove}
        onPointerUp={() => setDrag(null)}
        onPointerLeave={() => setDrag(null)}
      >
        <defs>
          <clipPath id="loupeClip">
            {loupe && <circle cx={loupe.cx} cy={loupe.cy} r={LOUPE_R} />}
          </clipPath>
        </defs>

        <rect x={-PAD} y={-PAD} width={frame.w + 2 * PAD} height={frame.h + 2 * PAD} className="setup-bg" />
        <image href={frame.src} x="0" y="0" width={frame.w} height={frame.h} />
        {lines.map(([a, b], i) => (
          <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} className="setup-line" />
        ))}
        {net && (
          <line x1={net[0][0]} y1={net[0][1]} x2={net[1][0]} y2={net[1][1]} className="setup-net" />
        )}
        {CORNERS.map((c) => (
          <g key={c.key}>
            <circle
              cx={pts[c.key][0]}
              cy={pts[c.key][1]}
              r="15"
              className={`setup-handle ${drag === c.key ? "dragging" : ""} ${selected === c.key ? "selected" : ""}`}
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
              {c.label}
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
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <div className="setup-actions">
          <button className="btn" onClick={() => fileRef.current?.click()}>Load frame</button>
          <input ref={fileRef} type="file" accept="image/*" onChange={loadFrame} hidden />
          <button className="btn btn-ghost" onClick={() => setPts(defaultCorners(frame.w, frame.h))}>
            Reset corners
          </button>
          <button className="btn btn-primary" onClick={download}>Confirm &amp; save</button>
          <span className="muted setup-note">
            Saves <code>court_pts.json</code> → <code>run.py analyze --keypoints</code>.
          </span>
        </div>
      </div>
    </div>
  );
}
