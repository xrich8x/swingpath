import { useEffect, useMemo, useRef, useState } from "react";
import sampleMatch from "./data/sample_match.json";
import analyzedMatch from "./data/analyzed_match.json";
import Court from "./components/Court.jsx";
import Statistics from "./components/Statistics.jsx";
import Rallies from "./components/Rallies.jsx";
import Broadcast from "./components/Broadcast.jsx";
import CourtSetup from "./components/CourtSetup.jsx";
import { playerName } from "./lib/format.js";

const TABS = ["Broadcast", "Court", "Statistics", "Rallies", "Court Setup"];

export default function App() {
  const [match, setMatch] = useState(sampleMatch);
  const [source, setSource] = useState("demo");
  const [tab, setTab] = useState("Court");
  const [selectedRallyId, setSelectedRallyId] = useState(null);
  const [loadError, setLoadError] = useState(null);
  // Cache-buster for the annotated video: version by the FILE's headers, not the
  // match metadata — a re-render with identical stats still changes the overlay.
  const [videoVer, setVideoVer] = useState("");
  const fileRef = useRef(null);

  useEffect(() => {
    fetch("/analyzed.mp4", { method: "HEAD" })
      .then((r) =>
        setVideoVer(
          `${r.headers.get("last-modified") ?? ""}-${r.headers.get("content-length") ?? ""}`
        )
      )
      .catch(() => {});
  }, []);

  function pickSource(which) {
    setSource(which);
    setMatch(which === "analyzed" ? analyzedMatch : sampleMatch);
    setSelectedRallyId(null);
    setLoadError(null);
  }

  const selectedRally = useMemo(
    () =>
      selectedRallyId == null
        ? null
        : match.rallies.find((r) => r.id === selectedRallyId) ?? null,
    [match, selectedRallyId]
  );

  function handleSelectRally(id) {
    setSelectedRallyId((cur) => (cur === id ? null : id));
  }

  async function handleLoad(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (!data.shots || !data.rallies || !data.court) {
        throw new Error("Not a match.json (missing shots / rallies / court).");
      }
      setMatch(data);
      setSelectedRallyId(null);
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      e.target.value = "";
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">●</span>
          <div>
            <div className="brand-title">SwingVision Clone</div>
            <div className="brand-sub">single-camera tennis analyzer</div>
          </div>
        </div>

        <div className="source-toggle" role="group" aria-label="Data source">
          <button
            className={`seg ${source === "demo" ? "seg-active" : ""}`}
            onClick={() => pickSource("demo")}
          >
            Demo (synthetic)
          </button>
          <button
            className={`seg ${source === "analyzed" ? "seg-active" : ""}`}
            onClick={() => pickSource("analyzed")}
          >
            Analyzed clip
          </button>
        </div>

        <div className="scoreline" title="Final / running score">
          <div className="scoreline-players">
            {playerName(match, "A")} vs {playerName(match, "B")}
          </div>
          <div className="scoreline-score">{match.score.final}</div>
        </div>

        <div className="topbar-actions">
          <button className="btn" onClick={() => fileRef.current?.click()}>
            Load match
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            onChange={handleLoad}
            hidden
          />
        </div>
      </header>

      {loadError && <div className="banner banner-error">⚠ {loadError}</div>}

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? "tab-active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>

      <main className="content">
        {tab === "Broadcast" && (
          <Broadcast
            match={match}
            // Version the URL from the match metadata so a regenerated video is
            // never served stale from the browser cache.
            videoUrl={
              source === "analyzed"
                ? `/analyzed.mp4?v=${encodeURIComponent(
                    videoVer ||
                      `${match.video.filename}-${match.video.duration_s}-${match.stats.shot_count}`
                  )}`
                : null
            }
          />
        )}
        {tab === "Court" && (
          <Court
            match={match}
            selectedRally={selectedRally}
            onSelectRally={handleSelectRally}
          />
        )}
        {tab === "Statistics" && <Statistics match={match} />}
        {tab === "Rallies" && (
          <Rallies
            match={match}
            selectedRallyId={selectedRallyId}
            onSelectRally={handleSelectRally}
          />
        )}
        {tab === "Court Setup" && <CourtSetup />}
      </main>

      <footer className="footer">
        {source === "analyzed" ? (
          <>
            Analyzed from <code>{match.video.filename}</code> — TrackNet ball + YOLO-pose
            players, projected to court metres. Speeds are approximate (single camera).
          </>
        ) : (
          <>
            Demo data is synthetic (no model weights). Regenerate:&nbsp;
            <code>python run.py demo --out ../frontend/src/data/sample_match.json</code>
          </>
        )}
      </footer>
    </div>
  );
}
