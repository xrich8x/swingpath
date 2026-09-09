"""The setup tool's Save now stamps `_provenance`. It must not have moved a corner.

Repo rule 8: a refactor must prove it changed nothing. The thing that must not
change is the four corner NUMBERS the tool writes, on BOTH save paths (shape lock
ON and OFF). Everything else in the file is new metadata.

Three claims, in order of how much they would cost if broken:

  1. STRUCTURAL, machine-independent. Take the new file, drop `_provenance`, dump
     it again with the same options -- you get the pre-change text back character
     for character. This is the whole byte-identity claim, and it holds for any
     corner values, so it does not depend on this machine's optimiser arithmetic.
  2. END-TO-END, self-consistent. Drive the real `/api/save` over HTTP on both
     paths and check the corners ON DISK are byte-identical to the corners the
     handler reported in its own reply. This pins that `save_text` writes exactly
     what `lock_shape` returned, with no rounding or reordering in between.
  3. GOLDEN. The lock-ON corners for one fixed placement, captured by running the
     PRE-change code (tools/court_setup_server.py at d4fb85b) on 2026-09-09.
     Compared with a tolerance rather than `==`: the shape lock is a scipy
     optimisation and its last bits are not portable across BLAS builds. A drift
     of more than a nanopixel is not floating point, it is a behaviour change.

See docs/evidence/calibration-provenance.md.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

css = pytest.importorskip("court_setup_server")

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]

# A deliberately NOT-shape-locked quad, so the lock-ON path has real work to do
# and `moved_px` is non-zero. Placed on a 1280x720 frame.
PLACEMENT = {
    "near_bl_doubles": [210.0, 690.0],
    "near_br_doubles": [1090.0, 700.0],
    "far_br_doubles": [830.0, 300.0],
    "far_bl_doubles": [470.0, 296.0],
}

# Captured from the PRE-provenance code. See the module docstring.
GOLDEN_LOCK_ON = {
    "near_bl_doubles": [210.00000123933387, 690.000000668731],
    "near_br_doubles": [1089.9999992723165, 700.0000047979105],
    "far_br_doubles": [829.9605873021665, 299.4931770119386],
    "far_bl_doubles": [469.9982650203806, 296.01333126950584],
}
GOLDEN_LOCK_ON_MOVED = 0.5083531272432631
TOL_PX = 1e-9


def _legacy_text(named, exact):
    """Exactly what /api/save wrote before `_provenance` existed (d4fb85b)."""
    data = dict(named)
    if exact:
        data["_exact"] = True
    return json.dumps(data, indent=2)


def _strip_provenance(text):
    d = json.loads(text)
    assert "_provenance" in d, "save did not stamp provenance"
    d.pop("_provenance")
    return json.dumps(d, indent=2)


@pytest.mark.parametrize("exact", [False, True])
def test_provenance_is_purely_additive(exact):
    """CLAIM 1. Dropping `_provenance` reproduces the old file byte for byte."""
    prov = css.provenance_block({}, shape_lock=not exact, moved_px=1.25)
    new = css.save_text(PLACEMENT, exact=exact, provenance=prov)
    assert _strip_provenance(new) == _legacy_text(PLACEMENT, exact)


def test_provenance_never_precedes_the_corners():
    """A key inserted AHEAD of the corners would reflow their text. Order matters."""
    prov = css.provenance_block({}, shape_lock=True, moved_px=0.0)
    keys = list(json.loads(css.save_text(PLACEMENT, True, prov)).keys())
    assert keys[:4] == DBL
    assert keys[4:] == ["_exact", "_provenance"]


def test_save_text_without_provenance_is_the_legacy_writer():
    """Belt and braces: no provenance argument -> the old text, unconditionally."""
    for exact in (False, True):
        assert css.save_text(PLACEMENT, exact=exact) == _legacy_text(PLACEMENT, exact)


def _save_over_http(tmp_path, lock):
    """Drive the REAL handler and return (file_text, http_reply)."""
    out = tmp_path / f"{'on' if lock else 'off'}_pts.json"
    state = {"frame": np.zeros((720, 1280, 3), np.uint8), "out": str(out),
             "seed": None, "static_mask": None, "seq": 0}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), css.build_handler(state))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{srv.server_address[1]}/api/save",
            json.dumps({"corners": PLACEMENT, "lock": lock}).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            reply = json.loads(r.read())
    finally:
        srv.shutdown()
        srv.server_close()
    return out.read_text(encoding="utf-8"), reply


@pytest.mark.parametrize("lock", [True, False])
def test_saved_corners_match_the_handlers_own_reply(tmp_path, lock):
    """CLAIM 2. Disk and reply agree byte for byte, on both paths."""
    text, reply = _save_over_http(tmp_path, lock)
    on_disk = {k: v for k, v in json.loads(text).items() if not k.startswith("_")}
    assert list(on_disk) == DBL
    assert json.dumps(on_disk) == json.dumps(reply["corners"])
    # ...and the file is still the legacy file plus provenance.
    assert _strip_provenance(text) == _legacy_text(on_disk, exact=not lock)


def test_lock_off_still_writes_exact_and_does_not_move_the_placement(tmp_path):
    text, reply = _save_over_http(tmp_path, lock=False)
    d = json.loads(text)
    assert d["_exact"] is True
    assert {k: d[k] for k in DBL} == PLACEMENT      # shape lock OFF = untouched
    assert reply["moved"] == 0.0
    assert d["_provenance"]["shape_lock"] is False
    assert d["_provenance"]["moved_px"] == 0.0


def test_lock_on_corners_match_the_pre_change_golden(tmp_path):
    """CLAIM 3. The shape lock still solves to the same place it did at d4fb85b."""
    text, reply = _save_over_http(tmp_path, lock=True)
    d = json.loads(text)
    for k in DBL:
        for got, want in zip(d[k], GOLDEN_LOCK_ON[k]):
            assert abs(got - want) < TOL_PX, f"{k} moved: {got} vs {want}"
    assert abs(reply["moved"] - GOLDEN_LOCK_ON_MOVED) < TOL_PX


def test_moved_px_is_recorded_and_is_the_value_the_reply_reports(tmp_path):
    """The point of the exercise: lock-ON used to DISCARD how far it shifted."""
    text, reply = _save_over_http(tmp_path, lock=True)
    prov = json.loads(text)["_provenance"]
    assert prov["shape_lock"] is True
    assert prov["moved_px"] == reply["moved"] > 0.0


def test_placed_by_does_not_claim_a_human():
    """`_exact` was read as 'a human placed this'. Nothing here may repeat that.

    The tool serves a localhost page; it cannot tell a person's mouse from an
    agent's POST, so the only honest default is an explicit non-attribution.
    """
    prov = css.provenance_block({}, shape_lock=True, moved_px=0.0)
    assert prov["placed_by"] == "unattributed"
    assert "human" not in json.dumps(prov).lower()


def test_source_is_null_not_invented_when_the_tool_cannot_know():
    """--video builds a median clean plate: there IS no single source frame."""
    class A:
        frame = clip = None
        video = "clip.mp4"
        no_plate = False
        camera = None
    src = css.source_desc(A())
    assert src["frame"] is None and src["kind"] == "video_clean_plate"
    assert src["video"] == "clip.mp4"

    class B(A):
        video = None
        frame = "shot.jpg"
    assert css.source_desc(B()) == {"kind": "image", "path": "shot.jpg"}

    class C(A):
        video = None
    assert css.source_desc(C())["kind"] == "unknown"


def test_provenance_key_is_underscored_so_every_reader_skips_it():
    """All 17 consumers filter `k.startswith('_')`; the new key must qualify."""
    prov = css.provenance_block({}, shape_lock=True, moved_px=0.0)
    d = json.loads(css.save_text(PLACEMENT, True, prov))
    assert [k for k in d if not k.startswith("_")] == DBL
