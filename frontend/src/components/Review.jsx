import { useMemo, useState } from "react";
import { fmtDuration, fmtSpeed, playerName } from "../lib/format.js";

/**
 * Review — overrule the analyzer, point by point.
 *
 * README has listed this as a known gap from the start: "Scoring from vision alone
 * is brittle; a manual-correction UI is a known gap." The brittleness is
 * structural — a rally winner rests on a bounce a single camera cannot always
 * place — so the answer is not a better detector, it is letting the person who
 * watched the match say what happened.
 *
 * This panel only ever EDITS FACTS: who won a rally, whether a ball was in, what
 * stroke it was. It never touches the score or the stats, because those are
 * derived. Corrections export as a small JSON that `run.py correct` applies, and
 * the backend replays scoring.TennisScore and schema.compute_stats to produce a
 * corrected match.json. One implementation of the tennis rules, not two.
 */
export default function Review({ match }) {
  // Keyed "target:id" so a second edit of the same field replaces the first
  // rather than stacking — the file should say what you decided, not how you got there.
  const [edits, setEdits] = useState({});
  const shotById = useMemo(
    () => new Map(match.shots.map((s) => [s.id, s])),
    [match]
  );
  const players = (match.players ?? []).map((p) => p.id).slice(0, 2);
  const [pA, pB] = players.length === 2 ? players : ["A", "B"];

  function setEdit(target, id, value, original) {
    const key = `${target}:${id}`;
    setEdits((cur) => {
      const next = { ...cur };
      if (value === original) delete next[key];        // back to what it said: not a correction
      else next[key] = { target, id, value, original };
      return next;
    });
  }

  function valueOf(target, id, current) {
    return edits[`${target}:${id}`]?.value ?? current;
  }

  const list = Object.values(edits);

  function download() {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            tool: "dashboard Review tab",
            match: match.video?.filename ?? null,
            corrections: list,
          },
          null,
          1
        ),
      ],
      { type: "application/json" }
    );
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "corrections.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="review">
      <p className="muted review-help">
        Fix what the analyzer got wrong. Changing a winner or a call here does{" "}
        <strong>not</strong> edit the score — export the corrections and run{" "}
        <code>run.py correct match.json --corrections corrections.json</code>, which
        replays the scoring rules so everything stays consistent.
      </p>

      <div className="review-bar">
        <span>
          {list.length === 0
            ? "No corrections yet"
            : `${list.length} correction${list.length === 1 ? "" : "s"}`}
        </span>
        <span className="review-bar-actions">
          <button onClick={() => setEdits({})} disabled={!list.length}>
            Reset
          </button>
          <button className="primary" onClick={download} disabled={!list.length}>
            Export corrections
          </button>
        </span>
      </div>

      {match.rallies.map((r) => {
        const shots = r.shot_ids.map((id) => shotById.get(id)).filter(Boolean);
        const winner = valueOf("rally.winner", r.id, r.winner);
        const changed = winner !== r.winner;
        return (
          <div key={r.id} className={`review-rally ${changed ? "review-changed" : ""}`}>
            <div className="review-rally-head">
              <strong>Rally {r.id + 1}</strong>
              <span className="muted">
                {fmtDuration(r.end_s - r.start_s)} · {r.shot_ids.length} shot
                {r.shot_ids.length === 1 ? "" : "s"}
              </span>
              <span className="review-winner">
                Point to:
                {[pA, pB].map((p) => (
                  <button
                    key={p}
                    className={`chip ${winner === p ? "chip-on" : ""}`}
                    onClick={() => setEdit("rally.winner", r.id, p, r.winner)}
                  >
                    {playerName(match, p)}
                  </button>
                ))}
                {changed && <em className="review-was">was {playerName(match, r.winner)}</em>}
              </span>
            </div>

            <div className="review-shots">
              {shots.map((s) => {
                const call = valueOf("shot.call", s.id, s.call);
                const type = valueOf("shot.type", s.id, s.type);
                return (
                  <div key={s.id} className="review-shot">
                    <span className="muted">{s.t_hit_s.toFixed(1)}s</span>
                    <span>{playerName(match, s.player)}</span>
                    <select
                      value={type}
                      onChange={(e) => setEdit("shot.type", s.id, e.target.value, s.type)}
                    >
                      {["serve", "forehand", "backhand", "volley", "smash", "slice"].map(
                        (t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        )
                      )}
                    </select>
                    <span className="review-call">
                      {["in", "out"].map((c) => (
                        <button
                          key={c}
                          className={`chip ${call === c ? "chip-on" : ""}`}
                          onClick={() => setEdit("shot.call", s.id, c, s.call)}
                        >
                          {c}
                        </button>
                      ))}
                      {/* The analyzer already knows when it could not be sure. Say so,
                          so the eye goes to the calls actually worth reviewing. */}
                      {s.call_confident === false && (
                        <em className="review-flag" title="The analyzer was not confident in this call">
                          unsure
                        </em>
                      )}
                    </span>
                    <span className="muted">
                      {fmtSpeed(s.speed_kmh)}
                      {s.speed_confident === false ? " (est)" : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
