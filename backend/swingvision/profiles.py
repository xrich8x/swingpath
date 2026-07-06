"""Two capture profiles — PRO (broadcast) and AMATEUR (phone) — one codebase.

Broadcast and amateur footage are different domains and want different
perception. This module is the single place that declares how each profile
configures the pipeline; the geometry (homography, projection, speed) and the
logic (scoring, rallies) are shared and identical for both.

  pro      official/broadcast: fixed high camera, clean lines, standard courts
  amateur  phone/practice: low mount, 720p, motion blur, non-standard courts

Rationale per field lives inline. Callers: calibration.calibrate_for_profile
(court method) and pipeline/run.py (ball + gates + bounce). Fields that name a
not-yet-built component (bounce="classifier") are the roadmap for the pro path
(reimplement ArtLabss's trajectory bounce classifier); until then the caller
falls back to the shared heuristic.
"""

from __future__ import annotations

PROFILES: dict[str, dict] = {
    "pro": {
        # Court: automatic broadcast line-snap (calibration.detect_court_broadcast).
        # Clean straight lines on a fixed camera fit precisely; refuses + falls
        # back if coverage is low, never emits a skewed overlay.
        "court": "broadcast",
        # Ball: TrackNet+WASB fusion — TrackNet's training domain is broadcast.
        "ball_model": "fusion",
        "pose_quality": "accurate",
        # High camera: an airborne ball projects only slightly past the court, so
        # the court-plausibility gate is sound.
        "court_gate": True,
        "live_ball_filter": True,
        # Bounce: reimplement ArtLabss's trained trajectory classifier (98%/83%).
        # NOT built yet -> caller uses the shared heuristic until it exists.
        "bounce": "classifier",
    },
    "amateur": {
        # Court: manual corner-drag or learned CourtNet — broadcast auto-detect
        # fails on low/oblique phone angles (measured).
        "court": "manual",
        # Ball: fusion + BallNet v2 available; the live-ball filter does the heavy
        # lifting on false-fire once corners exist.
        "ball_model": "fusion",
        "pose_quality": "accurate",
        # Low phone camera (~2 m): an airborne ball's ground projection lands tens
        # of metres out, so the court gate would eat real detections -> OFF.
        "court_gate": False,
        "live_ball_filter": True,
        "bounce": "heuristic",
    },
}

DEFAULT_PROFILE = "amateur"


def get_profile(name: str | None) -> dict:
    """Return a profile config by name (defaults to amateur). Raises on unknown."""
    key = (name or DEFAULT_PROFILE).lower()
    if key not in PROFILES:
        raise ValueError(f"unknown profile {name!r}; choose from {list(PROFILES)}")
    return PROFILES[key]
