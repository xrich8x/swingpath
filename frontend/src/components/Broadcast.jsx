import { useState } from "react";
import { fmtDuration } from "../lib/format.js";

export default function Broadcast({ match, videoUrl }) {
  // videoUrl is the annotated overlay video (court + players + ball + shot labels),
  // produced by `run.py analyze --annotate`. Falls back to a placeholder if absent
  // or unplayable (e.g. the synthetic demo, which has no footage).
  const [failed, setFailed] = useState(false);
  const showVideo = Boolean(videoUrl) && !failed;

  return (
    <div className="broadcast">
      <div className="broadcast-frame">
        {showVideo ? (
          <video
            className="broadcast-video"
            src={videoUrl}
            controls
            playsInline
            onError={() => setFailed(true)}
          />
        ) : (
          <div className="broadcast-empty">
            <div className="broadcast-icon">▶</div>
            <h3>No annotated video for this match</h3>
            <p className="muted">
              The synthetic demo has no footage. Analyze a real clip with{" "}
              <code>--annotate</code> and this becomes the video with the court overlay,
              player skeletons, ball trail, and shot/line-call labels drawn on top.
            </p>
            <code>
              python run.py analyze match.mp4 --keypoints court_pts.json --annotate --out
              ../data/output/match.json
            </code>
          </div>
        )}
      </div>
      <div className="broadcast-meta">
        <div>
          <span className="muted">Source</span>
          <div>{match.video.filename}</div>
        </div>
        <div>
          <span className="muted">Duration</span>
          <div>{fmtDuration(match.video.duration_s)}</div>
        </div>
        <div>
          <span className="muted">Resolution</span>
          <div>
            {match.video.width}×{match.video.height} @ {Math.round(match.video.fps)}fps
          </div>
        </div>
      </div>
    </div>
  );
}
