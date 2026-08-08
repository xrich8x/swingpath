import { useState } from "react";
import { fmtDuration, fmtSpeed, playerName } from "../lib/format.js";

/**
 * Rallies — the table, plus per-rally playback when clips exist.
 *
 * `clips` is the highlights.json manifest written by `run.py highlights`, served
 * from /rallies/ the same way the annotated video is served from /analyzed.mp4.
 * It is optional by design: without it this is exactly the table it always was,
 * because the clips are generated artifacts and a match.json can outlive them.
 */
export default function Rallies({ match, selectedRallyId, onSelectRally, clips }) {
  const [playing, setPlaying] = useState(null);
  const shotById = new Map(match.shots.map((s) => [s.id, s]));
  const scoreByRally = new Map(match.score.timeline.map((e) => [e.rally_id, e]));

  // The manifest is served from one fixed path, so it must be matched to the
  // loaded match before it is trusted: rally ids are per-match, and showing
  // another video's clips against these rows would play the wrong point
  // entirely. Only clips that were actually cut are playable — a rally can be
  // skipped (no shots) or fail, and the manifest records both.
  const forThisMatch = clips?.video === match.video?.filename;
  const clipByRally = new Map(
    forThisMatch
      ? (clips?.clips ?? []).filter((c) => c.ok).map((c) => [c.rally_id, c])
      : []
  );
  const top = (forThisMatch ? clips?.top ?? [] : [])
    .map((id) => clipByRally.get(id))
    .filter(Boolean);
  const playingClip = playing == null ? null : clipByRally.get(playing);

  return (
    <div className="rallies">
      <p className="muted rallies-help">
        Click a rally to focus it on the Court tab; click again to deselect.
        {clipByRally.size > 0 && " Hit Play to watch just that point."}
      </p>

      {playingClip && (
        <div className="rally-player">
          <div className="broadcast-frame">
            <video
              className="broadcast-video"
              src={`/rallies/${playingClip.file}`}
              controls
              autoPlay
              playsInline
              key={playingClip.file}
            />
          </div>
          <div className="rally-player-bar">
            <span>
              <strong>Rally {playingClip.rally_id + 1}</strong>
              <span className="muted"> · {playingClip.why}</span>
            </span>
            <button onClick={() => setPlaying(null)}>Close</button>
          </div>
        </div>
      )}

      {top.length > 0 && (
        <div className="rally-top">
          <span className="rally-top-label">Top rallies</span>
          {top.map((c) => (
            <button
              key={c.rally_id}
              className={`chip ${playing === c.rally_id ? "chip-on" : ""}`}
              onClick={() => setPlaying(c.rally_id)}
            >
              #{c.rank} · Rally {c.rally_id + 1}
              <span className="rally-top-why"> {c.why}</span>
            </button>
          ))}
        </div>
      )}

      <div className="rally-table">
        <div className="rally-table-head">
          <div>#</div>
          <div>Winner</div>
          <div>Shots</div>
          <div>Duration</div>
          <div>Top speed</div>
          <div>Score after</div>
          <div />
        </div>
        {match.rallies.map((r) => {
          const shots = r.shot_ids.map((id) => shotById.get(id)).filter(Boolean);
          // Prefer confidently-projected speeds; fall back to all if none qualify.
          const confident = shots.filter((s) => s.speed_confident !== false);
          const speedPool = confident.length ? confident : shots;
          const topSpeed = speedPool.reduce((m, s) => Math.max(m, s.speed_kmh), 0);
          const ev = scoreByRally.get(r.id);
          const active = selectedRallyId === r.id;
          const clip = clipByRally.get(r.id);
          return (
            <div key={r.id} className={`rally-row ${active ? "rally-row-active" : ""}`}>
              <button
                className="rally-main"
                onClick={() => onSelectRally(r.id)}
                aria-pressed={active}
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
              <div className="rally-play">
                {clip && (
                  <button
                    className="chip"
                    onClick={() => setPlaying(r.id)}
                    aria-label={`Play rally ${r.id + 1}`}
                  >
                    ▶ Play
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {clipByRally.size === 0 && (
        <p className="muted rallies-help rallies-hint">
          No rally clips for this match. Cut them with{" "}
          <code>python run.py highlights match.mp4 --match match.json --out-dir
          ../frontend/public/rallies --reel</code>{" "}
          and each rally becomes its own playable point.
        </p>
      )}
    </div>
  );
}
