import { useEffect, useMemo, useRef, useState } from "react";
import {
  LINES,
  NET_LINE,
  DOUBLES_WIDTH,
  LENGTH,
  makeCourtLayout,
} from "../lib/court.js";
import { fmtSpeedConf, fmtStroke, playerName } from "../lib/format.js";
import { heatCells, heatColor } from "../lib/heatmap.js";

const L = makeCourtLayout(20, 30);

export default function Court({ match, selectedRally, onSelectRally }) {
  // Scrub state for the selected rally's ball track.
  const track = selectedRally?.ball_track ?? [];
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showHeat, setShowHeat] = useState(false);
  const raf = useRef(null);

  // Reset scrubber whenever the selected rally changes.
  useEffect(() => {
    setFrame(0);
    setPlaying(Boolean(selectedRally));
  }, [selectedRally]);

  // Animation loop: advance ~1 track sample per 60ms while playing.
  useEffect(() => {
    if (!playing || track.length === 0) return;
    let last = performance.now();
    const tick = (now) => {
      if (now - last >= 60) {
        last = now;
        setFrame((f) => {
          if (f + 1 >= track.length) {
            setPlaying(false);
            return f;
          }
          return f + 1;
        });
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, track.length]);

  // Shots to mark: the selected rally's, or all shots when nothing selected.
  const landings = useMemo(() => {
    if (selectedRally) {
      const ids = new Set(selectedRally.shot_ids);
      return match.shots.filter((s) => ids.has(s.id));
    }
    return match.shots;
  }, [match, selectedRally]);

  // Shot-placement density: Gaussian-splat every landing into a court grid.
  const heat = useMemo(
    () => (showHeat ? heatCells(landings.map((s) => s.bounce_xy)) : []),
    [showHeat, landings]
  );

  const trailPath = useMemo(() => {
    if (track.length === 0) return "";
    return track
      .slice(0, frame + 1)
      .map((p, i) => `${i === 0 ? "M" : "L"} ${L.sx(p.xy[0]).toFixed(1)} ${L.sy(p.xy[1]).toFixed(1)}`)
      .join(" ");
  }, [track, frame]);

  const ball = track[frame];

  return (
    <div className="court-layout">
      <div className="court-stage">
        <svg
          className="court-svg"
          viewBox={`0 0 ${L.width} ${L.height}`}
          role="img"
          aria-label="Top-down tennis court with shot landings"
        >
          {/* Playing surface */}
          <rect
            x={L.sx(0)}
            y={L.sy(LENGTH)}
            width={DOUBLES_WIDTH * L.scale}
            height={LENGTH * L.scale}
            rx="4"
            className="court-surface"
          />

          {/* Shot-placement heatmap (under the lines so they stay readable) */}
          {heat.map((cell, i) => (
            <rect
              key={`h${i}`}
              x={L.sx(cell.x0)}
              y={L.sy(cell.y0 + cell.h)}
              width={cell.w * L.scale + 0.6}
              height={cell.h * L.scale + 0.6}
              fill={heatColor(cell.intensity)}
              opacity={0.18 + cell.intensity * 0.62}
            />
          ))}

          {/* Court lines */}
          {LINES.map(([a, b], i) => (
            <line
              key={i}
              x1={L.sx(a[0])}
              y1={L.sy(a[1])}
              x2={L.sx(b[0])}
              y2={L.sy(b[1])}
              className="court-line"
            />
          ))}
          <line
            x1={L.sx(NET_LINE[0][0])}
            y1={L.sy(NET_LINE[0][1])}
            x2={L.sx(NET_LINE[1][0])}
            y2={L.sy(NET_LINE[1][1])}
            className="court-net"
          />

          {/* Player end labels */}
          <text x={L.sx(DOUBLES_WIDTH / 2)} y={L.height - 6} className="court-end-label">
            {playerName(match, "A")}
          </text>
          <text x={L.sx(DOUBLES_WIDTH / 2)} y={14} className="court-end-label">
            {playerName(match, "B")}
          </text>

          {/* Rally ball trail */}
          {selectedRally && trailPath && (
            <path d={trailPath} className="ball-trail" fill="none" />
          )}

          {/* Shot landing dots. Far-court bounces the single camera can't pin down
              (call_confident === false) are drawn hollow/dashed — shown, not trusted. */}
          {landings.map((s) => {
            const uncertain = s.call_confident === false;
            return (
              <circle
                key={s.id}
                cx={L.sx(s.bounce_xy[0])}
                cy={L.sy(s.bounce_xy[1])}
                r={selectedRally ? 4.5 : 3}
                className={`landing ${s.call === "in" ? "landing-in" : "landing-out"}${
                  uncertain ? " landing-uncertain" : ""
                }`}
              >
                <title>
                  {`${fmtStroke(s)} · ${fmtSpeedConf(s.speed_kmh, s.speed_confident)} · ${
                    s.call.toUpperCase()
                  }${uncertain ? " (uncertain — far court)" : ""}`}
                </title>
              </circle>
            );
          })}

          {/* Animated ball */}
          {selectedRally && ball && (
            <circle cx={L.sx(ball.xy[0])} cy={L.sy(ball.xy[1])} r="5" className="ball" />
          )}
        </svg>
      </div>

      <aside className="court-side">
        <div className="court-toggle" role="group" aria-label="Court overlay">
          <button
            className={`seg ${!showHeat ? "seg-active" : ""}`}
            onClick={() => setShowHeat(false)}
          >
            Landings
          </button>
          <button
            className={`seg ${showHeat ? "seg-active" : ""}`}
            onClick={() => setShowHeat(true)}
          >
            Heatmap
          </button>
        </div>
        {!selectedRally ? (
          <div className="court-help">
            <h3>All shot landings</h3>
            <p>
              Every bounce in the match. <span className="dot dot-in" /> in,&nbsp;
              <span className="dot dot-out" /> out.
            </p>
            <p className="muted">
              Pick a rally below to trail the ball through a single point.
            </p>
            <div className="legend">
              <div>
                <span className="dot dot-in" /> {match.stats.line_calls.in} in
              </div>
              <div>
                <span className="dot dot-out" /> {match.stats.line_calls.out} out
              </div>
            </div>
          </div>
        ) : (
          <div className="court-scrubber">
            <div className="scrubber-head">
              <h3>Rally {selectedRally.id + 1}</h3>
              <button className="btn btn-ghost" onClick={() => onSelectRally(selectedRally.id)}>
                Deselect
              </button>
            </div>
            <p className="muted">
              Won by {playerName(match, selectedRally.winner)} ·{" "}
              {selectedRally.shot_ids.length} shots
            </p>

            <div className="scrubber-controls">
              <button className="btn" onClick={() => setPlaying((p) => !p)}>
                {playing ? "❚❚ Pause" : "▶ Play"}
              </button>
              <input
                type="range"
                min={0}
                max={Math.max(0, track.length - 1)}
                value={frame}
                onChange={(e) => {
                  setPlaying(false);
                  setFrame(Number(e.target.value));
                }}
              />
            </div>
            <div className="scrubber-readout">
              t = {ball ? ball.t_s.toFixed(1) : "0.0"} s · frame {frame + 1}/{track.length}
            </div>
          </div>
        )}

        <div className="rally-rail">
          {match.rallies.map((r) => (
            <button
              key={r.id}
              className={`rally-chip ${selectedRally?.id === r.id ? "rally-chip-active" : ""}`}
              onClick={() => onSelectRally(r.id)}
              title={`Rally ${r.id + 1} — won by ${playerName(match, r.winner)}`}
            >
              {r.id + 1}
            </button>
          ))}
        </div>
      </aside>
    </div>
  );
}
