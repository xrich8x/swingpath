import { useMemo, useState } from "react";
import { fmtSpeed, fmtShotType, playerName } from "../lib/format.js";
import {
  X_LEFT_SINGLES,
  X_RIGHT_SINGLES,
  X_CENTER,
  SINGLES_WIDTH,
  SERVICE_LINE_FROM_NET,
} from "../lib/court.js";

function Tile({ label, value, sub }) {
  return (
    <div className="tile">
      <div className="tile-value">{value}</div>
      <div className="tile-label">{label}</div>
      {sub && <div className="tile-sub">{sub}</div>}
    </div>
  );
}

// Serve-placement band widths (metres) — mirror analytics.SERVE_*_BAND_M.
const T_BAND = 0.7;
const WIDE_BAND = 0.7;
const BOX_W = SINGLES_WIDTH / 2; // 4.115
const BODY_BAND = BOX_W - T_BAND - WIDE_BAND; // 2.715

// Sum a player's (or both players') serve-placement zones.
function zonesFor(placement, who) {
  const acc = {
    deuce: { T: 0, body: 0, wide: 0 },
    ad: { T: 0, body: 0, wide: 0 },
    total: 0,
  };
  const ids = who === "both" ? Object.keys(placement) : [who];
  for (const pid of ids) {
    const p = placement[pid];
    if (!p) continue;
    for (const side of ["deuce", "ad"]) {
      for (const band of ["T", "body", "wide"]) {
        acc[side][band] += p[side]?.[band] || 0;
      }
    }
    acc.total += p.total || 0;
  }
  return acc;
}

// A 6-zone serve-placement diagram: the returner's two service boxes (deuce | ad),
// each split into wide / body / T bands. Built as columns left->right in metres so
// widths match the real court. Filled by count intensity.
function ServeCourt({ zones }) {
  const scale = 36;
  const pad = 26;
  const depth = SERVICE_LINE_FROM_NET; // 6.40 m box depth
  const w = SINGLES_WIDTH * scale + 2 * pad;
  const h = depth * scale + 2 * pad;

  // Columns: deuce [wide, body, T] then ad [T, body, wide]. The centre service
  // line sits where the two T bands meet.
  const cols = [
    { side: "deuce", band: "wide", width: WIDE_BAND },
    { side: "deuce", band: "body", width: BODY_BAND },
    { side: "deuce", band: "T", width: T_BAND },
    { side: "ad", band: "T", width: T_BAND },
    { side: "ad", band: "body", width: BODY_BAND },
    { side: "ad", band: "wide", width: WIDE_BAND },
  ];
  const max = Math.max(
    1,
    ...cols.map((c) => zones[c.side][c.band])
  );

  let cursor = 0;
  const rects = cols.map((c, i) => {
    const x0 = cursor;
    cursor += c.width;
    const count = zones[c.side][c.band];
    const alpha = count === 0 ? 0 : 0.15 + 0.6 * (count / max);
    return {
      key: i,
      x: pad + x0 * scale,
      y: pad,
      w: c.width * scale,
      h: depth * scale,
      count,
      alpha,
      cx: pad + (x0 + c.width / 2) * scale,
      label: c.band === "body" ? "Body" : c.band === "T" ? "T" : "Wide",
    };
  });

  return (
    <svg
      className="serve-court"
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label="Serve placement: deuce and ad service boxes split into T, body and wide bands"
    >
      {/* Box surface */}
      <rect x={pad} y={pad} width={SINGLES_WIDTH * scale} height={depth * scale}
            rx="3" className="court-surface" />
      {/* Zone fills */}
      {rects.map((r) => (
        <g key={r.key}>
          <rect x={r.x} y={r.y} width={r.w} height={r.h}
                fill="var(--accent)" opacity={r.alpha} />
          <text x={r.cx} y={pad + depth * scale * 0.42} className="serve-zone-count"
                textAnchor="middle">{r.count}</text>
          <text x={r.cx} y={pad + depth * scale * 0.62} className="serve-zone-label"
                textAnchor="middle">{r.label}</text>
        </g>
      ))}
      {/* Zone dividers */}
      {rects.slice(1).map((r) => (
        <line key={`d${r.key}`} x1={r.x} y1={pad} x2={r.x} y2={pad + depth * scale}
              className="serve-zone-div" />
      ))}
      {/* Centre service line (drawn bolder) */}
      <line x1={pad + BOX_W * scale} y1={pad} x2={pad + BOX_W * scale}
            y2={pad + depth * scale} className="serve-center-line" />
      {/* Outer box outline */}
      <rect x={pad} y={pad} width={SINGLES_WIDTH * scale} height={depth * scale}
            className="serve-court-outline" fill="none" />
      {/* Court-side labels */}
      <text x={pad + BOX_W * 0.5 * scale} y={pad - 8} className="serve-side-label"
            textAnchor="middle">Deuce court</text>
      <text x={pad + BOX_W * 1.5 * scale} y={pad - 8} className="serve-side-label"
            textAnchor="middle">Ad court</text>
      <text x={w / 2} y={h - 8} className="serve-side-label" textAnchor="middle">
        Net
      </text>
    </svg>
  );
}

function ServePlacementPanel({ placement, match }) {
  const servers = Object.keys(placement).filter((pid) => (placement[pid]?.total || 0) > 0);
  const [who, setWho] = useState("both");
  const zones = useMemo(() => zonesFor(placement, who), [placement, who]);
  const total = zones.total;

  // Standard-band share (for a quick sanity read vs the pro reference ~25-30% T).
  const bandTotal = (band) => zones.deuce[band] + zones.ad[band];
  const pct = (n) => (total ? Math.round((n / total) * 100) : 0);

  return (
    <section className="panel panel-wide">
      <div className="panel-head">
        <h3>Serve placement</h3>
        {servers.length > 1 && (
          <div className="seg-group" role="group" aria-label="Server">
            <button className={`seg ${who === "both" ? "seg-active" : ""}`}
                    onClick={() => setWho("both")}>Both</button>
            {servers.map((pid) => (
              <button key={pid} className={`seg ${who === pid ? "seg-active" : ""}`}
                      onClick={() => setWho(pid)}>{playerName(match, pid)}</button>
            ))}
          </div>
        )}
      </div>

      {total === 0 ? (
        <p className="muted">
          No confidently-placed serves in this match. Serve placement needs a
          bounce inside the service box with a trusted line call — sparse on
          real single-camera clips, rich on the synthetic demo.
        </p>
      ) : (
        <div className="serve-placement">
          <ServeCourt zones={zones} />
          <div className="serve-placement-side">
            <div className="serve-band-summary">
              <div><span className="swatch swatch-t" /> T — {bandTotal("T")} ({pct(bandTotal("T"))}%)</div>
              <div><span className="swatch swatch-body" /> Body — {bandTotal("body")} ({pct(bandTotal("body"))}%)</div>
              <div><span className="swatch swatch-wide" /> Wide — {bandTotal("wide")} ({pct(bandTotal("wide"))}%)</div>
            </div>
            <p className="muted">
              {total} placed serve{total === 1 ? "" : "s"}. Bands are ~0.7 m targets
              (one racquet-length) along the centre line (T) and singles sideline
              (wide); body is the ~2.7 m between. Pro reference: ~25–30% T, ~25% wide.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function pctStr(n, d) {
  return d ? `${Math.round((n / d) * 100)}%` : "—";
}

function ServeSplitPanel({ split, match }) {
  const players = Object.keys(split);
  if (players.length === 0) return null;
  return (
    <section className="panel">
      <h3>1st / 2nd serve</h3>
      <div className="serve-split">
        {players.map((pid) => {
          const sp = split[pid];
          const firstPct = pctStr(sp.first_in, sp.first_total);
          const secondPct = pctStr(sp.second_in, sp.second_total);
          return (
            <div className="serve-split-row" key={pid}>
              <div className="serve-split-name">{playerName(match, pid)}</div>
              <div className="serve-split-cols">
                <div className="serve-split-cell">
                  <div className="serve-split-pct">{firstPct}</div>
                  <div className="serve-split-cap">1st in ({sp.first_in}/{sp.first_total})</div>
                </div>
                <div className="serve-split-cell">
                  <div className="serve-split-pct">{secondPct}</div>
                  <div className="serve-split-cap">2nd in ({sp.second_in}/{sp.second_total})</div>
                </div>
              </div>
              {sp.unknown > 0 && (
                <div className="serve-split-unknown">
                  {sp.unknown} serve{sp.unknown === 1 ? "" : "s"} unknown (point state
                  unclear)
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="muted">
        1st vs 2nd is read from the fault sequence — a serve after the same
        player's fault is a second serve. Ambiguous points are counted honestly
        as unknown, not guessed.
      </p>
    </section>
  );
}

function RallyLengthPanel({ buckets }) {
  const order = ["1-3", "4-6", "7-9", "10+"];
  const entries = order.filter((k) => k in (buckets || {})).map((k) => [k, buckets[k]]);
  const max = Math.max(1, ...entries.map(([, c]) => c));
  const total = entries.reduce((n, [, c]) => n + c, 0);
  return (
    <section className="panel">
      <h3>Rally length</h3>
      <div className="bars">
        {entries.map(([bucket, count]) => {
          const pct = Math.round((count / max) * 100);
          return (
            <div className="bar-row" key={bucket}>
              <div className="bar-label">{bucket} shots</div>
              <div className="bar-track">
                <div className="bar-fill bar-forehand" style={{ width: `${pct}%` }} />
              </div>
              <div className="bar-value">
                {count}
                <span className="muted"> ({total ? Math.round((count / total) * 100) : 0}%)</span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="muted">Rallies by shots played (Tennis Abstract buckets).</p>
    </section>
  );
}

export default function Statistics({ match }) {
  const s = match.stats;
  const mixEntries = Object.entries(s.shot_mix).sort((a, b) => b[1] - a[1]);
  const mixTotal = mixEntries.reduce((n, [, c]) => n + c, 0) || 1;
  const callTotal = s.line_calls.in + s.line_calls.out || 1;
  const inPct = Math.round((s.line_calls.in / callTotal) * 100);

  // Player movement (court-plane distance run). A value is null when the player
  // was not located on enough frames to integrate a path — see
  // pipeline.MIN_TRACK_COVERAGE. Only real numbers scale the bars, so an
  // untracked player cannot silently define the maximum.
  const dist = s.distance_run_m || {};
  // Why a value is missing. Do NOT assume "too few frames": in doubles the
  // track is dense but holds two people, so the backend supplies the reason.
  const distNote = s.distance_run_note || {};
  const distMax = Math.max(
    ...["A", "B"].map((p) => (typeof dist[p] === "number" ? dist[p] : 0)), 1);
  const missingReasons = ["A", "B"]
    .filter((p) => typeof dist[p] !== "number" && distNote[p])
    .map((p) => `${playerName(match, p)}: ${distNote[p]}`);

  // Physics-based spin (ball_physics): populated when bounce-anchored fits succeed.
  const spins = (match.shots || []).filter((sh) => sh.spin_rpm > 0).map((sh) => sh.spin_rpm);
  const avgSpin = spins.length ? Math.round(spins.reduce((a, b) => a + b, 0) / spins.length) : null;
  const physicsShots = (match.shots || []).filter((sh) => sh.speed_source === "physics").length;

  // Headline speeds count only confidently-projected shots (far-court bounces are
  // perspective-amplified noise); surface how many shots backed the number.
  // When nothing met the strict bar the backend falls back to estimates and sets
  // speed_estimated, rather than reporting 0.0 — which read as a broken pipeline
  // and was the normal case on an amateur-height camera. Label it honestly: the
  // number is real, its uncertainty is measured (vs the SwingVision HUD), and it
  // must never be presented as a measurement.
  const shots = match.shots || [];
  const confidentSpeeds = shots.filter((sh) => sh.speed_confident !== false && sh.speed_kmh > 0).length;
  const estimated = s.speed_estimated === true;
  const errPct = s.speed_err_pct || 0;
  const speedSub = estimated
    ? `estimate — typically ±${Math.round(errPct)}%`
    : confidentSpeeds > 0
      ? `${confidentSpeeds} confidently-tracked shot${confidentSpeeds === 1 ? "" : "s"}`
      : "low confidence — far court";
  const speedPrefix = estimated ? "~" : "";

  // Serve/rally analytics are additive — older match.json simply lack them.
  const servePlacement = s.serve_placement || {};
  const serveSplit = s.serve_split || {};
  const rallyBuckets = s.rally_length_buckets || {};
  const hasServeData = Object.keys(servePlacement).length > 0;
  const hasRallyBuckets = Object.keys(rallyBuckets).length > 0;

  return (
    <div className="stats">
      <div className="tiles">
        <Tile label="Shots" value={s.shot_count} />
        <Tile label="Rallies" value={s.rally_count} />
        <Tile
          label="Avg speed"
          value={s.avg_speed_kmh > 0 ? `${speedPrefix}${fmtSpeed(s.avg_speed_kmh)}` : fmtSpeed(s.avg_speed_kmh)}
          sub={speedSub}
        />
        <Tile
          label="Top speed"
          value={s.top_speed_kmh > 0 ? `${speedPrefix}${fmtSpeed(s.top_speed_kmh)}` : fmtSpeed(s.top_speed_kmh)}
          sub={speedSub}
        />
        <Tile
          label="Avg spin"
          value={avgSpin != null ? `${avgSpin} rpm` : "—"}
          sub={physicsShots ? `${physicsShots} physics shots` : "needs good calibration"}
        />
      </div>

      <div className="stats-grid">
        {hasServeData && <ServePlacementPanel placement={servePlacement} match={match} />}
        {hasServeData && <ServeSplitPanel split={serveSplit} match={match} />}
        {hasRallyBuckets && <RallyLengthPanel buckets={rallyBuckets} />}

        <section className="panel">
          <h3>Shot mix</h3>
          <div className="bars">
            {mixEntries.map(([type, count]) => {
              const pct = Math.round((count / mixTotal) * 100);
              return (
                <div className="bar-row" key={type}>
                  <div className="bar-label">{fmtShotType(type)}</div>
                  <div className="bar-track">
                    <div className={`bar-fill bar-${type}`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="bar-value">
                    {count} <span className="muted">({pct}%)</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="panel">
          <h3>Line calls</h3>
          <div className="callsplit">
            <div className="callsplit-bar">
              <div className="callsplit-in" style={{ width: `${inPct}%` }} />
              <div className="callsplit-out" style={{ width: `${100 - inPct}%` }} />
            </div>
            <div className="callsplit-legend">
              <div>
                <span className="dot dot-in" /> In — {s.line_calls.in} ({inPct}%)
              </div>
              <div>
                <span className="dot dot-out" /> Out — {s.line_calls.out} ({100 - inPct}%)
              </div>
              {(s.line_calls.uncertain || 0) > 0 && (
                <div title="Bounce landed in the far court, too perspective-amplified for a single camera to judge — excluded from in/out.">
                  <span className="dot dot-uncertain" /> Uncertain — {s.line_calls.uncertain}
                </div>
              )}
            </div>
            <p className="muted">
              Speeds are average ball speed and read ~15–20% under a radar gun — expected,
              not a bug.
            </p>
          </div>
        </section>

        <section className="panel">
          <h3>Player movement</h3>
          <div className="bars">
            {["A", "B"].map((pid) => {
              // null/undefined means the player was never tracked densely enough
              // to integrate a path — NOT that they stood still. Rendering that
              // as a 0 m bar told the user the opposite of the truth, and it was
              // the normal case for the far player (tracked on 1-11% of frames).
              const m = dist[pid];
              const tracked = typeof m === "number";
              const pct = tracked ? Math.round((m / distMax) * 100) : 0;
              return (
                <div className="bar-row" key={pid}>
                  <div className="bar-label">{playerName(match, pid)}</div>
                  <div className="bar-track">
                    {tracked && (
                      <div className={`bar-fill bar-${pid === "A" ? "forehand" : "backhand"}`}
                           style={{ width: `${pct}%` }} />
                    )}
                  </div>
                  <div className="bar-value">
                    {tracked ? `${m} m` : <span className="muted">not tracked</span>}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="muted">
            Court-plane distance run. “Not tracked” means we could not measure a path
            for that player — it does <strong>not</strong> mean they did not move.
            {missingReasons.length > 0 && ` ${missingReasons.join("; ")}.`}
          </p>
        </section>
      </div>
    </div>
  );
}
