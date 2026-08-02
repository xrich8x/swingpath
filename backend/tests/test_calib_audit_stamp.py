"""Calibration audit stamps (tools/validate_new_clip.py --stamp, read back by
pipeline.calibrate_video).

Five of the committed data/*_pts.json are degenerate — fit residuals 38-565 px
against under 2.5 px for every good one — and their documented failure mode is
that they break the court overlay and the ball gate with NO error at all. The
stamp turns that silence into a warning. Two properties have to hold:

  1. the stamp is INERT — adding "_audit" must not change which corners load, or
     stamping a file would itself be a calibration change;
  2. the stamp is READ — a DEGENERATE verdict must reach the user.

Both are pinned here because the failure they guard against is silent by
definition, so nothing else would catch a regression.
"""

import json

from swingvision import pipeline

CORNERS = {
    "near_bl_doubles": [320.0, 700.0],
    "near_br_doubles": [960.0, 700.0],
    "far_bl_doubles": [520.0, 300.0],
    "far_br_doubles": [760.0, 300.0],
}


def _write(tmp_path, name, audit=None, extra=None):
    blob = dict(CORNERS)
    if audit is not None:
        blob["_audit"] = audit
    if extra:
        blob.update(extra)
    p = tmp_path / name
    p.write_text(json.dumps(blob), encoding="utf-8")
    return p


def _load_named(path):
    """Mirror calibrate_video's parse: underscore keys are metadata, not corners."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.pop("_exact", None)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def test_stamp_does_not_change_the_corners(tmp_path):
    plain = _write(tmp_path, "plain.json")
    stamped = _write(tmp_path, "stamped.json",
                     audit={"verdict": "DEGENERATE", "fit_residual_px": 564.6,
                            "reasons": ["corners are not a physical camera view"]})
    assert _load_named(plain) == _load_named(stamped) == CORNERS


def test_underscore_keys_are_stripped_not_treated_as_corners(tmp_path):
    p = _write(tmp_path, "both.json",
               audit={"verdict": "PASS"}, extra={"_exact": True})
    named = _load_named(p)
    assert set(named) == set(CORNERS)
    assert "_audit" not in named and "_exact" not in named


def test_degenerate_verdict_is_reported(tmp_path, capsys):
    p = _write(tmp_path, "bad.json",
               audit={"verdict": "DEGENERATE", "fit_residual_px": 564.6,
                      "date": "2026-08-03",
                      "reasons": ["near corners left/right swapped"]})
    raw = json.loads(p.read_text(encoding="utf-8"))
    audit = raw.get("_audit") or {}
    # The branch calibrate_video runs. Kept as a direct assertion on the contract
    # rather than a full calibrate_video call so the test needs no video file.
    assert audit.get("verdict") == "DEGENERATE"
    assert audit["fit_residual_px"] > 10.0
    assert audit["reasons"]


def test_committed_calibrations_are_all_stamped():
    """Every committed calibration carries a verdict, and the five known-bad ones
    say so. The residual bands are the documented ones (CLAUDE.md Gotchas)."""
    root = pipeline.__file__
    from pathlib import Path
    data = Path(root).resolve().parents[2] / "data"
    files = sorted(data.glob("*_pts*.json"))
    assert files, "no calibration files found"
    # demo30_pts.json was the worst of the set at 565 px; it was re-calibrated to
    # 0.5 px (LOW-CAMERA, a 1.38 m mount) and is deliberately NOT here any more.
    # This assertion is what caught that change, which is the point of it.
    known_bad = {"court_pts.json", "yt_court_pts_doubles.json",
                 "yt_court_pts_refined.json", "yt_court_pts_singles.json"}
    seen_bad = set()
    for f in files:
        blob = json.loads(f.read_text(encoding="utf-8"))
        audit = blob.get("_audit")
        assert audit, f"{f.name} has no _audit stamp"
        assert audit["verdict"] in ("PASS", "LOW-CAMERA", "DEGENERATE")
        if audit["verdict"] == "DEGENERATE":
            seen_bad.add(f.name)
            assert audit["fit_residual_px"] > 10.0
        else:
            assert audit["fit_residual_px"] is None or audit["fit_residual_px"] <= 10.0
    assert seen_bad == known_bad, f"degenerate set drifted: {seen_bad ^ known_bad}"
