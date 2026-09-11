"""An older match.json must open. A newer one must not be able to lie.

`setup` is an ADDITIVE block and `SCHEMA_VERSION` deliberately does not move for
it. Every match.json ever written by this project lacks the key; bumping the
version would have made `schema.validate` reject all of them, which is a
compatibility break dressed up as bookkeeping. So the contract this file pins is:

  * no `setup` key            -> validates, loads, reads as `unknown`
  * a partial / unknown-value one -> loads as `unknown`, never as `clear`
  * a self-contradicting one  -> FAILS validation loudly
  * a corrections replay      -> carries the state through, and cannot upgrade it

The asymmetry is the point. Reading is forgiving (an old file opens); writing is
strict (a file may not claim its numbers are verified when its own two axes say
otherwise). Trap T23 and T26 are both cases of a claim outliving its evidence.

Also here: the three representative fixtures (clear / limited / overlap) that the
frontend and any mobile consumer can be pointed at. They are built from the same
synthetic pinhole the state tests use, so they need no footage and no weights.
"""

import json
import math

import numpy as np
import pytest

from swingvision import corrections, court, schema
from swingvision import setup_state as ss

pytest.importorskip("scipy")

from swingvision import calibration as C  # noqa: E402

DBL = ["near_bl_doubles", "near_br_doubles", "far_br_doubles", "far_bl_doubles"]
W, H = 1280, 720


def _cam(Cz, hfov_deg=74.0, back=8.0):
    f_px = W / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))
    Cx, Cy = court.DOUBLES_WIDTH / 2.0, -back
    pitch = math.atan2(Cz, back + court.LENGTH * 0.5)
    st, ct = math.sin(pitch), math.cos(pitch)
    fwd, right, up = (np.array([0.0, ct, -st]), np.array([1.0, 0.0, 0.0]),
                      np.array([0.0, st, ct]))
    img, wld = [], []
    for n in DBL:
        X, Y = court.LANDMARKS[n]
        d = np.array([X - Cx, Y - Cy, -Cz])
        z = d @ fwd
        img.append([W / 2 + f_px * (d @ right) / z, H / 2 - f_px * (d @ up) / z])
        wld.append([X, Y])
    return C.compute_homography(wld, img)


def _minimal_match(setup=None):
    """The smallest dict `schema.validate` accepts, plus one shot so the
    corrections path has something to act on."""
    m = {
        "schema_version": schema.SCHEMA_VERSION,
        "video": {"filename": "x.mp4", "fps": 30.0, "width": W, "height": H,
                  "duration_s": 10.0},
        "court": {"length_m": court.LENGTH, "width_m": court.DOUBLES_WIDTH},
        "players": [{"id": "A", "name": "Near"}, {"id": "B", "name": "Far"}],
        "shots": [{"id": 1, "rally_id": 1, "player": "A", "type": "forehand",
                   "t_hit_s": 1.0, "speed_kmh": 90.0, "hit_xy": [5.0, 2.0],
                   "bounce_xy": [5.0, 15.0], "bounce_t_s": 1.4, "is_in": True,
                   "call": "in"}],
        "rallies": [{"id": 1, "start_s": 0.5, "end_s": 2.0, "shot_ids": [1],
                     "winner": "A", "ball_track": []}],
        "score": {"final": "0-0", "sets": [], "games": [0, 0], "timeline": []},
        "stats": {"shot_count": 1, "rally_count": 1, "avg_speed_kmh": 90.0,
                  "top_speed_kmh": 90.0, "shot_mix": {"forehand": 1},
                  "line_calls": {"in": 1, "out": 0, "uncertain": 0}},
    }
    if setup is not None:
        m["setup"] = setup
    return m


# --- fixtures the whole product can be pointed at ---------------------------
FIXTURE_MOUNTS = {"clear": 3.4, "overlap": 1.5}


def _fixture(kind):
    """A representative match.json for one framing state. `clear` is the only
    one that is also `user_confirmed`, because that is the only combination in
    which the product presents court numbers as verified."""
    if kind == "limited":
        for cz in np.arange(2.0, 3.0, 0.02):
            st = ss.from_homography(_cam(float(cz)), (W, H),
                                    calibration_status=ss.CALIB_USER_CONFIRMED)
            if st.framing_status == ss.FRAMING_LIMITED:
                break
        else:
            pytest.fail("no limited-band camera height found")
    else:
        st = ss.from_homography(
            _cam(FIXTURE_MOUNTS[kind]), (W, H),
            calibration_status=(ss.CALIB_USER_CONFIRMED if kind == "clear"
                                else ss.CALIB_USER_CONFIRMED))
    return _minimal_match(st.to_dict())


@pytest.mark.parametrize("kind", ["clear", "limited", "overlap"])
def test_each_representative_fixture_validates(kind):
    m = _fixture(kind)
    assert m["setup"]["framing_status"] == kind
    assert schema.validate(m) == []


def test_only_the_clear_fixture_presents_verified_metrics():
    """All three fixtures are hand-confirmed calibrations, so the ONLY thing
    separating them is what the camera could see. That is the product claim."""
    got = {k: _fixture(k)["setup"]["metrics_eligible"]
           for k in ("clear", "limited", "overlap")}
    assert got == {"clear": True, "limited": False, "overlap": False}


@pytest.mark.parametrize("kind", ["limited", "overlap"])
def test_the_limited_fixtures_keep_every_reviewable_field(kind):
    """A limited setup loses claims, never content. The shots, the rallies and
    the score are all still there to review and correct."""
    m = _fixture(kind)
    assert m["shots"] and m["rallies"] and m["score"]
    assert m["stats"]["shot_count"] == 1


# --- backwards compatibility -------------------------------------------------
def test_a_match_without_a_setup_block_validates():
    """Every match.json written before this feature. It must open."""
    assert schema.validate(_minimal_match()) == []


def test_a_match_without_a_setup_block_reads_as_unknown():
    m = _minimal_match()
    n = ss.normalize(m.get("setup"))
    assert n["framing_status"] == ss.FRAMING_UNKNOWN
    assert n["metrics_eligible"] is False


def test_a_match_survives_a_json_round_trip():
    m = _fixture("overlap")
    back = json.loads(json.dumps(m))
    assert back["setup"] == m["setup"]
    assert schema.validate(back) == []


def test_a_new_match_always_carries_a_setup_block():
    """The default is a full `unknown` state, not None: every path that builds a
    Match produces a file the UI can read with no null check, because 'we did not
    measure this' is a real answer and deserves to be written down."""
    m = schema.Match(video=schema.Video("x.mp4", 30.0, W, H, 1.0), players=[],
                     shots=[], rallies=[],
                     score=schema.Score(final="0-0", sets=[], games=[0, 0]),
                     stats=schema.compute_stats([], []))
    d = m.to_dict()
    assert d["setup"]["framing_status"] == ss.FRAMING_UNKNOWN
    assert d["setup"]["metrics_eligible"] is False


# --- a file may not lie -------------------------------------------------------
def test_validate_rejects_a_setup_that_contradicts_itself():
    m = _minimal_match({"framing_status": "overlap",
                        "calibration_status": "provisional",
                        "metrics_eligible": True, "reasons": []})
    problems = schema.validate(m)
    assert any("metrics_eligible" in p for p in problems), problems


def test_validate_rejects_an_unknown_status_string():
    m = _minimal_match({"framing_status": "excellent",
                        "calibration_status": "user_confirmed",
                        "metrics_eligible": False, "reasons": []})
    assert any("framing_status" in p for p in schema.validate(m))


def test_validate_rejects_a_non_object_setup():
    assert any("setup" in p for p in schema.validate(_minimal_match("clear")))


# --- corrections --------------------------------------------------------------
def _correct(match, items):
    fixed, res = corrections.apply_corrections(match, items)
    return fixed, res


def test_a_correction_carries_the_setup_state_through_unchanged():
    """A correction changes facts about the match. It cannot change what the
    camera could see."""
    m = _fixture("overlap")
    before = dict(m["setup"])
    fixed, res = _correct(m, [{"target": "shot.call", "id": 1, "value": "out"}])
    assert res.applied, "the fixture correction did not apply"
    assert fixed["setup"] == before
    assert fixed["stats"]["line_calls"]["out"] == 1, "stats did re-derive"


def test_a_correction_cannot_launder_a_hand_edited_claim():
    """The one way a replay could have upgraded trust: edit `metrics_eligible`
    to true, apply a correction, let the replay bless it. `normalize` re-derives
    the field from the two axes, so the edit dies at the replay."""
    m = _fixture("overlap")
    m["setup"]["metrics_eligible"] = True
    fixed, _ = _correct(m, [{"target": "shot.call", "id": 1, "value": "out"}])
    assert fixed["setup"]["metrics_eligible"] is False


def test_a_correction_on_an_old_match_gives_it_an_explicit_unknown_state():
    """An old file with no block acquires one on its first replay, rather than
    silently keeping none - so a corrected export is always self-describing."""
    m = _minimal_match()
    fixed, _ = _correct(m, [{"target": "shot.call", "id": 1, "value": "out"}])
    assert fixed["setup"]["framing_status"] == ss.FRAMING_UNKNOWN
    assert schema.validate(fixed) == []
