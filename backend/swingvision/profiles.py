"""Capture profile — AMATEUR (phone) footage. One codebase, one focus.

The product hyperfocuses on amateur footage: phone/practice clips, low OR high
mount, 720p, motion blur, non-standard courts. This module is the single place
that declares how that profile configures the pipeline; the geometry (homography,
projection, speed) and the logic (scoring, rallies) are shared.

  amateur  phone/practice: any mount height, 720p, motion blur, non-standard courts

Note: for HIGH-angle amateur clips with clean straight lines, the classical
auto court-setup in calibration.detect_court_broadcast is a candidate automatic
path (it snaps four corners onto detected white lines); low/oblique phone angles
still fall back to a manual corner-drag or the learned CourtNet.
"""

from __future__ import annotations

PROFILES: dict[str, dict] = {
    "amateur": {
        # Court: manual corner-drag or learned CourtNet. High-angle clips can also
        # try calibration.detect_court_broadcast; low/oblique angles need corners.
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
