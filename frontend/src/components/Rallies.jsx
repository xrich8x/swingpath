import { fmtDuration, fmtSpeed, playerName } from "../lib/format.js";

export default function Rallies({ match, selectedRallyId, onSelectRally }) {
  const shotById = new Map(match.shots.map((s) => [s.id, s]));
  const scoreByRally = new Map(match.score.timeline.map((e) => [e.rally_id, e]));

  return (
    <div className="rallies">
      <p className="muted rallies-help">
        Click a rally to focus it on the Court tab; click again to deselect.
      </p>
      <div className="rally-table">
        <div className="rally-table-head">
          <div>#</div>
          <div>Winner</div>
          <div>Shots</div>
          <div>Duration</div>
          <div>Top speed</div>
          <div>Score after</div>
        </div>
        {match.rallies.map((r) => {
          const shots = r.shot_ids.map((id) => shotById.get(id)).filter(Boolean);
          // Prefer confidently-projected speeds; fall back to all if none qualify.
          const confident = shots.filter((s) => s.speed_confident !== false);
          const speedPool = confident.length ? confident : shots;
          const topSpeed = speedPool.reduce((m, s) => Math.max(m, s.speed_kmh), 0);
          const ev = scoreByRally.get(r.id);
          const active = selectedRallyId === r.id;
          return (
            <button
              key={r.id}
              className={`rally-row ${active ? "rally-row-active" : ""}`}
              onClick={() => onSelectRally(r.id)}
            >
              <div>{r.id + 1}</div>
              <div>
                <span className={`pill pill-${r.winner.toLowerCase()}`}>
                  {playerName(match, r.winner)}
                </span>
              </div>
              <div>{r.shot_ids.length}</div>
              <div>{fmtDuration(r.end_s - r.start_s)}</div>
              <div>{fmtSpeed(topSpeed)}</div>
              <div className="rally-score">
                {ev ? `${ev.display} · ${ev.games_display}` : "—"}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
