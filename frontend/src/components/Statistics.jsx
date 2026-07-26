import { fmtSpeed, fmtShotType, playerName } from "../lib/format.js";

function Tile({ label, value, sub }) {
  return (
    <div className="tile">
      <div className="tile-value">{value}</div>
      <div className="tile-label">{label}</div>
      {sub && <div className="tile-sub">{sub}</div>}
    </div>
  );
}

export default function Statistics({ match }) {
  const s = match.stats;
  const mixEntries = Object.entries(s.shot_mix).sort((a, b) => b[1] - a[1]);
  const mixTotal = mixEntries.reduce((n, [, c]) => n + c, 0) || 1;
  const callTotal = s.line_calls.in + s.line_calls.out || 1;
  const inPct = Math.round((s.line_calls.in / callTotal) * 100);

  // Player movement (court-plane distance run). Far player is approximate.
  const dist = s.distance_run_m || {};
  const distMax = Math.max(dist.A || 0, dist.B || 0, 1);

  // Physics-based spin (ball_physics): populated when bounce-anchored fits succeed.
  const spins = (match.shots || []).filter((sh) => sh.spin_rpm > 0).map((sh) => sh.spin_rpm);
  const avgSpin = spins.length ? Math.round(spins.reduce((a, b) => a + b, 0) / spins.length) : null;
  const physicsShots = (match.shots || []).filter((sh) => sh.speed_source === "physics").length;

  // Headline speeds count only confidently-projected shots (far-court bounces are
  // perspective-amplified noise); surface how many shots backed the number.
  const shots = match.shots || [];
  const confidentSpeeds = shots.filter((sh) => sh.speed_confident !== false && sh.speed_kmh > 0).length;
  const speedSub =
    confidentSpeeds > 0
      ? `${confidentSpeeds} confidently-tracked shot${confidentSpeeds === 1 ? "" : "s"}`
      : "low confidence — far court";

  return (
    <div className="stats">
      <div className="tiles">
        <Tile label="Shots" value={s.shot_count} />
        <Tile label="Rallies" value={s.rally_count} />
        <Tile label="Avg speed" value={fmtSpeed(s.avg_speed_kmh)} sub={speedSub} />
        <Tile label="Top speed" value={fmtSpeed(s.top_speed_kmh)} sub={speedSub} />
        <Tile
          label="Avg spin"
          value={avgSpin != null ? `${avgSpin} rpm` : "—"}
          sub={physicsShots ? `${physicsShots} physics shots` : "needs good calibration"}
        />
      </div>

      <div className="stats-grid">
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
              const m = dist[pid] || 0;
              const pct = Math.round((m / distMax) * 100);
              return (
                <div className="bar-row" key={pid}>
                  <div className="bar-label">{playerName(match, pid)}</div>
                  <div className="bar-track">
                    <div className={`bar-fill bar-${pid === "A" ? "forehand" : "backhand"}`}
                         style={{ width: `${pct}%` }} />
                  </div>
                  <div className="bar-value">{m} m</div>
                </div>
              );
            })}
          </div>
          <p className="muted">Court-plane distance run · far player approximate (single camera).</p>
        </section>
      </div>
    </div>
  );
}
