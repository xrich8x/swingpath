"""Perception-cache provenance (pipeline._build_provenance /
_provenance_mismatches): every new cache must record how it was built, and
loading a cache under different settings must be detected — this is the guard
against untraceable caches like the archived demo30 one (HANDOFF.md §6)."""

import numpy as np

from swingvision import pipeline

H = np.array([[1.0, 0.1, 5.0],
              [0.0, 1.2, 3.0],
              [0.0, 0.0, 1.0]])


def _stamp(tmp_path, **overrides):
    w = tmp_path / "w.pt"
    if not w.exists():
        w.write_bytes(b"weights-bytes")
    kw = dict(ball_model="tracknet", weight_files={"tracknet": str(w)},
              pose_model="yolo11m-pose.pt@1280", device="cpu",
              camera_hfov_deg=70.0, cam_h=4.4, gate_on=True, H=H)
    kw.update(overrides)
    return pipeline._build_provenance(**kw)


def test_provenance_records_required_fields(tmp_path):
    prov = _stamp(tmp_path)
    assert prov["ball_model"] == "tracknet"
    assert prov["pose_model"] == "yolo11m-pose.pt@1280"
    assert prov["device"] == "cpu"
    assert prov["camera_hfov_deg"] == 70.0
    assert prov["court_gate_min_cam_h_m"] == pipeline.COURT_GATE_MIN_CAM_H
    assert prov["court_gate_on"] is True
    assert prov["weights"]["tracknet"]["sha256"]
    assert prov["homography_sha256"] == pipeline._homography_fingerprint(H)
    assert prov["created_utc"]


def test_matching_settings_produce_no_warnings(tmp_path):
    prov = _stamp(tmp_path)
    assert pipeline._provenance_mismatches(prov, "cpu", 70.0, H) == []


def test_mismatched_settings_are_detected(tmp_path):
    prov = _stamp(tmp_path, device="cuda", camera_hfov_deg=93.5)
    H2 = H.copy()
    H2[0, 2] += 4.0  # a different calibration
    diffs = pipeline._provenance_mismatches(prov, "cpu", 70.0, H2)
    text = "\n".join(diffs)
    assert "device" in text and "cuda" in text
    assert "hfov" in text and "93.5" in text
    assert "calibration" in text
    # Weight file edited on disk after the cache was built -> flagged too.
    (tmp_path / "w.pt").write_bytes(b"retrained-weights")
    diffs = pipeline._provenance_mismatches(prov, "cuda", 93.5, H)
    assert any("CHANGED" in d for d in diffs)


def test_homography_fingerprint_is_scale_invariant():
    # Homographies are defined up to scale; the fingerprint must agree.
    assert (pipeline._homography_fingerprint(H)
            == pipeline._homography_fingerprint(2.5 * H))
    H2 = H.copy()
    H2[1, 2] += 0.01
    assert (pipeline._homography_fingerprint(H)
            != pipeline._homography_fingerprint(H2))
